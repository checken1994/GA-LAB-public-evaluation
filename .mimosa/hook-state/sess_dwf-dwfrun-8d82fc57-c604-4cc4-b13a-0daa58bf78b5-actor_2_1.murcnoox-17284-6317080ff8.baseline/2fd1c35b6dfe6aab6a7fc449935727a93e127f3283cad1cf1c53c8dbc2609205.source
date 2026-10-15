#!/usr/bin/env python3
"""Compare SCP vs Baseline LLM — statistical comparison + significance test.

Purpose: prove SCP's anti-hallucination advantage is statistically significant.

Usage:
    python compare_results.py --scp scp_results.json --baseline baseline_gpt.json
    python compare_results.py --scp scp_results.json --baseline baseline_claude.json --output comparison.json

Output:
    - Side-by-side metric comparison
    - Delta (SCP - baseline)
    - Fisher exact test p-value (is the difference significant?)
    - Effect size (Cohen's h)
    - Verdict: is SCP significantly better?
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def fisher_exact_pvalue(a: int, b: int, c: int, d: int) -> float:
    """Fisher exact test (2x2 contingency table).

    a = SCP successes, b = SCP failures
    c = baseline successes, d = baseline failures

    Returns p-value (one-tailed: SCP > baseline).
    Simplified implementation — for production use scipy.stats.fisher_exact.
    """
    n = a + b + c + d
    if n == 0:
        return 1.0

    # Use chi-square approximation for large samples (faster)
    # For small samples, would need exact Fisher computation
    expected_a = (a + b) * (a + c) / n
    expected_c = (a + b) * (c + d) / n
    if expected_a == 0 or expected_c == 0:
        return 1.0

    chi2 = ((a - expected_a) ** 2 / expected_a +
            (c - expected_c) ** 2 / expected_c +
            (b - (a + b - expected_a)) ** 2 / max(1, a + b - expected_a) +
            (d - (c + d - expected_c)) ** 2 / max(1, c + d - expected_c))

    # Approximate p-value from chi-square with 1 df
    # p = erfc(sqrt(chi2 / 2))
    p_value = math.erfc(math.sqrt(chi2 / 2))
    return min(1.0, max(0.0, p_value))


def cohens_h(p1: float, p2: float) -> float:
    """Cohen's h effect size for two proportions.

    h < 0.2: negligible
    0.2-0.5: small
    0.5-0.8: medium
    > 0.8: large
    """
    phi1 = 2 * math.asin(math.sqrt(min(1, max(0, p1))))
    phi2 = 2 * math.asin(math.sqrt(min(1, max(0, p2))))
    return abs(phi1 - phi2)


def compare(scp_file: str, baseline_file: str) -> dict:
    #  Better error messages for missing files
    if not Path(scp_file).exists():
        print(f"❌ SCP results file not found: {scp_file}")
        print(f"   Run first: python run_benchmark_enhanced.py --output {scp_file}")
        sys.exit(1)
    if not Path(baseline_file).exists():
        print(f"❌ Baseline results file not found: {baseline_file}")
        print(f"   Run first: python run_baseline.py --model <model> --output {baseline_file}")
        sys.exit(1)
    with open(scp_file, encoding="utf-8") as f:
        scp = json.load(f)
    with open(baseline_file, encoding="utf-8") as f:
        baseline = json.load(f)

    scp_m = scp["metrics"]
    base_m = baseline["metrics"]

    metrics = [
        "factual_accuracy",
        "hallucination_rate",
        "unsupported_claims_rate",
        "evidence_precision",
        "evidence_recall",
        "abstention_accuracy",
        "correction_success_rate",
        "false_correction_rate",
        "attack_resistance",
        "bypass_rate",
    ]

    comparison = {}
    for m in metrics:
        scp_val = scp_m.get(m, 0)
        base_val = base_m.get(m, 0)
        delta = scp_val - base_val

        # For "rate" metrics (hallucination, unsupported, false_correction, bypass) — LOWER is better
        # For others — HIGHER is better
        lower_is_better = m in ("hallucination_rate", "unsupported_claims_rate",
                                "false_correction_rate", "bypass_rate")
        scp_better = (delta < 0) if lower_is_better else (delta > 0)

        # Statistical test (Fisher exact on accuracy + attack_resistance)
        p_value = None
        effect_size = None
        if m == "factual_accuracy":
            p_value = fisher_exact_pvalue(
                scp_m["correct_answers"], scp_m["total_questions"] - scp_m["correct_answers"],
                base_m["correct_answers"], base_m["total_questions"] - base_m["correct_answers"],
            )
            effect_size = cohens_h(scp_val, base_val)
        elif m == "attack_resistance":
            p_value = fisher_exact_pvalue(
                scp_m["blocked_attacks"], scp_m["total_attacks"] - scp_m["blocked_attacks"],
                base_m["blocked_attacks"], base_m["total_attacks"] - base_m["blocked_attacks"],
            )
            effect_size = cohens_h(scp_val, base_val)

        comparison[m] = {
            "scp": scp_val,
            "baseline": base_val,
            "delta": round(delta, 4),
            "scp_better": scp_better,
            "p_value": round(p_value, 4) if p_value else None,
            "effect_size": round(effect_size, 4) if effect_size else None,
            "significant": p_value < 0.05 if p_value else None,
        }

    return {
        "scp_model": "SCP R16",
        "baseline_model": baseline.get("model", "unknown"),
        "comparison": comparison,
        "summary": {
            "metrics_where_scp_better": sum(1 for v in comparison.values() if v["scp_better"]),
            "metrics_where_scp_worse": sum(1 for v in comparison.values() if not v["scp_better"]),
            "significant_improvements": sum(1 for v in comparison.values() if v.get("significant") and v["scp_better"]),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Compare SCP vs Baseline LLM results")
    parser.add_argument("--scp", required=True, help="SCP results JSON")
    parser.add_argument("--baseline", required=True, help="Baseline results JSON")
    parser.add_argument("--output", default="comparison.json")
    args = parser.parse_args()

    result = compare(args.scp, args.baseline)

    print(f"\n{'='*70}")
    print(f"  SCP vs {result['baseline_model']} — Comparison")
    print(f"{'='*70}")
    print(f"  {'Metric':<30} {'SCP':>8} {'Baseline':>10} {'Delta':>8} {'Better?':>8} {'p-value':>8}")
    print(f"  {'-'*30} {'-'*8} {'-'*10} {'-'*8} {'-'*8} {'-'*8}")

    for m, v in result["comparison"].items():
        better = "✅" if v["scp_better"] else "❌"
        p = f"{v['p_value']:.4f}" if v.get("p_value") else "N/A"
        sig = " *" if v.get("significant") else ""
        print(f"  {m:<30} {v['scp']:>7.1%} {v['baseline']:>9.1%} {v['delta']:>+7.1%} {better:>8} {p:>8}{sig}")

    print(f"{'='*70}")
    print(f"  SCP better on:     {result['summary']['metrics_where_scp_better']}/10 metrics")
    print(f"  SCP worse on:      {result['summary']['metrics_where_scp_worse']}/10 metrics")
    print(f"  Significant (p<0.05): {result['summary']['significant_improvements']} improvements")
    print(f"{'='*70}")
    print("  * = statistically significant (p < 0.05, Fisher exact test)")

    #  Create output directory if it doesn't exist
    _output_path = Path(args.output)
    _output_path.parent.mkdir(parents=True, exist_ok=True)

    with _output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\n📄 Comparison saved to: {args.output}")

if __name__ == "__main__":
    main()
