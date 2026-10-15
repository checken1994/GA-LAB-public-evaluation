"""Security regression tests — OWASP API5 BFLA (Broken Function Level Authorization).

RC-10 fix — external check that admin routes have auth.

Scope:
- Every @app.get/post("/v98/*"), /v100/*, /v102/*, /v103/*, /v104/*, /v105/* route
  MUST have Depends(verify_admin) — either in the decorator's `dependencies=[...]`
  list OR in the function signature.
- Public routes (/health, /metrics, /, /dashboard, /v1/chat/completions,
  /v1/models, /ask) are EXEMPT — they are user-facing endpoints, not admin
  management APIs. (PyRIT/garak need /v1/* open for testing; /ask is the main
  Q&A endpoint.)

This test is INDEPENDENT from SCP's own scanners — it parses source directly
with regex, so SCP's autofix cannot silently disable it.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from scp.core.safe_process import safe_run

# This file lives at tests/internal/external_audit/test_security.py, so the
# repository root is FOUR parents up (external_audit -> internal -> tests -> root).
SCP_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# Product modules live inside the `scp/` package (GOD-split layout), not at
# the repository root. Point every canonical product path at the real files
# so these audits exercise live source instead of silently skipping it.
SCP_PACKAGE = SCP_ROOT / "scp"
API_SERVER = SCP_PACKAGE / "api_server.py"
API_LIFESPAN = SCP_PACKAGE / "api_server_parts" / "lifespan.py"
ROUTES_DIR = SCP_PACKAGE / "api" / "routes"
CANONICAL_AUTH = SCP_PACKAGE / "security" / "auth.py"

# Routes that are PUBLIC by design — exempt from BFLA check.
# Add new public routes here ONLY with justification comment.
PUBLIC_ROUTES = {
    "/",            # root info
    "/health",      # liveness probe (must be open for k8s/docker healthcheck)
    "/metrics",     # prometheus metrics (read-only, no secrets)
    "/dashboard",   # HTML dashboard (token required via URL ?token=... in JS)
    "/ask",         # main Q&A endpoint (user-facing, has rate limiting)
    "/v1/chat/completions",  # OpenAI-compatible (PyRIT/garak need open access)
    "/v1/models",           # OpenAI-compatible model list (public metadata)
}


def _extract_routes(src: str) -> list[tuple[int, str, str]]:
    """Return [(line_number, method, path)] for every FastAPI app/router decorator."""
    routes = []
    for i, line in enumerate(src.splitlines(), start=1):
        m = re.match(
            r'\s*@(app|router)\.(get|post|put|delete)\(\s*"([^"]+)"',
            line,
        )
        if m:
            routes.append((i, m.group(2), m.group(3)))
    return routes


def _route_has_auth(src: str, decorator_line: int) -> bool:
    """Check whether the route on `decorator_line` has verify_admin auth.

    Looks at the decorator line itself AND the next 8 lines (function signature).
    """
    lines = src.splitlines()
    chunk = lines[decorator_line - 1]
    for j in range(decorator_line, min(decorator_line + 8, len(lines))):
        chunk += "\n" + lines[j]
    return "Depends(verify_admin)" in chunk


def test_admin_routes_have_auth():
    """RC-2 BFLA check: every /v9*, /v10*, /v105* admin route must have verify_admin."""
    missing_auth = []
    # Fail-closed: if the canonical product sources are missing, the audit
    # must FAIL loudly instead of passing vacuously over an empty scan set.
    assert API_SERVER.exists(), f"canonical api_server.py missing at {API_SERVER}"
    assert ROUTES_DIR.is_dir(), f"canonical api/routes dir missing at {ROUTES_DIR}"
    sources = [API_SERVER] + sorted(ROUTES_DIR.glob("*.py"))
    for source_path in sources:
        if not source_path.exists():
            continue
        src = source_path.read_text(encoding="utf-8")
        for lineno, method, path in _extract_routes(src):
            if path in PUBLIC_ROUTES:
                continue
            if not re.match(r'^/v(9|10)\d+', path) and not path.startswith("/v105/"):
                continue
            if not _route_has_auth(src, lineno):
                missing_auth.append(f"  {source_path.name}:L{lineno}: {method.upper()} {path}")

    assert not missing_auth, (
        "BFLA regression — admin routes without verify_admin (RC-2):\n"
        + "\n".join(missing_auth)
    )


def test_verify_admin_no_dev_mode_bypass():
    """RC-2: verify_admin function must NOT contain the SCP_DEV_MODE bypass."""
    assert CANONICAL_AUTH.exists(), "canonical security/auth.py is missing"
    src = CANONICAL_AUTH.read_text(encoding="utf-8")
    m = re.search(
        r'^def verify_admin\([^)]*\)[^:]*:(?:.|\n)*?^(?:def |class |\Z)',
        src, re.MULTILINE,
    )
    assert m, "verify_admin function not found in canonical security/auth.py"
    body = re.sub(r'\n(?:def |class ).*$', '', m.group(0), flags=re.MULTILINE)
    bypass_pattern = re.compile(
        r'SCP_DEV_MODE[^"\n]*"1"[^:\n]*:[^\n]*\n\s*return\s+True',
        re.MULTILINE,
    )
    assert not bypass_pattern.search(body), (
        "RC-2 regression: SCP_DEV_MODE bypass (return True) present in verify_admin body"
    )


def test_no_hardcoded_token_in_source():
    """RC-2 CODE-AUDIT-001: no production token hardcoded in source."""
    token = os.environ.get("SCP_AUTH_TOKEN_SECRET", "")
    if not token:
        pytest.skip("SCP_AUTH_TOKEN_SECRET not set — cannot verify no-hardcoded-token")
    offenders = []
    for py_file in SCP_ROOT.rglob("*.py"):
        # Compare POSIX-normalized repo-relative paths: the original
        # forward-slash filters never matched on Windows backslash paths,
        # which caused test-fixture tokens to be flagged as product leaks.
        rel_path = py_file.relative_to(SCP_ROOT).as_posix()
        if "__pycache__" in rel_path:
            continue
        if (
            "tests/" in rel_path
            or "/test_" in f"/{rel_path}"
            or rel_path.startswith("test_")
        ):
            continue
        try:
            src = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if token in src:
            offenders.append(str(py_file))
    benchmark_dir = SCP_ROOT / "benchmark"
    if benchmark_dir.exists():
        for md_file in benchmark_dir.rglob("*.md"):
            try:
                src = md_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if token in src:
                offenders.append(str(md_file))
    assert not offenders, (
        "RC-2 regression: hardcoded production token found in:\n  "
        + "\n  ".join(offenders)
    )


def test_bandit_no_new_high_severity_via_bandit():
    """RC-10 external audit: bandit HIGH-severity count must not increase."""
    result = safe_run(
        ["bandit", "-r", str(SCP_ROOT), "-f", "json", "-q"],
    )
    if result.returncode not in (0, 1):
        pytest.skip(f"bandit failed to run: {result.stderr[:200]}")
    import json
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.skip("bandit did not produce JSON output")
    high_issues = [
        issue for issue in data.get("results", [])
        if issue.get("issue_severity") == "HIGH"
    ]
    new_categories = set()
    for issue in high_issues:
        if issue.get("test_id") != "B324":
            new_categories.add((issue.get("test_id"), issue.get("filename")))
    new_categories = {
        (tid, fn) for (tid, fn) in new_categories
        if "/tests/external_audit/" not in fn
    }
    assert not new_categories, (
        "RC-10 regression: new HIGH-severity bandit issues appeared:\n  "
        + "\n  ".join(f"{tid} in {fn}" for tid, fn in new_categories)
    )


def test_pc_read_only_allowlist_rejects_command_chains(tmp_path):
    """A read-only prefix must not permit a second shell command."""
    from scp.pc_control.pc_controller import PCController

    # [S16 FIX 2026-09-13] Bind the controller to a tmp working dir. The
    # default constructor binds kill_switch_path to the repository data/
    # directory, so a kill switch engaged by ANY earlier test in the same
    # pytest process (previously: the /v3/pc/kill route tests in
    # tests/T03_capability/, now tmp-isolated) turned every evaluate() into
    # PolicyDecision(False, 'Kill switch is engaged') before the
    # chain-rejection logic under test ever ran (observed on CI). The
    # allowlist/chain logic itself is data-dir independent.
    controller = PCController(working_dir=tmp_path)
    for command in (
        "whoami; Start-Process calc",
        "whoami ; Start-Process calc",
        "whoami && Start-Process calc",
        "whoami | Out-File probe.txt",
        "whoami $(Start-Process calc)",
    ):
        decision = controller.evaluate(command, capability_level=0)
        assert decision.allowed is False, command
        assert "chain" in decision.reason.lower(), decision


def test_browser_validator_rejects_private_network_targets():
    """Public browsing must share the canonical private-IP SSRF policy."""
    from scp.web_control.browser_session import BrowserSession

    for url in (
        "http://127.0.0.1:9222/json/list",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
    ):
        with pytest.raises(ValueError, match="internal/private"):
            BrowserSession.validate_url(url)


@pytest.mark.asyncio
async def test_webhook_handlers_pass_request_to_canonical_admin_auth(monkeypatch):
    """All webhook handlers must pass the Starlette Request into verify_admin."""
    from starlette.requests import Request

    import scp.api._shared as shared
    from scp.api import webhook

    captured: list[tuple[str, Request]] = []

    def fake_verify_admin(token: str | None = None, *, request: Request):
        captured.append((token or "", request))
        return True

    class FakeVerdict:
        verdict = "PASS"
        confidence = 0.9
        evidence: dict = {}
        domain = "general"
        final_answer = ""

    class FakeJudge:
        def judge(self, **_kwargs):
            return FakeVerdict()

    monkeypatch.setattr(shared, "verify_admin", fake_verify_admin)
    monkeypatch.setattr(shared, "get_judge", lambda: FakeJudge())

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/analyze",
            "headers": [(b"authorization", b"Bearer test-token")],
            "client": ("127.0.0.1", 12345),
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )
    analyze_handler = webhook.analyze_prompt.__wrapped__
    await analyze_handler(webhook.AnalyzeRequest(prompt="safe test"), request)
    await webhook.register_system(webhook.RegisterRequest(system_id="test-system"), request)
    await webhook.list_threats(request)
    await webhook.list_alerts(request)
    await webhook.list_systems(request)

    assert len(captured) == 5
    assert [token for token, _request in captured] == ["test-token"] * 5
    assert all(received_request is request for _token, received_request in captured)
    webhook._registered_systems.pop("test-system", None)


@pytest.mark.asyncio
async def test_webnavigator_revalidates_private_redirect_before_second_request(monkeypatch):
    """A public 302 to a private host must stop before another HTTP request."""
    from scp.web_control import web_navigator

    # [S15 FIX] The EE-G1 egress gate runs BEFORE the first HTTP hop inside
    # browse_public. Under an ambient SCP_EGRESS_MODE=deny (CI baseline) the
    # gate would raise on the public fixture URL before the redirect
    # revalidation this test pins is ever reached. Run under an explicit,
    # narrow allowlist instead: the public fixture host is permitted, the
    # redirect target (loopback) passes the egress gate and must then be
    # rejected by the SSRF revalidation — the contract under test.
    monkeypatch.setenv("SCP_EGRESS_MODE", "allowlist")
    monkeypatch.setenv("SCP_EGRESS_ALLOWLIST", "public.example.test")

    public_url = "https://public.example.test/start"
    private_url = "http://127.0.0.1:8000/internal"
    requested_urls: list[str] = []

    def fake_validate(url: str) -> str:
        if url == private_url:
            raise ValueError("internal/private target rejected")
        return url

    class FakeResponse:
        status_code = 302
        headers = {"location": private_url}
        url = public_url
        encoding = "utf-8"

        def raise_for_status(self):
            return None

    class FakeStream:
        async def __aenter__(self):
            return FakeResponse()

        async def __aexit__(self, _exc_type, _exc, _tb):
            return None

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return None

        def stream(self, method: str, url: str):
            assert method == "GET"
            requested_urls.append(url)
            return FakeStream()

    monkeypatch.setattr(web_navigator.BrowserSession, "validate_url", staticmethod(fake_validate))
    monkeypatch.setattr(web_navigator.httpx, "AsyncClient", FakeClient)

    navigator = web_navigator.WebNavigator()
    with pytest.raises(ValueError, match="internal/private"):
        await navigator.browse_public(public_url)

    assert requested_urls == [public_url]


def test_detail_routes_share_producer_data_path_constants():
    """Detail routes must read the same SCP_DATA_DIR-derived files as producers."""
    from scp.api.routes.audit_routes import AUDIT_DB as route_audit_db
    from scp.core.ai_threat_scanner import THREATS_DB as producer_threats_db
    from scp.core.audit_fetcher import AUDIT_DB as producer_audit_db
    from scp.core.harm_detector import HARM_DB as producer_harm_db

    threat_route_src = (ROUTES_DIR / "threat_routes.py").read_text(encoding="utf-8")
    assert route_audit_db == producer_audit_db
    assert "from scp.core.ai_threat_scanner import THREATS_DB" in threat_route_src
    assert "from scp.core.harm_detector import HARM_DB" in threat_route_src
    assert str(producer_threats_db).endswith("ai_threats.jsonl")
    assert str(producer_harm_db).endswith("ai_harm_incidents.jsonl")


def test_active_lifespan_does_not_autostart_ungated_external_producers():
    """Direct-request producers stay opt-in until a shared egress gate exists."""
    lifespan_src = API_LIFESPAN.read_text(encoding="utf-8")
    assert "async def lifespan" in lifespan_src
    for start_call in ("start_audit_fetcher", "start_scanner", "start_detector"):
        assert start_call not in lifespan_src


def test_stream_route_contract_is_live_and_offloads_sync_judge():
    """The registered stream route must not advertise the old dead-route state."""
    stream_src = (ROUTES_DIR / "stream_routes.py").read_text(encoding="utf-8")
    assert "LIVE ROUTE" in stream_src
    assert "DEAD ROUTE" not in stream_src
    assert "await asyncio.to_thread(" in stream_src
    assert '"/v105/ask/stream"' in stream_src
