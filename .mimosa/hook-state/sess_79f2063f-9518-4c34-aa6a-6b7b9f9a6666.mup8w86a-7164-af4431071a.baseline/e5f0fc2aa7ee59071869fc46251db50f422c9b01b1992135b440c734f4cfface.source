import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const LOCAL_IPS = new Set(["127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"]);

// Trusted-proxy shared secret (injected by the reverse proxy, see
// deploy/vps/Caddyfile.dashboard.example). Next 16 no longer exposes the
// socket peer as request.ip, so when :3000 is directly reachable the
// XFF-based restriction below rests on headers a direct client can spoof.
//
// [AUDIT-FIX SEC-01 2026-09-28] Fail-closed contract (replaces the old
// fail-open "XFF-only + warn" default):
// - WHEN SCP_DASHBOARD_PROXY_SECRET is set: every gated dashboard API request
//   must carry `x-scp-proxy-secret` matching it (403 on missing/mismatch) —
//   only the proxy holding the secret can reach the dashboard API. The XFF
//   localhost validation still runs afterwards (defense in depth).
// - WHEN the env is unset AND SCP_DEV_MODE=1 (explicit local-dev flag): the
//   historical XFF-only fallback is preserved and a single warning is logged.
// - WHEN the env is unset WITHOUT SCP_DEV_MODE (production): the gated API is
//   DISABLED — every gated route answers 503 with setup instructions instead
//   of trusting spoofable X-Forwarded-For/X-Real-IP headers.
//
// SCP_DEV_MODE is read per-request (same pattern as the proxy secret below)
// so a process-level flag flip is always honored and runtime harnesses can
// exercise both branches in one evaluation context.
let proxySecretWarningLogged = false;

// [AUDIT-FIX low-9] Trước đây chỉ /api/scp/* nằm trong gate; /api/audit,
// /api/autofix, /api/scanners lộ ngoài IP/secret gate (vd /api/autofix
// trả về internal backendUrl). Tất cả route groups của dashboard API nay
// cùng một gate fail-closed.
const GATED_API_ROOTS = ["/api/scp", "/api/audit", "/api/autofix", "/api/scanners"];

function isGatedApiPath(pathname: string): boolean {
  return GATED_API_ROOTS.some(
    (root) => pathname === root || pathname.startsWith(`${root}/`)
  );
}

function extractHopHeaders(request: NextRequest): string[] {
  const forwardedHeader = request.headers.get("x-forwarded-for");
  const realIpHeader = request.headers.get("x-real-ip");
  return forwardedHeader
    ? forwardedHeader.split(",").map((s) => s.trim()).filter(Boolean)
    : realIpHeader
    ? [realIpHeader.trim()]
    : [];
}

export function middleware(request: NextRequest) {
  if (!isGatedApiPath(request.nextUrl.pathname)) {
    return NextResponse.next();
  }

  const proxySecret = process.env.SCP_DASHBOARD_PROXY_SECRET?.trim() ?? "";
  const presentedSecret = request.headers.get("x-scp-proxy-secret")?.trim() ?? "";

  if (proxySecret) {
    if (presentedSecret !== proxySecret) {
      return NextResponse.json(
        { error: "Access denied. Missing or invalid proxy secret; dashboard API is restricted to the trusted reverse proxy." },
        { status: 403 }
      );
    }
  } else if (process.env.SCP_DEV_MODE?.trim() === "1") {
    // Explicit local-dev fallback: keep the convenient XFF-only behavior and
    // warn once so operators notice this mode must never run in production.
    if (!proxySecretWarningLogged) {
      proxySecretWarningLogged = true;
      console.warn(
        "[scp-dashboard] SCP_DEV_MODE=1 with SCP_DASHBOARD_PROXY_SECRET unset: dashboard API access control (/api/scp/*, /api/audit, /api/autofix, /api/scanners) falls back to X-Forwarded-For/X-Real-IP headers only, which a direct client can spoof. This fallback exists for local development only. Production must set SCP_DASHBOARD_PROXY_SECRET on the Next.js process and inject it via the reverse proxy (deploy/vps/Caddyfile.dashboard.example); without the secret and without SCP_DEV_MODE=1, all gated routes answer 503."
      );
    }
  } else {
    // [AUDIT-FIX SEC-01] Production fail-closed: no secret configured and no
    // explicit dev flag — deny the gated API entirely rather than trusting
    // spoofable X-Forwarded-For/X-Real-IP headers.
    return NextResponse.json(
      {
        error: "Dashboard API unavailable: SCP_DASHBOARD_PROXY_SECRET is not set (fail-closed). Set SCP_DASHBOARD_PROXY_SECRET on the Next.js dashboard process and configure the reverse proxy to inject the x-scp-proxy-secret header with the same value (see deploy/vps/Caddyfile.dashboard.example). For local development only, set SCP_DEV_MODE=1 to enable the XFF fallback.",
      },
      { status: 503 }
    );
  }

  const hops = extractHopHeaders(request);

  // Next 16 no longer exposes the socket peer as request.ip; access control
  // rests entirely on the trusted reverse proxy contract: the proxy ALWAYS
  // appends the peer IP to x-forwarded-for (see deploy/vps/Caddyfile), so a
  // request without hop headers is rejected fail-closed even from localhost.
  if (hops.length === 0) {
    return NextResponse.json(
      { error: "Access denied. Missing IP headers; dashboard API is restricted to localhost." },
      { status: 403 }
    );
  }

  // Strict multi-hop validation:
  // 1. The last hop appended by the trusted reverse proxy must be in LOCAL_IPS.
  // 2. All hops in the chain must be local to prevent first-hop or intermediary injection.
  const lastHop = hops[hops.length - 1];
  const allLocal = hops.every((ip) => LOCAL_IPS.has(ip));

  if (!LOCAL_IPS.has(lastHop) || !allLocal) {
    return NextResponse.json(
      { error: "Access denied. Dashboard API is restricted to localhost." },
      { status: 403 }
    );
  }

  return NextResponse.next();
}

export const config = {
  // [AUDIT-FIX low-9] matcher mở rộng theo GATED_API_ROOTS (:path* match cả
  // zero segment → root path cũng vào gate).
  matcher: [
    "/api/scp/:path*",
    "/api/audit/:path*",
    "/api/autofix/:path*",
    "/api/scanners/:path*",
  ],
};
