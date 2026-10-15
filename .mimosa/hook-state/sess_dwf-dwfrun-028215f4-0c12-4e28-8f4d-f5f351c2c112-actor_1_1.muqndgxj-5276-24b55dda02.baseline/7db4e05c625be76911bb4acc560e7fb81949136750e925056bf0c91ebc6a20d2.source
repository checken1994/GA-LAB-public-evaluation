"""Reality test for Fix 4-a-005: ONE canonical URL fetcher (no divergence).

Behavioral execution test: tests SSRF prevention, scheme restriction, and
delegation from fetch_with_retry to _safe_fetch_url.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

def test_fetch_with_retry_blocks_loopback_ssrf():
    from scp.core.api_utils import fetch_with_retry

    # Loopback IP must be blocked fail-closed (returns None)
    res = fetch_with_retry("http://127.0.0.1:9999/ssrf-test", None, timeout=1, max_retries=1)
    assert res is None, f"Expected None for loopback SSRF, got {res!r}"

def test_fetch_with_retry_blocks_file_scheme():
    from scp.core.api_utils import fetch_with_retry

    # Non-HTTP(S) scheme must be blocked fail-closed (returns None)
    res = fetch_with_retry("file:///etc/passwd", None, timeout=1, max_retries=1)
    assert res is None, f"Expected None for file:// scheme, got {res!r}"

def test_safe_fetch_url_blocks_metadata_ip():
    from scp.core.url_fetcher import _safe_fetch_url

    # Cloud metadata / link-local IP 169.254.169.254 must raise ValueError
    with pytest.raises(ValueError):
        _safe_fetch_url("http://169.254.169.254/latest/meta-data", timeout=1)

def test_helpers_reexport_identity():
    from scp.api_server_parts import helpers
    from scp.core import url_fetcher

    assert helpers._safe_fetch_url is url_fetcher._safe_fetch_url
    assert helpers._SafeRedirectHandler is url_fetcher._SafeRedirectHandler
    assert helpers._is_disallowed_ip is url_fetcher._is_disallowed_ip

if __name__ == "__main__":
    test_fetch_with_retry_blocks_loopback_ssrf()
    test_fetch_with_retry_blocks_file_scheme()
    test_safe_fetch_url_blocks_metadata_ip()
    test_helpers_reexport_identity()
    print("PASS: reality_4-a-005 behavioral tests passed")
