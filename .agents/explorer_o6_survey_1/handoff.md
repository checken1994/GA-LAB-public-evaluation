# Handoff Report: Technical Survey for R1 (Critical Security Chain) & R2 (Runtime Wiring)

**Agent:** explorer_o6_survey_1  
**Target:** orchestrator_6 (ID: `d743754f-8fbb-42e5-ae1d-08ee4bb86635`)  
**Type:** Hard Handoff  
**Working Directory:** `D:\scp\.agents\explorer_o6_survey_1`  
**Artifact Reference:** `D:\scp\.agents\explorer_o6_survey_1\survey_report.md`  

---

## 1. Observation

### R1: Critical Security Chain
1. **Dashboard Middleware Fail-Open (`dashboard/src/middleware.ts:6-7`):**
   ```typescript
   const clientIp = request.headers.get("x-forwarded-for") || request.headers.get("x-real-ip") || "127.0.0.1";
   const isLocal = clientIp.includes("127.0.0.1") || clientIp.includes("::1") || clientIp.includes("localhost");
   if (!isLocal && request.nextUrl.pathname.startsWith("/api/scp/")) {
       return NextResponse.json({ error: "Access denied..." }, { status: 403 });
   }
   ```
   Directly observed: If no proxy headers are present, `clientIp` defaults to `"127.0.0.1"`, evaluating `isLocal` to `true`. Substring matching also allows spoofing via `X-Forwarded-For: 127.0.0.1`.

2. **Dashboard JWT Admin Auto-Minting (`dashboard/src/app/api/scp/ask/route.ts:15-35, 60-70`):**
   *(Note: Prompt cited `dashboard/src/app/ask/route.ts`; actual path is `dashboard/src/app/api/scp/ask/route.ts`)*
   ```typescript
   function createJwt(secret: string): string {
     const h = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url")
     const p = Buffer.from(JSON.stringify({ sub: "admin", exp: Math.floor(Date.now() / 1000) + 3600 })).toString("base64url")
     const sig = createHmac("sha256", secret).update(`${h}.${p}`).digest("base64url")
     return `${h}.${p}.${sig}`
   }
   ```
   Directly observed: `POST` receives unauthenticated client requests, creates an admin JWT with `sub: "admin"` using `SCP_JWT_SECRET`, and sends it with `Authorization: Bearer ${token}` to `${base}/ask`.

3. **Chatbot Lane Governance KILL Override to ALLOW (`scp/api_server_parts/_ask_impl.py` & `scp/api/chat.py`):**
   *(Note: Prompt cited `scp/api/_ask_impl.py`; actual file is `scp/api_server_parts/_ask_impl.py`)*
   - `_ask_impl.py:548-549`:
     ```python
     _is_true_security_threat = (
         (_gov_decision == 'KILL' and not _is_chatbot_lane)
     ```
   - `_ask_impl.py:645-648`:
     ```python
     if v.verdict in ('FAIL', 'UNKNOWN'):
         v.verdict = 'PASS'
     if _gov_decision == 'KILL' or not _gov_decision:
         _gov_decision = 'ALLOW'
     ```
   - `chat.py:497-502`:
     ```python
     elif _is_chatbot_lane:
         _abstain = False
         _ws_answer = v.final_answer or _candidate_answer or "(Không có câu trả lời)"
         if v.verdict in ("UNKNOWN", "FAIL"):
             v.verdict = "PASS"
     ```
   Directly observed: Governance KILL decisions are excluded from security threat handling and flipped to `ALLOW` with `PASS` verdict whenever a query is routed to `LANE_CHATBOT`.

4. **JWT Guard Accepting Static Keys as Admin (`scp/security/jwt_guard.py:37-43`):**
   ```python
   for env_key in ("SCP_API_KEY", "SCP_ADMIN_KEY", "SCP_AUTH_TOKEN_SECRET"):
       expected = os.environ.get(env_key, "").strip()
       if expected and _secrets.compare_digest(token.encode("utf-8"), expected.encode("utf-8")):
           return {"sub": "admin", "role": "admin", "auth_type": "api_key"}
   ```
   Directly observed: Static keys supplied as Bearer tokens in `verify_jwt_token` bypass JWT signature/expiration checks and are granted blanket `role: "admin"`.

5. **Evaluation API Default PASS & Unvalidated Confidence (`scp/api/routes/evaluation_routes.py`):**
   - Lines 86-88: `STATE TO EVALUATE:\n\"\"\"\n{state[:20000]}\n\"\"\"` allows delimiter escaping.
   - Lines 211-212: `verdict = "PASS" if is_safe else "FAIL"`; `confidence = 0.85 if is_safe else 0.0`. On LLM timeout/error, fails open to `PASS` with `0.85`.
   - Lines 226-233: `verdict = str(parsed["verdict"]).upper()` is unvalidated against allowlist; `confidence = float(parsed["confidence"])` is unclamped.

### R2: Runtime Wiring of Unwired Security Modules
1. **`scp/capabilities/tools.py`:**
   - Ripgrep: `grep -rn "capabilities.tools"` returns exactly 2 hits: `tests/T03_capability/test_autonomous_tool_contracts.py:10` and `tools/adversarial_goal3_probe.py:26`. Zero production callers.
   - Current caller in `scp/hands/planner.py:486-495` delegates to `AutonomousCapabilityGovernor` (`scp/security/autonomous_governor.py`) with 4 crude regexes, and `HandsExecutor` executes via raw `powershell.exe` in `PCController`.
2. **`scp/policy/egress.py`:**
   - Ripgrep: `grep -rn "policy.egress"` returns exactly 3 hits: `capabilities/tools.py:18`, `adversarial_goal3_probe.py:32`, `test_egress_policy_unified.py:6`. Zero production callers.
   - Production runtime instead calls `scp/security/url_safety.py` (20+ call sites) and `scp/llm_gateway/egress_policy.py`, both of which default open in dev.
3. **`scp/core/autonomous_ledger.py`:**
   - Ripgrep: `grep -rn "AutonomousAuditLedger"` returns exactly 2 hits: `test_autonomous_audit_ledger_provenance.py:9` and `adversarial_goal3_probe.py:31`. Zero production callers.
   - Uses bare SHA-256 (`hashlib.sha256`) rather than keyed HMAC.
   - Production runtime `HandsExecutor` (`scp/hands/hands_executor.py:62-65`) directly appends raw un-hashed JSON lines to `data/hands/audit.jsonl`.

---

## 2. Logic Chain

1. **R1 Exploit Chain Assembly:**
   - Observation 1 (Middleware default to 127.0.0.1) allows an external attacker to access `/api/scp/ask`.
   - Observation 2 (Ask route auto-minting) mints an admin JWT with `sub: "admin"` for this unauthenticated caller.
   - Observation 4 (JWT guard static key acceptance) permits bypass of token constraints.
   - Observation 3 (Chatbot lane KILL override) neuters governance, converting any `KILL` safety verdict to `ALLOW` and forced `PASS`.
   - Observation 5 (Evaluation API default PASS) guarantees that even external evaluators fail open.
   - *Deduction:* The 4 vulnerabilities constitute an end-to-end exploit chain allowing unauthenticated remote command execution under an admin identity with safety shut off.

2. **R2 Decorative Hardening ("Hardening Trang Trí"):**
   - Observations 6, 7, 8 demonstrate that unit tests and the adversarial probe (`adversarial_goal3_probe.py`) instantiate the modules directly and pass cleanly.
   - However, the actual application runtime path (`HandsPlanner` -> `HandsExecutor` -> `PCController`, `url_safety.py`, and `data/hands/audit.jsonl`) runs entirely separate, unhardened code paths.
   - *Deduction:* The system gives an illusion of security in isolated tests while running vulnerable logic in production.

3. **HMAC vs Bare SHA-256 in Provenance Ledger:**
   - Observation 8 shows `AutonomousAuditLedger` uses bare `sha256:`.
   - A bare hash chain detects unintentional bit rot, but provides zero tamper-proofing against a local adversary or rogue subagent who can modify `data/trace_ledger.jsonl` and recompute valid SHA-256 hashes.
   - *Deduction:* HMAC-SHA256 with a kernel-held key (`SCP_LEDGER_HMAC_SECRET`) is mandatory to guarantee non-repudiation and cryptographic authenticity.

---

## 3. Caveats

1. **Path Discrepancies:** The user prompt cited `dashboard/src/app/ask/route.ts` and `scp/api/_ask_impl.py`. The actual filesystem paths in the repository are `dashboard/src/app/api/scp/ask/route.ts` and `scp/api_server_parts/_ask_impl.py`. (A stale copy `prev_ask_impl.py` also exists at repo root and should be purged).
2. **Meta-Audit Baseline State:** Running `python tools/t00_meta_audit.py` revealed 2 existing failures in `tests/internal/external_audit/test_security.py` due to `pytest.skip()` calls. Implementers must not add new skips or modify test baselines unapproved.
3. **Scope Discipline:** As an explorer agent, no production or test files were altered during this survey.

---

## 4. Conclusion

1. **R1 Must Be Severed at Every Link:**
   - `dashboard/src/middleware.ts`: Eliminate `"127.0.0.1"` fallback; fail closed on non-loopback IPs.
   - `dashboard/src/app/api/scp/ask/route.ts`: Remove `createJwt()` auto-minting; require caller authentication.
   - `scp/api_server_parts/_ask_impl.py` & `scp/api/chat.py`: Remove lines overriding `KILL` to `ALLOW` and forcing `PASS`.
   - `scp/security/jwt_guard.py`: Disallow static keys in `verify_jwt_token`.
   - `scp/api/routes/evaluation_routes.py`: Default to `UNKNOWN`/`0.0` on gateway error; clamp confidence to `[0.0, 1.0]`; validate verdicts.
2. **R2 Must Be Wired into Production Runtime:**
   - Bridge `scp/security/url_safety.py` and `scp/llm_gateway/egress_policy.py` to delegate directly to `scp.policy.egress.EgressPolicy`.
   - Bridge `scp/security/autonomous_governor.py` and `scp/hands/hands_executor.py` to use `SafeCommandRunnerTool`, `WorkspaceAnalysisTool`, and `SystemInspectionTool`.
   - Bridge `scp/hands/hands_executor.py` to record two-phase cryptographic provenance via `AutonomousAuditLedger` with HMAC.
3. **Integration Test Suite Required:** Implement `tests/T02_contract/test_critical_security_chain_break.py` verifying each broken link under adversarial conditions.

---

## 5. Verification Method

To independently verify all findings:
1. **Grep Callers Verification:**
   ```powershell
   grep -rn "from scp.capabilities.tools import" scp/
   grep -rn "from scp.policy.egress import" scp/
   grep -rn "from scp.core.autonomous_ledger import" scp/
   ```
   Confirm all return 0 results (proving unwired status).
2. **Inspect Vulnerable Lines:**
   ```powershell
   # Middleware fail-open
   Get-Content dashboard/src/middleware.ts -TotalCount 15
   # Auto-minting
   Get-Content dashboard/src/app/api/scp/ask/route.ts | Select-String -Pattern "createJwt" -Context 2,5
   # Governance KILL override
   Get-Content scp/api_server_parts/_ask_impl.py | Select-String -Pattern "_gov_decision = 'ALLOW'" -Context 3,3
   # JWT static key
   Get-Content scp/security/jwt_guard.py | Select-String -Pattern "SCP_ADMIN_KEY" -Context 2,5
   # Eval API default PASS
   Get-Content scp/api/routes/evaluation_routes.py | Select-String -Pattern "verdict = \"PASS\" if is_safe" -Context 2,4
   ```
3. **Collection Check:**
   ```powershell
   pytest tests/ --collect-only -q
   ```
   Confirms 2,127 tests collected cleanly in ~2.8s.
