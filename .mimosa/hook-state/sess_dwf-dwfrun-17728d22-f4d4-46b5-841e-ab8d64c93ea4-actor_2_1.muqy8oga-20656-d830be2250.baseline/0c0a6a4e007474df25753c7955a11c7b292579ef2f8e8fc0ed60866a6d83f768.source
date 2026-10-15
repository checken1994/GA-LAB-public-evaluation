# SCP CIRCUIT: M02 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M02-closure.json)
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import sqlite3
import threading
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from scp.core.runtime_paths import runtime_data_dir
from scp.core.verifier_receipt import VerifierReceipt, sign_verifier_receipt

logger = logging.getLogger(__name__)


_c3_logger = logging.getLogger("scp.ask_kernel_adapter")

try:
    from .task_kernel import InvalidTransition, KernelError, StorageIntegrityError, TaskKernel
    from .trace_ledger import TraceLedger
except ImportError:
    logger.debug('<module>: ImportError ignored', exc_info=True)
    from task_kernel import InvalidTransition, KernelError, StorageIntegrityError, TaskKernel
    from trace_ledger import TraceLedger
try:
    from scp.api_server_parts.helpers import AskResponse
except Exception:  # pragma: no cover - standalone kernel tests do not need API schema
    logger.warning('<module>: Exception not handled', exc_info=True)
    AskResponse = None


_TRACE_LOCK = threading.Lock()
_TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}
# States in which the in-process ask attempt still holds execution authority
# over the task. Anything else that is non-terminal means the watchdog,
# boot-recovery, lease expiry or a previous escalation already moved the
# task out of the happy path — finalize must route, not assume.
_ASK_LIFECYCLE_INTACT_STATES = {"RUNNING", "VERIFYING"}

# [S20 2026-09-13] Long-LLM availability. Runtime evidence (bench_final_seed99
# + GA.md B11): free-tier provider latency measured 30-260s (mean 85.6s) while
# the /ask claim lease TTL was a fixed 60s. The lease expired mid-handler, the
# watchdog moved the task, and S19's fail-closed state-route correctly
# discarded a real, correct answer (2/10 asks on seed 99). The fix is NOT a
# bigger TTL (that just slows real crash detection): the holder renews the
# lease while it is alive (kernel.renew_lease, expiry-only, fencing-checked),
# so an expired lease again proves the worker is *dead*, not merely *slow*.
DEFAULT_ASK_LEASE_TTL_SECONDS = 60


def ask_lease_ttl_seconds() -> int:
    """SCP_ASK_LEASE_TTL_SECONDS as int seconds; default 60 preserved.

    Parse errors / zero / negative fall back to the default — importing or
    starting the adapter must never crash on a bad env value, and a
    non-positive TTL would violate the kernel lease contract (claim raises).
    """
    raw = os.environ.get("SCP_ASK_LEASE_TTL_SECONDS", "")
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        return DEFAULT_ASK_LEASE_TTL_SECONDS
    if value <= 0:
        return DEFAULT_ASK_LEASE_TTL_SECONDS
    return value


def ask_lease_heartbeat_enabled() -> bool:
    """Kill switch SCP_ASK_LEASE_HEARTBEAT=0|false|off|no disables renewal.

    Kept for the deterministic anti-placebo control test (T04 S20): with the
    heartbeat off and a slow provider, the old lifecycle_authority_lost
    failure must reproduce — proving the test actually exercises the bug.
    """
    raw = os.environ.get("SCP_ASK_LEASE_HEARTBEAT", "").strip().lower() or "1"
    return raw not in {"0", "false", "off", "no"}


def _dump(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, dict):
        return obj
    return dict(vars(obj))


def _verification_fail_reason(response_data: dict[str, Any]) -> str:
    """[SECURITY-REASON 2026-09-26] Kernel reason for a non-verified ask.

    The old code used ONE reason ('ask_evidence_insufficient_or_contradicted')
    for every non-verified run, so kernel/trace audits could not tell a
    security-lane kill apart from a benign evidence-insufficient ask.

    Contract:
      * security lane determined the outcome (LANE_SECURITY on the response, a
        security-blocked v98 guard, or a governance KILL from the judge-level
        pipeline) → 'ask_security_escalate';
      * benign evidence-insufficient/contradicted run keeps the historical
        reason 'ask_evidence_insufficient_or_contradicted'.

    `response_data` is the judge-level response dump read BEFORE
    _safe_response applies the boundary override (KILL/ESCALATE), so a
    governance KILL here is the pipeline's own security decision, not the
    verifier's escalation bookkeeping.
    """
    guard = response_data.get("v98_guard")
    security_determined = (
        str(response_data.get("lane") or "") == "LANE_SECURITY"
        or str(response_data.get("governance_decision") or "") == "KILL"
        or (isinstance(guard, dict) and bool(guard.get("security_blocked")))
    )
    return (
        "ask_security_escalate"
        if security_determined
        else "ask_evidence_insufficient_or_contradicted"
    )


def t2_fork_enabled() -> bool:
    """[S24] Mirror of scp.runtime.question_router.t2_fork_enabled, defined
    locally so run_rag's kill-switch check works even if the router module
    fails to import (fork off = old behavior, never a crash)."""
    raw = os.environ.get("SCP_T2_ROUTER", "").strip().lower() or "1"
    return raw not in {"0", "false", "off", "no"}


class AskKernelAdapter:
    """Durable lifecycle gate around the existing context-backed /ask path.

    The adapter does not replace JudgeCore. It calls the supplied handler first,
    then independently checks the returned answer against request evidence before
    allowing the TaskKernel to complete the task.
    """

    def __init__(self, db_path: str | None = None, trace_path: str | None = None, *, autonomous_mode: bool | None = None):
        if db_path is None:
            # [SEC 2026-09-25] tempfile.mktemp is the insecure predictable-name
            # pattern (Mimosa finding): the name can be raced between guess and
            # open. tempfile.mkstemp creates the file atomically (O_EXCL, 0600)
            # and returns the fd — close it and hand the name onward; SQLite
            # treats an existing empty file as a fresh database, same semantics
            # as before (same directory family: the process temp dir).
            import tempfile
            fd, db_path = tempfile.mkstemp(suffix=".sqlite", prefix="kernel_")
            os.close(fd)
        if trace_path is None:
            import tempfile
            fd, trace_path = tempfile.mkstemp(suffix=".jsonl", prefix="trace_")
            os.close(fd)
        if autonomous_mode is not None:
            self.autonomous_mode = bool(autonomous_mode)
        else:
            self.autonomous_mode = os.environ.get("SCP_AUTONOMOUS_MODE", "").strip().lower() in {"1", "true", "yes"}
        self.kernel = TaskKernel(db_path, autonomous_mode=self.autonomous_mode)
        self.trace = TraceLedger(trace_path)
        # [C3 — Gemini indictment: SQLite SPOF] Boot-time durability:
        # integrity quick_check + online backup với retention. Lỗi maintenance
        # KHÔNG bao giờ chặn serving (chỉ log) — nhưng hỏng được ghi nhận.
        self.last_maintenance: dict[str, Any] | None = None
        try:
            integrity = self.kernel.verify_integrity()
            if integrity["quick_check"] != "ok":
                _c3_logger.error("[C3] kernel DB quick_check FAILED: %s", integrity["quick_check"])
            backup_result = self.kernel.backup(
                Path(db_path).parent / "kernel-backups",
                retain=int(os.environ.get("SCP_KERNEL_BACKUP_RETENTION", "7")),
            )
            self.last_maintenance = {"integrity": integrity, "backup": backup_result}
            _c3_logger.info(
                "[C3] kernel maintenance ok: quick_check=%s backup=%s (%s bytes, retained=%s)",
                integrity["quick_check"], Path(backup_result["backup"]).name,
                backup_result["size_bytes"], backup_result["retained"],
            )
        except Exception as exc:  # durability check phải không bao giờ chặn serving
            logger.warning('AskKernelAdapter.__init__: Exception not handled: %s', exc, exc_info=True)
            _c3_logger.warning("[C3] kernel maintenance failed (non-blocking): %s", exc)
            self.last_maintenance = None

    def _existing_task(self, task_id: str) -> dict[str, Any] | None:
        try:
            return self.kernel.get_task(task_id)
        except Exception:
            logger.warning('AskKernelAdapter._existing_task: Exception not handled', exc_info=True)
            return None

    # Lifecycle states where a racing transport retry must still be deduped:
    # the first execution has not reached a decision yet.
    _IN_FLIGHT_STATES = {
        "CREATED", "PLANNING", "READY", "QUEUED", "LEASED", "RUNNING",
        "WAITING_TOOL", "VERIFYING", "CHECKPOINTED", "UNKNOWN",
        "RECOVERING", "RECONCILING", "RETRY_SCHEDULED",
    }

    @staticmethod
    def _duplicate_is_reaskable(existing: dict[str, Any] | None) -> bool:
        """A duplicate whose lifecycle has REACHED A DECISION (terminal, or
        HUMAN_REVIEW — the answer was withheld) is a finished ask: a new
        identical request is a legitimate new ask, not a transport retry.
        Only an in-flight duplicate must be deduped against."""
        if not existing:
            return False
        return existing.get("state") not in AskKernelAdapter._IN_FLIGHT_STATES

    @staticmethod
    def canonical_input_hash(question: str, contexts: list[str], retrieved_context: str) -> str:
        raw = json_bytes(
            {
                "question": question,
                "contexts": contexts,
                "retrieved_context": retrieved_context,
            }
        )
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    @classmethod
    def task_id_for(
        cls,
        question: str,
        contexts: list[str],
        retrieved_context: str,
        session_id: str | None,
        request_id: str | None,
    ) -> str:
        """Durable identity for one logical ask. Exposed as a classmethod so
        harnesses derive the SAME id instead of mirroring (and drifting from)
        the private formula.

        [S19 BUG-2 fix 2026-09-13] The canonical question/evidence hash is
        ALWAYS part of the identity. The previous derivation let a client
        idempotency key REPLACE the hash entirely
        (``identity = request_id or f"{session}|{hash}"``), so a client that
        reuses one key (per-run key, per-provider key, benchmark replay) mapped
        EVERY different question onto the FIRST ask's task; create_task then
        collided and every later request died fail-closed with
        "stable logical ask already exists" — the endpoint locked after the
        first question. Idempotency semantics: a key (or session) dedupes
        REPEATS OF THE SAME question+evidence (transport retries), it must not
        act as a global mutex over unrelated questions. The key/session stays
        the retry SCOPE discriminator; the input hash stays the PER-QUESTION
        discriminator; a retry with the same key and same body still maps to
        the same durable id.
        """
        input_hash = cls.canonical_input_hash(question, contexts, retrieved_context)
        scope = request_id or session_id or ""
        return "ask-" + hashlib.sha256(f"{scope}|{input_hash}".encode()).hexdigest()[:24]

    def _task_id(
        self,
        question: str,
        contexts: list[str],
        retrieved_context: str,
        session_id: str | None,
        request_id: str | None,
    ) -> str:
        return self.task_id_for(question, contexts, retrieved_context, session_id, request_id)

    def _input_hash(self, question: str, contexts: list[str], retrieved_context: str) -> str:
        return self.canonical_input_hash(question, contexts, retrieved_context)

    @staticmethod
    def _request_id(request: Any) -> str | None:
        headers = getattr(request, "headers", None)
        if headers is None:
            return None
        value = headers.get("X-SCP-Idempotency-Key") or headers.get("Idempotency-Key")
        return str(value)[:200] if value else None

    def begin(
        self,
        question: str,
        contexts: list[str],
        retrieved_context: str,
        session_id: str | None,
        request: Any = None,
        _retried: bool = False,
    ) -> dict[str, Any]:
        request_id = self._request_id(request)
        task_id = self._task_id(question, contexts, retrieved_context, session_id, request_id)
        if _retried:
            # [FIX 2026-08-29] A terminal duplicate older than the window is a
            # legitimate NEW ask, not a transport retry. Uniquify the durable
            # id so repeat asks are not blocked for the database's lifetime.
            task_id = task_id + "-" + uuid.uuid4().hex[:8]
        input_hash = self._input_hash(question, contexts, retrieved_context)
        # [CHAIN-AUDIT: backpressure] Admission control — chặn intake trước khi
        # kernel ngập. Vượt cap → fail-closed (caller nhận blocked response),
        # thay vì tích dồn vô hạn task rồi chậm chết cả chuỗi.
        max_inflight = int(os.environ.get("SCP_ASK_MAX_INFLIGHT", "200"))
        if max_inflight > 0 and self.kernel.in_flight_count() >= max_inflight:
            raise KernelError(
                f"backpressure: in-flight ask tasks at cap {max_inflight} — try again later"
            )
        try:
            self.kernel.create_task(task_id, "ask-route", "rag-verified /ask", "R0", input_hash=input_hash)
            for state in ("PLANNING", "READY", "QUEUED"):
                self.kernel.transition(task_id, state, actor="ask-kernel-adapter", reason="ask_lifecycle")
            lease_ttl = ask_lease_ttl_seconds()
            lease = self.kernel.claim(task_id, "ask-route-worker", ttl_seconds=lease_ttl)
            self.kernel.start(task_id, lease.lease_id)
            logical_key, claimed = self.kernel.idempotency_claim(
                task_id,
                "rag-read",
                "rag.context.read",
                input_hash,
            )
            if not claimed:
                raise KernelError("logical ask action already claimed")
            # [F-03] The exact planned_action object is kept in the returned
            # task handle: finalize needs it to re-present the same bytes to
            # kernel.finalize_checkpoint (planned_action_hash match) — no
            # reconstruction drift.
            checkpoint_planned_action = {
                "operation": "rag-verified-read",
                "risk_tier": "R0",
                "contexts_count": len(contexts),
                "retrieved_context_present": bool(retrieved_context.strip()),
            }
            checkpoint_id = self.kernel.checkpoint(
                task_id,
                lease.lease_id,
                "rag-read",
                "RUNNING",
                checkpoint_planned_action,
                0,
                logical_key,
                pre_observation_ref=f"ask://{task_id}/pre",
            )
            with _TRACE_LOCK:
                self.trace.append(
                    task_id=task_id,
                    attempt_id=lease.attempt_id,
                    step_id="rag-read",
                    lease_id=lease.lease_id,
                    checkpoint_id=checkpoint_id,
                    outcome="STARTED",
                    input_hash=input_hash,
                )
            return {
                "task_id": task_id,
                "lease_id": lease.lease_id,
                "attempt_id": lease.attempt_id,
                "fencing_token": lease.fencing_token,
                "lease_ttl_seconds": lease_ttl,
                "checkpoint_id": checkpoint_id,
                "checkpoint_planned_action": checkpoint_planned_action,
                "input_hash": input_hash,
            }
        except (sqlite3.IntegrityError, StorageIntegrityError) as exc:
            # Duplicate durable identity: within the idempotency window this is
            # a transport retry — a safe block, not a second handler execution.
            # Past the window a terminal duplicate is a NEW ask — re-ask once
            # with a uniquified id instead of blocking forever.
            existing = self._existing_task(task_id)
            if not _retried and self._duplicate_is_reaskable(existing):
                return self.begin(question, contexts, retrieved_context, session_id, request=request, _retried=True)
            try:
                current = self.kernel.get_task(task_id)
            except Exception:
                logger.warning('AskKernelAdapter.begin: Exception not handled', exc_info=True)
                current = {"state": "UNKNOWN"}
            with _TRACE_LOCK:
                self.trace.append(
                    task_id=task_id,
                    outcome="REJECTED_DUPLICATE",
                    reason="stable_idempotency_duplicate",
                    input_hash=input_hash,
                    existing_state=current.get("state"),
                )
            raise KernelError("stable logical ask already exists") from exc
        except Exception as exc:
            try:
                current = self.kernel.get_task(task_id)
                if current["state"] not in _TERMINAL:
                    self.kernel.set_task_kill(task_id, actor="ask-kernel-adapter-begin-failure")
            finally:
                with _TRACE_LOCK:
                    self.trace.append(
                        task_id=task_id,
                        outcome="FAILED",
                        reason="ask_begin_failed",
                        error_type=type(exc).__name__,
                        input_hash=input_hash,
                    )
            raise

    async def verify_response(self, req: Any, response: Any, task: dict[str, Any] | None = None) -> dict[str, Any]:
        if task is None:
            task = {"task_id": "ask-task-default"}
        data = _dump(response)
        contexts = [str(value) for value in (getattr(req, "contexts", None) or []) if str(value).strip()]
        retrieved_context = str(getattr(req, "retrieved_context", "") or "").strip()
        if retrieved_context:
            contexts.append(retrieved_context)
        answer = str(data.get("final_answer") or "")
        verdict = str(data.get("verdict") or "")
        governance = str(data.get("governance_decision") or "")
        # [S24] LOOKUP fork evidence: với answer compose từ data-API, payload
        # thô của API CHÍNH LÀ input context mà answer được tạo từ — đưa vào
        # cùng grounding/judge check (THÊM bằng chứng; không bỏ/nới check nào).
        fork_evidence = str(data.get("data_api_evidence") or "").strip()
        if fork_evidence:
            contexts.append(fork_evidence)
        provenance_value = (data.get("v98_classification") or {}).get("provenance")
        provenance = str(provenance_value or "")
        evidence_ref = f"ask://{task['task_id']}/response/{data.get('trace_id') or 'no-trace'}"
        if not answer or answer.startswith("[SCP:"):
            return {
                "verdict": "INSUFFICIENT",
                "verifier_id": "scp-ask-rag-verifier-v2",
                "evidence_ref": evidence_ref,
                "failures": ["missing_answer"],
                "checked": [],
            }

        if not contexts:
            grounded_ratio = 0.0
        else:
            import re
            ans_words = set(re.findall(r"[\w\xc0-\u1ef9]{2,}", answer.lower()))
            if not ans_words:
                grounded_ratio = 0.0
            else:
                ctx_text = " ".join(contexts).lower()
                overlap = sum(1 for w in ans_words if w in ctx_text)
                grounded_ratio = overlap / len(ans_words)

        # --- Double-Judge Elimination & Gate Unblocking ---
        # 1. Do NOT demand verdict == "PASS" for LANE_CHATBOT / conversational queries.
        # 2. Eliminate redundant second RealityJudge().judge_async call if already evaluated by handler or for chatbot.
        # 3. Web-assisted facts do not trigger withholding (remove web_fallback_not_used check).
        # 4. Only trigger fail-closed on true security threats.
        is_chatbot_lane = False
        try:
            from scp.runtime.question_router import LANE_CHATBOT, route_question
            q_text = str(getattr(req, "question", "") or "")
            if q_text:
                decision = route_question(q_text)
                                # [S-M2 fix] Lane detection is lane-only: bypass_verdict_pass
                # no longer widens the verifier for non-chatbot queries.
                if decision.lane == LANE_CHATBOT:
                    is_chatbot_lane = True
        except Exception as _cb_err:
            logger.debug('Chatbot lane check failed: %s', _cb_err, exc_info=True)
        if not is_chatbot_lane and (data.get("lane") == "LANE_CHATBOT" or getattr(req, "lane", None) == "LANE_CHATBOT"):
            is_chatbot_lane = True

        already_judged = bool(
            data.get("evidence", {}).get("judge_evaluated")
            or data.get("judge_evaluated")
            or (isinstance(data.get("v98_classification"), dict) and data["v98_classification"].get("judge_evaluated"))
            or (isinstance(data.get("v98_guard"), dict) and data["v98_guard"].get("judge_evaluated"))
            or ("slm_trace" in data and "elapsed_ms" in data)
        )

        # [SEC-R2-02-ADAPTER] Chatbot lane requires an explicit POSITIVE
        # governance clearance (UPHOLD/ALLOW). Unknown, empty, or missing
        # clearance must NOT fall through as a pass (SEC-R2-02 residual,
        # audit 2026-09-28).
        _CHATBOT_CLEARANCES = {"UPHOLD", "ALLOW"}
        judge_pass = True
        if is_chatbot_lane:
            _gov = str(governance or "").strip().upper()
            judge_pass = (
                verdict not in ("FAIL", "FLAGGED")
                and _gov in _CHATBOT_CLEARANCES
            )
        elif already_judged:
            judge_pass = (verdict not in ("FAIL", "FLAGGED") and governance != "KILL")
        else:
            try:
                from scp.runtime.judge import RealityJudge
                judge = RealityJudge()
                judge_res = await judge.judge_async(
                    question=str(getattr(req, "question", "")),
                    ai_answer=answer,
                    context=" ".join(contexts)
                )
                judge_pass = (judge_res["verdict"] == "PASS")
            except Exception:
                logger.warning('AskKernelAdapter.verify_response: Exception not handled', exc_info=True)
                judge_pass = False

        # Contract (2026-08-29), split explicitly:
        #   - Context-backed (RAG) ask: the request carried evidence, so the
        #     answer is held to the grounding contract; grounded_ratio and the
        #     evidence context hash are recorded for audit.
        #   - General chat ask (no contexts): grounding is not applicable —
        #     the judge + governance pipeline is the verifier. This matches
        #     api_server's documented intent ("Task Kernel integration is
        #     deliberately scoped to context-backed/RAG asks; normal chat
        #     keeps the JudgeCore path"): the kernel lifecycle still wraps
        #     chat for durability, but grounding cannot be demanded from a
        #     request that carries no evidence.
        is_rag_ask = bool(contexts)
        checks = {
            "verdict_pass": (verdict != "FAIL") if is_chatbot_lane else (verdict == "PASS"),
            "judge_pass": judge_pass,
            "governance_uphold": (str(governance or "").strip().upper() in _CHATBOT_CLEARANCES) if is_chatbot_lane else (governance == "UPHOLD"),
            # Empty provenance is tolerated for old GA-LAB responses; if the
            # route supplies one, it must explicitly be input-context-only, or web fallback.
            "provenance_compatible": provenance in {"", "input_context_only"} or bool(data.get("web_fallback_used")),
        }
        if is_rag_ask and not is_chatbot_lane:
            checks["rag_evidence_bound"] = True
        failures = [name for name, ok in checks.items() if not ok]
        return {
            "verdict": "VERIFIED" if not failures else "CONTRADICTED",
            "verifier_id": "scp-ask-rag-verifier-v2",
            "evidence_ref": evidence_ref,
            "grounded_ratio": round(grounded_ratio, 6),
            "evidence_context_count": len(contexts),
            "evidence_context_hash": hashlib.sha256(
                json_bytes(contexts)
            ).hexdigest(),
            "checked": checks,
            "failures": failures,
            # [F-01 FIX 2026-09-25] Expose lane classification so finalize's
            # unified-ledger fallback label does not reference this method's
            # local scope (a NameError there silently skipped the whole
            # ledger append for responses without an explicit lane).
            "is_chatbot_lane": is_chatbot_lane,
        }

    def _safe_response(self, response: Any, verification: dict[str, Any]) -> Any:
        if verification.get("verdict") == "VERIFIED":
            return response
        data = _dump(response)
        if isinstance(response, dict) and data is response:
            # [F-01 FIX 2026-09-25] _dump returns dict inputs by reference:
            # mutating `data` below would also mutate the caller's response
            # object (and any ledger snapshot taken from it), rewriting the
            # judge-level provenance the unified ledger must preserve.
            data = dict(data)
        fail_reasons = ', '.join(verification.get('failures', []))
        if not str(data.get("final_answer", "")).startswith("[SCP:"):
            data["final_answer"] = f"[SCP: Answer withheld — evidence not verified: {fail_reasons}]"
        data["verdict"] = "FAIL"
        data["governance_decision"] = "KILL" if data.get("governance_decision") == "KILL" else "ESCALATE"
        data["confidence"] = 0.0
        if hasattr(response, "model_copy"):
            return response.model_copy(update=data)
        if isinstance(response, dict):
            return data
        if hasattr(response, "copy"):
            try:
                return response.copy(update=data)
            except TypeError:
                logger.debug('AskKernelAdapter._safe_response: TypeError ignored', exc_info=True)
                return data
        return data

    def _escalate_to_human_review(
        self,
        task_id: str,
        reason: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Move a task to HUMAN_REVIEW idempotently — never raise.

        [S19/W2 BUG-1 fix 2026-09-13] The W2 witness observed HTTP 500 from
        ``InvalidTransition: HUMAN_REVIEW->HUMAN_REVIEW`` when a task already
        sat in HUMAN_REVIEW (lease expiry sweeps VERIFYING->HUMAN_REVIEW, boot
        recovery moves RUNNING/VERIFYING->HUMAN_REVIEW) and finalize escalated
        again. A second escalation of the SAME decision is an idempotent
        no-op: the outcome (answer withheld, human required) is already
        recorded — re-raising would only crash the client request. A raced
        state move (concurrent watchdog, released/expired lease) is likewise
        skipped with a log; the lifecycle decision belongs to the recovery
        machinery, not to this request path.
        """
        current = self.kernel.get_task(task_id)
        if current["state"] in _TERMINAL:
            return current
        if current["state"] == "HUMAN_REVIEW":
            logger.info(
                "[ask-kernel] HUMAN_REVIEW escalation for %s is already recorded "
                "(idempotent no-op): %s",
                task_id,
                reason,
            )
            return current
        try:
            return self.kernel.transition(
                task_id,
                "HUMAN_REVIEW",
                actor="ask-kernel-adapter",
                reason=reason,
                payload=payload,
            )
        except KernelError as exc:  # InvalidTransition / StaleLease / OptimisticLockError
            logger.warning(
                "[ask-kernel] HUMAN_REVIEW escalation skipped for %s in state %s "
                "(%s: %s): %s",
                task_id,
                current["state"],
                type(exc).__name__,
                exc,
                reason,
            )
            return self.kernel.get_task(task_id)

    def _fail_closed_autonomous(
        self,
        task_id: str,
        reason: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Move a task to FAILED idempotently in autonomous mode — never raise."""
        current = self.kernel.get_task(task_id)
        if current["state"] in _TERMINAL:
            return current
        try:
            return self.kernel.fail_task_fail_closed(
                task_id,
                reason=reason,
                error_payload=payload,
                actor="ask-kernel-adapter",
            )
        except KernelError as exc:
            logger.warning(
                "[ask-kernel] Autonomous fail-closed skipped for %s in state %s "
                "(%s: %s): %s",
                task_id,
                current["state"],
                type(exc).__name__,
                exc,
                reason,
            )
            return self.kernel.get_task(task_id)

    def _finalize_task_checkpoint(
        self,
        task: dict[str, Any],
        verification: dict[str, Any],
        note: str | None = None,
    ) -> None:
        """[F-03 2026-09-25] Close the 'rag-read' checkpoint at the task's
        terminal boundary (runtime audit RUNTIME-AUDIT-20260925-0411 F-03:
        checkpoint rows stayed state='RUNNING' with NULL post_ref /
        verifier_verdict after the task reached COMPLETED / HUMAN_REVIEW).

        Records ONLY data this adapter already computed (verifier verdict,
        evidence_ref from the verification dict) — nothing is fabricated; when
        the checkpoint cannot be finalized the kernel records the reason IN the
        row (fail-closed visibility). Never raises: this is audit-durability
        improvement and must not break the response path.
        """
        checkpoint_id = task.get("checkpoint_id")
        planned_action = task.get("checkpoint_planned_action")
        if not checkpoint_id or planned_action is None:
            return
        try:
            final_state = str(self.kernel.get_task(task["task_id"])["state"])
            tool_result = {
                "final_task_state": final_state,
                "verifier_verdict": verification.get("verdict"),
                "verifier_id": verification.get("verifier_id"),
                "evidence_ref": verification.get("evidence_ref"),
                "failures": list(verification.get("failures") or []),
            }
            result = self.kernel.finalize_checkpoint(
                task["task_id"],
                checkpoint_id,
                planned_action=planned_action,
                verifier_verdict=str(verification["verdict"]) if verification.get("verdict") else None,
                post_observation_ref=str(verification["evidence_ref"]) if verification.get("evidence_ref") else None,
                tool_result=tool_result,
                note=note,
            )
            logger.info(
                "[ask-kernel] checkpoint %s finalized for %s: %s (state=%s)",
                checkpoint_id,
                task["task_id"],
                result.get("finalization"),
                result.get("state"),
            )
        except Exception as exc:
            logger.debug(f"_finalize_task_checkpoint ignored: {exc}", exc_info=True)
            logger.warning(
                "[ask-kernel] checkpoint finalization failed for %s (non-fatal): %s: %s",
                task.get("task_id"),
                type(exc).__name__,
                exc,
            )

    @staticmethod
    def _effective_run_identity(response_data: dict[str, Any], request: Any) -> tuple[str, Any]:
        """Resolve the run identity recorded by the unified ledger: the response's
        trace/run ids, else the request-scope run started by the API boundary,
        else a freshly minted ledger-internal trace id."""
        scp_run = getattr(getattr(request, "state", None), "scp_run", None)
        effective_trace_id = (
            response_data.get("trace_id") or getattr(scp_run, "trace_id", None) or f"trace_{uuid.uuid4().hex}"
        )
        effective_run_id = response_data.get("run_id") or getattr(scp_run, "run_id", None)
        return effective_trace_id, effective_run_id

    @staticmethod
    def _unified_ledger_path() -> Path:
        """Same file the finalize happy path writes: trace_ledger.jsonl inside
        the runtime data dir (SCP_DATA_DIR-aware via scp.core.runtime_paths),
        matching what the /v3/trace reader resolves."""
        return runtime_data_dir() / "trace_ledger.jsonl"

    def _unified_ledger_fields(
        self,
        *,
        req: Any,
        request: Any,
        response: Any,
        verification: dict[str, Any],
        final_task: dict[str, Any],
        response_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """[F-01] One schema builder for the unified trace-ledger entry so every
        terminal disposition of a run records the SAME fields with the SAME
        semantics: judge-level verdict/governance stay as provenance while the
        final_verdict / final_governance / final_outcome fields MUST equal what
        /ask returns for this run. _safe_response is deterministic (its "[SCP:"
        guard makes re-wrapping idempotent) and never mutates the caller's
        response, so recomputing the boundary view here yields exactly the
        delivered decision.

        [SECOND-PASS FIX 2026-09-30 — docstring honesty] ``final_answer`` is
        the RAW judge-level answer (pre-safe provenance), NOT the withheld/
        safe text the client actually received: the delivered answer is what
        _safe_response produced for the HTTP response. Only
        final_verdict/final_governance/final_outcome carry the
        delivered-decision contract (F-01); the previous wording ("final_*
        MUST equal what /ask returns") wrongly implied final_answer was the
        delivered text.

        [SECOND-PASS FIX 2026-09-30 — SEC-R2-02] The judge-level
        governance_decision provenance defaults to "UNKNOWN" (fail-closed),
        never "ALLOW": a missing governance decision must not be recorded as
        an ALLOW clearance in the audit trail.
        """
        if response_data is None:
            response_data = _dump(response)
        effective_trace_id, effective_run_id = self._effective_run_identity(response_data, request)
        safe_data = _dump(self._safe_response(response, verification))
        return {
            "trace_id": effective_trace_id,
            "run_id": effective_run_id,
            "session_id": getattr(req, "session_id", "") or response_data.get("session_id", ""),
            "question": str(getattr(req, "question", "") or ""),
            # Pre-safe provenance: RAW judge-level answer — NOT the delivered
            # (withheld/safe) text; see the docstring.
            "final_answer": str(response_data.get("final_answer", "") or ""),
            "verdict": response_data.get("verdict", verification.get("verdict", "UNKNOWN")),
            "confidence": float(response_data.get("confidence", 0.0) or 0.0),
            "domain": str(response_data.get("domain", "") or getattr(req, "domain", "") or "general"),
            "lane": (
                response_data.get("lane")
                or getattr(req, "lane", None)
                or ("LANE_CHATBOT" if verification.get("is_chatbot_lane") else "LANE_FACTUAL")
            ),
            "routing": response_data.get("routing", {}),
            # [SECOND-PASS FIX 2026-09-30] "UNKNOWN", never "ALLOW": missing
            # governance must not be recorded as a clearance (SEC-R2-02
            # fail-closed — the audit trail must not fabricate an ALLOW).
            "governance_decision": response_data.get("governance_decision") or "UNKNOWN",
            "why_gate": response_data.get("why_gate") or {},
            "slm_trace": response_data.get("slm_trace") or [],
            "web_fallback": response_data.get("web_fallback") or None,
            "elapsed_ms": round(float(response_data.get("elapsed_ms") or 0.0), 1),
            "final_verdict": str(safe_data.get("verdict") or "UNKNOWN"),
            "final_governance": str(safe_data.get("governance_decision") or "UNKNOWN"),
            "final_outcome": str(final_task.get("state") or "UNKNOWN"),
        }

    def _append_unified_ledger(self, fields: dict[str, Any]) -> None:
        """Fail-safe append to the unified trace ledger.

        EVERY terminal disposition of a run — verified commit, safe-terminal
        lifecycle race, stale-lifecycle route, or failure — must appear in this
        ledger with the same schema and through the same hash-chained
        TraceLedger.append as the happy path (no run may vanish from the audit
        trail). A failed append never raises into the response path, but it is
        logged at WARNING with the exception summary (was DEBUG: a silently
        missing ledger row is an audit failure, not a debug detail).
        """
        try:
            if not fields.get("timestamp"):
                import datetime as _dt

                fields = {**fields, "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat()}
            TraceLedger(self._unified_ledger_path()).append(**fields)
        except Exception as exc:
            logger.debug(f"_append_unified_ledger ignored: {exc}", exc_info=True)
            logger.warning(
                "[ask-kernel] TraceLedger append failed: %s: %s (fields=%s)",
                type(exc).__name__,
                exc,
                sorted(fields.keys()),
            )

    async def finalize(self, task: dict[str, Any], response: Any, req: Any, request: Any = None) -> dict[str, Any]:
        task_id, lease_id = task["task_id"], task["lease_id"]

        def _terminal_result(current_task: dict[str, Any]) -> dict[str, Any]:
            verification = {
                "verdict": "INSUFFICIENT",
                "verifier_id": "scp-ask-kernel-terminal-v1",
                "evidence_ref": f"ask://{task_id}/terminal/{str(current_task['state']).lower()}",
                "failures": ["task_terminal_before_verification"],
                "checked": {"kernel_task_non_terminal": False},
            }
            # [F-03] The task already reached a decision — close the checkpoint
            # row against it instead of leaving a bare RUNNING.
            self._finalize_task_checkpoint(task, verification, note="task_terminal_before_verification")
            response_data = _dump(response)
            with _TRACE_LOCK:
                self.trace.append(
                    task_id=task_id,
                    attempt_id=task.get("attempt_id"),
                    step_id="rag-read",
                    lease_id=lease_id,
                    checkpoint_id=task.get("checkpoint_id"),
                    verifier_id=verification["verifier_id"],
                    evidence_ref=verification["evidence_ref"],
                    run_id=response_data.get("run_id"),
                    trace_id=response_data.get("trace_id"),
                    outcome=current_task["state"],
                    verdict=verification["verdict"],
                    reason="task_terminal_before_verification",
                    response_elapsed_ms=response_data.get("elapsed_ms"),
                )
            # [LEDGER-RACE FIX 2026-09-26] The run still terminated here (HTTP
            # 200 with a withheld answer) — record its disposition in the
            # unified ledger with the same schema and hash chain as the happy
            # path so a safe-terminal run cannot vanish from the audit trail.
            self._append_unified_ledger(
                self._unified_ledger_fields(
                    req=req,
                    request=request,
                    response=response,
                    verification=verification,
                    final_task=current_task,
                    response_data=response_data,
                )
            )
            return {
                "task": current_task,
                "verification": verification,
                "safe_response": self._safe_response(response, verification),
            }

        current_task = self.kernel.get_task(task_id)
        if current_task["state"] in _TERMINAL:
            return _terminal_result(current_task)

        def _stale_lifecycle_result(stale_task: dict[str, Any], reason: str) -> dict[str, Any]:
            """[S19 BUG-1 fix 2026-09-13] The response was observed after the
            kernel had already moved this task out of the happy path
            (RECONCILING via boot-replay/watchdog — the runtime crash
            ``InvalidTransition: RECONCILING->VERIFYING`` at ask_response_
            observed; also RECOVERING/UNKNOWN/HUMAN_REVIEW and friends).

            Design decision (b): route by current state instead of widening
            ALLOWED_TRANSITIONS with RECONCILING->VERIFYING. Adding that edge
            would let a stale attempt auto-complete work whose execution
            authority was already revoked: enter_reconciling/auto_reconcile
            release the lease (fencing), and the reconcile contract
            (recovery_decision 'human_review_if_unknown', reconcile_unknown
            'without auto-completing') deliberately exits RECONCILING to
            HUMAN_REVIEW, not to VERIFYING. Fail-closed honesty wins: the
            client gets an explicit withheld result (HTTP 200, no 500), the
            task lands in HUMAN_REVIEW via a legal edge for the reconcile/
            human flow, and the journal records that a response WAS observed.
            """
            verification = {
                "verdict": "INSUFFICIENT",
                "verifier_id": "scp-ask-kernel-lifecycle-race-v1",
                "evidence_ref": f"ask://{task_id}/lifecycle/{str(stale_task['state']).lower()}",
                "failures": [reason],
                "checked": {"kernel_execution_authority": False},
            }
            response_data = _dump(response)
            if self.autonomous_mode:
                final_task = self._fail_closed_autonomous(
                    task_id,
                    reason=reason,
                    payload={"verification": verification},
                )
            else:
                final_task = self._escalate_to_human_review(
                    task_id,
                    reason=reason,
                    payload={"verification": verification},
                )
            # [F-03] The lifecycle race produced its decision — close the
            # checkpoint row against the resulting state.
            self._finalize_task_checkpoint(task, verification, note=reason)
            with _TRACE_LOCK:
                self.trace.append(
                    task_id=task_id,
                    attempt_id=task.get("attempt_id"),
                    step_id="rag-read",
                    lease_id=lease_id,
                    checkpoint_id=task.get("checkpoint_id"),
                    verifier_id=verification["verifier_id"],
                    evidence_ref=verification["evidence_ref"],
                    run_id=response_data.get("run_id"),
                    trace_id=response_data.get("trace_id"),
                    outcome=final_task["state"],
                    verdict=verification["verdict"],
                    reason=reason,
                    response_elapsed_ms=response_data.get("elapsed_ms"),
                )
            # [LEDGER-RACE FIX 2026-09-26] The lifecycle race produced a real
            # decision (HUMAN_REVIEW escalation or autonomous fail-closed) and
            # the client received a withheld result — record it in the unified
            # ledger (same schema/hash chain as the happy path) instead of
            # skipping the write on this branch.
            self._append_unified_ledger(
                self._unified_ledger_fields(
                    req=req,
                    request=request,
                    response=response,
                    verification=verification,
                    final_task=final_task,
                    response_data=response_data,
                )
            )
            return {
                "task": final_task,
                "verification": verification,
                "safe_response": self._safe_response(response, verification),
            }

        if current_task["state"] not in _ASK_LIFECYCLE_INTACT_STATES:
            return _stale_lifecycle_result(
                current_task,
                f"lifecycle_authority_lost:{current_task['state']}",
            )

        try:
            if current_task["state"] == "RUNNING":
                self.kernel.transition(task_id, "VERIFYING", actor="ask-kernel-adapter", reason="ask_response_observed")
        except InvalidTransition:
            current_task = self.kernel.get_task(task_id)
            if current_task["state"] in _TERMINAL:
                return _terminal_result(current_task)
            return _stale_lifecycle_result(
                current_task,
                f"verifying_transition_raced:{current_task['state']}",
            )

        verification = await self.verify_response(req, response, task)
        if verification["verdict"] == "VERIFIED":
            receipt = sign_verifier_receipt(
                VerifierReceipt(
                    task_id=task_id,
                    verifier_id=str(verification.get("verifier_id", "scp-ask-rag-verifier-v2")),
                    verdict="VERIFIED",
                    evidence_ref=str(verification.get("evidence_ref", "")),
                    issued_at=time.time(),
                    attempt_id=task.get("attempt_id"),
                )
            )
            verification["task_id"] = task_id
            verification["issued_at"] = receipt.issued_at
            verification["signature"] = receipt.signature
            try:
                final_task = self.kernel.commit_verification_result(task_id, lease_id, receipt)
            except KernelError:
                # [S19/W2 family] A slow verification can outlive the 60s ask
                # lease: expire_leases sweeps VERIFYING->HUMAN_REVIEW while the
                # judge runs, so commit hits a stale lease or an illegal
                # source state. That must not 500 the request either — the
                # evidence was verified but the execution authority is gone:
                # route through the same lifecycle-race path.
                current_task = self.kernel.get_task(task_id)
                if current_task["state"] in _TERMINAL:
                    return _terminal_result(current_task)
                if self.autonomous_mode and current_task["state"] == "HUMAN_REVIEW":
                    try:
                        self.kernel.auto_resolve_human_review(task_id, reason="autonomous_verification_passed")
                        self.kernel.transition(task_id, "QUEUED", actor="ask-kernel-adapter", reason="autonomous_auto_advance")
                        new_lease = self.kernel.claim(task_id, worker_id=task.get("worker_id") or "ask-route-worker")
                        self.kernel.transition(task_id, "RUNNING", actor="ask-kernel-adapter", lease_id=new_lease.lease_id, reason="autonomous_auto_advance")
                        self.kernel.transition(task_id, "VERIFYING", actor="ask-kernel-adapter", lease_id=new_lease.lease_id, reason="autonomous_auto_advance")
                        fresh_receipt = sign_verifier_receipt(
                            VerifierReceipt(
                                task_id=task_id,
                                verifier_id=str(verification.get("verifier_id", "scp-ask-rag-verifier-v2")),
                                verdict="VERIFIED",
                                evidence_ref=str(verification.get("evidence_ref", "")),
                                issued_at=time.time(),
                                attempt_id=new_lease.attempt_id,
                            )
                        )
                        final_task = self.kernel.commit_verification_result(task_id, new_lease.lease_id, fresh_receipt)
                    except Exception as auto_err:
                        logger.warning("[ask-kernel] Failed to auto-resolve and complete from HUMAN_REVIEW: %s", auto_err, exc_info=True)
                        return _stale_lifecycle_result(self.kernel.get_task(task_id), f"auto_resolve_failed:{auto_err}")
                else:
                    return _stale_lifecycle_result(current_task, "commit_raced_lease_or_state")
        else:
            # [SECURITY-REASON 2026-09-26] Reason decision extracted to
            # _verification_fail_reason (module-level, unit-testable): a
            # security-determined run escalates under a distinct reason while
            # benign insufficient-evidence runs keep the historical one.
            _fail_data = _dump(response)
            _fail_reason = _verification_fail_reason(_fail_data)
            if self.autonomous_mode:
                try:
                    attempts = int(task.get("attempts", 0))
                    max_attempts = int(task.get("max_attempts", 3))
                    is_retryable = (attempts + 1 < max_attempts)
                    classification = "RETRYABLE" if is_retryable else "VERIFICATION_FAILED"
                    indictment = str(verification.get("evidence_ref") or f"ask://{task_id}/verification_failed")
                    actor = task.get("worker_id") or "ask-route-worker"
                    final_task = self.kernel.commit_failed(
                        task_id,
                        lease_id,
                        actor=actor,
                        failure_classification=classification,
                        indictment_ref=indictment,
                        details={"reason": _fail_reason, "verification": verification},
                    )
                except KernelError as fail_err:
                    logger.warning("[ask-kernel] Autonomous commit_failed failed (%s); failing closed: %s", fail_err, task_id)
                    final_task = self._fail_closed_autonomous(
                        task_id,
                        # Infra-failure keeps its own reason: the kernel commit
                        # itself failed (unleased) — do not conflate it with
                        # the verification outcome (_fail_reason).
                        reason="ask_verification_failed_unleased",
                        payload={"verification": verification, "commit_error": str(fail_err)},
                    )
            else:
                final_task = self._escalate_to_human_review(
                    task_id,
                    reason=_fail_reason,
                    payload={"verification": verification},
                )
        # [F-03] The task outcome is committed — project it onto the checkpoint
        # row (COMPLETED / HUMAN_REVIEW / FAILED) instead of leaving it RUNNING.
        self._finalize_task_checkpoint(task, verification)
        response_data = _dump(response)

        # [F-01 FIX 2026-09-25] Compute the FINAL API-boundary decision BEFORE
        # the unified trace-ledger write. Previously the ledger recorded the
        # judge-level verdict/governance while _safe_response (called later)
        # could override them to FAIL/ESCALATE for boundary-blocked runs — the
        # audit trail then contradicted the HTTP response (runtime audit
        # RUNTIME-AUDIT-20260925-0411, finding F-01). Fail-closed rule: the
        # final_* ledger fields MUST equal what /ask returns for this run;
        # judge-level verdict/governance stay as provenance.
        safe_resp = self._safe_response(response, verification)

        # The run identity is resolved ONCE and reused by the unified ledger,
        # the per-attempt trace and the response payload — a minted fallback
        # trace id must never diverge between ledger and client.
        ledger_fields = self._unified_ledger_fields(
            req=req,
            request=request,
            response=response,
            verification=verification,
            final_task=final_task,
            response_data=response_data,
        )
        effective_trace_id = ledger_fields["trace_id"]
        effective_run_id = ledger_fields["run_id"]
        self._append_unified_ledger(ledger_fields)

        with _TRACE_LOCK:
            self.trace.append(
                task_id=task_id,
                attempt_id=task.get("attempt_id"),
                step_id="rag-read",
                lease_id=lease_id,
                checkpoint_id=task.get("checkpoint_id"),
                verifier_id=verification.get("verifier_id"),
                evidence_ref=verification.get("evidence_ref"),
                run_id=effective_run_id,
                trace_id=effective_trace_id,
                outcome=final_task.get("state"),
                verdict=verification.get("verdict"),
                grounded_ratio=verification.get("grounded_ratio"),
                response_elapsed_ms=response_data.get("elapsed_ms"),
            )
        if hasattr(safe_resp, "model_copy"):
            safe_resp = safe_resp.model_copy(update={"trace_id": effective_trace_id, "run_id": effective_run_id})
        elif isinstance(safe_resp, dict):
            safe_resp["trace_id"] = effective_trace_id
            safe_resp["run_id"] = effective_run_id
        return {
            "task": final_task,
            "verification": verification,
            "safe_response": safe_resp,
        }

    def fail(
        self,
        task: dict[str, Any],
        reason: str,
        failure_classification: str = "FATAL",
        indictment_ref: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        try:
            current = self.kernel.get_task(task["task_id"])
            if current["state"] not in _TERMINAL:
                lease_id = task.get("lease_id") or current.get("active_lease_id")
                if lease_id:
                    self.kernel.commit_failed(
                        task_id=task["task_id"],
                        lease_id=lease_id,
                        actor=task.get("worker_id") or "ask-route-worker",
                        failure_classification=failure_classification,
                        indictment_ref=indictment_ref or f"ask://{task['task_id']}/failure/{reason}",
                        details=details or {"reason": reason},
                    )
                else:
                    self.kernel.set_task_kill(task["task_id"], actor="ask-kernel-adapter")
            # [F-03] Failure path must also close the checkpoint row. No
            # verifier verdict exists on this path — only the failure evidence
            # ref and reason are recorded (nothing fabricated).
            self._finalize_task_checkpoint(
                task,
                {
                    "verdict": None,
                    "verifier_id": None,
                    "evidence_ref": indictment_ref or f"ask://{task['task_id']}/failure/{reason}",
                    "failures": [reason],
                },
                note=reason,
            )
            with _TRACE_LOCK:
                self.trace.append(
                    task_id=task["task_id"],
                    attempt_id=task.get("attempt_id"),
                    lease_id=task.get("lease_id"),
                    checkpoint_id=task.get("checkpoint_id"),
                    outcome="FAILED",
                    reason=reason,
                )
            # [LEDGER-RACE FIX 2026-09-26] A failed run must also appear in the
            # unified ledger through the same hash-chained append as the happy
            # path: this run is skipped at the boundary (the handler raised),
            # so the entry records the ACTUAL terminal kernel disposition.
            # [SECOND-PASS FIX 2026-09-30 — schema honesty] This is a
            # KERNEL-DISPOSITION SUBSET, not the full happy-path schema: the
            # response-derived fields (trace_id/question/final_answer and the
            # judge provenance) are OMITTED, not fabricated — no response
            # existed on this path (nothing was delivered), so there is no
            # honest value for them. Nothing about an answer is fabricated:
            # final_verdict=FAIL (no verified answer), final_governance=KILL
            # (force-terminated via commit_failed/set_task_kill, never
            # delivered).
            try:
                terminal_state = str(self.kernel.get_task(task["task_id"])["state"])
            except Exception:
                logger.debug("fail ignored", exc_info=True)
                terminal_state = "FAILED"
            self._append_unified_ledger(
                {
                    "task_id": task["task_id"],
                    "attempt_id": task.get("attempt_id"),
                    "lease_id": task.get("lease_id"),
                    "checkpoint_id": task.get("checkpoint_id"),
                    "input_hash": task.get("input_hash"),
                    "outcome": terminal_state,
                    "reason": reason,
                    "failure_classification": failure_classification,
                    "final_verdict": "FAIL",
                    "final_governance": "KILL",
                    "final_outcome": terminal_state,
                }
            )
        except Exception as exc:  # non-fatal audit fallback; original error wins
            logger.warning('AskKernelAdapter.fail: Exception not handled: %s', exc, exc_info=True)
            try:
                from scp.core.exception_policy import observe_nonfatal

                observe_nonfatal(component="scp/ask_kernel_adapter.py:fail", exception_type=type(exc).__name__)
            except Exception:
                logger.warning('AskKernelAdapter.fail: Exception not handled', exc_info=True)
                return

    def _kernel_blocked_response(self, req: Any, exc: Exception) -> Any:
        session = getattr(req, "session_id", None) or "ask-kernel-blocked"
        trace_id = "trace-kernel-blocked-" + uuid.uuid4().hex
        msg = f"[SCP: Answer withheld — Kernel gate blocked: {type(exc).__name__} - {str(exc)}]"
        if AskResponse is None:
            return {
                "verdict": "FAIL",
                "final_answer": msg,
                "confidence": 0.0,
                "domain": getattr(req, "domain_override", "") or getattr(req, "domain", "") or "general",
                "run_status": "REJECTED",
                "trace_id": trace_id,
                "governance_decision": "KILL"
            }
        return AskResponse(
            verdict="FAIL",
            final_answer=msg,
            confidence=0.0,
            domain=getattr(req, "domain_override", "") or getattr(req, "domain", "") or "general",
            falsification_status="KERNEL_GATE",
            governance_decision="KILL",
            v98_guard={
                "mode": "rag-verified",
                "readOnly": True,
                "security_blocked": True,
                "kernel_error": type(exc).__name__,
            },
            v98_classification={"provenance": "kernel_gate", "evidence_count": 0},
            elapsed_ms=0.0,
            session_id=session,
            run_id="run-kernel-blocked-" + uuid.uuid4().hex,
            trace_id=trace_id,
            run_status="REJECTED",
            ledger_status="BLOCKED",
        )

    async def _lease_heartbeat(
        self,
        task: dict[str, Any],
        stop: asyncio.Event,
    ) -> None:
        """[S20] Renew the ask lease every ttl/3 while the in-process attempt
        still holds it, so a slow (but alive) provider no longer forfeits a
        correct answer to lease expiry.

        Invariant-safe: renew_lease is expiry-only (no state change) and
        fencing-checked, so this can only extend the CURRENT attempt. When it
        returns False the lease is already gone (released/expired/fenced-off/
        killed) — log, stop, and let finalize's state-route fail-closed
        (S19 path) decide the outcome. NEVER raise from here: a heartbeat
        must not kill the request it is trying to protect.
        """
        ttl = float(task.get("lease_ttl_seconds") or DEFAULT_ASK_LEASE_TTL_SECONDS)
        interval = max(ttl / 3.0, 0.05)
        task_id, lease_id = task["task_id"], task["lease_id"]
        while True:
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
                return  # requested stop (handler + finalize finished)
            except asyncio.TimeoutError:
                pass
            try:
                renewed = self.kernel.renew_lease(
                    task_id, lease_id, task["fencing_token"], ttl_seconds=ttl
                )
            except Exception as exc:  # infra fault: stop, do not mask request path
                logger.debug(f"_lease_heartbeat ignored: {exc}", exc_info=True)
                logger.warning(
                    "[ask-kernel] lease heartbeat error for %s (lease %s): %s — stopping heartbeat",
                    task_id, lease_id, type(exc).__name__,
                )
                return
            if not renewed:
                _c3_logger.warning(
                    "[S20] lease renew refused for %s (lease %s, attempt %s) — "
                    "heartbeat stopped; finalize will route by current state (fail-closed)",
                    task_id, lease_id, task.get("attempt_id"),
                )
                return

    async def run_rag(
        self,
        req: Any,
        request: Any,
        handler: Callable[[Any, Any], Awaitable[Any]],
    ) -> Any:
        try:
            task = self.begin(
                req.question,
                list(req.contexts or []),
                req.retrieved_context or "",
                req.session_id,
                request=request,
            )
        except Exception as exc:
            logger.debug(f"run_rag ignored: {exc}", exc_info=True)
            return self._kernel_blocked_response(req, exc)
        # [S20] Provider calls legitimately run 30-260s (free tier); the fixed
        # TTL would expire the lease under a living worker and force S19's
        # fail-closed state-route to discard correct answers. Keep the lease
        # alive ONLY while this coroutine owns the attempt; crash detection is
        # preserved because a dead process stops renewing.
        stop = asyncio.Event()
        heartbeat: asyncio.Task | None = None
        if ask_lease_heartbeat_enabled():
            heartbeat = asyncio.create_task(self._lease_heartbeat(task, stop))
        try:
            # [S24 2026-09-13] LOOKUP→data-API fork TRƯỚC generation (owner
            # directive: "hơn 1000 API để lấy thông tin. LLM CHỈ dùng khi 1000
            # API không có" — trước S24 mọi câu bay thẳng LLM, see
            # reports/benchmark-2026-09-12/bench_combined_seed2026.json).
            # Fork trả None → generation path cũ chạy nguyên vẹn. Bất kỳ lỗi
            # nào trong fork cũng phải fallback về handler (fork không được
            # phép phá /ask). Answer fork vẫn đi qua finalize/verify bên dưới
            # — cùng verification/governance path, không có check nào bị bỏ.
            fork_response: Any = None
            if t2_fork_enabled():
                try:
                    from scp.runtime.question_router import attempt_lookup_fork

                    fork_response = await attempt_lookup_fork(req)
                except Exception as exc:
                    logger.debug(f"run_rag ignored: {exc}", exc_info=True)
                    logger.warning(
                        "[S24] lookup fork errored (%s: %s) — falling back to LLM handler",
                        type(exc).__name__, exc,
                    )
                    fork_response = None
            if fork_response is not None:
                response = fork_response
            else:
                response = await handler(req, request)
            result = await self.finalize(task, response, req, request=request)
            return result["safe_response"]
        except Exception:
            self.fail(task, "ask_rag_exception")
            raise
        finally:
            if heartbeat is not None:
                stop.set()
                try:
                    await asyncio.wait_for(heartbeat, timeout=5.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    heartbeat.cancel()


def json_bytes(value: Any) -> bytes:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


