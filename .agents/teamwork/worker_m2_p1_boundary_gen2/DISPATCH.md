# DISPATCH: worker_m2_p1_boundary_gen2

## Mandatory Instructions
MANDATORY: Read `D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md` before starting work.
MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Source of Truth
Read `D:\scp\.agents\teamwork\explorer_m1_3\handoff.md` Section 1.3 and Section 2.3 for exact line numbers and code implementations.

## Assigned Scope & Exclusive File Ownership
You exclusively own and may edit ONLY the following files:
1. `dashboard/src/app/api/scp/ask/route.ts` (and any route handler using extractCallerAuth)
2. `dashboard/src/middleware.ts`
3. `dashboard/src/lib/probe-allowlist.ts` (or equivalent allowlist in dashboard)
4. `mini-services/llm-bridge/core.ts` (and any related Bun LLM bridge auth files)
5. `scp/web_control/web_navigator.py` & `scp/web_control/browser_session.py` (for egress policy enforcement)

## Implementation Checklist
1. **Dashboard Pseudo-Auth in `extractCallerAuth`**:
   - In Next.js route handlers (`dashboard/src/app/api/scp/ask/route.ts` etc.):
     Remove pseudo-auth (which only checked if header string was non-empty).
     Enforce real cryptographic validation: check against `process.env.SCP_ADMIN_TOKEN` or verify JWT signature with `SCP_AUTH_TOKEN_SECRET`. If invalid or missing, reject with HTTP 401 Unauthorized.
2. **IP Spoofing in `dashboard/src/middleware.ts`**:
   - Do NOT unconditionally trust `X-Forwarded-For` or `X-Real-IP`.
   - Require a dedicated proxy secret header (`x-scp-proxy-secret`) before trusting forwarded headers.
   - For direct loopback requests (`127.0.0.1`, `::1`), allow them only without spoofed external headers.
   - In `probe-allowlist.ts`, remove broad RFC1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) from default allowlist; restrict default to localhost loopback only.
3. **Bun LLM Bridge Token Protection** (`mini-services/llm-bridge/core.ts`):
   - Secure the bridge endpoint: require `Authorization: Bearer <BRIDGE_SECRET>`.
   - Use `crypto.timingSafeEqual` with SHA-256 hashes to prevent timing attacks. Fail closed if `BRIDGE_SECRET` is unset in production.
4. **Egress Policy Enforcement**:
   - In `scp/web_control/web_navigator.py` and `scp/web_control/browser_session.py`:
     Enforce `enforce_egress_policy(url)` before any network connection or browser navigation.
     Resolve DNS and re-verify IP to prevent TOCTOU DNS rebinding bypasses.

## Verification
Run tests or static syntax checks on modified TypeScript/Python files.
Write `D:\scp\.agents\teamwork\worker_m2_p1_boundary_gen2\handoff.md` and report back to parent.
