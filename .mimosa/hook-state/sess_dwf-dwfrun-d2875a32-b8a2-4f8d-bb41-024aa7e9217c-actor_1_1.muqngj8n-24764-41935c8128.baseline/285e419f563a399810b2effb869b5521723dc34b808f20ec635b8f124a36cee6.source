# SCP CIRCUIT: M10 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M10-closure.json)
"""
SCP V105 â€” Streaming /ask endpoint (real-time response)

LIVE ROUTE â€” registered by api_server.py. This router is live and
already wired by the app. The route
below (`POST /v105/ask/stream`) is reachable at runtime â€” calling it
through the gateway returns a streamed response.

The older WIP/dead-route note is historical and no longer describes the
current app wiring. See `scp/api/routes/README.md` only for route inventory.

[LIVE-FIX] Streaming response cho /ask:
- POST /v105/ask/stream â€” streaming verdict (real-time)

Registration is already active:
    # In scp/api_server.py (around line 540, where other v105 routers are
    # registered):
    from scp.api.routes.stream_routes import router as stream_router
    app.include_router(stream_router)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from scp.api._shared import verify_admin

logger = logging.getLogger("scp.api.stream")

from scp.core.request_run_ledger import RequestRunLedger, traced_request

_STREAM_ROUTES_LEDGER = RequestRunLedger()

router = APIRouter(tags=["stream"])


class StreamAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    ai_answer: str = Field("", max_length=10000)


@router.post("/v105/ask/stream", dependencies=[Depends(verify_admin)])
@traced_request(_STREAM_ROUTES_LEDGER, require_write=False, action="ask_stream")
async def ask_stream(req: StreamAskRequest):
    """Streaming /ask â€” tráº£ verdict tá»«ng bÆ°á»›c real-time."""

    async def generate():
        try:
            # Step 1: Classify
            yield f"data: {json.dumps({'step': 'classify', 'status': 'running', 'ts': time.time()})}\n\n"

            from scp.api._shared import get_judge
            judge = get_judge()

            from scp.core.smart_classifier import SmartClassifier
            classifier = SmartClassifier()
            classification = classifier.classify(req.question)

            yield f"data: {json.dumps({'step': 'classify', 'status': 'done', 'domain': classification.domain, 'confidence': classification.confidence, 'method': classification.method})}\n\n"

            # Step 2: SLM predict
            yield f"data: {json.dumps({'step': 'slm_predict', 'status': 'running', 'ts': time.time()})}\n\n"

            # Step 3: Judge (full pipeline)
            yield f"data: {json.dumps({'step': 'judge', 'status': 'running', 'ts': time.time()})}\n\n"

            # The judge pipeline is synchronous and can perform CPU/network
            # work. Run it off the event loop so SSE heartbeats and other
            # requests remain responsive while the verdict is computed.
            verdict = await asyncio.to_thread(
                judge.judge, req.question, req.ai_answer, cycle_count=0
            )

            # [M10-FIX / AUDIT-20260909] RealityJudge.judge() returns a plain
            # dict (scp/runtime/judge.py: keys verdict/confidence/reasoning/
            # final_answer/evidence/...). This route previously read
            # `verdict.verdict` etc. as ATTRIBUTES -> AttributeError on every
            # request -> the stream always ended in `step: error` and the
            # `judge done` + `final` frames were never emitted. Read the real
            # dict contract; `domain` comes from the classify step (the judge
            # result carries no domain key). Any contract drift now fails
            # loudly through the existing step:error branch, not silently.
            reasoning = verdict.get("reasoning") or ""
            evidence = verdict.get("evidence")
            if not isinstance(evidence, dict):
                evidence = {}

            yield f"data: {json.dumps({'step': 'judge', 'status': 'done', 'verdict': verdict.get('verdict'), 'confidence': verdict.get('confidence'), 'domain': classification.domain, 'reasoning': reasoning[:200]})}\n\n"

            # Final
            result = {
                "step": "final",
                "status": "complete",
                "question": req.question,
                "verdict": verdict.get("verdict"),
                "confidence": verdict.get("confidence"),
                "domain": classification.domain,
                "final_answer": verdict.get("final_answer"),
                "reasoning": reasoning,
                "evidence": evidence,
            }
            yield f"data: {json.dumps(result)}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'step': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
