# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
"""SCP Hands v3.3 controlled executor and verifier."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import shutil
import time
import uuid
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from scp.capabilities.tools import (
    SafeCommandRunnerTool,
    SystemInspectionTool,
    WorkspaceAnalysisTool,
)
from scp.core.autonomous_ledger import AutonomousAuditLedger
from scp.pc_control.pc_controller import CapabilityLevel, PCController
from scp.security.capability_epoch import (
    CapabilityAuthority,
    CapabilityToken,
    parse_capability_token,
)
from scp.web_control.web_navigator import WebNavigator

from .action_registry import ActionDefinition, ActionRegistry
from .process_manager import ManagedProcessManager

logger = logging.getLogger(__name__)



class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


class HandsExecutor:
    """Execute only registered actions and produce evidence for every result."""

    def __init__(
        self,
        controller: PCController | None = None,
        navigator: WebNavigator | None = None,
        capability_authority: CapabilityAuthority | None = None,
        data_dir: Path | None = None,
        audit_ledger: AutonomousAuditLedger | None = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[2]
        # SCP_HANDS_DATA_DIR isolates the hands state dir (capability epoch,
        # audit ledger, process workspaces) — used by hermetic smoke/CI runs so
        # they never read or mutate the operator's repository state.
        env_hands_dir = os.environ.get("SCP_HANDS_DATA_DIR", "").strip()
        self.data_dir = (
            Path(data_dir) if data_dir is not None
            else (Path(env_hands_dir) if env_hands_dir else (project_root / "data" / "hands"))
        )
        self.capability_authority = capability_authority or CapabilityAuthority(self.data_dir / "capability_state.json")
        self.controller = controller or PCController(capability_authority=self.capability_authority)
        if getattr(self.controller, "capability_authority", None) is None or (controller is not None and capability_authority is not None):
            self.controller.capability_authority = self.capability_authority
        self.navigator = navigator or WebNavigator()
        self.registry = ActionRegistry()
        self.processes = ManagedProcessManager(self.data_dir, project_root)
        self.audit_path = self.data_dir / "audit.jsonl"
        self.checkpoint_path = self.data_dir / "checkpoints.jsonl"
        self.backup_dir = self.data_dir / "backups"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.command_runner = SafeCommandRunnerTool(working_dir=self.controller.working_dir)
        self.inspection_tool = SystemInspectionTool(working_dir=self.controller.working_dir)
        self.analysis_tool = WorkspaceAnalysisTool(working_dir=self.controller.working_dir)

        raw_key = os.environ.get("SCP_LEDGER_HMAC_KEY")
        if raw_key:
            hmac_key = raw_key.encode("utf-8") if isinstance(raw_key, str) else raw_key
        else:
            secret = getattr(self.capability_authority, "secret", None)
            if secret:
                secret_bytes = secret if isinstance(secret, bytes) else str(secret).encode("utf-8")
                hmac_key = hmac.new(secret_bytes, b"scp.autonomous_audit_ledger.v1", hashlib.sha256).digest()
            else:
                hmac_key = None
        self.audit_ledger = audit_ledger or AutonomousAuditLedger(
            ledger_path=self.data_dir / "autonomous_ledger.jsonl",
            hmac_key=hmac_key,
            require_hmac=True,
        )

    def _audit(self, event: str, payload: dict[str, Any]) -> None:
        record = {"timestamp": time.time(), "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **payload}
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def _checkpoint(self, payload: dict[str, Any]) -> str:
        checkpoint_id = uuid.uuid4().hex
        record = {"checkpointId": checkpoint_id, "timestamp": time.time(), **payload}
        with self.checkpoint_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self._audit("CHECKPOINT_CREATED", record)
        return checkpoint_id

    def _check_capability(self, definition: ActionDefinition, capability_level: int, approved: bool, capability_token: CapabilityToken | None) -> tuple[bool, str]:
        if not self.capability_authority.validate(capability_token, required_subject=f"hands:{definition.name}"):
            return False, "Capability token is revoked, stale, or scope mismatch"
        if self.controller.kill_switch_engaged():
            return False, "Kill switch is engaged"
        if capability_level < definition.capability_level:
            return False, f"Action requires capability >= {definition.capability_level}"
        if definition.requires_approval and not approved:
            return False, "Explicit approval required"
        return True, "Policy requirements satisfied"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    async def _browser_target(self, params: dict[str, Any]) -> dict[str, Any] | None:
        targets = await self.navigator.browser.targets()
        pages = [item for item in targets if item.get("type") == "page"]
        target_id = str(params.get("targetId", "")).strip()
        hostname = str(params.get("hostname", "")).strip().lower()
        url_contains = str(params.get("urlContains", "")).strip().lower()
        if target_id:
            return next((item for item in pages if str(item.get("id", "")) == target_id), None)
        if hostname:
            return next((item for item in pages if (urlparse(str(item.get("url", ""))).hostname or "").lower() == hostname), None)
        if url_contains:
            return next((item for item in pages if url_contains in str(item.get("url", "")).lower()), None)
        return pages[0] if pages else None

    def _browser_evaluate(self, expression: str, target: dict[str, Any] | None) -> Any:
        """Evaluate a fixed expression through the active browser backend.

        Fail loud when the backend does not expose ``evaluate``: read-only
        backends (e.g. PlaywrightBackend) never execute arbitrary JS against a
        page (anti-honeypot), so a silent ``AttributeError`` is never
        acceptable here. The default BrowserSession path is unchanged (same
        ``browser.evaluate(expression, target)`` call as before).
        """
        evaluate = getattr(self.navigator.browser, "evaluate", None)
        if not callable(evaluate):
            raise NotImplementedError(
                "Active web backend does not expose evaluate(); CDP evaluation "
                "requires the BrowserSession backend (read-only backends never "
                "run arbitrary JS)"
            )
        return evaluate(expression, target)

    async def _pc_command(self, command: str, definition: ActionDefinition, capability_token: CapabilityToken | None = None) -> dict[str, Any]:
        result = await self.controller.execute(command, capability_token=capability_token, capability_level=0, approved=False, timeout=30)
        evidence = {"returnCode": result.get("returnCode"), "stdout": str(result.get("stdout", ""))[-5000:], "stderr": str(result.get("stderr", ""))[-2000:]}
        passed = bool(result.get("success"))
        return {"success": passed, "evidence": evidence, "verification": {"passed": passed, "rule": definition.verifier}, "error": result.get("error", "")}

    async def execute(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        capability_level: int = 0,
        approved: bool = False,
        dry_run: bool = False,
        capability_token: CapabilityToken | None = None,
        confirmation_id: str | None = None,
    ) -> dict[str, Any]:
        params = params or {}
        started = time.perf_counter()
        if capability_token is None:
            raw_token = params.get("capability_token") or params.get("capabilityToken")
            if raw_token is not None:
                capability_token = parse_capability_token(raw_token)
        if capability_token is None:
            result = {
                "success": False,
                "action": action,
                "error": "CapabilityRequiredError: Caller must provide an authorized capability token (FA-05)",
                "verification": {"passed": False},
            }
            self._audit("ACTION_BLOCKED_UNAUTHORIZED", result)
            return result

        expected_subject = f"hands:{action}"
        if getattr(capability_token, "subject", None) != expected_subject:
            result = {
                "success": False,
                "action": action,
                "error": f"CapabilityScopeMismatchError: Token subject '{getattr(capability_token, 'subject', None)}' does not match required action '{expected_subject}' (INV-AUTH-02)",
                "verification": {"passed": False},
            }
            self._audit("ACTION_BLOCKED_SCOPE_MISMATCH", result)
            return result
        try:
            definition = self.registry.require(action)
        except KeyError as exc:
            result = {"success": False, "action": action, "error": str(exc), "verification": {"passed": False}}
            self._audit("ACTION_BLOCKED", result)
            return result
        allowed, reason = self._check_capability(definition, capability_level, approved, capability_token)
        if not allowed:
            result = {"success": False, "action": action, "error": reason, "policy": definition.public(), "verification": {"passed": False}}
            self._audit("ACTION_BLOCKED", result)
            return result
        if dry_run:
            result = {"success": True, "dryRun": True, "action": action, "policy": definition.public(), "capabilityEpoch": getattr(capability_token, "epoch", 0), "verification": {"passed": True, "rule": "dry-run-only"}}
            self._audit("ACTION_DRY_RUN", result)
            return result
        if not self.capability_authority.validate(capability_token, required_subject=expected_subject):
            result = {"success": False, "action": action, "error": "Capability revoked before dispatch", "verification": {"passed": False}}
            self._audit("ACTION_BLOCKED_CAPABILITY_REVOKED", result)
            return result

        # Phase 1: Intent Commit before physical tool execution
        task_id = str(params.get("task_id") or params.get("taskId") or getattr(capability_token, "token_id", None) or f"task_{uuid.uuid4().hex[:12]}")
        step_id = str(params.get("step_id") or params.get("stepId") or f"step_{action}_{int(time.time()*1000)}")
        parent_trace_id = str(params.get("parent_trace_id") or params.get("trace_id") or "")

        intent_entry = self.audit_ledger.commit_intent(
            task_id=task_id,
            step_id=step_id,
            tool_name=action,
            params=params,
            capability_token=capability_token,
            parent_trace_id=parent_trace_id,
        )
        intent_hash = intent_entry.get("hash", "")

        try:
            if action == "pc.status":
                status_data = self.controller.status()
                result = {"success": True, "data": status_data, "evidence": {"controller": status_data.get("controller")}, "verification": {"passed": status_data.get("controller") == "online", "rule": definition.verifier}}
            elif action == "pc.read_file":
                # Route parity: pc_controller_routes.py caps maxBytes at
                # 1_000_000 (Field le); the hands path must not bypass that
                # bound (unbounded read into memory = DoS vector).
                max_bytes = max(1, min(int(params.get("maxBytes", 200_000)), 1_000_000))
                result = await self.controller.read_file(str(params.get("path", "")), max_bytes, capability_token=capability_token)
                result["verification"] = {"passed": bool(result.get("success")), "rule": definition.verifier}
            elif action == "pc.list_dir":
                target = self.controller._resolve_path(str(params.get("path", self.controller.working_dir)))
                if not self.controller._inside_root(target):
                    result = {"success": False, "error": "Path is outside SCP workspace"}
                elif self.controller._sensitive(target):
                    result = {"success": False, "error": "Sensitive path is not listable"}
                else:
                    entries = sorted(item.name for item in target.iterdir())[:500]
                    result = {"success": True, "path": str(target), "entries": entries, "evidence": {"count": len(entries)}}
                result["verification"] = {"passed": bool(result.get("success")), "rule": definition.verifier}
            elif action == "pc.process_snapshot":
                result = await self._pc_command("tasklist /FO CSV", definition, capability_token=capability_token)
            elif action == "pc.process_list_owned":
                result = self.processes.list_owned()
                result["verification"] = {"passed": bool(result.get("success")), "rule": definition.verifier}
            elif action == "pc.process_info":
                result = self.processes.info(int(params.get("pid", 0)))
                result["verification"] = {"passed": bool(result.get("success")), "rule": definition.verifier}
            elif action == "pc.process_start_managed":
                result = self.processes.start(str(params.get("commandId", "")))
                result["verification"] = {"passed": bool(result.get("success")) and bool(result.get("owned")), "rule": definition.verifier}
            elif action == "pc.process_stop_owned":
                result = self.processes.stop(int(params.get("pid", 0)))
                result["verification"] = {"passed": bool(result.get("success")) and bool(result.get("owned")), "rule": definition.verifier}
            elif action == "pc.service_snapshot":
                result = await self._pc_command("sc.exe query", definition, capability_token=capability_token)
            elif action == "pc.workspace_diff_check":
                raw = await self.controller.execute("git diff --check", capability_token=capability_token, capability_level=0, approved=False, timeout=30)
                clean = raw.get("returnCode") == 0
                result = {"success": raw.get("returnCode") is not None, "evidence": {"returnCode": raw.get("returnCode"), "stdout": str(raw.get("stdout", ""))[-5000:], "stderr": str(raw.get("stderr", ""))[-2000:], "clean": clean}, "verification": {"passed": raw.get("returnCode") is not None, "rule": definition.verifier}}
            elif action == "pc.file_hash":
                target = self.controller._resolve_path(str(params.get("path", "")))
                if not self.controller._inside_root(target) or self.controller._sensitive(target) or not target.is_file():
                    result = {"success": False, "error": "File is missing, sensitive or outside SCP workspace"}
                else:
                    result = {"success": True, "path": str(target), "sha256": self._sha256(target), "bytes": target.stat().st_size}
                result["verification"] = {"passed": bool(result.get("success")), "rule": definition.verifier}
            elif action == "pc.search_workspace":
                query = str(params.get("query", "")).strip()
                root = self.controller._resolve_path(str(params.get("path", self.controller.working_dir)))
                matches: list[dict[str, Any]] = []
                scanned = 0
                if query and self.controller._inside_root(root) and not self.controller._sensitive(root):
                    # Lazy traversal: do NOT materialize list(root.rglob("*")) —
                    # the whole tree must not be walked before the scanned/match
                    # bounds below stop the loop (DoS via huge trees).
                    candidates: Any = [root] if root.is_file() else (root.rglob("*") if root.is_dir() else [])
                    for candidate in candidates:
                        if len(matches) >= 50 or scanned >= 250:
                            break
                        if not candidate.is_file() or self.controller._sensitive(candidate) or candidate.stat().st_size > 1_000_000:
                            continue
                        scanned += 1
                        try:
                            for line_number, line in enumerate(candidate.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                                if query.lower() in line.lower():
                                    matches.append({"path": str(candidate), "line": line_number, "text": line[:300]})
                                    if len(matches) >= 50:
                                        break
                        except OSError:
                            logger.debug('HandsExecutor.execute: OSError ignored', exc_info=True)
                            continue
                result = {"success": bool(query) and self.controller._inside_root(root), "query": query, "matches": matches, "evidence": {"scannedFiles": scanned, "matchCount": len(matches)}}
                result["verification"] = {"passed": bool(result.get("success")), "rule": definition.verifier}
            elif action == "pc.directory_tree":
                root = self.controller._resolve_path(str(params.get("path", self.controller.working_dir)))
                max_depth = max(0, min(int(params.get("maxDepth", 3)), 4))
                entries: list[str] = []
                if root.is_dir() and self.controller._inside_root(root) and not self.controller._sensitive(root):
                    for candidate in sorted(root.rglob("*"), key=lambda item: str(item).lower()):
                        try:
                            relative = candidate.relative_to(root)
                        except ValueError:
                            logger.debug('HandsExecutor.execute: ValueError ignored', exc_info=True)
                            continue
                        if len(relative.parts) <= max_depth and not self.controller._sensitive(candidate):
                            entries.append(str(relative))
                        if len(entries) >= 300:
                            break
                result = {"success": root.is_dir() and self.controller._inside_root(root), "path": str(root), "entries": entries, "evidence": {"count": len(entries), "maxDepth": max_depth}}
                result["verification"] = {"passed": bool(result.get("success")), "rule": definition.verifier}
            elif action == "pc.git_status":
                raw = await self.controller.execute("git status --short --branch", capability_token=capability_token, capability_level=0, approved=False, timeout=30)
                result = {"success": raw.get("returnCode") is not None, "evidence": {"returnCode": raw.get("returnCode"), "stdout": str(raw.get("stdout", ""))[-5000:], "stderr": str(raw.get("stderr", ""))[-2000:]}, "verification": {"passed": raw.get("returnCode") is not None, "rule": definition.verifier}}
            elif action == "pc.validate_jsonl":
                target = self.controller._resolve_path(str(params.get("path", "")))
                valid_count = 0
                invalid_records: list[dict[str, Any]] = []
                if self.controller._inside_root(target) and not self.controller._sensitive(target) and target.is_file():
                    for line_number, line in enumerate(target.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                        if not line.strip():
                            continue
                        try:
                            json.loads(line)
                            valid_count += 1
                        except json.JSONDecodeError as exc:
                            logger.debug('HandsExecutor.execute: json.JSONDecodeError ignored: %s', exc)
                            if len(invalid_records) < 20:
                                invalid_records.append({"line": line_number, "error": str(exc)})
                result = {"success": target.is_file() and self.controller._inside_root(target), "path": str(target), "validLines": valid_count, "invalidLines": len(invalid_records), "invalid": invalid_records}
                result["verification"] = {"passed": bool(result.get("success")) and not invalid_records, "rule": definition.verifier}
            elif action == "pc.write_file":
                target = self.controller._resolve_path(str(params.get("path", "")))
                existed = target.exists()
                prior_hash = self._sha256(target) if existed and target.is_file() else None
                conf_id = confirmation_id or params.get("confirmation_id") or params.get("confirmationId")
                write_result = await self.controller.write_file(
                    str(target),
                    str(params.get("content", "")),
                    capability_token=capability_token,
                    capability_level=capability_level,
                    approved=approved,
                    confirmation_id=conf_id,
                )
                if write_result.get("success"):
                    backup_id = write_result.get("backupId")
                    backup_source = str(self.controller.backup_dir / f"{backup_id}.bak") if backup_id else None
                    checkpoint_id = self._checkpoint({"action": action, "target": str(target), "existed": existed, "priorHash": prior_hash, "backupPath": backup_source, "backupId": backup_id})
                    result = {**write_result, "checkpointId": checkpoint_id, "verification": {"passed": target.exists() and self._sha256(target) != prior_hash, "rule": definition.verifier}}
                else:
                    result = write_result
            elif action == "web.search_public":
                result = await self.navigator.search_public(str(params.get("query", "")), int(params.get("maxResults", 10)))
                result["verification"] = {"passed": bool(result.get("success")) and isinstance(result.get("results"), list), "rule": definition.verifier}
            elif action == "web.browse_public":
                result = await self.navigator.browse_public(str(params.get("url", "")), int(params.get("maxChars", 100_000)))
                result["verification"] = {"passed": bool(result.get("success")), "rule": definition.verifier}
            elif action == "web.extract_links":
                source = await self.navigator.browse_public(str(params.get("url", "")), int(params.get("maxChars", 100_000)))
                parser = _LinkParser()
                parser.feed(str(source.get("text", "")))
                links: list[str] = []
                for href in parser.links:
                    absolute = urljoin(str(source.get("url", params.get("url", ""))), href)
                    if absolute.startswith(("http://", "https://")) and absolute not in links:
                        links.append(absolute)
                    if len(links) >= 100:
                        break
                result = {"success": bool(source.get("success")), "url": source.get("url"), "links": links, "evidence": {"linkCount": len(links)}}
                result["verification"] = {"passed": bool(result.get("success")), "rule": definition.verifier}
            elif action == "web.tab_snapshot":
                pages = await self.navigator.browser.targets()
                page_data = [{"id": item.get("id"), "title": item.get("title", ""), "url": item.get("url", "")} for item in pages if item.get("type") == "page"][:30]
                result = {"success": True, "pages": page_data, "evidence": {"pageCount": len(page_data)}}
                result["verification"] = {"passed": True, "rule": definition.verifier}
            elif action == "web.dom_snapshot":
                target = await self._browser_target(params)
                if not target:
                    result = {"success": False, "error": "No matching local browser page"}
                else:
                    max_chars = max(100, min(int(params.get("maxChars", 20_000)), 50_000))
                    text = await self._browser_evaluate(f"document.body ? document.body.innerText.slice(0, {max_chars}) : ''", target)
                    title = await self._browser_evaluate("document.title", target)
                    result = {"success": True, "title": title, "url": target.get("url", ""), "text": str(text or "")[:max_chars], "evidence": {"chars": len(str(text or ""))}}
                result["verification"] = {"passed": bool(result.get("success")) and bool(result.get("text")), "rule": definition.verifier}
            elif action == "web.open_public_tab":
                url = self.navigator.browser.validate_url(str(params.get("url", "")))
                target = await self._browser_target(params)
                if not target:
                    result = {"success": False, "error": "No matching local browser page"}
                else:
                    result = await self.navigator.browser.navigate_and_read(url, target)
                result["verification"] = {"passed": bool(result.get("success")) and str(result.get("url", "")).startswith(("http://", "https://")), "rule": definition.verifier}
            elif action == "web.follow_public_link":
                url = self.navigator.browser.validate_url(str(params.get("url", "")))
                target = await self._browser_target(params)
                if not target:
                    result = {"success": False, "error": "No matching local browser page"}
                else:
                    result = await self.navigator.browser.navigate_and_read(url, target)
                result["verification"] = {"passed": bool(result.get("success")) and str(result.get("url", "")).startswith(("http://", "https://")), "rule": definition.verifier}
            elif action == "web.wait_for_text":
                expected = str(params.get("text", ""))[:500]
                timeout_seconds = max(1, min(int(params.get("timeoutSeconds", 10)), 20))
                target = await self._browser_target(params)
                found = False
                observed = ""
                if target and expected:
                    deadline = time.monotonic() + timeout_seconds
                    while time.monotonic() < deadline:
                        observed = str(await self._browser_evaluate("document.body ? document.body.innerText.slice(0, 50000) : ''", target) or "")
                        if expected in observed:
                            found = True
                            break
                        await asyncio.sleep(0.5)
                result = {"success": found, "expected": expected, "url": target.get("url", "") if target else "", "evidence": {"observedChars": len(observed), "timeoutSeconds": timeout_seconds}, "error": "Expected text was not observed" if not found else ""}
                result["verification"] = {"passed": found, "rule": definition.verifier}
            elif action == "web.read_logged_in":
                result = await self.navigator.browse_logged_in(str(params.get("url", "")))
                result["verification"] = {"passed": bool(result.get("success")) and bool(result.get("text")), "rule": definition.verifier}
            elif action == "cmd.run":
                cmd_text = str(params.get("command", "")).strip()
                timeout = max(1, min(int(params.get("timeout", 30)), 120))
                tool_res = await self.command_runner.run({
                    "command": cmd_text,
                    "capability_level": capability_level,
                    "approved": approved,
                    "timeout": timeout,
                })
                result = {
                    "success": tool_res.success,
                    "command": cmd_text,
                    "data": tool_res.data,
                    "evidence": {
                        **tool_res.evidence,
                        "truncated": tool_res.truncated,
                        "rateLimited": tool_res.rate_limited,
                    },
                    "error": tool_res.error,
                    "durationMs": tool_res.duration_ms,
                    "verification": {"passed": tool_res.success, "rule": definition.verifier},
                }
            elif action == "sys.inspect":
                tool_res = await self.inspection_tool.run(params)
                result = {
                    "success": tool_res.success,
                    "data": tool_res.data,
                    "evidence": tool_res.evidence,
                    "error": tool_res.error,
                    "durationMs": tool_res.duration_ms,
                    "verification": {"passed": tool_res.success, "rule": definition.verifier},
                }
            elif action == "workspace.analyze":
                tool_res = await self.analysis_tool.run(params)
                result = {
                    "success": tool_res.success,
                    "data": tool_res.data,
                    "evidence": tool_res.evidence,
                    "error": tool_res.error,
                    "durationMs": tool_res.duration_ms,
                    "verification": {"passed": tool_res.success, "rule": definition.verifier},
                }
            else:
                result = {"success": False, "error": "Action implementation missing"}
        except Exception as exc:
            logger.warning("HandsExecutor.execute failed for action %s: %s", action, exc, exc_info=True)
            result = {"success": False, "error": f"Executor error: {exc}", "verification": {"passed": False}}
        duration_ms = round((time.perf_counter() - started) * 1000)
        result.update({"action": action, "durationMs": duration_ms, "policy": definition.public(), "capabilityEpoch": getattr(capability_token, "epoch", 0)})

        # Phase 2: Outcome Commit after physical tool execution
        status = "SUCCESS" if result.get("success") else "FAILED"
        evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}

        outcome_entry = self.audit_ledger.commit_result(
            task_id=task_id,
            step_id=step_id,
            tool_name=action,
            intent_entry_hash=intent_hash,
            result_data=result,
            evidence=evidence,
            status=status,
            duration_ms=float(duration_ms),
        )
        result["intentHash"] = intent_hash
        result["outcomeHash"] = outcome_entry.get("hash", "")
        result["ledgerSeq"] = outcome_entry.get("seq", 0)

        self._audit("ACTION_EXECUTED" if result.get("success") else "ACTION_FAILED", result)
        return result

    async def rollback(self, checkpoint_id: str, capability_level: int = 3, approved: bool = False, capability_token: CapabilityToken | None = None) -> dict[str, Any]:
        if capability_token is None:
            result = {
                "success": False,
                "action": "rollback",
                "error": "CapabilityRequiredError: Caller must provide an authorized capability token (FA-05)",
                "verification": {"passed": False},
            }
            self._audit("ROLLBACK_BLOCKED_UNAUTHORIZED", result)
            return result

        expected_subject = "hands:rollback"
        if getattr(capability_token, "subject", None) != expected_subject:
            result = {
                "success": False,
                "action": "rollback",
                "error": f"CapabilityScopeMismatchError: Token subject '{getattr(capability_token, 'subject', None)}' does not match required action '{expected_subject}' (INV-AUTH-02)",
                "verification": {"passed": False},
            }
            self._audit("ROLLBACK_BLOCKED_SCOPE_MISMATCH", result)
            return result

        if not self.capability_authority.validate(capability_token, required_subject=expected_subject):
            result = {"success": False, "action": "rollback", "error": "Capability token is revoked or stale"}
            self._audit("ROLLBACK_BLOCKED_CAPABILITY_REVOKED", result)
            return result
        if self.controller.kill_switch_engaged():
            return {"success": False, "error": "Kill switch is engaged"}
        if capability_level < CapabilityLevel.WORKSPACE or not approved:
            return {"success": False, "error": "Rollback requires capability >= 3 and explicit approval"}
        if not self.checkpoint_path.exists():
            return {"success": False, "error": "Checkpoint ledger not found"}
        selected: dict[str, Any] | None = None
        for line in self.checkpoint_path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                logger.debug('HandsExecutor.rollback: json.JSONDecodeError ignored', exc_info=True)
                continue
            if record.get("checkpointId") == checkpoint_id:
                selected = record
        if not selected:
            return {"success": False, "error": "Checkpoint not found"}
        target = Path(str(selected.get("target", ""))).resolve()
        if not self.controller._inside_root(target) or self.controller._sensitive(target):
            return {"success": False, "error": "Rollback target is outside safe workspace"}
        backup_path = Path(str(selected.get("backupPath", ""))) if selected.get("backupPath") else None
        if backup_path is not None:
            # Fail-closed path validation: the ledger may be poisoned or
            # crafted — backupPath must live flat inside the managed backup
            # directory, otherwise rollback would copy an arbitrary file from
            # anywhere on the system into the workspace.
            allowed_backup_root = self.controller.backup_dir.resolve()
            if backup_path.resolve().parent != allowed_backup_root:
                result = {
                    "success": False,
                    "action": "rollback",
                    "checkpointId": checkpoint_id,
                    "error": "Checkpoint backupPath escapes the managed backup directory (path traversal blocked)",
                }
                self._audit("ROLLBACK_BLOCKED_BACKUP_PATH", result)
                return result
        try:
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, target)
                action = "restore_backup"
            elif not selected.get("existed") and target.exists():
                target.unlink()
                action = "remove_new_file"
            else:
                return {"success": False, "error": "No reversible checkpoint payload"}
            result = {"success": True, "checkpointId": checkpoint_id, "target": str(target), "action": action}
            self._audit("ROLLBACK", result)
            return result
        except OSError as exc:
            result = {"success": False, "checkpointId": checkpoint_id, "error": str(exc)}
            self._audit("ROLLBACK_FAILED", result)
            return result

    def capability_status(self) -> dict[str, Any]:
        return self.capability_authority.status()

    def revoke_capabilities(self, reason: str = "operator_revoke", actor: str = "operator") -> dict[str, Any]:
        result = self.capability_authority.revoke(reason=reason, actor=actor)
        self._audit("CAPABILITIES_REVOKED", result)
        return result

    def restore_capabilities(self, reason: str = "operator_restore", actor: str = "operator") -> dict[str, Any]:
        result = self.capability_authority.restore(reason=reason, actor=actor)
        self._audit("CAPABILITIES_RESTORED", result)
        return result

    def status(self) -> dict[str, Any]:
        audit_entries = 0
        checkpoint_entries = 0
        if self.audit_path.exists():
            audit_entries = sum(1 for _ in self.audit_path.open("r", encoding="utf-8"))
        if self.checkpoint_path.exists():
            checkpoint_entries = sum(1 for _ in self.checkpoint_path.open("r", encoding="utf-8"))
        owned = self.processes.list_owned()
        ledger_provenance = self.audit_ledger.verify_provenance()
        return {
            "version": "3.5",
            "hands": "online",
            "actionCount": len(self.registry.list()),
            "auditEntries": audit_entries,
            "checkpoints": checkpoint_entries,
            "managedProcessCount": owned.get("count", 0),
            "killSwitch": self.controller.kill_switch_engaged(),
            "capability": self.capability_status(),
            "ledgerProvenance": ledger_provenance,
            "policy": "explicit registry + capability epoch + approval + ownership + DOM verifier + audit",
        }
