from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from question_generator import generate_random_questions
from run_benchmark_v2 import (
    check_factual_correctness,
    classify_attack_result,
    compute_all_metrics_v2,
    compute_claim_hallucination,
    compute_evidence_metrics,
    extract_claims_from_answer,
    post_with_retry,
)


def eval_question(url: str, headers: dict[str, str], q: dict[str, Any], inject: bool) -> dict[str, Any]:
    started = time.time()
    question = q.get("question", "")
    expected = q.get("expected_answer", "")
    answerable = q.get("answerable", True)
    corrupted = q.get("corrupted_answer", "")
    injected = corrupted if inject and corrupted and answerable else ""
    base = {
        "id": q.get("id", "?"),
        "category": q.get("category", "unknown"),
        "question": question,
        "expected_answer": expected,
        "answer_type": q.get("answer_type", "string"),
        "answerable": answerable,
        "gold_evidence": q.get("gold_evidence", []),
        "corrupted_answer": corrupted,
        "ai_answer_injected": injected,
    }
    try:
        response = post_with_retry(
            f"{url}/ask",
            {"question": question, "ai_answer": injected, "source": "benchmark_v2_parallel"},
            headers,
        )
        elapsed = round((time.time() - started) * 1000, 2)
        if response.status_code != 200:
            return {**base, "correct": False, "error": f"HTTP {response.status_code}", "latency_ms": elapsed}
        data = response.json()
        answer = data.get("final_answer", "")
        verdict = data.get("verdict", "")
        correct, method = check_factual_correctness(answer, expected, base["answer_type"])
        trace = data.get("slm_trace") or []
        claims = extract_claims_from_answer(answer, question)
        return {
            **base,
            "correct": correct,
            "match_method": method,
            "verdict": verdict,
            "confidence": data.get("confidence", 0),
            "scp_answer": str(answer)[:500],
            "latency_ms": elapsed,
            "claim_analysis": compute_claim_hallucination(claims, base["gold_evidence"], trace),
            "evidence_metrics": compute_evidence_metrics(trace, base["gold_evidence"]),
            "response": data,
        }
    except Exception as exc:
        return {**base, "correct": False, "error": str(exc), "latency_ms": round((time.time() - started) * 1000, 2)}


def eval_attack(url: str, headers: dict[str, str], attack: dict[str, Any]) -> dict[str, Any]:
    started = time.time()
    base = {"id": attack.get("id", "?"), "category": attack.get("category", "unknown"), "attack_text": attack.get("attack_text", ""), "expected_block": attack.get("expected_block", True)}
    try:
        response = post_with_retry(f"{url}/ask", {"question": base["attack_text"], "source": "benchmark_v2_parallel_attack"}, headers)
        data = response.json() if response.content else {}
        verdict = data.get("verdict", "")
        return {**base, "http_status": response.status_code, "verdict": verdict, "classification": classify_attack_result(response.status_code, verdict, None), "latency_ms": round((time.time() - started) * 1000, 2), "response": data}
    except Exception as exc:
        error = str(exc)
        classification = "TIMEOUT" if "timeout" in error.lower() else "ERROR"
        return {**base, "http_status": 0, "verdict": "", "classification": classification, "latency_ms": round((time.time() - started) * 1000, 2), "error": error}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--questions-output", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-math", type=int, default=400)
    parser.add_argument("--num-geography", type=int, default=400)
    parser.add_argument("--num-ambiguous", type=int, default=200)
    parser.add_argument("--num-attacks", type=int, default=20)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--no-corruption", action="store_true")
    args = parser.parse_args()

    workers = max(1, min(args.workers, 8))
    questions, attacks = generate_random_questions(args.num_math, args.num_geography, args.num_ambiguous, args.num_attacks, args.seed)
    Path(args.questions_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.questions_output).write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in questions) + "\n", encoding="utf-8")
    import requests
    admin_key = os.environ.get("SCP_ADMIN_KEY", "admin")
    try:
        auth_res = requests.post(f"{args.url}/auth/token", json={"admin_key": admin_key}, timeout=5)
        auth_res.raise_for_status()
        access_token = auth_res.json()["access_token"]
    except Exception as e:
        print(f"Warning: Failed to fetch auth token, proceeding without it: {e}")
        access_token = "dummy"
    headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}
    started = time.time()
    question_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(eval_question, args.url, headers, q, not args.no_corruption) for q in questions]
        for index, future in enumerate(as_completed(futures), 1):
            question_results.append(future.result())
            if index % 50 == 0:
                print(f"progress_questions={index}/{len(questions)}", flush=True)
    attack_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(workers, 4)) as pool:
        futures = [pool.submit(eval_attack, args.url, headers, attack) for attack in attacks]
        for index, future in enumerate(as_completed(futures), 1):
            attack_results.append(future.result())
            if index % 10 == 0:
                print(f"progress_attacks={index}/{len(attacks)}", flush=True)
    metrics = compute_all_metrics_v2(question_results, attack_results)
    output = {
        "version": "v2-parallel",
        "timestamp": time.time(),
        "iso_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "url": args.url,
        "mode": "random",
        "seed": args.seed,
        "question_counts": {"math": args.num_math, "geography": args.num_geography, "ambiguous": args.num_ambiguous, "attacks": args.num_attacks},
        "workers": workers,
        "metrics": metrics,
        "question_results": question_results,
        "attack_results": attack_results,
        "elapsed_seconds": round(time.time() - started, 2),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"complete_questions={len(question_results)}|complete_attacks={len(attack_results)}|elapsed_seconds={output['elapsed_seconds']}")
    print(json.dumps(metrics, ensure_ascii=False, default=str))
    print(f"results={out}")


if __name__ == "__main__":
    main()
