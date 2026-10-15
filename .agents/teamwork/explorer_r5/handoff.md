# Comprehensive Security & Architecture Audit Report: Stream R5
**Target**: Dashboard Frontend (Next.js 16) & Bun Microservices (`llm-bridge`, `loop-scheduler`)  
**Auditor**: Explorer R5  
**Project Root**: `D:\scp`  
**Working Directory**: `D:\scp\.agents\teamwork\explorer_r5`  
**Date**: 2026-09-27  
**Mode**: Pure Read-Only Audit  

---

## Executive Summary

This report delivers a line-by-line security and architectural investigation of the Next.js Web Dashboard and Bun microservices in the SCP (Secure Control Plane) platform. Every finding is strictly grounded in direct source code evidence, the 26 SCP DNA principles, and Fail-Closed & Evidence-First invariants.

### Key Audit Highlights:
1. **Token Injection Resolution & New Pseudo-Auth Risk**: Historic auto-minting of admin JWTs (`createJwt`) in `/api/scp/ask/route.ts` was severed in commit `47a56a9b`. However, the replacement helper `extractCallerAuth` (`auth-helper.ts`) only checks for the *presence* of a non-empty token string or cookie without validating signature or authenticity. Local sensitive endpoints like `/api/scp/activity` rely on this helper as their sole gate, allowing complete bypass with `Authorization: Bearer <any_string>`.
2. **Client-Side Auth Disconnect**: Frontend UI components (`scp-overview.tsx`, `live-activity-stream.tsx`) transmit raw API calls without `Authorization` headers or cookies, meaning legitimate UI user interactions now fail with HTTP 401 Unauthorized errors out-of-the-box.
3. **Dashboard Middleware Spoofability**: When `SCP_DASHBOARD_PROXY_SECRET` is unset (the default configuration), `middleware.ts` allows any client supplying `X-Forwarded-For: 127.0.0.1` to bypass IP gating, while blocking legitimate local browsers that send no forwarding headers.
4. **SSRF Expansion & Unchecked Redirects**: `probe-allowlist.ts` explicitly whitelists all RFC1918 private IPv4 addresses (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), allowing server-side probes against internal cloud VPC resources. Furthermore, all 15 server-side `fetch()` calls in the dashboard use default `redirect: "follow"`, bypassing allowlist validation if the target issues an HTTP 302 redirect.
5. **Microservice Security Gaps**: `mini-services/llm-bridge/core.ts` uses non-constant-time string comparison (`===`) for token checks (timing attack vulnerability), lacks replay protection, and discloses upstream provider errors. `mini-services/loop-scheduler/index.ts` exposes full filesystem log paths and recent audit run details via unauthenticated `GET /` with `Access-Control-Allow-Origin: *`.

---

## Severity Summary Table

| Finding ID | Title | File Path & Lines | Severity | SCP DNA Principle |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-R5-01** | Token Presence Pseudo-Auth Bypass in `extractCallerAuth` & `activity` Route | `dashboard/src/lib/auth-helper.ts:13-36`<br>`dashboard/src/app/api/scp/activity/route.ts:23-32` | **HIGH** | DNA #22 (PASS ≠ TRUE)<br>DNA #5 (Ảo giác đồng thuận) |
| **SEC-R5-02** | Dashboard Middleware IP Spoofing via Injected `X-Forwarded-For` | `dashboard/src/middleware.ts:33-81` | **HIGH** | DNA #6 (Gốc tin cậy bên ngoài)<br>DNA #5 (Ảo giác đồng thuận) |
| **SEC-R5-03** | Frontend UI Components Detached From Authentication Credentials | `dashboard/src/components/dashboard/scp-overview.tsx:463,484-489`<br>`dashboard/src/components/dashboard/live-activity-stream.tsx:78,142` | **HIGH** | DNA #2 (Vòng lặp khép kín)<br>DNA #26 (Reality có quyền cuối cùng) |
| **SEC-R5-04** | Overly Permissive RFC1918 Private IP Allowlist in `probe-allowlist.ts` | `dashboard/src/lib/probe-allowlist.ts:49-57,98-100` | **HIGH** | DNA #16 (Học nói phạm vi)<br>DNA #7 (Autofix an toàn) |
| **SEC-R5-05** | Unrestricted HTTP Redirect Following in Server-Side `fetch()` Sinks | `dashboard/src/app/api/autofix/route.ts:67`<br>`dashboard/src/app/api/scanners/route.ts:45`<br>`dashboard/src/app/api/scp/status/route.ts:236` (15 sinks total) | **HIGH** | DNA #19 (Tầng kiểm toán bằng chứng)<br>DNA #22 (PASS ≠ TRUE) |
| **SEC-R5-06** | Timing Attack in `llm-bridge` Token Authentication | `mini-services/llm-bridge/core.ts:926-934` | **HIGH** | DNA #6 (Gốc tin cậy bên ngoài)<br>DNA #20 (Không kiểm tra vô hạn) |
| **SEC-R5-07** | Complete Absence of Replay Prevention on Microservice Token Endpoints | `mini-services/llm-bridge/core.ts:926-935`<br>`mini-services/loop-scheduler/index.ts:627-650` | **HIGH** | DNA #6 (Gốc tin cậy bên ngoài)<br>DNA #8 (KB accumulation) |
| **SEC-R5-08** | Unauthenticated Cross-Origin Filesystem Path & Audit Leak in `loop-scheduler` | `mini-services/loop-scheduler/index.ts:604-615,657-686` | **MEDIUM** | DNA #6 (Gốc tin cậy bên ngoài)<br>DNA #16 (Học nói phạm vi) |
| **SEC-R5-09** | Missing Authentication on Internal Status & Probe Endpoints | `dashboard/src/app/api/autofix/route.ts:56-88`<br>`dashboard/src/app/api/scanners/route.ts:35-61`<br>`dashboard/src/app/api/scp/status/route.ts:218-251`<br>`dashboard/src/app/api/scp/loop/route.ts:29-52`<br>`dashboard/src/app/api/scp/v3/hands/planner/status/route.ts:7-18` | **MEDIUM** | DNA #16 (Học nói phạm vi)<br>DNA #6 (Gốc tin cậy bên ngoài) |
| **SEC-R5-10** | Suppression of 401/403 Errors Returning False 200 OK | `dashboard/src/app/api/scp/v3/hands/status/route.ts:26-28`<br>`dashboard/src/app/api/scp/v3/pc/status/route.ts:22-24`<br>`dashboard/src/app/api/scp/v3/web/status/route.ts:22-24` | **MEDIUM** | DNA #22 (PASS ≠ TRUE)<br>DNA #26 (Reality có quyền cuối cùng) |
| **SEC-R5-11** | Internal Backend URL Disclosure in API Responses | `dashboard/src/app/api/autofix/route.ts:82,93`<br>`dashboard/src/app/api/scanners/route.ts:55,66` | **MEDIUM** | DNA #16 (Học nói phạm vi) |
| **SEC-R5-12** | Detailed Upstream Error Disclosure in `llm-bridge` | `mini-services/llm-bridge/core.ts:828,1007,1101,1219` | **MEDIUM** | DNA #16 (Học nói phạm vi) |
| **SEC-R5-13** | Lack of Role Segregation in `llm-bridge` (Inference vs Admin Cache Purge) | `mini-services/llm-bridge/core.ts:1191-1215` | **MEDIUM** | DNA #6 (Gốc tin cậy bên ngoài) |
| **SEC-R5-14** | Route Handlers Bypassing `scp-backend-url.ts` Single PEP Pattern | `dashboard/src/app/api/autofix/route.ts:31-32`<br>`dashboard/src/app/api/scanners/route.ts:21-22`<br>`dashboard/src/app/api/scp/status/route.ts:45-46`<br>`dashboard/src/app/api/scp/loop/route.ts:23-24`<br>`dashboard/src/app/api/scp/loop/trigger/route.ts:41-42` | **LOW** | DNA #5 (Ảo giác đồng thuận)<br>DNA #19 (Tầng kiểm toán bằng chứng) |
| **SEC-R5-15** | Plaintext HTTP Communication & Host Binding Risks in Microservices | `mini-services/llm-bridge/core.ts:1154-1157`<br>`mini-services/loop-scheduler/index.ts:854-857` | **LOW** | DNA #6 (Gốc tin cậy bên ngoài) |

---

## 1. Observations

### 1.1 Token Injection Audit in Next.js API Routes

#### A. Resolution of Historic JWT Auto-Minting
Direct examination of `dashboard/src/app/api/scp/ask/route.ts` confirms that the vulnerability noted in previous audits (lines 15-34 of earlier revisions auto-minting admin JWTs via `createJwt(process.env.SCP_JWT_SECRET)`) has been removed.
Commit `47a56a9b46` deleted `createJwt()` and `readAdminToken()`.

#### B. The Pseudo-Authentication Gate in `auth-helper.ts`
Inspection of `dashboard/src/lib/auth-helper.ts` reveals:
```typescript
7: export function extractCallerAuth(request: Request): {
8:   authenticated: boolean;
9:   authHeader: string;
10:   pcToken?: string;
11:   errorResponse?: NextResponse;
12: } {
13:   let authToken = "";
14:   const authHeader = request.headers.get("authorization") || request.headers.get("Authorization");
15:   if (authHeader && authHeader.trim()) {
16:     authToken = authHeader.trim();
17:   } else {
18:     const cookieHeader = request.headers.get("cookie");
19:     if (cookieHeader) {
20:       const match = cookieHeader.match(/(?:^|;\s*)(?:scp_token|session_token|token)=([^;]+)/);
21:       if (match && match[1]) {
22:         authToken = `Bearer ${decodeURIComponent(match[1].trim())}`;
23:       }
24:     }
25:   }
26: 
27:   if (!authToken) {
28:     return {
29:       authenticated: false,
30:       authHeader: "",
31:       errorResponse: NextResponse.json(
32:         { error: "Unauthorized: Missing authentication credentials" },
33:         { status: 401 }
34:       ),
35:     };
36:   }
...
44:   return {
45:     authenticated: true,
46:     authHeader: authHeaderToSend,
47:     pcToken,
48:   };
49: }
```
`extractCallerAuth` performs NO cryptographic verification or secret matching. It merely checks `if (!authToken)`.

Now, observe `dashboard/src/app/api/scp/activity/route.ts:23-32, 103-106, 140-169`:
```typescript
23: function requireAuth(request: Request): NextResponse | null {
24:   const auth = extractCallerAuth(request)
25:   if (!auth.authenticated || auth.errorResponse) {
26:     return (
27:       auth.errorResponse ||
28:       NextResponse.json({ error: "Unauthorized" }, { status: 401 })
29:     )
30:   }
31:   return null
32: }
...
103: export async function GET(request: Request) {
104:   const unauthorized = requireAuth(request)
105:   if (unauthorized) return unauthorized
...
140:   const serviceLogsDir = path.join(SCP_ROOT, "data", "service-logs")
141:   const schedulerLines = readRecentLogLines(path.join(serviceLogsDir, "scheduler.log"), 15)
...
154:   const desktopConsoleLines = readRecentLogLines(path.join(SCP_ROOT, "data", "desktop-logs", "desktop-console.log"), 15)
```
Unlike proxy routes that forward `authHeader` to FastAPI for backend verification, `activity/route.ts` is served entirely within Next.js. Any request bearing `Authorization: Bearer test` or cookie `token=x` satisfies `requireAuth()` and receives unredacted server logs.

#### C. Unauthenticated Next.js API Routes
Inspection across all 19 route files in `dashboard/src/app/api/` reveals that the following endpoints invoke backend services or expose internal metrics without verifying caller credentials:
- `dashboard/src/app/api/autofix/route.ts:56-88`: Calls `fetch("${SCP_BACKEND_URL}/v105/autofix/stats")`. No caller authentication.
- `dashboard/src/app/api/scanners/route.ts:35-61`: Calls `fetch("${SCP_BACKEND_URL}/v105/scanners")`. No caller authentication.
- `dashboard/src/app/api/scp/status/route.ts:218-251`: Calls `fetch("${SCP_BASE_URL}/health")` and performs file system inspections. No caller authentication.
- `dashboard/src/app/api/scp/loop/route.ts:29-52`: Calls `fetch("${SCHEDULER_URL}/")`. No caller authentication.
- `dashboard/src/app/api/scp/v3/hands/planner/status/route.ts:7-18`: Calls `fetch("${base}/v3/hands/planner/status")`. No caller authentication.

#### D. Status Route Error Suppression (False 200 OK)
In `dashboard/src/app/api/scp/v3/hands/status/route.ts:26-28`:
```typescript
26:     if (response.status === 403 || response.status === 401) {
27:       return NextResponse.json({ hands: "offline", planner: { planner: "offline" }, reason: "Chưa cấu hình token hoặc chưa kích hoạt" }, { status: 200 })
28:     }
```
Identical code patterns exist in `dashboard/src/app/api/scp/v3/pc/status/route.ts:22-24` and `dashboard/src/app/api/scp/v3/web/status/route.ts:22-24`. HTTP 401/403 responses from upstream services are suppressed and replaced with HTTP 200 OK.

#### E. IP Restriction Spoofing in `middleware.ts`
In `dashboard/src/middleware.ts:33-81`:
```typescript
33:     const proxySecret = process.env.SCP_DASHBOARD_PROXY_SECRET?.trim() ?? "";
34:     if (proxySecret) {
35:       const presented = request.headers.get("x-scp-proxy-secret") ?? "";
36:       if (presented !== proxySecret) {
37:         return NextResponse.json(..., { status: 403 });
38:       }
39:     }
...
49:     const forwardedHeader = request.headers.get("x-forwarded-for");
50:     const realIpHeader = request.headers.get("x-real-ip");
51: 
52:     const hops = forwardedHeader
53:       ? forwardedHeader.split(",").map((s) => s.trim()).filter(Boolean)
54:       : realIpHeader
55:       ? [realIpHeader.trim()]
56:       : [];
...
63:     if (hops.length === 0) {
64:       return NextResponse.json(
65:         { error: "Access denied. Missing IP headers; dashboard API is restricted to localhost." },
66:         { status: 403 }
67:       );
68:     }
...
73:     const lastHop = hops[hops.length - 1];
74:     const allLocal = hops.every((ip) => LOCAL_IPS.has(ip));
75: 
76:     if (!LOCAL_IPS.has(lastHop) || !allLocal) {
77:       return NextResponse.json(
78:         { error: "Access denied. Dashboard API is restricted to localhost." },
79:         { status: 403 }
80:       );
81:     }
```
When `SCP_DASHBOARD_PROXY_SECRET` is unset, an external client connecting directly to `:3000` with header `X-Forwarded-For: 127.0.0.1` produces `hops = ["127.0.0.1"]`, passes `LOCAL_IPS.has(lastHop)` and `allLocal`, and is granted access.
A legitimate browser client connecting to `http://localhost:3000` has `hops = []` and is blocked with 403.

#### F. Frontend UI Components Missing Auth Headers
In `dashboard/src/components/dashboard/scp-overview.tsx:484-489`:
```typescript
484:       const response = await fetch("/api/scp/ask", {
485:         method: "POST",
486:         headers: { "Content-Type": "application/json" },
487:         body: JSON.stringify({ question, domain: "general", session_id: ensureSessionId(), image_data: pendingImageRef.current }),
488:         cache: "no-store",
489:       })
```
No `Authorization` header is attached, and no authentication cookies are managed. The request fails with HTTP 401 when sent to `/api/scp/ask`.

---

### 1.2 Dashboard SSRF Vectors & Probe Allowlist

#### A. RFC1918 Private Range Whitelisting in `probe-allowlist.ts`
In `dashboard/src/lib/probe-allowlist.ts:49-57, 98-100`:
```typescript
49: function isPrivateIPv4(host: string): boolean {
50:   const v4 = parseIPv4(host)
51:   if (!v4) return false
52:   const [a, b] = v4
53:   if (a === 10) return true // 10.0.0.0/8
54:   if (a === 172 && b >= 16 && b <= 31) return true // 172.16.0.0/12
55:   if (a === 192 && b === 168) return true // 192.168.0.0/16
56:   return false
57: }
...
98:   if (isPrivateIPv4(host)) {
99:     return { allowed: true, reason: "private range (RFC1918)" }
100:  }
```
Any target URL with an RFC1918 IPv4 address is deemed valid.

#### B. Absence of Redirect Restraints on Server-Side `fetch()`
Across all 15 server-side `fetch()` call sites in `dashboard/src/app/api/`:
- `autofix/route.ts:67`
- `scanners/route.ts:45`
- `scp/status/route.ts:236`
- `scp/health/route.ts:84`
- `scp/loop/route.ts:35`
- `scp/loop/trigger/route.ts:86`
- `scp/ask/route.ts:71`
- `scp/call/session/route.ts:16`
- `scp/voice/route.ts:22`
- `scp/v3/hands/planner/status/route.ts:13`
- `scp/v3/hands/status/route.ts:21`
- `scp/v3/pc/status/route.ts:21`
- `scp/v3/web/status/route.ts:21`
- `scp/v3/web/search/route.ts:29`
- `scp/v3/trace/[trace_id]/route.ts:28`

None specify `redirect: "manual"` or `redirect: "error"`. The runtime environment (Node.js/Bun) follows HTTP 301/302 redirects automatically without re-invoking `isAllowedProbeTarget`.

#### C. Backend URL Disclosure
In `dashboard/src/app/api/autofix/route.ts:82, 93`:
```typescript
82:         backendUrl: `${SCP_BACKEND_URL}/v105/autofix/stats`,
...
93:     backendUrl: `${SCP_BACKEND_URL}/v105/autofix/stats`,
```
And `dashboard/src/app/api/scanners/route.ts:55, 66`:
```typescript
55:         backendUrl: `${SCP_BACKEND_URL}/v105/scanners`,
...
66:     backendUrl: `${SCP_BACKEND_URL}/v105/scanners`,
```
The internal backend URL is exposed directly in JSON responses.

#### D. Bypassing `scp-backend-url.ts`
Five route handlers (`autofix`, `scanners`, `status`, `loop`, `loop/trigger`) construct URLs using module-level constants derived directly from `process.env.SCP_INTERNAL_URL` or `process.env.LOOP_SCHEDULER_URL`, bypassing the centralized `resolveScpApiBase()` and `resolveHealthProbeTargets()` helpers in `dashboard/src/lib/scp-backend-url.ts`.

---

### 1.3 Bun Microservices Security

#### A. Non-Constant-Time Token Comparison in `llm-bridge`
In `mini-services/llm-bridge/core.ts:926-934`:
```typescript
926: function isAuthorized(req: Request): boolean {
927:   const auth = req.headers.get("authorization");
928:   const shared = process.env.SHARED_SECRET;
929:   const bearer = process.env.BEARER_TOKEN;
930:   return !!auth && (
931:     (shared && auth === `Bearer ${shared}`) ||
932:     (bearer && auth === `Bearer ${bearer}`)
933:   );
934: }
```
String comparison is performed using standard equality `===`, exposing the service to timing side-channel analysis. In contrast, `mini-services/loop-scheduler/index.ts:618-625` uses `constantTimeTokenEquals`.

#### B. Absence of Replay Prevention
Token authentication in `mini-services/llm-bridge/core.ts:926-935` and `mini-services/loop-scheduler/index.ts:627-650` accepts static Bearer tokens or static `X-SCP-Admin-Token` headers. There are no timestamps, nonces, or signature verification.

#### C. Unauthenticated System Disclosure via CORS `*` in `loop-scheduler`
In `mini-services/loop-scheduler/index.ts:604-615, 658-686`:
```typescript
604: function jsonResponse(data: unknown, status = 200): Response {
605:   return new Response(JSON.stringify(data, null, 2), {
606:     status,
607:     headers: {
608:       "Content-Type": "application/json",
609:       "Cache-Control": "no-store",
610:       "Access-Control-Allow-Origin": "*",
611:       "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
612:       "Access-Control-Allow-Headers": "Content-Type, Authorization",
613:     },
614:   });
615: }
...
658:   if (method === "GET" && (path === "/" || path === "")) {
...
679:       log_path: LOOP_LOG_PATH,
680:       state_path: LOOP_STATE_PATH,
...
684:       recent_runs: state.recent_runs,
685:     });
686:   }
```
GET `/` requires no authorization and responds with `"Access-Control-Allow-Origin": "*"`. It leaks `LOOP_LOG_PATH`, `LOOP_STATE_PATH`, `SCP_BASE_URL`, and full details of the 10 most recent audit runs.

#### D. Error Disclosure in `llm-bridge`
In `mini-services/llm-bridge/core.ts:828, 1007, 1101, 1219`:
Raw errors from upstream providers are string-interpolated and returned to callers:
```typescript
828:           throw new Error(`OpenRouter API ${response.status}: ${errText.slice(0, 200)}`);
...
1007:     return ollamaError(502, `z-ai-web-dev-sdk error: ${err?.message ?? String(err)}`);
...
1219:       return ollamaError(500, `internal error: ${err?.message ?? String(err)}`);
```

#### E. Startup Script Omissions
In `start-scp.bat:84-101` and `start-scp.sh:66-118`:
- `llm-bridge` is launched without setting `SHARED_SECRET` or `BEARER_TOKEN`.
- `loop-scheduler` is launched without setting `SCP_SCHEDULER_ADMIN_TOKEN`.
- `dashboard` is launched without setting `SCP_DASHBOARD_PROXY_SECRET`.

---

## 2. Logic Chain

### 2.1 From Observation 1.1.B to Conclusion SEC-R5-01
1. **Observation**: `extractCallerAuth()` (lines 15-36 of `auth-helper.ts`) checks only if `authToken` is non-empty. If present, it returns `{ authenticated: true, authHeader: authHeaderToSend }`.
2. **Observation**: `activity/route.ts` (lines 23-32) guards access to local logs (`scheduler.log`, `desktop-console.log`, `loop_runs.jsonl`) solely using `requireAuth()`, which calls `extractCallerAuth()`.
3. **Deduction**: Because `activity/route.ts` does not forward the request to an authenticating upstream service and performs no signature/secret check of its own, any caller passing `Authorization: Bearer dummy` or `Cookie: token=dummy` causes `extractCallerAuth` to declare `authenticated: true`.
4. **Conclusion**: An attacker can access sensitive internal service logs without holding valid system credentials. This represents a pseudo-authentication vulnerability (violating DNA #22 PASS ≠ TRUE and DNA #5).

### 2.2 From Observation 1.1.E to Conclusion SEC-R5-02
1. **Observation**: In `middleware.ts:33-81`, when `process.env.SCP_DASHBOARD_PROXY_SECRET` is unset, access control is derived entirely from `X-Forwarded-For` and `X-Real-IP`.
2. **Observation**: If an untrusted caller connects directly to port 3000 and supplies `X-Forwarded-For: 127.0.0.1`, `hops` evaluates to `["127.0.0.1"]`, which matches `LOCAL_IPS`.
3. **Deduction**: Any direct network caller can forge loopback client headers, bypassing the IP restriction entirely.
4. **Observation**: When a legitimate local browser requests `http://localhost:3000/api/...`, the browser sets neither `X-Forwarded-For` nor `X-Real-IP`. `hops` evaluates to `[]`.
5. **Deduction**: The middleware rejects legitimate local browser users with HTTP 403 while admitting attackers who forge the header.
6. **Conclusion**: The middleware IP gate fails open to spoofed headers while failing closed against legitimate local clients (violating DNA #6 and DNA #5).

### 2.3 From Observation 1.2.A & 1.2.B to Conclusions SEC-R5-04 and SEC-R5-05
1. **Observation**: `isPrivateIPv4()` in `probe-allowlist.ts` permits all RFC1918 private IPv4 addresses (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
2. **Observation**: Cloud VPC environments place databases, cache instances, and internal microservices on RFC1918 subnets.
3. **Deduction**: An operator configuring a dashboard endpoint or an attacker who influences base URLs can cause the dashboard server to probe arbitrary internal services across the private cloud subnet.
4. **Observation**: None of the 15 server-side `fetch()` calls configure `redirect: "manual"` or `redirect: "error"`.
5. **Deduction**: If an allowable target endpoint responds with an HTTP 302 redirect pointing to `http://169.254.169.254/` (cloud metadata), the runtime's HTTP client automatically follows the redirect without re-validating the destination against `isAllowedProbeTarget`.
6. **Conclusion**: The dashboard's server-side fetch architecture contains SSRF pivoting risks (violating DNA #19 and DNA #22).

### 2.4 From Observation 1.3.A & 1.3.C to Conclusions SEC-R5-06 and SEC-R5-08
1. **Observation**: `isAuthorized()` in `llm-bridge/core.ts` compares the Authorization header against `SHARED_SECRET` using `===`.
2. **Deduction**: Variable-time string comparison permits byte-by-byte timing attacks against the shared secret over network connections.
3. **Observation**: `loop-scheduler/index.ts` exposes `GET /` with `Access-Control-Allow-Origin: *` and no auth gate, disclosing `LOOP_LOG_PATH`, `LOOP_STATE_PATH`, and run history.
4. **Deduction**: Any malicious site rendered in a browser on the same host can query `http://127.0.0.1:3030/` via JavaScript and read internal file paths and audit statistics.
5. **Conclusion**: Microservices leak internal state and enforce credentials with insufficient cryptographic safeguards (violating DNA #6 and DNA #16).

---

## 3. Caveats

1. **Localhost Binding Assumption**: Both microservices default to `127.0.0.1`. In single-host local developer environments, network-based timing attacks or external spoofing are mitigated if the ports are not exposed on external interfaces (`0.0.0.0`). However, containerized deployments (Docker/Podman/Kubernetes) often expose ports across container network bridges where these vectors become active.
2. **Upstream FastAPI Defense-in-Depth**: Proxy routes (`/api/scp/ask`, `/api/scp/call/session`, `/api/scp/voice`, `/api/scp/v3/trace/[trace_id]`) forward the caller's `authHeader` to the FastAPI backend. Although `extractCallerAuth()` does not validate the token locally, the Python backend validates the token via `verify_admin` or `verify_jwt_token`. The vulnerability in `extractCallerAuth` is strictly critical for routes handled locally within Next.js (like `/api/scp/activity`).
3. **No Dynamic Code Modification**: In accordance with the mandatory read-only invariant, no changes were applied to source files or configurations during this audit.

---

## 4. Conclusion

1. **Unsolicited Token Injection Severed**: The historic auto-minting of admin tokens in Next.js API routes has been successfully eliminated. Routes no longer inject `process.env.SCP_ADMIN_TOKEN` or mint admin JWTs.
2. **Authentication Gate Inadequacy**: The current authentication architecture in the dashboard relies on token *presence* rather than token *validity*. This creates an illusion of security on local routes (`/api/scp/activity`) while breaking the frontend UI, which was not updated to send credentials.
3. **SSRF and Egress Boundaries Incomplete**: The dashboard probe allowlist is overly broad with respect to RFC1918 subnets, and server-side fetch calls do not disable automatic redirect following.
4. **Microservices Hardening Deficits**: Both Bun microservices require cryptographic hardening: constant-time token comparison, replay prevention (nonces/signatures), CORS origin restriction, and sanitization of upstream error traces.

---

## 5. Verification Method

To independently reproduce and verify every finding in this report without modifying the codebase:

### 5.1 Verifying Pseudo-Auth Bypass in `/api/scp/activity` (SEC-R5-01)
Execute the following command using Bun:
```bash
bun -e "
import { GET } from './dashboard/src/app/api/scp/activity/route.ts';
const req = new Request('http://localhost:3000/api/scp/activity', {
  headers: { 'Authorization': 'Bearer arbitrary_invalid_token_12345' }
});
const res = await GET(req);
const data = await res.json();
console.log('Status:', res.status, 'Success:', data.success, 'Events count:', data.events?.length);
"
```
**Expected Verification Result**: Returns HTTP 200 and dumps service logs, proving that any non-empty bearer token bypasses authentication.

### 5.2 Verifying IP Gate Spoofing in `middleware.ts` (SEC-R5-02)
Run the following verification probe:
```bash
bun -e "
const { middleware } = await import('./dashboard/src/middleware.ts');
const { NextRequest } = await import('next/server');
delete process.env.SCP_DASHBOARD_PROXY_SECRET;

// 1. Spoofed XFF
const spoofedReq = new NextRequest('http://127.0.0.1:3000/api/scp/status', {
  headers: { 'x-forwarded-for': '127.0.0.1' }
});
console.log('Spoofed XFF status:', middleware(spoofedReq).status);

// 2. Direct browser request without hop headers
const directReq = new NextRequest('http://127.0.0.1:3000/api/scp/status', { headers: {} });
console.log('Direct browser status:', middleware(directReq).status);
"
```
**Expected Verification Result**: `Spoofed XFF status` returns 200 (allowed), while `Direct browser status` returns 403 (blocked).

### 5.3 Verifying Non-Constant-Time Check in `llm-bridge` (SEC-R5-06)
Inspect `mini-services/llm-bridge/core.ts:930-933`:
```bash
git grep -n "auth === \`Bearer" mini-services/llm-bridge/
```
Compare with `mini-services/loop-scheduler/index.ts:618-625` to confirm `constantTimeTokenEquals` is absent in `llm-bridge`.

### 5.4 Verifying Cross-Origin Information Leak in `loop-scheduler` (SEC-R5-08)
Inspect `mini-services/loop-scheduler/index.ts:604-615, 658-686`:
Verify that `jsonResponse` sets `"Access-Control-Allow-Origin": "*"` on `GET /`, which serializes `LOOP_LOG_PATH` and `state.recent_runs` without requiring `Authorization`.

### 5.5 Invalidation Conditions
These findings shall be considered resolved only when:
1. `auth-helper.ts` validates token cryptographic signatures or compares them against `SCP_ADMIN_TOKEN` / `SCP_JWT_SECRET`.
2. `middleware.ts` rejects unauthenticated external requests without relying on client-supplied `X-Forwarded-For`.
3. All dashboard server-side `fetch()` calls specify `redirect: "error"`.
4. `probe-allowlist.ts` restricts allowed target hosts to an explicit allowlist rather than broad RFC1918 blocks.
5. Microservices employ constant-time comparison, request timestamps/nonces, and restrict CORS headers.
