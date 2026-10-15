"""[AUDIT-FIX low-9] Contract test — dashboard middleware IP/secret gate.

Root cause (external audit low-9): matcher chỉ phủ /api/scp/*; /api/audit,
/api/autofix, /api/scanners nằm NGOÀI gate — /api/autofix trả về internal
backendUrl. Fix: GATED_API_ROOTS + matcher mở rộng.

Regression:
  * Static: matcher config phải chứa cả 4 prefix.
  * Runtime (bun + next/server thật): request KHÔNG headers → 403 cho mọi
    gated path (kể cả /api/autofix/scanners); secret đúng + XFF local → pass;
    path ngoài gate → pass.
"""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MIDDLEWARE = ROOT / "dashboard" / "src" / "middleware.ts"
DASHBOARD_DIR = ROOT / "dashboard"

RUNTIME_SCRIPT = r"""
const { middleware } = await import("./src/middleware.ts");
const { NextRequest } = await import("next/server");

async function statusFor(path, headers = {}, secret = "") {
  // [P2-06 fix 2026-09-28] When no proxy secret is configured the
  // production branch FAILS CLOSED (503). The XFF-only 403 contract this
  // test pins requires the explicit dev-mode fallback, so the harness
  // opts in per request.
  process.env.SCP_DEV_MODE = secret ? "" : "1";
  process.env.SCP_DASHBOARD_PROXY_SECRET = secret;
  const req = new NextRequest("http://127.0.0.1" + path, { headers });
  const res = middleware(req);
  return res.status;
}

// 1. Mọi gated path KHÔNG headers → 403 fail-closed (bao gồm case audit).
const gated = [
  "/api/autofix/scanners",
  "/api/autofix",
  "/api/autofix/",
  "/api/audit",
  "/api/audit/x",
  "/api/scanners",
  "/api/scanners/x",
  "/api/scp/ask",
  "/api/scp/activity",
];
for (const p of gated) {
  const s = await statusFor(p);
  if (s !== 403) {
    console.error(`FAIL gated ${p} -> ${s} (expected 403)`);
    process.exit(1);
  }
}

// 2. Secret đúng + XFF local → middleware cho đi tiếp (NextResponse.next()).
const ok = await statusFor(
  "/api/autofix/scanners",
  { "x-scp-proxy-secret": "s3cret", "x-forwarded-for": "127.0.0.1" },
  "s3cret",
);
if (ok !== 200) {
  console.error(`FAIL authorized passthrough -> ${ok} (expected 200)`);
  process.exit(1);
}

// 3. Secret SAI → 403 dù có IP headers.
const bad = await statusFor(
  "/api/autofix/scanners",
  { "x-scp-proxy-secret": "wrong", "x-forwarded-for": "127.0.0.1" },
  "s3cret",
);
if (bad !== 403) {
  console.error(`FAIL wrong secret -> ${bad} (expected 403)`);
  process.exit(1);
}

// 4. Path ngoài gate → không bị chặn bởi middleware này.
const other = await statusFor("/api/public-route");
if (other !== 200) {
  console.error(`FAIL non-gated ${"/api/public-route"} -> ${other}`);
  process.exit(1);
}

console.log("MIDDLEWARE_GATE_OK");
"""


def test_middleware_matcher_covers_all_gated_roots():
    source = MIDDLEWARE.read_text(encoding="utf-8")
    for pattern in (
        '"/api/scp/:path*"',
        '"/api/audit/:path*"',
        '"/api/autofix/:path*"',
        '"/api/scanners/:path*"',
    ):
        assert pattern in source, f"matcher thiếu {pattern}"
    # Gate logic phải check cả exact path lẫn prefix.
    for root in ('"/api/scp"', '"/api/audit"', '"/api/autofix"', '"/api/scanners"'):
        assert root in source, f"GATED_API_ROOTS thiếu {root}"


@pytest.mark.parametrize("marker", ["MIDDLEWARE_GATE_OK"])
def test_middleware_runtime_gate_behavior(marker):
    """Runtime thật qua bun (node_modules của dashboard): NextRequest +
    middleware(request) — không phải mock."""
    result = subprocess.run(
        ["bun", "-e", RUNTIME_SCRIPT],
        cwd=str(DASHBOARD_DIR),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"middleware gate runtime FAIL:\n{result.stdout}\n{result.stderr}"
    )
    assert marker in result.stdout
