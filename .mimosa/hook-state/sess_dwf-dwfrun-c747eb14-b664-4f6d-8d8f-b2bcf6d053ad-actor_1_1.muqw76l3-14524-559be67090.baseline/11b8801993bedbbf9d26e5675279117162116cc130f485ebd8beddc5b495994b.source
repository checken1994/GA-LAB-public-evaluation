"""Unit tests for the Unified Egress Policy Engine."""
from __future__ import annotations

import pytest

from scp.policy.egress import (
    EgressDeniedError,
    EgressDestination,
    EgressMode,
    EgressPolicy,
)


def test_egress_destination_from_url() -> None:
    """Verifies parsing URL strings into structured EgressDestination objects."""
    dest = EgressDestination.from_url("https://api.github.com:8443/v1/repos")
    assert dest.host == "api.github.com"
    assert dest.port == 8443
    assert dest.scheme == "https"

    # Default scheme and port
    dest2 = EgressDestination.from_url("http://127.0.0.1/health")
    assert dest2.host == "127.0.0.1"
    assert dest2.port is None
    assert dest2.scheme == "http"


def test_egress_deny_blocks_external_allows_loopback() -> None:
    """EgressMode.DENY blocks all external network targets while permitting local loopbacks."""
    policy = EgressPolicy(mode=EgressMode.DENY, production_mode=False)

    # Loopbacks allowed
    policy.enforce("http://127.0.0.1:8000/api/health")
    policy.enforce("http://localhost:3000")
    policy.enforce("http://[::1]:8081/health")

    # External targets blocked
    with pytest.raises(EgressDeniedError) as excinfo:
        policy.enforce("https://example.com/api")
    assert "blocks all non-loopback" in str(excinfo.value)

    with pytest.raises(EgressDeniedError):
        policy.enforce("https://api.github.com")


def test_egress_blocks_cloud_metadata_unconditionally() -> None:
    """Cloud metadata endpoints (AWS, GCP, Azure, link-local) are unconditionally blocked."""
    # Even in OPEN mode and even if explicitly placed in allowlist!
    for mode in (EgressMode.DENY, EgressMode.ALLOWLIST, EgressMode.OPEN):
        policy = EgressPolicy(
            mode=mode,
            allowlist=["169.254.169.254", "metadata.google.internal"],
            production_mode=False,
        )

        with pytest.raises(EgressDeniedError) as exc_aws:
            policy.enforce("http://169.254.169.254/latest/meta-data")
        assert "cloud metadata" in str(exc_aws.value).lower()

        with pytest.raises(EgressDeniedError) as exc_gcp:
            policy.enforce("http://metadata.google.internal/computeMetadata/v1")
        assert "cloud metadata" in str(exc_gcp.value).lower()

        with pytest.raises(EgressDeniedError):
            policy.enforce("http://169.254.170.2/v2/credentials")

        # Generic 169.254.x.x link-local subnet
        with pytest.raises(EgressDeniedError):
            policy.enforce("http://169.254.10.20/endpoint")


def test_egress_allowlist_matches_subdomains_strictly() -> None:
    """Exact allowlist entry api.github.com allows only that host, denying similar or evil domains."""
    policy = EgressPolicy(
        mode=EgressMode.ALLOWLIST,
        allowlist=["api.github.com"],
        production_mode=False,
    )

    # Allowed exact match
    policy.enforce("https://api.github.com/users")
    policy.enforce("https://api.github.com:443/repos")

    # Denied non-matching hosts
    with pytest.raises(EgressDeniedError):
        policy.enforce("https://evil-api.github.com")

    with pytest.raises(EgressDeniedError):
        policy.enforce("https://attacker.com")

    with pytest.raises(EgressDeniedError):
        policy.enforce("https://github.com")


def test_egress_allowlist_wildcard_matching() -> None:
    """Wildcard allowlist entry *.github.com matches any subdomain of github.com and base domain."""
    policy = EgressPolicy(
        mode=EgressMode.ALLOWLIST,
        allowlist=["*.github.com"],
        production_mode=False,
    )

    policy.enforce("https://api.github.com")
    policy.enforce("https://raw.github.com")
    policy.enforce("https://github.com")

    with pytest.raises(EgressDeniedError):
        policy.enforce("https://evilgithub.com")


def test_egress_token_bound_allowed_hosts() -> None:
    """Dynamic allowlist contributed by a scoped capability token expands allowlist safely."""
    policy = EgressPolicy(
        mode=EgressMode.ALLOWLIST,
        allowlist=["api.github.com"],
        production_mode=False,
    )

    # pypi.org is not in global allowlist
    with pytest.raises(EgressDeniedError):
        policy.enforce("https://pypi.org/simple")

    # With capability token bound allowlist
    policy.enforce("https://pypi.org/simple", token_allowed_hosts=["pypi.org"])

    # Other non-granted hosts still fail
    with pytest.raises(EgressDeniedError):
        policy.enforce("https://registry.npmjs.org", token_allowed_hosts=["pypi.org"])


def test_egress_production_mode_fails_closed() -> None:
    """In production mode, open or unverified modes fail-closed immediately."""
    policy = EgressPolicy(mode=EgressMode.OPEN, production_mode=True)

    with pytest.raises(EgressDeniedError) as excinfo:
        policy.enforce("https://example.com")
    assert "production mode requires" in str(excinfo.value).lower()


def test_egress_empty_host_rejected() -> None:
    """Empty or invalid destination URL fails closed."""
    policy = EgressPolicy(mode=EgressMode.ALLOWLIST, production_mode=False)

    with pytest.raises(EgressDeniedError):
        policy.enforce("://")


def test_egress_blocks_ipv4_mapped_ipv6_metadata() -> None:
    """IPv4-mapped IPv6 cloud metadata addresses are detected and blocked fail-closed."""
    policy = EgressPolicy(mode=EgressMode.OPEN, production_mode=False)

    assert policy.is_cloud_metadata("::ffff:169.254.169.254") is True
    assert policy.is_cloud_metadata("[::ffff:169.254.169.254]") is True

    with pytest.raises(EgressDeniedError):
        policy.enforce("http://[::ffff:169.254.169.254]/latest/meta-data")

    with pytest.raises(EgressDeniedError):
        policy.enforce(EgressDestination(host="::ffff:169.254.169.254"))

    with pytest.raises(EgressDeniedError):
        policy.enforce(EgressDestination(host="[::ffff:169.254.169.254]"))


def test_egress_blocks_ipv6_aws_imds() -> None:
    """AWS IPv6 IMDS [fd00:ec2::254] is unconditionally blocked across all modes."""
    for mode in (EgressMode.DENY, EgressMode.ALLOWLIST, EgressMode.OPEN):
        policy = EgressPolicy(mode=mode, production_mode=False)
        assert policy.is_cloud_metadata("fd00:ec2::254") is True
        assert policy.is_cloud_metadata("[fd00:ec2::254]") is True
        with pytest.raises(EgressDeniedError):
            policy.enforce("http://[fd00:ec2::254]/latest/meta-data")


def test_safe_urlopen_redirect_enforces_egress_and_url_safety() -> None:
    """Verifies that 301/302 redirects in safe_urlopen re-validate with egress policy and validate_url."""
    import http.server
    import threading

    from scp.security.url_safety import safe_urlopen

    class RedirectToMetadataHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", "https://169.254.169.254/latest/meta-data")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), RedirectToMetadataHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with pytest.raises(EgressDeniedError):
            safe_urlopen(f"http://127.0.0.1:{port}/redirect", allow_internal=True, timeout=1.0)
    finally:
        server.shutdown()
        server.server_close()


def test_numeric_host_spellings_of_metadata_blocked_in_all_modes() -> None:
    """[AUDIT-FIX 2026-09-29 Agent1] Decimal/hex integer IPv4 spellings must not
    dodge the unconditional cloud-metadata block.

    Pre-fix: ipaddress.ip_address('2852039166') raises ValueError, so
    is_cloud_metadata returned False and EgressPolicy.enforce ALLOWED
    http://2852039166/latest/meta-data in OPEN mode (2852039166 ==
    169.254.169.254). OS resolvers accept this spelling, so the request was
    reachable. Regression pins: numeric conversion helper, detection across
    decimal + hex spellings, enforcement in ALL modes, and no over-blocking of
    a normal public IP expressed numerically (8.8.8.8 == 134744072) in OPEN mode.
    """
    from scp.policy.egress import _numeric_host_to_ip

    # Helper conversion (pure math, no socket)
    assert _numeric_host_to_ip("2852039166") == "169.254.169.254"
    assert _numeric_host_to_ip("0xA9FEA9FE") == "169.254.169.254"
    assert _numeric_host_to_ip("0Xa9fea9fe") == "169.254.169.254"
    assert _numeric_host_to_ip("example.com") is None
    assert _numeric_host_to_ip("123abc") is None
    assert _numeric_host_to_ip("") is None
    assert _numeric_host_to_ip("4294967296") is None  # > 32-bit

    policy = EgressPolicy(mode=EgressMode.OPEN, production_mode=False)
    assert policy.is_cloud_metadata("2852039166") is True
    assert policy.is_cloud_metadata("0xA9FEA9FE") is True
    # Another link-local address spelled numerically: 169.254.10.20
    assert policy.is_cloud_metadata(str(169 * 256**3 + 254 * 256**2 + 10 * 256 + 20)) is True
    # Non-metadata hosts stay untouched
    assert policy.is_cloud_metadata("134744072") is False  # 8.8.8.8
    assert policy.is_cloud_metadata("example.com") is False

    # Unconditional block holds in ALL modes for the integer spelling
    for mode in (EgressMode.DENY, EgressMode.ALLOWLIST, EgressMode.OPEN):
        policy = EgressPolicy(mode=mode, production_mode=False)
        with pytest.raises(EgressDeniedError):
            policy.enforce("http://2852039166/latest/meta-data")
        with pytest.raises(EgressDeniedError):
            policy.enforce("http://0xA9FEA9FE/latest/meta-data")

    # No over-blocking: numeric spelling of a public IP stays allowed in OPEN
    open_policy = EgressPolicy(mode=EgressMode.OPEN, production_mode=False)
    open_policy.enforce("http://134744072/")  # must NOT raise


def test_inet_aton_octal_and_compound_forms_metadata_blocked_f4a() -> None:
    """[AUDIT-FIX 2026-09-29 Agent5-F4a] inet_aton residual spellings closed.

    Linux inet_aton accepts octal-dotted ('0251.0376.0251.0376' ==
    169.254.169.254) and n-part tail forms ('169.254.169' == 169.254.0.169)
    that ipaddress rejects; Windows rejects some but SCP must be fail-closed
    across platforms. Old code (1def66c1) normalized only single-integer
    decimal/hex — those forms bypassed the metadata block in OPEN mode
    (Agent5 live-probe OBSERVED). New code normalizes them; bare-hex parts
    ('FE' without 0x) and parts overflowing their field correctly stay
    invalid (None), matching inet_aton.
    """
    from scp.policy.egress import _numeric_host_to_ip

    assert _numeric_host_to_ip("0251.0376.0251.0376") == "169.254.169.254"
    assert _numeric_host_to_ip("169.254.169") == "169.254.0.169"
    assert _numeric_host_to_ip("127.1") == "127.0.0.1"
    # invalid shapes stay invalid (None) — the standard parser rejects them
    assert _numeric_host_to_ip("0169.0254.0169.0254") is None  # 9 not octal
    assert _numeric_host_to_ip("0xA9FE.0xA9FE") is None  # head part > octet
    assert _numeric_host_to_ip("169.254.0xA9.FE") is None  # bare hex 'FE'

    policy = EgressPolicy(mode=EgressMode.OPEN, production_mode=False)
    assert policy.is_cloud_metadata("0251.0376.0251.0376") is True
    assert policy.is_cloud_metadata("169.254.169") is True

    for mode in (EgressMode.DENY, EgressMode.ALLOWLIST, EgressMode.OPEN):
        block_policy = EgressPolicy(mode=mode, production_mode=False)
        with pytest.raises(EgressDeniedError):
            block_policy.enforce("http://0251.0376.0251.0376/latest/meta-data")
        with pytest.raises(EgressDeniedError):
            block_policy.enforce("http://169.254.169/latest/meta-data")

    # no over-blocking: octal spelling of a PUBLIC ip and 3-part public form
    open_policy = EgressPolicy(mode=EgressMode.OPEN, production_mode=False)
    open_policy.enforce("http://0170.0254.0251.0376/")  # 120.172.169.254
    open_policy.enforce("http://8.8.8/")


def test_single_integer_leading_zero_octal_metadata_blocked() -> None:
    """[OCTAL-SINGLE-INT-FIX] Leading-0 SINGLE integer is OCTAL per inet_aton.

    Pre-fix: `host.isdigit()` parsed '025177524776' (= 0o25177524776 ==
    169.254.169.254) as DECIMAL → 25177524776 > 0xFFFFFFFF → None → the
    metadata spelling fell through to ipaddress (which rejects it) →
    is_cloud_metadata returned False → bypassed the unconditional metadata
    block in OPEN mode on Linux (inet_aton resolves it). Also fixes the
    docstring: '0170.0254.0251.0376' is 120.172.169.254 (public), NOT the
    metadata address — the correct dotted-octal spelling is
    '0251.0376.0251.0376'.
    """
    from scp.policy.egress import _numeric_host_to_ip

    assert _numeric_host_to_ip("025177524776") == "169.254.169.254"
    assert _numeric_host_to_ip("00") == "0.0.0.0"  # leading-0 multi-digit → octal, still zero
    assert _numeric_host_to_ip("0") == "0.0.0.0"  # single '0' stays decimal
    assert _numeric_host_to_ip("025177524778") is None  # '8' invalid octal → inet_aton rejects
    assert _numeric_host_to_ip("037777777777") == "255.255.255.255"  # octal 32-bit max
    assert _numeric_host_to_ip("047777777777") is None  # octal overflow → deny

    policy = EgressPolicy(mode=EgressMode.OPEN, production_mode=False)
    assert policy.is_cloud_metadata("025177524776") is True

    for mode in (EgressMode.DENY, EgressMode.ALLOWLIST, EgressMode.OPEN):
        block_policy = EgressPolicy(mode=mode, production_mode=False)
        with pytest.raises(EgressDeniedError):
            block_policy.enforce("http://025177524776/latest/meta-data")

    # no over-blocking: plain decimal single integer of a public IP unchanged
    open_policy = EgressPolicy(mode=EgressMode.OPEN, production_mode=False)
    open_policy.enforce("http://134744072/")  # 8.8.8.8
    # '08' part is invalid octal → None → standard parser/deny path decides;
    # in OPEN mode a non-metadata host is simply not metadata-blocked.
    open_policy.enforce("http://08.8.8.8/")  # must NOT raise
