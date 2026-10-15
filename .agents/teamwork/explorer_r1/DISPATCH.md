# Stream R1 Dispatch — Security Boundaries, Authentication & Secret Handling

## Target Working Directory
`D:\scp\.agents\teamwork\explorer_r1`

## Project Root & Request Reference
- Project Root: `D:\scp`
- Authoritative Request: `D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md`

## Mission
Conduct a meticulous, line-by-line, read-only security audit of Stream R1 in the SCP codebase.
Ground every finding in the 26 SCP DNA principles and strict Fail-Closed & Evidence-First invariants.

## Specific Areas of Investigation
1. **Auth Headers & JWT Validation**:
   - Inspect `scp/security/jwt_guard.py`, `dashboard/src/middleware.ts`, `dashboard/src/app/ask/route.ts`, and any API auth modules.
   - Verify whether `verify_jwt_token` accepts static admin keys as valid JWT tokens or if static keys bypass signature verification.
   - Check if the dashboard middleware or ask route auto-mints an admin JWT token when the client request is unauthenticated.
2. **API Key Role Segregation**:
   - Verify how `admin` vs `user` roles are enforced across FastAPI routes and background endpoints.
3. **Next.js Dashboard Middleware & IP Verification**:
   - Inspect IP extraction in `dashboard/src/middleware.ts`.
   - Check susceptibility to IP spoofing via `X-Forwarded-For`, `X-Real-IP`, or client-controlled headers.
4. **SSRF & Egress Enforcement**:
   - Review `scp/policy/egress.py`, `scp/security/url_safety.py`, `scp/llm_gateway/egress_policy.py`, and BrowserSession outbound calls.
   - Check for DNS rebinding vulnerabilities, dev-default open states, or bypasses for internal IPs (127.0.0.1, 169.254.169.254, RFC1918).
5. **Execution Boundaries & SafeCommandRunner**:
   - Inspect `scp/capabilities/command_runner.py` (or `SafeCommandRunnerTool`, `cmd.run`) and `scp/security/human_confirmation.py` (`HumanConfirmationStore`).
   - Verify whether risk level >= 3 commands are strictly blocked without human confirmation.
6. **Secret Leakage & Redaction**:
   - Inspect `scp/observability/trace_contract.py` (`redact_attributes()`), `trace_store.py`, `_trace_impl.py`.
   - Inspect `scp/chat/memory.py` / `ChatMemoryStore`, logging formatters, and exception handlers.
   - Verify if regex patterns cover JWTs (`ey...`), GitHub PATs (`ghp_...`), AWS keys (`AKIA...`), and generic bearer tokens.

## Output Requirements
Write `D:\scp\.agents\teamwork\explorer_r1\handoff.md` containing:
- Complete list of findings with:
  * `file_path` (exact path relative to D:\scp)
  * `line_number(s)` (exact lines)
  * `code snippet` (verbatim from codebase)
  * `severity` (CRITICAL, HIGH, MEDIUM, LOW, INFO)
  * `concrete risk / exploit scenario`
  * `SCP DNA principle citation`
- Summary table of findings by severity.
- Clear conclusion on security posture for R1.

## Invariant
PURE READ-ONLY. DO NOT modify or create any source code or test files.
