# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
"""SCP V3.1 PC Controller.

This module is intentionally conservative: the model proposes actions, while
this controller enforces capability levels, workspace boundaries, audit logs,
backups and a kill switch before touching the Windows host.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from enum import IntEnum
from pathlib import Path, PureWindowsPath
from typing import Any

from scp.core.capability_token import InvalidTokenSignatureError
from scp.security.capability_epoch import (
    CapabilityAuthority,
    CapabilityToken,
    parse_capability_token,
)
from scp.security.confirmation_store import (
    HumanConfirmationStore,
    get_confirmation_store,
)

get_human_confirmation_store = get_confirmation_store

logger = logging.getLogger("scp.pc_controller")


class CapabilityLevel(IntEnum):
    READ_ONLY = 0
    DRY_RUN = 1
    SANDBOX = 2
    WORKSPACE = 3
    REAL = 4
    PRIVILEGED = 5


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    risk: str
    requires_approval: bool
    capability_level: int


# [F4 fix] compiled once: strip quoted segments, then detect parens
_PAREN_RE = re.compile(r"[()]")
_QUOTED_RE = re.compile(r'"[^"]*"|\'[^\']*\'')


def default_kill_switch_path() -> Path:
    """[F-RUN-01 audit-r2 2026-10-01] Kill-switch flag path for the DEFAULT
    controller (no explicit ``working_dir`` argument): mirrors exactly the
    derivation in :meth:`PCController.__init__` — ``SCP_PC_WORKING_DIR`` env
    override wins, otherwise the project root two levels above this file.

    TẠI SAO hàm này tồn tại: the /ask admission gate (scp/api_server.py) must
    consult the SAME flag file that ``POST /v3/pc/kill`` writes, without
    instantiating a second PCController (whose __init__ creates data dirs and
    loads the capability authority). Deriving the path once here and reusing
    it in both places removes the path-drift class (e.g. a future data-dir
    change silently decoupling the kill switch from the ask gate).
    """
    project_root = Path(__file__).resolve().parents[2]
    configured = os.environ.get("SCP_PC_WORKING_DIR")
    if configured:
        working_dir = Path(configured).expanduser().resolve()
    else:
        working_dir = project_root
    return working_dir / "data" / "pc_controller" / "KILL_SWITCH"


class PCController:
    """Controlled local-PC executor for SCP's observe-plan-act-verify loop.

    The controller does not grant the LLM a shell. Commands are classified by
    an allowlist and executed through PowerShell without ``shell=True``. High
    capability levels require explicit approval and every action is appended to
    an audit JSONL ledger.
    """

    BLOCKED_PATTERNS = (
        r"\bformat\s+[a-z]:",
        r"\bshutdown\b",
        r"\breg\s+delete\b",
        r"\bnet\s+user\b.*\b(delete|/delete)\b",
        r"\b(remove|del|erase)\b.*\s(-recurse|-force|/s|/q)\b",
        r"\brm\s+-rf\b",
        r"\bcredential(s)?\b.*\b(export|dump|steal)\b",
        r"\b(invoke-webrequest|invoke-restmethod|irm|curl|wget)\b.*(\b(iex|invoke-expression)\b|https?://)",
        r"\b(iex|invoke-expression)\b",
        r"\b(encodedcommand|enc)\b",
        r"\bset-executionpolicy\b",
    )
    READ_ONLY_PATTERNS = (
        r"^\s*(dir|ls|get-childitem)(\s|$)",
        r"^\s*(type|cat|get-content)(\s|$)",
        # [F3 fix] git read verbs hardened in lockstep with tools.py
        # (17dec80e + F1/F2): no --no* abbreviations, no --output in either
        # form, branch restricted to listing forms, show dropped (can read
        # arbitrary history blobs). Non-matching git verbs fall through to
        # the capability-level gate instead of the read-only allowlist.
        r"^\s*git\s+status(?:\s+[^;&|<>`$()]+)*\s*$",
        r"^\s*git\s+diff(?:\s+(?!--no)(?!--output(?:=|\s))[^;&|<>`$()]+)*\s*$",
        r"^\s*git\s+log(?:\s+(?!--output(?:=|\s))[^;&|<>`$()]+)*\s*$",
        r"^\s*git\s+branch(?:\s+(?:-a|-r|--all|--list))?\s*$",
        r"^\s*git\s+rev-parse(?:\s+[^;&|<>`$()]+)*\s*$",
        r"^\s*(where|whoami|hostname|tasklist|netstat)(\s|$)",
        r"^\s*(get-service|sc(\.exe)?\s+query)(\s|$)",
        r"^\s*(python|python3|bun|node)\s+(-{0,2}(version|help))(\s|$)",
        r"^\s*git\s+diff\s+--check(\s|$)",
    )
    WORKSPACE_PATTERNS = (
        r"^\s*(bun|npm)\s+run\s+(build|lint|test)(\s|$)",
        r"^\s*(python|python3)\s+-m\s+(pytest|compileall)(\s|$)",
        r"^\s*pytest(\s|$)",
        r"^\s*git\s+diff\s+--check(\s|$)",
    )
    SENSITIVE_PARTS = {".env", ".private-secrets", "credentials", "secrets"}

    def __init__(
        self,
        working_dir: str | Path | None = None,
        capability_authority: CapabilityAuthority | None = None,
        human_store: HumanConfirmationStore | None = None,
        confirmation_store: HumanConfirmationStore | None = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[2]
        configured = working_dir or os.environ.get("SCP_PC_WORKING_DIR")
        self.working_dir = self._resolve_path(configured or project_root)
        self.data_dir = self.working_dir / "data" / "pc_controller"
        self.audit_path = self.data_dir / "audit.jsonl"
        self.backup_dir = self.data_dir / "backups"
        # [F-RUN-01 audit-r2 2026-10-01] When no explicit working_dir argument
        # is given, resolve the flag through default_kill_switch_path() so the
        # controller and the /ask admission gate share ONE derivation (drift
        # guard). An explicit working_dir keeps its own data dir, unchanged.
        if working_dir is None:
            self.kill_switch_path = default_kill_switch_path()
        else:
            self.kill_switch_path = self.data_dir / "KILL_SWITCH"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.capability_authority = capability_authority or CapabilityAuthority(
            self.data_dir / "capability_state.json"
        )
        self.human_store = human_store or confirmation_store or get_confirmation_store()
        self.confirmation_store = self.human_store

    def _verify_token(self, token: Any, required_action: str = "pc.execute") -> CapabilityToken:
        """Strict Zero-Trust Policy Enforcement Point (PEP) for PCController.

        Validates HMAC-SHA256 signature, epoch, and subject scope fail-closed.
        Raises InvalidTokenSignatureError or PermissionError immediately if invalid.
        """
        if token is None or token == "":
            self._audit("TOKEN_REJECTED", {"action": required_action, "reason": "missing_token"})
            raise PermissionError(
                f"CapabilityRequiredError: Action '{required_action}' requires an authorized capability token (FA-05)"
            )

        parsed = parse_capability_token(token)
        if parsed is None:
            self._audit("TOKEN_REJECTED", {"action": required_action, "reason": "invalid_format"})
            raise InvalidTokenSignatureError(
                "InvalidCapabilityTokenError: Capability token format is invalid (FA-04)"
            )

        # Cryptographic signature check (raises InvalidTokenSignatureError if tampered/unsigned)
        try:
            is_valid = self.capability_authority.validate(parsed, required_subject=None)
        except InvalidTokenSignatureError as exc:
            self._audit(
                "TOKEN_REJECTED",
                {
                    "action": required_action,
                    "reason": "signature_verification_failed",
                    "token_id": getattr(parsed, "token_id", ""),
                },
            )
            raise exc

        if not is_valid:
            self._audit(
                "TOKEN_REJECTED",
                {
                    "action": required_action,
                    "reason": "revoked_or_stale_epoch",
                    "token_id": getattr(parsed, "token_id", ""),
                    "epoch": getattr(parsed, "epoch", -1),
                },
            )
            raise PermissionError("CapabilityRevokedError: Capability token is revoked or epoch is stale")

        subject = str(getattr(parsed, "subject", "")).strip()
        allowed_scopes: dict[str, set[str]] = {
            "pc.execute": {"pc.execute", "pc:execute", "hands:execute", "hands:pc.execute"},
            "pc.write_file": {"pc.write_file", "pc:write_file", "hands:pc.write_file"},
            "pc.read_file": {"pc.read_file", "pc:read_file", "hands:pc.read_file"},
            "pc.rollback": {"pc.rollback", "pc:rollback", "hands:rollback", "hands:pc.rollback"},
            "pc.clear_kill_switch": {"pc.clear_kill_switch", "pc:clear_kill_switch", "hands:admin", "hands:pc.clear_kill_switch"},
        }

        is_scope_valid = False
        valid_set = allowed_scopes.get(required_action, {required_action})
        if subject in valid_set:
            is_scope_valid = True
        elif required_action == "pc.execute" and subject.startswith("hands:pc."):
            is_scope_valid = True

        if not is_scope_valid:
            self._audit("TOKEN_REJECTED", {"action": required_action, "reason": "scope_mismatch", "subject": subject})
            raise PermissionError(
                f"CapabilityScopeMismatchError: Token subject '{subject}' does not permit action '{required_action}' (INV-AUTH-02)"
            )

        return parsed

    def _resolve_path(self, value: str | Path) -> Path:
        path = Path(value).expanduser().resolve()
        return path

    def _inside_root(self, path: Path) -> bool:
        try:
            path.relative_to(self.working_dir)
            return True
        except ValueError:
            logger.debug('PCController._inside_root: ValueError ignored', exc_info=True)
            return False

    def _sensitive(self, path: Path) -> bool:
        return any(part.lower() in self.SENSITIVE_PARTS for part in path.parts)

    # [AUDIT-FIX 2026-09-24] File-read verbs whose path argument must pass the
    # same _sensitive/_inside_root validation as read_file. Kept in sync with
    # READ_ONLY_PATTERNS group 2 (type|cat|get-content).
    # [L-02 fix 2026-09-28] dir/ls/get-childitem args get the SAME path
    # validation as type/cat/get-content (independent audit: dir C:/Windows
    # was allowed through the read-only allowlist with no path check).
    FILE_READ_VERB_PATTERN = r"^\s*(type|cat|get-content|dir|ls|get-childitem)(\s+|$)"

    def _command_read_paths(self, command: str) -> list[Path]:
        """Extract path candidates referenced by file-read verbs.

        Conservative extraction: quoted segments are taken whole (paths with
        spaces), then every remaining whitespace-separated token is treated as
        an additional path candidate. All candidates must pass validation, so
        over-extraction only ever moves the decision toward deny.
        """
        if not re.match(self.FILE_READ_VERB_PATTERN, command, re.IGNORECASE):
            return []
        remainder = re.sub(self.FILE_READ_VERB_PATTERN, "", command, count=1, flags=re.IGNORECASE).strip()
        if not remainder:
            return []
        candidates: list[str] = []
        # Quoted segments first (single or double quotes) — one path each.
        for quoted in re.findall(r'"([^"]+)"|\'([^\']+)\'', remainder):
            candidates.append(quoted[0] or quoted[1])
        remainder_unquoted = re.sub(r'"[^"]*"|\'[^\']*\'', " ", remainder)
        candidates.extend(token for token in remainder_unquoted.split() if token)
        paths: list[Path] = []
        for raw in candidates:
            token = raw.strip().strip('"').strip("'")
            # [F5 fix] PowerShell -Path:<value> / -LiteralPath:<value> colon
            # syntax hides the real path behind a flag-looking token - split
            # and validate the value (probe: get-content -Path:.env ALLOWED).
            if token.startswith("-") and ":" in token:
                token = token.split(":", 1)[1].strip()
                if not token:
                    continue
            if (not token or token.startswith("-")
                    or (token.startswith("/") and len(token) <= 3 and not token.startswith("//"))):
                # PowerShell parameters (-Raw, -TotalCount) are not paths.
                continue
            # [audit-r2 CI fix 2026-10-01] Normalize Windows-style separators
            # BEFORE validation on every platform: a POSIX host treats
            # "..\..\..\Windows" or "C:\Windows\System32" as ordinary
            # filenames *inside* the workspace, which let the read-only
            # allowlist through payloads the contract requires blocking
            # everywhere (GitHub-hosted ubuntu runner failed 4 guard tests).
            token_norm = token.replace("\\", "/")
            candidate = Path(token_norm).expanduser()
            if not candidate.is_absolute():
                if PureWindowsPath(token_norm).is_absolute():
                    # Windows-absolute grammar (drive letter) on a POSIX
                    # host: cannot be resolved against the workspace — anchor
                    # at the filesystem root so containment fails closed.
                    candidate = Path(os.sep) / token_norm
                else:
                    # Commands execute with cwd=self.working_dir (_run_sync),
                    # so relative arguments must be anchored there for
                    # validation.
                    candidate = self.working_dir / candidate
            paths.append(candidate.resolve())
        return paths

    def _command_path_violation(self, command: str) -> str | None:
        """Return a deny reason when a read-command references a forbidden path.

        Mirrors read_file: sensitive parts (.env, secrets, credentials,
        .private-secrets) are never readable, and paths outside the workspace
        root are denied — identical semantics to the read_file PEP.
        """
        for target in self._command_read_paths(command):
            if self._sensitive(target):
                return (
                    "CapabilityScopeMismatchError: command reads a sensitive path "
                    "(denied by the same policy as pc.read_file)"
                )
            if not self._inside_root(target):
                return (
                    "CapabilityScopeMismatchError: command reads a path outside the "
                    "SCP workspace (denied by the same policy as pc.read_file)"
                )
        return None

    # P2-FIX-AUDIT: return a durable result; callers must fail closed.
    def _audit(self, event: str, payload: dict[str, Any]) -> bool:
        record = {
            "timestamp": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": event,
            **payload,
        }
        try:
            with self.audit_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return True
        except OSError:
            logger.exception("Unable to append PC controller audit entry")
            return False

    def kill_switch_engaged(self) -> bool:
        return self.kill_switch_path.exists()

    def status(self) -> dict[str, Any]:
        audit_count = 0
        if self.audit_path.exists():
            try:
                audit_count = sum(1 for _ in self.audit_path.open("r", encoding="utf-8"))
            except OSError:
                logger.debug('PCController.status: OSError ignored', exc_info=True)
                audit_count = -1
        return {
            "controller": "online",
            "version": "3.1",
            "workingDir": str(self.working_dir),
            "killSwitch": self.kill_switch_engaged(),
            "auditEntries": audit_count,
            "capabilityLevels": {level.name: int(level) for level in CapabilityLevel},
            "policy": "allowlist + explicit approval + audit + backup",
        }

    def evaluate(
        self,
        command: str,
        capability_level: int = 0,
        approved: bool = False,
        confirmation_id: str | None = None,
        consume_confirmation: bool = False,
    ) -> PolicyDecision:
        if "\n" in command or "\r" in command:
            return PolicyDecision(False, "Multiline commands are not allowed", "critical", False, capability_level)
        command = command.strip()
        if not command:
            return PolicyDecision(False, "Empty command", "low", False, capability_level)
        if self.kill_switch_engaged():
            return PolicyDecision(False, "Kill switch is engaged", "critical", False, capability_level)
        # A read-only prefix must describe the whole command. Reject shell
        # separators/substitution before applying the prefix allowlist so a
        # payload such as `whoami ; Start-Process ...` cannot smuggle a second
        # command through the read-only regex.
        if re.search(r"(?:;|&&|\|\||\||`|\$\(|\$\{)", command):
            return PolicyDecision(False, "Command chaining is not allowed", "critical", False, capability_level)
        try:
            level = CapabilityLevel(max(0, min(5, int(capability_level))))
        except (TypeError, ValueError):
            logger.debug('PCController.evaluate: TypeError, ValueError ignored', exc_info=True)
            return PolicyDecision(False, "Invalid capability level", "high", False, capability_level)

        # [F4 fix] Paren subexpressions are evaluated by PowerShell before
        # the outer verb runs (dir (whoami) executed whoami) - same guard
        # as tools.py evaluate_command.
        if _PAREN_RE.search(_QUOTED_RE.sub(' ', command)):
            return PolicyDecision(False, "Subexpression execution and unquoted parentheses are prohibited", "critical", False, int(level))
        # [F6 fix] Redirection writes files outside the read-only contract
        # (whoami > out.txt, dir > audit.jsonl were allowed). Fail-closed.
        if re.search(r"[><]", command):
            return PolicyDecision(False, "Redirection operators are prohibited", "critical", False, int(level))
        if any(re.search(pattern, command, re.IGNORECASE) for pattern in self.BLOCKED_PATTERNS):
            return PolicyDecision(False, "Command matches a blocked safety pattern", "critical", False, int(level))
        if any(re.search(pattern, command, re.IGNORECASE) for pattern in self.READ_ONLY_PATTERNS):
            # [AUDIT-FIX 2026-09-24] Read-verb commands (type/cat/get-content)
            # must pass the SAME sensitive-path / workspace-root validation as
            # the read_file endpoint. Pre-fix: READ_ONLY_PATTERNS allowed
            # `type .env` / `get-content C:\any\.env` — a token holder could
            # read secrets and absolute paths that read_file denies.
            # Fail-closed: any referenced path that is sensitive or outside
            # the workspace root is denied with CapabilityScopeMismatchError
            # semantics (INV-AUTH-02), regardless of capability level.
            path_violation = self._command_path_violation(command)
            if path_violation:
                return PolicyDecision(False, path_violation, "critical", False, int(level))
            return PolicyDecision(True, "Read-only allowlist", "low", False, int(level))
        if level < CapabilityLevel.WORKSPACE:
            return PolicyDecision(False, "Command is not read-only at this capability level", "medium", False, int(level))
        if not any(re.search(pattern, command, re.IGNORECASE) for pattern in self.WORKSPACE_PATTERNS):
            return PolicyDecision(False, "Command is outside the workspace allowlist", "high", True, int(level))

        # [SEC-R1-01] Eliminate caller self-attestation:
        # High capability operations (>= WORKSPACE) require explicit human confirmation in HumanConfirmationStore.
        # Caller passing approved=True without a valid confirmation record in HumanConfirmationStore MUST fail.
        # [F7-RECUR fix] plan() is a preview gate: peek without consuming,
        # so the later execute() with the same cid still finds a live record.
        # [F7-RECUR fix] consume the record ONLY on the real execution path;
        # plan()/preview gates pass consume_confirmation=False (peek).
        is_confirmed = self.human_store.is_confirmed(
            "pc.execute", command, confirmation_id, consume=consume_confirmation
        )
        if not is_confirmed:
            return PolicyDecision(
                False,
                "Explicit human confirmation required via HumanConfirmationStore",
                "critical",
                True,
                int(level),
            )
        return PolicyDecision(True, "Workspace allowlist + approval", "medium", True, int(level))

    def plan(
        self,
        command: str,
        capability_level: int = 0,
        approved: bool = False,
        confirmation_id: str | None = None,
    ) -> dict[str, Any]:
        decision = self.evaluate(command, capability_level, approved, confirmation_id=confirmation_id)
        result = {"command": command, "decision": asdict(decision), "workingDir": str(self.working_dir)}
        self._audit("PLAN", result)
        return result

    def _run_sync(self, command: str, timeout: int) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command],
                cwd=str(self.working_dir),
                capture_output=True,
                text=True,
                timeout=max(1, min(timeout, 300)),
                shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {
                "success": completed.returncode == 0,
                "returnCode": completed.returncode,
                "stdout": completed.stdout[-10000:],
                "stderr": completed.stderr[-5000:],
                "durationMs": round((time.perf_counter() - started) * 1000),
            }
        except subprocess.TimeoutExpired as exc:
            return {"success": False, "returnCode": None, "stdout": str(exc.stdout or "")[-5000:], "stderr": "timeout", "durationMs": round((time.perf_counter() - started) * 1000)}
        except OSError as exc:
            return {"success": False, "returnCode": None, "stdout": "", "stderr": str(exc), "durationMs": round((time.perf_counter() - started) * 1000)}

    async def execute(
        self,
        command: str | dict[str, Any],
        capability_token: CapabilityToken | str | dict[str, Any] | int | None = None,
        capability_level: int = 0,
        approved: bool = False,
        timeout: int = 120,
        confirmation_id: str | None = None,
    ) -> dict[str, Any]:
        if isinstance(command, dict):
            payload = command
            command = str(payload.get("command", ""))
            capability_level = int(payload.get("capability_level", payload.get("level", capability_level)))
            approved = bool(payload.get("approved", approved))
            timeout = int(payload.get("timeout", timeout))
            confirmation_id = payload.get("confirmation_id") or payload.get("confirmationId") or confirmation_id
            if capability_token is None:
                capability_token = payload.get("capability_token") or payload.get("capabilityToken")

        if isinstance(capability_token, (int, CapabilityLevel)):
            capability_level = int(capability_token)
            capability_token = None

        token_obj = self._verify_token(capability_token, "pc.execute")

        level = int(capability_level)
        # [SEC-R1-01] Eliminate caller self-attestation:
        # If operation requires approval (level >= WORKSPACE), caller cannot simply pass approved=True.
        # Approval MUST be verified against HumanConfirmationStore fail-closed.
        verified_human_approval = False
        if level >= CapabilityLevel.WORKSPACE:
            # [F7-RECUR fix] peek here; the consuming check happens inside
            # evaluate(consume_confirmation=True) on the execution path.
            verified_human_approval = self.human_store.is_confirmed(
                action="pc.execute",
                target=command,
                confirmation_id=confirmation_id,
                consume=False,
            )
            if not verified_human_approval:
                self._audit("BLOCKED_SELF_ATTESTATION", {
                    "command": command,
                    "capability_level": level,
                    "caller_approved": approved,
                    "reason": "Missing or invalid HumanConfirmationStore approval",
                })
                raise PermissionError("High capability command requires operator confirmation in HumanConfirmationStore")

        effective_approved = verified_human_approval if level >= CapabilityLevel.WORKSPACE else approved
        decision = self.evaluate(command, capability_level, effective_approved, confirmation_id=confirmation_id, consume_confirmation=True)
        base = {
            "command": command,
            "decision": asdict(decision),
            "workingDir": str(self.working_dir),
            "tokenId": token_obj.token_id,
            "epoch": token_obj.epoch,
            "confirmationId": confirmation_id,
        }
        if not decision.allowed:
            self._audit("BLOCK", base)
            return {**base, "success": False, "output": "", "error": decision.reason}
        if not self._audit("EXECUTE_INTENT", {**base, "timeout": timeout}):
            return {**base, "success": False, "output": "", "error": "Audit storage unavailable; action blocked", "auditStatus": "DB_WRITE_FAILED"}
        result = await asyncio.to_thread(self._run_sync, command, timeout)
        post_audit_ok = self._audit("EXECUTE", {**base, **result})
        if not post_audit_ok:
            return {**base, **result, "executed": True, "auditStatus": "DB_WRITE_FAILED", "error": "Audit write failed after execution"}
        return {**base, **result, "auditStatus": "OK"}

    async def read_file(
        self,
        path: str,
        max_bytes: int = 200_000,
        capability_token: CapabilityToken | str | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(max_bytes, int) and capability_token is None:
            capability_token = max_bytes
            max_bytes = 200_000

        token_obj = self._verify_token(capability_token, "pc.read_file")

        target = self._resolve_path(path)
        if not self._inside_root(target):
            return {"success": False, "error": "Path is outside SCP workspace"}
        if self._sensitive(target):
            return {"success": False, "error": "Sensitive path is not readable by this endpoint"}
        try:
            content = target.read_text(encoding="utf-8")[:max_bytes]
            result = {
                "success": True,
                "path": str(target),
                "content": content,
                "truncated": target.stat().st_size > max_bytes,
                "tokenId": token_obj.token_id,
            }
        except OSError as exc:
            result = {"success": False, "path": str(target), "error": str(exc), "tokenId": token_obj.token_id}
        self._audit("READ_FILE", {key: value for key, value in result.items() if key != "content"})
        return result

    async def write_file(
        self,
        path: str,
        content: str,
        capability_token: CapabilityToken | str | dict[str, Any] | int | None = None,
        capability_level: int = 0,
        approved: bool = False,
        confirmation_id: str | None = None,
    ) -> dict[str, Any]:
        if isinstance(capability_token, (int, CapabilityLevel)):
            capability_level = int(capability_token)
            capability_token = None

        token_obj = self._verify_token(capability_token, "pc.write_file")

        target = self._resolve_path(path)
        if not self._inside_root(target):
            return {"success": False, "error": "Path is outside SCP workspace"}
        if self._sensitive(target):
            return {"success": False, "error": "Sensitive path cannot be written by this endpoint"}
        if self.kill_switch_engaged() or capability_level < CapabilityLevel.WORKSPACE:
            return {"success": False, "error": "Write requires capability >= 3 and explicit approval"}

        # [SEC-R1-01] Eliminate caller self-attestation:
        # High capability file write requires explicit confirmation in HumanConfirmationStore fail-closed.
        verified_human_approval = self.human_store.is_confirmed(
            action="pc.write_file",
            target=str(target),
            confirmation_id=confirmation_id,
        )
        if not verified_human_approval:
            self._audit("BLOCKED_SELF_ATTESTATION", {
                "path": str(target),
                "capability_level": int(capability_level),
                "caller_approved": approved,
                "reason": "Missing or invalid HumanConfirmationStore approval for pc.write_file",
            })
            return {"success": False, "error": "Write requires operator confirmation in HumanConfirmationStore"}

        content_hash = hashlib.sha256(content.encode("utf-8", "replace")).hexdigest()
        intent = {
            "path": str(target),
            "bytes": len(content.encode("utf-8")),
            "content_sha256": content_hash,
            "capability_level": int(capability_level),
            "tokenId": token_obj.token_id,
            "epoch": token_obj.epoch,
            "confirmationId": confirmation_id,
        }
        if not self._audit("WRITE_FILE_INTENT", intent):
            return {"success": False, "error": "Audit storage unavailable; write blocked", "auditStatus": "DB_WRITE_FAILED"}
        target.parent.mkdir(parents=True, exist_ok=True)
        backup_id = uuid.uuid4().hex
        backup_path = self.backup_dir / f"{backup_id}.bak"
        existed = target.exists()
        if existed:
            shutil.copy2(target, backup_path)
        fd, temp_name = tempfile.mkstemp(prefix="scp-write-", suffix=".tmp", dir=str(target.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        result = {
            "success": True,
            "path": str(target),
            "backupId": backup_id if existed else None,
            "bytes": len(content.encode("utf-8")),
            "content_sha256": content_hash,
            "tokenId": token_obj.token_id,
            "confirmationId": confirmation_id,
        }
        if not self._audit("WRITE_FILE", result):
            try:
                if existed:
                    shutil.copy2(backup_path, target)
                else:
                    target.unlink(missing_ok=True)
            except OSError:
                logger.exception("Write rollback failed after audit failure")
            return {"success": False, "path": str(target), "error": "Audit write failed; write rolled back", "auditStatus": "DB_WRITE_FAILED"}
        return {**result, "auditStatus": "OK"}

    async def rollback(
        self,
        backup_id: str,
        approved: bool = False,
        capability_level: int = 3,
        capability_token: CapabilityToken | str | dict[str, Any] | None = None,
        confirmation_id: str | None = None,
    ) -> dict[str, Any]:
        _token_obj = self._verify_token(capability_token, "pc.rollback")
        if capability_level < CapabilityLevel.WORKSPACE:
            return {"success": False, "error": "Rollback requires explicit approval and capability >= 3"}
        verified_human_approval = self.human_store.is_confirmed(
            action="pc.rollback",
            target=backup_id,
            confirmation_id=confirmation_id,
        )
        if not verified_human_approval:
            self._audit("BLOCKED_SELF_ATTESTATION", {
                "backup_id": backup_id,
                "capability_level": int(capability_level),
                "caller_approved": approved,
                "reason": "Missing or invalid HumanConfirmationStore approval for pc.rollback",
            })
            return {"success": False, "error": "Rollback requires operator confirmation in HumanConfirmationStore"}
        backup = self.backup_dir / f"{backup_id}.bak"
        if not backup.exists():
            return {"success": False, "error": "Backup not found"}
        return {"success": False, "error": "Rollback target metadata is not available in this backup format; use audit entry to select a target"}

    rollback_action = rollback

    def engage_kill_switch(self, reason: str = "user requested") -> dict[str, Any]:
        reason_hash = hashlib.sha256(reason.encode("utf-8", "replace")).hexdigest()
        if not self._audit("KILL_SWITCH_INTENT", {"reason_sha256": reason_hash}):
            return {"success": False, "killSwitch": self.kill_switch_engaged(), "error": "Audit storage unavailable; kill-switch action blocked", "auditStatus": "DB_WRITE_FAILED"}
        self.kill_switch_path.write_text(json.dumps({"reason": reason, "timestamp": time.time()}, ensure_ascii=False), encoding="utf-8")
        if not self._audit("KILL_SWITCH_ENGAGED", {"reason_sha256": reason_hash}):
            return {"success": True, "killSwitch": True, "reason": reason, "auditStatus": "DB_WRITE_FAILED"}
        return {"success": True, "killSwitch": True, "reason": reason, "auditStatus": "OK"}

    def clear_kill_switch(
        self,
        approved: bool = False,
        capability_token: CapabilityToken | str | dict[str, Any] | None = None,
        confirmation_id: str | None = None,
    ) -> dict[str, Any]:
        """Clear the kill switch (capability-token PEP + optional human confirmation).

        [SEC-R1-01-KILLSWITCH] (S-02, audit 2026-09-28) A capability token
        proves *authority to request* the clear; ``approved=True`` is only an
        intention flag. When the caller supplies ``confirmation_id``, the
        HumanConfirmationStore is consulted fail-closed: the record must be
        live, unexpired and bound to action ``pc.clear_kill_switch`` with
        target ``kill_switch`` ? otherwise the clear is blocked and audited.
        Callers without a confirmation record remain authorized by the
        capability-token PEP (established contract pinned by
        test_pc_controller_token_pep / flow_04), but the absence of a human
        confirmation record is now permanently visible in the audit trail
        instead of being indistinguishable from a confirmed clear.
        """
        token_obj = self._verify_token(capability_token, "pc.clear_kill_switch")
        if not approved:
            return {"success": False, "error": "Clearing kill switch requires explicit approval"}
        audit_payload: dict[str, Any] = {"tokenId": token_obj.token_id}
        if confirmation_id is not None:
            if not self.human_store.is_confirmed(
                "pc.clear_kill_switch", "kill_switch", confirmation_id
            ):
                self._audit(
                    "KILL_SWITCH_CLEAR_BLOCKED",
                    {"tokenId": token_obj.token_id, "confirmation_id": str(confirmation_id)[:64]},
                )
                return {
                    "success": False,
                    "killSwitch": True,
                    "error": "Kill switch clear blocked: confirmation record invalid or expired",
                    "auditStatus": "OK",
                }
            audit_payload["confirmation_id"] = str(confirmation_id)[:64]
        else:
            audit_payload["human_confirmation"] = "ABSENT"
        if not self._audit("KILL_SWITCH_CLEAR_INTENT", audit_payload):
            return {"success": False, "killSwitch": True, "error": "Audit storage unavailable; clear blocked", "auditStatus": "DB_WRITE_FAILED"}
        self.kill_switch_path.unlink(missing_ok=True)
        if not self._audit("KILL_SWITCH_CLEARED", {"tokenId": token_obj.token_id}):
            self.kill_switch_path.write_text(json.dumps({"reason": "audit failure fail-closed", "timestamp": time.time()}, ensure_ascii=False), encoding="utf-8")
            return {"success": False, "killSwitch": True, "error": "Audit write failed; kill switch re-engaged", "auditStatus": "DB_WRITE_FAILED"}
        return {"success": True, "killSwitch": False, "auditStatus": "OK"}
