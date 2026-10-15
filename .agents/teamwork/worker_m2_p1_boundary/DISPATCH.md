# DISPATCH: worker_m2_p1_boundary

## 2026-09-27T08:39:34Z
MANDATORY: Read D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md and D:\scp\.agents\teamwork\worker_m2_p1_boundary\DISPATCH.md before starting work.
Read D:\scp\.agents\teamwork\explorer_m1_3\handoff.md Section 1.3 and Section 2.3 for exact line numbers and code implementations for P1 boundary issues.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You own and may edit ONLY:
1. dashboard/src/app/api/scp/ask/route.ts (and any route handler using extractCallerAuth)
2. dashboard/src/middleware.ts
3. dashboard/src/lib/probe-allowlist.ts
4. mini-services/llm-bridge/core.ts
5. scp/web_control/web_navigator.py and scp/web_control/browser_session.py

Implement the P1 boundary fixes:
1. Dashboard pseudo-auth removal in extractCallerAuth (real token check, reject unauthenticated with 401).
2. Middleware IP spoofing prevention in dashboard/src/middleware.ts (require proxy secret for X-Forwarded-For, allow genuine loopback, tighten probe-allowlist).
3. Bun LLM bridge token protection in mini-services/llm-bridge/core.ts (timing-safe Bearer secret check, fail-closed).
4. Egress policy enforcement in web_navigator.py and browser_session.py (enforce_egress_policy before navigation, DNS resolution check to prevent TOCTOU rebinding).

Verify all changes syntactically and logically.
Write your completion report to D:\scp\.agents\teamwork\worker_m2_p1_boundary\handoff.md.
Update progress.md in your directory as you work. When done, call send_message to report completion.
