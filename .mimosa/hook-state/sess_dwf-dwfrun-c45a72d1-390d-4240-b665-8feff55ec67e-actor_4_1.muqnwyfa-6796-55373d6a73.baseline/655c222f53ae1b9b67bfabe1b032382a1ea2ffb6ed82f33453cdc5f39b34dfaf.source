"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.

WHY Engine, Recursive Why, MetaFalsifier, ProofGraph
License: See LICENSE file
"""

"""
 Cognitive Gate — Cognitive layers AFFECT VERDICT.

Trước V45: MetaFalsifier/CounterQuestion/ProofGraph chỉ display, không affect verdict
V45: Cognitive Gate downgrade verdict khi:
  - MetaFalsifier: plan thiếu ≥2 critical attack vectors → PASS → UNKNOWN
  - ProofGraph: overall_status = "broken" → PASS → UNKNOWN
  - CounterQuestion: phát hiện ambiguity → PASS → PARTIAL
  - RecursiveWhy: depth < 1 (chưa trace tới axiom) → PASS → PARTIAL

 Improvements:
  - RecursiveWhy returns "trusted_source" for PubChem/CODATA/etc → no more downgrade
  - Domain-specific CRITICAL_VECTORS for medical/legal/arts/sports/tech (V46 domains)
  - CognitiveGate logs every downgrade to DB (cognitive_gate_log table)
  - Auto false_downgrade_rate tracking (ReVerify feedback)
"""
import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("scp.cognitive_gate")

# Lazy import DB helpers
try:
    from scp.core.db_manager import db_exec, init_db
    _DB_AVAILABLE = True
except Exception as exc:
    # silent-by-design: db_manager import is optional at module load; the flag drives the fallback.
    logger.debug("cognitive_gate: db_manager unavailable: %s", exc, exc_info=True)
    _DB_AVAILABLE = False


# Critical attack vectors per evidence type — missing these = plan incomplete
CRITICAL_VECTORS = {
    "numeric_value": {"source_agreement", "tolerance_check"},
    "string_value": {"source_agreement", "exact_match"},
    "boolean_value": {"deterministic_check"},
    "entity_fact": {"source_agreement", "temporal_check"},
    "deterministic_calculation": set(),  # deterministic - no need
    "deterministic_evaluation": set(),
    "codata_constants": {"source_agreement"},
    "biological_database": {"source_agreement"},
    "live_api_data": {"source_agreement", "temporal_freshness"},
    #  V46 domain-specific critical vectors
    "medical_fact": {"medical_guideline_currency", "dosage_range_check"},
    "legal_fact": {"jurisdiction_check", "effective_date_check"},
    "art_attribution": {"attribution_consensus", "period_consistency"},
    "sports_record": {"official_record_check", "temporal_check"},
    "tech_fact": {"version_check", "authority_check"},
}


class CognitiveGate:
    """
    Cognitive Gate — quyết định có downgrade verdict hay không dựa trên
    output từ 5 cognitive layers.

    Input:
      - verdict: PASS / FAIL / CONFLICT / PARTIAL / UNKNOWN
      - confidence: 0-1
      - cognitive_result: dict from CognitiveEngine.analyze()
      - evidence_type: từ why_plan

    Output:
      - gated_verdict: verdict mới (có thể downgrade)
      - gate_reasons: list lý do downgrade
      - original_verdict: verdict gốc (lưu trữ)
    """

    def __init__(self):
        self.stats = {
            "total_evaluated": 0,
            "downgraded_to_unknown": 0,
            "downgraded_to_partial": 0,
            "unchanged": 0,
            "false_downgrades": 0,  #  downgrade bị ReVerify chứng minh sai
            "confirmed_downgrades": 0,  #  downgrade đúng (ReVerify vẫn FAIL)
        }
        self._init_db()

    def _init_db(self):
        """ Create cognitive_gate_log table for audit trail."""
        if not _DB_AVAILABLE:
            return
        try:
            init_db()
            db_exec("""
                CREATE TABLE IF NOT EXISTS cognitive_gate_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    question TEXT,
                    domain TEXT,
                    original_verdict TEXT,
                    gated_verdict TEXT,
                    reasons TEXT,
                    evidence_type TEXT,
                    reverify_outcome TEXT,
                    reverify_timestamp TEXT
                )
            """)
            db_exec("CREATE INDEX IF NOT EXISTS idx_cgl_ts ON cognitive_gate_log(timestamp)")
            db_exec("CREATE INDEX IF NOT EXISTS idx_cgl_gated ON cognitive_gate_log(gated_verdict)")
            # [V104.29 #6 FIX] Retention cap 5000 entries (was: unbounded growth)
            try:
                db_exec("DELETE FROM cognitive_gate_log WHERE id NOT IN (SELECT id FROM cognitive_gate_log ORDER BY id DESC LIMIT 5000)")
            except Exception as e:
                logger.debug(f"[V104.37] meta/cognitive_gate.py: e={e}", exc_info=True)
        except Exception as e:
            logger.debug(f"cognitive_gate_log init error: {e}", exc_info=True)

    def _log_downgrade(self, question: str, domain: str,
                       original: str, gated: str, reasons: list[str],
                       evidence_type: str = ""):
        """ Log downgrade to DB for audit + false_downgrade_rate tracking."""
        if not _DB_AVAILABLE:
            return
        try:
            ts = datetime.now().astimezone().isoformat()
            db_exec(
                "INSERT INTO cognitive_gate_log "
                "(timestamp, question, domain, original_verdict, gated_verdict, reasons, evidence_type) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ts, question[:500], domain, original, gated,
                 json.dumps(reasons, ensure_ascii=False), evidence_type)
            )
            logger.info(f"[CognitiveGate V50] {original} -> {gated} | domain={domain} | reasons={reasons}")
        except Exception as e:
            logger.debug(f"CognitiveGate log error: {e}", exc_info=True)

    def _log_evaluated(self, question: str, domain: str,
                       original: str, gated: str, reasons: list[str],
                       evidence_type: str = ""):
        """ Log EVERY evaluation (not just downgrades) for audit."""
        if not _DB_AVAILABLE:
            return
        try:
            ts = datetime.now().astimezone().isoformat()
            db_exec(
                "INSERT INTO cognitive_gate_log "
                "(timestamp, question, domain, original_verdict, gated_verdict, reasons, evidence_type) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ts, question[:500], domain, original, gated,
                 json.dumps(reasons, ensure_ascii=False) if reasons else "[]", evidence_type)
            )
        except Exception as e:
            logger.debug(f"CognitiveGate log error: {e}", exc_info=True)

    def record_reverify_outcome(self, question: str, reverify_verdict: str):
        """
         Called by ReVerifyScheduler when a downgraded verdict is re-verified.

        If reverify_verdict == PASS → previous downgrade was FALSE → increment false_downgrades.
        If reverify_verdict in (FAIL, UNKNOWN) → downgrade was correct → increment confirmed.
        """
        if not _DB_AVAILABLE:
            return
        try:
            #  TẠI SAO: the old query used `WHERE question LIKE ?` with
            # parameter `question[:100]` (no wildcards). In SQLite, `LIKE` without
            # `%`/`_` wildcards behaves as an EXACT match on the full column value.
            # But the stored question could be >100 chars (if logged in full) OR
            # truncated to 100 chars at insert time — either way, `LIKE 'first 100'`
            # would NOT match a stored question of 150 chars. → reverify outcome
            # was NEVER recorded → false_downgrades counter stayed 0 forever →
            # CognitiveGate's self-correction feedback loop was DEAD.
            # Fix: use a real substring match. Two strategies:
            #   (a) Match on a normalized hash of the question (best — O(1), exact).
            #   (b) Use LIKE with explicit wildcards: '%' || ? || '%' (substring).
            # We use (b) with the FULL question (not truncated) wrapped in
            # wildcards, plus a length guard to avoid pathological long queries.
            # Also escape LIKE-special chars (% and _) in the question to avoid
            # pattern-injection.
            from scp.core.db_manager import db_query_one
            _q_full = question[:500]  # cap to avoid pathological inputs
            # Escape LIKE wildcards in the question so they match literally
            _q_escaped = _q_full.replace('%', r'\%').replace('_', r'\_')
            _like_pattern = f"%{_q_escaped}%"
            row = db_query_one(
                "SELECT id, gated_verdict FROM cognitive_gate_log "
                "WHERE question LIKE ? ESCAPE '\\' AND gated_verdict != original_verdict "
                "ORDER BY id DESC LIMIT 1",
                (_like_pattern,)
            )
            if row:
                ts = datetime.now().astimezone().isoformat()
                db_exec(
                    "UPDATE cognitive_gate_log SET reverify_outcome=?, reverify_timestamp=? WHERE id=?",
                    (reverify_verdict, ts, row["id"])
                )
                if reverify_verdict == "PASS" and row["gated_verdict"] in ("UNKNOWN", "PARTIAL"):
                    self.stats["false_downgrades"] += 1
                    logger.info(f"[CognitiveGate V50] FALSE downgrade detected: Q='{question[:50]}' was downgraded to {row['gated_verdict']} but ReVerify PASS")
                else:
                    self.stats["confirmed_downgrades"] += 1
        except Exception as e:
            logger.debug(f"record_reverify_outcome error: {e}", exc_info=True)

    def evaluate(
        self,
        verdict: str,
        confidence: float,
        cognitive_result: dict[str, Any] | None,
        evidence_type: str = "",
        sources_succeeded: list[str] | None = None,
        question: str = "",   #  for logging
        domain: str = "",     #  for logging
    ) -> tuple[str, list[str], str]:
        """
        Evaluate verdict qua cognitive gate.

        Returns:
            (gated_verdict, gate_reasons, original_verdict)
        """
        self.stats["total_evaluated"] += 1

        # Only gate PASS verdicts (don't upgrade FAIL)
        original_verdict = verdict
        if verdict != "PASS":
            self.stats["unchanged"] += 1
            return verdict, [], original_verdict

        if cognitive_result is None:
            self.stats["unchanged"] += 1
            return verdict, [], original_verdict

        # [V65 FIX] Was: `if high_confidence_skip_gate or deterministic: skip`
        #   high_confidence_skip_gate was set for ALL conf>0.92 → gate skipped everything
        #   → downgrades=0 even after 68K questions
        # Now: only `deterministic` flag (math AST, logic, codata) skips gate.
        #   Empirical cases (crypto/weather/currency/chemistry) WILL be evaluated,
        #   but trusted sources are still protected by `verified_sources` check below
        #   AND by RecursiveWhy `terminated_at` logic.
        if cognitive_result.get("deterministic"):
            self.stats["unchanged"] += 1
            return verdict, [], original_verdict

        reasons: list[str] = []
        critical_failure = False  # marks UNKNOWN (instead of just PARTIAL)

        # Skip gating for deterministic (math, logic) — they don't need cognitive checks
        if evidence_type in ("deterministic_calculation",
                             "deterministic_evaluation",
                             "codata_constants"):
            self.stats["unchanged"] += 1
            return verdict, [], original_verdict

        # [V48 FIX] Skip gating for verified authoritative sources
        # Sources like PubChem, CODATA, NIST, Frankfurter, CoinGecko have already been
        # verified by their authoritative institutions — RecursiveWhy not reaching "axiom"
        # is normal for empirical data, NOT a defect.
        # Trước V48: PubChem molar mass → RecursiveWhy "unprovable" → PASS→PARTIAL → 100% FAIL in calibration
        # V48: treat verified-source data as "axiom_reached"
        verified_sources = {
            "pubchem", "codata", "nist", "frankfurter", "coingecko", "binance",
            "rest_countries", "rest countries", "open-meteo", "open_meteo",
            "wikidata", "wikipedia",
            "local chemistry database", "local physics database", "local math database",
            "local biology database", "local geography database", "local history database",
            "local medical database", "local sports database", "local legal database",
            "local arts database", "local technology database",
            "iupac periodic table", "nasa planetary fact sheet",
            "local conversion database", "local reality database",
            "local statistics database", "local logic database",
            # [V48.1] Local DB variants (SLM may use "LocalDB" short name)
            "localdb", "local db", "local database",
            "knowledgecache", "knowledge cache",
            # Source strings with "weighted(...)" format
            "weighted(pubchem", "weighted(coingecko", "weighted(frankfurter",
            "weighted(rest_countries", "weighted(open-meteo",
        }
        is_verified_source = False
        if sources_succeeded:
            for src in sources_succeeded:
                src_lower = (src or "").lower()
                if any(vs in src_lower for vs in verified_sources):
                    is_verified_source = True
                    break
        # [V48.1] Also check evidence source in verdict (not just sources_succeeded)
        # This handles cases where SLM used local DB but sources_succeeded only has SLM name
        if not is_verified_source:
            # Walk through slm responses (passed via cognitive_result context)
            # Actually we can't access responses here, but the caller already extracted
            # sources_succeeded. As a fallback, if confidence is already high (>0.85),
            # treat as verified.
            pass

        # 1. MetaFalsifier check
        meta = cognitive_result.get("meta_falsification")
        if meta:
            missing = meta.get("missing_vectors", [])
            critical_for_type = CRITICAL_VECTORS.get(evidence_type, set())
            missing_critical = [v for v in missing if v in critical_for_type]
            if len(missing_critical) >= 2:
                # ≥2 critical missing = UNKNOWN
                critical_failure = True
                reasons.append(
                    f"MetaFalsifier: plan thiếu {len(missing_critical)} critical vectors "
                    f"({', '.join(missing_critical)})"
                )
            elif len(missing_critical) == 1:
                reasons.append(
                    f"MetaFalsifier: thiếu 1 critical vector ({missing_critical[0]})"
                )

        # 2. ProofGraph check
        proof = cognitive_result.get("proof_graph")
        if proof:
            status = proof.get("overall_status", "")
            if status in ("broken", "failed"):
                critical_failure = True
                reasons.append(f"ProofGraph: overall_status = '{status}'")
            elif status == "incomplete":
                reasons.append("ProofGraph: overall_status = 'incomplete'")

        # 3. CounterQuestion check (ambiguity)
        # [V63 FIX] Only flag ambiguity for domains where ambiguity is meaningful
        # V46 domains (arts, sports, medical, legal, technology) have generic counter-questions
        # that always trigger — this causes false PARTIAL downgrades for correct answers
        cqs = cognitive_result.get("counter_questions", [])
        _counter_question_exempt_domains = {"arts", "sports", "medical", "legal", "technology",
                                            "education", "tourism", "agriculture", "environment"}
        if cqs and len(cqs) >= 2 and domain not in _counter_question_exempt_domains:
            ambiguity_types = {cq.get("type", "") for cq in cqs}
            if "scope_narrowing" in ambiguity_types and "assumption_challenging" in ambiguity_types:
                reasons.append(
                    f"CounterQuestion: {len(cqs)} alternative framings suggest ambiguity"
                )

        # 4. RecursiveWhy check
        # [V50 FIX] Use terminated_at directly — no more is_verified_source hack
        # RecursiveWhy now returns:
        #   "axiom"           → math/logic axioms (highest trust)
        #   "trusted_source"  → PubChem/CODATA/NASA/LocalDB (authoritative empirical)
        #   "unprovable"      → unknown source (low trust → flag)
        #   "max_depth"       → chain too long (medium trust → flag)
        # CognitiveGate only flags "unprovable" or "max_depth" with low depth.
        rw = cognitive_result.get("recursive_why")
        if rw:
            depth = rw.get("depth", 0)
            terminated_at = rw.get("terminated_at", "")
            # [V76 FIX] Was: `if terminated_at in ("unprovable", "circular") and depth < 2`
            #   → 785 PASS→PARTIAL downgrades vì RecursiveWhy luôn trả depth=0 unprovable cho empirical data
            # Now: only flag if depth >= 1 (actually tried to trace) AND terminated badly
            # depth=0 means RecursiveWhy didn't even start — that's normal for empirical, not a defect
            if terminated_at in ("unprovable", "circular") and 1 <= depth < 2:
                reasons.append(
                    f"RecursiveWhy: depth={depth}, terminated at '{terminated_at}' (not trusted)"
                )
            #  trusted_source and axiom are GOOD — no flag
            # (V48 had: `if not is_verified_source and depth < 2` — needed verified_sources list)

        # 5. Source count check
        # [V50 FIX] Skip for trusted_source termination (covered by RecursiveWhy above)
        # Only apply to truly unknown sources (not authoritative)
        rw_terminated = (cognitive_result.get("recursive_why") or {}).get("terminated_at", "")
        is_trusted = rw_terminated in ("axiom", "trusted_source")
        if sources_succeeded is not None and len(sources_succeeded) < 2 and not is_trusted:
            if evidence_type in ("live_api_data", "entity_fact"):
                reasons.append(
                    f"Single source ({len(sources_succeeded)}) for {evidence_type} - need ≥2"
                )

        # Decide downgrade level
        if not reasons:
            self.stats["unchanged"] += 1
            #  Log even when unchanged — for audit trail
            self._log_evaluated(question, domain, original_verdict, verdict, [], evidence_type)
            return verdict, [], original_verdict

        # critical_failure OR ≥2 reasons → UNKNOWN; else → PARTIAL
        if critical_failure or len(reasons) >= 2:
            self.stats["downgraded_to_unknown"] += 1
            gated = "UNKNOWN"
        else:
            self.stats["downgraded_to_partial"] += 1
            gated = "PARTIAL"

        #  Log the downgrade to DB + structured log
        self._log_downgrade(question, domain, original_verdict, gated, reasons, evidence_type)
        return gated, reasons, original_verdict

    def get_stats(self) -> dict[str, int]:
        return self.stats.copy()

    def reset_stats(self):
        self.stats = {
            "total_evaluated": 0,
            "downgraded_to_unknown": 0,
            "downgraded_to_partial": 0,
            "unchanged": 0,
            # [V104.32 #28] was: missing → KeyError in record_reverify_outcome
            "false_downgrades": 0,
            "confirmed_downgrades": 0,
        }


# Singleton
_gate: CognitiveGate | None = None


def get_cognitive_gate() -> CognitiveGate:
    global _gate
    if _gate is None:
        _gate = CognitiveGate()
    return _gate
