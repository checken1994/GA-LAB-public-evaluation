# SPDX-License-Identifier: AGPL-3.0-only
"""
SCP V4 FORTRESS — AI Defense Citadel
Copyright (c) 2026 Minh / SCP V4 Project. AGPL-3.0-only.

File: falsification_engine.py
Module: scp_v4.falsification_engine
Purpose: Continuous Falsification Engine — measures deviation, never declares truth.

Philosophy
----------
V4 is being restructured from an "Omnipotent Security Gateway" into a
"Continuous Falsification Engine". The 10 layers are no longer shields —
they are DEVIATION SENSORS. V4 NEVER declares "SAFE" or "TRUTH"; it only
reports one of:

    * UNREFUTED_IN_CURRENT_SCOPE  — no test contradicted the claim (yet)
    * NO_KNOWN_PATTERN_MATCHED    — no antibody/KB pattern matched
    * NO_CONTRADICTION_FOUND      — LLM answer agrees with reference data
    * CONTRADICTION_DETECTED      — LLM answer disagrees with a source
    * PATTERN_MATCHED             — a known malicious pattern matched
    * HUMAN_DECISION_REQUIRED     — confidence < 90% OR > 2 contradictions
    * REFUTED_BY_REALITY          — ground truth proved V4 wrong
    * OUT_OF_SCOPE                — V4 cannot evaluate this request

The engine is a MICROSCOPE, not a JUDGE. Every refutation by reality is
treated as the most valuable event in V4's life — it is persisted to the
real ErrorStore (scp/brain/error_store.py) and the response honestly
reports whether that persistence actually happened [A3 F-M2].
"""


# ============================================================
# STANDARD LIBRARY ONLY — no external ML deps
# ============================================================

import json
import logging
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS — V4 FORTRESS scope fingerprint
# ============================================================

CONFIDENCE_THRESHOLD: float = 0.90        # < 90%  -> HUMAN_DECISION_REQUIRED
MAX_CONTRADICTIONS_AUTO: int = 2          # > 2    -> HUMAN_DECISION_REQUIRED
V4_TOTAL_TEST_CASES: int = 161            # PyRIT (161) + garak probes
V4_LAYERS_ACTIVE: int = 14                # 10 sensor layers + 4 countermeasures
ERRORSTORE_TARGET_SIZE: int = 50_000      # 50K records target capacity
KB_DEFAULT_SIZE: int = 12_000             # placeholder KB size

# Severity thresholds (relative delta)
SEVERITY_LOW: float = 0.02      # < 2%   -> LOW
SEVERITY_MEDIUM: float = 0.10   # < 10%  -> MEDIUM
SEVERITY_HIGH: float = 0.25     # < 25%  -> HIGH
# >= 25% -> CRITICAL

# ============================================================
# SKEPTICAL STATUS LANGUAGE
# ============================================================


class FalsificationStatus(str, Enum):
    """Skeptical status language — NEVER absolute truth claims.

    The old V3/V4 verdicts (PASS/FAIL/SAFE/UNCERTAIN) implied certainty.
    The new language is deliberately humble: V4 reports what was tested
    and what was found, never what is "true".
    """

    UNREFUTED_IN_CURRENT_SCOPE = "UNREFUTED_IN_CURRENT_SCOPE"  # was PASS
    NO_KNOWN_PATTERN_MATCHED = "NO_KNOWN_PATTERN_MATCHED"      # was SAFE
    NO_CONTRADICTION_FOUND = "NO_CONTRADICTION_FOUND"          # was GROUND_TRUTH_VALID
    CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"          # LLM vs source mismatch
    PATTERN_MATCHED = "PATTERN_MATCHED"                        # was FAIL
    HUMAN_DECISION_REQUIRED = "HUMAN_DECISION_REQUIRED"        # confidence < 90%
    REFUTED_BY_REALITY = "REFUTED_BY_REALITY"                  # ground truth proved V4 wrong
    OUT_OF_SCOPE = "OUT_OF_SCOPE"                              # V4 cannot evaluate

    def is_skeptical(self) -> bool:
        """True if the status avoids any absolute truth claim."""
        return self in {
            FalsificationStatus.UNREFUTED_IN_CURRENT_SCOPE,
            FalsificationStatus.NO_KNOWN_PATTERN_MATCHED,
            FalsificationStatus.NO_CONTRADICTION_FOUND,
            FalsificationStatus.HUMAN_DECISION_REQUIRED,
            FalsificationStatus.OUT_OF_SCOPE,
        }

    def requires_human(self) -> bool:
        """True if a human must make the final decision."""
        return self in {
            FalsificationStatus.HUMAN_DECISION_REQUIRED,
            FalsificationStatus.REFUTED_BY_REALITY,
            FalsificationStatus.OUT_OF_SCOPE,
        }


# ============================================================
# NUMBER PARSING — Vietnamese-safe
# [Task 7-A Modularity] Đã tách sang _number_utils.py (giảm falsification_engine.py
# từ 1042 → 947 LOC). Helpers không phụ thuộc FalsificationEngine state.
# ============================================================

from scp.meta._number_utils import (
    _NUM_UNIT_RE,
    _UNIT_MULTIPLIERS,
    _normalize_number,
)

# ============================================================
# DATA MODELS
# ============================================================


@dataclass
class Deviation:
    """A single measured deviation between an LLM answer and a reference."""

    field: str
    llm_value: str
    reference_value: str
    delta: float          # relative |llm - ref| / |ref|
    severity: str         # LOW | MEDIUM | HIGH | CRITICAL
    # [SCP-DNA-FIX R5-6] missing_claim=True marks deviations where the LLM
    # produced NO numeric value for a numeric reference field. Such deviations
    # are real contradictions (severity="CRITICAL") but their delta=1.0 is a
    # SENTINEL ("100% missing") not a measured numeric deviation — including
    # them in max_dev would inflate max_dev to 1.0 whenever ANY field is
    # missing, masking actual numeric deviations. Default False preserves
    # backward-compat for all existing call sites (keyword-arg construction).
    missing_claim: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "llm_value": self.llm_value,
            "reference_value": self.reference_value,
            "delta": round(self.delta, 4),
            "severity": self.severity,
        }


@dataclass
class Contradiction:
    """A contradiction between two sources for a single field."""

    source_a: str
    source_b: str
    field: str
    value_a: str
    value_b: str
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_a": self.source_a,
            "source_b": self.source_b,
            "field": self.field,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "severity": self.severity,
        }


@dataclass
class Refutation:
    """A record of reality proving V4 wrong — V4's most valuable event."""

    refutation_id: str
    timestamp: str
    question: str
    v4_verdict: str
    reality: str
    lesson: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# FALSIFICATION ENGINE
# ============================================================


class FalsificationEngine:
    """Measures deviation, contradiction, and uncertainty.

    Never declares truth — only reports what was tested and what was found.

    Philosophy: V4 is a microscope, not a judge.
    """

    def __init__(self, error_store: Any | None = None) -> None:
        # All contradictions ever found by this engine instance.
        self.contradictions: list[Contradiction] = []
        # All refutations by reality — V4's "scars".
        self.refutations: list[Refutation] = []
        # [A3 F-M2] Real ErrorStore backing refutation records. None means
        # "not built yet" — the store is lazily constructed on first
        # record_refutation() call (deferred import, no I/O at engine boot).
        # Injectable for tests (tmp_path-backed store / fault-injecting stub).
        self._error_store: Any | None = error_store
        # [A3 F-M2] Count of refutation records ACTUALLY persisted to the
        # ErrorStore (never assumed). calculate_scope() reports this real
        # number instead of the previous fictional target-size arithmetic.
        self._errorstore_persisted: int = 0
        # What V4 tested vs what it didn't (mutable scope fingerprint).
        self.scope_limits: dict[str, Any] = {
            "last_self_falsification": "never",
            "domains_covered": set(),
            "domains_uncovered": set(),
        }
        # Per-test-type counters.
        self.test_coverage: dict[str, int] = defaultdict(int)

    # --------------------------------------------------------
    # VERDICT TRANSLATION (old absolute -> new skeptical)
    # --------------------------------------------------------

    def translate_old_verdict(self, old_verdict: str, context: dict) -> dict:
        """Translate old absolute verdicts to skeptical status.

        PASS      -> UNREFUTED_IN_CURRENT_SCOPE
                     + scope: "161 test cases"
                     + note: "Not declared safe — only unrefuted within test scope"
        FAIL      -> PATTERN_MATCHED
                     + pattern: which antibody/pattern matched
                     + note: "Known malicious pattern detected"
        UNCERTAIN -> HUMAN_DECISION_REQUIRED
                     + reason: why uncertain
                     + contradictions: list of conflicting signals
        ESCALATED -> HUMAN_DECISION_REQUIRED
                     + reason: medical/safety escalation

        Returns: {status, old_verdict, scope, note, contradictions, confidence}
        """
        context = context or {}
        old = (old_verdict or "").upper().strip()
        confidence = float(context.get("confidence", 0.0) or 0.0)
        scope = str(context.get("scope", f"{V4_TOTAL_TEST_CASES} test cases"))
        contradictions = list(context.get("contradictions", []) or [])

        if old == "PASS":
            return {
                "status": FalsificationStatus.UNREFUTED_IN_CURRENT_SCOPE.value,
                "old_verdict": old_verdict,
                "scope": scope,
                "note": "Not declared safe — only unrefuted within test scope",
                "contradictions": contradictions,
                "confidence": confidence if confidence else 0.95,
            }

        if old == "FAIL":
            return {
                "status": FalsificationStatus.PATTERN_MATCHED.value,
                "old_verdict": old_verdict,
                "scope": "pattern-matching layer (antibodies + KB)",
                "note": "Known malicious pattern detected",
                "pattern": context.get("pattern", "unknown"),
                "contradictions": contradictions,
                "confidence": confidence if confidence else 0.99,
            }

        if old == "UNCERTAIN":
            reason = context.get("reason", "conflicting signals across layers")
            return {
                "status": FalsificationStatus.HUMAN_DECISION_REQUIRED.value,
                "old_verdict": old_verdict,
                "scope": "insufficient — human review required",
                "note": "V4 could not reach threshold confidence",
                "reason": reason,
                "contradictions": contradictions,
                "confidence": confidence if confidence else 0.50,
            }

        if old == "ESCALATED":
            reason = context.get("reason", "medical/safety escalation")
            return {
                "status": FalsificationStatus.HUMAN_DECISION_REQUIRED.value,
                "old_verdict": old_verdict,
                "scope": "medical/safety domain — human owns final decision",
                "note": "Human decision required — safety-critical domain",
                "reason": reason,
                "contradictions": contradictions,
                "confidence": confidence,
            }

        # Unknown verdict type — V4 honestly admits it cannot translate.
        return {
            "status": FalsificationStatus.OUT_OF_SCOPE.value,
            "old_verdict": old_verdict,
            "scope": "unknown verdict type",
            "note": f"V4 cannot translate verdict '{old_verdict}' — out of scope",
            "contradictions": contradictions,
            "confidence": 0.0,
        }

    # --------------------------------------------------------
    # DEVIATION MEASUREMENT
    # --------------------------------------------------------

    @staticmethod
    def _extract_numbers(text: str) -> list[dict[str, Any]]:
        """Extract all (value, raw, unit) triples from free text.

        Vietnamese-safe: preserves diacritics, recognises 'tỷ', 'triệu', etc.
        """
        if not text:
            return []
        results: list[dict[str, Any]] = []
        seen_spans = set()
        for m in _NUM_UNIT_RE.finditer(str(text)):
            span = m.span()
            if span in seen_spans:
                continue
            seen_spans.add(span)
            raw_num, unit = m.group(1), m.group(2)
            try:
                value = float(raw_num.replace(",", ""))
            except ValueError as exc:
                # silent-by-design: probe order — next probe swaps the separator to a dot.
                logger.debug("falsification_engine: comma-strip parse failed, trying dot-swap: %s", exc, exc_info=True)
                try:
                    value = float(raw_num.replace(",", "."))
                except ValueError as exc:
                    # silent-by-design: both parse probes failed; the token is not a number by contract.
                    logger.debug("falsification_engine: number parse failed, skipping token: %s", exc, exc_info=True)
                    continue
            if unit:
                mult = _UNIT_MULTIPLIERS.get(unit.lower())
                if mult is not None:
                    value *= mult
            results.append({
                "value": value,
                "raw": m.group(0).strip(),
                "unit": unit or "",
            })
        return results

    @staticmethod
    def _classify_severity(delta: float) -> str:
        """Classify a relative delta into a severity bucket."""
        if delta < SEVERITY_LOW:
            return "LOW"
        if delta < SEVERITY_MEDIUM:
            return "MEDIUM"
        if delta < SEVERITY_HIGH:
            return "HIGH"
        return "CRITICAL"

    def measure_deviation(self, llm_answer: str, reference_data: dict) -> dict:
        """Measure deviation between LLM answer and reference data.

        Does NOT correct — only MEASURES.

        Parameters
        ----------
        llm_answer : str
            Free-text answer produced by the LLM.
        reference_data : dict
            Mapping of field_name -> value (number or string with number+unit).
            Example: {"revenue": "62.849 tỷ", "growth_pct": 17.3}

        Returns
        -------
        dict
            {
                deviations: [{field, llm_value, reference_value, delta, severity}],
                max_deviation: float,
                contradiction_count: int,
                status: NO_CONTRADICTION_FOUND | CONTRADICTION_DETECTED
            }
        """
        deviations: list[Deviation] = []
        llm_numbers = self._extract_numbers(llm_answer)

        for field_name, ref_value in (reference_data or {}).items():
            ref_num = _normalize_number(ref_value)
            if ref_num is None:
                # Reference itself is non-numeric — skip (cannot measure deviation).
                continue

            best_match: dict[str, Any] | None = None
            best_delta: float = float("inf")
            for ln in llm_numbers:
                if ref_num == 0.0:
                    delta = abs(ln["value"])
                else:
                    delta = abs(ln["value"] - ref_num) / abs(ref_num)
                if delta < best_delta:
                    best_delta = delta
                    best_match = ln

            if best_match is None:
                # LLM produced no number for this field — record as a missing-claim.
                # [SCP-DNA-FIX R5-6] TẠI SAO: was hardcoding delta=1.0 for ALL
                # missing-claim deviations, which then DOMINATED the max_dev
                # calculation below (max(d.delta for d in deviations)) whenever
                # ANY field was missing — even if the LLM DID answer other
                # numeric fields correctly with small deviations.
                # REALITY EVIDENCE (PowerShell.txt V97 falsification logs):
                # 72/72 V97 log lines had max_dev=1.0 because the LLM (under
                # jailbreak attack) gave non-numeric answers and every numeric
                # reference field became a missing-claim with delta=1.0.
                # This produced false-alarm CONTRADICTION_DETECTED on every
                # attack response even when no measurable numeric deviation
                # existed. Fix: keep delta=1.0 + severity="CRITICAL" (still
                # flags the missing-claim as a contradiction in
                # contradiction_count) but set missing_claim=True so the
                # max_dev computation below EXCLUDES sentinel deviations and
                # reflects only actual measured numeric deviations.
                deviations.append(Deviation(
                    field=field_name,
                    llm_value="<no number found>",
                    reference_value=str(ref_value),
                    delta=1.0,
                    severity="CRITICAL",
                    missing_claim=True,
                ))
                continue

            severity = self._classify_severity(best_delta)
            deviations.append(Deviation(
                field=field_name,
                llm_value=best_match["raw"],
                reference_value=str(ref_value),
                delta=best_delta,
                severity=severity,
            ))

        # [SCP-DNA-FIX R5-6] max_dev EXCLUDES missing_claim deviations (their
        # delta=1.0 is a sentinel, not a measured numeric deviation). Without
        # this filter, ANY missing numeric field inflates max_dev to 1.0,
        # masking actual numeric deviations. See Deviation.missing_claim above.
        numeric_deltas = [d.delta for d in deviations if not d.missing_claim]
        max_dev = max(numeric_deltas, default=0.0)
        contradiction_count = sum(
            1 for d in deviations if d.severity in ("HIGH", "CRITICAL")
        )
        status = (
            FalsificationStatus.CONTRADICTION_DETECTED
            if contradiction_count > 0
            else FalsificationStatus.NO_CONTRADICTION_FOUND
        )

        # Track coverage for scope accounting.
        self.test_coverage["measure_deviation"] += 1

        return {
            "deviations": [d.to_dict() for d in deviations],
            "max_deviation": round(max_dev, 4),
            "contradiction_count": contradiction_count,
            "status": status.value,
        }

    # --------------------------------------------------------
    # CONTRADICTION REPORT (replaces closed verdict)
    # --------------------------------------------------------

    def generate_contradiction_report(
        self,
        question: str,
        llm_answer: str,
        evidence: list,
        ground_truth: dict,
    ) -> dict:
        """Generate a Contradiction Report (replaces the old closed verdict).

        The report does NOT conclude — it presents data for human decision.
        Every claim becomes either a contradiction or an unrefuted claim,
        never a "verified truth".
        """
        contradictions: list[dict[str, Any]] = []
        unrefuted_claims: list[dict[str, Any]] = []

        # 1. Measure LLM answer against ground truth.
        llm_vs_gt = self.measure_deviation(llm_answer, ground_truth)
        for dev in llm_vs_gt["deviations"]:
            entry = {
                "source_a": "llm_answer",
                "source_b": "ground_truth",
                "field": dev["field"],
                "value_a": dev["llm_value"],
                "value_b": dev["reference_value"],
                "delta": dev["delta"],
                "severity": dev["severity"],
            }
            if dev["severity"] in ("HIGH", "CRITICAL"):
                contradictions.append(entry)
                self.contradictions.append(Contradiction(
                    source_a="llm_answer",
                    source_b="ground_truth",
                    field=dev["field"],
                    value_a=dev["llm_value"],
                    value_b=dev["reference_value"],
                    severity=dev["severity"],
                ))
            else:
                unrefuted_claims.append(entry)

        # 2. Measure each piece of evidence against ground truth.
        for idx, ev in enumerate(evidence or []):
            if not isinstance(ev, dict):
                # Plain string evidence — compare its numbers to GT fields.
                ev_dev = self.measure_deviation(str(ev), ground_truth)
                for dev in ev_dev["deviations"]:
                    if dev["severity"] in ("HIGH", "CRITICAL"):
                        contradictions.append({
                            "source_a": f"evidence[{idx}]",
                            "source_b": "ground_truth",
                            "field": dev["field"],
                            "value_a": dev["llm_value"],
                            "value_b": dev["reference_value"],
                            "delta": dev["delta"],
                            "severity": dev["severity"],
                        })
                continue
            # Dict evidence: only compare keys that overlap with ground_truth.
            overlap = {k: v for k, v in ev.items() if k in ground_truth}
            if not overlap:
                continue
            ev_dev = self.measure_deviation(json.dumps(overlap, ensure_ascii=False), overlap)
            for dev in ev_dev["deviations"]:
                if dev["severity"] in ("HIGH", "CRITICAL"):
                    contradictions.append({
                        "source_a": f"evidence[{idx}]",
                        "source_b": "ground_truth",
                        "field": dev["field"],
                        "value_a": dev["llm_value"],
                        "value_b": dev["reference_value"],
                        "delta": dev["delta"],
                        "severity": dev["severity"],
                    })

        # 3. Confidence: ratio of unrefuted claims to total measured claims.
        total_claims = len(llm_vs_gt["deviations"])
        contradicted = sum(
            1 for c in contradictions if c["source_a"] == "llm_answer"
        )
        if total_claims > 0:
            confidence = max(0.0, 1.0 - (contradicted / total_claims))
        else:
            confidence = 0.5  # nothing to measure — uncertain by default

        # 4. Test scope fingerprint.
        test_scope = {
            "tests_run": V4_TOTAL_TEST_CASES,
            "tests_passed": V4_TOTAL_TEST_CASES - len(self.refutations),
            "tests_failed": len(self.refutations),
            "coverage_percent": round(
                100.0 * (1.0 - len(self.refutations) / max(V4_TOTAL_TEST_CASES, 1)), 2
            ),
        }

        # 5. Should a human decide?
        escalate, escalate_reason = self.should_escalate_human(
            confidence, contradictions
        )

        # 6. V4 recommendation is NEVER "approve/reject" — only a review hint.
        if contradictions:
            recommendation = (
                f"Review {len(contradictions)} contradiction(s) before deciding — "
                f"V4 will not conclude."
            )
        else:
            recommendation = (
                "No contradictions detected within test scope — "
                "human still owns the final decision."
            )

        self.test_coverage["contradiction_reports"] += 1

        return {
            "question": question,
            "llm_answer": llm_answer,
            "evidence_summary": f"{len(evidence or [])} source(s) checked",
            "contradictions": contradictions,
            "unrefuted_claims": unrefuted_claims,
            "test_scope": test_scope,
            "confidence": round(confidence, 4),
            "v4_recommendation": recommendation,
            "human_decision_required": escalate,
            "escalation_reason": escalate_reason,
        }

    # --------------------------------------------------------
    # SCOPE CALCULATION
    # --------------------------------------------------------

    def calculate_scope(self) -> dict:
        """Calculate what V4 has tested vs what it hasn't.

        Returns
        -------
        dict
            {
                total_test_cases: int,    # 161 PyRIT + garak probes
                layers_active: int,       # 14
                errorstore_size: int,
                kb_size: int,
                coverage_gaps: [str],     # known blind spots
                last_falsification: str,  # ISO timestamp or "never"
            }
        """
        coverage_gaps = [
            "multilingual attacks <5% coverage (vi/en/fr/ja/zh)",
            "zero-day prompt patterns untested",
            "multimodal (image/audio) partial — text-only verified",
            "agentic tool-use attacks emerging — coverage TBD",
            "long-context (>32k tokens) injection untested",
            "cross-modal latent injection untested",
        ]
        return {
            "total_test_cases": V4_TOTAL_TEST_CASES,
            "layers_active": V4_LAYERS_ACTIVE,
            # [A3 F-M2] HONEST count: only refutation records this engine
            # actually persisted to the real ErrorStore. Previously this key
            # reported `ERRORSTORE_TARGET_SIZE + len(self.refutations)` — a
            # fictional 50K+ figure that never matched any store on disk.
            "errorstore_size": self._errorstore_persisted,
            "errorstore_target_capacity": ERRORSTORE_TARGET_SIZE,
            "kb_size": KB_DEFAULT_SIZE,
            "coverage_gaps": coverage_gaps,
            "last_falsification": self.scope_limits.get(
                "last_self_falsification", "never"
            ),
        }

    # --------------------------------------------------------
    # REFUTATION RECORDING — V4's most valuable event
    # --------------------------------------------------------

    def _get_error_store(self) -> Any:
        """Return the real ErrorStore backing refutation records (lazy).

        [A3 F-M2] record_refutation previously returned
        ``errorstore_grew: True`` unconditionally while never writing to any
        store. The claim must be earned: refutations are appended to
        ``scp.brain.error_store.ErrorStore`` (default ``data/error_store.jsonl``,
        the same store the rest of the pipeline uses). The import is deferred
        to avoid any module-load cycle; construction failures propagate to the
        caller's best-effort handler, never silently swallowed.
        """
        if self._error_store is None:
            from scp.brain.error_store import ErrorStore

            self._error_store = ErrorStore()
        return self._error_store

    def record_refutation(
        self, question: str, v4_verdict: str, reality: str
    ) -> dict:
        """Record when Reality proves V4 wrong.

        This is the MOST VALUABLE event in V4's life — it is learning its
        own limits. Each refutation grows the ErrorStore (the HEART of
        humble V4) so the same mistake is never repeated.

        [A3 F-M2 honesty fix] The response now reports EXACTLY what happened:
        ``errorstore_grew`` is True only when a record was really appended to
        the ErrorStore; spam-filter rejections and store failures are reported
        via ``errorstore_note`` with ``errorstore_grew: False`` (fail-honest,
        never a manufactured claim).

        Returns
        -------
        dict
            {refutation_id, recorded, errorstore_grew, errorstore_id,
             errorstore_note, lesson, timestamp}
        """
        refutation = Refutation(
            refutation_id=f"ref_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            question=question,
            v4_verdict=v4_verdict,
            reality=reality,
            lesson=(
                f"V4 said '{v4_verdict}' but reality was '{reality}' — "
                f"scope limit exposed and recorded in ErrorStore."
            ),
        )
        self.refutations.append(refutation)
        self.scope_limits["last_self_falsification"] = refutation.timestamp
        self.test_coverage["refutations"] += 1

        logger.info(
            "REFUTATION_RECORDED id=%s question=%r v4=%r reality=%r",
            refutation.refutation_id, question[:80], v4_verdict, reality[:80],
        )

        # [A3 F-M2] Persist to the REAL ErrorStore — best-effort but HONEST:
        # every outcome that is not a successful append downgrades the
        # response instead of claiming growth that never happened.
        errorstore_grew = False
        errorstore_id: str | None = None
        errorstore_note: str | None = None
        try:
            record = self._get_error_store().add(
                question=question,
                answer=refutation.lesson,
                verdict="REFUTED",
                domain="falsification",
                error_type="v4_refutation",
                details={
                    "refutation_id": refutation.refutation_id,
                    "v4_verdict": v4_verdict,
                    "reality": reality,
                },
            )
            if isinstance(record, dict) and record.get("rejected"):
                errorstore_note = (
                    "errorstore_rejected:"
                    + str(record.get("reject_reason", "unknown"))
                )
                logger.warning(
                    "Refutation %s NOT persisted — ErrorStore rejected it (%s)",
                    refutation.refutation_id,
                    record.get("reject_reason", "unknown"),
                )
            else:
                errorstore_grew = True
                errorstore_id = (
                    str(record.get("id")) if isinstance(record, dict) else None
                )
                self._errorstore_persisted += 1
        except Exception as exc:
            errorstore_note = (
                f"errorstore_unavailable:{type(exc).__name__}:{exc}"
            )
            logger.warning(
                "Refutation %s could NOT be persisted to ErrorStore: %s",
                refutation.refutation_id,
                errorstore_note,
                exc_info=True,
            )

        return {
            "refutation_id": refutation.refutation_id,
            "recorded": True,
            # [A3 F-M2] earned claim — True ONLY on a real successful append.
            "errorstore_grew": errorstore_grew,
            "errorstore_id": errorstore_id,
            "errorstore_note": errorstore_note,
            "lesson": refutation.lesson,
            "timestamp": refutation.timestamp,
        }

    # --------------------------------------------------------
    # HUMAN ESCALATION POLICY
    # --------------------------------------------------------

    def should_escalate_human(
        self, confidence: float, contradictions: list
    ) -> tuple[bool, str]:
        """Determine if a human decision is required.

        Rule: confidence < 90%  OR  contradictions > 2  ->  escalate.

        Returns
        -------
        (escalate: bool, reason: str)
        """
        reasons: list[str] = []
        try:
            conf = float(confidence)
        except (TypeError, ValueError) as exc:
            # silent-by-design: the 0% treatment is recorded in reasons and returned to the caller.
            logger.debug("falsification_engine: confidence unparseable, treating as 0: %s", exc, exc_info=True)
            conf = 0.0
            reasons.append("confidence unparseable — treating as 0%")
        if conf < CONFIDENCE_THRESHOLD:
            reasons.append(
                f"confidence {conf:.1%} < {CONFIDENCE_THRESHOLD:.0%} threshold"
            )
        n_contradictions = len(contradictions or [])
        if n_contradictions > MAX_CONTRADICTIONS_AUTO:
            reasons.append(
                f"{n_contradictions} contradictions > {MAX_CONTRADICTIONS_AUTO} "
                f"auto-decide limit"
            )
        if reasons:
            return True, "; ".join(reasons)
        return False, (
            f"within auto-decide scope (confidence {conf:.1%}, "
            f"{n_contradictions} contradictions)"
        )

    # --------------------------------------------------------
    # FALSIFICATION STATS — focused on LIMITS, not successes
    # --------------------------------------------------------

    def get_falsification_stats(self) -> dict:
        """Stats focused on V4's LIMITS, not its successes.

        Returns
        -------
        dict
            {
                total_refutations: int,
                total_contradictions: int,
                coverage_gaps: list,
                errorstore_growth_rate: float,
                human_escalations: int,
                last_self_falsification: str,
                scope_label: "161 test cases, 14 layers, 50K error store"
            }
        """
        # Count refutations that triggered a human escalation.
        human_escalations = sum(
            1 for r in self.refutations
            if "human" in (r.v4_verdict or "").lower()
            or "escalat" in (r.v4_verdict or "").lower()
        )

        # Coverage gaps are inherited from calculate_scope() to stay in sync.
        scope = self.calculate_scope()

        # ErrorStore growth rate: refutations per "day" (here: per session,
        # since we have no real clock — we approximate with count).
        growth_rate = float(len(self.refutations))

        return {
            "total_refutations": len(self.refutations),
            "total_contradictions": len(self.contradictions),
            "coverage_gaps": scope["coverage_gaps"],
            "errorstore_growth_rate": round(growth_rate, 4),
            "human_escalations": human_escalations,
            "last_self_falsification": scope["last_falsification"],
            "scope_label": (
                f"{V4_TOTAL_TEST_CASES} test cases, "
                f"{V4_LAYERS_ACTIVE} layers, "
                f"{ERRORSTORE_TARGET_SIZE // 1000}K error store"
            ),
            "test_coverage": dict(self.test_coverage),
        }

    # --------------------------------------------------------
    # SERIALIZATION (for persistence / debugging)
    # --------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize the engine state to a plain dict (JSON-safe)."""
        return {
            "contradictions": [c.to_dict() for c in self.contradictions],
            "refutations": [r.to_dict() for r in self.refutations],
            "scope_limits": {
                k: (list(v) if isinstance(v, set) else v)
                for k, v in self.scope_limits.items()
            },
            "test_coverage": dict(self.test_coverage),
            "stats": self.get_falsification_stats(),
        }

    def __repr__(self) -> str:
        return (
            f"<FalsificationEngine contradictions={len(self.contradictions)} "
            f"refutations={len(self.refutations)}>"
        )


# ============================================================
# SMOKE TEST — runs when invoked as `python -m scp_v4.falsification_engine`
# ============================================================


def _smoke_test() -> None:
    """Exercise every public method of FalsificationEngine."""

    sep = "=" * 72
    print(sep)
    print("SCP V4 FORTRESS — FalsificationEngine smoke test")
    print("Philosophy: V4 is a microscope, not a judge.")
    print(sep)

    engine = FalsificationEngine()

    # --------------------------------------------------------
    # TEST 1: translate_old_verdict (PASS -> UNREFUTED_IN_CURRENT_SCOPE)
    # --------------------------------------------------------
    print("\n[1] translate_old_verdict: PASS -> UNREFUTED_IN_CURRENT_SCOPE")
    translated = engine.translate_old_verdict(
        "PASS",
        {"scope": "161 test cases", "confidence": 0.95},
    )
    print(f"    status    = {translated['status']}")
    print(f"    scope     = {translated['scope']}")
    print(f"    note      = {translated['note']}")
    print(f"    confidence= {translated['confidence']}")
    assert translated["status"] == "UNREFUTED_IN_CURRENT_SCOPE", (  # noqa: S101
        "PASS must translate to UNREFUTED_IN_CURRENT_SCOPE"
    )
    assert "Not declared safe" in translated["note"]  # noqa: S101
    print("    [OK] PASS correctly translated to skeptical status.")

    # Also test FAIL, UNCERTAIN, ESCALATED.
    fail_t = engine.translate_old_verdict(
        "FAIL", {"pattern": "prompt_injection_jailbreak", "confidence": 0.99}
    )
    print(f"\n    FAIL   -> {fail_t['status']} (pattern={fail_t['pattern']})")
    assert fail_t["status"] == "PATTERN_MATCHED"  # noqa: S101

    unc_t = engine.translate_old_verdict(
        "UNCERTAIN", {"reason": "conflicting layers", "confidence": 0.55}
    )
    print(f"    UNCERT -> {unc_t['status']} (reason={unc_t['reason']})")
    assert unc_t["status"] == "HUMAN_DECISION_REQUIRED"  # noqa: S101

    esc_t = engine.translate_old_verdict(
        "ESCALATED", {"reason": "medical dosage — safety critical"}
    )
    print(f"    ESCAL  -> {esc_t['status']} (reason={esc_t['reason']})")
    assert esc_t["status"] == "HUMAN_DECISION_REQUIRED"  # noqa: S101

    unk_t = engine.translate_old_verdict("BOGUS_VERDICT", {})
    print(f"    BOGUS  -> {unk_t['status']}")
    assert unk_t["status"] == "OUT_OF_SCOPE"  # noqa: S101

    # --------------------------------------------------------
    # TEST 2: measure_deviation (FPT revenue 52 tỷ vs 62.849 tỷ)
    # --------------------------------------------------------
    print("\n[2] measure_deviation: LLM '52 tỷ' vs reference '62.849 tỷ'")
    llm_answer = "FPT Corporation reported revenue of 52 tỷ VND in Q3 2026."
    reference_data = {"revenue": "62.849 tỷ"}
    dev = engine.measure_deviation(llm_answer, reference_data)
    print(f"    status            = {dev['status']}")
    print(f"    max_deviation     = {dev['max_deviation']:.4f} "
          f"({dev['max_deviation']*100:.2f}%)")
    print(f"    contradiction_cnt = {dev['contradiction_count']}")
    for d in dev["deviations"]:
        print(f"    - {d['field']}: llm={d['llm_value']} vs "
              f"ref={d['reference_value']} delta={d['delta']:.4f} "
              f"severity={d['severity']}")
    assert dev["status"] == "CONTRADICTION_DETECTED", (  # noqa: S101
        "52 tỷ vs 62.849 tỷ must be a contradiction"
    )
    assert dev["max_deviation"] > 0.10, "delta should exceed 10%"  # noqa: S101
    assert dev["deviations"][0]["severity"] in ("HIGH", "CRITICAL")  # noqa: S101
    print("    [OK] Deviation correctly measured — NOT corrected, only measured.")

    # --------------------------------------------------------
    # TEST 3: generate_contradiction_report with conflicting data
    # --------------------------------------------------------
    print("\n[3] generate_contradiction_report: conflicting evidence")
    question = "What was FPT's Q3 2026 revenue?"
    llm_answer_2 = "FPT revenue was 52 tỷ VND, profit 8 tỷ VND."
    evidence = [
        {"source": "Cafef", "revenue": "60 tỷ"},
        {"source": "VnExpress", "revenue": "62.849 tỷ"},
    ]
    ground_truth = {"revenue": "62.849 tỷ", "profit": "8.5 tỷ"}
    report = engine.generate_contradiction_report(
        question, llm_answer_2, evidence, ground_truth
    )
    print(f"    question              = {report['question']}")
    print(f"    evidence_summary      = {report['evidence_summary']}")
    print(f"    contradictions        = {len(report['contradictions'])}")
    for c in report["contradictions"]:
        print(f"      - {c['source_a']} vs {c['source_b']} on {c['field']}: "
              f"{c['value_a']} vs {c['value_b']} [{c['severity']}]")
    print(f"    unrefuted_claims      = {len(report['unrefuted_claims'])}")
    print(f"    confidence            = {report['confidence']:.4f}")
    print(f"    human_decision_req    = {report['human_decision_required']}")
    print(f"    v4_recommendation     = {report['v4_recommendation']}")
    assert len(report["contradictions"]) >= 1, "should find >=1 contradiction"  # noqa: S101
    assert "Review" in report["v4_recommendation"] or "No contradictions" in report["v4_recommendation"]  # noqa: S101
    print("    [OK] Report generated — no conclusion, only data for human review.")

    # --------------------------------------------------------
    # TEST 4: should_escalate_human (confidence 0.85 < 0.90)
    # --------------------------------------------------------
    print("\n[4] should_escalate_human: confidence 0.85 < 0.90")
    escalate, reason = engine.should_escalate_human(0.85, [])
    print(f"    escalate = {escalate}")
    print(f"    reason   = {reason}")
    assert escalate is True, "0.85 < 0.90 must escalate"  # noqa: S101
    assert "confidence" in reason.lower()  # noqa: S101

    # Boundary case: exactly 0.90 -> no escalate.
    esc2, reason2 = engine.should_escalate_human(0.90, [])
    print(f"    boundary 0.90 -> escalate={esc2} ({reason2})")
    assert esc2 is False, "0.90 == threshold should NOT escalate"  # noqa: S101

    # Contradiction count > 2 -> escalate even at high confidence.
    esc3, reason3 = engine.should_escalate_human(0.99, [1, 2, 3])
    print(f"    3 contradictions @ 0.99 -> escalate={esc3} ({reason3})")
    assert esc3 is True, "3 contradictions must escalate"  # noqa: S101
    print("    [OK] Escalation policy correctly enforced.")

    # --------------------------------------------------------
    # TEST 5: record_refutation
    # --------------------------------------------------------
    print("\n[5] record_refutation: reality proves V4 wrong")
    ref = engine.record_refutation(
        question="Is medicine X safe in pregnancy?",
        v4_verdict="UNREFUTED_IN_CURRENT_SCOPE",
        reality="CONTRAINDICATED in 1st trimester — FDA category D",
    )
    print(f"    refutation_id   = {ref['refutation_id']}")
    print(f"    recorded        = {ref['recorded']}")
    print(f"    errorstore_grew = {ref['errorstore_grew']}")
    print(f"    lesson          = {ref['lesson']}")
    assert ref["recorded"] is True  # noqa: S101
    assert ref["errorstore_grew"] is True  # noqa: S101
    assert len(engine.refutations) == 1  # noqa: S101
    print("    [OK] Refutation recorded — ErrorStore grew by 1.")

    # --------------------------------------------------------
    # TEST 6: calculate_scope
    # --------------------------------------------------------
    print("\n[6] calculate_scope: what V4 tested vs what it didn't")
    scope = engine.calculate_scope()
    print(f"    total_test_cases   = {scope['total_test_cases']}")
    print(f"    layers_active      = {scope['layers_active']}")
    print(f"    errorstore_size    = {scope['errorstore_size']}")
    print(f"    kb_size            = {scope['kb_size']}")
    print(f"    coverage_gaps      = {len(scope['coverage_gaps'])} known gaps")
    for g in scope["coverage_gaps"][:3]:
        print(f"      - {g}")
    print(f"    last_falsification = {scope['last_falsification']}")
    assert scope["total_test_cases"] == V4_TOTAL_TEST_CASES  # noqa: S101
    assert scope["layers_active"] == V4_LAYERS_ACTIVE  # noqa: S101
    assert len(scope["coverage_gaps"]) > 0, "V4 must acknowledge its blind spots"  # noqa: S101
    print("    [OK] Scope fingerprint includes coverage gaps.")

    # --------------------------------------------------------
    # TEST 7: get_falsification_stats
    # --------------------------------------------------------
    print("\n[7] get_falsification_stats: V4's limits, not its successes")
    stats = engine.get_falsification_stats()
    print(f"    total_refutations       = {stats['total_refutations']}")
    print(f"    total_contradictions    = {stats['total_contradictions']}")
    print(f"    coverage_gaps           = {len(stats['coverage_gaps'])} gaps")
    print(f"    errorstore_growth_rate  = {stats['errorstore_growth_rate']}")
    print(f"    human_escalations       = {stats['human_escalations']}")
    print(f"    last_self_falsification = {stats['last_self_falsification']}")
    print(f"    scope_label             = {stats['scope_label']}")
    print(f"    test_coverage           = {stats['test_coverage']}")
    assert stats["total_refutations"] == 1  # noqa: S101
    assert stats["total_contradictions"] >= 1  # noqa: S101
    assert "161 test cases" in stats["scope_label"]  # noqa: S101
    print("    [OK] Stats focus on limits — refutations, gaps, escalations.")

    # --------------------------------------------------------
    # TEST 8: serialization sanity
    # --------------------------------------------------------
    print("\n[8] to_dict() serialization sanity")
    payload = engine.to_dict()
    json_str = json.dumps(payload, ensure_ascii=False, default=str)
    print(f"    serialized length = {len(json_str)} chars")
    print(f"    refutations       = {len(payload['refutations'])}")
    print(f"    contradictions    = {len(payload['contradictions'])}")
    assert len(payload["refutations"]) == 1  # noqa: S101
    assert len(payload["contradictions"]) >= 1  # noqa: S101
    print("    [OK] Engine state is JSON-serializable.")

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------
    print("\n" + sep)
    print("ALL SMOKE TESTS PASSED")
    print("V4 never declared SAFE or TRUTH — only measured and reported.")
    print(sep)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    _smoke_test()
