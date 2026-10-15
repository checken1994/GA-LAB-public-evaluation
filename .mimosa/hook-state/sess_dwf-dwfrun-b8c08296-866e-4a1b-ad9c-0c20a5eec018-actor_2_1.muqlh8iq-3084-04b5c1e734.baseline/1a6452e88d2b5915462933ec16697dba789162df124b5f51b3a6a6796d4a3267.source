from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def contexts_from_runtime(record: dict) -> list[str]:
    observed = record.get("evidence_observed") or {}
    result: list[str] = []
    for item in observed.get("items", []):
        value = item.get("value")
        if isinstance(value, str) and len(value.strip()) >= 20:
            result.append(value.strip())
        elif isinstance(value, list):
            for nested in value:
                if isinstance(nested, str) and len(nested.strip()) >= 20:
                    result.append(nested.strip())
                elif isinstance(nested, dict):
                    for key in ("text", "content", "evidence", "citation", "output", "result", "message", "summary"):
                        value2 = nested.get(key)
                        if isinstance(value2, str) and len(value2.strip()) >= 20:
                            result.append(value2.strip())
    return list(dict.fromkeys(result))


def build_admission(runtime_rows: list[dict], gold_rows: dict[str, dict]) -> tuple[list[dict], Counter]:
    admitted = []
    excluded: Counter = Counter()
    for runtime in runtime_rows:
        qid = runtime.get("question_id")
        gold = gold_rows.get(qid or "")
        if runtime.get("http_status") != 200:
            excluded["runtime_http_not_200"] += 1
            continue
        if not gold:
            excluded["gold_row_missing"] += 1
            continue
        if gold.get("eligible_for_ragas") is not True:
            excluded["gold_not_verified_or_not_eligible"] += 1
            continue
        if gold.get("review_status") not in {"HUMAN_VERIFIED", "INDEPENDENT_LLM_REVIEWED"}:
            excluded["gold_review_status_not_verified"] += 1
            continue
        answer = str((runtime.get("response_json") or {}).get("final_answer") or "").strip()
        contexts = contexts_from_runtime(runtime)
        ground_truth = str(gold.get("reviewed_answer") or gold.get("gold_answer") or "").strip()
        if not answer:
            excluded["runtime_answer_empty"] += 1
            continue
        if not contexts:
            excluded["runtime_contexts_empty"] += 1
            continue
        if not ground_truth:
            excluded["ground_truth_empty"] += 1
            continue
        admitted.append({"question": runtime.get("question", ""), "answer": answer, "contexts": contexts, "ground_truth": ground_truth, "question_id": qid})
    return admitted, excluded


def run(args: argparse.Namespace) -> dict:
    runtime_path = Path(args.runtime).resolve()
    gold_path = Path(args.gold).resolve()
    output_path = Path(args.output).resolve()
    runtime_rows = read_jsonl(runtime_path)
    gold_rows = {row["question_id"]: row for row in read_jsonl(gold_path)}
    admitted, excluded = build_admission(runtime_rows, gold_rows)
    report = {
        "schema_version": "phase3-ragas-v2-result",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_method": "official_ragas_evaluate_only",
        "ragas_version": package_version("ragas"),
        "datasets_version": package_version("datasets"),
        "langchain_openai_version": package_version("langchain-openai"),
        "model_id": args.model,
        "runtime_input_path": str(runtime_path),
        "runtime_input_sha256": sha256(runtime_path),
        "gold_input_path": str(gold_path),
        "gold_input_sha256": sha256(gold_path),
        "runtime_rows_seen": len(runtime_rows),
        "gold_rows_seen": len(gold_rows),
        "rows_admitted": len(admitted),
        "rows_excluded_by_reason": dict(excluded),
        "metrics_requested": ["faithfulness", "context_precision", "context_recall", "answer_relevancy", "answer_correctness"],
        "proxy_fallback_used": False,
        "score_release_allowed": False,
        "raw_judge_artifacts": [],
        "provider": {"openai_api_base_present": bool(os.environ.get("OPENAI_API_BASE")), "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY"))},
    }
    if not admitted:
        report["status"] = "BLOCKED_NO_VERIFIED_ROWS"
        report["blocked_reason"] = "No runtime row is paired with a Gold row carrying verified review provenance and eligible_for_ragas=true. Ragas evaluate() was not called; no score exists."
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return report

    try:
        from datasets import Dataset
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas import evaluate
        from ragas.metrics import answer_correctness, answer_relevancy, context_precision, context_recall, faithfulness
    except Exception as exc:
        report["status"] = "BLOCKED_RAGAS_IMPORT_ERROR"
        report["blocked_reason"] = f"{type(exc).__name__}: {str(exc)[:1000]}"
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return report

    dataset = Dataset.from_list([{key: row[key] for key in ("question", "answer", "contexts", "ground_truth")} for row in admitted])
    llm = ChatOpenAI(model=args.model, temperature=0, max_tokens=args.max_tokens)
    embeddings = OpenAIEmbeddings(model=args.embedding_model)
    try:
        result = evaluate(dataset, metrics=[faithfulness, context_precision, context_recall, answer_relevancy, answer_correctness], llm=llm, embeddings=embeddings, is_async=False, raise_exceptions=True)
        report["status"] = "RAGAS_EVALUATED"
        report["score_release_allowed"] = True
        report["rows_scored"] = len(admitted)
        report["scores"] = result.to_pandas().to_dict(orient="records")
    except Exception as exc:
        report["status"] = "BLOCKED_RAGAS_RUNTIME_ERROR"
        report["blocked_reason"] = f"{type(exc).__name__}: {str(exc)[:1000]}"
        report["rows_scored"] = 0
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run official Ragas only after verified Gold admission")
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--gold", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--max-tokens", type=int, default=1200)
    args = parser.parse_args()
    report = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
