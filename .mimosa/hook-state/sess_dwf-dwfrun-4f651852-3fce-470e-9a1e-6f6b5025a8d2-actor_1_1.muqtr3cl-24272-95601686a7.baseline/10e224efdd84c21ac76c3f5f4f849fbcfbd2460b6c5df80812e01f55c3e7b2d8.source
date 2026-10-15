from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from math import isfinite
from typing import Any

from .ledger import ForecastContractError


def _probability(value: Any) -> float:
    try:
        p = float(value)
    except (TypeError, ValueError) as exc:
        raise ForecastContractError("probability must be numeric") from exc
    if not isfinite(p) or p < 0.0 or p > 1.0:
        raise ForecastContractError("probability must be in [0, 1]")
    return p


def score_binary_forecasts(rows: Iterable[dict[str, Any]], *, threshold: float = 0.5) -> dict[str, Any]:
    """Score only resolved binary forecast rows.

    Each row must contain a numeric `probability` and `actual` in {0,1}. Rows with
    `outcome_code=9` are excluded; unresolved rows never become a negative label.
    The frequency baseline is computed from the resolved sample and is reported as
    a reference, not as an independent out-of-sample estimate.
    """
    if not isfinite(threshold) or threshold < 0.0 or threshold > 1.0:
        raise ForecastContractError("threshold must be in [0, 1]")
    resolved: list[tuple[float, int]] = []
    excluded_unresolved = 0
    for row in rows:
        code = row.get("outcome_code")
        if code == 9 or row.get("status") == "UNRESOLVED":
            excluded_unresolved += 1
            continue
        actual = row.get("actual")
        if actual not in (0, 1):
            raise ForecastContractError("resolved binary row requires actual=0 or actual=1")
        resolved.append((_probability(row.get("probability")), int(actual)))
    if not resolved:
        return {
            "status": "NO_RESOLVED_FORECASTS",
            "n": 0,
            "excluded_unresolved": excluded_unresolved,
            "brier_score": None,
            "baseline_brier_score": None,
            "skill_vs_frequency_baseline": None,
            "accuracy": None,
            "calibration": [],
        }

    n = len(resolved)
    event_rate = sum(actual for _, actual in resolved) / n
    brier = sum((p - actual) ** 2 for p, actual in resolved) / n
    baseline_brier = sum((event_rate - actual) ** 2 for _, actual in resolved) / n
    skill = None if baseline_brier == 0 else 1.0 - brier / baseline_brier
    accuracy = sum((p >= threshold) == bool(actual) for p, actual in resolved) / n

    buckets: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for p, actual in resolved:
        bucket = min(9, int(p * 10))
        buckets[bucket].append((p, actual))
    calibration = []
    for bucket in sorted(buckets):
        values = buckets[bucket]
        calibration.append({
            "bucket": f"{bucket / 10:.1f}-{(bucket + 1) / 10:.1f}",
            "n": len(values),
            "mean_probability": sum(p for p, _ in values) / len(values),
            "observed_frequency": sum(actual for _, actual in values) / len(values),
        })
    return {
        "status": "SCORED",
        "n": n,
        "excluded_unresolved": excluded_unresolved,
        "event_rate": event_rate,
        "brier_score": brier,
        "baseline_brier_score": baseline_brier,
        "skill_vs_frequency_baseline": skill,
        "accuracy": accuracy,
        "calibration": calibration,
    }


__all__ = ["score_binary_forecasts"]
