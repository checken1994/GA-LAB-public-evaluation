"""Step 5: Benchmark suite for SCP LLM Gateway.

Runs MMLU (sample), GSM-8K (sample), and Code-generation tasks across
all configured providers. Saves results as CSV in benchmarks/results/.

Usage:
    python -m scp.benchmark.benchmark_suite
    python -m scp.benchmark.benchmark_suite --tasks mmlu gsm8k
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("scp.benchmark")

# Minimal sample questions per task type
BENCHMARK_TASKS = {
    "mmlu": [
        {"q": "What is the capital of France?", "expected_contains": "Paris"},
        {"q": "What is 2 + 2?", "expected_contains": "4"},
        {"q": "What element has atomic number 1?", "expected_contains": "hydrogen"},
    ],
    "gsm8k": [
        {"q": "If a train travels 60 km/h for 2 hours, how far does it go?", "expected_contains": "120"},
        {"q": "A store has 50 apples. If 20 are sold, how many remain?", "expected_contains": "30"},
    ],
    "codegen": [
        {"q": "Write a Python function that returns the sum of a list of numbers.", "expected_contains": "def"},
        {"q": "Write a Python one-liner to reverse a string s.", "expected_contains": "[::-1]"},
    ],
}

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "benchmarks" / "results"


async def run_benchmark_task(gateway, task_name: str, question: str, expected: str) -> dict:
    start = time.monotonic()
    answer, provider = await gateway.chat(question, task="coding" if task_name == "codegen" else "default")
    latency_ms = (time.monotonic() - start) * 1000
    success = bool(answer and expected.lower() in answer.lower())
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "task": task_name,
        "provider": provider,
        "question": question[:80],
        "latency_ms": round(latency_ms, 2),
        "success": success,
        "answer_len": len(answer) if answer else 0,
    }


async def run_all(task_filter: list[str] | None = None) -> list[dict]:
    from scp.llm_gateway.client import get_gateway
    gateway = get_gateway()
    results = []
    tasks_to_run = task_filter or list(BENCHMARK_TASKS.keys())
    for task_name in tasks_to_run:
        questions = BENCHMARK_TASKS.get(task_name, [])
        for item in questions:
            result = await run_benchmark_task(gateway, task_name, item["q"], item["expected_contains"])
            results.append(result)
            logger.info("[benchmark] %s | %s | %s | %.1fms | success=%s",
                       task_name, result["provider"], item["q"][:40], result["latency_ms"], result["success"])
    return results


def save_results(results: list[dict]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"benchmark_{ts}.csv"
    if not results:
        return path
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    logger.info("[benchmark] results saved to %s", path)
    return path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="SCP Benchmark Suite")
    parser.add_argument("--tasks", nargs="*", choices=list(BENCHMARK_TASKS.keys()), help="Tasks to benchmark")
    parser.add_argument("--output-json", action="store_true", help="Print results as JSON")
    args = parser.parse_args()

    results = asyncio.run(run_all(args.tasks))
    path = save_results(results)

    total = len(results)
    passed = sum(1 for r in results if r["success"])
    avg_ms = sum(r["latency_ms"] for r in results) / total if total else 0
    print("\n=== SCP Benchmark Results ===")
    print(f"Total: {total} | Passed: {passed} | Failed: {total - passed} | Avg latency: {avg_ms:.1f}ms")
    print(f"Results: {path}")

    if args.output_json:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
