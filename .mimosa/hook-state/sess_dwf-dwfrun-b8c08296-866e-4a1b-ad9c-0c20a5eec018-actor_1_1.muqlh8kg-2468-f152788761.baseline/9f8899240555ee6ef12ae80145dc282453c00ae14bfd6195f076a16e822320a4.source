"""Bounded adapter between Agent Task Lane and SCP AutoFixEngine.

The adapter deliberately keeps three phases separate:

* propose: classify a candidate and persist only hashes/metadata;
* apply: pass the candidate through ``process_bug_with_llm(..., allow_llm=False)``;
* resume: apply a permission-approved request through AutoFixEngine's existing
  permission state machine.

The agent never calls ``_apply_fix`` directly, never enables LLM AutoFix in this
lane, and never accepts a caller-provided tier as authority.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from scp.autofix.classifier import BugReport, BugTier
from scp.core.request_run_ledger import RequestRunLedger

logger = logging.getLogger(__name__)


class AutoFixAdapter:
    """Safe proposal/apply/resume boundary for AgentOrchestrator."""

    VERSION = "1.0"
    MAX_FILE_BYTES = 2_000_000

    def __init__(self, ledger: RequestRunLedger | None = None, data_dir: str | Path = "data") -> None:
        self.ledger = ledger or RequestRunLedger()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.proposals_path = self.data_dir / "agent_autofix_proposals.jsonl"
        self._root = Path(__file__).resolve().parents[2]

    @staticmethod
    def _hash(value: Any) -> str:
        if isinstance(value, bytes):
            raw = value
        else:
            raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _bounded(value: Any, limit: int = 500) -> str:
        return str(value or "")[:limit]

    def _safe_path(self, file_value: str) -> Path:
        candidate = Path(str(file_value or "")).expanduser()
        if not candidate.is_absolute():
            candidate = self._root / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self._root.resolve())
        except ValueError as exc:
            raise ValueError("file is outside SCP workspace") from exc
        if resolved.is_symlink():
            raise ValueError("symlink targets are not accepted")
        return resolved

    def _read_file_hash(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            raise ValueError("file does not exist")
        if path.stat().st_size > self.MAX_FILE_BYTES:
            raise ValueError("file exceeds bounded AutoFix size")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _append(self, record: dict[str, Any]) -> bool:
        safe = {
            "ts": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "adapter_version": self.VERSION,
            **record,
        }
        # Never persist raw prompt, patch, explanation or answer in this ledger.
        for key in ("suggested_fix", "patch", "prompt", "goal", "answer"):
            safe.pop(key, None)
        try:
            with self.proposals_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(safe, ensure_ascii=False, sort_keys=True, default=str) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return True
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("autofix adapter: proposal ledger append failed for %s: %s", self.proposals_path, exc, exc_info=True)
            return False

    def _latest(self, proposal_id: str) -> dict[str, Any] | None:
        latest = None
        if not self.proposals_path.exists():
            return None
        try:
            for line in self.proposals_path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    # Corrupt ledger line must be visible; skipping keeps the
                    # reader resilient but a silent skip would hide corruption.
                    logger.warning("autofix adapter: corrupt line in proposals ledger %s", self.proposals_path, exc_info=True)
                    continue
                if item.get("proposal_id") == proposal_id:
                    latest = item
        except OSError as exc:
            logger.warning("autofix adapter: proposals ledger read failed for %s: %s", self.proposals_path, exc, exc_info=True)
            return None
        return latest

    def _begin(self, action: str, risk_class: str, parent_trace_id: str | None) -> Any:
        run = self.ledger.begin(
            SimpleNamespace(source="agent_autofix_adapter", domain="autofix", message=action),
            action=action,
            risk_class=risk_class,
            decision_source="agent_autofix_adapter",
        )
        if run.ledger_write_ok:
            self.ledger.stage(run, "autofix_adapter_received", "RUNNING", parent_trace_id=parent_trace_id or "")
        return run

    def _make_bug(self, payload: dict[str, Any], path: Path) -> BugReport:
        # Caller cannot promote a tier. The classifier is the authority.
        try:
            path.relative_to(self._root.resolve())
        except ValueError as exc:
            raise ValueError("file is outside SCP workspace") from exc
        return BugReport(
            # AutoFixEngine resolves BugReport.file from the process cwd; use
            # the already-validated absolute path so service launch directories
            # cannot change the target file.
            file=str(path),
            line=max(0, int(payload.get("line", 0) or 0)),
            bug_type=str(payload.get("bugType", "Unknown") or "Unknown")[:120],
            description=str(payload.get("description", "") or "")[:2000],
            suggested_fix=str(payload.get("suggestedFix", "") or ""),
            tier=BugTier.TIER_1_AUTO_FIX,
            is_restraint=False,
            is_reversible=True,
            affects_logic=False,
        )

    def _engine(self):
        from scp.autofix.engine import get_autofix_engine
        return get_autofix_engine()

    def _candidate_hash(self, payload: dict[str, Any]) -> str:
        return self._hash({
            "file": str(payload.get("file", "")),
            "line": int(payload.get("line", 0) or 0),
            "bugType": str(payload.get("bugType", "")),
            "description": str(payload.get("description", "")),
            "suggestedFix": str(payload.get("suggestedFix", "")),
        })

    async def propose(self, payload: dict[str, Any], *, parent_trace_id: str | None = None) -> dict[str, Any]:
        run = self._begin("agent_autofix_propose", "normal", parent_trace_id)
        if not run.ledger_write_ok:
            return {"success": False, "status": "DB_WRITE_FAILED", "run_id": run.run_id, "trace_id": run.trace_id}
        try:
            path = self._safe_path(str(payload.get("file", "")))
            before_hash = self._read_file_hash(path)
            bug = self._make_bug(payload, path)
            engine = self._engine()
            classified = engine.classifier.classify(
                file=bug.file,
                line=bug.line,
                bug_type=bug.bug_type,
                description=bug.description,
                suggested_fix=bug.suggested_fix,
                in_attack_mode=engine.in_attack_mode,
                tier_hint=None,
            )
            proposal_id = f"afp_{uuid.uuid4().hex}"
            candidate_hash = self._candidate_hash(payload)
            record = {
                "proposal_id": proposal_id,
                "run_id": run.run_id,
                "trace_id": run.trace_id,
                "parent_trace_id": parent_trace_id,
                "event": "PROPOSAL_READY",
                "status": "PROPOSAL_READY",
                "file": bug.file,
                "line": bug.line,
                "bug_type": bug.bug_type,
                "tier": int(classified.tier),
                "candidate_hash": candidate_hash,
                "before_hash": before_hash,
                "requires_human_approval": int(classified.tier) == int(BugTier.TIER_3_PERMISSION),
            }
            persisted = self._append(record)
            if not persisted:
                self.ledger.finish(run, "DB_WRITE_FAILED", result={"verdict": "UNKNOWN"}, proposal_id=proposal_id)
                return {"success": False, "status": "DB_WRITE_FAILED", "run_id": run.run_id, "trace_id": run.trace_id}
            self.ledger.stage(run, "autofix_proposal_ready", "RUNNING", proposal_id=proposal_id, candidate_hash=candidate_hash, parent_trace_id=parent_trace_id or "")
            terminal, ledger_ok = self.ledger.finish(run, "UNKNOWN", result={"verdict": "UNKNOWN"}, proposal_id=proposal_id, tier=int(classified.tier))
            return {
                "success": True,
                "status": "PROPOSAL_READY",
                "proposal_id": proposal_id,
                "run_id": run.run_id,
                "trace_id": run.trace_id,
                "parent_trace_id": parent_trace_id,
                "candidate_hash": candidate_hash,
                "before_hash": before_hash,
                "tier": int(classified.tier),
                "requires_human_approval": int(classified.tier) == int(BugTier.TIER_3_PERMISSION),
                "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED",
                "terminal_status": terminal,
            }
        except Exception as exc:
            logger.debug(f"propose ignored: {exc}", exc_info=True)
            terminal, ledger_ok = self.ledger.finish(run, "INTERNAL_FAILED", error=exc, result={"verdict": "UNKNOWN"})
            return {"success": False, "status": "INTERNAL_FAILED", "run_id": run.run_id, "trace_id": run.trace_id, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal, "error": self._bounded(exc, 300)}

    def _evidence_result(self, result: dict[str, Any], path: Path, before_hash: str) -> dict[str, Any]:
        after_hash = str(result.get("after_hash", ""))
        rollback_token = str(result.get("rollback_token", ""))
        reality = result.get("reality_test_result")
        evidence_ok = bool(after_hash and rollback_token and reality not in (None, "", "n/a", "skipped"))
        if evidence_ok:
            try:
                # AutoFix audit_log hashes decoded text. On Windows, hashing
                # raw bytes would see CRLF while Path.read_text() normalizes
                # newlines to LF, causing a false evidence rejection and a
                # needless rollback.
                observed_text = path.read_text(encoding="utf-8")
                evidence_ok = hashlib.sha256(observed_text.encode("utf-8")).hexdigest()[:32] == after_hash
            except OSError as exc:
                # silent-by-design: fail-safe — evidence stays incomplete so the
                # caller proceeds to rollback; the failure itself must be visible.
                logger.warning("autofix adapter: evidence re-read failed for %s: %s", path, exc, exc_info=True)
                evidence_ok = False
        if evidence_ok:
            return {
                "evidence_status": "COMPLETE",
                "before_hash": before_hash,
                "after_hash": after_hash,
                "rollback_token": rollback_token,
                "reality_test_result": reality,
            }
        rollback = {"attempted": False, "ok": False}
        if rollback_token:
            rollback["attempted"] = True
            try:
                rollback = {"attempted": True, **self._engine().rollback_fix_by_token(rollback_token)}
            except Exception as exc:
                logger.debug(f"_evidence_result ignored: {exc}", exc_info=True)
                rollback["error"] = self._bounded(exc, 250)
        return {
            "evidence_status": "INCOMPLETE",
            "before_hash": before_hash,
            "after_hash": after_hash,
            "rollback_token": rollback_token,
            "reality_test_result": reality,
            "rollback": rollback,
        }

    async def apply(self, proposal_id: str, payload: dict[str, Any], *, parent_trace_id: str | None = None) -> dict[str, Any]:
        state = self._latest(proposal_id)
        run = self._begin("agent_autofix_apply", "high", parent_trace_id)
        if not run.ledger_write_ok:
            return {"success": False, "status": "DB_WRITE_FAILED", "run_id": run.run_id, "trace_id": run.trace_id}
        try:
            if not state or state.get("status") not in {"PROPOSAL_READY", "WAITING_APPROVAL", "APPLY_FAILED"}:
                raise ValueError("proposal not found or no longer applicable")
            if self._candidate_hash(payload) != str(state.get("candidate_hash", "")):
                raise ValueError("candidate hash mismatch")
            path = self._safe_path(str(payload.get("file", "")))
            current_before = self._read_file_hash(path)
            if current_before != str(state.get("before_hash", "")):
                raise ValueError("file changed after proposal")
            bug = self._make_bug(payload, path)
            # Deterministic-only: LLM provider output is not allowed in this lane.
            from scp.autofix.llm_fix import process_bug_with_llm
            result = process_bug_with_llm(bug, self._engine(), allow_llm=False)
            action = str(result.get("action", "skipped"))
            self.ledger.stage(run, "autofix_engine_result", "RUNNING", proposal_id=proposal_id, action=action, parent_trace_id=parent_trace_id or "")
            if action == "permission_requested":
                permission_request_id = str(result.get("request_id", ""))
                self._append({"proposal_id": proposal_id, "run_id": run.run_id, "trace_id": run.trace_id, "event": "WAITING_APPROVAL", "status": "WAITING_APPROVAL", "permission_request_id": permission_request_id, "candidate_hash": state.get("candidate_hash"), "before_hash": current_before})
                terminal, ledger_ok = self.ledger.finish(run, "UNKNOWN", result={"verdict": "UNKNOWN"}, proposal_id=proposal_id, permission_request_id=permission_request_id)
                return {"success": False, "status": "WAITING_APPROVAL", "proposal_id": proposal_id, "permission_request_id": permission_request_id, "run_id": run.run_id, "trace_id": run.trace_id, "parent_trace_id": parent_trace_id, "result": {"action": action, "tier": result.get("tier"), "reason": result.get("reason")}, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal}
            if action != "fixed":
                terminal, ledger_ok = self.ledger.finish(run, "VERIFY_REJECTED", result={"verdict": "UNKNOWN"}, proposal_id=proposal_id, action=action)
                return {"success": False, "status": "NOT_APPLIED", "proposal_id": proposal_id, "run_id": run.run_id, "trace_id": run.trace_id, "result": result, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal}
            evidence = self._evidence_result(result, path, current_before)
            if evidence["evidence_status"] != "COMPLETE":
                terminal, ledger_ok = self.ledger.finish(run, "VERIFY_REJECTED", result={"verdict": "UNKNOWN"}, proposal_id=proposal_id, evidence_status="INCOMPLETE")
                self._append({"proposal_id": proposal_id, "run_id": run.run_id, "trace_id": run.trace_id, "event": "EVIDENCE_INCOMPLETE", "status": "APPLY_FAILED", "evidence_status": "INCOMPLETE"})
                return {"success": False, "status": "EVIDENCE_INCOMPLETE", "proposal_id": proposal_id, "run_id": run.run_id, "trace_id": run.trace_id, "evidence": evidence, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal}
            self._append({"proposal_id": proposal_id, "run_id": run.run_id, "trace_id": run.trace_id, "event": "APPLIED", "status": "APPLIED", "evidence": evidence, "candidate_hash": state.get("candidate_hash")})
            terminal, ledger_ok = self.ledger.finish(run, "SUCCESS", result={"verdict": "PASS"}, proposal_id=proposal_id, evidence_status="COMPLETE")
            return {"success": True, "status": "APPLIED", "proposal_id": proposal_id, "run_id": run.run_id, "trace_id": run.trace_id, "parent_trace_id": parent_trace_id, "evidence": evidence, "result": {"action": "fixed", "fix_source": result.get("fix_source"), "method": result.get("method")}, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal}
        except Exception as exc:
            logger.debug(f"apply ignored: {exc}", exc_info=True)
            self._append({"proposal_id": proposal_id, "run_id": run.run_id, "trace_id": run.trace_id, "event": "APPLY_FAILED", "status": "APPLY_FAILED", "error_class": type(exc).__name__})
            terminal, ledger_ok = self.ledger.finish(run, "INTERNAL_FAILED", error=exc, proposal_id=proposal_id)
            return {"success": False, "status": "APPLY_FAILED", "proposal_id": proposal_id, "run_id": run.run_id, "trace_id": run.trace_id, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal, "error": self._bounded(exc, 300)}

    async def resume(self, proposal_id: str, permission_request_id: str, *, parent_trace_id: str | None = None) -> dict[str, Any]:
        state = self._latest(proposal_id)
        run = self._begin("agent_autofix_resume", "high", parent_trace_id)
        if not run.ledger_write_ok:
            return {"success": False, "status": "DB_WRITE_FAILED", "run_id": run.run_id, "trace_id": run.trace_id}
        try:
            if not state or state.get("permission_request_id") != permission_request_id:
                raise ValueError("proposal and permission request do not match")
            result = self._engine().apply_approved_fix(permission_request_id)
            if result.get("action") != "fixed":
                terminal, ledger_ok = self.ledger.finish(run, "VERIFY_REJECTED", result={"verdict": "UNKNOWN"}, proposal_id=proposal_id)
                return {"success": False, "status": "NOT_APPLIED", "proposal_id": proposal_id, "run_id": run.run_id, "trace_id": run.trace_id, "result": result, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal}
            evidence = {key: result.get(key) for key in ("before_hash", "after_hash", "rollback_token", "reality_test_result")}
            complete = all(value not in (None, "", "n/a", "skipped") for value in evidence.values())
            terminal_status = "SUCCESS" if complete else "VERIFY_REJECTED"
            terminal, ledger_ok = self.ledger.finish(run, terminal_status, result={"verdict": "PASS" if complete else "UNKNOWN"}, proposal_id=proposal_id, evidence_status="COMPLETE" if complete else "INCOMPLETE")
            return {"success": complete, "status": "APPLIED" if complete else "EVIDENCE_INCOMPLETE", "proposal_id": proposal_id, "run_id": run.run_id, "trace_id": run.trace_id, "parent_trace_id": parent_trace_id, "evidence": evidence, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal}
        except Exception as exc:
            logger.debug(f"resume ignored: {exc}", exc_info=True)
            terminal, ledger_ok = self.ledger.finish(run, "INTERNAL_FAILED", error=exc, proposal_id=proposal_id)
            return {"success": False, "status": "RESUME_FAILED", "proposal_id": proposal_id, "run_id": run.run_id, "trace_id": run.trace_id, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal, "error": self._bounded(exc, 300)}


__all__ = ["AutoFixAdapter"]
