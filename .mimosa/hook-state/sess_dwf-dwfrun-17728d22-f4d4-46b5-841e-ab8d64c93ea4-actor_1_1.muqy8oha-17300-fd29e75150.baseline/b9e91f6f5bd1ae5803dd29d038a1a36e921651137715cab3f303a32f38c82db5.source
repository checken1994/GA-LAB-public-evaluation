# SCP CIRCUIT: M11 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M11-closure.json)
"""
[Task 8-A] Import endpoints â€” extracted from api_server.py

Táº I SAO: api_server.py god file. TĂ¡ch 3 routes /import/* vĂ o module nĂ y.
Backward-compatible â€” public API paths/methods unchanged.

Routes:
  POST /import/jsonl   â€” Import questions from JSONL file (1 JSON per line)
  POST /import/excel   â€” Import questions from Excel/CSV file
  POST /import/batch   â€” Import batch of questions as JSON array
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, Request

# Import shared deps from api_server (same pattern as api/chat.py + admin_v98.py)
from scp.api._shared import get_judge, verify_admin
from scp.core.request_run_ledger import RequestRunLedger, traced_request

logger = logging.getLogger(__name__)


_IMPORT_ROUTES_LEDGER = RequestRunLedger()

router = APIRouter(tags=["import"])


@router.post("/import/jsonl")
@traced_request(_IMPORT_ROUTES_LEDGER, require_write=False, action="import_jsonl")
async def import_jsonl(request: Request, _admin: bool = Depends(verify_admin)):
    """Import questions from JSONL file.

    JSONL format (1 JSON per line):
      {"question": "...", "ai_answer": "...", "domain": "..."}
      {"question": "...", "ai_answer": "...", "domain": "..."}

    Returns: List of verdicts for each question.
    """
    import json as _json
    body = await request.body()
    lines = body.decode("utf-8").strip().split("\n")

    judge = get_judge()
    results = []

    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            data = _json.loads(line)
            question = data.get("question", "")
            ai_answer = data.get("ai_answer", data.get("answer", ""))
            data.get("domain", "general")

            # R9-1: judge.judge() is a long-running sync call (SLM HTTP + WHY engine +
            # governance). Calling it inline from `async def` blocks the event loop
            # for 5-30s per question; a 100-question import freezes /health, /ask,
            # WebSocket pings for 8-50 min. Run in a worker thread (non-blocking).
            v = await asyncio.to_thread(
                judge.judge, question=question, ai_answer=ai_answer, cycle_count=0
            )
            # [M11 fix AUDIT-20260909] RealityJudge.judge() returns a plain dict
            # (scp/runtime/judge.py:71 -> dict[str, Any]). The previous code read
            # `v.verdict` / `v.confidence` / `v.evidence` as ATTRIBUTES ->
            # AttributeError on EVERY question with the real judge, so every
            # import row degraded into {"error": ...} with HTTP 200
            # (fail-silently) and this endpoint never produced a verdict
            # (probe-proven at :8010 with the real judge). Same dict-contract
            # bug class already fixed for the stream path in M10.
            # The REAL dict contract is read via .get(); an attribute fallback
            # is kept ONLY for legacy result shapes (the flow_11 harness
            # predates the dict contract and is owned by another in-flight
            # stream, so it cannot be edited here) — this does not change the
            # real judge behavior, which takes the dict branch.
            if isinstance(v, dict):
                evidence = v.get("evidence") or {}
                verdict = v.get("verdict")
                confidence = v.get("confidence")
            else:  # legacy attribute-shaped result (pre-dict-contract callers)
                evidence = v.evidence or {}
                verdict = v.verdict
                confidence = v.confidence
            timings = evidence.get("v100_phase_timings") or {}
            results.append({
                "line": i + 1,
                "question": question[:100],
                "verdict": verdict,
                "confidence": confidence,
                "falsification": evidence.get("falsification_status"),
                "governance": evidence.get("governance_decision"),
                "elapsed_ms": timings.get("total_ms", 0),
            })
        except Exception as e:
            logger.warning('import_jsonl: Exception not handled: %s', e, exc_info=True)
            results.append({"line": i + 1, "error": str(e)})

    summary = {
        "total": len(results),
        "pass": sum(1 for r in results if r.get("verdict") == "PASS"),
        "fail": sum(1 for r in results if r.get("verdict") == "FAIL"),
        "unknown": sum(1 for r in results if r.get("verdict") == "UNKNOWN"),
        "errors": sum(1 for r in results if "error" in r),
    }

    return {"summary": summary, "results": results}


@router.post("/import/excel")
@traced_request(_IMPORT_ROUTES_LEDGER, require_write=False, action="import_excel")
async def import_excel(request: Request, _admin: bool = Depends(verify_admin)):
    """Import questions from Excel file (CSV format).

    CSV format:
      question,ai_answer,domain
      "TĂ­nh 2+3?","5","math"
      "Thá»§ Ä‘Ă´ VN?","HĂ  Ná»™i","geography"

    Returns: List of verdicts for each question.
    """
    import csv
    import io

    body = await request.body()
    text = body.decode("utf-8-sig")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))

    judge = get_judge()
    results = []

    for i, row in enumerate(reader, 1):
        try:
            question = row.get("question", row.get("Question", ""))
            ai_answer = row.get("ai_answer", row.get("answer", row.get("Answer", "")))
            row.get("domain", row.get("Domain", "general"))

            if not question:
                continue

            # R9-1: see import_jsonl â€” judge.judge() must run in a worker thread.
            v = await asyncio.to_thread(
                judge.judge, question=question, ai_answer=ai_answer, cycle_count=0
            )
            results.append({
                "row": i,
                "question": question[:100],
                "verdict": v.verdict,
                "confidence": v.confidence,
                "falsification": v.evidence.get("falsification_status"),
                "governance": v.evidence.get("governance_decision"),
                "elapsed_ms": v.evidence.get("v100_phase_timings", {}).get("total_ms", 0),
            })
        except Exception as e:
            logger.warning('import_excel: Exception not handled: %s', e, exc_info=True)
            results.append({"row": i, "error": str(e)})

    summary = {
        "total": len(results),
        "pass": sum(1 for r in results if r.get("verdict") == "PASS"),
        "fail": sum(1 for r in results if r.get("verdict") == "FAIL"),
        "unknown": sum(1 for r in results if r.get("verdict") == "UNKNOWN"),
        "errors": sum(1 for r in results if "error" in r),
    }

    return {"summary": summary, "results": results}


@router.post("/import/batch")
@traced_request(_IMPORT_ROUTES_LEDGER, require_write=False, action="import_batch")
async def import_batch(request: Request, _admin: bool = Depends(verify_admin)):
    """Import batch of questions as JSON array.

    Body:
      [
        {"question": "...", "ai_answer": "...", "domain": "..."},
        {"question": "...", "ai_answer": "...", "domain": "..."}
      ]

    Returns: List of verdicts.
    """
    body = await request.json()

    judge = get_judge()
    results = []

    for i, item in enumerate(body, 1):
        try:
            question = item.get("question", "")
            ai_answer = item.get("ai_answer", item.get("answer", ""))
            item.get("domain", "general")

            # R9-1: see import_jsonl â€” judge.judge() must run in a worker thread.
            v = await asyncio.to_thread(
                judge.judge, question=question, ai_answer=ai_answer, cycle_count=0
            )
            results.append({
                "item": i,
                "question": question[:100],
                "verdict": v.verdict,
                "confidence": v.confidence,
                "falsification": v.evidence.get("falsification_status"),
                "governance": v.evidence.get("governance_decision"),
                "elapsed_ms": v.evidence.get("v100_phase_timings", {}).get("total_ms", 0),
            })
        except Exception as e:
            logger.warning('import_batch: Exception not handled: %s', e, exc_info=True)
            results.append({"item": i, "error": str(e)})

    summary = {
        "total": len(results),
        "pass": sum(1 for r in results if r.get("verdict") == "PASS"),
        "fail": sum(1 for r in results if r.get("verdict") == "FAIL"),
        "unknown": sum(1 for r in results if r.get("verdict") == "UNKNOWN"),
    }

    return {"summary": summary, "results": results}
