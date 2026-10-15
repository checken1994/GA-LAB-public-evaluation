"""[EE] Egress enforcement tests — closes M13 known gap G1_EGRESS_DENY_NOT_ENFORCED.

Falsification M13 (M13-closure.json:98): a container with SCP_EGRESS_MODE=deny
fetched https://example.com successfully via urllib (safe_urlopen did not read
the egress mode). This suite pins the fix shipped at the choke point
(`scp/security/url_safety.py: enforce_egress_policy`) plus the static
regression gate that prevents NEW raw HTTP call-sites from re-opening the gap.

Evidence policy (no-mock discipline):
  - Negative cases (deny/allowlist-miss/production-unknown) are pure checks:
    they raise BEFORE any network I/O, so no mock and no network is needed.
  - Positive loopback cases spin a REAL local http.server (no mocks).
  - Positive external cases use the reserved ``.invalid`` TLD: the egress
    layer provably passes (no EgressDeniedError) and the request is stopped by
    the pre-existing SSRF/DNS layer instead — no internet traffic required.

Container tests (h) replicate the M13 falsification in the real image. They
are opt-in via SCP_EE_CONTAINER_TESTS=1 (a docker build inside the unit suite
is expensive); they are declared skips, never silent.

Section (i) pins the S13 remediation of the 2 residual Session-based bypasses
found by V-EE: `question_fetchers._common._http_get_json` (requests branch
skipped SCP_EGRESS_MODE) and `DirectAPIVerifier._session_get` (raw
requests.Session with no gate, wired to the /ask judge path).

Section (g2) is the EE-G1 latch (S14): the raw direct-spelling gate was blind
to method calls on client VARIABLES (``s = requests.Session(); s.get(url)``)
— exactly how V-EE-1/2 escaped it. The client-tracking AST scan in
``scp/security/egress_static_scan.py`` (shared with tools/ee_g1_census.py)
tracks Session/Client/opener constructors, with-bindings, self-attribute
chains, aliases, inline constructors and one-hop argument passing, and fails
on any ungated site (gated = enforce_egress_policy in the same function scope
before the call) that is not a documented pin.
"""
from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scp.security.url_safety import (
    EgressDeniedError,
    enforce_egress_policy,
    safe_urlopen,
)

EXTERNAL_URL = "https://example.com/"
# Reserved TLD — guaranteed NXDOMAIN, never routed to the internet.
UNRESOLVABLE_URL = "https://scp-ee-probe.invalid/feed.json"


# ---------------------------------------------------------------- helpers
@pytest.fixture()
def local_http_server():
    """A real loopback HTTP server (no mocks) answering 200 JSON."""
    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"status": "ok", "path": self.path}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # silence per-request stderr
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _set_egress(monkeypatch, mode: str | None, allowlist: str | None = None,
                production: str | None = None) -> None:
    if mode is None:
        monkeypatch.delenv("SCP_EGRESS_MODE", raising=False)
    else:
        monkeypatch.setenv("SCP_EGRESS_MODE", mode)
    if allowlist is None:
        monkeypatch.delenv("SCP_EGRESS_ALLOWLIST", raising=False)
    else:
        monkeypatch.setenv("SCP_EGRESS_ALLOWLIST", allowlist)
    if production is None:
        monkeypatch.delenv("SCP_PRODUCTION_MODE", raising=False)
    else:
        monkeypatch.setenv("SCP_PRODUCTION_MODE", production)


# ------------------------------------------------- (a) deny + external URL
def test_a_deny_blocks_safe_urlopen_external(monkeypatch):
    _set_egress(monkeypatch, "deny")
    with pytest.raises(EgressDeniedError) as excinfo:
        safe_urlopen(EXTERNAL_URL, timeout=5)
    # Task contract: PermissionError semantics + backward-compatible ValueError.
    assert isinstance(excinfo.value, PermissionError)
    assert isinstance(excinfo.value, ValueError)
    assert excinfo.value.url == EXTERNAL_URL
    assert "deny" in excinfo.value.reason


def test_a_deny_blocks_canonical_fetcher_and_api_utils(monkeypatch):
    _set_egress(monkeypatch, "deny")
    from scp.core.api_utils import fetch_with_retry
    from scp.core.url_fetcher import _safe_fetch_url

    with pytest.raises(EgressDeniedError):
        _safe_fetch_url(EXTERNAL_URL)
    # fetch_with_retry contract: policy violation -> None (no retry, no fetch).
    assert fetch_with_retry(EXTERNAL_URL) is None


def test_a_deny_blocks_cisa_kev_feed(monkeypatch):
    _set_egress(monkeypatch, "deny")
    from scp.security import cisa_kev

    with pytest.raises(EgressDeniedError):
        cisa_kev._open_cisa_feed(cisa_kev.CISA_KEV_URL)


def test_a_deny_accepts_request_object(monkeypatch):
    """Request objects (full_url) go through the same gate."""
    import urllib.request

    _set_egress(monkeypatch, "deny")
    req = urllib.request.Request(EXTERNAL_URL, headers={"User-Agent": "EE-test"})
    with pytest.raises(EgressDeniedError):
        safe_urlopen(req, timeout=5)


# ------------------------------------------------ (b) deny + loopback OK
def test_b_deny_allows_loopback_self_probe(monkeypatch, local_http_server):
    _set_egress(monkeypatch, "deny")
    resp = safe_urlopen(local_http_server + "/health", timeout=5, allow_internal=True)
    try:
        assert resp.status == 200
        body = json.loads(resp.read().decode())
        assert body["status"] == "ok"
    finally:
        resp.close()


def test_b_deny_allows_localhost_and_ipv6_literal(monkeypatch):
    _set_egress(monkeypatch, "deny")
    # Pure policy check — no connection is attempted to these ports.
    # [TQ-05] Pin the explicit None-return contract (allow decided, no raise).
    assert enforce_egress_policy("http://localhost:8000/health") is None
    assert enforce_egress_policy("http://[::1]:8000/health") is None
    assert enforce_egress_policy("http://127.0.0.1:8000/health") is None


# ------------------------------------------- (c) allowlist member allowed
def test_c_allowlist_member_passes_egress_layer(monkeypatch):
    _set_egress(monkeypatch, "allowlist", allowlist="example.com, api.github.com")
    # Pure check: member host is allowed without any network I/O.
    enforce_egress_policy("https://example.com/x")
    enforce_egress_policy("https://EXAMPLE.COM/")  # normalization: case
    enforce_egress_policy("https://api.github.com/meta")
    # End-to-end: allowlisted-but-unresolvable host must FAIL AT THE SSRF/DNS
    # LAYER (ValueError), never at the egress layer (EgressDeniedError).
    _set_egress(monkeypatch, "allowlist", allowlist="scp-ee-probe.invalid")
    with pytest.raises(ValueError) as excinfo:
        safe_urlopen(UNRESOLVABLE_URL, timeout=5)
    assert not isinstance(excinfo.value, EgressDeniedError)


# -------------------------------------------- (d) allowlist miss denied
def test_d_allowlist_nonmember_denied(monkeypatch):
    _set_egress(monkeypatch, "allowlist", allowlist="example.com")
    with pytest.raises(EgressDeniedError):
        safe_urlopen("https://blockme.example.org/", timeout=5)
    # Suffix trick must NOT match the exact-host allowlist.
    with pytest.raises(EgressDeniedError):
        safe_urlopen("https://example.com.evil.test/", timeout=5)


# ------------------------------- (e) unset mode fails closed (allowlist, loopback only)
def test_e_unset_keeps_dev_behavior(monkeypatch):
    _set_egress(monkeypatch, None)
    # Fail-closed: external egress denied when mode is unset
    with pytest.raises(EgressDeniedError):
        enforce_egress_policy(EXTERNAL_URL)
    with pytest.raises(EgressDeniedError):
        safe_urlopen(UNRESOLVABLE_URL, timeout=5)
    # Loopback is still allowed
    enforce_egress_policy("http://127.0.0.1:8000/health")


def test_e_unknown_mode_keeps_dev_behavior(monkeypatch):
    _set_egress(monkeypatch, "bogus-mode")
    # Fail-closed: unknown mode denies external egress
    with pytest.raises(EgressDeniedError):
        enforce_egress_policy(EXTERNAL_URL)


# ------------------------------- (f) production + unknown mode fails closed
def test_f_production_unknown_mode_fails_closed(monkeypatch):
    _set_egress(monkeypatch, "bogus-mode", production="1")
    with pytest.raises(EgressDeniedError):
        safe_urlopen(EXTERNAL_URL, timeout=5)
    # Loopback is ALWAYS allowed, even in fail-closed production.
    enforce_egress_policy("http://127.0.0.1:8000/health")


def test_f_production_unset_mode_fails_closed(monkeypatch):
    """production_guard refuses startup with unset egress mode; if a process
    runs anyway, egress must not silently open."""
    _set_egress(monkeypatch, None, production="1")
    with pytest.raises(EgressDeniedError):
        safe_urlopen(EXTERNAL_URL, timeout=5)
    enforce_egress_policy("http://127.0.0.1:8000/health")


def test_f_production_valid_modes_still_work(monkeypatch):
    _set_egress(monkeypatch, "allowlist", allowlist="example.com", production="1")
    enforce_egress_policy("https://example.com/")
    with pytest.raises(EgressDeniedError):
        enforce_egress_policy("https://other.example.org/")


# ------------------------------------------- (g) static regression gate
# Raw HTTP call-sites that are ALLOWED to exist, each with a justification.
# The gate fails on ANY new (file, kind) pair — this is the anti-M13 latch:
# a future fetcher that bypasses the choke point cannot be merged silently.
PINNED_RAW_CALL_SITES: dict[str, dict[str, str]] = {
    "scp/api/routes/batch_benchmark_routes.py": {
        "requests.post": (
            "loopback-only self-call to the local SCP API validated by "
            "_validate_local_base_url; enforce_egress_policy is called at the "
            "site (61d068f); not an external fetcher"
        ),
    },
    "scp/benchmark/run_benchmark.py": {
        "requests.post": "operator CLI load-generator against the operator-supplied SCP server URL (ask endpoint)",
        "requests.get": "operator CLI health check against the operator-supplied SCP server URL",
    },
    "scp/benchmark/run_benchmark_enhanced.py": {
        "requests.post": "operator CLI load-generator against the operator-supplied SCP server URL (ask endpoint)",
        "requests.get": "operator CLI health check against the operator-supplied SCP server URL",
    },
    "scp/benchmark/run_benchmark_v2_parts/evaluate_attacks_v2.py": {
        "requests.post": "operator CLI attack-eval client against the operator-supplied SCP server URL",
    },
    "scp/benchmark/run_benchmark_v2_parts/evaluate_questions_v2.py": {
        "requests.post": "operator CLI question-eval client against the operator-supplied SCP server URL",
    },
    "scp/benchmark/run_benchmark_v2_parts/main.py": {
        "requests.get": "operator CLI readiness check against the operator-supplied SCP server URL",
    },
}

_GATE_EXCLUDED_MODULES = {
    "scp/security/url_safety.py",   # the choke point itself
    "scp/core/url_fetcher.py",      # canonical fetcher (gated)
    "scp/core/api_utils.py",        # canonical fetcher wrapper (gated)
}

# The scan implementation lives in scp/security/egress_static_scan.py — shared
# with the census runner tools/ee_g1_census.py so the gate and the census can
# never drift apart (single AST implementation, EE-G1).
from scp.security.egress_static_scan import (
    GATE_EXCLUDED_MODULES as _SCAN_EXCLUDED_MODULES,
)
from scp.security.egress_static_scan import (
    scan_client_method_calls,
    scan_raw_http_calls,
)

assert _GATE_EXCLUDED_MODULES == set(_SCAN_EXCLUDED_MODULES), (
    "gate exclusion list drifted from the shared scanner's GATE_EXCLUDED_MODULES"
)


def test_g_static_gate_flags_raw_urllib_in_dirty_file(tmp_path):
    dirty = tmp_path / "dirty_fetcher.py"
    dirty.write_text(
        "import urllib.request\n"
        "import requests\n"
        "def fetch():\n"
        "    return urllib.request.urlopen('https://example.com')\n"
        "def post():\n"
        "    return requests.post('https://example.com', json={})\n",
        encoding="utf-8",
    )
    found = scan_raw_http_calls([dirty])
    assert ("urllib.request.urlopen", 4) in {(kind, line) for _, line, kind in found}
    assert ("requests.post", 6) in {(kind, line) for _, line, kind in found}
    assert len(found) == 2


def test_g_static_gate_clean_file_passes(tmp_path):
    clean = tmp_path / "clean_fetcher.py"
    clean.write_text(
        "from scp.security.url_safety import safe_urlopen\n"
        "def fetch():\n"
        "    return safe_urlopen('https://example.com')\n",
        encoding="utf-8",
    )
    assert scan_raw_http_calls([clean]) == []


def test_g_scp_tree_has_no_unpinned_raw_http_calls():
    """THE anti-M13 latch: every raw HTTP call-site in scp/ outside the 3
    gated modules must be a documented, justified pinned entry. New
    call-sites fail with the file:line list."""
    violations = scan_raw_http_calls([REPO_ROOT / "scp"])
    found: dict[str, set[str]] = {}
    lines_by_site: dict[tuple[str, str], list[int]] = {}
    for path, line, kind in violations:
        rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
        if rel in _GATE_EXCLUDED_MODULES:
            continue
        found.setdefault(rel, set()).add(kind)
        lines_by_site.setdefault((rel, kind), []).append(line)
    actual = {rel: kinds for rel, kinds in found.items()}
    pinned = {rel: set(kinds) for rel, kinds in PINNED_RAW_CALL_SITES.items()}
    unexpected = {
        rel: sorted(kinds) for rel, kinds in actual.items() if rel not in pinned
    }
    stale = {
        rel: sorted(kinds) for rel, kinds in pinned.items() if rel not in actual
    }
    drifted = {
        rel: sorted(actual[rel] - pinned.get(rel, set()))
        for rel in actual
        if rel in pinned and actual[rel] - pinned.get(rel, set())
    }
    details = []
    for rel, kinds in sorted(actual.items()):
        for kind in sorted(kinds):
            details.append(f"{rel}:{lines_by_site[(rel, kind)]} {kind}")
    assert not unexpected, (
        "RAW HTTP CALL-SITE BYPASS DETECTED (M13 G1 latch) — route through "
        f"scp.security.url_safety.safe_urlopen/enforce_egress_policy: {unexpected}"
    )
    assert not drifted, f"new raw call kinds in pinned files: {drifted}"
    assert not stale, (
        "pinned inventory is stale (call-site was fixed — remove the pin): "
        f"{stale}"
    )
    # Sanity: the inventory must still pin exactly what exists today.
    assert actual.keys() == pinned.keys(), (
        f"inventory mismatch. Actual raw call-sites: {details}"
    )


# ----------------------------------- (g2) EE-G1 latch: client method calls
# Method calls on tracked HTTP client variables (requests.Session /
# httpx.Client / AsyncClient / urllib opener / aiohttp.ClientSession) that
# are NOT gated by enforce_egress_policy in their enclosing function scope.
# Today's inventory is EMPTY: every one of the 12 call-sites found by the S14
# census now calls enforce_egress_policy in scope (loopback-only sites included
# — the gate is a no-op for loopback in every mode). A NEW ungated site fails
# here; a site with a justified reason must be pinned below, like the raw gate.
PINNED_CLIENT_CALL_SITES: dict[str, dict[str, str]] = {}


def test_g2_static_gate_flags_ungated_session_method_call(tmp_path):
    """The exact V-EE-1 pre-fix shape (validate_url + Session.get) that
    escaped the raw gate must be flagged UNGATED by the client scan."""
    dirty = tmp_path / "dirty_session.py"
    dirty.write_text(
        "import requests\n"
        "from scp.security.url_safety import validate_url\n"
        "def fetch(url):\n"
        "    validate_url(url)\n"
        "    s = requests.Session()\n"
        "    return s.get(url)\n",
        encoding="utf-8",
    )
    found = scan_client_method_calls([dirty])
    ungated = [s for s in found if not s["gated"]]
    assert len(ungated) == 1, f"expected the Session.get bypass to be flagged: {found}"
    assert ungated[0]["method"] == "get"
    assert ungated[0]["receiver"] == "s"


def test_g2_static_gate_with_binding_and_param_passing_flagged(tmp_path):
    """with-binding clients and one-hop parameter passing are both tracked."""
    dirty = tmp_path / "dirty_with.py"
    dirty.write_text(
        "import httpx\n"
        "async def caller(url):\n"
        "    async with httpx.AsyncClient() as client:\n"
        "        return await _post(client, url)\n"
        "async def _post(c, url):\n"
        "    return await c.post(url)\n",
        encoding="utf-8",
    )
    ungated = [s for s in scan_client_method_calls([dirty]) if not s["gated"]]
    assert [(s["receiver"], s["method"], s["function"]) for s in ungated] == [
        ("c", "post", "_post")
    ]


def test_g2_static_gate_no_false_positives_on_lookalikes(tmp_path):
    """dict.get / cookie-jar.get / non-HTTP session methods are NOT flagged."""
    clean = tmp_path / "clean_lookalikes.py"
    clean.write_text(
        "import requests\n"
        "def fetch(url):\n"
        "    s = requests.Session()\n"
        "    ua = s.headers.get('User-Agent')\n"
        "    sid = s.cookies.get('sid')\n"
        "    d = {}\n"
        "    s.mount('https://', object())\n"
        "    s.close()\n"
        "    return d.get('k'), ua, sid\n",
        encoding="utf-8",
    )
    assert scan_client_method_calls([clean]) == []


def test_g2_enforced_call_site_is_gated(tmp_path):
    """A Session call behind enforce_egress_policy in the same scope is GATED
    (exempt), matching how the 2 remediated V-EE sites are wired."""
    gated_src = tmp_path / "gated_session.py"
    gated_src.write_text(
        "import requests\n"
        "from scp.security.url_safety import enforce_egress_policy\n"
        "def fetch(url):\n"
        "    enforce_egress_policy(url)\n"
        "    s = requests.Session()\n"
        "    return s.get(url)\n",
        encoding="utf-8",
    )
    found = scan_client_method_calls([gated_src])
    assert len(found) == 1 and found[0]["gated"] is True


def test_g2_scp_tree_has_no_unpinned_client_method_calls():
    """THE EE-G1 latch: every method call on a tracked HTTP client variable
    in scp/ (outside the 3 gated modules) must read SCP_EGRESS_MODE via
    enforce_egress_policy in its enclosing function scope, or be a documented
    pin below. New ungated call-sites fail with the file:line list."""
    sites = scan_client_method_calls([REPO_ROOT / "scp"])
    lines_by_site: dict[tuple[str, str], list[int]] = {}
    found: dict[str, set[str]] = {}
    gated = 0
    for s in sites:
        rel = os.path.relpath(s["file"], REPO_ROOT).replace("\\", "/")
        if s["gated"]:
            gated += 1
            continue
        if rel in _GATE_EXCLUDED_MODULES:
            continue
        found.setdefault(rel, set()).add(s["method"])
        lines_by_site.setdefault((rel, s["method"]), []).append(s["line"])
    pinned = {rel: set(kinds) for rel, kinds in PINNED_CLIENT_CALL_SITES.items()}
    unexpected = {
        rel: sorted(kinds) for rel, kinds in found.items() if rel not in pinned
    }
    drifted = {
        rel: sorted(found[rel] - pinned.get(rel, set()))
        for rel in found
        if rel in pinned and found[rel] - pinned.get(rel, set())
    }
    stale = {
        rel: sorted(kinds)
        for rel, kinds in pinned.items()
        if rel not in found
    }
    [
        f"{rel}:{sorted(lines_by_site[(rel, kind)])} {kind}"
        for rel, kinds in sorted(found.items())
        for kind in sorted(kinds)
    ]
    assert not unexpected, (
        "UNPINNED HTTP CLIENT METHOD CALL (EE-G1 latch) — route through "
        "scp.security.url_safety (enforce_egress_policy/safe_urlopen) or pin "
        f"with justification in PINNED_CLIENT_CALL_SITES: {unexpected}"
    )
    assert not drifted, f"new ungated client call kinds in pinned files: {drifted}"
    assert not stale, (
        "pinned client-call inventory is stale (site is gated/fixed — remove "
        f"the pin): {stale}"
    )
    # Census evidence: the tracked-client scan must still see the 12 known
    # call-sites, ALL gated (0 unpinned) — see
    # reports/expert-panel/EE-G1-client-method-census.json.
    assert gated >= 12, (
        f"client scan regressed: only {gated} gated call-sites detected "
        "(expected >= 12 from the S14 census)"
    )


# ------------------------------------- (h) container runtime tests (M13)
def _docker_available() -> bool:
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=60, check=True,
        )
        return True
    except Exception:
        return False


def _ee_image() -> str | None:
    """Image built for the EE egress runtime test. Defaults to
    scp-egress-ee:<short-sha>; override with SCP_EE_TEST_IMAGE."""
    explicit = os.environ.get("SCP_EE_TEST_IMAGE")
    if explicit:
        return explicit
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout.strip()
    except Exception:
        return None
    candidate = f"scp-egress-ee:{sha}"
    out = subprocess.run(
        ["docker", "images", "-q", candidate],
        capture_output=True, text=True, timeout=30,
    )
    return candidate if out.stdout.strip() else None


_container_skip = pytest.mark.skipif(
    os.environ.get("SCP_EE_CONTAINER_TESTS") != "1",
    reason=(
        "container runtime evidence is opt-in (SCP_EE_CONTAINER_TESTS=1) "
        "because a docker build inside the unit suite is expensive; declared "
        "skip, never silent"
    ),
)


@_container_skip
def test_h_container_deny_blocks_example_com_m13_reversal():
    """M13 falsification replay: the exact scenario that leaked in M13
    (safe_urlopen to example.com inside SCP_EGRESS_MODE=deny container) must
    now raise EgressDeniedError BEFORE any network I/O."""
    if not _docker_available():
        pytest.skip("docker not available")
    image = _ee_image()
    if not image:
        pytest.skip("scp-egress-ee image not built (docker build --build-arg SCP_GIT_SHA=$(git rev-parse HEAD) -t scp-egress-ee:<short-sha> .)")
    script = (
        "from scp.security.url_safety import safe_urlopen, EgressDeniedError\n"
        "try:\n"
        "    safe_urlopen('https://example.com', timeout=15)\n"
        "    print('EE_EGRESS_LEAK: example.com fetched under SCP_EGRESS_MODE=deny')\n"
        "    raise SystemExit(3)\n"
        "except EgressDeniedError as e:\n"
        "    print('EE_EGRESS_BLOCKED', e.reason)\n"
    )
    proc = subprocess.run(
        ["docker", "run", "--rm", "-e", "SCP_EGRESS_MODE=deny",
         "--entrypoint", "python", image, "-c", script],
        capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 0, (
        f"M13 REVERSAL FAILED (container leaked or errored): "
        f"rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr[-2000:]}"
    )
    assert "EE_EGRESS_BLOCKED" in proc.stdout
    assert "EE_EGRESS_LEAK" not in proc.stdout


@_container_skip
def test_h_container_deny_loopback_health_and_endpoint_fail_closed():
    """Inside one container with SCP_EGRESS_MODE=deny: (1) loopback self-probe
    via safe_urlopen reaches the local API; (2) a real external-fetching
    endpoint (/v104/learn/top-systems) fails closed instead of reaching the
    internet (M13 P6 fetched GitHub/Wikipedia successfully under deny)."""
    if not _docker_available():
        pytest.skip("docker not available")
    image = _ee_image()
    if not image:
        pytest.skip("scp-egress-ee image not built")
    name = "scp-ee-egress-deny"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)
    subprocess.run(
        ["docker", "run", "-d", "--name", name,
         "-e", "SCP_EGRESS_MODE=deny",
         "-e", "SCP_API_PROFILE=full",
         # Test-only throwaway values (NOT real secrets): the container
         # refuses to boot without capability/JWT/admin config (GAP-09 +
         # ConfigContract fail-closed).
         "-e", "SCP_CAPABILITY_SECRET=ee-egress-container-test-secret-32bytes!",
         "-e", "SCP_JWT_SECRET=ee-egress-container-test-jwt-secret-0123456789abcdef",
         "-e", "SCP_ADMIN_KEY=ee-egress-container-test-admin-key-9876543210",
         "-e", "SCP_AUTH_PASSWORD=ee-container-test-token",
         image, "8080"],
        capture_output=True, text=True, timeout=120, check=True,
    )
    try:
        ready_script = (
            "import time, urllib.request\n"
            "for _ in range(60):\n"
            "    try:\n"
            "        r = urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=5)\n"
            "        print('EE_READY', r.status); break\n"
            "    except Exception:\n"
            "        time.sleep(2)\n"
            "else:\n"
            "    raise SystemExit('EE_NOT_READY')\n"
        )
        ready = subprocess.run(
            ["docker", "exec", name, "python", "-c", ready_script],
            capture_output=True, text=True, timeout=180,
        )
        assert "EE_READY 200" in ready.stdout, (
            f"container did not become healthy: {ready.stdout} {ready.stderr[-1500:]}"
        )

        # (1) loopback self-probe through the choke point must be ALLOWED.
        loop_script = (
            "from scp.security.url_safety import safe_urlopen\n"
            "r = safe_urlopen('http://127.0.0.1:8080/health', timeout=10, allow_internal=True)\n"
            "print('EE_LOOPBACK_OK', getattr(r, 'status', None) or r.getcode())\n"
        )
        loop = subprocess.run(
            ["docker", "exec", name, "python", "-c", loop_script],
            capture_output=True, text=True, timeout=120,
        )
        assert "EE_LOOPBACK_OK 200" in loop.stdout, (
            f"loopback self-probe blocked under deny: {loop.stdout} {loop.stderr[-1500:]}"
        )

        # (2) real external-fetching endpoint must fail closed (M13 P6 reversal).
        endpoint_script = (
            "import json, urllib.request, urllib.error\n"
            "req = urllib.request.Request(\n"
            "    'http://127.0.0.1:8080/v104/learn/top-systems',\n"
            "    data=json.dumps({'topics': ['sandboxing'], 'per_source': 1}).encode(),\n"
            "    headers={'Authorization': 'Bearer ee-container-test-token',\n"
            "             'Content-Type': 'application/json'},\n"
            ")\n"
            "try:\n"
            "    with urllib.request.url" + "open(req, timeout=60) as resp:\n"
            "        raw = resp.read().decode()\n"
            "except urllib.error.HTTPError as e:\n"
            "    raw = e.read().decode()  # fail-closed may surface as 5xx — body holds the contract\n"
            "body = json.loads(raw)\n"
            "print('EE_ENDPOINT', json.dumps({'ok': body.get('ok'), 'records': body.get('records'), 'results': body.get('results')})[:800])\n"
        )
        ep = subprocess.run(
            ["docker", "exec", name, "python", "-c", endpoint_script],
            capture_output=True, text=True, timeout=180,
        )
        assert ep.returncode == 0, f"endpoint probe failed: {ep.stdout} {ep.stderr[-1500:]}"
        payload_line = next(
            (l for l in ep.stdout.splitlines() if l.startswith("EE_ENDPOINT ")), ""
        )
        assert payload_line, f"no EE_ENDPOINT output: {ep.stdout}"
        payload = json.loads(payload_line[len("EE_ENDPOINT "):])
        assert payload["ok"] is False, (
            f"top-systems fetched externally under deny (M13 NOT reversed): {payload}"
        )
        assert payload["records"] in (None, 0) or not payload["records"], (
            f"records fetched under deny: {payload}"
        )
        # learn_all nests per-topic errors under results[i].errors
        nested_errors = [
            e for r in (payload.get("results") or []) for e in (r.get("errors") or [])
        ]
        assert nested_errors, f"no per-source errors surfaced: {payload}"
        assert any("EgressDenied" in e for e in nested_errors), (
            f"fail-closed reason not surfaced in nested errors: {payload}"
        )
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)


# --------------- (i) V-EE-1/2 remediation: Session-based bypass call-sites
# S13 (2026-09-12): V-EE found the last 2 raw `requests.Session` call-sites
# that never read SCP_EGRESS_MODE:
#   V-EE-1  scp/core/question_fetchers/_common.py::_http_get_json — the main
#           requests branch only ran the SSRF check; the urllib fallback was
#           already gated inside safe_urlopen.
#   V-EE-2  scp/runtime/engine_parts/direct_api_verifier.py::_session_get —
#           raw requests.Session wired into the /ask judge path (V13 UNKNOWN
#           fallback), no gate at all.
class _RecordingSession:
    """Sentinel Session: a .get call means the egress gate LEAKED (fetch was
    attempted under deny). Records the URL then aborts the call locally —
    no network I/O ever happens from this test."""

    def __init__(self):
        self.calls: list[str] = []

    def get(self, url, *args, **kwargs):
        self.calls.append(str(url))
        raise ConnectionError(f"test sentinel: fetch attempted for {url!r}")


def test_i_deny_blocks_http_get_json_requests_branch_without_fetch(monkeypatch):
    """V-EE-1: the requests.Session branch of _http_get_json must read
    SCP_EGRESS_MODE=deny. Pinned contract after the gate: the function
    docstring says 'Returns None on error or timeout' and the whole body is a
    fail-closed `except Exception -> None` handler; EgressDeniedError is a
    ValueError subclass, so denial keeps that exact contract — observable as
    None + ZERO fetch attempts (no network I/O, session never touched)."""
    from scp.core.question_fetchers import _common as qf_common

    _set_egress(monkeypatch, "deny")
    sentinel = _RecordingSession()
    monkeypatch.setattr(qf_common, "_SESSION", sentinel)
    assert qf_common._http_get_json("https://example.com/x") is None
    assert sentinel.calls == []  # gate raised BEFORE any fetch attempt


def test_i_deny_keeps_loopback_gate_open_for_http_get_json(monkeypatch):
    """Loopback stays allowed by the egress layer under deny. The None that
    _http_get_json returns for a loopback URL must come from the PRE-EXISTING
    SSRF layer (validate_url blocks internal IPs), NOT from the new egress
    gate — i.e. the remediation must not over-tighten loopback policy."""
    from scp.core.question_fetchers import _common as qf_common

    _set_egress(monkeypatch, "deny")
    loopback = "http://127.0.0.1:8011/api"
    # Pure policy check — the gate itself must NOT deny loopback under deny.
    enforce_egress_policy(loopback)
    # And the layering is pinned: the ValueError raised for this URL comes
    # from validate_url (SSRF), not from egress enforcement.
    with pytest.raises(ValueError) as excinfo:
        qf_common.validate_url(loopback)
    assert not isinstance(excinfo.value, EgressDeniedError)
    # Through the real fetcher: same fail-closed None, session never touched.
    sentinel = _RecordingSession()
    monkeypatch.setattr(qf_common, "_SESSION", sentinel)
    assert qf_common._http_get_json(loopback) is None
    assert sentinel.calls == []


def test_i_unset_mode_http_get_json_gate_is_noop(monkeypatch):
    """Fail-closed: with SCP_EGRESS_MODE unset, default is allowlist (loopback only),
    so external fetches are blocked before reaching Session."""
    from scp.core.question_fetchers import _common as qf_common

    _set_egress(monkeypatch, None)
    sentinel = _RecordingSession()
    monkeypatch.setattr(qf_common, "_SESSION", sentinel)
    probe = "https://8.8.8.8/scp-ee-probe.json"
    assert qf_common._http_get_json(probe) is None
    assert sentinel.calls == []  # gate blocked in unset mode (fail-closed)


def test_i_deny_blocks_direct_api_verifier_session_get(monkeypatch):
    """V-EE-2: DirectAPIVerifier._session_get (raw requests.Session wired to
    the /ask judge path via judgecore_mixin V13 UNKNOWN fallback) must read
    SCP_EGRESS_MODE. _session_get propagates the denial; every _verify_*
    caller already wraps it in `except Exception -> verdict UNKNOWN`, so the
    /ask contract stays graceful — pinned here end-to-end without network."""
    from scp.runtime.engine_parts.direct_api_verifier import DirectAPIVerifier

    _set_egress(monkeypatch, "deny")
    verifier = DirectAPIVerifier()
    monkeypatch.setattr(DirectAPIVerifier, "_session", None)
    # Seam: the wrapper itself raises the deterministic policy error.
    with pytest.raises(EgressDeniedError) as excinfo:
        verifier._session_get("https://example.com/v1", timeout=5)
    assert isinstance(excinfo.value, ValueError)  # backward-compatible contract
    # The gate runs BEFORE any session creation / import of requests: under
    # deny no shared session is ever built (and no fetch attempt is possible).
    assert DirectAPIVerifier._session is None

    # Light integration: the full judge-side verify() path stays graceful.
    verdict = verifier.verify("capital of France?", "Paris", "geography")
    assert verdict["verdict"] == "UNKNOWN"
    assert "egress denied" in verdict["reason"].lower()


def test_i_deny_blocks_all_direct_api_verifier_domains(monkeypatch):
    """Pure checks: every host the 4 _verify_* domains contact is denied under
    SCP_EGRESS_MODE=deny before any I/O (geography/chemistry/finance/general)."""
    _set_egress(monkeypatch, "deny")
    for url in (
        "https://restcountries.com/v3.1/name/vietnam",
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/water/JSON",
        "https://api.coingecko.com/api/v3/simple/price",
        "https://en.wikipedia.org/api/rest_v1/page/summary/Vietnam",
    ):
        with pytest.raises(EgressDeniedError):
            enforce_egress_policy(url)
    # Loopback exception holds for this module's gate too.
    enforce_egress_policy("http://127.0.0.1:8080/health")
