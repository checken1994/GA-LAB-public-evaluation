"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""
from __future__ import annotations

#!/usr/bin/env python3
"""
SCP V28 — Verdict Predictor.

Dự đoán verdict (PASS/FAIL/UNKNOWN) từ question pattern + domain,
TRƯỚC khi gọi API. Mục đích:
    - Nếu prediction = PASS với confidence cao → skip API call (tiết kiệm)
    - Nếu prediction = FAIL → ưu tiên verify API
    - Nếu prediction = UNKNOWN → skip API (sẽ UNKNOWN anyway)

Cơ chế:
    1. Lookup error_history cho cùng question (or same domain)
    2. Tính fail_rate / pass_rate / unknown_rate của pattern gần nhất
    3. Trả verdict prediction + confidence

Luồng tích hợp vào RealityJudge.judge():
    prediction = VerdictPredictor.predict(question, domain)
    if prediction.verdict == "PASS" and prediction.confidence > 0.8:
        # Skip API call, use SLM answer directly
        ...
    else:
        # Continue with full RealityJudge flow
        ...
"""

import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import logging

from scp.core.db_manager import db_query_all, init_db

logger = logging.getLogger("scp.verdict_predictor")


@dataclass
class VerdictPrediction:
    """Kết quả dự đoán verdict."""
    verdict: str           # "PASS" / "FAIL" / "UNKNOWN"
    confidence: float      # 0.0 - 1.0
    method: str            # "exact_match" / "domain_pattern" / "heuristic"
    sample_count: int      # số samples dùng để dự đoán
    skip_api: bool         # có nên skip API call không
    reason: str


class VerdictPredictor:
    """
    Verdict Predictor — dự đoán verdict trước khi gọi API.

    3 cấp:
      1. EXACT MATCH — same question đã từng hỏi → dùng verdict cũ
      2. DOMAIN PATTERN — cùng domain, tính fail_rate → heuristic
      3. HEURISTIC — rule-based (vd: math deterministic → PASS chắc)
    """

    # Cache trong memory (per-process)
    _CACHE_TTL_SEC = 300  # 5 minutes

    def __init__(self):
        init_db()
        self._exact_cache: dict[str, tuple[VerdictPrediction, float]] = {}
        self._domain_cache: dict[str, tuple[dict, float]] = {}

    # ============================================================
    # PREDICT
    # ============================================================
    def predict(self, question: str, domain: str = "",
                ai_answer: str = "") -> VerdictPrediction:
        """
        Dự đoán verdict cho 1 question.

        Returns:
            VerdictPrediction với verdict + skip_api flag.
        """
        # Normalize question
        q_norm = self._normalize_question(question)
        cache_key = f"{q_norm}|{domain}"

        # Check cache
        now = datetime.now().timestamp()
        if cache_key in self._exact_cache:
            pred, ts = self._exact_cache[cache_key]
            if now - ts < self._CACHE_TTL_SEC:
                return pred

        # 1) EXACT MATCH — same question đã từng hỏi
        pred = self._predict_exact(q_norm, question, domain)
        if pred is not None:
            self._exact_cache[cache_key] = (pred, now)
            return pred

        # 2) HEURISTIC — domain có SLM deterministic
        pred = self._predict_heuristic(question, domain)
        if pred is not None:
            self._exact_cache[cache_key] = (pred, now)
            return pred

        # 3) DOMAIN PATTERN — cùng domain, tính fail_rate
        pred = self._predict_domain_pattern(question, domain)
        self._exact_cache[cache_key] = (pred, now)
        return pred

    # ============================================================
    # STRATEGY 1: EXACT MATCH
    # ============================================================
    def _predict_exact(self, q_norm: str, question: str,
                       domain: str) -> VerdictPrediction | None:
        """Tìm cùng question trong error_history."""
        try:
            rows = db_query_all(
                "SELECT final_verdict, timestamp FROM error_history "
                "WHERE question = ? OR question LIKE ? "
                "ORDER BY timestamp DESC LIMIT 10",
                (question, f"%{q_norm[:50]}%")
            )
            if not rows:
                return None

            # Vote: đếm verdict gần nhất (last 5)
            recent = rows[:5]
            verdicts = [r["final_verdict"] for r in recent if r["final_verdict"]]
            if not verdicts:
                return None

            counter = Counter(verdicts)
            most_common, count = counter.most_common(1)[0]
            confidence = count / len(verdicts)
            sample_count = len(rows)

            # Skip API if confidence high
            skip_api = confidence > 0.8 and most_common != "UNKNOWN"

            return VerdictPrediction(
                verdict=most_common,
                confidence=confidence,
                method="exact_match",
                sample_count=sample_count,
                skip_api=skip_api,
                reason=f"Found {sample_count} similar questions, {count}/{len(verdicts)} = {most_common}",
            )
        except Exception as e:
            logger.warning(f"Predict exact error: {e}", exc_info=True)
            return None

    # ============================================================
    # STRATEGY 2: HEURISTIC (domain-specific rules)
    # ============================================================
    def _predict_heuristic(self, question: str,
                           domain: str) -> VerdictPrediction | None:
        """Heuristic rules cho domain có deterministic answer."""
        q_lower = question.lower()

        # Math — deterministic, luôn PASS nếu parse được
        # [V104.34 #61] TẠI SAO: "-" matches "AI-based", "self-correcting" → non-math misrouted
        import re as _re
        if domain == "math" or any(kw in q_lower for kw in ["tính", "calculate"]) or _re.search(r'\d\s*[+\-*/]\s*\d', q_lower):
            # Check if math expression extractable
            try:
                from scp.core.math_evaluator import extract_math_expression
                expr = extract_math_expression(question)
                if expr:
                    return VerdictPrediction(
                        verdict="PASS",
                        confidence=0.95,
                        method="heuristic_math_deterministic",
                        sample_count=0,
                        skip_api=True,  # Skip API — MathSLM đã deterministic
                        reason=f"Math deterministic: {expr}",
                    )
            except Exception as e:
                logger.debug(f"[V104.37] meta/verdict_predictor.py: e={e}", exc_info=True)

        # Logic — same as math
        if domain == "logic":
            if re.search(r'\d\s*[<>=!]+\s*\d', q_lower):
                return VerdictPrediction(
                    verdict="PASS", confidence=0.95,
                    method="heuristic_logic_deterministic",
                    sample_count=0, skip_api=True,
                    reason="Logic deterministic comparison",
                )

        # Statistics — deterministic
        if domain == "statistics":
            nums = re.findall(r'-?\d+\.?\d*', question)
            if len(nums) >= 2:
                return VerdictPrediction(
                    verdict="PASS", confidence=0.95,
                    method="heuristic_stats_deterministic",
                    sample_count=0, skip_api=True,
                    reason="Stats deterministic",
                )

        # Reality (constants) — deterministic if known
        if domain == "reality":
            CONSTANTS_KW = ["tốc độ ánh sáng", "hằng số planck", "số avogadro",
                            "gia tốc trọng trường", "speed of light", "gravity"]
            if any(kw in q_lower for kw in CONSTANTS_KW):
                return VerdictPrediction(
                    verdict="PASS", confidence=0.90,
                    method="heuristic_reality_known",
                    sample_count=0, skip_api=False,  # still call API to verify value
                    reason="Known CODATA constant",
                )

        return None

    # ============================================================
    # STRATEGY 3: DOMAIN PATTERN
    # ============================================================
    def _predict_domain_pattern(self, question: str,
                                domain: str) -> VerdictPrediction:
        """Tính fail_rate/pass_rate/unknown_rate cho domain."""
        if not domain:
            return VerdictPrediction(
                verdict="UNKNOWN", confidence=0.0,
                method="no_domain", sample_count=0,
                skip_api=False, reason="No domain specified"
            )

        # Check cache
        now = datetime.now().timestamp()
        if domain in self._domain_cache:
            stats, ts = self._domain_cache[domain]
            if now - ts < self._CACHE_TTL_SEC:
                return self._build_from_stats(stats, domain)

        # Query error_history grouped by frame=domain
        try:
            rows = db_query_all(
                "SELECT final_verdict, COUNT(*) as cnt FROM error_history "
                "WHERE frame = ? GROUP BY final_verdict",
                (domain,)
            )
            stats: dict[str, int] = {r["final_verdict"]: r["cnt"] for r in rows}
            self._domain_cache[domain] = (stats, now)
            return self._build_from_stats(stats, domain)
        except Exception as e:
            logger.warning(f"Domain pattern error: {e}", exc_info=True)
            return VerdictPrediction(
                verdict="UNKNOWN", confidence=0.0,
                method="error", sample_count=0,
                skip_api=False, reason=f"Error: {e}"
            )

    def _build_from_stats(self, stats: dict[str, int],
                          domain: str) -> VerdictPrediction:
        """Build prediction từ stats dict."""
        total = sum(stats.values())
        if total == 0:
            return VerdictPrediction(
                verdict="UNKNOWN", confidence=0.0,
                method="domain_pattern_empty", sample_count=0,
                skip_api=False, reason=f"No samples for domain '{domain}'"
            )

        pass_count = stats.get("PASS", 0)
        fail_count = stats.get("FAIL", 0)
        unknown_count = stats.get("UNKNOWN", 0)

        pass_rate = pass_count / total
        fail_rate = fail_count / total
        unknown_rate = unknown_count / total

        # Pick most likely verdict
        if pass_rate >= 0.7:
            verdict = "PASS"
            confidence = pass_rate
            skip_api = pass_rate > 0.85
        elif fail_rate >= 0.7:
            verdict = "FAIL"
            confidence = fail_rate
            skip_api = False  # always verify FAIL
        elif unknown_rate >= 0.5:
            verdict = "UNKNOWN"
            confidence = unknown_rate
            skip_api = unknown_rate > 0.8  # if mostly unknown, skip
        else:
            # Mixed — unknown prediction
            verdict = "UNKNOWN"
            confidence = 0.3
            skip_api = False

        return VerdictPrediction(
            verdict=verdict, confidence=confidence,
            method="domain_pattern",
            sample_count=total, skip_api=skip_api,
            reason=f"Domain '{domain}': pass={pass_rate:.0%} fail={fail_rate:.0%} unk={unknown_rate:.0%} (n={total})",
        )

    # ============================================================
    # HELPERS
    # ============================================================
    def _normalize_question(self, q: str) -> str:
        """Normalize question for comparison."""
        if not q:
            return ""
        # Lowercase, strip whitespace, collapse multiple spaces
        s = re.sub(r'\s+', ' ', q.lower().strip())
        return s

    # ============================================================
    # STATS
    # ============================================================
    def get_stats(self) -> dict[str, Any]:
        """Thống kê verdict predictor."""
        try:
            # Domain distribution
            rows = db_query_all(
                "SELECT frame, final_verdict, COUNT(*) as cnt FROM error_history "
                "GROUP BY frame, final_verdict ORDER BY frame, cnt DESC"
            )
            by_domain: dict[str, dict[str, int]] = defaultdict(lambda: {})
            for r in rows:
                d = r["frame"] or "unknown"
                by_domain[d][r["final_verdict"]] = r["cnt"]

            # Cache stats
            cache_size = len(self._exact_cache)
            domain_cache_size = len(self._domain_cache)

            return {
                "exact_cache_size": cache_size,
                "domain_cache_size": domain_cache_size,
                "domains": dict(by_domain),
            }
        except Exception as e:
            logger.warning("Verdict predictor get_stats failed: %s", e, exc_info=True)
            return {"error": str(e)}


# ============================================================
# MAIN
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCP V28 Verdict Predictor")
    parser.add_argument("--test", type=str, help="Test với 1 question")
    parser.add_argument("--domain", type=str, default="", help="Domain hint")
    parser.add_argument("--stats", action="store_true", help="Show stats")
    args = parser.parse_args()

    predictor = VerdictPredictor()

    if args.stats:
        stats = predictor.get_stats()
        print(f"\n{'='*60}")
        print("  VERDICT PREDICTOR STATS")
        print(f"{'='*60}")
        print(f"  Exact cache:   {stats.get('exact_cache_size', 0)}")
        print(f"  Domain cache:  {stats.get('domain_cache_size', 0)}")
        print("\n  Domain distribution:")
        for d, v in stats.get("domains", {}).items():
            total = sum(v.values())
            print(f"    {d:20s} total={total:>5} | {v}")
        return

    if args.test:
        pred = predictor.predict(args.test, args.domain)
        print(f"\n{'='*60}")
        print(f"  PREDICTION FOR: '{args.test}'")
        print(f"  Domain: {args.domain or '(auto)'}")
        print(f"{'='*60}")
        print(f"  Verdict:    {pred.verdict}")
        print(f"  Confidence: {pred.confidence:.3f}")
        print(f"  Method:     {pred.method}")
        print(f"  Samples:    {pred.sample_count}")
        print(f"  Skip API:   {pred.skip_api}")
        print(f"  Reason:     {pred.reason}")
        return

    print("Use --test 'question' or --stats")


if __name__ == "__main__":
    main()
