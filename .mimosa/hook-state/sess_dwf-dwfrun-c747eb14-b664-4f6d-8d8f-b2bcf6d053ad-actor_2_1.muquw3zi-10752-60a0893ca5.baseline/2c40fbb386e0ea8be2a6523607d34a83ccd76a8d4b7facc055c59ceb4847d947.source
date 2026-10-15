# SCP CIRCUIT: M03 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M03-closure.json)
"""
[Task 8-A] V105 AutoFix endpoints Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â extracted from api_server.py

TĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â I SAO: api_server.py 2,144 LOC god file. T-Ă¢â‚¬Â-Ă‚Â¡ch 6 routes /v105/* v-Ă¢â‚¬Â-Ă‚Â o module
n-Ă¢â‚¬Â-Ă‚Â y. Backward-compatible Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â public API paths/methods unchanged.

Routes:
  GET  /v105/autofix/permissions                          Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â List pending permission requests
  POST /v105/autofix/permissions/{request_id}/approve     Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â Human approves a fix
  POST /v105/autofix/permissions/{request_id}/deny        Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â Human denies a fix
  POST /v105/autofix/attack-mode/{enabled}                Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â Toggle attack mode
  GET  /v105/autofix/stats                                Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â AutoFix engine stats
  POST /v105/autofix/run-audit                            Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â Trigger deep audit cycle
  GET  /v105/autofix/monitor                              Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â [OPT-31] AutoFixMonitor stats (success rate by bug_type/provider/diagnosis)
  POST /v105/autofix/cleanup-cache                        Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â [OPT-32] Remove legacy broken SmartCache disk entries
  POST /v105/autofix/rollback/{rollback_token}            Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â  Revert a specific auto-approved fix
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Literal

# [AUDIT-20260909 M3] `Request` is REQUIRED here: rag_query(request: Request)
# relies on it, but with `from __future__ import annotations` the missing
# import left an unresolvable ForwardRef that made app.openapi() fail with
# PydanticUserError "class not fully defined" (import-order contract probe).
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

# Import shared deps from api_server (same pattern as api/chat.py + admin_v98.py)
from scp.api._shared import verify_admin
from scp.core.subsystem_telemetry import SubsystemTelemetry

logger = logging.getLogger("scp.api.v105")

from scp.core.request_run_ledger import RequestRunLedger, traced_request

_V105_ROUTES_LEDGER = RequestRunLedger()

router = APIRouter(tags=["v105"])


class AutoFixAuditRequest(BaseModel):
    """Bounded audit request; observe mode never writes source files."""

    mode: Literal["apply", "observe"] = "apply"
    max_bugs: int = 0


@router.get("/v105/autofix/permissions", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=False, action="v105_list_permissions")
async def v105_list_permissions():
    """List pending permission requests (logic bugs awaiting human approval)."""
    try:
        # [EXEC-1 A2] TĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â I SAO: was `AutoFixEngine()` per-request Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ throwaway
        # instance Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ attack_mode / rate limits / cooldowns were all no-ops.
        # Use singleton so state persists across handlers.
        from scp.autofix.engine import get_autofix_engine
        eng = get_autofix_engine()
        pending = eng.permission_gate.list_pending()
        return {
            "pending": [
                {
                    "request_id": r.request_id,
                    "file": r.file,
                    "line": r.line,
                    "bug_type": r.bug_type,
                    "description": r.description,
                    "suggested_fix": r.suggested_fix,
                    "timestamp": r.timestamp,
                }
                for r in pending
            ],
            "count": len(pending),
        }
    except Exception as e:
        raise HTTPException(500, f"Error: {e}") from e


@router.post("/v105/autofix/permissions/{request_id}/approve", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=True, action="v105_approve_permission")
async def v105_approve_permission(request_id: str, note: str = ""):
    """Human approves a logic bug fix. SCP then applies it.

    [OPT-14 / G-Ă¢â‚¬Â-Ă‚Â  Ă„â€Ă¢â‚¬Â-Ă‚Â§11] The `note` field is checked by UnderstandingChecker Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â
    the human must explain what the fix does in their own words. Empty,
    trivial, or copy-paste notes are rejected with HTTP 400 (the request
    was found, but understanding was not demonstrated).

    [Phase 5-A / 4-a-009] Transactional apply:
      Pre-fix: approve() committed, then apply_approved_fix() called. If
        apply raised (LLM fix fails, file write fails, etc.), the approval
        was already persisted (status="approved") but the fix was never
        applied Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ "approved-but-not-applied" limbo. The request was no
        longer pending (so couldn't be re-approved via this endpoint) and
        not applied (so the bug remained). Stuck state. DNA #8/#9.
      Post-fix: apply wrapped in try/except. On success Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ status="applied"
        (terminal). On exception Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ status="apply_failed" (recoverable Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â
        operator can re-approve via this endpoint; approve() will re-set
        status to "approved" and the apply retried). Audit trail records
        the error message for operator diagnosis (DNA #8 KB accumulation).
    """
    try:
        # [EXEC-1 A2] singleton Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â see v105_list_permissions
        from scp.autofix.engine import get_autofix_engine
        eng = get_autofix_engine()
        # Pre-check: is the request even in the pending dict? If not, 404.
        if request_id not in eng.permission_gate._pending:
            raise HTTPException(404, "Permission request not found")
        ok = eng.permission_gate.approve(request_id, decided_by="api_admin", note=note)
        if not ok:
            # [OPT-14 / G-Ă¢â‚¬Â-Ă‚Â  Ă„â€Ă¢â‚¬Â-Ă‚Â§11] approve() returned False Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â either not found
            # (handled above) or understanding check failed. The latter means
            # the human note didn't demonstrate understanding of the fix.
            raise HTTPException(
                400,
                "Approval rejected — note does not demonstrate understanding. "
                "Re-approve with a real explanation in your own words: "
                "explain what the fix does, not just repeat the suggested_fix text."
            )
        # [Phase 5-A / 4-a-009] Apply the approved fix Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â TRANSACTIONAL.
        # On success: mark_apply_status(request_id, "applied") Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â terminal.
        # On exception: mark_apply_status(request_id, "apply_failed", error=...)
        #   Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ recoverable (operator re-approves via this endpoint; approve()
        #   re-sets status to "approved" and apply is retried). Pre-fix the
        #   request would have been stuck in "approved-but-not-applied" limbo.
        try:
            result = eng.apply_approved_fix(request_id)
        except Exception as apply_exc:
            eng.permission_gate.mark_apply_status(
                request_id, "apply_failed", error=str(apply_exc)
            )
            logger.error(
                f"[v105_approve_permission] apply_failed for {request_id}: "
                f"{apply_exc}"
            )
            raise HTTPException(
                500,
                f"Approved but fix apply FAILED: {apply_exc}. Request "
                f"marked apply_failed — operator can re-approve via this "
                f"endpoint (transactional recovery)."
            ) from apply_exc
        # Apply succeeded Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â mark as applied (terminal). This distinguishes
        # from the pre-fix limbo where "approved" meant "approved-but-maybe-
        # not-applied" Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â now "approved" means pending_apply, "applied" means
        # success, "apply_failed" means recoverable failure.
        eng.permission_gate.mark_apply_status(request_id, "applied")
        return {"approved": True, "applied": True, "fix_result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {e}") from e


@router.post("/v105/autofix/permissions/{request_id}/deny", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=True, action="v105_deny_permission")
async def v105_deny_permission(request_id: str, note: str = ""):
    """Human denies a logic bug fix. SCP does not apply it."""
    try:
        # [EXEC-1 A2] singleton Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â see v105_list_permissions
        from scp.autofix.engine import get_autofix_engine
        eng = get_autofix_engine()
        ok = eng.permission_gate.deny(request_id, decided_by="api_admin", note=note)
        if not ok:
            raise HTTPException(404, "Permission request not found")
        return {"denied": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {e}") from e


@router.post("/v105/autofix/attack-mode/{enabled}", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=True, action="v105_toggle_attack_mode")
async def v105_toggle_attack_mode(enabled: bool):
    """Toggle attack mode. When ON, SCP auto-applies restraints (Tier 4).
    Use during active attacks Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â SCP reacts faster than human review."""
    try:
        # [EXEC-1 A2] singleton Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â CRITICAL: with per-request AutoFixEngine(),
        # attack_mode toggle was LOST on next request (new engine defaulted to
        # False). Singleton persists the toggle across all handlers + runner.
        from scp.autofix.engine import get_autofix_engine
        eng = get_autofix_engine()
        eng.set_attack_mode(enabled)
        return {
            "attack_mode": enabled,
            "message": f"Attack mode {'ENABLED — SCP auto-applies restraints' if enabled else 'DISABLED — normal permission flow'}",
        }
    except Exception as e:
        raise HTTPException(500, f"Error: {e}") from e


@router.get("/v105/autofix/stats", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=False, action="v105_autofix_stats")
async def v105_autofix_stats():
    """Get AutoFix engine stats for monitoring."""
    try:
        # [EXEC-1 A2] singleton Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â stats reflect cumulative state across all
        # fixes applied by the engine (not just this request's throwaway).
        from scp.autofix.engine import get_autofix_engine
        eng = get_autofix_engine()
        return eng.stats()
    except Exception as e:
        raise HTTPException(500, f"Error: {e}") from e


@router.post("/v105/autofix/run-audit", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=True, action="v105_run_deep_audit")
async def v105_run_deep_audit(payload: AutoFixAuditRequest | None = None):
    """[EXEC-1 A5] Trigger a deep audit cycle. SCP scans itself for bugs and
    auto-fixes (Tier 1/2) or requests permission (Tier 3).

    This is the WIRING that was missing: AutoFixEngine.process_bug() existed
    but had zero callers Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â the 4-tier autonomy system was dead code. This
    endpoint invokes scp.autofix.runner.run_deep_audit() which:
      1. AST-scans scp/ for bare `except: pass`, undefined names, syntax errors
      2. For each finding, calls get_autofix_engine().process_bug(bug)
      3. Writes per-bug result to data/deep_audit_results.jsonl

    Returns a summary: {processed, fixed, permission_requested, skipped,
    details, engine_stats, source} Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â source='ast_scan' confirms the scanner
    actually ran (vs returning empty when no audit_bugs.jsonl exists).

    Idempotent: re-running hits the engine's cooldown (same bug not re-fixed
    within 1h) so safe to call repeatedly.
    """
    try:
        request = payload or AutoFixAuditRequest(
            mode=os.environ.get("SCP_AUTOFIX_MODE", "apply").strip().lower() or "apply",
            max_bugs=int(os.environ.get("SCP_MAX_AUDIT_BUGS", "0") or 0),
        )
        if request.max_bugs < 0 or request.max_bugs > 200:
            raise HTTPException(422, "max_bugs must be between 0 and 200")
        if request.mode == "observe":
            # Observe-only path: scanner evidence is collected, but no
            # AutoFixEngine.process_bug() call is made and no source is written.
            from scp.autofix.runner_phases.ast_scan import ast_scan_scp
            # Observe mode is evidence collection, not a full enterprise
            # security scan. Keep it bounded and non-blocking; apply mode is
            # still available separately with the normal runner contract.
            observe_max_files = min(
                max(10, int(os.environ.get("SCP_OBSERVE_MAX_FILES", "50"))),
                100,
            )
            findings = await asyncio.to_thread(
                ast_scan_scp,
                max_files=observe_max_files,
                max_bugs=request.max_bugs or 20,
                include_enterprise=False,
            )
            if request.max_bugs:
                findings = findings[: request.max_bugs]
            details = [
                {
                    "file": getattr(bug, "file", ""),
                    "line": getattr(bug, "line", 0),
                    "bug_type": getattr(bug, "bug_type", ""),
                    "tier": int(getattr(getattr(bug, "tier", 0), "value", getattr(bug, "tier", 0)) or 0),
                }
                for bug in findings
            ]
            return {
                "audit_complete": True,
                "mode": "observe",
                "results": {
                    "processed": 0,
                    "fixed": 0,
                    "permission_requested": 0,
                    "skipped": len(details),
                    "findings_count": len(details),
                    "details": details,
                    "source": "ast_scan_observe_only",
                },
            }
        from scp.autofix.runner import run_deep_audit, run_once
        deterministic_only = os.environ.get("SCP_AUTOFIX_DETERMINISTIC_ONLY", "0") == "1"
        worker_mode = (
            os.environ.get("SCP_AUTOFIX_WORKER_MODE", "inline").strip().lower()
            or "inline"
        )
        # Out-of-loop deterministic mode: the request only scans + enqueues.
        # A separately supervised worker owns apply/verify/rollback. This keeps
        # the backend response bounded and makes queued/rejected/applied states
        # observable instead of turning a slow apply into an HTTP timeout.
        if deterministic_only and worker_mode == "deterministic":
            from scp.autofix.deterministic_worker import DeterministicWorker
            from scp.autofix.runner_phases.ast_scan import ast_scan_scp
            bounded_max_files = min(
                max(10, int(os.environ.get("SCP_AUTOFIX_MAX_SCAN_FILES", "50"))),
                100,
            )
            findings = await asyncio.to_thread(
                ast_scan_scp,
                max_files=bounded_max_files,
                max_bugs=request.max_bugs or 5,
                include_enterprise=False,
            )
            worker = DeterministicWorker()
            jobs = []
            for finding in findings[: request.max_bugs or len(findings)]:
                try:
                    jobs.append(worker.enqueue_bug(finding))
                except Exception as enqueue_error:
                    logger.error(
                        "[deterministic-worker] enqueue failed for %s:%s: %s",
                        getattr(finding, "file", ""), getattr(finding, "line", 0), enqueue_error,
                        exc_info=True,
                    )
            return {
                "audit_complete": True,
                "mode": "queued",
                "deterministic_only": True,
                "worker": "deterministic",
                "results": {
                    "processed": 0,
                    "fixed": 0,
                    "permission_requested": 0,
                    "skipped": len(findings) - len(jobs),
                    "findings_count": len(findings),
                    "jobs_enqueued": len(jobs),
                    "job_ids": [j.get("job_id") for j in jobs],
                    "source": "bounded_ast_scan_deterministic_worker_queue",
                },
            }
        # R9-2: run_deep_audit() AST-scans 371 .py. Production child can
        # explicitly disable provider I/O while still applying deterministic
        # safe fixes and recording unresolved findings as skipped.
        # (deepseek-r1:8b via Ollama — 30s+ per fix). Calling inline from
        # `async def` blocks the event loop for 2-10 min — /health, /ask,
        # WebSocket all freeze. Run in a worker thread (non-blocking).
        if deterministic_only:
            from scp.autofix.runner_phases.ast_scan import ast_scan_scp
            bounded_max_files = min(
                max(10, int(os.environ.get("SCP_AUTOFIX_MAX_SCAN_FILES", "50"))),
                100,
            )
            findings = await asyncio.to_thread(
                ast_scan_scp,
                max_files=bounded_max_files,
                max_bugs=request.max_bugs or 5,
                include_enterprise=False,
            )
            results = await asyncio.to_thread(
                run_once,
                bugs=findings,
                max_bugs=request.max_bugs,
                deterministic_only=True,
            )
            results["source"] = "bounded_ast_scan_deterministic_only"
        else:
            results = await asyncio.to_thread(
                run_deep_audit,
                max_bugs=request.max_bugs,
                deterministic_only=False,
            )
        return {
            "audit_complete": True,
            "mode": "apply",
            "deterministic_only": deterministic_only,
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {e}") from e


@router.get("/v105/autofix/worker/status", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=False, action="deterministic_worker_status")
async def deterministic_worker_status():
    """Return deterministic worker queue counts without exposing payload secrets."""
    try:
        from scp.autofix.deterministic_worker import DeterministicWorker
        return DeterministicWorker().status()
    except Exception as exc:
        raise HTTPException(500, f"Worker status error: {exc}") from exc


@router.get("/v105/runtime/subsystems", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=False, action="runtime_subsystem_status")
async def runtime_subsystem_status():
    """Return heartbeat snapshots for long-lived learning/evolution subsystems."""
    try:
        data_dir = os.environ.get("SCP_DATA_DIR", "data")
        return {
            name: SubsystemTelemetry(name, data_dir).snapshot()
            for name in ("fast_learning", "evolution", "deep_audit", "attack_monitor")
        }
    except Exception as exc:
        raise HTTPException(500, f"Subsystem status error: {exc}") from exc


@router.get("/v105/autofix/worker/jobs/{job_id}", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=False, action="deterministic_worker_job")
async def deterministic_worker_job(job_id: str):
    """Return one deterministic worker job and its transition events."""
    try:
        from scp.autofix.deterministic_worker import DeterministicWorker
        status = DeterministicWorker().status(job_id)
        if status.get("job") is None:
            raise HTTPException(404, "Worker job not found")
        return status
    except HTTPException:
        raise
    except Exception as exc:
        # [AUDIT-20260909 MACH2-R2-3] Trước đây leak str(exc) vào response
        # (message nội bộ lộ ra client). Log full ở server, client chỉ nhận
        # 500 generic.
        logger.warning("worker job status failed", exc_info=True)
        raise HTTPException(500, "internal error") from exc


@router.get("/v105/autofix/monitor", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=False, action="autofix_monitor")
async def autofix_monitor():
    """[OPT-31] AutoFixMonitor stats Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â success rate by bug_type/provider/diagnosis.

    DNA SCP #8 KB accumulation: expose AutoFix performance for admin dashboard.

    Distinct from `/v105/autofix/stats` (which returns AutoFixEngine cumulative
    counters like total bugs/fixed/skipped) Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â this endpoint returns the
    AutoFixMonitor view: per-bug-type / per-provider / per-diagnosis breakdowns
    + recent_attempts (last 10). Together they give the admin full visibility:
      - stats   = "what has the engine done?"
      - monitor = "how well is it doing it? which providers succeed?"
    """
    try:
        from scp.autofix.monitor import get_monitor
        monitor = get_monitor()
        stats = monitor.get_stats()
        recent = monitor.get_recent(limit=10)
        return {
            "status": "ok",
            "stats": stats,
            "recent_attempts": recent,
        }
    except Exception as e:
        # [AUDIT-20260909 MACH2-R2-3] Trước đây trả {"status":"error",
        # "message":str(e)} kèm HTTP 200 — lỗi nội bộ masquerade thành success
        # và leak message. Chuyển sang log server-side + 500 generic.
        logger.warning("autofix_monitor failed", exc_info=True)
        raise HTTPException(500, "internal error") from e


@router.post("/v105/autofix/cleanup-cache", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=True, action="cleanup_cache")
async def cleanup_cache():
    """[OPT-32] Clean up legacy broken SmartCache disk entries.

    TĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â I SAO: Task 35-A fixed SLMResponse serialization going forward
    (_slm_response_to_dict at slm_cache_set boundary), but ~9 legacy rows
    already in `smart_cache_disk` table store the broken string repr
    (`"SLMResponse(question='...', ...)"`) instead of a proper JSON dict.
    Task 35-A made _disk_get return None for those (treated as cache miss),
    so they're harmless Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â but they waste disk space + pollute debug queries.

    DNA SCP #7 safe: cleanup ONLY matches rows whose value_blob decodes to a
    JSON string starting with `"SLMResponse(" Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â valid JSON dict entries
    (the new format) are untouched.
    """
    try:
        from scp.core.smart_cache import cleanup_legacy_cache_entries
        result = cleanup_legacy_cache_entries()
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(500, f"Error: {e}") from e


@router.post("/v105/autofix/tier3-auto/{enabled}", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=True, action="v105_toggle_tier3_auto")
async def v105_toggle_tier3_auto(enabled: str):
    """[V4.3] Toggle Tier-3 auto-approve at RUNTIME Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â no restart needed.

    User cĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â¥p quyĂ„â€Ă‚Â¡-Ă‚Â»-Ă‚Ân qua API thay v-Ă¢â‚¬Â-Ă‚Â¬ .env:
      POST /v105/autofix/tier3-auto/1  Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ enable auto-approve
      POST /v105/autofix/tier3-auto/0  Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ disable auto-approve

    Safety guards vĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â«n active (1h timeout, 5/hour limit, etc.)
    Audit log ghi lĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â¡i: who toggled, when, from what source.
    """
    import os as _os
    old_val = _os.environ.get("SCP_AUTO_APPROVE_TIER3", "0")
    new_val = "1" if enabled in ("1", "true", "on", "yes") else "0"
    _os.environ["SCP_AUTO_APPROVE_TIER3"] = new_val

    # Audit log
    from scp.autofix.engine import get_tier3_config
    config = get_tier3_config()

    # Log toggle event
    import json as _json
    import time as _time
    from pathlib import Path as _Path
    audit = _Path("data/tier3_auto_audit.jsonl")
    audit.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": _time.time(),
        "action": "toggle",
        "old_value": old_val,
        "new_value": new_val,
        "source": "API (/v105/autofix/tier3-auto/)",
        "permission_source": config.get_permission_source(),
    }
    try:
        with open(audit, "a", encoding="utf-8") as f:
            f.write(_json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as _e:
        logger.debug("[silent-except] %s", _e, exc_info=True)

    # Log to SCP console
    import logging as _logging
    _logging.getLogger("scp.autofix").info(
        f"[TIER3-AUTO] Permission TOGGLED via API: {old_val} Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ {new_val}\n"
        f"  Source: API endpoint\n"
        f"  Safety guards: {'ACTIVE' if new_val == '1' else 'N/A (disabled)'}\n"
        f"  Audit: {audit}"
    )

    return {
        "status": "ok",
        "old_value": old_val,
        "new_value": new_val,
        "enabled": new_val == "1",
        "message": (
            f"Tier-3 auto-approve {'ENABLED' if new_val == '1' else 'DISABLED'} "
            f"(was {old_val}). Safety guards active: 1h timeout, 5/hour limit, "
            f"no relaxation, no BareExceptPass."
        ),
        "audit_log": str(audit),
    }


@router.post("/v105/autofix/rollback/{rollback_token}", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=True, action="v105_autofix_rollback")
async def v105_autofix_rollback(rollback_token: str):
    """[SCP-DNA-FIX R7-13] Revert a specific Tier-3 auto-approved fix by token.

    TĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â I SAO: R5/R6 audit log had no rollback_token Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â operators had to manually
    grep .tier3bak files + figure out which backup matched which fix. R7-13
    extended the audit schema (see _auto_approve_tier3 in engine.py) to write
    a UUID `rollback_token` per auto-approve. This endpoint accepts that token,
    looks up the audit entry, and reverts the file to its `before_hash` state
    by restoring from the .tier3bak backup (if present + hash matches).

    Reality test (R7-13 T2/T3/T4):
      T2 rollback endpoint present Ă„â€Ă‚Â¢-¦Ă¢â‚¬Å“│Ă¢â€Â¬Ă…â€œ (this route)
      T3 rollback reverts file to before_hash Ă„â€Ă‚Â¢-¦Ă¢â‚¬Å“│Ă¢â€Â¬Ă…â€œ (hash-verify before restore)
      T4 rollback logged separately Ă„â€Ă‚Â¢-¦Ă¢â‚¬Å“│Ă¢â€Â¬Ă…â€œ (append action="rollback" to audit log)

    Returns:
      {"status": "ok", "file": <path>, "restored_hash": <sha256>}
      404 if rollback_token not found in audit log
      409 if .tier3bak missing or before_hash doesn't match backup (tamper)
    """
    import hashlib as _hashlib
    import json as _json
    import time as _time
    from pathlib import Path as _Path
    audit_log = _Path("data/tier3_auto_audit.jsonl")
    if not audit_log.is_file():
        raise HTTPException(404, f"Audit log not found at {audit_log}")
    # Find the entry with matching rollback_token (last match wins Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â most recent).
    matching_entry = None
    try:
        for line in audit_log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = _json.loads(line)
                if entry.get("rollback_token") == rollback_token:
                    matching_entry = entry
            except Exception:
                logger.warning('v105_autofix_rollback: Exception not handled', exc_info=True)
                continue
    except Exception as e:
        raise HTTPException(500, f"Failed to read audit log: {e}") from e
    if matching_entry is None:
        raise HTTPException(404, f"rollback_token {rollback_token!r} not found in audit log")
    file_path_str = matching_entry.get("file", "")
    before_hash = matching_entry.get("before_hash", "")
    if not file_path_str or not before_hash:
        raise HTTPException(409, "Audit entry lacks file/before_hash (pre-R7-13 entry?)")
    file_path = _Path(file_path_str)
    # [SCP-DNA-FIX R8-5] TĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â I SAO: R7-13 d-Ă¢â‚¬Â-Ă‚Â¹ng single .tier3bak per file Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢
    # backup CLOBBERED bĂ„â€Ă‚Â¡-Ă‚Â»-¦Ă‚Â¸i later fix tr-Ă¢â‚¬Â-Ă‚Âªn c-Ă¢â‚¬Â-Ă‚Â¹ng file Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ rollback cĂ„â€Ă‚Â¡-Ă‚Â»-Ă‚Â§a fix CĂ„â€Ă¢â‚¬Â¦-Ă‚Â¨
    # fails vĂ„â€Ă‚Â¡-Ă‚Â»│Ă¢â€Â¬Ă‚Âºi misleading 409 "Backup hash mismatch (tampered?)" Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â backup
    # kh-Ă¢â‚¬Â-Ă‚Â´ng bĂ„â€Ă‚Â¡-Ă‚Â»│Ă¢â€Â¬Ă‚Â¹ tamper, bĂ„â€Ă‚Â¡-Ă‚Â»│Ă¢â€Â¬Ă‚Â¹ ghi Ă„â€Ă¢â‚¬Â│Ă¢â€Â¬Ă‹Å“-Ă¢â‚¬Â-Ă‚Â¨. Fix: per-token backup `.tier3bak.{token}`
    # (engine.py R8-5). Endpoint derive bak_path tĂ„â€Ă‚Â¡-Ă‚Â»-Ă‚Â« rollback_token. NĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â¿u
    # per-token backup kh-Ă¢â‚¬Â-Ă‚Â´ng tĂ„â€Ă‚Â¡-Ă‚Â»│Ă¢â€Â¬Ă…â€œn tĂ„â€Ă‚Â¡-Ă‚Âº-Ă‚Â¡i, fall back legacy single .tier3bak
    # (back-compat pre-R8-5 entries) trĂ„â€Ă¢â‚¬Â -Ă‚Â°Ă„â€Ă‚Â¡-Ă‚Â»│Ă¢â€Â¬Ă‚Âºc khi error.
    bak_path_token = file_path.with_suffix(
        file_path.suffix + f".tier3bak.{rollback_token}"
    )
    bak_path_legacy = file_path.with_suffix(file_path.suffix + ".tier3bak")
    if bak_path_token.is_file():
        bak_path = bak_path_token
    elif bak_path_legacy.is_file():
        # Pre-R8-5 entry OR uuid failed at fix time Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â use legacy single backup.
        bak_path = bak_path_legacy
    else:
        raise HTTPException(
            409,
            f"No backup for rollback_token {rollback_token!r} on file {file_path}. "
            f"Either the fix pre-dates R8-5 (single .tier3bak, since clobbered by "
            f"a later fix on same file) or the backup was deleted. "
            f"R8-5 note: per-token backups (.tier3bak.{{token}}) added to prevent "
            f"this clobber Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â older single-.tier3bak entries remain vulnerable."
        )
    # Verify backup hash matches before_hash (tamper detection).
    bak_hash = _hashlib.sha256(bak_path.read_bytes()).hexdigest()
    if bak_hash != before_hash:
        raise HTTPException(
            409,
            f"Backup hash mismatch for token {rollback_token!r}: "
            f"expected={before_hash} got={bak_hash}. "
            f"Likely cause: pre-R8-5 single-.tier3bak was clobbered by a LATER "
            f"fix on same file (the backup you're reading is from a newer fix, "
            f"not tampered). Apply fixes in newest-first order or upgrade to "
            f"R8-5 per-token backups (already done for new fixes)."
        )
    # Restore: ATOMIC write to target via temp file + fsync + os.replace.
    # [Phase 5-A / 4-a-008] Old code did `file_path.write_text(backup_content)`
    # directly Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â if interrupted mid-write (disk full, crash, signal), the
    # target file was left truncated/corrupt. A SAFETY mechanism that corrupts
    # the file on failure is worse than no rollback (DNA #7, #9).
    #
    # New flow:
    #   1. Read backup content into memory (small files Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â typical .py source).
    #   2. tempfile.mkstemp(dir=target_dir) Ă„â€Ă‚Â¢│Ă¢â€Â¬Ă‚Â │Ă¢â€Â¬Ă¢â€Â¢ temp file in SAME directory
    #      (so os.replace is atomic Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â POSIX guarantees atomic rename within
    #      the same filesystem; same-dir temp guarantees same filesystem).
    #   3. Write content, flush, fsync (durability Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â survives power loss).
    #   4. Verify temp-file hash matches before_hash BEFORE the rename
    #      (catches disk corruption / encoding issues without touching the
    #      live file).
    #   5. os.replace(tmp, target) Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â atomic on POSIX. Either old or new,
    #      never partial.
    #   6. On ANY exception: os.unlink(tmp) to clean up temp, then raise.
    import os as _os
    import tempfile as _tempfile
    backup_content = bak_path.read_text(encoding="utf-8")
    target_dir = file_path.parent
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:  # noqa: BLE001 Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â DNA #23 honest limit
        raise HTTPException(500, f"Failed to ensure target dir exists: {e}") from e
    fd, tmp_path = _tempfile.mkstemp(
        dir=str(target_dir),
        prefix=".rollback-tmp-",
        suffix=file_path.suffix or ".tmp",
    )
    try:
        with _os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(backup_content)
            f.flush()
            _os.fsync(f.fileno())
        # Pre-rename hash verification Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â if temp doesn't match before_hash,
        # the temp file is corrupt; DO NOT rename. Original file untouched.
        tmp_hash = _hashlib.sha256(_Path(tmp_path).read_bytes()).hexdigest()
        if tmp_hash != before_hash:
            raise HTTPException(
                500,
                f"Pre-rename temp hash mismatch: expected={before_hash} "
                f"got={tmp_hash}. Target file UNTOUCHED (atomic restore "
                f"aborted before os.replace)."
            )
        # ATOMIC rename Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â POSIX guarantees atomicity within same filesystem.
        _os.replace(tmp_path, str(file_path))
    except HTTPException:
        try:
            _os.unlink(tmp_path)
        except OSError:
            logger.debug('v105_autofix_rollback: OSError ignored', exc_info=True)  # tmp may already be gone (os.replace succeeded) Ă„â€Ă‚Â¢│Ă¢â‚¬ÂĂ‚Â¬│Ă¢â€Â¬Ă‚Â fine
        raise
    except Exception as e:
        try:
            _os.unlink(tmp_path)
        except OSError:
            logger.debug('v105_autofix_rollback: OSError ignored', exc_info=True)
        raise HTTPException(500, f"Failed to restore file atomically: {e}") from e
    # Verify post-restore hash matches before_hash.
    restored_hash = _hashlib.sha256(file_path.read_bytes()).hexdigest()
    if restored_hash != before_hash:
        raise HTTPException(500, f"Post-restore hash mismatch: expected={before_hash} got={restored_hash}")
    # [R7-13 T4] Log the rollback as a separate audit entry (action="rollback").
    rollback_entry = {
        "timestamp": _time.time(),
        "action": "rollback",
        "rollback_token": rollback_token,
        "file": file_path_str,
        "restored_hash": restored_hash,
        "original_audit_timestamp": matching_entry.get("timestamp"),
        "source": "API (/v105/autofix/rollback/)",
    }
    try:
        with open(audit_log, "a", encoding="utf-8") as f:
            f.write(_json.dumps(rollback_entry, ensure_ascii=False) + "\n")
    except Exception as _e:
        logger.warning(f" Failed to log rollback entry: {_e}", exc_info=True)
    logger.info(
        f" Rollback SUCCESS: token={rollback_token} file={file_path_str} "
        f"restored_hash={restored_hash[:12]}..."
    )
    return {
        "status": "ok",
        "rollback_token": rollback_token,
        "file": file_path_str,
        "restored_hash": restored_hash,
        "original_audit_timestamp": matching_entry.get("timestamp"),
        "message": f"File {file_path_str} reverted to before_hash state.",
    }

@router.post("/v105/rag/query", dependencies=[Depends(verify_admin)])
@traced_request(_V105_ROUTES_LEDGER, require_write=False, action="rag_query")
async def rag_query(request: Request):
    """Query RAG via canonical retriever (Wave 3)."""
    from scp.rag.canonical_retriever import HybridRetriever
    body = await request.json()
    query = str(body.get("query", ""))
    limit = int(body.get("limit", 3))

    # Init retriever (usually needs a path, defaulting to local)
    retriever = HybridRetriever()
    results = retriever.search(query, top_k=limit)
    return {"query": query, "results": results}
