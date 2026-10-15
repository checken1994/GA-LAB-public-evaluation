# Comprehensive Technical Survey & Mapping Report: R1 & R2
**Date:** 2026-09-22T18:15:00Z  
**Agent:** explorer_o6_survey_1  
**Working Directory:** `D:\scp\.agents\explorer_o6_survey_1`  
**Target Codebase:** SCP (Secure Control Plane) Agent OS  
**Status:** Completed  

---

## 1. Executive Summary

This survey provides exhaustive technical mapping, file verification, line-by-line vulnerability analysis, and architectural integration plans for:
1. **R1: Critical Security Chain** — A composite exploit chain spanning 4 interconnected subsystems (Dashboard Middleware, Dashboard Route Proxy, Backend Chatbot Lane Governance, JWT Guard, and Evaluation API) that enables unauthenticated remote clients to obtain admin credentials, bypass governance safety killswitches, and fail open on evaluations.
2. **R2: Runtime Wiring of Unwired Security Modules** — Remediation of the "hardening trang trí" (decorative hardening) anti-pattern where three production-grade security engines (`scp/capabilities/tools.py`, `scp/policy/egress.py`, `scp/core/autonomous_ledger.py`) have passed unit tests and adversarial probes in isolation, but possess **zero production callers** in the runtime execution pipeline.

### Core Survey Findings Matrix

| Ref | Target Subsystem | Exact File Location & Lines | Status in Codebase | Severity | Runtime Status |
|---|---|---|---|---|---|
| **R1.1** | Dashboard Middleware Fail-Open | `dashboard/src/middleware.ts:6-7` | Confirmed active bug | **CRITICAL** | Production active |
| **R1.2** | Dashboard JWT Admin Auto-Minting | `dashboard/src/app/api/scp/ask/route.ts:15-34` *(prompt cited `dashboard/src/app/ask/route.ts`)* | Confirmed active bug | **CRITICAL** | Production active |
| **R1.3** | Chatbot Lane KILL Override to ALLOW | `scp/api_server_parts/_ask_impl.py:548-555,645-648` *(prompt cited `scp/api/_ask_impl.py:646-648`)* & `scp/api/chat.py:497-503` | Confirmed active bug | **CRITICAL** | Production active |
| **R1.4** | JWT Guard Accepting Static Keys as Admin | `scp/security/jwt_guard.py:37-43` | Confirmed active bug | **HIGH** | Production active |
| **R1.5** | Evaluation API Default PASS & Unclamped Confidence | `scp/api/routes/evaluation_routes.py:86-88, 211-212, 226-233` | Confirmed active bug | **HIGH** | Production active |
| **R2.1** | Bounded Autonomous Tools Engine | `scp/capabilities/tools.py` | Standalone library | **HIGH** | **0 production callers** (unwired) |
| **R2.2** | Unified Fail-Closed Egress Engine | `scp/policy/egress.py` | Standalone library | **HIGH** | **0 production callers** (unwired) |
| **R2.3** | Cryptographic Provenance Ledger | `scp/core/autonomous_ledger.py` | Standalone library | **HIGH** | **0 production callers** (unwired) |

---

## 2. R1: Critical Security Chain Deep Dive

### R1.1: Dashboard Middleware Fail-Open (`dashboard/src/middleware.ts:6-7`)

#### Code Observation
```typescript
File: D:/scp/dashboard/src/middleware.ts
Lines 4-17:
4: export function middleware(request: NextRequest) {
5:   // Fix B2: Prevent LAN access to unauthenticated proxy across all dashboard routes
6:   const clientIp = request.headers.get("x-forwarded-for") || request.headers.get("x-real-ip") || "127.0.0.1";
7:   const isLocal = clientIp.includes("127.0.0.1") || clientIp.includes("::1") || clientIp.includes("localhost");
8:   
9:   if (!isLocal && request.nextUrl.pathname.startsWith("/api/scp/")) {
10:     return NextResponse.json(
11:       { error: "Access denied. Dashboard API is restricted to localhost." },
12:       { status: 403 }
13:     );
14:   }
15:   
16:   return NextResponse.next();
17: }
18: 
19: export const config = {
20:   matcher: "/api/scp/:path*",
21: };
```

#### Vulnerability Analysis & Logic Chain
1. **Unconditional Localhost Fallback (Line 6):** If an external client connects directly (e.g. from the Internet or LAN) without proxy headers, `request.headers.get("x-forwarded-for")` and `request.headers.get("x-real-ip")` are `null`. The code falls back to `"127.0.0.1"`.
2. **Fail-Open Local Check (Line 7):** `"127.0.0.1".includes("127.0.0.1")` evaluates to `true`, making `isLocal === true`. The 403 restriction at line 9 is bypassed completely.
3. **Trivial Header Spoofing:** Because client-supplied headers are trusted unconditionally, any external client can inject `X-Forwarded-For: 127.0.0.1` or `X-Real-IP: 127.0.0.1`.
4. **Substring Match Insecurity:** `.includes("127.0.0.1")` matches any string containing that substring (e.g., `X-Forwarded-For: 203.0.113.195, 127.0.0.1`).
5. **Partial Route Matcher (Line 20):** `matcher: "/api/scp/:path*"` leaves other dashboard routes (such as `/api/audit`, `/api/autofix`, `/api/scanners`) completely uninspected by middleware.

#### Remediation Specification
- Eliminate the `"127.0.0.1"` fallback string.
- If running behind a reverse proxy, extract the left-most client IP only from trusted proxy hops; if standalone, inspect `request.ip` or connection socket address.
- Fail closed: if the client IP cannot be proven to be loopback (`127.0.0.1`, `::1`), immediately reject with 403 Forbidden.
- Require session/token authentication on all proxy routes.

---

### R1.2: Dashboard JWT Admin Auto-Minting (`dashboard/src/app/api/scp/ask/route.ts:15-34`)

*(Note on path: Cited in dispatch as `dashboard/src/app/ask/route.ts`; actual filesystem path is `dashboard/src/app/api/scp/ask/route.ts`)*

#### Code Observation
```typescript
File: D:/scp/dashboard/src/app/api/scp/ask/route.ts
Lines 15-35:
15: function createJwt(secret: string): string {
16:   const h = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url")
17:   const p = Buffer.from(JSON.stringify({ sub: "admin", exp: Math.floor(Date.now() / 1000) + 3600 })).toString("base64url")
18:   const sig = createHmac("sha256", secret).update(`${h}.${p}`).digest("base64url")
19:   return `${h}.${p}.${sig}`
20: }
21: 
22: async function readAdminToken(): Promise<string> {
23:   const jwtSecret = process.env.SCP_JWT_SECRET?.trim()
24:   if (jwtSecret) {
25:     return createJwt(jwtSecret)
26:   }
27:   const direct = process.env.SCP_AUTH_TOKEN_SECRET?.trim()
28:   if (direct) return direct
29:   if (!TOKEN_FILE) return ""
30:   try {
31:     return (await readFile(TOKEN_FILE, "utf8")).trim()
32:   } catch {
33:     return ""
34:   }
35: }
...
Lines 60-70:
60:     const token = await readAdminToken()
61:     if (!token) return NextResponse.json({ error: "SCP auth token chưa được cấu hình" }, { status: 503 })
...
69:       headers: { Accept: "application/json", "Content-Type": "application/json", Authorization: `Bearer ${token}` },
70:       body: JSON.stringify(payload),
```

#### Vulnerability Analysis & Logic Chain
1. **Confused Deputy Credential Auto-Minting:** The `POST` route handler accepts unauthenticated incoming HTTP requests from the browser/client.
2. In lines 22-26, it reads the server's own `SCP_JWT_SECRET` environment variable and mints a brand-new signed JWT with `sub: "admin"`.
3. It then attaches this minted admin JWT as `Authorization: Bearer ${token}` to the backend `/ask` endpoint.
4. **Exploit Synergy with R1.1:** Any remote client who bypasses or passes through `middleware.ts` can POST to `/api/scp/ask`. The Next.js server acts as a confused deputy, forging an admin identity for the anonymous client.

#### Remediation Specification
- Prohibit auto-minting admin JWTs for incoming client requests.
- The route handler must extract user credentials or active session token from the incoming client request (`request.headers.get("Authorization")` or session cookie).
- If no valid client credential exists, return `401 Unauthorized`.
- If client credentials exist, forward the client's token or verify the user's authenticated identity before interacting with the SCP backend.

---

### R1.3: Chatbot Lane Governance KILL Override to ALLOW (`scp/api_server_parts/_ask_impl.py` & `scp/api/chat.py`)

*(Note on path: Cited in dispatch as `scp/api/_ask_impl.py:646-648`; actual production implementation file is `scp/api_server_parts/_ask_impl.py`. There is also a dead file `prev_ask_impl.py` at the repo root).*

#### Code Observation
```python
File: D:/scp/scp/api_server_parts/_ask_impl.py
Lines 304-306:
304:     from scp.runtime.question_router import route_question, LANE_CHATBOT, LANE_FACTUAL, LANE_SECURITY
305:     _route_decision = route_question(req.question)
306:     _is_chatbot_lane = (_route_decision.lane == LANE_CHATBOT or getattr(_route_decision, "bypass_verdict_pass", False))
...
Lines 548-555:
548:     _is_true_security_threat = (
549:         (_gov_decision == 'KILL' and not _is_chatbot_lane)
550:         or v.verdict == 'FLAGGED'
551:         or _multimodal_block
552:         or _route_decision.lane == LANE_SECURITY
553:         or bool(v.evidence.get('threat_detected'))
554:         or bool(v.evidence.get('injection_detected'))
555:     )
...
Lines 645-648:
645:         if v.verdict in ('FAIL', 'UNKNOWN'):
646:             v.verdict = 'PASS'
647:         if _gov_decision == 'KILL' or not _gov_decision:
648:             _gov_decision = 'ALLOW'
```

And in the WebSocket chat handler:
```python
File: D:/scp/scp/api/chat.py
Lines 479-482:
479:                 _is_chatbot_lane = (_route.lane == LANE_CHATBOT or getattr(_route, "bypass_verdict_pass", False))
480:                 _gov = v.evidence.get("governance_decision", "")
...
Lines 497-503:
497:                 elif _is_chatbot_lane:
498:                     _abstain = False
499:                     _ws_answer = v.final_answer or _candidate_answer or "(Không có câu trả lời)"
500:                     _ws_reasoning = v.reasoning[:300] if v.reasoning else ""
501:                     if v.verdict in ("UNKNOWN", "FAIL"):
502:                         v.verdict = "PASS"
```

#### Vulnerability Analysis & Logic Chain
1. **Safety Exemption for Chatbot Lane (Line 549):** The boolean `_is_true_security_threat` gates whether an answer is withheld. Line 549 explicitly subtracts the chatbot lane: `(_gov_decision == 'KILL' and not _is_chatbot_lane)`. If a request is classified as `LANE_CHATBOT`, a governance KILL decision is ignored by the security threat detector.
2. **Explicit Governance Decision Override (Lines 647-648):** Under `elif _is_chatbot_lane:`, if `_gov_decision == 'KILL'`, it is explicitly rewritten to `_gov_decision = 'ALLOW'`.
3. **Verdict Whitewashing (Line 646 & Line 502):** The verification verdict is rewritten from `FAIL` or `UNKNOWN` to `PASS`.
4. **DNA Violation (FA-01, FA-02, Reality over Model):** The Governance Engine is the highest-tier system safety circuit breaker. Overriding a KILL verdict based on natural language categorization (chatbot lane) allows adversaries to bypass all security policies simply by phrasing hostile requests as casual conversation.

#### Remediation Specification
- Governance `KILL` verdict must be absolute and non-negotiable.
- Remove `and not _is_chatbot_lane` from `_is_true_security_threat`.
- If `_gov_decision == 'KILL'`, response must withhold answer: `_api_final_answer = '[SCP: Answer withheld — Governance KILL]'`, verdict must remain `FAIL`, and `_gov_decision` must propagate as `'KILL'`.
- Delete lines 647-648 in `_ask_impl.py` that set `_gov_decision = 'ALLOW'`.
- In `chat.py`, if `_gov == "KILL"`, `_abstain` must be `True` and verdict must remain `FAIL`.

---

### R1.4: JWT Guard Accepting Static Keys as Admin (`scp/security/jwt_guard.py:37-43`)

#### Code Observation
```python
File: D:/scp/scp/security/jwt_guard.py
Lines 36-51:
36: def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
37:     token = credentials.credentials.strip()
38:     import secrets as _secrets
39:     for env_key in ("SCP_API_KEY", "SCP_ADMIN_KEY", "SCP_AUTH_TOKEN_SECRET"):
40:         expected = os.environ.get(env_key, "").strip()
41:         if expected and _secrets.compare_digest(token.encode("utf-8"), expected.encode("utf-8")):
42:             return {"sub": "admin", "role": "admin", "auth_type": "api_key"}
43: 
44:     try:
45:         payload = jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
46:         return payload
47:     except jwt.ExpiredSignatureError:
48:         raise HTTPException(status_code=401, detail="Token has expired")
49:     except jwt.InvalidTokenError:
50:         raise HTTPException(status_code=401, detail="Invalid token")
```

#### Vulnerability Analysis & Logic Chain
1. **Conflation of Token Types:** `verify_jwt_token` is designated as the PEP for cryptographically verifiable JWTs with expiration (`exp`) and subject (`sub`).
2. **Blanket Admin Grant for API Keys:** Lines 39-42 iterate through `SCP_API_KEY`, `SCP_ADMIN_KEY`, and `SCP_AUTH_TOKEN_SECRET`. If any matches the bearer token string, it unconditionally returns `{"sub": "admin", "role": "admin", "auth_type": "api_key"}`.
3. Even a non-admin key (`SCP_API_KEY`) is automatically escalated to `role: "admin"`.
4. Static keys do not expire and cannot carry user identity or claims, destroying audit provenance across multi-agent calls.

#### Remediation Specification
- Strict separation of auth paths: `verify_jwt_token` must ONLY accept valid, signed JWTs. If a static key is passed into `verify_jwt_token`, it must raise `HTTPException(401, detail="Invalid token")`.
- Define a separate dependency `verify_api_key` for routes that legitimately accept static API keys, with distinct scopes for `SCP_API_KEY` (standard user) vs `SCP_ADMIN_KEY` (admin).

---

### R1.5: Evaluation API Default PASS & Unvalidated Confidence (`scp/api/routes/evaluation_routes.py:86-88, 211-212, 226-233`)

#### Code Observation
```python
File: D:/scp/scp/api/routes/evaluation_routes.py
Lines 85-88 (Prompt Delimiter Injection):
85: STATE TO EVALUATE:
86: \"\"\"
87: {state[:20000]}
88: \"\"\"
...
Lines 210-213 (Default PASS on Error):
210:     answers: Dict[str, Any] = {}
211:     verdict = "PASS" if is_safe else "FAIL"
212:     confidence = 0.85 if is_safe else 0.0
213:     reasoning = "Evaluated via SCP Independent Verifier"
...
Lines 226-233 (Unvalidated Verdict & Unclamped Confidence):
226:                 if parsed.get("verdict"):
227:                     verdict = str(parsed["verdict"]).upper()
228:                     try:
229:                         confidence = float(parsed["confidence"])
230:                     except (ValueError, TypeError):
231:                         logger.debug("Evaluation confidence float conversion ignored", exc_info=True)
232:                 if parsed.get("reasoning"):
233:                     reasoning = str(parsed["reasoning"])
```

#### Vulnerability Analysis & Logic Chain
1. **Silent Fallback to PASS (Line 211-212):** If the LLM call times out, crashes, or returns unparseable JSON, `verdict` defaults to `"PASS"` (because `is_safe` is just the Tier 1 AST syntax check) with `confidence = 0.85`. This directly violates the fail-closed invariant.
2. **Unvalidated Verdict (Line 227):** `verdict` takes any arbitrary string from the LLM without validating against the expected verdict set (`PASS`, `FAIL`, `FLAGGED`, `UNKNOWN`).
3. **Unclamped Confidence (Line 229):** The raw float is assigned without bounds checking, allowing values like `999.0` or `-5.0`.
4. **Prompt Delimiter Escape (Lines 86-88):** Raw `state` is injected into `\"\"\"{state[:20000]}\"\"\"`. An input containing `"""` escapes the evaluation block and can inject arbitrary instructions to force the LLM to output `{"verdict": "PASS", "confidence": 1.0}`.

#### Remediation Specification
- Default verdict on LLM error/parse failure must be `UNKNOWN` or `FAIL`, with confidence `0.0`.
- Strict validation: `verdict` must be validated against `{"PASS", "FAIL", "FLAGGED", "UNKNOWN"}` (fallback to `UNKNOWN` if unrecognized).
- Confidence must be clamped: `confidence = max(0.0, min(1.0, float(confidence)))`.
- Escape delimiters in the evaluation prompt (e.g., XML tags `<state_to_evaluate>` with escaping or unique random boundary tokens).

---

### R1.6: Requirements and Architecture for Chain-Break Integration Test

To definitively prove that the critical security chain is severed at every link, an integration test suite must be implemented (recommended location: `tests/T02_contract/test_critical_security_chain_break.py`).

```
                    CRITICAL CHAIN-BREAK TEST TOPOLOGY
                    
  [External Client]
         │
    (1)  ▼  (Header spoof: X-Forwarded-For: 127.0.0.1 or missing)
  [dashboard/src/middleware.ts] ──────► [Assert: 403 Forbidden]
         │ (If bypassed)
    (2)  ▼
  [dashboard/src/app/api/scp/ask/route.ts] ──► [Assert: No admin JWT auto-minted]
         │ (If forged JWT sent)
    (3)  ▼
  [scp/security/jwt_guard.py] ────────► [Assert: Static key rejected as JWT]
         │ (If prompt sent)
    (4)  ▼
  [scp/api_server_parts/_ask_impl.py] ──► [Assert: Governance KILL propagated,
                                                    never overridden to ALLOW]
         │
    (5)  ▼
  [scp/api/routes/evaluation_routes.py] ─► [Assert: Gateway crash yields UNKNOWN/0.0,
                                                    never default PASS]
```

#### Test Suite Specification
1. **Test Case 1: `test_middleware_rejects_spoofed_and_missing_ip()`**
   - Submit request to `/api/scp/ask` with `X-Forwarded-For: 203.0.113.1` -> assert status 403.
   - Submit request with missing `X-Forwarded-For` and `X-Real-IP` -> assert status 403 (no fail-open default).
2. **Test Case 2: `test_dashboard_ask_route_prohibits_auto_minting()`**
   - Submit unauthenticated request to `/api/scp/ask` -> assert status 401.
   - Inspect forwarded request payload to verify no admin JWT (`sub: admin`) is manufactured.
3. **Test Case 3: `test_jwt_guard_rejects_static_admin_key()`**
   - Call `verify_jwt_token(HTTPAuthorizationCredentials(scheme="Bearer", credentials="<SCP_ADMIN_KEY>"))`.
   - Assert `HTTPException` with status code 401 is raised.
4. **Test Case 4: `test_chatbot_lane_governance_kill_cannot_be_overridden()`**
   - Mock QuestionRouter to return `lane = LANE_CHATBOT`.
   - Mock Judge to return `governance_decision = "KILL"` and verdict `"FAIL"`.
   - Execute `/ask` implementation.
   - Assert `response.verdict != "PASS"`, `response.final_answer == "[SCP: Answer withheld — Governance KILL]"`, and `response.governance_decision == "KILL"`.
5. **Test Case 5: `test_evaluation_routes_fail_closed_on_gateway_error()`**
   - Mock LLM gateway to raise `RuntimeError("LLM Gateway down")`.
   - Call `/v1/eval` with arbitrary state.
   - Assert `response.verdict in ("UNKNOWN", "FAIL")` and `response.confidence == 0.0`.
   - Call `/v1/eval` with mocked LLM output `{"verdict": "HACKED", "confidence": 150.0}`.
   - Assert `response.verdict == "UNKNOWN"` and `response.confidence == 1.0` (clamped).

---

## 3. R2: Runtime Wiring of Unwired Security Modules Deep Dive

### R2.1: Bounded Autonomous Tools (`scp/capabilities/tools.py`)

#### Code Summary & Capabilities
`scp/capabilities/tools.py` (424 lines) defines:
- `BaseAutonomousTool`: Abstract base enforcing `working_dir` containment and `TokenBucketRateLimiter`.
- `SystemInspectionTool` (`sys.inspect`): Bounded OS, CPU, disk, memory diagnostics without shelling out; capped at 4KB serialization.
- `WorkspaceAnalysisTool` (`workspace.analyze`): Confinded workspace directory tree, file search, and bounded file reading; blocks path traversal and sensitive patterns (`.env`, `.private-secrets`, `credentials`, `.key`).
- `SafeCommandRunnerTool` (`cmd.run`): 11 blocked pattern regexes (format, shutdown, reg delete, rm -rf, curl|bash, iex, sudo, etc.), prohibitions on redirection (`><`), command chaining (`;`, `&&`, `||`, `|`, subshells), read-only and workspace allowlists, cross-platform PowerShell/sh execution with process tree kill on timeout, and dual head/tail output truncation (first 2,000 + last 4,000 chars).

#### Current Runtime Path vs Unwired Status
- **Callers Inventory:** `grep -rn "capabilities.tools"` reveals **only 2 callers**:
  1. `tests/T03_capability/test_autonomous_tool_contracts.py:10`
  2. `tools/adversarial_goal3_probe.py:26`
  **Production runtime callers: 0.**
- **Existing Runtime Execution Path:**
  - `scp/hands/planner.py:486-495`: When `autonomous_mode` is enabled, it queries `AutonomousCapabilityGovernor` (`scp/security/autonomous_governor.py`).
  - `AutonomousCapabilityGovernor` checks only 4 simplistic regexes (`rm -rf /`, `nc -e`, `curl | bash`, `sudo`).
  - Once granted, `HandsExecutor._pc_command` in `scp/hands/hands_executor.py:126-130` calls `PCController.execute()`, which executes raw commands via `subprocess.run(["powershell.exe", ...])` without rate limiting, without subshell blocking, and without dual head/tail truncation.

#### Wiring & Integration Specification
1. **Governor Delegation:** In `scp/security/autonomous_governor.py`, replace the simplistic regex check with `SafeCommandRunnerTool.evaluate_command(command, capability_level, approved)`.
2. **Action Registry Registration:** In `scp/hands/action_registry.py`, register `sys.inspect`, `workspace.analyze`, and `cmd.run` as first-class actions.
3. **Execution Path Delegation:** In `scp/hands/hands_executor.py:execute()`, when executing `pc.execute` or `cmd.run`, delegate the command execution to `SafeCommandRunnerTool.run()`. When executing workspace queries, delegate to `WorkspaceAnalysisTool`.

---

### R2.2: Fail-Closed Unified Egress Engine (`scp/policy/egress.py`)

#### Code Summary & Capabilities
`scp/policy/egress.py` (164 lines) defines:
- `EgressPolicy`, `EgressDestination`, `EgressMode` (`DENY`, `ALLOWLIST`, `OPEN`), and `EgressDeniedError`.
- **Invariant 1:** Cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`, `metadata.aws`, `169.254.170.2`, `169.254.0.0/16`) are **unconditionally blocked** across ALL modes, even in OPEN mode and even if explicitly listed in the allowlist.
- **Invariant 2:** Loopback (`127.0.0.1`, `::1`, `localhost`) is always permitted for internal microservices.
- **Invariant 3:** `DENY` mode blocks all external network traffic.
- **Invariant 4:** `ALLOWLIST` mode supports wildcard domain matching (`*.github.com`) and per-token allowed hosts.
- **Invariant 5:** In production mode (`SCP_PRODUCTION_MODE=1`), any non-explicit mode fails closed.

#### Current Runtime Path vs Unwired Status
- **Callers Inventory:** `grep -rn "policy.egress"` reveals **only 3 callers**:
  1. `scp/capabilities/tools.py:18` (which itself has 0 production callers)
  2. `tools/adversarial_goal3_probe.py:32`
  3. `tests/T03_capability/test_egress_policy_unified.py:6`
  **Production runtime callers: 0.**
- **Existing Runtime Execution Path:**
  Production code relies on two fragmented, older implementations:
  1. `scp/security/url_safety.py`: Defines `enforce_egress_policy()` and `safe_urlopen()`. Over 20 runtime files import this module (including `web_navigator.py`, `browser_session.py`, `url_fetcher.py`, `internet_search.py`, `llm_gateway/client.py`, `runtime/notifications.py`). It has a dev-default OPEN gap (`if not mode and not _production_mode_declared(): return`).
  2. `scp/llm_gateway/egress_policy.py`: Has `llm_egress_allowed()` with separate `_DENY_MODES` and dev-default OPEN (`if mode == "": return True`).

#### Wiring & Integration Specification
The cleanest and most robust integration strategy:
1. **Bridge via `scp/security/url_safety.py`:**
   Modify `scp/security/url_safety.py` to instantiate and delegate `enforce_egress_policy` to `scp.policy.egress.EgressPolicy`:
   ```python
   from scp.policy.egress import EgressPolicy, EgressDeniedError as _UnifiedEgressDeniedError

   _UNIFIED_EGRESS_POLICY = EgressPolicy()

   def enforce_egress_policy(url, extra_allowed_hosts=None):
       _UNIFIED_EGRESS_POLICY.enforce(url, token_allowed_hosts=extra_allowed_hosts)
   ```
2. **Bridge via `scp/llm_gateway/egress_policy.py`:**
   Update `llm_egress_allowed(base_url)` to delegate checking to `_UNIFIED_EGRESS_POLICY`.
3. **Impact:** Instantly wires `scp/policy/egress.py` into all 20+ runtime network choke points across the entire system without modifying 20 disparate call-sites.

---

### R2.3: Cryptographic Provenance Ledger (`scp/core/autonomous_ledger.py`)

#### Code Summary & Capabilities
`scp/core/autonomous_ledger.py` (127 lines) defines:
- `ProvenanceBlock`: Structured record tracking `task_id`, `step_id`, `tool_name`, `input_sha256`, `capability_token_id`, `capability_token_hash`, `output_sha256`, `status`, `duration_ms`, `timestamp`, `prev_block_hash`.
- `AutonomousAuditLedger`: Two-phase commit ledger:
  - `commit_intent()`: Phase 1 pre-dispatch recording with parameter redaction and input hash.
  - `commit_result()`: Phase 2 post-dispatch recording linking to intent entry hash with evidence and output digests.
  - `verify_provenance()`: Traverses and validates the immutable hash chain.

#### Current Runtime Path vs Unwired Status
- **Callers Inventory:** `grep -rn "AutonomousAuditLedger"` reveals **only 2 callers**:
  1. `tests/T04_kernel/test_autonomous_audit_ledger_provenance.py:9`
  2. `tools/adversarial_goal3_probe.py:31`
  **Production runtime callers: 0.**
- **Existing Runtime Execution Path:**
  - `HandsExecutor` (`scp/hands/hands_executor.py:62-65`) uses `_audit()`, which directly appends raw JSON lines to `data/hands/audit.jsonl` without cryptographic hashing, without two-phase commit, and without tamper detection.
  - `TaskKernelHandsBridge` (`scp/hands/task_kernel_bridge.py`) records state transitions in SQLite, but does not emit two-phase cryptographic provenance blocks to the trace ledger.

#### HMAC vs Bare SHA-256 Analysis
- **The Threat Model:**
  - Bare SHA-256 forms a Merkle hash chain (`prev_hash`). This detects bit flips or accidental corruption, but **cannot prevent forgery** by a local attacker or rogue subagent with write permissions to the ledger file (`data/trace_ledger.jsonl`), because anyone can rewrite the file and recompute valid SHA-256 hashes.
  - **HMAC-SHA256 (Keyed Hash):** Keys the digest with a secret key held exclusively by the Kernel/Supervisor (`SCP_LEDGER_HMAC_SECRET` or derived from the Capability Authority epoch key).
  - Even if an attacker has read/write access to the JSONL log file, they cannot forge new blocks or alter historical blocks without invalidating the HMAC signature.
- **Recommended Wiring:**
  1. In `scp/core/autonomous_ledger.py`, support keyed HMAC-SHA256: if `hmac_secret` is configured, compute `hmac.new(secret, serialized, hashlib.sha256).hexdigest()`. For backwards compatibility with existing tests expecting `sha256:`, format hash as `"hmac-sha256:"` or maintain a dual-hash verification mechanism.
  2. In `scp/hands/hands_executor.py`:
     - Initialize `self.audit_ledger = AutonomousAuditLedger(ledger_path=self.data_dir / "audit_trace_ledger.jsonl")`.
     - In `execute()`:
       - Before dispatch: Call `intent_entry = self.audit_ledger.commit_intent(task_id, step_id, action, params, capability_token)`.
       - After dispatch: Call `self.audit_ledger.commit_result(task_id, step_id, action, intent_entry["hash"], result, evidence, status, duration_ms)`.
     - This anchors every autonomous tool action into a verifiable cryptographic ledger.

---

## 4. Implementation Guidance & Remediation Checklist

For the implementer agent(s), follow this precise execution sequence:

```
[Phase 1: Break R1 Security Chain]
  ├── 1. dashboard/src/middleware.ts -> Remove 127.0.0.1 fallback; fail-closed IP verification.
  ├── 2. dashboard/src/app/api/scp/ask/route.ts -> Remove createJwt(secret); require user auth.
  ├── 3. scp/api_server_parts/_ask_impl.py & scp/api/chat.py -> Remove KILL override to ALLOW.
  ├── 4. scp/security/jwt_guard.py -> Prohibit static keys in verify_jwt_token.
  └── 5. scp/api/routes/evaluation_routes.py -> Fail-closed on error (UNKNOWN/0.0), validate & clamp.

[Phase 2: Wire R2 Security Modules]
  ├── 1. scp/security/url_safety.py & scp/llm_gateway/egress_policy.py -> Delegate to EgressPolicy.
  ├── 2. scp/security/autonomous_governor.py & scp/hands/hands_executor.py -> Wire SafeCommandRunnerTool.
  └── 3. scp/hands/hands_executor.py -> Wire AutonomousAuditLedger two-phase commit.

[Phase 3: Verify Chain-Break & Integrity]
  ├── 1. Create tests/T02_contract/test_critical_security_chain_break.py covering all 5 links.
  ├── 2. Run pytest tests/T02_contract/test_critical_security_chain_break.py -v.
  ├── 3. Run python tools/t00_meta_audit.py to verify test integrity.
  └── 4. Run grep -rn verification confirming all 3 unwired modules have production callers.
```

---

## 5. Summary Conclusion

Both R1 and R2 represent critical security gaps that must be remediated together. The R1 chain currently leaves the door wide open from the frontend down to the LLM verification layer. The R2 unwired modules represent excellent defensive implementations that simply need to be connected to the live execution path. Implementing the proposed wiring and severing the R1 chain will eliminate the "hardening trang trí" defect and achieve genuine Fail-Closed & Evidence-First operational security.
