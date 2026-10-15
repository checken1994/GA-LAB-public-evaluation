# SCP CIRCUIT: M12 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M12-closure.json)
# Auto-extracted from why_engine.py
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any

from scp.core.db_manager import db_exec, db_query_all, db_query_one, init_db
from scp.meta.why_engine_parts.init_why_db import init_why_db

# [M12-FIX PF-8] NOTE on VerificationPlan: it is DEFINED in
# scp/meta/why_engine.py, which injects it into this module via importlib
# AFTER importing it (`_impl.VerificationPlan = VerificationPlan`). Callers
# that import THIS module directly (e.g. api_server_parts.helpers.get_judge:
# `from scp.meta.why_engine_parts.whyengine import WhyEngine`) never triggered
# that injection -> create_verification_plan / execute_pending_plans raised
# `NameError: name 'VerificationPlan' is not defined` at RUNTIME and
# execute_pending_plans silently released every claimed row (executed: 0,
# claimed_by reset to NULL) — reproduced live in the pinned container.
# A module-level `from scp.meta.why_engine import VerificationPlan` here is
# NOT safe (reproduced circular AttributeError: parent's importlib wiring runs
# while this module is still partially initialized in the direct-import order),
# so both construction sites resolve the class lazily at call time, when both
# modules are fully importable in either order.
from scp.meta.why_sources.crypto import query_crypto as _why_query_crypto
from scp.meta.why_sources.frankfurter import query_frankfurter as _why_query_frankfurter
from scp.meta.why_sources.nasa import query_nasa as _why_query_nasa
from scp.meta.why_sources.open_meteo import query_open_meteo as _why_query_open_meteo
from scp.meta.why_sources.pubchem import query_pubchem as _why_query_pubchem
from scp.meta.why_sources.rest_countries import query_rest_countries as _why_query_rest_countries
from scp.meta.why_sources.wikidata import query_wikidata as _why_query_wikidata
from scp.meta.why_sources.wikipedia import query_wikipedia as _why_query_wikipedia

# [M12-FIX PF-2] logger was USED throughout this module (_save_plan except,
# _query_source except, execute_pending_plans warnings, LLM classifier paths)
# but NEVER defined -> every error/debug path raised NameError INSIDE an
# except handler, masking the original failure (fail-silently -> crash).
logger = logging.getLogger("scp.meta.why_engine")

class WhyEngine:
    """
    WHY Engine — biến câu hỏi Neo thành VerificationPlan.

    4 bước:
        1. target_identification — phân tích câu hỏi, xác định đối tượng
        2. evidence_type_selection — chọn loại bằng chứng phù hợp
        3. proof_criteria_definition — định nghĩa điều kiện chứng minh
        4. falsification_criteria_definition — định nghĩa điều kiện bác bỏ
    """
    TARGET_PATTERNS = {'math_expression': {'regex': '(?:tính|calculate|compute)\\s+(.+)|(\\d+\\s*[+\\-*/^%]+\\s*\\d+)|(\\d+\\s*!)|sqrt\\(|gcd\\(', 'type': 'value', 'evidence': 'deterministic_calculation', 'answer_type': 'numeric'}, 'physical_constant': {'regex': '(?:tốc độ ánh sáng|hằng số planck|số avogadro|gia tốc trọng trường|nhiệt độ sôi|nhiệt độ đóng băng|khối lượng trái đất|hằng số hấp dẫn)', 'type': 'entity', 'evidence': 'codata_constants', 'answer_type': 'numeric'}, 'molecular_weight': {'regex': '(?:khối lượng phân tử|molecular weight|molar mass)\\s+(.+)', 'type': 'entity', 'evidence': 'chemical_database', 'answer_type': 'numeric'}, 'weather_temperature': {'regex': '(?:nhiệt độ|temperature).*(?:tại|ở|at|in)\\s+(.+)', 'type': 'value', 'evidence': 'real_time_weather_api', 'answer_type': 'numeric'}, 'crypto_price': {'regex': '(?:giá|price of)\\s+(bitcoin|ethereum|solana|dogecoin|ripple|tether|monero|litecoin|cardano)', 'type': 'value', 'evidence': 'real_time_market_data', 'answer_type': 'numeric'}, 'currency_rate': {'regex': '(?:chuyển đổi|convert)\\s+\\d+\\s+([A-Z]{3})\\s+sang\\s+([A-Z]{3})', 'type': 'value', 'evidence': 'central_bank_rates', 'answer_type': 'numeric'}, 'geography_capital': {'regex': '(?:thủ đô|capital)\\s+(?:of\\s+|của\\s+)?(.+?)(?:\\s+là|\\?|$)', 'type': 'entity', 'evidence': 'geographic_database', 'answer_type': 'string'}, 'history_event': {'regex': '(?:sự kiện|event|năm\\s+\\d{4})', 'type': 'event', 'evidence': 'historical_records', 'answer_type': 'string'}, 'history_person': {'regex': '(?:ai là|who is|who was)\\s+(.+)', 'type': 'entity', 'evidence': 'biographical_records', 'answer_type': 'string'}, 'biology_constant': {'regex': '(?:nhiễm sắc thể|chromosome|nhiệt độ cơ thể|body temperature|nhịp tim|heart rate)', 'type': 'entity', 'evidence': 'biological_database', 'answer_type': 'numeric'}, 'logic_comparison': {'regex': '\\d+\\s*[<>=!]+\\s*\\d+', 'type': 'value', 'evidence': 'deterministic_evaluation', 'answer_type': 'boolean'}, 'statistics_aggregate': {'regex': '(?:trung bình|mean|median|phương sai|variance|min|max)', 'type': 'value', 'evidence': 'deterministic_calculation', 'answer_type': 'numeric'}}
    EVIDENCE_STRATEGIES = {'deterministic_calculation': {'sources': ['PythonAST', 'PythonMath'], 'proof': 'AST evaluator returns consistent result', 'falsification': 'Different evaluator returns different result', 'strategy': 'deterministic_ast', 'confidence_threshold': 0.95}, 'codata_constants': {'sources': ['CODATA table', 'Wikipedia (cross-check)'], 'proof': 'Value matches CODATA reference within 0.01%', 'falsification': 'Value differs from CODATA by >1%', 'strategy': 'constant_lookup', 'confidence_threshold': 0.95}, 'chemical_database': {'sources': ['PubChem', 'Wikidata'], 'proof': '≥2 sources agree within 0.1%', 'falsification': 'Sources disagree by >5%', 'strategy': 'multi_source_weighted_avg', 'confidence_threshold': 0.9}, 'real_time_weather_api': {'sources': ['Open-Meteo', 'Open-Meteo Archive'], 'proof': '≥2 sources agree within 3°C', 'falsification': 'Sources disagree by >10°C', 'strategy': 'multi_source_median', 'confidence_threshold': 0.85}, 'real_time_market_data': {'sources': ['Binance', 'Coinbase', 'Kraken', 'Bitstamp', 'KuCoin'], 'proof': '≥3 exchanges agree within 2%', 'falsification': 'Any exchange reports price differing >10%', 'strategy': 'multi_source_median', 'confidence_threshold': 0.9}, 'central_bank_rates': {'sources': ['Frankfurter', 'open.er-api.com'], 'proof': '≥2 sources agree within 1%', 'falsification': 'Sources disagree by >5%', 'strategy': 'multi_source_weighted_avg', 'confidence_threshold': 0.9}, 'geographic_database': {'sources': ['REST Countries API', 'LocalDB', 'Wikipedia'], 'proof': '≥2 sources return same capital', 'falsification': 'Sources return different capitals', 'strategy': 'majority_vote', 'confidence_threshold': 0.85}, 'historical_records': {'sources': ['LocalDB', 'Wikipedia'], 'proof': 'Wikipedia extract contains event keywords', 'falsification': 'Wikipedia returns not_found or mismatch', 'strategy': 'string_match', 'confidence_threshold': 0.7}, 'biographical_records': {'sources': ['LocalDB', 'Wikipedia'], 'proof': 'Wikipedia extract contains person keywords', 'falsification': 'Wikipedia returns not_found', 'strategy': 'string_match', 'confidence_threshold': 0.7}, 'biological_database': {'sources': ['InternalKB'], 'proof': 'Value matches internal knowledge base', 'falsification': 'Value differs from KB', 'strategy': 'kb_lookup', 'confidence_threshold': 0.85}, 'deterministic_evaluation': {'sources': ['PythonAST'], 'proof': 'AST evaluator returns boolean result', 'falsification': 'Evaluator returns different boolean', 'strategy': 'deterministic_ast', 'confidence_threshold': 0.95}}

    def __init__(self):
        init_db()
        init_why_db()
        import threading as _threading
        self._execute_pending_lock = _threading.Lock()

    def identify_target(self, question: str) -> tuple[str, str, str]:
        """
        Step 1: Xác định đối tượng câu hỏi đang hỏi về.

        Returns:
            (target, target_type, evidence_type)
        """
        q_lower = question.lower()
        for _pattern_name, pattern_info in self.TARGET_PATTERNS.items():
            m = re.search(pattern_info['regex'], q_lower, re.IGNORECASE)
            if m:
                target = question.strip()
                if m.groups():
                    for g in m.groups():
                        if g:
                            target = g.strip().rstrip('?').rstrip('.').strip()
                            break
                return (target, pattern_info['type'], pattern_info['evidence'])
        return (question[:50], 'unknown', 'wikipedia_search')

    def _classify_question_with_llm(self, question: str):
        """[V5.7-WHY] LLM-based question classification (opt-in, regex fallback).

        [ROOT-FIX 44-A] Now routes through gateway.chat_sync(task="why")
        → qwen2.5:7b (multilingual + factual). Previously called
        _call_openrouter directly (bypassed Ollama entirely even when
        Ollama was the user's preferred local provider).
        """
        try:
            from scp.llm_gateway import chat_sync
        except Exception as e:
            logger.debug(f'[V5.7-WHY] LLM gateway import failed: {e}', exc_info=True)
            return None
        valid_evidence_types = list(self.EVIDENCE_STRATEGIES.keys()) + ['wikipedia_search']
        valid_target_types = ('entity', 'value', 'relationship', 'event')
        valid_answer_types = ('numeric', 'string', 'boolean', 'temporal')
        prompt = f'Classify this question for fact-verification. Output ONLY a JSON object (no markdown fences, no explanation).\n\nQuestion: {question}\n\nReturn JSON with these fields:\n- "target": the entity/value the question asks about (short, <60 chars)\n- "target_type": one of {list(valid_target_types)!r}\n- "evidence_type": one of {valid_evidence_types!r}\n- "answer_type": one of {list(valid_answer_types)!r}\n\nExample for "Tại sao giá bitcoin hiện tại là $62000?":\n{{"target": "bitcoin_price_usd", "target_type": "value", "evidence_type": "real_time_market_data", "answer_type": "numeric"}}\n\nOutput ONLY the JSON object.'
        try:
            response, _provider = chat_sync(prompt, task='why')
            if not response:
                return None
            json_match = re.search('\\{[^{}]*\\}', response, re.DOTALL)
            if not json_match:
                logger.debug(f'[V5.7-WHY] LLM response has no JSON: {response[:200]}')
                return None
            parsed = json.loads(json_match.group(0))
            target = str(parsed.get('target', '')).strip()[:60]
            target_type = str(parsed.get('target_type', '')).strip().lower()
            evidence_type = str(parsed.get('evidence_type', '')).strip().lower()
            answer_type = str(parsed.get('answer_type', '')).strip().lower()
            if not target or not evidence_type:
                logger.debug('[V5.7-WHY] LLM returned incomplete classification')
                return None
            if target_type not in valid_target_types:
                target_type = 'entity'
            if evidence_type not in valid_evidence_types:
                logger.debug(f'[V5.7-WHY] LLM returned unknown evidence_type: {evidence_type!r} — falling back to regex')
                return None
            if answer_type not in valid_answer_types:
                answer_type = 'string'
            logger.info(f'[V5.7-WHY] LLM classified: target={target!r}, type={target_type}, evidence={evidence_type}, answer_type={answer_type}')
            return (target, target_type, evidence_type, answer_type)
        except Exception as e:
            logger.debug(f'[V5.7-WHY] LLM classification failed: {e}', exc_info=True)
            return None

    def select_evidence_type(self, evidence_type: str) -> dict[str, Any]:
        """
        Step 2: Chọn loại bằng chứng phù hợp.

        Returns:
            {sources, strategy, confidence_threshold}
        """
        return self.EVIDENCE_STRATEGIES.get(evidence_type, {'sources': ['Wikipedia'], 'proof': 'Wikipedia extract supports claim', 'falsification': 'Wikipedia contradicts claim', 'strategy': 'wikipedia_search', 'confidence_threshold': 0.6})

    def define_criteria(self, evidence_type: str, target: str, answer_type: str) -> tuple[str, str]:
        """
        Step 3+4: Định nghĩa proof + falsification criteria.

        Returns:
            (proof_criteria, falsification_criteria)
        """
        strategy = self.EVIDENCE_STRATEGIES.get(evidence_type, {})
        proof = strategy.get('proof', 'Source confirms claim')
        falsification = strategy.get('falsification', 'Source contradicts claim')
        if answer_type == 'numeric':
            proof = f'{proof} (within tolerance for {target})'
            falsification = f'{falsification} (exceeds tolerance for {target})'
        elif answer_type == 'string':
            proof = f'{proof} (string match for {target})'
            falsification = f'{falsification} (no match for {target})'
        elif answer_type == 'boolean':
            proof = f'{proof} (boolean evaluation for {target})'
            falsification = f'{falsification} (opposite boolean for {target})'
        return (proof, falsification)

    def create_verification_plan(self, question: str) -> VerificationPlan:  # noqa: F821  # [hygiene-keep] VerificationPlan injected by why_engine.py rebind/wire
        """
        WHY Engine entry point.

        Neo asks "Tại sao X?" → WHY Engine creates VerificationPlan.

        Args:
            question: Neo's question (vd "Tại sao giá bitcoin là $62000?")

        Returns:
            VerificationPlan with target, evidence, criteria
        """
        # [M12-FIX PF-8] lazy resolve — see the PF-8 note at module imports.
        from scp.meta.why_engine import VerificationPlan as _VerificationPlan
        clean_q = re.sub('^tại\\s+sao\\s+', '', question, flags=re.IGNORECASE).strip()
        clean_q = re.sub('^why\\s+', '', clean_q, flags=re.IGNORECASE).strip()
        _why_classifier_used = 'regex'
        _llm_was_attempted = False
        target = None
        target_type = None
        evidence_type = None
        answer_type = 'string'
        if os.environ.get('SCP_WHY_LLM_ENABLED', '0') == '1':
            _llm_was_attempted = True
            try:
                _llm_result = self._classify_question_with_llm(clean_q)
                if _llm_result is not None:
                    target, target_type, evidence_type, answer_type = _llm_result
                    _why_classifier_used = 'llm'
            except Exception as _llm_err:
                logger.debug(f'[V5.7-WHY] LLM classifier exception (falling back to regex): {_llm_err}', exc_info=True)
        if target is None or evidence_type is None:
            target, target_type, evidence_type = self.identify_target(clean_q)
            for _pattern_name, pattern_info in self.TARGET_PATTERNS.items():
                if re.search(pattern_info['regex'], clean_q.lower(), re.IGNORECASE):
                    answer_type = pattern_info['answer_type']
                    break
            if _llm_was_attempted and _why_classifier_used == 'regex':
                _why_classifier_used = 'llm_failed_regex_fallback'
        evidence_strategy = self.select_evidence_type(evidence_type)
        proof_criteria, falsification_criteria = self.define_criteria(evidence_type, target, answer_type)
        plan = _VerificationPlan(question=question, target=target, target_type=target_type, evidence_type=evidence_type, proof_criteria=proof_criteria, falsification_criteria=falsification_criteria, verification_strategy=evidence_strategy['strategy'], sources_to_query=evidence_strategy['sources'], expected_answer_type=answer_type, confidence_threshold=evidence_strategy['confidence_threshold'], reasoning=f"Target='{target}', type={target_type}, evidence={evidence_type}, strategy={evidence_strategy['strategy']}, classifier={_why_classifier_used} [V5.7-WHY]")
        self._save_plan(plan)
        return plan

    def _save_plan(self, plan: VerificationPlan) -> None:  # noqa: F821  # [hygiene-keep] VerificationPlan injected by why_engine.py rebind/wire
        """Save plan to DB.  Skip for deterministic — they don't need plans."""
        if plan.evidence_type in ('deterministic_calculation', 'deterministic_evaluation', 'codata_constants', 'biological_database'):
            return
        try:
            ts = datetime.now().astimezone().isoformat()
            db_exec("\n                INSERT INTO why_verification_plans\n                (timestamp, question, target, evidence_type, proof_criteria,\n                 falsification_criteria, verification_strategy, sources_to_query,\n                 status, verdict, executed_at, confidence_threshold)\n                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, NULL, ?)\n            ", (ts, plan.question, plan.target, plan.evidence_type, plan.proof_criteria, plan.falsification_criteria, plan.verification_strategy, json.dumps(plan.sources_to_query), plan.confidence_threshold))
        except Exception as e:
            logger.warning(f'WhyEngine save error: {e}', exc_info=True)

    def execute_plan(self, plan: VerificationPlan, ai_answer: str) -> dict[str, Any]:  # noqa: F821  # [hygiene-keep] VerificationPlan injected by why_engine.py rebind/wire
        """[Task 8-A] Delegate — implementation in scp.meta.why_execute_plan.

        See scp.meta.why_execute_plan.execute_plan for full docstring.
        Returns: {verdict, confidence, sources_queried, all_values, reasoning}
        """
        from scp.meta.why_execute_plan import execute_plan as _execute_plan_impl
        return _execute_plan_impl(self, plan, ai_answer)

    def _query_source(self, source_name: str, target: str, question: str) -> str | None:
        """Query a single source for the target value."""
        source_name_lower = source_name.lower().strip()
        try:
            if 'localdb' in source_name_lower or 'local db' in source_name_lower:
                return self._query_local_db(target, question)
            if 'wikipedia' in source_name_lower:
                return self._query_wikipedia(target, question)
            elif 'pubchem' in source_name_lower:
                return self._query_pubchem(target)
            elif 'wikidata' in source_name_lower:
                return self._query_wikidata(target, question)
            elif 'rest_countries' in source_name_lower or 'rest countries' in source_name_lower:
                return self._query_rest_countries(target)
            elif 'open-meteo' in source_name_lower or 'open_meteo' in source_name_lower:
                return self._query_open_meteo(target, question)
            elif any(x in source_name_lower for x in ['binance', 'coingecko', 'coinbase', 'kraken', 'bitstamp', 'kucoin']):
                return self._query_crypto(target)
            elif 'frankfurter' in source_name_lower or 'open.er-api.com' in source_name_lower or 'er-api' in source_name_lower:
                return self._query_frankfurter(target, question)
            elif 'nasa' in source_name_lower:
                return self._query_nasa(target)
            else:
                logger.debug(f"WHY: unknown source '{source_name}'")
                return None
        except Exception as e:
            logger.debug(f"WHY query_source '{source_name}' error: {e}", exc_info=True)
            return None

    def _query_local_db(self, target: str, question: str) -> str | None:
        """[FIX #21] Query SCP's local DB (GeographySLM cache) for capital/population/area.

        TẠI SAO: LocalDB is the trusted cache populated by previous successful API
        calls. It has capitals for 50+ countries. When REST Countries API is
        deprecated (Bug #16/#22), LocalDB is the authoritative fallback.
        """
        try:
            # [S26 2026-09-13] GeographySLM (cây cũ slms.py/slm_impls, đã xóa)
            # → Geography (cây mới scp/runtime/experts/ — cùng `_local` cache
            # 231 keys, WHY-GATE hermetic so cũ/mới: 6/6 case MATCH).
            from scp.runtime.experts.humanities import Geography
            if not hasattr(self, '_geo_slm_for_queries'):
                self._geo_slm_for_queries = Geography()
            geo = self._geo_slm_for_queries
            target_lower = target.lower().strip()
            if target_lower in geo._local:
                data = geo._local[target_lower]
                q_lower = question.lower()
                if 'capital' in q_lower:
                    return data.get('capital', '')
                elif 'population' in q_lower:
                    return str(data.get('population', ''))
                elif 'area' in q_lower:
                    return str(data.get('area', ''))
                else:
                    return data.get('capital', '')
            from scp.data_sources._matching import _token_boundary_match
            for key, data in geo._local.items():
                if _token_boundary_match(key, target_lower):
                    q_lower = question.lower()
                    if 'capital' in q_lower:
                        return data.get('capital', '')
                    elif 'population' in q_lower:
                        return str(data.get('population', ''))
                    elif 'area' in q_lower:
                        return str(data.get('area', ''))
                    else:
                        return data.get('capital', '')
            return None
        except Exception as e:
            logger.debug(f'WHY LocalDB query error: {e}', exc_info=True)
            return None

    def _query_wikipedia(self, target: str, question: str) -> str | None:
        """[Task 7-A] Delegates to meta.why_sources.wikipedia for modularity.

        Original 63 LOC body extracted to standalone function — same behavior.
        """
        return _why_query_wikipedia(target, question)

    def _query_pubchem(self, target: str) -> str | None:
        """[Task 7-A] Delegates to meta.why_sources.pubchem for modularity.

        Original 15 LOC body extracted to standalone function — same behavior.
        """
        return _why_query_pubchem(target)

    def _query_wikidata(self, target: str, question: str) -> str | None:
        """[Task 9-B] Delegates to meta.why_sources.wikidata for modularity."""
        return _why_query_wikidata(target, question)

    def _query_rest_countries(self, target: str) -> str | None:
        """[Task 9-B] Delegates to meta.why_sources.rest_countries for modularity."""
        return _why_query_rest_countries(target)

    def _query_open_meteo(self, target: str, question: str) -> str | None:
        """[Task 9-B] Delegates to meta.why_sources.open_meteo for modularity."""
        return _why_query_open_meteo(target, question)

    def _query_crypto(self, target: str) -> str | None:
        """[Task 7-A] Delegates to meta.why_sources.crypto for modularity.

        Original 15 LOC body extracted to standalone function — same behavior.
        """
        return _why_query_crypto(target)

    def _query_frankfurter(self, target: str, question: str) -> str | None:
        """[Task 9-B] Delegates to meta.why_sources.frankfurter for modularity."""
        return _why_query_frankfurter(target, question)

    def _query_nasa(self, target: str) -> str | None:
        """[Task 9-B] Delegates to meta.why_sources.nasa for modularity."""
        return _why_query_nasa(target)

    def execute_pending_plans(self, limit: int=10, worker_id: str | None=None) -> dict:
        """[WHY-FIX Bước 3] Execute pending plans from DB (background scheduler).

        [SCP-DNA-FIX R7-3] Atomic plan claiming via UPDATE ... RETURNING.
        TẠI SAO: Previously used `SELECT ... WHERE status='pending'` with no lock.
        Two concurrent threads could pick the same rows → double-execution →
        falsification data corrupted. Now uses atomic UPDATE ... WHERE
        claimed_by IS NULL RETURNING * — only the claiming thread receives
        the row. Reality evidence: hypothesis 8-thread concurrent test → 0 duplicates.

        [SCP-DNA-FIX R7-3+] Defense-in-depth: in-process threading.Lock around the
        atomic claim step. The UPDATE ... RETURNING already prevents cross-thread
        double-claim at the DB level, but two threads inside the SAME process can
        still race on the Python-side claim + execute boundary if a second caller
        arrives between the DB commit and the per-row processing. The lock
        serializes the in-process claim so concurrent calls (e.g. periodic
        scheduler + manual /admin trigger) cannot interleave. Cross-process
        safety still relies on the DB-level claimed_by column.

        Returns: {executed, passed, failed, conflicts, unknowns}
        """
        import uuid as _uuid
        _worker_id = worker_id or str(_uuid.uuid4())
        _now = time.time()
        with self._execute_pending_lock:
            try:
                pending = db_query_all("UPDATE why_verification_plans SET claimed_by = ?, claimed_at = ? WHERE id IN (  SELECT id FROM why_verification_plans   WHERE status = 'pending' AND claimed_by IS NULL   ORDER BY id LIMIT ?) RETURNING id, question, target, evidence_type, proof_criteria, falsification_criteria, verification_strategy, sources_to_query, confidence_threshold", (_worker_id, _now, limit))
            except Exception as e:
                logger.warning(f' Atomic claim failed (SQLite < 3.35?), fallback: {e}', exc_info=True)
                try:
                    pending = db_query_all("SELECT id, question, target, evidence_type, proof_criteria, falsification_criteria, verification_strategy, sources_to_query, confidence_threshold FROM why_verification_plans WHERE status='pending' AND claimed_by IS NULL ORDER BY id LIMIT ?", (limit,))
                    for row in pending:
                        db_exec('UPDATE why_verification_plans SET claimed_by=?, claimed_at=? WHERE id=?', (_worker_id, _now, row['id']))
                except Exception as e2:
                    logger.warning(f'WHY execute_pending: query failed: {e2}', exc_info=True)
                    return {'executed': 0, 'error': str(e2)}
        stats = {'executed': 0, 'passed': 0, 'failed': 0, 'conflicts': 0, 'unknowns': 0}
        # [M12-FIX PF-8] lazy resolve — see the PF-8 note at module imports.
        from scp.meta.why_engine import VerificationPlan as _VerificationPlan
        for row in pending:
            try:
                plan = _VerificationPlan(question=row['question'], target=row['target'], target_type='entity', evidence_type=row['evidence_type'], proof_criteria=row['proof_criteria'], falsification_criteria=row['falsification_criteria'], verification_strategy=row['verification_strategy'], sources_to_query=json.loads(row['sources_to_query']) if row['sources_to_query'] else [], expected_answer_type='string', confidence_threshold=row['confidence_threshold'] or 0.5, reasoning='', plan_id=row['id'])
                result = self.execute_plan(plan, ai_answer='')
                stats['executed'] += 1
                v = result.get('verdict', 'UNKNOWN')
                if v == 'PASS':
                    stats['passed'] += 1
                elif v == 'FAIL':
                    stats['failed'] += 1
                elif v == 'CONFLICT':
                    stats['conflicts'] += 1
                else:
                    stats['unknowns'] += 1
            except Exception as e:
                logger.debug(f"WHY execute_pending: row {row.get('id')}: {e}", exc_info=True)
                try:
                    db_exec('UPDATE why_verification_plans SET claimed_by=NULL, claimed_at=NULL WHERE id=?', (row['id'],))
                except Exception as release_exc:
                    # [M12-FIX D6] was bare `except Exception: pass` — a failed
                    # claim-release would leave the row claimed forever with no
                    # observable trace. Log the release failure (the row stays
                    # claimed and will NOT be retried until claimed_by cleared).
                    logger.warning(f'WHY execute_pending: claim-release failed for row {row.get("id")}: {release_exc}', exc_info=True)
        logger.info(f"WHY Engine: executed {stats['executed']} pending plans — PASS={stats['passed']}, FAIL={stats['failed']}, CONFLICT={stats['conflicts']}, UNKNOWN={stats['unknowns']}")
        return stats

    def run_pending_verification_cycle(self, limit: int=10) -> dict:
        """[SCP-DNA-FIX R5-3] Run one cycle of pending-plan verification.

        Idempotent + safe to call from a scheduler (wraps execute_pending_plans
        in a try/except that NEVER raises). Returns the stats dict from
        execute_pending_plans, or {"executed": 0, "error": "..."} on failure.

        Args:
            limit: max number of pending plans to execute this cycle (default 10).

        Returns:
            {"executed": int, "passed": int, "failed": int,
             "conflicts": int, "unknowns": int}  (+ optional "error": str)
        """
        try:
            return self.execute_pending_plans(limit=limit)
        except Exception as e:
            logger.warning(f'[SCP-DNA-FIX R5-3] run_pending_verification_cycle failed: {e}', exc_info=True)
            return {'executed': 0, 'error': str(e)}

    def get_stats(self) -> dict[str, Any]:
        """Stats cho WHY Engine."""
        try:
            total = db_query_one('SELECT COUNT(*) as cnt FROM why_verification_plans')['cnt']
            pending = db_query_one("SELECT COUNT(*) as cnt FROM why_verification_plans WHERE status = 'pending'")['cnt']
            executed = total - pending
            by_type_rows = db_query_all('SELECT evidence_type, COUNT(*) as cnt FROM why_verification_plans GROUP BY evidence_type')
            by_type = {r['evidence_type']: r['cnt'] for r in by_type_rows} if by_type_rows else {}
            return {'total_plans': total, 'pending': pending, 'executed': executed, 'by_evidence_type': by_type, 'target_patterns': len(self.TARGET_PATTERNS), 'evidence_strategies': len(self.EVIDENCE_STRATEGIES)}
        except Exception as e:
            logger.warning("WHY engine get_stats failed: %s", e, exc_info=True)
            return {'error': str(e)}

    def _v80_why_llm_call(self, prompt: str, max_tokens: int=600) -> str | None:
        """[V8.0-WHY] Helper: call LLM via gateway with task="why".

        [ROOT-FIX 44-A] Routes through gateway.chat_sync(task="why")
        → qwen2.5:7b (multilingual + factual accuracy). Previously
        called _call_openrouter directly (bypassed Ollama entirely).

        Returns None on any failure (import error, API key missing, HTTP error,
        timeout). WhyEngine callers fall back to defensive default dict.
        """
        try:
            from scp.llm_gateway import chat_sync
            response, _provider = chat_sync(prompt, task='why')
            return response
        except Exception as e:
            logger.debug(f'[V8.0-WHY] LLM call failed: {e}', exc_info=True)
            return None

    def _v80_why_extract_json(self, response: str) -> dict | None:
        """[V8.0-WHY] Helper: extract first JSON object from LLM response.

        LLM may wrap JSON in markdown fences, search-replace markers, or
        explanatory text — use regex to extract the outermost {...} block.
        Handles one level of nested braces (e.g. {"a": {"b": 1}}).

        Returns None on parse failure (caller falls back to default dict).
        """
        if not response:
            return None
        try:
            m = re.search('\\{[^{}]*(?:\\{[^{}]*\\}[^{}]*)*\\}', response, re.DOTALL)
            if not m:
                return None
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.debug(f'[V8.0-WHY] JSON parse failed: {e} — response: {response[:200]}')
            return None

    def _v80_normalize_cwe(self, cwe_id: str) -> str:
        """[V8.0-WHY] Helper: normalize CWE id to bare digits.

        Accepts "CWE-89", "cwe-89", "CWE89", "89" — all return "89".
        Falls back to "0" if no digits found.
        """
        if not cwe_id:
            return '0'
        m = re.search('(\\d+)', cwe_id)
        return m.group(1) if m else '0'

    def type_inference_why(self, var_name: str, expected_type: str, actual_type: str, context: str) -> dict:
        """[Task 9-B] Delegates to meta.why_v80_modes.type_inference_why for modularity.

        Original ~110 LOC body extracted to standalone function — same behavior.
        Takes engine (self) as first arg for _v80_why_llm_call access.
        """
        from scp.meta.why_v80_modes import type_inference_why as _v80_type_inference
        return _v80_type_inference(self, var_name, expected_type, actual_type, context)

    def data_flow_why(self, source: str, sink: str, path: list[str], context: str) -> dict:
        """[Task 9-B] Delegates to meta.why_v80_modes.data_flow_why for modularity.

        Original ~125 LOC body extracted to standalone function — same behavior.
        Takes engine (self) as first arg for _v80_why_llm_call access.
        """
        from scp.meta.why_v80_modes import data_flow_why as _v80_data_flow
        return _v80_data_flow(self, source, sink, path, context)

    def security_threat_why(self, code_pattern: str, cwe_id: str, context: str) -> dict:
        """[Task 9-B] Delegates to meta.why_v80_modes.security_threat_why for modularity.

        Original ~115 LOC body extracted to standalone function — same behavior.
        Takes engine (self) as first arg for _v80_why_llm_call access.
        """
        from scp.meta.why_v80_modes import security_threat_why as _v80_security_threat
        return _v80_security_threat(self, code_pattern, cwe_id, context)
