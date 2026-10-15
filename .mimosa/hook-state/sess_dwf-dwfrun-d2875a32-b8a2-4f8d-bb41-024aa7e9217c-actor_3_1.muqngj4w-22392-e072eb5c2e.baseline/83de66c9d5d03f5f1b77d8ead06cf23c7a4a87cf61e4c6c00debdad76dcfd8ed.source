# SCP CIRCUIT: M02 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M02-closure.json)
"""
[V104.48] SCP Chat Ă¢â‚¬â€ WebSocket giao ti-p real-time vĂ¡Â»â€ºi user

T-I SAO: SCP V104.47 chĂ¡Â»â€° cÄ‚Â³ /ask (1 question Ă¢â€ â€™ 1 verdict) vÄ‚Â  /v1/chat/completions
(OpenAI-compat). KH-NG cÄ‚Â³ chat nhi-u turn, nhĂ¡Â»â€º context, h-i lĂ¡ÂºÂ¡i user, giĂ¡ÂºÂ£i thÄ‚Â­ch.

Module nÄ‚Â y th-m:
  - WebSocket /chat: real-time bidirectional
  - Context memory: nhĂ¡Â»â€º lĂ¡Â»â€¹ch s-­ conversation
  - SCP t-± h-i lĂ¡ÂºÂ¡i user khi UNKNOWN
  - SimpleExplainer: giĂ¡ÂºÂ£i thÄ‚Â­ch quy-t Ă„â€˜Ă¡Â»â€¹nh bĂ¡ÂºÂ±ng ti-ng ViĂ¡Â»â€¡t
  - Evolution status: user xem SCP Ă„â€˜ang t-± s-­a gÄ‚Â¬
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import time
import uuid
from collections import deque
from types import SimpleNamespace
from typing import Any  # [hygiene F821-fix] dùng ở annotation dict[str, Any] trong /chat flow

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

# [FIX-CRIT-27 BUG 9] Import verify_admin from api_server to gate the
# /chat/sessions + /chat/{id}/history endpoints (previously NO auth Ă¢â‚¬â€ anyone
# could list all active sessions + read any session's full history).
from scp.api._shared import verify_admin
from scp.core.chat_memory_store import ChatMemoryStore
from scp.core.release_identity import RELEASE_LABEL
from scp.core.request_run_ledger import RequestRunLedger

logger = logging.getLogger("scp.chat")

router = APIRouter()
_CHAT_LEDGER = RequestRunLedger()  # P2_CHAT_LEDGER

# [AUDIT-20260909 MACH2-BUG1] Per-connection input bounds. TAI SAO: the chat
# receive loop previously trusted any payload size and any send rate — a single
# connection could stream unbounded frames (DoS) into the judge pipeline.
# These bounds mirror the deterministic caps the rest of the API already
# enforces (tier1_guard MAX_ANSWER_CHARS=8000, slowapi limits on /ask).
MAX_CHAT_MESSAGE_CHARS = 8000
# Raw-frame guard: JSON wrapper/metadata overhead must never smuggle a payload
# several times larger than the message cap past the parse step.
MAX_CHAT_FRAME_CHARS = MAX_CHAT_MESSAGE_CHARS * 4
CHAT_RATE_LIMIT_MESSAGES = 20
CHAT_RATE_LIMIT_WINDOW_SECONDS = 60.0


class _DotDict(dict):
    """dict with attribute access — judge.judge() returns a plain dict but the
    response-building code below uses attribute access (v.verdict, v.evidence).
    Mirrors the DotDict normalization already used in _ask_impl.py."""

    def __getattr__(self, name):
        return self.get(name, None)

    def __setattr__(self, name, value):
        self[name] = value


def _normalize_judge_result(v):
    """Normalize a RealityJudge.judge() dict into attribute-accessible form.

    [AUDIT-20260909 MACH2-BUG1] TAI SAO: chat.py called judge.judge() then read
    v.verdict / v.evidence — but RealityJudge.judge() returns a plain dict, so
    EVERY chat message raised AttributeError and fell into the generic error
    frame even before the ai_answer="" bug. Same normalization contract as
    _ask_impl.py (DotDict + guaranteed evidence/confidence fields).
    """
    if isinstance(v, dict):
        if v.get("evidence") is None:
            v["evidence"] = {}
        if v.get("slm_responses") is None:
            v["slm_responses"] = []
        if v.get("confidence") is None:
            v["confidence"] = 0.0
        if v.get("final_answer") is None:
            v["final_answer"] = v.get("evidence", {}).get("final_answer", "")
        return _DotDict(v)
    return v


async def _generate_candidate_answer(user_message: str, conversation_context: str) -> str:
    """Generate a candidate answer BEFORE judging.

    [AUDIT-20260909 MACH2-BUG1] TAI SAO: the WebSocket chat used to call
    judge.judge(..., ai_answer="") — the deterministic tier1_guard then rejected
    every single message with REJECT_EMPTY before the LLM ever ran, so the chat
    feature was dead: every reply was "rejected". This mirrors the working
    pattern in _ask_impl.py: llm_gateway.chat(task="chat") first, then a bounded
    public-web fallback when the gateway has no healthy provider. Returns ""
    when nothing could be generated (judge fail-closes on empty — by design).
    """
    _candidate = ""
    try:
        from scp.llm_gateway import get_gateway
        from scp.runtime.question_router import detect_language

        _lang = detect_language(user_message)
        if _lang == "vi":
            _sys_prompt = (
                "Bạn là SCP — một trợ lý AI thông minh, giao tiếp tự nhiên, thân thiện và chính xác bằng tiếng Việt. "
                "Trả lời ngắn gọn, rõ ràng, trung thực và hỗ trợ thảo luận mở. Chỉ trả lời câu hỏi HIỆN TẠI. "
                "Nếu thiếu dữ liệu, nói rõ chưa đủ dữ liệu thay vì đoán."
            )
            _ctx_header = "Lịch sử gần đây (chỉ để tham khảo):\n"
        else:
            _sys_prompt = (
                "You are SCP — an intelligent AI assistant. Respond naturally, fluently, and accurately in English. "
                "Provide clear, honest, and helpful explanations. Answer the CURRENT question. "
                "State clearly if data is insufficient rather than guessing."
            )
            _ctx_header = "Recent conversation history (for reference only):\n"

        _gateway = get_gateway()
        _generated, _provider = await _gateway.chat(
            user_message,
            context=(
                _ctx_header + conversation_context
                if conversation_context
                else ""
            ),
            system_prompt=_sys_prompt,
            task="chat",
        )
        if _generated and _generated.strip():
            _candidate = _generated.strip()
            logger.info(
                "[CHATBOT] LLM (%s) generated chat candidate: %s...",
                _provider,
                _candidate[:80],
            )
    except Exception as _generation_error:
        logger.warning("[CHATBOT] LLM candidate call failed: %s", _generation_error, exc_info=True)

    if _candidate:
        return _candidate

    if os.environ.get("SCP_WEB_FALLBACK", "1") == "1":
        try:
            from scp.web_control.internet_search import InternetSearch

            _web_timeout = min(float(os.environ.get("SCP_WEB_FALLBACK_TIMEOUT", "8")), 12.0)
            _web_search = InternetSearch(timeout=min(_web_timeout / 2.0, 4.0))
            _web_fallback = await asyncio.wait_for(
                _web_search.search(user_message, max_results=6), timeout=_web_timeout
            )
            if _web_fallback and _web_fallback.get("success"):
                _snippets = []
                for _item in (_web_fallback.get("results") or [])[:6]:
                    _title = str(_item.get("title", "")).strip()
                    _snippet = str(_item.get("snippet", "")).strip()
                    _url = str(_item.get("url", "")).strip()
                    if _title or _snippet:
                        _snippets.append(f"- {_title}: {_snippet} ({_url})")
                if _snippets:
                    _candidate = (
                        "[SCP public-web evidence; untrusted, requires verification]\n"
                        + "\n".join(_snippets)
                    )
                    logger.info("[CHATBOT] public-web fallback produced candidate")
        except Exception as _web_err:
            logger.warning("[CHATBOT] public-web fallback failed: %s", _web_err, exc_info=True)

    return _candidate


class ConversationManager:
    """QuĂ¡ÂºÂ£n lÄ‚Â½ lĂ¡Â»â€¹ch s-­ conversation per session."""

    def __init__(self, max_sessions: int = 100, max_history: int = 20, memory_store: ChatMemoryStore | None = None):
        self._sessions: dict[str, list[dict]] = {}
        self._lock = threading.Lock()
        self._max_sessions = max_sessions
        self._max_history = max_history
        if memory_store is not None:
            self._memory_store = memory_store
        else:
            from scp.core.chat_memory import get_chat_memory_store
            self._memory_store = get_chat_memory_store()
        self._persistence_failures = 0

    def get_history(self, session_id: str) -> list[dict]:
        loaded = self._memory_store.load(session_id, limit=self._max_history)
        with self._lock:
            if loaded:
                self._sessions[session_id] = loaded[-self._max_history :]
            return self._sessions.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str, metadata: dict | None = None):
        with self._lock:
            if session_id not in self._sessions:
                if len(self._sessions) >= self._max_sessions:
                    oldest = next(iter(self._sessions))
                    del self._sessions[oldest]
                self._sessions[session_id] = []

            self._sessions[session_id].append({
                "role": role,
                "content": content,
                "timestamp": time.time(),
                "metadata": metadata or {},
            })

            if len(self._sessions[session_id]) > self._max_history:
                self._sessions[session_id] = self._sessions[session_id][-self._max_history:]
        if not self._memory_store.append(session_id, role, content, metadata):
            self._persistence_failures += 1

    def persistence_status(self) -> dict:
        return {
            "mode": "redacted_durable",
            "path_configured": True,
            "write_failures": self._persistence_failures,
        }

    def get_context_string(self, session_id: str) -> str:
        history = self.get_history(session_id)
        if not history:
            return ""
        lines = []
        for msg in history[-10:]:
            role = "User" if msg["role"] == "user" else "SCP"
            lines.append(f"{role}: {msg['content'][:200]}")
        return "\n".join(lines)


_conversation_mgr = ConversationManager()


@router.websocket("/chat")
async def scp_chat(websocket: WebSocket):
    """
    WebSocket endpoint Ă¢â‚¬â€  chat real-time vĂ¡Â»â€ºi SCP.

    User g-­i: {"message": "What is 2+2?"}
    SCP trĂ¡ÂºÂ£: {"answer": "4", "verdict": "PASS", "confidence": 0.99, "reasoning": "..."}
    """
    await websocket.accept()

    try:
        from scp.security.auth_config import load_auth_config
        cfg = load_auth_config()
        # [STEP0-FIX 2026-09-02] session_id is NOT a credential. The old dev-UI
        # fallback let a client-controlled query param be evaluated against the
        # real secret; WebSocket auth now requires the explicit token query
        # param (canonical contract: explicit token only, fail-closed).
        client_token = str(websocket.query_params.get("token", "") or "")
        if client_token.startswith("Bearer "):
            client_token = client_token[7:]

        import secrets
        is_valid = False
        if cfg.token and secrets.compare_digest(client_token, cfg.token):
            is_valid = True
        elif cfg.password and secrets.compare_digest(client_token, cfg.password):
            is_valid = True

        if not cfg.configured:
            await websocket.close(code=1011)
            return
        if not is_valid:
            await websocket.close(code=1008)
            return
    except Exception:
        logger.warning('scp_chat: Exception not handled', exc_info=True)
        await websocket.close(code=1011)
        return

    requested_session = str(websocket.query_params.get("session_id", "")).strip()
    session_id = requested_session if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", requested_session or "") else str(uuid.uuid4())[:8]
    resumed_history = bool(await asyncio.to_thread(_conversation_mgr.get_history, session_id))
    logger.info(f"[SCP Chat] Session {session_id} connected resumed={resumed_history}")

    await websocket.send_json({
        "type": "system",
        "message": f"{RELEASE_LABEL} — kết nối. Session: {session_id}\n"
                   f"Tôi có thể kiểm tra câu trả lời, phát hiện tấn công, và tự học.\n"
                   f"Hỏi tôi bất cứ điều gì — tôi sẽ nói 'Tại sao?' và kiểm tra.",
        "session_id": session_id,
        "resumed": resumed_history,
        "memory_mode": "redacted_durable",
    })

    try:
        # [F-RUN-01 audit-r2 2026-10-01] Kill-switch admission helpers for the
        # chat lane, imported lazily INSIDE the connection handler: this module
        # is imported by scp.api_server at module level, so a top-level import
        # would be circular. EVIDENCE: /chat runs judge.judge() (and
        # AgentOrchestrator in task mode) directly and registers NO ask-kernel
        # adapter, so the kernel global_kill that /v3/pc/kill flips via
        # api_server._ASK_KERNEL_ADAPTERS (commit 155c95b0) and the /ask
        # admission gate are BOTH invisible here — after a kill the chat lane
        # kept processing frames (kernel bypass, same A9 class as /ask).
        # Reusing the /ask helpers via import keeps ONE refusal authority
        # instead of a copied fork that could drift.
        from scp.api_server import _kill_switch_blocked_response, _pc_kill_switch_engaged
        from scp.api_server_parts.helpers import AskRequest

        _msg_timestamps: deque[float] = deque()  # [AUDIT-20260909] per-connection rate window
        while True:
            data = await websocket.receive_text()

            # [F-RUN-01 audit-r2 2026-10-01] Absolute stop: no chat frame may be
            # processed while the kill switch is engaged. Checked per frame (the
            # durable flag file can flip mid-session) and BEFORE any ledger or
            # judge/orchestrator work — mirrors the /ask gate placement ("before
            # every other check"). Fail-closed is inherited from
            # _pc_kill_switch_engaged (unreadable flag state counts as engaged).
            if _pc_kill_switch_engaged():
                _blocked = _kill_switch_blocked_response(
                    AskRequest(question=data[:8000], source="websocket_chat")
                )
                logger.warning("[F-RUN-01] /chat frame refused: kill switch engaged")
                await websocket.send_json({
                    "type": "error",
                    "reason": "kill_switch_engaged",
                    "message": _blocked.final_answer,
                    "falsification_status": _blocked.falsification_status,
                    "governance": _blocked.governance_decision,
                    "run_status": _blocked.run_status,
                })
                await websocket.close(code=1008)  # 1008 = policy violation
                break

            # [AUDIT-20260909 MACH2-BUG1] Raw-frame guard + message cap. A frame
            # whose raw size can never contain a valid message is rejected before
            # JSON parsing; an oversized parsed message is rejected before any
            # pipeline work. Both close the connection — no silent drop.
            if len(data) > MAX_CHAT_FRAME_CHARS:
                logger.warning("[SCP Chat] oversized frame rejected (%d chars)", len(data))
                await websocket.send_json({
                    "type": "error",
                    "reason": "message_too_large",
                    "message": f"Tin nhắn vượt giới hạn {MAX_CHAT_MESSAGE_CHARS} ký tự.",
                    "max_chars": MAX_CHAT_MESSAGE_CHARS,
                })
                await websocket.close(code=1009)  # 1009 = message too big
                break

            # [AUDIT-20260909 MACH2-BUG1] Per-connection rate limit: sliding
            # window of accepted message timestamps. Exceeding the limit is a
            # policy violation → error frame + close 1008.
            _now = time.time()
            while _msg_timestamps and (_now - _msg_timestamps[0]) > CHAT_RATE_LIMIT_WINDOW_SECONDS:
                _msg_timestamps.popleft()
            if len(_msg_timestamps) >= CHAT_RATE_LIMIT_MESSAGES:
                logger.warning("[SCP Chat] rate limit exceeded (%d msgs/%ds)", CHAT_RATE_LIMIT_MESSAGES, int(CHAT_RATE_LIMIT_WINDOW_SECONDS))
                await websocket.send_json({
                    "type": "error",
                    "reason": "rate_limit_exceeded",
                    "message": f"Tối đa {CHAT_RATE_LIMIT_MESSAGES} tin nhắn mỗi {int(CHAT_RATE_LIMIT_WINDOW_SECONDS)} giây.",
                    "limit": CHAT_RATE_LIMIT_MESSAGES,
                    "window_seconds": CHAT_RATE_LIMIT_WINDOW_SECONDS,
                })
                await websocket.close(code=1008)  # 1008 = policy violation
                break
            _msg_timestamps.append(_now)

            msg = {}
            try:
                msg = json.loads(data)
                user_message = str(msg.get("message", "") or "").strip()
            except json.JSONDecodeError:
                logger.debug('scp_chat: json.JSONDecodeError ignored', exc_info=True)
                user_message = data.strip()

            if user_message and len(user_message) > MAX_CHAT_MESSAGE_CHARS:
                logger.warning("[SCP Chat] message over cap rejected (%d chars)", len(user_message))
                await websocket.send_json({
                    "type": "error",
                    "reason": "message_too_large",
                    "message": f"Tin nhắn vượt giới hạn {MAX_CHAT_MESSAGE_CHARS} ký tự.",
                    "max_chars": MAX_CHAT_MESSAGE_CHARS,
                })
                await websocket.close(code=1009)
                break

            task_mode = str(msg.get("mode", "")).strip().lower() in {"agent_task", "task", "orchestrate"}
            if not user_message:
                continue
            await asyncio.to_thread(_conversation_mgr.add_message, session_id, "user", user_message, {"type": "user_message", "mode": "agent_task" if task_mode else "chat"})
            run = _CHAT_LEDGER.begin(SimpleNamespace(source="websocket_chat", domain="general", message=user_message))
            if not run.ledger_write_ok:
                await websocket.send_json({"type": "error", "message": "Audit ledger unavailable; chat processing blocked", "run_id": run.run_id, "trace_id": run.trace_id, "run_status": "DB_WRITE_FAILED", "ledger_status": "DB_WRITE_FAILED"})
                continue
            _CHAT_LEDGER.stage(run, "chat_message_started", "RUNNING")

            if task_mode:
                try:
                    from scp.core.agent_orchestrator import AgentOrchestrator

                    agent = AgentOrchestrator()
                    task_result = await agent.run(
                        goal=user_message,
                        execute=True,
                        capability_level=0,
                        approved=False,
                        parent_trace_id=run.trace_id,
                    )
                    task_status = str(task_result.get("status", "INTERNAL_FAILED"))
                    if task_result.get("ledger_status") == "DB_WRITE_FAILED":
                        outer_status = "DB_WRITE_FAILED"
                    elif task_result.get("success") is True:
                        outer_status = "SUCCESS"
                    elif task_status in {"PLAN_READY", "WAITING_APPROVAL"}:
                        outer_status = "UNKNOWN"
                    else:
                        outer_status = "INTERNAL_FAILED"
                    terminal_status, ledger_ok = _CHAT_LEDGER.finish(
                        run,
                        outer_status,
                        result={"verdict": "PASS" if outer_status == "SUCCESS" else "UNKNOWN"},
                        task_status=task_status,
                        agent_run_id=task_result.get("agent_run_id"),
                    )
                    task_response = {
                        "type": "agent_task",
                        "status": task_status,
                        "success": bool(task_result.get("success")),
                        "answer": "Đã hoàn thành tác vụ an toàn." if task_result.get("success") else "Tác vụ chưa được hoàn thành; xem trạng thái và approval.",
                        "agent_run_id": task_result.get("agent_run_id"),
                        "agent_trace_id": task_result.get("trace_id"),
                        "plan": task_result.get("plan"),
                        "approval": task_result.get("approval"),
                        "result": task_result.get("result"),
                        "run_id": run.run_id,
                        "trace_id": run.trace_id,
                        "run_status": outer_status if terminal_status != "DB_WRITE_FAILED" else "DB_WRITE_FAILED",
                        "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED",
                    }
                    await websocket.send_json(task_response)
                    await asyncio.to_thread(_conversation_mgr.add_message, session_id, "scp", task_response.get("answer", ""), task_response)
                except Exception as exc:
                    logger.warning('scp_chat: Exception not handled: %s', exc, exc_info=True)
                    failure_status = _CHAT_LEDGER.classify_error(exc)
                    terminal_status, ledger_ok = _CHAT_LEDGER.finish(run, failure_status, error=exc, task_mode=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": "Lỗi xử lý agent task; xem run_id trong ledger",
                        "run_id": run.run_id,
                        "trace_id": run.trace_id,
                        "run_status": terminal_status,
                        "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED",
                    })
                continue

            _conversation_context = await asyncio.to_thread(_conversation_mgr.get_context_string, session_id)

            try:
                # [F-WS-FIX] Local `import asyncio` here shadowed the module-
                # level import for the whole function body, breaking the earlier
                # asyncio.to_thread call at the handshake (UnboundLocalError).
                # Module-level import is authoritative; nothing to re-import.
                from scp.api_server import get_judge

                # [FIX-CRIT-27 BUG 8] Removed `os.environ.setdefault("SCP_DEV_MODE", "1")`
                # Ă¢â‚¬â€ any WebSocket client was force-enabling SCP_DEV_MODE globally,
                # which disables admin auth for ALL endpoints server-wide (verify_admin
                # reads SCP_DEV_MODE at call time). Dev mode must be explicit, not
                # auto-enabled by a chat connection.
                judge = get_judge()
                _CHAT_LEDGER.stage(run, "judge_ready", "RUNNING")

                # [AUDIT-20260909 MACH2-BUG1] Generate a REAL candidate answer
                # BEFORE judging. Previously ai_answer="" was passed and the
                # tier1_guard REJECT_EMPTY check failed every message — the LLM
                # never ran and the chat was permanently "rejected".
                from scp.knowledge.domain_knowledge import AutonomousEvidenceRetriever, FactSeparator
                from scp.runtime.question_router import LANE_CHATBOT, LANE_FACTUAL, LANE_SECURITY, route_question
                _route = route_question(user_message)
                _retrieval_res: dict[str, Any] = {}
                _is_factual_query = (_route.lane == LANE_FACTUAL or any(kw in user_message.lower() for kw in ("thủ đô", "capital", "là gì", "ở đâu", "ai là", "speed of", "diện tích", "dân số")))
                if _is_factual_query:
                    try:
                        _retriever = AutonomousEvidenceRetriever()
                        _retrieval_res = await _retriever.retrieve(
                            user_message,
                            current_confidence=0.5,
                            domain="general",
                            allow_web=bool(os.environ.get("SCP_WEB_FALLBACK", "1") == "1"),
                        )
                    except Exception as _ret_err:
                        logger.warning("[SCP Chat] Autonomous retrieval failed: %s", _ret_err, exc_info=True)

                _candidate_answer = await _generate_candidate_answer(user_message, _conversation_context)
                if not _candidate_answer and _retrieval_res.get("clean_evidence_snippets"):
                    _candidate_answer = "\n".join(_retrieval_res["clean_evidence_snippets"][:3])
                if not _candidate_answer:
                    logger.warning("[SCP Chat] no candidate answer could be generated; judge will fail closed (REJECT_EMPTY)")

                v_raw = await asyncio.to_thread(
                    judge.judge,
                    question=user_message,
                    ai_answer=_candidate_answer,
                    cycle_count=0,
                    source="chat",
                    v98_context={
                        "session_id": session_id,
                        "ip": "websocket",
                        "conversation_history": _conversation_context,
                        "current_question": user_message,
                        "retrieved_context": "\n".join(_retrieval_res.get("clean_evidence_snippets", [])),
                    },
                )
                v = _normalize_judge_result(v_raw)
                _CHAT_LEDGER.stage(run, "verifier_completed", "RUNNING", verdict=v.verdict, governance_decision=v.evidence.get("governance_decision", ""))

                _is_chatbot_lane = (_route.lane == LANE_CHATBOT)
                _gov = v.evidence.get("governance_decision", "")
                _is_attack = bool(
                    _gov == "KILL"
                    or _route.lane == LANE_SECURITY
                    or v.verdict == "FLAGGED"
                    or v.evidence.get("threat_detected")
                    or v.evidence.get("injection_detected")
                    or v.evidence.get("is_attack")
                    or v.evidence.get("adversarial")
                    or v.evidence.get("jailbreak_detected")
                )

                if _is_attack or not _candidate_answer:
                    _abstain = True
                    _ws_answer = "[SCP: Answer withheld]"
                    _ws_reasoning = ""
                    v.verdict = "FAIL"
                elif _is_chatbot_lane:
                    # [SEC-R2-02] Fail-closed: require explicit clearance (UPHOLD/ALLOW) and PASS
                    if _gov in ("KILL", "REJECT", "DENY", "DEGRADED", "ESCALATE", "UNKNOWN") or v.verdict in ("FAIL", "FLAGGED", "DEGRADED", "UNCERTAIN", "ESCALATE") or not _gov:
                        _abstain = True
                        _ws_answer = "[SCP: Answer withheld]"
                        _ws_reasoning = ""
                        v.verdict = "FAIL"
                        _gov = _gov or "KILL"
                    else:
                        _abstain = False
                        _ws_answer = v.final_answer or _candidate_answer or "(Không có câu trả lời)"
                        _ws_reasoning = v.reasoning[:300] if v.reasoning else ""
                else:
                    _abstain = (_gov in ("KILL", "DEGRADED", "ESCALATE")) or (v.verdict in ("FAIL", "FLAGGED", "DEGRADED", "UNCERTAIN", "ESCALATE"))
                    _ws_answer = ("[SCP: Answer withheld]" if _abstain
                                  else (v.final_answer or "(Không có câu trả lời)"))
                    _ws_reasoning = ("" if _abstain
                                     else (v.reasoning[:300] if v.reasoning else ""))

                # Milestone 2: Fact Separation & Confidence Badge Payload (R2)
                _fact_separator = FactSeparator()
                _fact_res = _fact_separator.separate(
                    question=user_message,
                    answer=_ws_answer,
                    lane=_route.lane,
                    confidence=float(v.confidence if v.confidence is not None else 0.0),
                    retrieval_result=_retrieval_res,
                )

                response = {
                    "type": "answer",
                    "answer": _ws_answer,
                    "verdict": v.verdict,
                    "confidence": round(v.confidence, 2) if v.confidence is not None else 0.0,
                    "domain": v.domain or "general",
                    "reasoning": _ws_reasoning,
                    "why_plan": "no" if _abstain else ("yes" if v.evidence.get("why_plan") else "no"),
                    "governance": _gov if _gov else "KILL",
                    "healing": 0 if _abstain else len(v.evidence.get("healing_actions", [])),
                    "verified_facts": [] if (_abstain or _is_attack or v.verdict == "FAIL") else _fact_res["verified_facts"],
                    "llm_reasoning": "" if (_abstain or _is_attack or v.verdict == "FAIL") else _fact_res["llm_reasoning"],
                    "confidence_badge": {
                        "badge": "UNVERIFIED_CONJECTURE",
                        "score": 0.0,
                        "sources_consulted": [],
                        "transparency_notes": "Security boundary triggered fail-closed withhold.",
                    } if (_abstain or _is_attack or v.verdict == "FAIL") else _fact_res["confidence_badge"],
                }

                if _abstain or v.verdict == "FAIL":
                    response["type"] = "rejected"
                    response["answer"] = "[SCP: Answer withheld]"
                    response["reasoning"] = ""
                    response["explanation"] = (
                        f"Tôi không thể xác nhận câu trả lời này. Lý do: "
                        f"{v.reasoning[:200] if v.reasoning else 'Không đủ bằng chứng.'}"
                    )
                elif v.verdict == "UNKNOWN" and not _is_chatbot_lane:
                    response["type"] = "clarification"
                    response["question"] = (
                        f"Tôi chưa đủ thông tin để kết luận. "
                        f"Bạn có thể cung cấp thêm chi tiết về '{user_message[:50]}' không?"
                    )
                elif v.verdict == "PASS":
                    response["type"] = "verified"
                    response["explanation"] = (
                        f"Đã kiểm tra: câu trả lời đạt độ tin cậy {response['confidence']:.0%}. "
                        f"Domain: {v.domain}."
                    )

                if "tiến hóa" in user_message.lower() or "evolution" in user_message.lower():
                    try:
                        from scp.core.code_evolution_agent import get_evolution_agent
                        agent = get_evolution_agent()
                        response["evolution"] = agent.get_stats()
                    except Exception:
                        logger.exception("[chat.py:182] silenced exception")

                if "học" in user_message.lower() or "learning" in user_message.lower():
                    try:
                        from scp.api_server import _fast_learning
                        if _fast_learning:
                            # [SCP-DNA-FIX] FastLearningEngine exposes stats(),
                            # NOT get_stats(). Previous call -> AttributeError ->
                            # silent except -> learning stats never surfaced in chat.
                            response["learning"] = _fast_learning.stats()
                    except Exception:
                        logger.exception("[chat.py:190] silenced exception")

                run_status = RequestRunLedger.classify_result(response)
                terminal_status, ledger_ok = _CHAT_LEDGER.finish(run, run_status, result=response)
                if run_status == "SUCCESS" and terminal_status == "DB_WRITE_FAILED":
                    run_status = "DB_WRITE_FAILED"
                response.update({"run_id": run.run_id, "trace_id": run.trace_id, "run_status": run_status, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED"})
                await websocket.send_json(response)
                await asyncio.to_thread(_conversation_mgr.add_message, session_id, "scp", response.get("answer", ""), response)

            except Exception as e:
                failure_status = _CHAT_LEDGER.classify_error(e)
                terminal_status, ledger_ok = _CHAT_LEDGER.finish(run, failure_status, error=e)
                await websocket.send_json({
                    "type": "error",
                    "message": "Lỗi xử lý request; xem run_id trong ledger",
                    "run_id": run.run_id,
                    "trace_id": run.trace_id,
                    "run_status": terminal_status,
                    "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED",
                })
                logger.error(f"[SCP Chat] Error: {e}", exc_info=True)

    except WebSocketDisconnect:
        logger.info(f"[SCP Chat] Session {session_id} disconnected")
    except Exception as e:
        logger.error(f"[SCP Chat] WebSocket error: {e}", exc_info=True)


@router.get("/chat/sessions")
async def list_sessions(_admin: bool = Depends(verify_admin)):  # [FIX-CRIT-27 BUG 9] was NO auth
    return {
        "active_sessions": len(_conversation_mgr._sessions),
        "sessions": list(_conversation_mgr._sessions.keys()),
        "memory": _conversation_mgr.persistence_status(),
    }


@router.get("/chat/{session_id}/history")
async def get_session_history(session_id: str, _admin: bool = Depends(verify_admin)):  # [FIX-CRIT-27 BUG 9] was NO auth
    return {
        "session_id": session_id,
        "messages": await asyncio.to_thread(_conversation_mgr.get_history, session_id),
    }
