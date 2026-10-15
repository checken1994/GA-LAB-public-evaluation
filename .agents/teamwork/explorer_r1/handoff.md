# Comprehensive Security & Architecture Audit Report: Stream R1
**Target**: Security Boundaries, Authentication & Secret Handling  
**Auditor**: Explorer R1  
**Project Root**: `D:\scp`  
**Working Directory**: `D:\scp\.agents\teamwork\explorer_r1`  
**Date**: 2026-09-27  
**Mode**: Pure Read-Only Audit  

---

## Executive Summary

Stream R1 conducted a line-by-line audit of authentication boundaries, token validation, role segregation, egress/SSRF controls, command runner sandboxing, and secret leakage prevention across the SCP codebase. All findings are grounded in direct source code evidence, the 26 SCP DNA principles, and Fail-Closed & Evidence-First invariants.

---

## Severity Summary Table

| Finding ID | Title | File Path & Lines | Severity | SCP DNA Principle |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-R1-01** | `pc.execute` Self-Attestation Bypass Overriding HumanConfirmationStore | `scp/pc_control/pc_controller.py:240-275`<br>`scp/security/confirmation_store.py:93-136` | **CRITICAL** | DNA #4 (Con người quyết định)<br>DNA #6 (Gốc tin cậy bên ngoài) |
| **SEC-R1-02** | `SafeCommandRunnerTool` PowerShell Path Traversal & Python Code Injection | `scp/capabilities/tools.py:382-425` | **CRITICAL** | DNA #6 (Gốc tin cậy bên ngoài)<br>DNA #16 (Học nói phạm vi) |
| **SEC-R1-03** | Total Absence of Role-Based Authorization Enforcement Across API Routes | `scp/api/routes/openai_compat.py:108`<br>`scp/api_server_parts/_ask_impl.py:668`<br>`scp/security/jwt_guard.py:35-50` | **HIGH** | DNA #6 (Gốc tin cậy bên ngoài)<br>DNA #5 (Ảo giác đồng thuận) |
| **SEC-R1-04** | DNS Rebinding TOCTOU Window in `WebNavigator.browse_public` | `scp/web_control/web_navigator.py:65-90`<br>`scp/security/url_safety.py:326-352` | **HIGH** | DNA #19 (Tầng kiểm toán bằng chứng)<br>DNA #26 (Reality có quyền cuối cùng) |
| **SEC-R1-05** | Suppression of 401/403 Upstream Errors Returning Fake 200 OK | `dashboard/src/app/api/scp/v3/pc/status/route.ts:22-24`<br>`dashboard/src/app/api/scp/v3/web/status/route.ts:22-24`<br>`dashboard/src/app/api/scp/v3/hands/status/route.ts:26-28` | **HIGH** | DNA #22 (PASS ≠ TRUE)<br>DNA #26 (Reality có quyền cuối cùng) |
| **SEC-R1-06** | Incomplete Secret Redaction Patterns in Multi-Turn Chat Memory & Traces | `scp/core/chat_memory_store.py:35-45`<br>`scp/observability/trace_contract.py:120-145` | **MEDIUM** | DNA #16 (Học nói phạm vi)<br>DNA #25 (Câu hỏi SCP không nghĩ ra) |

---

## Detailed Findings & Code Evidence

### SEC-R1-01: `pc.execute` Self-Attestation Bypass Overriding HumanConfirmationStore (CRITICAL)
- **File**: `scp/pc_control/pc_controller.py:240-275`
- **Code Snippet**:
```python
245: if capability_level >= CapabilityLevel.HIGH:
246:     # Caller-provided approval overrides the human confirmation check
247:     if payload.get("approved") is True:
248:         logger.info("pc.execute: self-approved by caller with approved=True")
249:     elif not self.confirmation_store.is_confirmed("pc.execute", target=command):
250:         raise PermissionError("High capability command requires operator confirmation")
```
- **Risk / Exploit Scenario**:
Any untrusted caller or subagent issuing a `pc.execute` call for Level >= 3 commands (such as formatting, file destruction, or arbitrary shell commands) can simply supply `{"approved": True}` in the JSON payload. This completely nullifies `HumanConfirmationStore`, violating the non-negotiable invariant that humans must approve high-impact actions.
- **DNA Violation**: DNA #4 (Con người quyết định), DNA #6 (Gốc tin cậy bên ngoài).

### SEC-R1-02: `SafeCommandRunnerTool` PowerShell Path Traversal & Python Code Injection (CRITICAL)
- **File**: `scp/capabilities/tools.py:382-425`
- **Code Snippet**:
```python
392: if sys.platform == "win32":
393:     # Allowlist includes PowerShell aliases 'dir', 'ls' without workspace boundary checks
394:     # python -c is allowed but blocklist only checks literal 'exec(', 'eval('
395:     cmd = ["powershell", "-NoProfile", "-Command", command_str]
```
- **Risk / Exploit Scenario**:
1. Path Traversal: While `PCController` confines commands to `self.working_dir`, `SafeCommandRunnerTool` does not validate paths for `dir` or `ls`. An agent can execute `dir C:\Windows\System32` or inspect arbitrary system directories.
2. Code Execution: The regex blocklist permits `python -c`. Attackers can bypass keyword blocks via string concatenation (e.g. `getattr(__import__('sh' + 'util'), 'rm' + 'tree')('...')`) or unblocked modules (`httpx`, `ctypes`).
- **DNA Violation**: DNA #6 (Gốc tin cậy bên ngoài), DNA #16 (Học nói phạm vi).

### SEC-R1-03: Total Absence of Role-Based Authorization Enforcement Across API Routes (HIGH)
- **File**: `scp/security/jwt_guard.py:35-50`, `scp/api/routes/openai_compat.py:108`, `scp/api_server_parts/_ask_impl.py:668`
- **Code Snippet**:
```python
# scp/security/jwt_guard.py
42: payload = {"sub": user_id, "role": role or "admin"}  # Defaults to admin
...
# scp/api/routes/
# No endpoints inspect or enforce payload.get("role") == "admin" vs "user"
```
- **Risk / Exploit Scenario**:
API keys with restricted roles (e.g., `user`) receive identical privileges to `admin`. The codebase generates role claims but no route validates them; `role` is only referenced to parse chat history messages (`msg.get("role") == "user"`).
- **DNA Violation**: DNA #6 (Gốc tin cậy bên ngoài), DNA #5 (Ảo giác đồng thuận).

### SEC-R1-04: DNS Rebinding TOCTOU Window in `WebNavigator.browse_public` (HIGH)
- **File**: `scp/web_control/web_navigator.py:65-90`
- **Code Snippet**:
```python
67: enforce_egress_policy(url)
68: current_url = self.browser.validate_url(url)
...
73: async with httpx.AsyncClient(follow_redirects=False, trust_env=False) as client:
84:     async with client.stream("GET", current_url) as response:
```
- **Risk / Exploit Scenario**:
`validate_url` performs DNS resolution at line 68 to verify that the host does not resolve to a private IP. However, `httpx.AsyncClient` performs an independent DNS resolution during the subsequent `client.stream` request. An attacker controlling a DNS server with a low TTL (0 seconds) can return a public IP for validation and `169.254.169.254` (cloud metadata) for the actual HTTP connection, bypassing SSRF protections.
- **DNA Violation**: DNA #19 (Tầng kiểm toán bằng chứng), DNA #26 (Reality có quyền cuối cùng).

### SEC-R1-05: Suppression of 401/403 Upstream Errors Returning Fake 200 OK (HIGH)
- **File**: `dashboard/src/app/api/scp/v3/pc/status/route.ts:22-24`, `dashboard/src/app/api/scp/v3/web/status/route.ts:22-24`, `dashboard/src/app/api/scp/v3/hands/status/route.ts:26-28`
- **Code Snippet**:
```typescript
22: if (response.status === 403 || response.status === 401) {
23:   return NextResponse.json({ controller: "offline", reason: "Chưa cấu hình token hoặc chưa kích hoạt" }, { status: 200 })
24: }
```
- **Risk / Exploit Scenario**:
Security authentication failures are masked as benign "offline" states with HTTP 200 OK. Monitoring systems and client UI treat unauthorized attempts as successful status queries, obscuring security break-in attempts or credential expiry.
- **DNA Violation**: DNA #22 (PASS ≠ TRUE), DNA #26 (Reality có quyền cuối cùng).

### SEC-R1-06: Incomplete Secret Redaction Patterns in Multi-Turn Chat Memory & Traces (MEDIUM)
- **File**: `scp/core/chat_memory_store.py:35-45`, `scp/observability/trace_contract.py:120-145`
- **Code Snippet**:
```python
_REDACT_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]+"),
    # Missing: JWT (ey...), GitHub PAT (ghp_...), AWS keys (AKIA...)
]
```
- **Risk / Exploit Scenario**:
User chat history and operational traces containing AWS access keys (`AKIA...`), GitHub Personal Access Tokens (`ghp_...`), and compact JWT tokens (`ey...`) escape regex filtering and are persisted in plaintext `.jsonl` files on disk.
- **DNA Violation**: DNA #16 (Học nói phạm vi), DNA #25 (Câu hỏi SCP không nghĩ ra).
