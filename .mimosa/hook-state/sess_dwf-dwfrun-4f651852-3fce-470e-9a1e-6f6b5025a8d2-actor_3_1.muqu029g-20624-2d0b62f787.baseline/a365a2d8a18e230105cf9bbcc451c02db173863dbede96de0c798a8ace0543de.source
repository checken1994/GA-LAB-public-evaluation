from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from benchmark.run_benchmark_v2 import check_factual_correctness, fold_text

ROOT = Path(str(Path(__file__).resolve().parent.parent))
JOB = ROOT / "data" / "benchmark_batches" / "bc9dca05dfb5425081c35fb5e6fc9b0e"
questions = {}
for line in (JOB / "questions.jsonl").read_text(encoding="utf-8").splitlines():
    item = json.loads(line)
    questions[str(item.get("id"))] = item

results = []
for line in (JOB / "results.jsonl").read_text(encoding="utf-8").splitlines():
    item = json.loads(line)
    q = questions.get(str(item.get("id")), {})
    response = item.get("response") or {}
    answer = str(response.get("final_answer", "") or "")
    expected = str(q.get("expected_answer", "") or "")
    answer_type = str(q.get("answer_type", "string") or "string")
    answerable = bool(q.get("answerable", bool(expected)))
    correct, method = check_factual_correctness(answer, expected, answer_type)
    unknown_like = response.get("verdict") in {"UNKNOWN", "FAIL", "KILL", "CONFLICT"}
    if not answerable:
        unknown_like = unknown_like or any(token in fold_text(answer) for token in ("unknown", "cannot", "not enough", "unspecified", "unable"))
    results.append({
        "id": item.get("id"),
        "category": q.get("category", "unknown"),
        "answerable": answerable,
        "expected": expected,
        "answer": answer[:500],
        "correct": bool(correct) if answerable else None,
        "safe_unknown": bool(unknown_like) if not answerable else None,
        "method": method,
        "verdict": response.get("verdict"),
        "latency_ms": float(response.get("elapsed_ms", 0) or 0),
        "provider": ((response.get("slm_trace") or [{}])[0] or {}).get("slm_name"),
        "web_fallback_used": bool(response.get("web_fallback_used")),
    })

answerable_rows = [row for row in results if row["answerable"]]
ambiguous_rows = [row for row in results if not row["answerable"]]
correct = sum(1 for row in answerable_rows if row["correct"])
safe = sum(1 for row in ambiguous_rows if row["safe_unknown"])
latencies = [row["latency_ms"] for row in results if row["latency_ms"] > 0]
by_category = defaultdict(lambda: {"n": 0, "correct": 0, "safe_unknown": 0, "latencies": []})
for row in results:
    bucket = by_category[row["category"]]
    bucket["n"] += 1
    bucket["latencies"].append(row["latency_ms"])
    if row["answerable"]:
        bucket["correct"] += int(row["correct"])
    else:
        bucket["safe_unknown"] += int(row["safe_unknown"])

summary = {
    "job_id": JOB.name,
    "total": len(results),
    "answerable": len(answerable_rows),
    "factual_accuracy": round(correct / len(answerable_rows), 4) if answerable_rows else None,
    "ambiguous": len(ambiguous_rows),
    "ambiguous_safe_unknown_rate": round(safe / len(ambiguous_rows), 4) if ambiguous_rows else None,
    "evidence_recall": None,
    "evidence_note": "N/A for benchmark-fast: verification deferred and no independent retrieved evidence is counted.",
    "self_correction": None,
    "self_correction_note": "N/A: this batch was not run with corrupted_answer injection.",
    "latency_ms": {
        "mean": round(statistics.mean(latencies), 2) if latencies else None,
        "p50": round(statistics.median(latencies), 2) if latencies else None,
        "max": round(max(latencies), 2) if latencies else None,
    },
    "providers": dict(Counter(str(row["provider"]) for row in results)),
    "web_fallback_count": sum(row["web_fallback_used"] for row in results),
    "by_category": {
        category: {
            "n": bucket["n"],
            "factual_accuracy": round(bucket["correct"] / bucket["n"], 4) if category != "ambiguous" else None,
            "safe_unknown_rate": round(bucket["safe_unknown"] / bucket["n"], 4) if category == "ambiguous" else None,
            "mean_latency_ms": round(statistics.mean(bucket["latencies"]), 2) if bucket["latencies"] else None,
        }
        for category, bucket in sorted(by_category.items())
    },
    "failure_samples": [row for row in results if row["answerable"] and not row["correct"]][:20],
}
output = JOB / "replay_metrics.json"
output.write_text(json.dumps({"summary": summary, "rows": results}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
print(f"saved={output}")
