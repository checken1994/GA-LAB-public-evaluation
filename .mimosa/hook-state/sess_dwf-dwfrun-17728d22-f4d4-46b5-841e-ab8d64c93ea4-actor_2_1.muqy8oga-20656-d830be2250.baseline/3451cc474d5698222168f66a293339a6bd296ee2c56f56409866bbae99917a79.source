"""Integration check against a LIVE SCP API server on 127.0.0.1:8000.

[TQ-01 rewrite 2026-09-28] The original body swallowed every failure
(`except URLError: pass` + print-only), so the test passed even when the
server was down or the endpoint was broken ? a placebo. The contract is now:

  - server reachable  -> real HTTP response must be verified (status code
    must be an int in [200, 500) and the body must parse as JSON);
  - server not running -> explicit skip WITH reason (live-server dependency),
    never a silent pass.

This test does not start the server itself; it is a liveness probe for the
end-to-end flow, matching the R4-04 behavioral-test contract (real runtime
verification or an explicit skip ? never an unconditional pass).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from scp.security.url_safety import safe_urlopen

API_BASE = "http://127.0.0.1:8000"


def test_api_status():
    req = urllib.request.Request(f"{API_BASE}/v3/web/status", method="GET")
    try:
        # [SSRF gate] B310: loopback target -> safe_urlopen(allow_internal=True);
        # egress policy always permits loopback (scp/policy/egress.py Invariant 2).
        with safe_urlopen(req, timeout=5, allow_internal=True) as resp:
            status = resp.getcode()
            raw_body = resp.read()
    except urllib.error.HTTPError as e:
        # The server IS running and answered with an HTTP error status:
        # still real evidence, verify the code is a well-formed HTTP code.
        status = e.code
        raw_body = b""
    except (urllib.error.URLError, OSError) as e:
        pytest.skip(f"SCP API not running on {API_BASE} ? live-server probe skipped: {e}")

    assert isinstance(status, int), f"HTTP status must be int, got {type(status)!r}"
    assert 200 <= status < 500, f"SCP API returned unexpected status {status}"
    if raw_body:
        # /v3/web/status must answer JSON; a parse failure is a real defect.
        json.loads(raw_body.decode("utf-8"))
