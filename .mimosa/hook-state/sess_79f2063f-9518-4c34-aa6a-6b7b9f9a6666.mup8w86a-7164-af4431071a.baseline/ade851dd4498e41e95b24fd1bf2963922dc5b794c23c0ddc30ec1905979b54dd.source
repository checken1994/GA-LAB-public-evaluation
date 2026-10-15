# SCP CIRCUIT: M03 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M03-closure.json)
"""
[Task 8-A] OpenAI-compatible endpoints â€” extracted from api_server.py

Táº I SAO: api_server.py 2,144 LOC god file. TĂ¡ch 2 routes /v1/* vĂ o module
nĂ y cho PyRIT/garak integration tests. Backward-compatible â€” public API
paths/methods unchanged.

Routes:
  POST /v1/chat/completions   â€” OpenAI-compatible chat (PyRIT/garak target)
  GET  /v1/models             â€” OpenAI models list
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

# Import shared deps from api_server (same pattern as api/chat.py + admin_v98.py)
# [BLE001-fix] logger được định nghĩa local (cùng singleton "scp.api" như
# scp.api._shared) để ruff resolve được logging call trong except handler.
from scp.api._shared import _extract_v98_context, get_judge
from scp.security.jwt_guard import get_current_user

logger = logging.getLogger("scp.api")
from scp.core.release_identity import CANONICAL_MODEL_ID, model_id_candidates
from scp.core.request_run_ledger import RequestRunLedger, traced_request

_OPENAI_COMPAT_LEDGER = RequestRunLedger()

router = APIRouter(tags=["openai-compat"])

# [M03-STUB-VISIBILITY 2026-09-26] TẠI SAO: /v1/chat/completions hiện KHÔNG
# sinh câu trả lời bằng LLM — nó chạy judge với ai_answer='' (known gap M03,
# M03-closure.json: CLOSED_WITH_KNOWN_GAP). PyRIT/garak consumers previously
# could mistake the canned/refusal-shaped completion for real generation.
# Minimal fix (không xây feature): mark rõ stub — top-level "warning" field +
# response header "x-scp-stub: true" + WARNING đúng 1 lần mỗi process.
_STUB_WARNING = "openai_compat stub: no LLM generation performed (M03 gap)"
_STUB_WARNING_LOGGED = False
_STUB_WARNING_LOCK = threading.Lock()


def _log_stub_warning_once() -> None:
    """Emit the stub WARNING exactly once per process (no per-request spam)."""
    global _STUB_WARNING_LOGGED
    with _STUB_WARNING_LOCK:
        if not _STUB_WARNING_LOGGED:
            _STUB_WARNING_LOGGED = True
            logger.warning("[openai_compat] %s", _STUB_WARNING)


@router.post("/v1/chat/completions")
@traced_request(_OPENAI_COMPAT_LEDGER, require_write=False, action="openai_chat")
async def openai_chat(request: Request, response: Response, current_user: str = Depends(get_current_user)):
    """OpenAI-compatible endpoint â€” PyRIT/garak gá»i endpoint nĂ y.

    Extracts user message â†’ runs V98 pipeline â†’ returns OpenAI-format response.
    `response: Response` được FastAPI DI cung cấp để gắn header stub mà vẫn
    trả plain dict (traced_request.attach phải inject run_status/ledger_status
    vào body — trả JSONResponse sẽ làm mất chúng, gãy ledger contract).
    """
    # [SCP-DNA-FIX 4-a-007] Capture _t0 at the very START of the handler.
    # Táº I SAO: previously `elapsed_ms` was computed as
    # `round((time.time() - v98_context.get("_t0", time.time())) * 1000, 1)`,
    # but `_t0` was NEVER set in v98_context (both _shared._extract_v98_context
    # and helpers._extract_v98_context omit it). The fallback `time.time()`
    # was evaluated at the same moment as the subtraction's left operand â†’
    # elapsed_ms â‰ˆ 0 always (DNA #22: PASSâ‰ TRUE â€” field present but always 0).
    # Operators/PyRIT could not see real latency. Fix: local `_t0` captured
    # at handler entry, used in the response builder. perf_counter() for
    # precision (monotonic, not wall-clock).
    _t0 = time.perf_counter()

    # [AUDIT-20260909 M3] Malformed bodies used to escape as an unstructured
    # 500 (Request.json() JSONDecodeError) at an OpenAI-compat boundary that
    # PyRIT/garak fuzz by design. Fail closed with the OpenAI error envelope.
    try:
        body = await request.json()
    except Exception:
        logger.warning("[openai_compat] request body is not valid JSON", exc_info=True)
        return JSONResponse(
            {"error": {"message": "Invalid JSON body", "type": "invalid_request"}},
            status_code=400,
        )
    messages = body.get("messages", [])
    model = body.get("model", CANONICAL_MODEL_ID)

    # [AUDIT-20260909 M3] A wrongly-shaped `messages` (string / non-dict
    # items) previously reached the extraction loop and crashed with
    # AttributeError ('str' object has no attribute 'get') → unstructured
    # 500. Same fail-closed envelope as above.
    if not isinstance(messages, list) or not all(isinstance(m, dict) for m in messages):
        logger.warning("[openai_compat] rejected malformed messages payload")
        return JSONResponse(
            {"error": {"message": "messages must be a list of message objects", "type": "invalid_request"}},
            status_code=400,
        )

    # Extract last user message
    question = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            question = msg.get("content", "")
            break

    if not question:
        return JSONResponse({"error": {"message": "No user message", "type": "invalid_request"}}, status_code=400)

    judge = get_judge()
    v98_context = _extract_v98_context(request)
    v98_context["body"] = question

    # [AUDIT-FIX 2026-09-24] Resource-quota pairing. TAI SAO: this endpoint
    # used to call dos_protection.record_verdict() WITHOUT ever calling
    # check_request() — record_verdict decrements the GLOBAL resource-quota
    # counter, so chat-completions traffic was freeing /ask requests' slots,
    # forging concurrency headroom past MAX_CONCURRENT=100. Design chosen:
    # pair check_request/record_verdict on the SHARED DoSProtectionEngine so
    # the 100-slot global invariant stays honest — chat-completions runs the
    # same judge pipeline as /ask, so it must consume from the same global
    # quota (a separate per-endpoint registry would allow 200 concurrent
    # pipelines). Per-IP rate limiting + circuit breaker now also protect
    # this endpoint, consistent with /ask.
    dos = getattr(judge, "dos_protection", None)
    _dos_slot_taken = False
    if dos:
        try:
            client_ip = request.client.host if request.client else "unknown"
            dos_alert = dos.check_request(client_ip)
            action = getattr(dos_alert, "action_taken", "") if dos_alert else ""
            should_block = action in ("block", "throttle") or (isinstance(dos_alert, dict) and dos_alert.get("should_block"))
            if should_block:
                status_code = int(getattr(dos_alert, "status_code", 0) or 429)
                headers = dict(getattr(dos_alert, "recommended_headers", {}) or {})
                return JSONResponse(
                    {"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}},
                    status_code=status_code,
                    headers=headers,
                )
            # check_request returns None only when the request was admitted —
            # that is exactly when one global slot was taken.
            _dos_slot_taken = dos_alert is None
        except Exception as e:
            logger.debug(f"[openai_compat] DoS check error: {e}", exc_info=True)

    # [V104.41 #AA] Táº I SAO: was calling judge.judge() synchronously in async def
    # â†’ blocks event loop when SLM/API slow. PyRIT/garak parallel requests â†’ server hang.
    # Fix: use asyncio.to_thread (same as /ask path).
    # [AUDIT-20260909 M3][ERR-1] A judge pipeline failure must surface as a
    # structured OpenAI 503 — never an unstructured 500, never an internal
    # message leak (same posture as the M2 BUG 4 fix). Logged at ERROR so the
    # failure stays loud (D6 fail-loudly).
    # [AUDIT-FIX 2026-09-24] Single try/finally guards the WHOLE pairing so
    # every exit path (success, judge exception → 503, record failure)
    # releases the quota slot exactly once.
    # [SECOND-PASS FIX 2026-09-30] record_verdict now runs on the SUCCESS path
    # BEFORE the finally (same shape as _ask_impl). TẠI SAO: the finally used
    # to release the slot on the success path too (clearing _dos_slot_taken),
    # so the post-finally record_verdict was dead code — the real sequence was
    # check_request → judge → release_slot, never record_verdict. The
    # consecutive-UNKNOWN circuit breaker was therefore never fed from this
    # endpoint, contradicting the pairing contract in
    # DoSProtectionEngine.record_verdict. _verdict_recorded is the separate
    # flag that keeps the finally a release-on-early-exit-only path.
    _verdict_recorded = False
    try:
        v = await asyncio.to_thread(
            judge.judge,
            question=question, ai_answer="", cycle_count=0, source="openai_compat",
            v98_context=v98_context
        )
        # record_verdict is only allowed on a path that holds a slot (see
        # pairing contract in DoSProtectionEngine); it both updates the
        # verdict circuit and releases the slot.
        if dos and _dos_slot_taken and not _verdict_recorded:
            try:
                dos.record_verdict(v.get("verdict", ""))
                _verdict_recorded = True
                _dos_slot_taken = False  # record_verdict released the slot
            except Exception as e:
                logger.debug(f"[V104.41 #AC] DoS record_verdict error: {e}", exc_info=True)
    except Exception:
        logger.exception("[openai_compat] judge pipeline failure")
        return JSONResponse(
            {"error": {"message": "Upstream judge pipeline unavailable", "type": "server_error"}},
            status_code=503,
        )
    finally:
        if _dos_slot_taken and dos and not _verdict_recorded:
            # Early exit (judge exception before a verdict) — return the slot.
            _dos_slot_taken = False
            try:
                dos.release_slot()
            except Exception as _dos_release_err:
                logger.debug(f"[openai_compat] DoS slot release error: {_dos_release_err}", exc_info=True)

    # [V104.41 #X] Enforce KILL/FAIL/FLAGGED at OpenAI boundary too (consistency with /ask)
    answer = v.get("final_answer", "")
    _gov = v.get("evidence", {}).get("governance_decision", "")
    if _gov == "KILL" or v.get("verdict", "") in ("FAIL", "FLAGGED"):
        answer = "I cannot comply with this request."
    elif v.get("verdict", "") == "UNKNOWN" and answer:
        answer = answer + "\n\n[SCP: unverified â€” confidence below threshold]"

    # [V104.41 #AB] Táº I SAO: canary was appended to visible content â†’ attacker sees it
    # immediately â†’ honeypot value destroyed. Fix: put canary in response metadata only,
    # NOT in visible content.
    canary = v.get("evidence", {}).get("v98_canary_token")

    # [M03-STUB-VISIBILITY 2026-09-26] Mark the stub explicitly: this response
    # was NOT generated by an LLM (judge ran with ai_answer='' — M03 gap), so
    # PyRIT/garak consumers must not mistake it for real generation. The
    # marker is additive: a top-level "warning" field plus an "x-scp-stub:
    # true" response header; the OpenAI envelope shape is unchanged. Header
    # is set on the DI-provided Response so the plain-dict return (required
    # by traced_request.attach) still carries it on the wire.
    _log_stub_warning_once()
    response.headers["x-scp-stub"] = "true"
    payload = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": answer},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "warning": _STUB_WARNING,
        "scp_metadata": {
            "verdict": v.get("verdict", ""),
            "confidence": v.get("confidence", 0.0),
            "falsification_status": v.get("evidence", {}).get("falsification_status"),
            "governance_decision": v.get("evidence", {}).get("governance_decision"),
            "v98_guard": v.get("evidence", {}).get("v98_guard_verdict", {}).get("recommendation") if v.get("evidence", {}).get("v98_guard_verdict") else None,
            "v98_classification": v.get("evidence", {}).get("v98_classification", {}).get("actor") if v.get("evidence", {}).get("v98_classification") else None,
            "v98_counter_phase": v.get("evidence", {}).get("v98_attack_policy", {}).get("phase") if v.get("evidence", {}).get("v98_attack_policy") else 0,
            "v98_canary_token": canary,
            "v98_bypass_recorded": v.get("evidence", {}).get("v98_bypass_recorded", False),
            "elapsed_ms": round((time.perf_counter() - _t0) * 1000, 1),
        },
    }
    return payload


@router.get("/v1/models")
@traced_request(_OPENAI_COMPAT_LEDGER, require_write=False, action="openai_models")
async def openai_models(current_user: str = Depends(get_current_user)):
    """OpenAI-compatible models list."""
    return {
        "object": "list",
        "data": [{
            "id": model_id,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "scp",
            "canonical": index == 0,
            "deprecated": index != 0,
        } for index, model_id in enumerate(model_id_candidates())],
    }
