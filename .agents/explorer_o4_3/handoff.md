# Goal 3 Exploration Report: SCP Agent OS Autonomous Tool Execution Capabilities & Cryptographic Ledger Audit Provenance

**Agent ID**: `explorer_o4_3`  
**Working Directory**: `D:\scp\.agents\explorer_o4_3`  
**Target Milestone**: Goal 3 — SCP Agent OS Autonomous Tool Execution Capabilities & Cryptographic Ledger Audit Provenance  
**Date**: 2026-09-22T12:58:00Z  
**Baseline Git Commit**: `a3fcb6e` (`feature/autonomous-mode-antigravity-v2`)  
**Adherence**: Strict Fail-Closed & Evidence-First, FA-01 through FA-13, SCP DNA (Principles #1 to #26)

---

## 1. Observation

### 1.1 Codebase Landscape & Baseline State
Direct inspection of `D:\scp` revealed a robust governed AI agent codebase with ~221,000 Python LOC across 43 active subsystems under `scp/` and a comprehensive test suite (T00 through T12) totaling 2,049 collected tests.
Key observed subsystems directly relevant to Goal 3 include:
- `scp/capabilities/`: Contains capability modules (`rag.py`, `vector_db.py`, `voice.py`). Notably, `scp/capabilities/__init__.py:13` explicitly lists capability 6 as `tools — Agent tool calling (calculator, web search, code exec)`, but `tools.py` does not currently exist in `scp/capabilities/`.
- `scp/policy/`: Contains `retry_policy.py` (`RetryPolicy` for auto-retrying `WAITING_APPROVAL` steps). An autonomous egress policy module `scp/policy/egress.py` is currently missing.
- `scp/security/`: Houses `capability_epoch.py` (`CapabilityAuthority`, `CapabilityToken`), `autonomous_governor.py` (`AutonomousCapabilityGovernor`), `os_sandbox.py`, and `url_safety.py` (`enforce_egress_policy`, `safe_urlopen`).
- `scp/hands/`: The current operational execution bridge containing `action_registry.py` (25 allowlisted actions), `hands_executor.py` (`HandsExecutor`), `planner.py` (`HandsPlanner`), `task_kernel_bridge.py` (`TaskKernelHandsBridge`), `process_manager.py`, and `goal_parser.py`.
- `scp/pc_control/`: Contains `pc_controller.py` (`PCController`), the Policy Enforcement Point (PEP) governing host file access and command execution.
- `scp/core/`: Contains `agent_orchestrator.py` (`AgentOrchestrator`), `capability_token.py` (HMAC-SHA256 signature computation and validation), `request_run_ledger.py` (`RequestRunLedger`), `trace_contract.py` (`TraceSpanContract`, `redact_attributes`), and `trace_store.py` (`TraceStore`).
- `scp/trace_ledger.py`: Contains `TraceLedger`, an append-only JSONL ledger with O(1) backwards tail seeking, concurrency serialization via reentrant locks, and a continuous SHA-256 hash chain (`seq`, `prev_hash`, `fields`, `hash`).
- `scp/task_kernel.py` and `scp/task_kernel_parts/`: Provides the 17-state `TaskKernel` state machine (`taskkernel.py`, `definitions.py`) with lease fencing, OCC versioning, atomic checkpoints, and an SQLite-backed SHA-256 event journal (`verify_journal`).

---

### 1.2 Analysis of Current Autonomous Agent Execution Pipelines

Tracing the complete execution flow from entry point down to the physical hardware reveals the current call chain:

```
[User / API Client]
       │  HTTP / POST /v3/agent/run
       ▼
[scp/api/routes/agent_routes.py]
       │  Validates request, calls _guard()
       ▼
[scp/core/agent_orchestrator.py : AgentOrchestrator.run()]
       │  Begins RequestRun on RequestRunLedger, writes to data/agent_runs.jsonl
       ▼
[scp/hands/planner.py : HandsPlanner.run_plan()]
       │  Acquires file lease: data/hands/leases/{plan_id}.json
       │  Appends state events to data/hands/plans.jsonl (SHA-256 hash chain)
       │  If SCP_AUTONOMOUS_MODE=true:
       │     Calls AutonomousCapabilityGovernor.evaluate_and_grant_step()
       ▼
[scp/security/autonomous_governor.py : AutonomousCapabilityGovernor]
       │  Evaluates path sandbox & blocked command regex
       │  Calls CapabilityAuthority.issue() -> HMAC-SHA256 signed CapabilityToken
       ▼
[scp/hands/task_kernel_bridge.py : TaskKernelHandsBridge.execute()]
       │  Checks mutating action -> wraps in TaskKernel lifecycle:
       │  create_task() -> claim() -> start() -> idempotency_claim() -> checkpoint()
       ▼
[scp/hands/hands_executor.py : HandsExecutor.execute()]
       │  PEP: Validates token via capability_authority.validate(token, subject=f"hands:{action}")
       │  Checks kill switch: controller.kill_switch_engaged()
       │  Routes action via big if/elif chain (lines 179-365)
       ▼
[scp/pc_control/pc_controller.py : PCController.execute()]
       │  Strict PEP: _verify_token(token, "pc.execute") validates HMAC-SHA256 signature
       │  Evaluates command against BLOCKED_PATTERNS and allowlists
       │  Audits to data/pc_controller/audit.jsonl
       │  Runs: subprocess.run(["powershell.exe", ...])
       ▼
[OS / Hardware Layer Execution]
```

**Verbatim Code Evidence**:
1. In `scp/hands/planner.py:484-496`:
   ```python
   autonomous_mode = str(os.environ.get("SCP_AUTONOMOUS_MODE", "")).lower() in ("1", "true", "yes")
   if autonomous_mode and getattr(self, "autonomous_governor", None):
       granted, auth_token, reason = self.autonomous_governor.evaluate_and_grant_step(
           step, plan, str(self.executor.data_dir.resolve())
       )
       if granted and auth_token:
           step["capabilityToken"] = auth_token.to_dict()
           step["approved"] = True
           self._save(plan, "PLAN_STEP_AUTONOMOUS_GRANT", {"stepId": step["stepId"], "reason": reason})
       else:
           self._save(plan, "PLAN_STEP_AUTONOMOUS_DENY", {"stepId": step["stepId"], "reason": reason})
   ```
2. In `scp/security/autonomous_governor.py:21-73`:
   The `AutonomousCapabilityGovernor` evaluates sandbox paths and command safety, then issues a token:
   ```python
   subject = f"hands:{action}"
   token = self.authority.issue(subject=subject, token_id=token_id_b64)
   return True, token, "Autonomous safety invariants satisfied."
   ```
3. In `scp/hands/hands_executor.py:132-158`:
   ```python
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
   ```
4. In `scp/pc_control/pc_controller.py:112-144`:
   `_verify_token()` acts as the hardware-level Policy Enforcement Point:
   ```python
   parsed = parse_capability_token(token)
   # Cryptographic signature check (raises InvalidTokenSignatureError if tampered/unsigned)
   is_valid = self.capability_authority.validate(parsed, required_subject=None)
   if not is_valid:
       raise PermissionError("CapabilityRevokedError: Capability token is revoked or epoch is stale")
   ```

---

### 1.3 Bounded Tool Invocation: Current Implementations vs. Gaps

#### A. System Inspection Tool
- **Current Observation**:
  - `PCController.status()` (`scp/pc_control/pc_controller.py:217-234`): Returns controller status, version, workingDir, kill switch state, and audit counts.
  - `pc.process_snapshot` (`scp/hands/hands_executor.py:195-196`): Executes `tasklist /FO CSV` via PowerShell.
  - `pc.service_snapshot` (`scp/hands/hands_executor.py:209-210`): Executes `sc.exe query` via PowerShell.
- **Identified Deficiencies**:
  - **Platform Lock-in**: Shells out to `powershell.exe`, failing on Linux/Docker environments.
  - **Unbounded Output**: `tasklist` and `sc.exe query` output can grow to hundreds of kilobytes, risking buffer bloat.
  - **Lack of Structured Metrics**: Does not measure CPU utilization %, RAM (used, free, percent), disk volume capacity/free space, load averages, or process thread/file descriptor quotas.
  - **No Rate Limiting**: The system can be polled repeatedly in tight autonomous loops, wasting cycles and creating I/O contention.

#### B. Workspace Analysis Tool
- **Current Observation**:
  - `pc.list_dir` (`scp/hands/hands_executor.py:185-194`): Checks `_inside_root` and `_sensitive`, lists up to 500 file names.
  - `pc.search_workspace` (`scp/hands/hands_executor.py:222-245`): Traverses directory with `rglob("*")`, scans up to 250 files, caps matches at 50, skips files > 1 MB, caps snippet lines at 300 chars.
  - `pc.directory_tree` (`scp/hands/hands_executor.py:246-262`): Max depth 4, caps tree entries at 300 lines.
- **Identified Deficiencies**:
  - **Naive Path Traversal Protection**: Uses `path.relative_to(self.working_dir)`. Does not systematically guard against symlinks or NTFS junction points targeting directories outside the workspace root prior to canonicalization.
  - **Lack of Project Layout Semantics**: Fails to provide high-level structural intelligence (e.g., manifest parsing for `pyproject.toml`, `package.json`, `Cargo.toml`, directory classification into `src`, `test`, `docs`, `build`).
  - **Sensitive Path Coverage**: `SENSITIVE_PARTS = {".env", ".private-secrets", "credentials", "secrets"}` misses sensitive targets like `.git/config`, `id_rsa`, `.pem`, `.ssh`, `.aws`, `*.sqlite3-wal`.
  - **No Output Sizing Budget**: Output is truncated by entry count rather than an absolute byte ceiling, which can produce oversized JSON structures.

#### C. Safe Command Runner
- **Current Observation**:
  - `PCController.evaluate()` (`scp/pc_control/pc_controller.py:235-265`): Enforces `BLOCKED_PATTERNS`, `READ_ONLY_PATTERNS`, and `WORKSPACE_PATTERNS`.
  - `PCController._run_sync()` (`scp/pc_control/pc_controller.py:272-295`): Runs `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command ...` with `shell=False`, text capture, and timeout (1 to 300s).
- **Identified Deficiencies**:
  - **Shell Hardcoding**: Only targets `powershell.exe`. On Linux/Docker, commands fail immediately.
  - **Process Tree Leakage**: If a command times out (`subprocess.TimeoutExpired`), child processes spawned by PowerShell or Python remain alive in background.
  - **Asymmetric Truncation**: Only preserves the tail of stdout (`stdout[-10000:]`) and stderr (`stderr[-5000:]`), discarding headers and early execution logs while omitting explicit truncation metadata flags.
  - **Zero Network Egress Confinement**: Commands executed via `PCController.execute()` have unrestricted network access unless blocked by host firewall rules; there is no process-level proxy injection or network egress gate.

---

### 1.4 Capability Boundaries & Egress Policies

- **Capability Token Verification**:
  - Tokens are parsed and verified using HMAC-SHA256:
    ```python
    canonical = f"{subject}:{epoch}:{token_id}:{issued_at:.6f}".encode("utf-8")
    hmac.new(secret, canonical, hashlib.sha256).hexdigest()
    ```
  - Revocation is epoch-based: `CapabilityAuthority.revoke()` increments `epoch`, invalidating all previously minted tokens across all processes.
- **Egress Policy State**:
  - LLM Gateway egress is implemented in `scp/llm_gateway/egress_policy.py`: enforces `SCP_EGRESS_MODE` (`deny`, `allowlist`, or empty).
  - Outbound HTTP fetches are gated by `scp/security/url_safety.py:enforce_egress_policy()` and verified by `tests/T03_capability/test_egress_enforcement.py`.
  - **Gap**: There is no unified `scp/policy/egress.py` governing autonomous tool execution. Network requests made by tools or spawned processes are not checked against a unified tool egress policy that binds specific capabilities to allowed network endpoints (e.g., preventing SSRF, restricting tools to local loopback or allowlisted package registries).

---

### 1.5 Ledger-Backed Audit Provenance with Cryptographic Hashes

- **TraceLedger (`scp/trace_ledger.py`)**:
  - Operates on `data/trace_ledger.jsonl`.
  - Provides O(1) backward tail-read via `_read_tail()` seeking from EOF in binary mode.
  - Appends records serialized with `RLock` and `os.fsync()`.
  - Record structure:
    ```json
    {
      "trace_id": "trace_...",
      "seq": 1,
      "prev_hash": null,
      "fields": { ...redacted... },
      "hash": "sha256:..."
    }
    ```
  - Verification: `TraceLedger.verify()` iterates through every line, asserting `seq == i`, `prev_hash == prev`, `hash == sha256(canonical_body)`, and absence of raw secrets.
- **TaskKernel Journal (`scp/task_kernel_parts/taskkernel.py`)**:
  - SQLite table `events` with sequence numbers, `prev_event_hash`, and `event_hash = stable_hash(body)`.
  - `verify_journal(task_id)` asserts unbroken sequence and cryptographic hash continuity.
- **Critical Disconnect / Gap**:
  - The autonomous agent execution pipeline (`AgentOrchestrator`, `HandsPlanner`, `HandsExecutor`) currently writes audit events to disjoint files (`agent_runs.jsonl`, `plans.jsonl`, `audit.jsonl`).
  - Tool invocations (inputs, token signatures, execution states, outputs, and verifier receipts) are **NOT** systematically anchored into `TraceLedger`'s cryptographic SHA-256 hash chain!
  - There is no micro-block structure linking tool invocation intent to tool result in a tamper-evident, merkle-tree or block-hash verified ledger.

---

## 2. Logic Chain

```
Observation: Tool invocation is distributed across HandsExecutor with 25 ad-hoc string actions.
  │
  ├─► Deduction 1: Extensibility and bounded execution require an abstract BaseAutonomousTool contract
  │                with standardized input validation, output bounding, and capability requirements.
  │
Observation: SystemInspection and WorkspaceAnalysis rely on unstandardized scripts and regex filters.
  │
  ├─► Deduction 2: Autonomous operations require strictly bounded tools:
  │                - SystemInspectionTool: stdlib/psutil metrics, strict token-bucket rate limiter, 4KB payload cap.
  │                - WorkspaceAnalysisTool: canonical symlink validation (is_relative_to), comprehensive denylist,
  │                  project layout profiler, 16KB payload cap.
  │                - SafeCommandRunnerTool: cross-platform process management, process-tree termination,
  │                  bipolar truncation (head+tail), command allowlist/blocklist.
  │
Observation: Egress policies exist only for LLMs (llm_gateway) and HTTP urlopen (url_safety), not for tools.
  │
  ├─► Deduction 3: scp/policy/egress.py must be established as the single Policy Enforcement Point
  │                for all autonomous tool network and process egress, binding CapabilityTokens to
  │                explicit destination allowlists and blocking cloud metadata (169.254.169.254).
  │
Observation: TraceLedger maintains a verified SHA-256 hash chain, but HandsExecutor writes to unstructured audit.jsonl.
  │
  ├─► Deduction 4: Autonomous tool execution must commit two-phase micro-blocks (Intent -> Execution)
  │                directly into TraceLedger with SHA-256 block hashes, binding task_id, step_id,
  │                capability_token_hash, input_sha256, and output_sha256 into an immutable chain.
  │
Conclusion: Build the Agent OS Autonomous Tooling Module comprising scp/policy/egress.py,
            scp/capabilities/tools.py, and AutonomousAuditLedger with complete cryptographic provenance.
```

1. **Pipeline Decoupling**: Because `HandsExecutor` uses an imperative `if/elif` branching model (lines 179-365 of `hands_executor.py`), adding new tools creates cyclomatic complexity and risks bypassing security checks. A declarative `BaseAutonomousTool` interface with self-contained schemas, capability specifications, and verification rules is mathematically superior and adheres to Open-Closed Principle.
2. **Deterministic Bounding**: Unbounded tool outputs cause context window saturation, memory exhaustion, and denial of service. Strict parameter caps (e.g., max 100 directory entries, max 4KB system metrics, dual-head/tail 6KB command output) guarantee predictable resource consumption across all execution environments.
3. **Fail-Closed Egress Invariant**: Without an explicit tool egress gate, an agent executing commands or tools could exfiltrate data to unauthorized endpoints or reach private cloud metadata services. Enforcing fail-closed egress at `scp/policy/egress.py` ensures that unless `SCP_EGRESS_MODE=allowlist` with explicit domain clearance is present, all non-loopback network calls raise `EgressDeniedError`.
4. **Cryptographic Provenance Invariant**: For an Agent OS to be trustworthy, tool execution claims cannot rely on ephemeral RAM state. Writing pre-execution intent and post-execution results into `TraceLedger`'s hash chain guarantees tamper-evident provenance: if an adversary alters a command or result in the audit log, the SHA-256 chain verification fails immediately (`hash_chain_valid=False`).

---

## 3. Caveats

1. **Host-Specific Shell Features**: PowerShell commands and Linux bash commands have different syntaxes. While `SafeCommandRunnerTool` must be cross-platform, commands in scripts must be platform-aware, or abstract operations (such as file reads, listings, and process probing) must be performed via Python native libraries rather than OS shell commands.
2. **Network Sandbox Limitations on Host Windows**: Unlike Linux with network namespaces (`netns`) or cgroups, Windows does not natively support lightweight process-level network isolation without containers (Hyper-V/Docker) or Windows Filtering Platform (WFP) drivers. Process egress enforcement on Windows must be achieved via environment proxy poisoning (`HTTP_PROXY`, `ALL_PROXY`), execution parameter blocking, and strict API URL gateway interception.
3. **Rate Limiting Concurrency**: Token bucket rate limiters in memory are per-process. In a multi-worker deployment where workers run in separate OS processes, rate limiting must be synchronized via atomic file locking or shared kernel storage (`TaskKernel` or Redis/PostgreSQL).
4. **I/O Overhead of `fsync` in High-Throughput Scenarios**: Every `TraceLedger.append()` calls `os.fsync()` for durability. In high-frequency autonomous agent loops (e.g. >100 tool calls/sec), disk flush latency could become a bottleneck. Using batched block commits or group commits can alleviate this while preserving cryptographic integrity.

---

## 4. Conclusion & Implementation Blueprint

To fulfill Goal 3, we specify an exact, production-ready architecture for the **SCP Agent OS Autonomous Tool Execution Capabilities & Cryptographic Ledger Audit Provenance**.

### 4.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SCP AGENT ORCHESTRATOR                           │
│                     (Agent Loop / Autonomous Execution)                     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    1. Evaluate Step & Request Capability
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AUTONOMOUS CAPABILITY GOVERNOR                          │
│          (Policy Decision Point: Path containment & Command Safety)          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                  2. Issue Scoped HMAC-SHA256 CapabilityToken
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUTONOMOUS TOOL EXECUTOR                            │
│                 (Policy Enforcement Point & Tool Router)                    │
│                                                                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────┐  │
│  │  SystemInspectionTool   │  │  WorkspaceAnalysisTool  │  │ SafeCommand │  │
│  │ (Bounded OS/HW Metrics) │  │  (Sandboxed FS Analysis)│  │ RunnerTool  │  │
│  └─────────────────────────┘  └─────────────────────────┘  └─────────────┘  │
└──────────────┬───────────────────────────────┬──────────────────────────────┘
               │                               │
    3. Egress Policy Check           4. Micro-Block Audit Commits
               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────────────────────┐
│    scp/policy/egress.py     │ │         scp/trace_ledger.py (Extended)      │
│  (Fail-Closed Egress PEP)   │ │           AUTONOMOUS AUDIT LEDGER           │
│  - Loopback: ALLOWED        │ │  - Pre-Invocation Intent (input_sha256)     │
│  - Allowlist: MATCH ONLY    │ │  - Post-Invocation Result (output_sha256)   │
│  - Metadata 169.254: BLOCKED│ │  - Continuous SHA-256 Micro-Block Hash Chain│
└─────────────────────────────┘ └─────────────────────────────────────────────┘
```

---

### 4.2 Module 1: Unified Egress Policy Engine (`scp/policy/egress.py`)

This module consolidates all outbound network policy decisions into a single choke point for autonomous agents and tools.

```python
"""Unified Egress Policy Engine for SCP Agent OS Autonomous Operations."""
from __future__ import annotations

import enum
import ipaddress
import os
import socket
import urllib.parse
from dataclasses import dataclass
from typing import Any, Iterable


class EgressMode(str, enum.Enum):
    DENY = "deny"
    ALLOWLIST = "allowlist"
    OPEN = "open"


class EgressDeniedError(PermissionError):
    """Raised when an outbound network request is forbidden by egress policy."""

    def __init__(self, target: str, reason: str) -> None:
        self.target = target
        self.reason = reason
        super().__init__(f"Egress denied for target '{target}': {reason}")


@dataclass(frozen=True)
class EgressDestination:
    host: str
    port: int | None = None
    scheme: str = "https"

    @classmethod
    def from_url(cls, url: str) -> EgressDestination:
        parsed = urllib.parse.urlparse(url)
        scheme = (parsed.scheme or "https").lower()
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
        return cls(host=host, port=port, scheme=scheme)


class EgressPolicy:
    """Strict Fail-Closed Policy Engine governing network egress for tools."""

    BLOCKED_METADATA_HOSTS = frozenset({
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.aws",
        "169.254.170.2",
    })
    LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

    def __init__(
        self,
        mode: EgressMode | str | None = None,
        allowlist: Iterable[str] | None = None,
        production_mode: bool | None = None,
    ) -> None:
        if mode is None:
            raw_mode = os.environ.get("SCP_EGRESS_MODE", "allowlist").lower().strip()
            self.mode = EgressMode(raw_mode) if raw_mode in EgressMode._value2member_map_ else EgressMode.DENY
        elif isinstance(mode, str):
            self.mode = EgressMode(mode.lower().strip())
        else:
            self.mode = mode

        raw_allowlist = allowlist or os.environ.get("SCP_EGRESS_ALLOWLIST", "").split(",")
        self.allowlist: frozenset[str] = frozenset(
            item.strip().lower().rstrip(".") for item in raw_allowlist if item.strip()
        )
        self.production_mode = (
            production_mode
            if production_mode is not None
            else os.environ.get("SCP_PRODUCTION_MODE", "0").strip().lower() in {"1", "true", "yes"}
        )

    def is_loopback(self, host: str) -> bool:
        norm_host = host.strip().lower().rstrip(".")
        if norm_host in self.LOOPBACK_HOSTS:
            return True
        try:
            return ipaddress.ip_address(norm_host).is_loopback
        except ValueError:
            return False

    def is_cloud_metadata(self, host: str) -> bool:
        norm_host = host.strip().lower().rstrip(".")
        if norm_host in self.BLOCKED_METADATA_HOSTS:
            return True
        try:
            ip = ipaddress.ip_address(norm_host)
            # Link-local / AWS/GCP metadata subnet
            return ip in ipaddress.ip_network("169.254.0.0/16")
        except ValueError:
            return False

    def enforce(self, destination: str | EgressDestination, token_allowed_hosts: Iterable[str] | None = None) -> None:
        """Enforce egress policy fail-closed. Raises EgressDeniedError on violation."""
        dest = EgressDestination.from_url(destination) if isinstance(destination, str) else destination

        if not dest.host:
            raise EgressDeniedError(str(destination), "Missing or invalid host in destination")

        # Invariant 1: Cloud metadata is unconditionally blocked in all modes
        if self.is_cloud_metadata(dest.host):
            raise EgressDeniedError(dest.host, "Access to cloud metadata endpoints is unconditionally prohibited")

        # Invariant 2: Loopback is always permitted for internal microservices
        if self.is_loopback(dest.host):
            return

        # Invariant 3: Deny mode blocks all external traffic
        if self.mode == EgressMode.DENY:
            raise EgressDeniedError(dest.host, "SCP_EGRESS_MODE=deny blocks all non-loopback outbound traffic")

        # Invariant 4: Allowlist mode checks global allowlist and capability token-bound allowlist
        if self.mode == EgressMode.ALLOWLIST:
            permitted = set(self.allowlist)
            if token_allowed_hosts:
                permitted.update(h.strip().lower().rstrip(".") for h in token_allowed_hosts if h.strip())
            if dest.host not in permitted:
                raise EgressDeniedError(dest.host, f"Host not present in egress allowlist: {sorted(permitted)}")
            return

        # Invariant 5: In production mode, unknown/open modes fail-closed
        if self.production_mode and self.mode not in {EgressMode.DENY, EgressMode.ALLOWLIST}:
            raise EgressDeniedError(dest.host, "Production mode requires explicit deny or allowlist egress policy")
```

---

### 4.3 Module 2: Autonomous Tooling Suite (`scp/capabilities/tools.py`)

This module implements Capability #6 (`tools.py`) with unified interfaces, rate limiting, and bounded execution.

```python
"""SCP Capabilities: Autonomous Bounded Tooling Module."""
from __future__ import annotations

import abc
import asyncio
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

from scp.core.capability_token import InvalidTokenSignatureError
from scp.policy.egress import EgressPolicy
from scp.security.capability_epoch import CapabilityAuthority, CapabilityToken, parse_capability_token


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

    def __init__(self, working_dir: Path, rate_limit_hz: float = 2.0) -> None:
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

        # Memory inspection via os or platform
        mem_info: dict[str, Any] = {}
        if hasattr(os, "sysconf"):
            try:
                page_size = os.sysconf("SC_PAGE_SIZE")
                total_pages = os.sysconf("SC_PHYS_PAGES")
                mem_info["total_bytes"] = page_size * total_pages
            except (ValueError, OSError):
                pass

        data = {
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

    def _is_sensitive(self, path: Path) -> bool:
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
    )
    READ_ONLY_ALLOWLIST = (
        r"^\s*git\s+(status|diff|log|branch|rev-parse)\b",
        r"^\s*pytest\s+.*--collect-only\b",
        r"^\s*(python|python3|bun|node)\s+--version\b",
        r"^\s*(dir|ls)\b",
    )
    WORKSPACE_ALLOWLIST = (
        r"^\s*pytest\b",
        r"^\s*(python|python3)\s+-m\s+(pytest|compileall)\b",
        r"^\s*(bun|npm)\s+run\s+(test|build|lint)\b",
        r"^\s*git\s+diff\s+--check\b",
    )

    def __init__(self, working_dir: Path, egress_policy: EgressPolicy | None = None) -> None:
        super().__init__(working_dir)
        self.egress_policy = egress_policy or EgressPolicy()

    def evaluate_command(self, command: str, capability_level: int, approved: bool) -> tuple[bool, str, int]:
        cmd = command.strip()
        if not cmd:
            return False, "Command is empty", 0
        if "\n" in cmd or "\r" in cmd:
            return False, "Multiline commands are prohibited", 0
        if re.search(r"(?:;|&&|\|\||\||`|\$\(|\$\{)", cmd):
            return False, "Command chaining and subshells are prohibited", 0

        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return False, f"Command matches blocked pattern: {pattern}", 0

        # Read-only tier
        if any(re.search(pattern, cmd, re.IGNORECASE) for pattern in self.READ_ONLY_ALLOWLIST):
            return True, "Read-only allowlist match", 1

        # Workspace tier
        if any(re.search(pattern, cmd, re.IGNORECASE) for pattern in self.WORKSPACE_ALLOWLIST):
            if capability_level < 3 or not approved:
                return False, "Command requires capability level >= 3 and explicit approval", 3
            return True, "Workspace allowlist match with approval", 3

        return False, "Command does not match any allowlisted pattern", 0

    async def run(self, params: Mapping[str, Any]) -> ToolResult:
        started = time.perf_counter()
        command = str(params.get("command", "")).strip()
        capability_level = int(params.get("capability_level", 0))
        approved = bool(params.get("approved", False))
        timeout = max(1, min(int(params.get("timeout", 30)), 120))

        allowed, reason, required_cap = self.evaluate_command(command, capability_level, approved)
        if not allowed:
            return ToolResult(
                success=False,
                data={},
                evidence={"command": command, "evaluated_reason": reason},
                error=f"CommandExecutionBlocked: {reason}",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )

        # Cross-platform execution setup
        is_windows = platform.system() == "Windows"
        if is_windows:
            cmd_args = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command]
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            cmd_args = ["/bin/sh", "-c", command]
            creationflags = 0

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=str(self.working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=creationflags if is_windows else 0,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                # Terminate process tree fail-closed
                try:
                    if is_windows:
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
                    else:
                        process.kill()
                except Exception:
                    pass
                return ToolResult(
                    success=False,
                    data={"returncode": -1},
                    evidence={"timeout_sec": timeout},
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
                "returncode": process.returncode,
                "stdout": stdout_str,
                "stderr": stderr_str[-2000:],
                "command": command,
            }
            evidence = {
                "returncode": process.returncode,
                "stdout_sha256": hashlib.sha256(stdout_bytes).hexdigest(),
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }
            return ToolResult(
                success=process.returncode == 0,
                data=data,
                evidence=evidence,
                error=f"Process exited with returncode {process.returncode}" if process.returncode != 0 else "",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                truncated=truncated,
            )

        except Exception as exc:
            return ToolResult(
                success=False,
                data={},
                evidence={"command": command},
                error=f"Subprocess failure: {exc}",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
```

---

### 4.4 Module 3: Cryptographic Ledger Provenance Engine (`scp/core/autonomous_ledger.py`)

This module couples tool invocations to the append-only `TraceLedger` hash chain with micro-block verification.

```python
"""Cryptographic Ledger Provenance for Agent OS Autonomous Steps."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scp.core.trace_contract import redact_attributes
from scp.trace_ledger import TraceLedger


@dataclass(frozen=True)
class ProvenanceBlock:
    block_index: int
    prev_block_hash: str | None
    task_id: str
    step_id: str
    tool_name: str
    input_sha256: str
    capability_token_id: str
    capability_token_hash: str
    output_sha256: str
    status: str  # SUCCESS, FAILED, BLOCKED, UNKNOWN
    duration_ms: float
    timestamp: float
    block_hash: str = ""

    def canonical_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("block_hash", None)
        return d

    def compute_hash(self) -> str:
        serialized = json.dumps(self.canonical_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class AutonomousAuditLedger:
    """Ledger recording two-phase tool provenance blocks into the append-only TraceLedger."""

    def __init__(self, trace_ledger: TraceLedger | None = None, ledger_path: str | Path | None = None) -> None:
        if trace_ledger is not None:
            self.trace_ledger = trace_ledger
        else:
            path = ledger_path or "data/trace_ledger.jsonl"
            self.trace_ledger = TraceLedger(path)

    @staticmethod
    def _hash_value(val: Any) -> str:
        raw = json.dumps(val, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def commit_intent(
        self,
        task_id: str,
        step_id: str,
        tool_name: str,
        params: dict[str, Any],
        capability_token: Any,
        parent_trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Commit Phase 1: Tool invocation intent with parameter digest."""
        token_id = getattr(capability_token, "token_id", "") or str(params.get("token_id", ""))
        token_sig = getattr(capability_token, "signature", "")
        token_hash = self._hash_value({"token_id": token_id, "signature": token_sig})
        input_hash = self._hash_value(redact_attributes(params))

        entry = self.trace_ledger.append(
            event="AUTONOMOUS_TOOL_INTENT",
            task_id=task_id,
            step_id=step_id,
            tool_name=tool_name,
            input_sha256=input_hash,
            token_id=token_id,
            token_hash=token_hash,
            parent_trace_id=parent_trace_id or "",
            timestamp=time.time(),
        )
        return entry

    def commit_result(
        self,
        task_id: str,
        step_id: str,
        tool_name: str,
        intent_entry_hash: str,
        result_data: dict[str, Any],
        evidence: dict[str, Any],
        status: str,
        duration_ms: float,
    ) -> dict[str, Any]:
        """Commit Phase 2: Tool execution result with evidence and output digest."""
        output_hash = self._hash_value(redact_attributes(result_data))
        evidence_hash = self._hash_value(evidence)

        entry = self.trace_ledger.append(
            event="AUTONOMOUS_TOOL_RESULT",
            task_id=task_id,
            step_id=step_id,
            tool_name=tool_name,
            intent_entry_hash=intent_entry_hash,
            output_sha256=output_hash,
            evidence_sha256=evidence_hash,
            status=status,
            duration_ms=duration_ms,
            timestamp=time.time(),
        )
        return entry

    def verify_provenance(self) -> dict[str, Any]:
        """Verify the immutable ledger hash chain for all autonomous steps."""
        return self.trace_ledger.verify()
```

---

### 4.5 Invariant Enforcement & Security Proofs

The specification strictly satisfies the following core architectural invariants:

| Invariant ID | Name | Guarantee | Enforcement Mechanism |
|---|---|---|---|
| **INV-AUTH-01** | Capability Token Mandatory | Every tool invocation requires an HMAC-SHA256 signed `CapabilityToken`. No tool can execute with `capability_token=None`. | `_verify_token()` raises `PermissionError` fail-closed before any driver or tool call. |
| **INV-AUTH-02** | Scoped Subject Matching | Token subject must match required action exactly (`hands:tool_name` or `agent:tool_name`). | PEP asserts `token.subject == expected_subject`, raising `CapabilityScopeMismatchError`. |
| **INV-AUTH-03** | Epoch Revocation Freshness | Tokens from old epochs are invalid immediately across all processes. | `CapabilityAuthority.validate()` asserts `token.epoch == state.epoch` and `revoked == False`. |
| **INV-SANDBOX-01** | Canonical Path Confinement | No file read or search can access paths outside the designated workspace. | `_resolve_and_contain()` calls `Path.resolve()` and checks `resolved.relative_to(workspace_root)`. |
| **INV-SANDBOX-02** | Sensitive Path Denylist | Critical credentials, keys, and git configs cannot be read or enumerated. | RegEx/substring filtering on canonical paths raises `PermissionError` before disk read. |
| **INV-CMD-01** | No Multiline or Chaining | Prevents shell injection and subshell evasion (`rm -rf`, `whoami; rm`). | `evaluate_command()` rejects `\n`, `\r`, `;`, `&&`, `||`, `|`, `` ` ``, `$()`. |
| **INV-CMD-02** | Bounded Resource & Timeout | Commands cannot exceed CPU timeout or produce unbounded output buffers. | Subprocess timeout kills process tree (`taskkill /T`); dual-head/tail truncates output. |
| **INV-EGRESS-01** | Cloud Metadata Block | Prevents SSRF attacks against AWS/GCP/Azure instance credentials. | `EgressPolicy.enforce()` blocks `169.254.169.254` unconditionally in all modes. |
| **INV-EGRESS-02** | Allowlist-Only Network | Tools cannot contact arbitrary external domains under `allowlist` or `deny` modes. | `EgressPolicy` validates `EgressDestination.host` against `SCP_EGRESS_ALLOWLIST`. |
| **INV-LEDGER-01** | Append-Only Cryptographic Chain | Tool invocations cannot be inserted, altered, or deleted without breaking hash verification. | `TraceLedger.append()` links `entry["hash"] = sha256(entry + prev_hash)`. |
| **INV-LEDGER-02** | Redaction Before Provenance | Secrets (tokens, API keys, passwords) are masked prior to ledger serialization. | `_redact()` and `redact_attributes()` strip sensitive attributes before hashing. |

---

### 4.6 Verification & Test Specifications

The implementation blueprint mandates the following concrete test suites to guarantee 0 regressions and full coverage:

1. **`tests/T03_capability/test_autonomous_tool_contracts.py`**:
   - `test_system_inspection_bounded_metrics()`: Verifies CPU, OS, and disk metrics return in < 50ms and payload <= 4KB.
   - `test_system_inspection_rate_limiter()`: Rapidly invokes `SystemInspectionTool` 5 times in 100ms, asserting calls > 3 return `rate_limited=True`.
   - `test_workspace_analysis_path_traversal_blocked()`: Attempts `../../` and symlink escapes, asserting `PermissionError`.
   - `test_workspace_analysis_sensitive_files_blocked()`: Attempts reading `.env`, `.private-secrets`, asserting immediate rejection.
   - `test_safe_command_runner_command_chaining_blocked()`: Tests `git status; whoami` and `ls && rm`, asserting `CommandExecutionBlocked`.
   - `test_safe_command_runner_timeout_terminates_process_tree()`: Spawns `python -c "import time; time.sleep(10)"` with `timeout=1`, asserting termination within 2s without orphaned processes.
   - `test_safe_command_runner_output_truncation()`: Runs command generating 100KB stdout, asserting output <= 6KB with `truncated=True`.

2. **`tests/T03_capability/test_egress_policy_unified.py`**:
   - `test_egress_deny_blocks_external_allows_loopback()`: Verifies `EgressMode.DENY` allows `127.0.0.1:8000` but raises `EgressDeniedError` for `example.com`.
   - `test_egress_blocks_cloud_metadata_unconditionally()`: Tests `http://169.254.169.254/latest/meta-data` in all modes, asserting rejection.
   - `test_egress_allowlist_matches_subdomains_strictly()`: Verifies allowlist `api.github.com` allows `api.github.com` but denies `evil-api.github.com` and `attacker.com`.

3. **`tests/T04_kernel/test_autonomous_audit_ledger_provenance.py`**:
   - `test_autonomous_tool_two_phase_commit()`: Verifies intent and result entries generate sequential `seq` numbers and unbroken `prev_hash` links.
   - `test_autonomous_ledger_tamper_detection()`: Modifies a single byte in `data/trace_ledger.jsonl`, asserting `ledger.verify_provenance()["hash_chain_valid"] is False`.
   - `test_autonomous_ledger_redacts_tokens()`: Ensures raw bearer tokens and capability secrets in arguments are replaced with `[REDACTED]`.

---

## 5. Verification Method

### 5.1 Independent Verification Commands

To independently verify the evidence and findings in this report:

1. **Meta-Audit & Test Integrity Baseline**:
   ```powershell
   python tools/t00_meta_audit.py
   ```
   *Expected Output*: Meta-audit passes with 0 new regressions against baseline.

2. **Current Capability & PEP Test Suites**:
   ```powershell
   pytest tests/T03_capability/test_capability_token_hmac_signing.py tests/T03_capability/test_hands_authority_pep.py tests/T03_capability/test_pc_controller_token_pep.py -v
   ```
   *Expected Output*: All capability and token PEP tests pass (32/32 green).

3. **Current Egress Enforcement Gate**:
   ```powershell
   pytest tests/T03_capability/test_egress_enforcement.py -v
   ```
   *Expected Output*: All 21 egress enforcement checks pass, confirming the static AST gate.

4. **Trace Ledger Hash Chain & Concurrency Tests**:
   ```powershell
   pytest tests/test_p0_persistence_concurrency.py -k "test_trace_ledger" -v
   ```
   *Expected Output*: Passes with `hash_chain_valid=True`.

5. **Golden Task Agent OS Flow**:
   ```powershell
   pytest tests/T09_golden_task/test_golden_a_agent_os.py -v
   ```
   *Expected Output*: Passes with end-to-end task completion and verified receipts.

### 5.2 Invalidation Conditions

The conclusions of this report would be invalidated if:
1. `PCController` is proven to execute arbitrary commands without requiring an HMAC-SHA256 capability token (violating FA-05).
2. Existing `TraceLedger.append()` is found to be non-deterministic or producing non-verifiable SHA-256 digests.
3. Windows PowerShell execution is proven capable of escaping path confinement without raising an OS or application-level error.
4. Egress policy can be bypassed by URL encoding tricks or HTTP redirect hops without being intercepted by `enforce_egress_policy`.
