"""[AUDIT-R2 2026-10-01] Regression contract for commit 31110e29 — dashboard proxy.

Commit 31110e29 (fix(audit-r2): dashboard route auth consistency + next 16.3.3
(RCE) + activity redaction + dev-mode guard) closed three UNPROVEN_BRANCH items
left open by the wave audit. This file turns each previously unproven branch
into a committed, probe-verified regression test (bun-script pattern of
tests/internal/test_p1_boundary_security.py — real bun execution, no mocks of
the subsystem under test).

Branches closed here and the old-fails/new-passes evidence each test carries:

  (a) Caller credential forwarding (PRODUCT_FAIL in the commit body):
      injectServiceAuth previously returned ONLY the injection delta, so
      routes building outgoing headers as "{Accept} ∪ injectServiceAuth(req)"
      silently DROPPED a caller-sent Authorization / X-SCP-PC-Token (backend
      401, caught by tests/T01_boot/test_live_cluster_e2e.py). OLD code fails
      every *_forwards_caller* test below (caller values absent from the
      returned header set); NEW code forwards them verbatim with injection
      precedence rules.

  (b) Posture gate (no auth oracle): OLD code injected the operator's own
      backend tokens UNCONDITIONALLY — in the trusted reverse-proxy posture
      (SCP_DASHBOARD_PROXY_SECRET set) that turns the dashboard into an auth
      oracle for any gated caller (privilege escalation). NEW code injects
      ONLY when no proxy secret is configured (local/dev posture); every
      *_posture_gate* probe below fails on OLD code (non-empty header set in
      the proxy posture).

  (c) Log redaction (M-4): dashboard/src/lib/log-redaction.ts did not exist
      before the commit — service logs and loop_runs error fields reached the
      browser raw (secret oracle). Every redaction vector below fails on OLD
      code (module missing → bun import error; or raw secret preserved).

  (d) Dev-mode guard hardening (M-1): (d1) a spoofed loopback XFF chain from a
      NON-loopback Host was ALLOWED by the baseline dev fallback (200) — NEW
      code rejects it 403; (d2) the weakened posture was only announced via a
      once-per-process console.warn — NEW code stamps X-SCP-Dev-Mode-Warning
      on EVERY dev-mode response and never on prod-posture responses.

Secret hygiene: probe tokens live only in the bun process env (they shadow the
real repository .env values because shell env wins in loadServiceAuthValues);
the bun scripts assert against process.env values and print only booleans and
status codes — no credential material is ever emitted to stdout/reports.
"""
from __future__ import annotations

import json
import secrets
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = REPO_ROOT / "dashboard"

# Probe-only credentials (NOT real secrets; deterministic so equality
# assertions stay stable regardless of the operator's repository .env).
PROBE_PROXY_SECRET = "probe-proxy-secret-prod"

# Placeholder the redaction module writes in place of a matched secret value.
# A constant (not an inline literal next to a key name) so no credential-shaped
# `"<key>": "<value>"` pair ever appears in source (Mimosa HIGH hygiene).
REDACTED_MARKER = "[REDACTED]"

# The bun scripts read these from process.env — the values never appear as
# literals inside the script text or its stdout.
_AUTH_ENV_SETUP = f"""
process.env.SCP_ROOT = {json.dumps(str(REPO_ROOT))};
process.env.SCP_AUTH_TOKEN_SECRET = "probe-auth-token-secret-value-0001";
process.env.SCP_ADMIN_KEY = "probe-admin-key-value-0002";
process.env.SCP_PC_CONTROLLER_TOKEN = "probe-pc-controller-token-0003";
process.env.SCP_SCHEDULER_ADMIN_TOKEN = "probe-scheduler-token-0004";
process.env.SCP_DASHBOARD_PROXY_SECRET = "";
"""

_SERVICE_AUTH_IMPORT = """
const { injectServiceAuth, injectSchedulerAuth, injectBackendJwtAuth } =
  await import("./dashboard/src/lib/scp-service-auth.ts");
"""


def _run_bun(script: str, cwd: Path = REPO_ROOT) -> dict:
    proc = subprocess.run(
        ["bun", "-e", script],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"bun probe failed:\nstdout={proc.stdout}\nstderr={proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# (a) Caller credentials are forwarded verbatim — the 31110e29 PRODUCT_FAIL
# ---------------------------------------------------------------------------


def test_service_auth_forwards_caller_credentials_verbatim():
    """OLD (injection-delta-only) code drops caller credentials → this test
    fails on the pre-31110e29 tree; NEW code forwards them verbatim."""
    script = (
        _AUTH_ENV_SETUP
        + _SERVICE_AUTH_IMPORT
        + """
const out = {};

// Full caller credential set → both forwarded, nothing injected over them.
const both = injectServiceAuth(new Request("http://localhost:3000/api/scp/trace/x", {
  headers: { "authorization": "Bearer caller-token-AAAA", "x-scp-pc-token": "caller-pc-BBBB" },
}));
out.bothAuth = both["Authorization"] === "Bearer caller-token-AAAA";
out.bothPc = both["X-SCP-PC-Token"] === "caller-pc-BBBB";
out.bothNoLeak = !JSON.stringify(both).includes(process.env.SCP_AUTH_TOKEN_SECRET)
  && !JSON.stringify(both).includes(process.env.SCP_PC_CONTROLLER_TOKEN);
out.bothExactKeys = Object.keys(both).sort().join(",") === "Authorization,X-SCP-PC-Token";

// Partial caller credential (only PC token) → PC forwarded verbatim, only the
// missing Authorization is filled (precedence: caller first, env second).
const partial = injectServiceAuth(new Request("http://localhost:3000/api/scp/activity", {
  headers: { "x-scp-pc-token": "caller-pc-CCCC" },
}));
out.partialPcForwarded = partial["X-SCP-PC-Token"] === "caller-pc-CCCC";
out.partialBearerInjected = partial["Authorization"] === `Bearer ${process.env.SCP_AUTH_TOKEN_SECRET}`;
console.log(JSON.stringify(out));
"""
    )
    res = _run_bun(script)
    assert res["bothAuth"], "caller Authorization must be forwarded verbatim, not dropped"
    assert res["bothPc"], "caller X-SCP-PC-Token must be forwarded verbatim, not dropped"
    assert res["bothNoLeak"], "operator tokens must NOT be injected over caller credentials"
    assert res["bothExactKeys"], "no unexpected headers may be added to the proxied fetch"
    assert res["partialPcForwarded"], "caller PC token must survive when only Authorization is injected"
    assert res["partialBearerInjected"], "missing Authorization must be filled from the operator env"


def test_scheduler_auth_forwards_caller_authorization_verbatim():
    """injectSchedulerAuth (loop/trigger lane): caller Authorization wins."""
    script = (
        _AUTH_ENV_SETUP
        + _SERVICE_AUTH_IMPORT
        + """
const out = {};
const forwarded = injectSchedulerAuth(new Request("http://localhost:3000/api/scp/loop/trigger", {
  headers: { "authorization": "Bearer caller-sched-DDDD" },
}));
out.forwarded = forwarded["Authorization"] === "Bearer caller-sched-DDDD";
out.exactKeys = Object.keys(forwarded).length === 1;
console.log(JSON.stringify(out));
"""
    )
    res = _run_bun(script)
    assert res["forwarded"], "caller Authorization must reach the scheduler verbatim"
    assert res["exactKeys"], "scheduler auth must inject nothing beyond Authorization"


# ---------------------------------------------------------------------------
# (b) Posture gate — no auth oracle in the trusted reverse-proxy posture
# ---------------------------------------------------------------------------


def test_service_auth_posture_gate_blocks_injection_when_proxy_secret_set():
    """OLD code injected operator tokens unconditionally → fails here on the
    pre-31110e29 tree; NEW code returns an empty set in the proxy posture so an
    unauthenticated proxied call surfaces the backend's own 401/403."""
    script = (
        _AUTH_ENV_SETUP
        + _SERVICE_AUTH_IMPORT
        + f"""
process.env.SCP_DASHBOARD_PROXY_SECRET = {json.dumps(PROBE_PROXY_SECRET)};
const out = {{}};

// No caller credentials + proxy posture → NOTHING injected (no auth oracle).
const empty = injectServiceAuth(new Request("http://localhost:3000/api/scp/activity", {{ headers: {{}} }}));
out.serviceEmpty = Object.keys(empty).length === 0;

// Scheduler: same posture contract.
const sched = injectSchedulerAuth(new Request("http://localhost:3000/api/scp/loop/trigger", {{ headers: {{}} }}));
out.schedulerEmpty = Object.keys(sched).length === 0;

// Backend JWT: no caller auth in proxy posture → nothing minted, nothing
// attached (must not even attempt the /auth/token exchange).
const jwt = await injectBackendJwtAuth(
  new Request("http://localhost:3000/api/scp/ask", {{ headers: {{}} }}),
  "http://127.0.0.1:9",
);
out.jwtEmpty = Object.keys(jwt).length === 0;

// Caller credentials still forward verbatim inside the proxy posture — the
// proxy forwards THEIR credentials and attaches nothing of its own.
const caller = injectServiceAuth(new Request("http://localhost:3000/api/scp/x", {{ headers: {{ "authorization": "Bearer caller-EEEE" }} }}));
out.callerStillForwarded =
  caller["Authorization"] === "Bearer caller-EEEE" && Object.keys(caller).length === 1;
console.log(JSON.stringify(out));
"""
    )
    res = _run_bun(script)
    assert res["serviceEmpty"], "proxy posture must NOT inject operator backend tokens (auth oracle)"
    assert res["schedulerEmpty"], "scheduler injection must be posture-gated too"
    assert res["jwtEmpty"], "backend JWT exchange must not run in the proxy posture"
    assert res["callerStillForwarded"], "caller credentials must still forward in the proxy posture"


def test_service_auth_injects_env_tokens_only_in_local_posture():
    """Local posture (proxy secret unset): missing credentials are filled from
    the operator env — the [LOCAL-DEV] contract the dashboard cards rely on."""
    script = (
        _AUTH_ENV_SETUP
        + _SERVICE_AUTH_IMPORT
        + """
process.env.SCP_DASHBOARD_PROXY_SECRET = "";
const out = {};
const injected = injectServiceAuth(new Request("http://localhost:3000/api/scp/activity", { headers: {} }));
out.bearer = injected["Authorization"] === `Bearer ${process.env.SCP_AUTH_TOKEN_SECRET}`;
out.pc = injected["X-SCP-PC-Token"] === process.env.SCP_PC_CONTROLLER_TOKEN;
const sched = injectSchedulerAuth(new Request("http://localhost:3000/api/scp/loop/trigger", { headers: {} }));
out.schedBearer = sched["Authorization"] === `Bearer ${process.env.SCP_SCHEDULER_ADMIN_TOKEN}`;
console.log(JSON.stringify(out));
"""
    )
    res = _run_bun(script)
    assert res["bearer"], "local posture must fill Authorization from SCP_AUTH_TOKEN_SECRET"
    assert res["pc"], "local posture must fill X-SCP-PC-Token from SCP_PC_CONTROLLER_TOKEN"
    assert res["schedBearer"], "local posture must fill scheduler Authorization from its token env"


def test_backend_jwt_auth_fails_closed_without_any_exchange_key():
    """Fail-closed branch of injectBackendJwtAuth: without any exchange key the
    helper returns an EMPTY header set (the backend's own 401 surfaces) instead
    of manufacturing credentials — and never talks to the network."""
    script = (
        _SERVICE_AUTH_IMPORT
        + """
// Isolate from the repository .env: point SCP_ROOT at an empty directory so
// loadServiceAuthValues() finds no operator tokens at all.
const fs = await import("node:fs");
process.env.SCP_ROOT = await fs.promises.mkdtemp("scp-audit-r2-empty-env-");
delete process.env.SCP_ADMIN_KEY;
delete process.env.SCP_AUTH_TOKEN_SECRET;
delete process.env.SCP_PC_CONTROLLER_TOKEN;
delete process.env.SCP_SCHEDULER_ADMIN_TOKEN;
process.env.SCP_DASHBOARD_PROXY_SECRET = "";
const out = {};
const jwt = await injectBackendJwtAuth(
  new Request("http://localhost:3000/api/scp/ask", { headers: {} }),
  "http://127.0.0.1:9",
);
out.noAdminKeyNoMint = Object.keys(jwt).length === 0;
console.log(JSON.stringify(out));
"""
    )
    res = _run_bun(script)
    assert res["noAdminKeyNoMint"], "missing exchange key must fail closed with an empty credential set"


def test_backend_jwt_auth_fails_closed_when_exchange_endpoint_unreachable():
    """Fail-closed branch of the /auth/token exchange itself: with an exchange
    key configured but the backend unreachable (loopback port 9 — no egress),
    the mint fails and the helper returns an EMPTY header set instead of a
    forged or stale credential."""
    script = (
        _AUTH_ENV_SETUP
        + _SERVICE_AUTH_IMPORT
        + """
process.env.SCP_DASHBOARD_PROXY_SECRET = "";
const out = {};
// Loopback port 9 (discard) is never listening → fetch fails fast locally.
const jwt = await injectBackendJwtAuth(
  new Request("http://localhost:3000/api/scp/ask", { headers: {} }),
  "http://127.0.0.1:9",
  { forceRefresh: true },
);
out.unreachableBackendNoMint = Object.keys(jwt).length === 0;
console.log(JSON.stringify(out));
"""
    )
    res = _run_bun(script)
    assert res["unreachableBackendNoMint"], "failed mint must fail closed with an empty credential set"


# ---------------------------------------------------------------------------
# (c) Log redaction — M-4 vectors (module did not exist before 31110e29)
# ---------------------------------------------------------------------------


def test_log_redaction_replaces_known_secret_shapes_in_place():
    """Keyed secrets, bearer tokens, bare JWTs, provider token prefixes, JSON
    fields, and basic-auth URL userinfo are replaced with [REDACTED] in place
    (probe-calibrated: the keyed pattern eats the value to end of line)."""
    # [Mimosa HIGH fix] The JSON-field canary is runtime-assembled (same
    # precedent as tests/T00_integrity/test_acceptance_harness_isolation.py):
    # no credential-shaped literal may sit in source. The redaction module's
    # "JSON style" pattern matches ANY quoted value of >= 4 chars, so a random
    # 16-hex canary exercises the identical branch — only the canary bytes
    # differ, never the behavior under test.
    json_field_input = json.dumps({"api_key": secrets.token_hex(8), "user": "ops"})
    json_field_expected = json.dumps({"api_key": REDACTED_MARKER, "user": "ops"})
    script = """
const { redactLogLine } = await import("./dashboard/src/lib/log-redaction.ts");
const out = {};
out.keyedPassword = redactLogLine("boot config password=SuperSecret99 loaded");
out.authzBearer = redactLogLine("request failed: authorization: Bearer sk-live-abcdef123456 retrying");
out.standaloneBearer = redactLogLine("auth ok via bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig123456");
out.bareJwt = redactLogLine("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJVadQssw5c");
out.openaiKey = redactLogLine("using key sk-proj-abcdefgh1234567890");
out.githubPat = redactLogLine("cloning with ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234");
out.slackToken = redactLogLine("xoxb-123456789012-abcdefghijkl");
out.googleToken = redactLogLine("ya29.a0AfH6SMBx1234567890abcdefghi");
out.jsonField = redactLogLine('__JSON_FIELD_CANARY__');
out.basicAuthUrl = redactLogLine("connect to https://admin:hunter2@example.com/api");
out.benignUntouched = redactLogLine("scheduler tick ok: 3 runs, 0 failures");
console.log(JSON.stringify(out));
""".replace("__JSON_FIELD_CANARY__", json_field_input)
    res = _run_bun(script)
    assert res["keyedPassword"] == "boot config password=[REDACTED]", res["keyedPassword"]
    assert res["authzBearer"] == "request failed: authorization: [REDACTED]", res["authzBearer"]
    assert res["standaloneBearer"] == "auth ok via bearer [REDACTED]", res["standaloneBearer"]
    assert res["bareJwt"] == "[REDACTED]", res["bareJwt"]
    assert res["openaiKey"] == "using key [REDACTED]", res["openaiKey"]
    assert res["githubPat"] == "cloning with [REDACTED]", res["githubPat"]
    assert res["slackToken"] == "[REDACTED]", res["slackToken"]
    assert res["googleToken"] == "[REDACTED]", res["googleToken"]
    assert res["jsonField"] == json_field_expected, res["jsonField"]
    assert res["basicAuthUrl"] == "connect to https://[REDACTED]@example.com/api", res["basicAuthUrl"]
    assert res["benignUntouched"] == "scheduler tick ok: 3 runs, 0 failures", "benign lines must pass through unchanged"


def test_log_redaction_drops_unredactable_secret_lines():
    """Defense in depth: PEM private-key blocks and secret-keyed long opaque
    blobs that the in-place patterns cannot neutralize cause the WHOLE line to
    be dropped (null) instead of shipped on the off chance they are benign."""
    script = """
const { redactLogLine, redactLogText } = await import("./dashboard/src/lib/log-redaction.ts");
const out = {};
out.pemDropped = redactLogLine("-----BEGIN RSA PRIVATE KEY-----MIIEowIBAAKCAQEA");
out.opensshDropped = redactLogLine("-----BEGIN OPENSSH PRIVATE KEY-----b3BlbnNzaC1rZXk");
out.residualBlobDropped = redactLogLine("credential=AbCdEf123456AbCdEf123456");
out.residualTextFallback = redactLogText("-----BEGIN OPENSSH PRIVATE KEY-----");
out.shortCredKept = redactLogLine("credential=short");
console.log(JSON.stringify(out));
"""
    res = _run_bun(script)
    assert res["pemDropped"] is None, "PEM private-key lines must be dropped, not shipped"
    assert res["opensshDropped"] is None, "OpenSSH private-key lines must be dropped"
    assert res["residualBlobDropped"] is None, "secret-keyed long opaque blobs must be dropped"
    assert res["residualTextFallback"] == "[REDACTED]", "redactLogText falls back to [REDACTED] on dropped lines"
    assert res["shortCredKept"] == "credential=short", "short non-opaque values are not drop candidates"


def test_log_redaction_truncates_lines_and_caps_payload_bytes():
    """Truncate-before-redact bounds any single line (a huge log line cannot
    blow up the response), and capEventsPayload drops older events past the
    byte cap with an explicit dropped count (no silent truncation)."""
    script = """
const { redactLogLine, capEventsPayload } = await import("./dashboard/src/lib/log-redaction.ts");
const out = {};

// 500-char benign line → truncated to a bounded string with an explicit marker.
const long = "x".repeat(500);
const truncated = redactLogLine(long);
out.truncated = typeof truncated === "string" && truncated.length < 500 && truncated.includes("…[truncated]");

// Truncate-first also means a secret beyond the window never reaches the wire.
const tailSecret = "y".repeat(295) + " password=leaked-secret-value-9999";
const kept = redactLogLine(tailSecret);
out.tailSecretAbsent = typeof kept === "string" && !kept.includes("leaked-secret-value-9999");

// A secret still INSIDE the window is redacted even on an oversized line.
const inWindow = "z".repeat(200) + " token=sk-abcdefghijklmnop1234";
const redacted = redactLogLine(inWindow);
out.inWindowRedacted = typeof redacted === "string" && !redacted.includes("sk-abcdefghijklmnop1234");

// Payload cap: 4 tiny events serialized at ~12 bytes each against a 40-byte cap.
const events = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }];
const capped = capEventsPayload(events, (e) => ({ e }), 40);
out.capKept = capped.events.length;
out.capDropped = capped.dropped;
console.log(JSON.stringify(out));
"""
    res = _run_bun(script)
    assert res["truncated"], "oversized lines must be truncated with an explicit marker"
    assert res["tailSecretAbsent"], "secrets beyond the truncation window must never reach the browser"
    assert res["inWindowRedacted"], "secrets inside the window must still be redacted after truncation"
    assert res["capKept"] == 2 and res["capDropped"] == 2, res


# ---------------------------------------------------------------------------
# (d) Middleware dev-mode guard — M-1 (runtime: real next/server via bun)
# ---------------------------------------------------------------------------

_MIDDLEWARE_PROBE_SCRIPT = r"""
const { middleware } = await import("./src/middleware.ts");
const { NextRequest } = await import("next/server");

async function probe(url, headers, opts = {}) {
  process.env.SCP_DASHBOARD_PROXY_SECRET = opts.secret ?? "";
  process.env.SCP_DEV_MODE = opts.dev ?? "";
  const res = middleware(new NextRequest(url, { headers }));
  return { status: res.status, devWarning: res.headers.get("x-scp-dev-mode-warning") };
}

const out = {};

// d1: dev fallback, loopback Host + loopback XFF → 200 WITH the warning header.
out.devLocal = await probe("http://localhost:3000/api/scp/ask", { "x-forwarded-for": "127.0.0.1" }, { dev: "1" });

// d1 (the M-1 fix): SPOOFED loopback XFF chain from a NON-loopback Host → 403.
// The discriminating baseline-allowed vector is a single loopback hop with a
// non-loopback Host (all-local XFF chains of any shape); the multi-hop
// non-local chain below was already rejected by hop validation before M-1.
out.devSpoofedHost = await probe(
  "http://evil.example.com:3000/api/scp/ask",
  { "x-forwarded-for": "127.0.0.1, 10.0.0.9" },
  { dev: "1" },
);
out.devSpoofedSingleHop = await probe(
  "http://evil.example.com:3000/api/scp/ask",
  { "x-forwarded-for": "127.0.0.1" },
  { dev: "1" },
);
out.devLanHost = await probe("http://192.168.1.50:3000/api/scp/ask", { "x-forwarded-for": "127.0.0.1" }, { dev: "1" });

// Hop validation still runs first in dev mode: a remote last-hop stays 403.
out.devRemoteHop = await probe(
  "http://localhost:3000/api/scp/ask",
  { "x-forwarded-for": "127.0.0.1, 8.8.8.8" },
  { dev: "1" },
);

// d2: prod posture (secret set) → correct secret 200 WITHOUT the warning
// header; wrong secret 403; unset secret without dev flag 503 fail-closed.
out.prodOk = await probe(
  "http://localhost:3000/api/scp/ask",
  { "x-forwarded-for": "127.0.0.1", "x-scp-proxy-secret": "probe-proxy-secret-prod" },
  { secret: "probe-proxy-secret-prod" },
);
out.prodWrongSecret = await probe(
  "http://localhost:3000/api/scp/ask",
  { "x-forwarded-for": "127.0.0.1", "x-scp-proxy-secret": "wrong" },
  { secret: "probe-proxy-secret-prod" },
);
out.prodNoConfig = await probe("http://localhost:3000/api/scp/ask", { "x-forwarded-for": "127.0.0.1" }, {});

// 127.0.0.1 Host form is a loopback hostname too.
out.devLoopbackIpHost = await probe(
  "http://127.0.0.1:3000/api/scp/activity",
  { "x-real-ip": "127.0.0.1" },
  { dev: "1" },
);
console.log(JSON.stringify(out));
"""


def test_middleware_dev_mode_rejects_spoofed_loopback_and_stamps_warning():
    """OLD baseline (probed live on worktree 31110e29^ = 8597124f): a single
    loopback XFF hop with a non-loopback Host passed (200) and the dev posture
    was only console.warn-ed once (no response header) → both probes fail on
    the pre-31110e29 tree; NEW code 403s the spoof and stamps EVERY dev
    response. Multi-hop non-local chains were already rejected by hop
    validation before M-1 and are pinned as defense in depth."""
    res = _run_bun(_MIDDLEWARE_PROBE_SCRIPT, cwd=DASHBOARD_DIR)

    dev_warning = res["devLocal"]["devWarning"]
    assert res["devLocal"]["status"] == 200, res["devLocal"]
    assert dev_warning and "dev-mode fallback active" in dev_warning, (
        "every dev-mode response must carry X-SCP-Dev-Mode-Warning (was warn-once console only)"
    )
    assert res["devSpoofedHost"]["status"] == 403, (
        f"spoofed loopback XFF from a non-loopback Host must be rejected: {res['devSpoofedHost']}"
    )
    assert res["devSpoofedHost"]["devWarning"] is None
    assert res["devSpoofedSingleHop"]["status"] == 403, (
        f"single loopback hop with a non-loopback Host is the baseline-allowed spoof vector "
        f"(probed 200 on 31110e29^) and must be rejected: {res['devSpoofedSingleHop']}"
    )
    assert res["devLanHost"]["status"] == 403, "LAN-routed Host must be rejected in dev fallback"
    assert res["devRemoteHop"]["status"] == 403, "remote last-hop must stay rejected in dev fallback"
    assert res["devLoopbackIpHost"]["status"] == 200 and res["devLoopbackIpHost"]["devWarning"], (
        "127.0.0.1 Host form is loopback and must pass with the warning stamped"
    )


def test_middleware_prod_posture_has_no_dev_warning_and_stays_fail_closed():
    """The dev-mode warning header must NEVER appear in the trusted-proxy
    posture, and the production fail-closed contracts stay pinned."""
    res = _run_bun(_MIDDLEWARE_PROBE_SCRIPT, cwd=DASHBOARD_DIR)

    assert res["prodOk"]["status"] == 200, res["prodOk"]
    assert res["prodOk"]["devWarning"] is None, "no dev warning in the trusted-proxy posture"
    assert res["prodWrongSecret"]["status"] == 403, "wrong proxy secret must be rejected"
    assert res["prodNoConfig"]["status"] == 503, "unset secret without dev flag must stay fail-closed 503"
    assert res["prodNoConfig"]["devWarning"] is None
