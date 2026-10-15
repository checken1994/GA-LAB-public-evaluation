import datetime
import json
import time
import os
from pathlib import Path

import requests

ROOT = Path(os.environ.get("SCP_ROOT", Path(__file__).resolve().parents[1]))
SRC = ROOT / "data" / "benchmark_batches" / "cc047e32d62448678a773738abe08833" / "questions.jsonl"
SEED_V1 = ROOT / "reports" / "SCP_FULL_RUNTIME_RAG_1000_2026-08-17.jsonl"
SEED_V2 = ROOT / "reports" / "SCP_FULL_RUNTIME_RAG_1000_RETRY_V2_2026-08-17.jsonl"
OUT = ROOT / "reports" / "SCP_FULL_RUNTIME_RAG_1000_RETRY_V3_2026-08-17.jsonl"
SCP_INTERNAL_URL = os.environ.get("SCP_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
HEALTH_URL = SCP_INTERNAL_URL + "/health"
ASK_URL = SCP_INTERNAL_URL + "/ask"
MAX_REQUEST_ATTEMPTS = 3
MAX_ROUNDS = 8
HEALTH_WAIT_SECONDS = 45
REQUEST_TIMEOUT_SECONDS = 300


def load_jsonl(path):
    result = []
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            result.append(json.loads(line))
        except Exception:
            pass
    return result


def is_terminal_result(row):
    """A parsed HTTP-200 API result is terminal even when governance is UNKNOWN."""
    return row.get("http_status") == 200 and bool(row.get("verdict")) and bool(row.get("run_status"))


def health_wait(session, max_wait=HEALTH_WAIT_SECONDS):
    deadline = time.monotonic() + max_wait
    last_error = None
    while time.monotonic() < deadline:
        try:
            response = session.get(HEALTH_URL, timeout=10)
            if response.status_code == 200:
                return True, None
            last_error = f"health_http_{response.status_code}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {str(exc)[:180]}"
        time.sleep(3)
    return False, last_error


def call_one(session, question):
    qid = question.get("id") or question.get("question_id")
    body = {
        "question": question.get("question", ""),
        "domain": question.get("domain", "general"),
        "rag_enabled": True,
        "return_evidence": True,
        "include_sources": True,
    }
    transient_errors = []
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
        healthy, health_error = health_wait(session)
        if not healthy:
            transient_errors.append({"attempt": attempt, "phase": "health", "error": health_error})
            time.sleep(min(10 * attempt, 30))
            continue
        try:
            response = session.post(ASK_URL, json=body, timeout=REQUEST_TIMEOUT_SECONDS)
            payload = response.json()
            record = {
                "question_id": qid,
                "question": question.get("question", ""),
                "started_at": started,
                "http_status": response.status_code,
                "verdict": payload.get("verdict"),
                "run_status": payload.get("run_status"),
                "confidence": payload.get("confidence"),
                "governance_decision": payload.get("governance_decision"),
                "final_answer": payload.get("final_answer"),
                "run_id": payload.get("run_id"),
                "trace_id": payload.get("trace_id"),
                "elapsed_ms": payload.get("elapsed_ms"),
                "v100_claims": payload.get("v100_claims"),
                "error": None,
                "request_attempts": attempt,
                "transient_errors": transient_errors,
                "runner_version": "resilient-v3",
            }
            if is_terminal_result(record):
                return record
            transient_errors.append({"attempt": attempt, "phase": "application", "error": f"invalid_payload_http_{response.status_code}"})
        except Exception as exc:
            transient_errors.append({"attempt": attempt, "phase": "request", "error": f"{type(exc).__name__}: {str(exc)[:220]}"})
        time.sleep(min(5 * attempt, 20))
    return {
        "question_id": qid,
        "question": question.get("question", ""),
        "started_at": started,
        "http_status": None,
        "verdict": "REQUEST_ERROR",
        "run_status": "ERROR",
        "confidence": None,
        "governance_decision": None,
        "final_answer": None,
        "run_id": None,
        "trace_id": None,
        "elapsed_ms": None,
        "v100_claims": None,
        "error": "retry_exhausted",
        "request_attempts": MAX_REQUEST_ATTEMPTS,
        "transient_errors": transient_errors,
        "runner_version": "resilient-v3",
    }


def main():
    questions = load_jsonl(SRC)
    records = {}
    for seed_path in (SEED_V1, SEED_V2):
        for row in load_jsonl(seed_path):
            qid = row.get("question_id")
            if qid and is_terminal_result(row):
                records[qid] = row
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUT.exists():
        with OUT.open("w", encoding="utf-8") as handle:
            for row in records.values():
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    pending = [q for q in questions if (q.get("id") or q.get("question_id")) not in records]
    session = requests.Session()
    print(json.dumps({"input": len(questions), "seed_terminal": len(records), "pending": len(pending), "output": str(OUT)}, ensure_ascii=False), flush=True)
    for round_no in range(1, MAX_ROUNDS + 1):
        if not pending:
            break
        next_pending = []
        for index, question in enumerate(pending, 1):
            record = call_one(session, question)
            qid = record["question_id"]
            with OUT.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
            if is_terminal_result(record):
                records[qid] = record
            else:
                next_pending.append(question)
            if index % 10 == 0 or index == len(pending):
                print(json.dumps({"round": round_no, "processed_round": index, "pending_round": len(pending), "terminal_total": len(records), "retry_pending": len(next_pending)}, ensure_ascii=False), flush=True)
        pending = next_pending
        if pending:
            healthy, error = health_wait(session, HEALTH_WAIT_SECONDS)
            print(json.dumps({"round_complete": round_no, "retry_pending": len(pending), "health": healthy, "health_error": error}, ensure_ascii=False), flush=True)
            time.sleep(10)
    print(json.dumps({"total_input": len(questions), "terminal_total": len(records), "unresolved": len(pending), "output": str(OUT)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
