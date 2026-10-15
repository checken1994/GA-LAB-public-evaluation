# Auto-extracted from fast_learning_engine.py
from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import sqlite3
import time

logger = logging.getLogger(__name__)
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from scp.core.db_manager import _KNOWLEDGE_CANONICAL_DDL
from scp.core.learning_run_ledger import ledger_run
from scp.core.subsystem_telemetry import SubsystemTelemetry, telemetry_async_cycle

# [AUDIT-20260909 SSRF-S1] safe_urlopen thay raw urllib.request.urlopen.
from scp.security.url_safety import safe_urlopen

# [S8 security sweep — insecure-randomness finding][B311-fix 2026-09-30] Toàn
# bộ randomness trong module này CHỈ phục vụ stochastic sampling của câu hỏi
# học: chọn template trong ma trận quốc gia×lĩnh vực (fast_learning_cycle,
# ollama_learning_cycle), chọn quốc gia/compound để điền vào template, và
# shuffle danh sách câu hỏi compounding. KHÔNG có mục đích bảo mật: không
# token, không secret, không ID cần unguessable — khả năng đoán trước câu hỏi
# học tiếp theo không gây hại. Dùng instance SystemRandom RIÊNG ở module level
# (nguồn os.urandom, pattern: scp/security/gcg_attack.py `_GCG_RNG`) thay cho
# global RNG để (1) tách biệt với mọi lời random.seed() của module khác,
# (2) làm rõ ràng tại call site rằng đây là nguồn ngẫu nhiên phi bảo mật, và
# (3) triệt tiêu B311 của bandit. KHÔNG dùng random.Random(seed) ở đây vì
# không có contract seeded-determinism nào trên sampling câu hỏi học (grep
# tests/: không có .seed() hay tham chiếu _QUESTION_RNG).
_QUESTION_RNG = random.SystemRandom()

class FastLearningEngine:
    """
    V104.2 Fast Learning Engine (CANONICAL — post G3-MERGE).

    Cải thiện V104.1:
    - Parallel Ollama: 10 concurrent (asyncio.Semaphore)
    - Skip-already-known: check KB trước khi hỏi
    - Compounding: sinh câu hỏi sâu hơn dựa trên facts đã học
    - Adaptive interval: 1-30 min tùy throughput
    - Batch Wikipedia: 5 concurrent

    [G3-MERGE] Also serves as RealLearningEngine (via stub alias). The class
    carries BOTH the V104.2 fast-cycle methods AND the V104.1 sequential
    methods (ollama_learning_cycle, local_learning_cycle, news_learning_cycle,
    run_all_cycles) ported from real_learning_engine.py. Both API surfaces
    (`/v104/learn/ollama` → _real_learning.ollama_learning_cycle() AND
    `/v104/learn/fast` → _fast_learning.fast_learning_cycle()) resolve to
    instances of THIS class.
    """

    def __init__(self, scp_db_path: str='data/v13.db', data_dir: str='data', telemetry_subsystem: str | None=None):
        self.scp_db_path = scp_db_path
        self.data_dir = Path(data_dir)
        self._telemetry = None
        if telemetry_subsystem:
            self._telemetry = SubsystemTelemetry(telemetry_subsystem, self.data_dir)
            self._telemetry.start(mode='background', config={'db_path': str(self.scp_db_path), 'count': 50, 'llm': 'ollama', 'verify': 'wikipedia'})
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._stats = {'cycles_completed': 0, 'llm_questions_asked': 0, 'ollama_questions_skipped_known': 0, 'llm_answers_verified': 0, 'llm_kb_facts_stored': 0, 'compounding_l2_questions': 0, 'compounding_l3_questions': 0, 'avg_cycle_time_ms': 0, 'fastest_cycle_ms': 999999, 'slowest_cycle_ms': 0, 'by_domain': {}, 'by_country': {}, 'adaptive_interval_current': LEARN_INTERVAL_FAST, 'local_files_scanned': 0, 'local_facts_verified': 0, 'local_kb_facts_stored': 0, 'news_headlines_fetched': 0, 'news_questions_generated': 0, 'news_facts_stored': 0, 'news_headlines_quarantined': 0}  # noqa: F821  # [hygiene-keep] LEARN_INTERVAL_FAST injected by fast_learning_engine.py rebind/wire
        self._init_kb()
        self._ollama_semaphore: asyncio.Semaphore | None = None
        self._wiki_semaphore: asyncio.Semaphore | None = None

    def _init_kb(self) -> None:
        """Initialize knowledge tables.

        [ROOT-FIX 1] TẠI SAO: the old schema had only 8 columns (missing
        last_verified, times_wrong, bias_correction, notes) — but the UPSERT
        in _store_kb (P1-13 fix) references `last_verified`. When FastLearning
        uses a standalone test DB (scp_db_path != default), this 8-col schema
        wins → UPSERT fails → 0 rows stored → compounding L2 never generates.
        Fix: use the canonical `_KNOWLEDGE_CANONICAL_DDL` from db_manager
        (single source of truth). Legacy ALTER loop removed — db_manager's
        `_migrate_knowledge_schema` guard handles migration on the global DB,
        and on a fresh standalone DB the canonical CREATE produces the right
        schema directly.
        """
        try:
            conn = sqlite3.connect(self.scp_db_path, timeout=10.0)
            conn.execute(_KNOWLEDGE_CANONICAL_DDL)
            conn.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_entity ON knowledge(entity)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_attr ON knowledge(attribute)')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f'KB init failed: {e}', exc_info=True)

    async def _get_ollama_semaphore(self) -> asyncio.Semaphore:
        if self._ollama_semaphore is None:
            self._ollama_semaphore = asyncio.Semaphore(PARALLEL_LLM_CONCURRENCY)  # noqa: F821  # [hygiene-keep] PARALLEL_LLM_CONCURRENCY injected by fast_learning_engine.py rebind/wire
        return self._ollama_semaphore

    async def _get_wiki_semaphore(self) -> asyncio.Semaphore:
        if self._wiki_semaphore is None:
            self._wiki_semaphore = asyncio.Semaphore(WIKIPEDIA_CONCURRENCY)  # noqa: F821  # [hygiene-keep] WIKIPEDIA_CONCURRENCY injected by fast_learning_engine.py rebind/wire
        return self._wiki_semaphore

    def _is_question_known(self, question: str) -> bool:
        """Check if question đã có trong KB (entity = question).

        [V104.35 #38] TẠI SAO: V104.34 marked TODO — was: sqlite3.connect bypasses
        _db_lock (race with Brain) + entity NOT lowercased (case mismatch with
        _store_kb which lowercases). SKIP_KNOWN dead → wasted Ollama compute.
        Fix: lowercase entity (mirror _store_kb). Still use sqlite3.connect for
        self.scp_db_path isolation (db_manager uses global DB, breaks test isolation).
        The race risk is acceptable for read-only SELECT with timeout=5.0.

        [EXEC-1 B2] TẠI SAO: replaced bare sqlite3.connect with db_query_one +
        db_path=self.scp_db_path. db_manager caches per-path connections under
        the SAME _db_lock as Brain writes — eliminates the race AND keeps test
        isolation (separate cache entry per scp_db_path). Lowercasing preserved.
        """
        try:
            from scp.core.db_manager import db_query_one
            entity_lower = question.lower()[:200]
            row = db_query_one('SELECT 1 FROM knowledge WHERE entity = ? LIMIT 1', (entity_lower,), db_path=str(self.scp_db_path))
            return row is not None
        except Exception as exc:
            logger.warning("fast_learning_engine: knowledge existence check failed (treating as unknown): %s", exc, exc_info=True)
            return False

    def _get_known_countries_domains(self) -> dict:
        """Lấy set (country, domain) đã học từ KB."""
        try:
            from scp.core.db_manager import db_query_all
            rows = db_query_all("SELECT entity FROM knowledge WHERE attribute = 'verified_answer'", (), db_path=str(self.scp_db_path))
            known = set()
            for row in rows:
                entity = row['entity']
                for country in COUNTRIES:  # noqa: F821  # [hygiene-keep] COUNTRIES injected by fast_learning_engine.py rebind/wire
                    if country in entity:
                        for domain in DOMAINS:  # noqa: F821  # [hygiene-keep] DOMAINS injected by fast_learning_engine.py rebind/wire
                            domain_keywords = {'geography': ['thủ đô', 'diện tích', 'dân số', 'sông', 'núi'], 'history': ['độc lập', 'sáng lập', 'chiến tranh'], 'chemistry': ['khoáng sản', 'hóa chất', 'nhiên liệu'], 'physics': ['vật lý', 'phát minh', 'đại học'], 'biology': ['động vật', 'thực vật', 'vườn quốc gia']}
                            for kw in domain_keywords.get(domain, []):
                                if kw in entity.lower():
                                    known.add((country, domain))
                                    break
                        break
            return known
        except Exception as exc:
            logger.warning("fast_learning_engine: known-entity scan failed, returning empty set: %s", exc, exc_info=True)
            return set()

    def _generate_compounding_questions(self, count: int=5) -> list[tuple[str, str, str]]:
        """Sinh câu hỏi Level-2 dựa trên facts đã học trong KB.

        Returns: list of (question, country, domain) tuples
        """
        if not COMPOUNDING_ENABLED:  # noqa: F821  # [hygiene-keep] COMPOUNDING_ENABLED injected by fast_learning_engine.py rebind/wire
            return []
        questions = []
        try:
            from scp.core.db_manager import db_query_all
            recent_facts = db_query_all("SELECT entity, value FROM knowledge WHERE attribute = 'verified_answer' ORDER BY timestamp DESC LIMIT 20", (), db_path=str(self.scp_db_path))
            for row in recent_facts:
                entity = row['entity']
                row['value']
                entity_lower = entity.lower() if entity else ''
                for country in COUNTRIES:  # noqa: F821  # [hygiene-keep] COUNTRIES injected by fast_learning_engine.py rebind/wire
                    if country.lower() in entity_lower:
                        if 'thủ đô' in entity.lower():
                            questions.append((f'Tại sao {country} chọn thủ đô này thay cho thành phố khác?', country, 'history'))
                        elif 'diện tích' in entity.lower():
                            questions.append((f'So sánh diện tích {country} với các nước láng giềng?', country, 'geography'))
                        elif 'khoáng sản' in entity.lower():
                            questions.append((f'Khoáng sản của {country} được khai thác ở tỉnh nào nhiều nhất?', country, 'chemistry'))
                        elif 'động vật' in entity.lower():
                            questions.append((f'Động vật đặc hữu của {country} đang bị đe dọa tuyệt chủng không?', country, 'biology'))
                        break
            _QUESTION_RNG.shuffle(questions)
            return questions[:count]
        except Exception as e:
            logger.debug(f'Compounding gen failed: {e}', exc_info=True)
            return []

    async def _ask_llm_parallel(self, question: str) -> str:
        """Gọi Ollama với semaphore để parallel (10 concurrent)."""
        semaphore = await self._get_ollama_semaphore()
        async with semaphore:
            try:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self._ask_llm_sync, question)
            except Exception as e:
                logger.debug(f'Parallel Ollama call failed: {e}', exc_info=True)
                return ''

    def _ask_llm_sync(self, question: str) -> str:
        """[ARCH-1 FIX] Đã chuyển sang LLM Gateway — unified client có retry + fallback.

        TÁI SAO: trước đây dùng urllib.request.urlopen trực tiếp — sync blocking,  # nosec B310 — URL validated by SCP
        no retry, no fallback. Ollama down = learning chết. Giờ dùng llm_gateway
        có fallback Ollama → OpenRouter + retry + shared connection pool.

        [ROOT-FIX 44-A] task="fast_learning" → routes to llama3.2 (3B = fastest).
        Fast learning prioritizes throughput over depth — small model is enough
        for quick Q&A cycles where Wikipedia will verify the answer afterward.
        """
        try:
            from scp.llm_gateway import chat_sync
            answer, provider = chat_sync(question, system_prompt='Trả lời ngắn gọn bằng tiếng Việt.', task='fast_learning')
            if answer:
                self._stats['ollama_provider'] = provider
            return answer or ''
        except Exception as e:
            logger.debug(f'LLM Gateway call failed: {e}', exc_info=True)
            return ''

    async def _check_wikipedia_parallel(self, question: str, answer: str) -> dict:
        """Verify bằng Wikipedia với semaphore."""
        semaphore = await self._get_wiki_semaphore()
        async with semaphore:
            try:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self._check_wikipedia_sync, question, answer)
            except Exception as e:
                logger.debug(f'Wiki parallel failed: {e}', exc_info=True)
                return {'verified': False, 'confidence': 0.0}

    def _check_wikipedia_sync(self, question: str, answer: str) -> dict:
        """Wikipedia verify sync (đã có trong V104.1, giữ nguyên)."""
        try:
            terms = re.findall('[\\wà-ỹ]+', question.lower())
            key_terms = [t for t in terms if len(t) > 3 and t not in ['của', 'là', 'gì', 'bao', 'nhiêu', 'khi', 'nào', 'ai', 'đâu', 'what', 'how', 'when', 'who', 'where', 'the', 'and', 'for']]
            if not key_terms:
                return {'verified': False, 'confidence': 0.0}
            search_term = ' '.join(key_terms[:3])
            params = urllib.parse.urlencode({'action': 'query', 'list': 'search', 'srsearch': search_term, 'format': 'json', 'srlimit': 1})
            url = f'https://vi.wikipedia.org/w/api.php?{params}'
            parsed_url = urllib.parse.urlparse(url)
            if parsed_url.scheme not in ('http', 'https'):
                raise ValueError(f'Unsupported URL scheme: {parsed_url.scheme!r}')
            req = urllib.request.Request(url, headers={'User-Agent': 'SCP-V104.2/1.0'})
            # [AUDIT-20260909 SSRF-S1] safe_urlopen thay urllib.request.urlopen
            # — host cố định vi.wikipedia.org, params đã urlencode; thêm lớp
            # validate scheme + chặn private IP.
            with safe_urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                search_results = data.get('query', {}).get('search', [])
                if not search_results:
                    return {'verified': False, 'confidence': 0.0}
                snippet = search_results[0].get('snippet', '').lower()
                answer_lower = answer.lower()
                answer_keywords = [w for w in answer_lower.split() if len(w) > 3]
                if not answer_keywords:
                    return {'verified': False, 'confidence': 0.0}
                matches = sum(1 for kw in answer_keywords if kw in snippet)
                match_ratio = matches / len(answer_keywords)
                if match_ratio >= 0.3:
                    return {'verified': True, 'confidence': 0.6 + match_ratio * 0.3}
                else:
                    return {'verified': False, 'confidence': 0.0}
        except Exception as e:
            logger.debug(f'Wikipedia verify failed: {e}', exc_info=True)
            return {'verified': False, 'confidence': 0.0}

    def _verify_learned_fact(self, entity: str, value: str, source: str) -> tuple[bool, str, float]:
        """Self-verify a learned fact before persisting to KB.

        Returns (is_valid, reason, confidence_adjustment).
        - is_valid=False → reject (don't store at all)
        - is_valid=True + confidence_adjustment<0 → store with downgraded confidence
        - is_valid=True + confidence_adjustment>=0 → store as-is

        Cross-check sources (in priority order):
          1. KB itself — does the entity already exist? Conflicting or matching value?
          2. Basic sanity — entity/value not empty, not spam, not absurd length
          3. Source sanity — source not from a blacklisted origin
        """
        try:
            if not entity or not isinstance(entity, str) or (not entity.strip()):
                return (False, 'empty entity (spam/junk)', -1.0)
            if not value or not isinstance(value, str) or len(value.strip()) < 2:
                return (False, 'empty/too-short value', -1.0)
            if len(value) > 2000:
                return (False, 'value too long (>2000 chars, likely junk)', -1.0)
            _stripped = value.strip().lower()
            if len(set(_stripped)) < 3:
                return (False, 'value too low entropy (spam/repeat)', -1.0)
            try:
                from scp.core.db_manager import db_query_one
                entity_lower = entity.lower()[:500]
                existing = db_query_one('SELECT value, confidence FROM knowledge WHERE entity = ? AND attribute = ? LIMIT 1', (entity_lower, 'verified_answer'), db_path=str(self.scp_db_path))
                if existing is not None:
                    existing_value = (existing.get('value') or '').strip().lower()
                    new_value = value.strip().lower()
                    if existing_value and existing_value == new_value:
                        return (True, 'cross-check OK (KB matches)', +0.05)
                    if existing_value and existing_value != new_value:
                        return (True, 'cross-check CONFLICT (KB has different value)', -0.4)
                return (True, 'no prior KB entry (unverified — no cross-check possible)', -0.3)
            except Exception as _kb_err:
                self._audit_v91('fast_learning_kb_crosscheck_error', {'entity': entity[:100], 'source': source, 'error': type(_kb_err).__name__})
                logger.error(f' KB cross-check failed; fact rejected: {_kb_err}', exc_info=True)
                return (False, 'KB cross-check infrastructure error', -1.0)
        except Exception as _verify_err:
            self._audit_v91('fast_learning_verify_error', {'entity': entity[:100], 'source': source, 'error': type(_verify_err).__name__})
            logger.error(f' Verification failed; fact rejected: {_verify_err}', exc_info=True)
            return (False, 'verification infrastructure error', -1.0)

    def _audit_v91(self, event: str, payload: dict) -> bool:
        try:
            import json as _json
            _entry = {'ts': time.time(), 'engine': 'fast_learning', 'event': event, 'payload': payload}
            _audit_path = self.data_dir / 'v91_upgrade_audit.jsonl'
            with open(_audit_path, 'a', encoding='utf-8') as f:
                f.write(_json.dumps(_entry, ensure_ascii=False) + '\n')
            return True
        except Exception as _audit_err:
            logger.error(f' audit log error: {_audit_err}', exc_info=True)
            return False

    def _store_kb(self, entity: str, attribute: str, value: str, source: str, confidence: float) -> bool:
        """Store fact into KB.

        [V104.24 #5 + V104.29 #4 FIX] Use db_exec from db_manager (was: separate
        sqlite3.connect calls bypassing _db_lock + case mismatch with Brain).
        Re-applied 3rd time after being lost in V104.24, V104.25, V104.29.

        [V104.46 #CF] TẠI SAO: FastLearning store didn't check SourceWatchlist →
        blocked sources could still write to KB. Fix: check watchlist before INSERT.

        [V9.0-WHY-GATE] WHY gates data learning — don't pollute KB without WHY approval.
        """
        try:
            from scp.meta.why_gate import get_why_gate
            _why = get_why_gate().gate(action_type='learning', action_desc=f'FastLearning store: entity={entity[:50]}, source={source}, conf={confidence}', context=f'value={value[:100]}')
            if not _why.allowed:
                logger.info(f'[V9.0-WHY-GATE] FastLearning KB store blocked by WHY for {entity[:30]}')
                return
        except Exception as _why_err:
            self._audit_v91('fast_learning_why_error', {'source': source, 'error': type(_why_err).__name__})
            logger.error(f'[V9.0-WHY-GATE] WHY Gate error; KB write blocked: {_why_err}', exc_info=True)
            return False
        try:
            try:
                from scp.knowledge.source_reputation import ReputationStore
                from scp.knowledge.source_watchlist import SourceWatchlist
                _watchlist = SourceWatchlist(store=ReputationStore())
                if _watchlist.is_blocked(source):
                    logger.warning(f'[V104.46 #CF] FastLearning KB write blocked by watchlist: source={source}')
                    return
            except Exception as _wl_err:
                self._audit_v91('fast_learning_watchlist_error', {'source': source, 'error': type(_wl_err).__name__})
                logger.error(f'[V104.46 #CF] Watchlist check error; KB write blocked: {_wl_err}', exc_info=True)
                return False
            try:
                _is_valid, _verify_reason, _conf_adj = self._verify_learned_fact(entity, value, source)
                if not _is_valid:
                    logger.info(f' FastLearning fact rejected by verify: entity={entity[:30]}, reason={_verify_reason}')
                    self._audit_v91('fast_learning_verify_reject', {'entity': entity[:100], 'source': source, 'reason': _verify_reason})
                    return
                if _conf_adj != 0.0:
                    confidence = max(0.0, min(1.0, confidence + _conf_adj))
                    if _conf_adj < 0:
                        confidence = min(confidence, 0.5)
                        logger.info(f' FastLearning fact downgraded to unverified (conf={confidence:.2f}): entity={entity[:30]}, reason={_verify_reason}')
                if not self._audit_v91('fast_learning_verify_ok', {'entity': entity[:100], 'source': source, 'conf_adj': _conf_adj, 'final_conf': confidence, 'reason': _verify_reason}):
                    return False
            except Exception as _verify_call_err:
                self._audit_v91('fast_learning_verify_error', {'entity': entity[:100], 'source': source, 'error': type(_verify_call_err).__name__})
                logger.error(f' Verification error; KB write blocked: {_verify_call_err}', exc_info=True)
                return False
            from scp.core.db_manager import db_exec
            entity_lower = entity.lower()[:500]
            _now = datetime.now().isoformat()
            db_exec("\n                INSERT INTO knowledge\n                (entity, attribute, value, value_type, confidence, source,\n                 timestamp, times_verified, last_verified)\n                VALUES (?, ?, ?, 'str', ?, ?, ?, 1, ?)\n                ON CONFLICT(entity, attribute) DO UPDATE SET\n                    value = excluded.value,\n                    confidence = excluded.confidence,\n                    source = excluded.source,\n                    timestamp = excluded.timestamp,\n                    last_verified = excluded.last_verified,\n                    times_verified = times_verified + 1\n            ", (entity_lower, attribute, value[:500], confidence, source, _now, _now), db_path=self.scp_db_path)
        except Exception as e:
            self._audit_v91('fast_learning_kb_write_fail', {'entity': entity[:100], 'source': source, 'error': type(e).__name__})
            logger.error(f'KB store failed; fact not persisted: {e}', exc_info=True)
            return False
        return True

    @ledger_run('fast')
    @telemetry_async_cycle
    async def fast_learning_cycle(self, count: int=50) -> dict:
        """
        V104.2 Fast learning cycle:
        - Sinh `count` câu hỏi từ ma trận 14×5
        - Skip những câu đã có trong KB
        - Hỏi Ollama PARALLEL (10 concurrent)
        - Verify Wikipedia PARALLEL (5 concurrent)
        - Store vào KB
        - Adaptive interval dựa trên verified ratio
        """
        cycle_start = time.time()
        results = {'asked': 0, 'skipped_known': 0, 'verified': 0, 'stored': 0, 'provider_failed': 0, 'provider_calls': 0, 'compounding_l2': 0, 'matrix_coverage': {'by_country': {}, 'by_domain': {}}, 'parallel_concurrency': PARALLEL_LLM_CONCURRENCY}  # noqa: F821  # [hygiene-keep] PARALLEL_LLM_CONCURRENCY injected by fast_learning_engine.py rebind/wire
        question_batch = []
        for _ in range(count):
            domain = _QUESTION_RNG.choice(DOMAINS)  # noqa: F821  # [hygiene-keep] DOMAINS injected by fast_learning_engine.py rebind/wire
            templates = SEED_QUESTIONS[domain]  # noqa: F821  # [hygiene-keep] SEED_QUESTIONS injected by fast_learning_engine.py rebind/wire
            country_templates = [t for t in templates if '{country}' in t]
            compound_templates = [t for t in templates if '{compound}' in t]
            generic_templates = [t for t in templates if '{country}' not in t and '{compound}' not in t]
            roll = _QUESTION_RNG.random()
            country_used = None
            if country_templates and roll < 0.7:
                template = _QUESTION_RNG.choice(country_templates)
                country = _QUESTION_RNG.choice(COUNTRIES)  # noqa: F821  # [hygiene-keep] COUNTRIES injected by fast_learning_engine.py rebind/wire
                question = template.format(country=country)
                country_used = country
            elif compound_templates and roll < 0.9:
                template = _QUESTION_RNG.choice(compound_templates)
                question = template.format(compound=_QUESTION_RNG.choice(COMPOUNDS))  # noqa: F821  # [hygiene-keep] COMPOUNDS injected by fast_learning_engine.py rebind/wire
            elif generic_templates:
                template = _QUESTION_RNG.choice(generic_templates)
                question = template
            elif country_templates:
                template = _QUESTION_RNG.choice(country_templates)
                country = _QUESTION_RNG.choice(COUNTRIES)  # noqa: F821  # [hygiene-keep] COUNTRIES injected by fast_learning_engine.py rebind/wire
                question = template.format(country=country)
                country_used = country
            else:
                template = _QUESTION_RNG.choice(compound_templates)
                question = template.format(compound=_QUESTION_RNG.choice(COMPOUNDS))  # noqa: F821  # [hygiene-keep] COMPOUNDS injected by fast_learning_engine.py rebind/wire
            hint = None
            if country_used and country_used in COUNTRY_DOMAIN_HINTS:  # noqa: F821  # [hygiene-keep] COUNTRY_DOMAIN_HINTS injected by fast_learning_engine.py rebind/wire
                hints_for_country = COUNTRY_DOMAIN_HINTS[country_used]  # noqa: F821  # [hygiene-keep] COUNTRY_DOMAIN_HINTS injected by fast_learning_engine.py rebind/wire
                if domain in hints_for_country:
                    hint = hints_for_country[domain]
            prompt = question
            if hint:
                prompt = f'{question}\n\n(Gợi ý: {hint})'
            question_batch.append({'question': question, 'prompt': prompt, 'country': country_used, 'domain': domain})
        if COMPOUNDING_ENABLED:  # noqa: F821  # [hygiene-keep] COMPOUNDING_ENABLED injected by fast_learning_engine.py rebind/wire
            compounding_qs = self._generate_compounding_questions(count=5)
            for q, country, domain in compounding_qs:
                question_batch.append({'question': q, 'prompt': q, 'country': country, 'domain': domain})
                results['compounding_l2'] += 1
                self._stats['compounding_l2_questions'] += 1
        if SKIP_KNOWN_QUESTIONS:  # noqa: F821  # [hygiene-keep] SKIP_KNOWN_QUESTIONS injected by fast_learning_engine.py rebind/wire
            new_batch = []
            for item in question_batch:
                if self._is_question_known(item['question']):
                    results['skipped_known'] += 1
                    self._stats['ollama_questions_skipped_known'] += 1
                else:
                    new_batch.append(item)
            question_batch = new_batch
        results['asked'] = len(question_batch)
        results['provider_calls'] = len(question_batch)
        self._stats['llm_questions_asked'] += len(question_batch)
        for item in question_batch:
            country = item['country']
            domain = item['domain']
            if country:
                results['matrix_coverage']['by_country'][country] = results['matrix_coverage']['by_country'].get(country, 0) + 1
                self._stats['by_country'][country] = self._stats['by_country'].get(country, 0) + 1
            results['matrix_coverage']['by_domain'][domain] = results['matrix_coverage']['by_domain'].get(domain, 0) + 1
            self._stats['by_domain'][domain] = self._stats['by_domain'].get(domain, 0) + 1
        ollama_tasks = [self._ask_llm_parallel(item['prompt']) for item in question_batch]
        llm_answers = await asyncio.gather(*ollama_tasks, return_exceptions=True)
        verify_tasks = []
        verify_items = []
        for item, answer in zip(question_batch, llm_answers):
            if isinstance(answer, Exception) or not answer or len(answer) < 3:
                results['provider_failed'] += 1
                continue
            verify_tasks.append(self._check_wikipedia_parallel(item['question'], answer))
            verify_items.append((item, answer))
        wiki_results = await asyncio.gather(*verify_tasks, return_exceptions=True)
        for (item, answer), wiki in zip(verify_items, wiki_results):
            if isinstance(wiki, Exception):
                wiki = {'verified': False, 'confidence': 0.0}
            if wiki.get('verified'):
                self._stats['llm_answers_verified'] += 1
                results['verified'] += 1
                stored_ok = self._store_kb(entity=item['question'][:200], attribute='verified_answer', value=answer[:500], source='llm-gateway+wiki', confidence=wiki['confidence'])
                if stored_ok:
                    self._stats['llm_kb_facts_stored'] += 1
                    results['stored'] += 1
        cycle_time_ms = int((time.time() - cycle_start) * 1000)
        # [STEP0-FIX 2026-09-02] Keep raw cycle times (bounded window) so the
        # benchmark route can report MEASURED p50/p95 instead of a
        # constant-model estimate (Bước 0.12: ESTIMATE != BENCHMARK).
        self._cycle_times_ms = (getattr(self, '_cycle_times_ms', []) + [cycle_time_ms])[-100:]
        self._stats['cycles_completed'] += 1
        self._stats['avg_cycle_time_ms'] = (self._stats['avg_cycle_time_ms'] * (self._stats['cycles_completed'] - 1) + cycle_time_ms) / self._stats['cycles_completed']
        self._stats['fastest_cycle_ms'] = min(self._stats['fastest_cycle_ms'], cycle_time_ms)
        self._stats['slowest_cycle_ms'] = max(self._stats['slowest_cycle_ms'], cycle_time_ms)
        if results['asked'] > 0:
            stored_ratio = results['stored'] / results['asked']
        else:
            stored_ratio = 0
        if stored_ratio > 0.5:
            new_interval = LEARN_INTERVAL_BURST  # noqa: F821  # [hygiene-keep] LEARN_INTERVAL_BURST injected by fast_learning_engine.py rebind/wire
            mode = 'BURST'
        elif stored_ratio < 0.1:
            new_interval = LEARN_INTERVAL_IDLE  # noqa: F821  # [hygiene-keep] LEARN_INTERVAL_IDLE injected by fast_learning_engine.py rebind/wire
            mode = 'IDLE'
        else:
            new_interval = LEARN_INTERVAL_FAST  # noqa: F821  # [hygiene-keep] LEARN_INTERVAL_FAST injected by fast_learning_engine.py rebind/wire
            mode = 'FAST'
        self._stats['adaptive_interval_current'] = new_interval
        results['cycle_time_ms'] = cycle_time_ms
        results['adaptive_mode'] = mode
        results['adaptive_interval_s'] = new_interval
        results['stored_ratio'] = round(stored_ratio, 3)
        logger.info(f"V104.2 FastLearning: asked={results['asked']}, skipped={results['skipped_known']}, verified={results['verified']}, stored={results['stored']}, compounding_L2={results['compounding_l2']}, time={cycle_time_ms}ms, mode={mode}")
        return results

    def get_adaptive_interval(self) -> int:
        return self._stats.get('adaptive_interval_current', LEARN_INTERVAL_FAST)  # noqa: F821  # [hygiene-keep] LEARN_INTERVAL_FAST injected by fast_learning_engine.py rebind/wire

    def stats(self) -> dict:
        payload = self._stats.copy()
        # [STEP0-FIX 2026-09-02] MEASURED distribution of real cycle times
        # (bounded window of 100) for honest p50/p95 reporting.
        times = sorted(getattr(self, '_cycle_times_ms', []) or [])
        payload['cycle_times_n'] = len(times)
        if times:
            def _pct(p: float) -> int:
                idx = min(len(times) - 1, max(0, round(p * (len(times) - 1))))
                return int(times[idx])
            payload['p50_cycle_ms'] = _pct(0.50)
            payload['p95_cycle_ms'] = _pct(0.95)
        else:
            payload['p50_cycle_ms'] = None
            payload['p95_cycle_ms'] = None
        return payload

    async def ollama_learning_cycle(self, count: int=10) -> dict:
        """
        [G3-MERGE PORTED] V104.1: Sinh câu hỏi theo ma trận 14 quốc gia × 5
        lĩnh vực → hỏi Ollama → verify bằng Wikipedia → lưu KB (SEQUENTIAL).

        Mặc định count=10: random pick từ 70+ combinations.
        count=70 → cover đầy đủ 1 vòng ma trận.
        """
        results = {'asked': 0, 'verified': 0, 'stored': 0, 'matrix_coverage': {'by_country': {}, 'by_domain': {}}}
        for _ in range(count):
            domain = _QUESTION_RNG.choice(DOMAINS)  # noqa: F821  # [hygiene-keep] DOMAINS injected by fast_learning_engine.py rebind/wire
            templates = SEED_QUESTIONS[domain]  # noqa: F821  # [hygiene-keep] SEED_QUESTIONS injected by fast_learning_engine.py rebind/wire
            country_templates = [t for t in templates if '{country}' in t]
            compound_templates = [t for t in templates if '{compound}' in t]
            generic_templates = [t for t in templates if '{country}' not in t and '{compound}' not in t]
            roll = _QUESTION_RNG.random()
            country_used = None
            if country_templates and roll < 0.7:
                template = _QUESTION_RNG.choice(country_templates)
                country = _QUESTION_RNG.choice(COUNTRIES)  # noqa: F821  # [hygiene-keep] COUNTRIES injected by fast_learning_engine.py rebind/wire
                question = template.format(country=country)
                country_used = country
                results['matrix_coverage']['by_country'][country] = results['matrix_coverage']['by_country'].get(country, 0) + 1
            elif compound_templates and roll < 0.9:
                template = _QUESTION_RNG.choice(compound_templates)
                question = template.format(compound=_QUESTION_RNG.choice(COMPOUNDS))  # noqa: F821  # [hygiene-keep] COMPOUNDS injected by fast_learning_engine.py rebind/wire
            elif generic_templates:
                template = _QUESTION_RNG.choice(generic_templates)
                question = template
            elif country_templates:
                template = _QUESTION_RNG.choice(country_templates)
                country = _QUESTION_RNG.choice(COUNTRIES)  # noqa: F821  # [hygiene-keep] COUNTRIES injected by fast_learning_engine.py rebind/wire
                question = template.format(country=country)
                country_used = country
                results['matrix_coverage']['by_country'][country] = results['matrix_coverage']['by_country'].get(country, 0) + 1
            else:
                template = _QUESTION_RNG.choice(compound_templates)
                question = template.format(compound=_QUESTION_RNG.choice(COMPOUNDS))  # noqa: F821  # [hygiene-keep] COMPOUNDS injected by fast_learning_engine.py rebind/wire
            results['matrix_coverage']['by_domain'][domain] = results['matrix_coverage']['by_domain'].get(domain, 0) + 1
            hint = None
            if country_used and country_used in COUNTRY_DOMAIN_HINTS:  # noqa: F821  # [hygiene-keep] COUNTRY_DOMAIN_HINTS injected by fast_learning_engine.py rebind/wire
                hints_for_country = COUNTRY_DOMAIN_HINTS[country_used]  # noqa: F821  # [hygiene-keep] COUNTRY_DOMAIN_HINTS injected by fast_learning_engine.py rebind/wire
                if domain in hints_for_country:
                    hint = hints_for_country[domain]
            if hint:
                prompt_for_ollama = f'{question}\n\n(Gợi ý: {hint})'
            else:
                prompt_for_ollama = question
            self._stats['llm_questions_asked'] += 1
            results['asked'] += 1
            llm_answer = await self._ask_llm(prompt_for_ollama)
            if not llm_answer or len(llm_answer) < 3:
                continue
            wiki_answer = self._check_wikipedia(question, llm_answer)
            if wiki_answer['verified']:
                self._stats['llm_answers_verified'] += 1
                results['verified'] += 1
                stored_ok = self._store_kb(entity=question[:200], attribute='verified_answer', value=llm_answer[:500], source='llm-gateway+wiki', confidence=wiki_answer['confidence'])
                if stored_ok:
                    self._stats['llm_kb_facts_stored'] += 1
                    results['stored'] += 1
                    self._stats['by_domain'][domain] = self._stats['by_domain'].get(domain, 0) + 1
                logger.info(f"Ollama Learning: VERIFIED '{question[:50]}' → '{llm_answer[:50]}'")
            else:
                logger.debug(f"Ollama Learning: NOT VERIFIED '{question[:50]}' → '{llm_answer[:50]}'")
        logger.info(f"Ollama Learning cycle: asked={results['asked']}, verified={results['verified']}, stored={results['stored']}")
        return results

    async def _ask_llm(self, question: str) -> str:
        """[G3-MERGE PORTED] V104.1 async LLM call — uses task="learning"
        (routes to qwen2.5:7b — better summarization + multilingual for
        Vietnamese learning questions).

        Distinct from _ask_llm_sync which uses task="fast_learning"
        (llama3.2 — speed-prioritized for parallel batch calls).
        """
        try:
            from scp.llm_gateway import get_gateway
            gw = get_gateway()
            answer, provider = await gw.chat(question, system_prompt='Trả lời ngắn gọn bằng tiếng Việt.', task='learning')
            return answer or ''
        except Exception as e:
            logger.debug(f'LLM Gateway async call failed: {e}', exc_info=True)
            return ''

    def _check_wikipedia(self, question: str, answer: str) -> dict:
        """[G3-MERGE PORTED] V104.1 sync Wikipedia verify.

        Body is identical to _check_wikipedia_sync (kept separate for backward
        compat — V104.1 API surface calls _check_wikipedia, V104.2 calls
        _check_wikipedia_sync).
        """
        return self._check_wikipedia_sync(question, answer)

    async def local_learning_cycle(self) -> dict:
        """[G3-MERGE PORTED] Scan data/ files → extract facts → verify bằng
        Ollama → lưu KB."""
        results = {'files_scanned': 0, 'facts_verified': 0, 'stored': 0}
        for filepath in self.data_dir.rglob('*'):
            if filepath.suffix not in ['.txt', '.jsonl']:
                continue
            if filepath.name == 'crawled_attacks.jsonl':
                continue
            self._stats['local_files_scanned'] += 1
            results['files_scanned'] += 1
            try:
                content = filepath.read_text(encoding='utf-8', errors='replace')
                sentences = self._extract_facts(content)
                for sentence in sentences[:20]:
                    llm_check = await self._ask_llm(f"Câu sau có đúng không? Trả lời 'ĐÚNG' hoặc 'SAI': {sentence}")
                    if llm_check and 'đúng' in llm_check.lower()[:10]:
                        self._stats['local_facts_verified'] += 1
                        results['facts_verified'] += 1
                        stored_ok = self._store_kb(entity=sentence[:200], attribute='local_fact', value='verified_true', source=f'local+ollama:{filepath.name}', confidence=0.7)
                        if stored_ok:
                            self._stats['local_kb_facts_stored'] += 1
                            results['stored'] += 1
            except Exception as e:
                logger.debug(f'Local file {filepath.name} failed: {e}', exc_info=True)
        logger.info(f"Local Learning: files={results['files_scanned']}, verified={results['facts_verified']}, stored={results['stored']}")
        return results

    def _extract_facts(self, text: str) -> list[str]:
        """[G3-MERGE PORTED] Extract sentences that look like facts (contain numbers)."""
        facts = []
        for sentence in text.split('\n'):
            sentence = sentence.strip()
            if 20 < len(sentence) < 500 and re.search('\\d+', sentence):
                facts.append(sentence)
        return facts

    async def news_learning_cycle(self) -> dict:
        """[G3-MERGE PORTED] Fetch news headlines → sinh câu hỏi → verify → lưu KB."""
        results = {'headlines': 0, 'questions': 0, 'stored': 0, 'quarantined': 0}
        # [STEP0-FIX 2026-09-02] Semantic firewall boundary (Bước 0.10): RSS
        # headlines are external content and must pass the same deterministic
        # injection scan as every other ingress (top_systems_learning,
        # knowledge_curation). Injected headlines are DROPPED - never turned
        # into questions, LLM checks, or KB facts.
        from scp.core.top_systems_learning import inspect_untrusted
        for rss_url in NEWS_SOURCES:  # noqa: F821  # [hygiene-keep] NEWS_SOURCES injected by fast_learning_engine.py rebind/wire
            try:
                headlines = self._fetch_rss_headlines(rss_url)
                for headline in headlines[:5]:
                    injected, reason = inspect_untrusted(headline)
                    if injected:
                        self._stats['news_headlines_quarantined'] += 1
                        results['quarantined'] += 1
                        logger.warning(f"[FIREWALL] RSS headline quarantined ({reason}): {headline[:80]!r}")
                        continue
                    self._stats['news_headlines_fetched'] += 1
                    results['headlines'] += 1
                    llm_check = await self._ask_llm(f"Sự kiện sau có thật không? Trả lời 'ĐÚNG' hoặc 'SAI': {headline}")
                    if llm_check and 'đúng' in llm_check.lower()[:10]:
                        self._stats['news_questions_generated'] += 1
                        results['questions'] += 1
                        stored_ok = self._store_kb(entity=headline[:200], attribute='news_fact', value='verified_true', source=f'news+ollama:{rss_url}', confidence=0.6)
                        if stored_ok:
                            self._stats['news_facts_stored'] += 1
                            results['stored'] += 1
            except Exception as e:
                logger.debug(f'News {rss_url} failed: {e}', exc_info=True)
        logger.info(f"News Learning: headlines={results['headlines']}, stored={results['stored']}")
        return results

    def _fetch_rss_headlines(self, rss_url: str) -> list[str]:
        """[G3-MERGE PORTED] Fetch RSS feed → extract headlines."""
        from defusedxml import ElementTree as DET
        headlines = []
        try:
            parsed = urllib.parse.urlparse(rss_url)
            if parsed.scheme not in ('http', 'https'):
                logger.debug(f'RSS URL scheme not allowed: {rss_url}')
                return []
            req = urllib.request.Request(rss_url, headers={'User-Agent': 'SCP-V104/1.0'})
            # [AUDIT-20260909 SSRF-S1] safe_urlopen thay urllib.request.urlopen
            # — rss_url từ NEWS_SOURCES (host cố định) nhưng vẫn validate
            # scheme + chặn private/loopback IP.
            with safe_urlopen(req, timeout=15) as resp:
                content = resp.read().decode('utf-8', errors='replace')
            root = DET.fromstring(content)
            items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
            for item in items[:10]:
                title = item.find('title')
                if title is not None and title.text:
                    headlines.append(title.text.strip())
        except Exception as e:
            logger.debug(f'RSS fetch failed: {e}', exc_info=True)
        return headlines

    async def run_all_cycles(self) -> dict:
        """[G3-MERGE PORTED] Run all 3 V104.1 learning loops sequentially.

        Used by /v104/learn/all endpoint (v104_routes.py:216).
        Distinct from fast_learning_cycle (V104.2 parallel).
        """
        logger.info('=== Real Learning Engine: Starting 3 cycles ===')
        ollama_result = await self.ollama_learning_cycle(count=10)
        local_result = await self.local_learning_cycle()
        news_result = await self.news_learning_cycle()
        total_stored = ollama_result['stored'] + local_result['stored'] + news_result['stored']
        logger.info(f'=== Real Learning Engine: {total_stored} facts stored ===')
        return {'ollama': ollama_result, 'local': local_result, 'news': news_result, 'total_stored': total_stored, 'stats': self._stats.copy()}
