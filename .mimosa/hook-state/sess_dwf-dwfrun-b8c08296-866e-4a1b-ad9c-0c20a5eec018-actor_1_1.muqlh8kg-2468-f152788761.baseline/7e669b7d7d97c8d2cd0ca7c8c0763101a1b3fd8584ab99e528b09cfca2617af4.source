"""SCP Capabilities: Autonomous Bounded Tooling Module."""
from __future__ import annotations

import abc
import asyncio
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

from scp.policy.egress import EgressPolicy

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ToolResult:
    success: bool
    data: dict[str, Any]
    evidence: dict[str, Any]
    error: str = ""
    duration_ms: float = 0.0
    truncated: bool = False
    rate_limited: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TokenBucketRateLimiter:
    """Thread-safe token bucket rate limiter for bounded tool calls."""

    def __init__(self, refill_rate_per_sec: float, capacity: float) -> None:
        self.refill_rate = refill_rate_per_sec
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False


class BaseAutonomousTool(abc.ABC):
    """Abstract base class for all bounded Agent OS autonomous tools."""

    name: str
    description: str
    capability_level: int
    requires_approval: bool
    mutates_state: bool

    def __init__(self, working_dir: Path | str, rate_limit_hz: float = 2.0) -> None:
        self.working_dir = Path(working_dir).resolve()
        self.rate_limiter = TokenBucketRateLimiter(refill_rate_per_sec=rate_limit_hz, capacity=3.0)

    @abc.abstractmethod
    async def run(self, params: Mapping[str, Any]) -> ToolResult:
        """Execute the tool within its bounded constraints."""
        pass


class SystemInspectionTool(BaseAutonomousTool):
    """Inspect system health, hardware, and OS metrics with bounded output."""

    name = "sys.inspect"
    description = "Inspect system hardware metrics, OS version, and disk capacity"
    capability_level = 0
    requires_approval = False
    mutates_state = False

    async def run(self, params: Mapping[str, Any]) -> ToolResult:
        started = time.perf_counter()
        if not await self.rate_limiter.acquire():
            return ToolResult(
                success=False,
                data={},
                evidence={"rate_limit": "exceeded"},
                error="Rate limit exceeded: maximum 2 calls per second",
                duration_ms=0.0,
                rate_limited=True,
            )

        # Collect bounded OS and hardware metrics without shelling out
        disk_usage = shutil.disk_usage(self.working_dir)
        cpu_count = os.cpu_count() or 1

        mem_info: dict[str, Any] = {}
        if hasattr(os, "sysconf"):
            try:
                page_size = os.sysconf("SC_PAGE_SIZE")
                total_pages = os.sysconf("SC_PHYS_PAGES")
                mem_info["total_bytes"] = page_size * total_pages
            except (ValueError, OSError) as exc:
                mem_info["sysconf_status"] = f"unsupported: {exc}"

        try:
            import psutil  # type: ignore[import-not-found]
            vm = psutil.virtual_memory()
            mem_info["total_bytes"] = vm.total
            mem_info["available_bytes"] = vm.available
            mem_info["used_percent"] = vm.percent
        except (ImportError, Exception) as exc:
            logger.debug(f"run ignored: {exc}", exc_info=True)
            mem_info["psutil_status"] = f"unavailable: {exc}"

        data: dict[str, Any] = {
            "os": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
            },
            "hardware": {
                "cpu_cores": cpu_count,
                "disk": {
                    "workspace_mount": str(self.working_dir),
                    "total_gb": round(disk_usage.total / (1024**3), 2),
                    "free_gb": round(disk_usage.free / (1024**3), 2),
                    "used_percent": round(((disk_usage.total - disk_usage.free) / disk_usage.total) * 100, 1),
                },
                "memory": mem_info,
            },
            "runtime": {
                "pid": os.getpid(),
                "working_dir": str(self.working_dir),
            },
        }

        # Strict 4KB serialization bound
        serialized = json.dumps(data, ensure_ascii=False)
        truncated = False
        if len(serialized) > 4096:
            data = {"summary": "System metrics truncated", "preview": serialized[:4000]}
            truncated = True

        duration = round((time.perf_counter() - started) * 1000, 2)
        return ToolResult(
            success=True,
            data=data,
            evidence={"metrics_collected": True, "disk_checked": str(self.working_dir)},
            duration_ms=duration,
            truncated=truncated,
        )


class WorkspaceAnalysisTool(BaseAutonomousTool):
    """Safely query workspace layout, tree structure, and files with path confinement."""

    name = "workspace.analyze"
    description = "Analyze project layout, directory trees, and search non-sensitive files"
    capability_level = 0
    requires_approval = False
    mutates_state = False

    SENSITIVE_PATTERNS = frozenset({
        ".env", ".private-secrets", "credentials", "secrets", "id_rsa", "id_ed25519",
        ".pem", ".key", ".git/config", ".ssh", ".aws", ".sqlite3-wal",
    })

    def _is_sensitive(self, path: Path | str) -> bool:
        lowered = str(path).lower().replace("\\", "/")
        return any(pattern in lowered for pattern in self.SENSITIVE_PATTERNS)

    def _resolve_and_contain(self, relative_path: str) -> Path:
        """Resolve path and verify strict containment inside workspace."""
        clean = Path(relative_path).expanduser()
        resolved = (self.working_dir / clean).resolve() if not clean.is_absolute() else clean.resolve()
        try:
            resolved.relative_to(self.working_dir)
        except ValueError:
            raise PermissionError(f"Path traversal detected: '{relative_path}' resolves outside workspace")
        if self._is_sensitive(resolved):
            raise PermissionError(f"Access to sensitive path denied: '{relative_path}'")
        return resolved

    async def run(self, params: Mapping[str, Any]) -> ToolResult:
        started = time.perf_counter()
        if not await self.rate_limiter.acquire():
            return ToolResult(success=False, data={}, evidence={}, error="Rate limit exceeded", rate_limited=True)

        mode = str(params.get("mode", "layout")).lower()
        try:
            if mode == "layout":
                manifests = []
                for name in ("pyproject.toml", "package.json", "Cargo.toml", "go.mod", "Dockerfile"):
                    if (self.working_dir / name).exists():
                        manifests.append(name)

                top_level_entries = []
                for entry in sorted(self.working_dir.iterdir()):
                    if not self._is_sensitive(entry):
                        top_level_entries.append({"name": entry.name, "is_dir": entry.is_dir()})

                data = {
                    "workspace_root": str(self.working_dir),
                    "detected_manifests": manifests,
                    "top_level_entries": top_level_entries[:50],
                }
                evidence = {"entries_count": len(top_level_entries)}

            elif mode == "find_files":
                pattern = str(params.get("pattern", "*"))
                max_results = min(int(params.get("limit", 50)), 100)
                matches = []
                for p in self.working_dir.rglob(pattern):
                    if len(matches) >= max_results:
                        break
                    if p.is_file() and not self._is_sensitive(p):
                        try:
                            rel = p.relative_to(self.working_dir)
                            matches.append(str(rel))
                        except ValueError:
                            continue
                data = {"pattern": pattern, "files": matches}
                evidence = {"match_count": len(matches)}

            elif mode == "read_bounded":
                target = self._resolve_and_contain(str(params.get("path", "")))
                if not target.is_file():
                    return ToolResult(success=False, data={}, evidence={}, error="Target is not a regular file")
                max_bytes = min(int(params.get("max_bytes", 16384)), 32768)
                content = target.read_text(encoding="utf-8", errors="replace")[:max_bytes]
                truncated = target.stat().st_size > max_bytes
                data = {"path": str(target.relative_to(self.working_dir)), "content": content, "truncated": truncated}
                evidence = {"sha256": hashlib.sha256(content.encode()).hexdigest(), "size_bytes": len(content)}

            else:
                return ToolResult(success=False, data={}, evidence={}, error=f"Unknown analysis mode: {mode}")

            duration = round((time.perf_counter() - started) * 1000, 2)
            return ToolResult(success=True, data=data, evidence=evidence, duration_ms=duration)

        except Exception as exc:
            logger.debug(f"run ignored: {exc}", exc_info=True)
            return ToolResult(
                success=False,
                data={},
                evidence={},
                error=f"WorkspaceAnalysis error: {exc}",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )


class SafeCommandRunnerTool(BaseAutonomousTool):
    """Execute commands within strict policy boundaries, timeouts, and output bounds."""

    name = "cmd.run"
    description = "Execute allowlisted development commands inside the workspace"
    capability_level = 1  # 1 for read-only cmds; mutating commands require level 3 + approval
    requires_approval = False
    mutates_state = False

    BLOCKED_PATTERNS = (
        r"\bformat\s+[a-z]:",
        r"\bshutdown\b",
        r"\breg\s+delete\b",
        r"\bnet\s+user\b",
        r"\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+(/|[a-zA-Z]:\\)",
        r"\b(remove|del|erase)\b.*\s(-recurse|-force|/s|/q)\b",
        r"\b(curl|wget)\s+.*\|.*(bash|sh|iex)",
        r"\b(iex|invoke-expression)\b",
        r"\b(su|sudo)\b",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r"\bchmod\s+(-[a-zA-Z]*[R][a-zA-Z]*\s+)*777\b",
        r"\bchown\s+-[a-zA-Z]*[R]\b",
        r"\b(nc\s+-e|bash\s+-i|/dev/tcp/)\b",
        r">\s*/dev/sda\b",
        r"\b(exec|eval|compile)\s*\(",
        r"\b(os\.system|os\.popen|os\.spawn|subprocess\.)",
        r"\b(socket|urllib|requests|http\.client)\b",
        r"\b(python|python3)\b.*?\s+-c\b",
    )
    # [P0-SEC-08/09/01/02 fixes 2026-09-28] Read-only allowlist hardened after
    # independent audit + live probes:
    #  * pytest removed entirely (pytest imports target modules => arbitrary
    #    top-level code execution at L1 via --collect-only; it now lives in
    #    WORKSPACE_ALLOWLIST only).
    #  * git: branch restricted to listing forms (-a/-r/--list/--all, no
    #    args) ? -D/-f/-m/-M/-c/-C are destructive writes; diff/log deny
    #    --no-index (arbitrary file read) and --output (arbitrary file write).
    READ_ONLY_ALLOWLIST = (
        r"^\s*git\s+status(?:\s+[^\s;&|><`$()]+)*\s*$",
        # [F1/F2 fix] deny --no* prefix (covers --no-index and abbreviations
        # like --no-i) and both --output= / --output<space> forms.
        r"^\s*git\s+diff(?:\s+(?!--no)(?!--output(?:=|\s))[^\s;&|><`$()]+)*\s*$",
        r"^\s*git\s+log(?:\s+(?!--output(?:=|\s))[^\s;&|><`$()]+)*\s*$",
        r"^\s*git\s+branch(?:\s+(?:-a|-r|--all|--list))?\s*$",
        r"^\s*git\s+rev-parse(?:\s+[^\s;&|><`$()]+)*\s*$",
        r"^\s*(python|python3|bun|node)\s+--version\s*$",
        r"^\s*(dir|ls)(?:\s+[^\s;&|><`$()]+)*\s*$",
        r"^\s*echo(?:\s+[^\s;&|><`$()]+)*\s*$",
    )
    WORKSPACE_ALLOWLIST = (
        r"^\s*pytest\b",
        r"^\s*(python|python3)\s+-m\s+(pytest|compileall)\b",
        r"^\s*(bun|npm)\s+run\s+(test|build|lint)\b",
        r"^\s*git\s+diff\s+--check\b",
    )

    SENSITIVE_PARTS = {
        ".env",
        ".private-secrets",
        "credentials",
        "secrets",
        "id_rsa",
        ".ssh",
        "shadow",
        "passwd",
    }
    SENSITIVE_PREFIXES = (
        "/etc",
        "/proc",
        "/sys",
        "/var",
        "c:\\windows",
        "c:/windows",
        "\\windows",
        "/windows",
    )

    def _validate_dir_ls_bounds(self, command: str, working_dir: Path | str | None = None) -> tuple[bool, str]:
        """Validate that dir/ls arguments remain strictly within working_dir and touch no sensitive paths."""
        parts = command.strip().split()
        if not parts:
            return True, ""
        verb = parts[0].lower()
        if verb not in {"dir", "ls", "get-childitem"}:
            return True, ""

        args = parts[1:]
        root_path = working_dir or self.working_dir
        working_root = Path(root_path).resolve()

        for arg in args:
            token = arg.strip().strip('"').strip("'")
            if not token:
                continue
            # Skip flags/options (e.g. -l, -la, /w, /b, -a) BUT split
            # PowerShell -Path:<value> / -LiteralPath:<value> colon syntax
            # first: the value after ":" is a real path that MUST be bounds-
            # checked (P1-SEC-10 colon bypass, confirmed by probe).
            token_check = token
            if token_check.startswith("-") and ":" in token_check:
                token_check = token_check.split(":", 1)[1].strip()
                if not token_check:
                    continue
                # fall through with the value as the token to validate
            elif token_check.startswith("-") or (token_check.startswith("/") and len(token_check) <= 3 and not token_check.startswith("//")):
                continue
            token = token_check


            token_norm = token.replace("\\", "/")
            token_lower = token_norm.lower()

            for prefix in self.SENSITIVE_PREFIXES:
                if token_lower == prefix or token_lower.startswith(prefix + "/"):
                    return False, f"Access to sensitive target '{token}' in '{verb}' is prohibited"

            for sens in self.SENSITIVE_PARTS:
                if sens in token_lower:
                    return False, f"Access to sensitive target '{token}' in '{verb}' is prohibited"

            try:
                # [audit-r2 CI fix 2026-10-01] Validate the separator-
                # normalized token on every platform: a POSIX host treats a
                # backslash traversal ("..\..\..\Windows") as an ordinary
                # filename inside the workspace, so the unnormalized Path
                # passed the bounds check (GitHub-hosted ubuntu runner red).
                # Windows-absolute grammar (drive letters) fails closed too.
                candidate = Path(token_norm).expanduser()
                if not candidate.is_absolute():
                    if PureWindowsPath(token_norm).is_absolute():
                        candidate = Path(os.sep) / token_norm
                    else:
                        candidate = working_root / candidate
                resolved = candidate.resolve()
            except Exception as e:
                return False, f"Invalid path in '{verb}': {e}"

            resolved_str = str(resolved).replace("\\", "/").lower()
            for prefix in self.SENSITIVE_PREFIXES:
                if resolved_str == prefix or resolved_str.startswith(prefix + "/"):
                    return False, f"Access to sensitive target '{token}' in '{verb}' is prohibited"

            for sens in self.SENSITIVE_PARTS:
                if any(sens == part.lower() for part in resolved.parts):
                    return False, f"Access to sensitive target '{token}' in '{verb}' is prohibited"

            try:
                resolved.relative_to(working_root)
            except ValueError:
                return False, f"Path '{token}' escapes working directory boundary '{working_root}'"

        return True, ""

    def __init__(self, working_dir: Path | str, egress_policy: EgressPolicy | None = None) -> None:
        super().__init__(working_dir)
        self.egress_policy = egress_policy or EgressPolicy()

    def evaluate_command(self, command: str, capability_level: int, approved: bool) -> tuple[bool, str, int]:
        cmd = command.strip()
        if not cmd:
            return False, "Command is empty", 0
        if "\n" in cmd or "\r" in cmd:
            return False, "Multiline commands are prohibited", 0

        normalized_cmd = re.sub(r'[\'\"\\]', '', cmd)
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE) or re.search(pattern, normalized_cmd, re.IGNORECASE):
                return False, f"Command matches blocked pattern: {pattern}", 0

        if re.search(r"[><]", cmd):
            return False, "Redirection operators are prohibited", 0
        if re.search(r"(?:;|&|\||`|\$\(|\$\{)", cmd):
            return False, "Command chaining and subshells are prohibited", 0

        # Subexpression execution guard (e.g. PowerShell (whoami) or (Get-Date))
        unquoted_cmd = re.sub(r'"[^"]*"|\'[^\']*\'', '', cmd)
        if re.search(r"[()]", unquoted_cmd):
            return False, "Subexpression execution and unquoted parentheses are prohibited", 0

        # Check dir/ls bounds before matching Read-Only allowlist
        if re.match(r"^\s*(dir|ls|get-childitem)\b", cmd, re.IGNORECASE):
            bounds_ok, bounds_reason = self._validate_dir_ls_bounds(cmd, self.working_dir)
            if not bounds_ok:
                return False, f"DirectoryTraversalBlocked: {bounds_reason}", 0

        # Read-only tier
        if any(re.search(pattern, cmd, re.IGNORECASE) for pattern in self.READ_ONLY_ALLOWLIST):
            return True, "Read-only allowlist match", 1

        # Workspace tier
        if any(re.search(pattern, cmd, re.IGNORECASE) for pattern in self.WORKSPACE_ALLOWLIST):
            if capability_level < 3 or not approved:
                return False, "Command requires capability level >= 3 and explicit approval", 3
            return True, "Workspace allowlist match with approval", 3

        return False, "Command does not match any allowlisted pattern", 0

    async def _execute_command(
        self,
        command: str,
        timeout: int = 30,
        working_dir: Path | str | None = None,
    ) -> tuple[int | None, bytes, bytes, bool, str | None]:
        cwd = Path(working_dir or self.working_dir).resolve()
        bounds_ok, bounds_reason = self._validate_dir_ls_bounds(command, cwd)
        if not bounds_ok:
            raise PermissionError(f"DirectoryTraversalBlocked: {bounds_reason}")

        is_windows = platform.system() == "Windows"
        if is_windows:
            cmd_args = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command]
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            cmd_args = ["/bin/sh", "-c", command]
            creationflags = 0

        process = await asyncio.create_subprocess_exec(
            *cmd_args,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=creationflags if is_windows else 0,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
            return process.returncode, stdout_bytes, stderr_bytes, False, None
        except asyncio.TimeoutError:
            kill_error: str | None = None
            try:
                if is_windows:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
                else:
                    process.kill()
            except Exception as exc:
                logger.debug(f"run ignored: {exc}", exc_info=True)
                kill_error = str(exc)
            return -1, b"", b"", True, kill_error

    async def run(self, params: Mapping[str, Any]) -> ToolResult:
        started = time.perf_counter()
        command = str(params.get("command", "")).strip()
        capability_level = int(params.get("capability_level", 0))
        approved = bool(params.get("approved", False))
        timeout = max(1, min(int(params.get("timeout", 30)), 120))

        # [P1-SEC-03 fix 2026-09-28] Workspace-tier commands require a real
        # human confirmation record: caller-approved=True alone is exactly the
        # self-attestation bypass the independent audit flagged. Read-only
        # tier stays approval-free.
        from scp.security.confirmation_store import get_confirmation_store
        _tier_probe = self.evaluate_command(command, capability_level, approved)
        if _tier_probe[0] and _tier_probe[2] >= 3:
            confirmation_id = str(params.get("confirmation_id") or params.get("confirmationId") or "").strip()
            _human_ok = False
            if confirmation_id:
                try:
                    _human_ok = get_confirmation_store().is_confirmed(
                        action="cmd.run", target=command, confirmation_id=confirmation_id
                    )
                except Exception:
                    _human_ok = False
            if not _human_ok:
                return ToolResult(
                    success=False,
                    data={},
                    evidence={"command": command, "tier": _tier_probe[2], "self_attested": approved},
                    error="CommandExecutionBlocked: workspace-tier command requires a valid HumanConfirmationStore confirmation_id",
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                )

        allowed, reason, required_cap = self.evaluate_command(command, capability_level, approved)
        if not allowed:
            return ToolResult(
                success=False,
                data={},
                evidence={"command": command, "evaluated_reason": reason},
                error=f"CommandExecutionBlocked: {reason}",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )

        # Enforce EgressPolicy on network destinations in the command
        urls = re.findall(r"https?://[^\s'\"`<>]+", command)
        ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", command)
        destinations = urls + [ip for ip in ips if not self.egress_policy.is_loopback(ip)]

        for word in re.findall(r"[a-zA-Z0-9.-]+", command):
            if self.egress_policy.is_cloud_metadata(word):
                destinations.append(word)

        for dest in destinations:
            try:
                self.egress_policy.enforce(dest)
            except Exception as ede:
                logger.debug(f"run ignored: {ede}", exc_info=True)
                return ToolResult(
                    success=False,
                    data={},
                    evidence={"command": command, "egress_denied": str(ede)},
                    error=f"EgressViolation: {ede}",
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                )

        try:
            returncode, stdout_bytes, stderr_bytes, timed_out, kill_error = await self._execute_command(
                command, timeout=timeout, working_dir=self.working_dir
            )
            if timed_out:
                return ToolResult(
                    success=False,
                    data={"returncode": -1},
                    evidence={"timeout_sec": timeout, "kill_error": kill_error},
                    error=f"Command timed out after {timeout} seconds",
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                )

            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")

            # Bounded dual-head/tail truncation: first 2000 chars + last 4000 chars
            truncated = False
            if len(stdout_str) > 6000:
                stdout_str = stdout_str[:2000] + f"\n...[TRUNCATED {len(stdout_str) - 6000} BYTES]...\n" + stdout_str[-4000:]
                truncated = True

            data = {
                "returncode": returncode,
                "stdout": stdout_str,
                "stderr": stderr_str[-2000:],
                "command": command,
            }
            evidence = {
                "returncode": returncode,
                "stdout_sha256": hashlib.sha256(stdout_bytes).hexdigest(),
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }
            return ToolResult(
                success=returncode == 0,
                data=data,
                evidence=evidence,
                error=f"Process exited with returncode {returncode}" if returncode != 0 else "",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                truncated=truncated,
            )

        except PermissionError as pe:
            return ToolResult(
                success=False,
                data={},
                evidence={"command": command, "evaluated_reason": str(pe)},
                error=f"CommandExecutionBlocked: {pe}",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
        except Exception as exc:
            logger.debug(f"run ignored: {exc}", exc_info=True)
            return ToolResult(
                success=False,
                data={},
                evidence={"command": command, "error": str(exc)},
                error=f"ToolExecutionError: {exc}",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )


__all__ = [
    "ToolResult",
    "TokenBucketRateLimiter",
    "BaseAutonomousTool",
    "SystemInspectionTool",
    "WorkspaceAnalysisTool",
    "SafeCommandRunnerTool",
]
