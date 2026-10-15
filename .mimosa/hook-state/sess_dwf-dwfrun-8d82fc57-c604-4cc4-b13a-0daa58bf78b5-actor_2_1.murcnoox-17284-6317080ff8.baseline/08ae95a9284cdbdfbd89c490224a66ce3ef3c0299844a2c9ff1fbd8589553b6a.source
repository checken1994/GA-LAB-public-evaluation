"""[LOG-LABEL-404 2026-09-26] fetch_with_retry log labels phải đúng loại lỗi.

Live sweep: mọi plain HTTP 404 (ValueError "HTTP error: 404" từ
_safe_fetch_url) bị gắn nhãn "Policy violation fetching ..." — sai sự thật:
404 là lỗi HTTP thông thường, không phải security event. Fix: chỉ
EgressDeniedError (và FetchBlockedError — policy rejection trước I/O) mới được
nhãn policy violation; HTTP error có nhãn riêng "http_error status=NNN".

Mock TẠI _safe_fetch_url (I/O boundary) — nhãn log là điều được kiểm chứng,
không phải network.
"""
from __future__ import annotations

import logging

import pytest

from scp.core import api_utils


@pytest.fixture()
def _no_retry_wait(monkeypatch):
    # Không ảnh hưởng: ValueError không nằm trong retry_if_exception_type.
    yield


def _allow_egress(monkeypatch):
    """Cô lập nhãn log khỏi egress policy: các test nhãn HTTP/fetch error
    phải tới được _safe_fetch_url (egress có suite riêng: test_egress_enforcement)."""
    monkeypatch.setattr(
        "scp.security.url_safety.enforce_egress_policy", lambda *a, **k: None
    )


def _cap_warnings(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def test_plain_http_404_gets_http_error_label_not_policy_violation(monkeypatch, caplog):
    _allow_egress(monkeypatch)

    def _fake_fetch(url, *, max_bytes=0, timeout=0.0):
        raise ValueError("HTTP error: 404")

    monkeypatch.setattr("scp.core.url_fetcher._safe_fetch_url", _fake_fetch)

    with caplog.at_level(logging.WARNING, logger="scp.api_utils"):
        result = api_utils.fetch_with_retry("https://example.gov/data.json")

    assert result is None  # contract giữ nguyên: không retry, trả None
    warnings = _cap_warnings(caplog)
    assert any("http_error status=404" in w for w in warnings)
    assert not any("Policy violation" in w for w in warnings), warnings


def test_egress_denied_keeps_policy_violation_label(monkeypatch, caplog):
    from scp.policy.egress import EgressDeniedError

    def _fake_enforce(url, extra_allowed_hosts=None):
        raise EgressDeniedError(url, "host not in allowlist", url=url)

    monkeypatch.setattr("scp.security.url_safety.enforce_egress_policy", _fake_enforce)

    with caplog.at_level(logging.WARNING, logger="scp.api_utils"):
        result = api_utils.fetch_with_retry("https://example.gov/data.json")

    assert result is None
    warnings = _cap_warnings(caplog)
    assert any("Policy violation" in w and "egress denied" in w for w in warnings)


def test_fetch_blocked_error_keeps_policy_violation_label(monkeypatch, caplog):
    from scp.core.url_fetcher import FetchBlockedError

    def _fake_enforce(url, extra_allowed_hosts=None):
        return None

    def _fake_fetch(url, *, max_bytes=0, timeout=0.0):
        raise FetchBlockedError("host resolves to disallowed IP range")

    monkeypatch.setattr("scp.security.url_safety.enforce_egress_policy", _fake_enforce)
    monkeypatch.setattr("scp.core.url_fetcher._safe_fetch_url", _fake_fetch)

    with caplog.at_level(logging.WARNING, logger="scp.api_utils"):
        result = api_utils.fetch_with_retry("https://example.gov/data.json")

    assert result is None
    warnings = _cap_warnings(caplog)
    assert any("Policy violation fetching" in w for w in warnings)
    assert not any("http_error" in w for w in warnings)


def test_non_http_valueerror_gets_fetch_failed_label(monkeypatch, caplog):
    _allow_egress(monkeypatch)

    def _fake_fetch(url, *, max_bytes=0, timeout=0.0):
        raise ValueError("DNS resolution failed: no records")

    monkeypatch.setattr("scp.core.url_fetcher._safe_fetch_url", _fake_fetch)

    with caplog.at_level(logging.WARNING, logger="scp.api_utils"):
        result = api_utils.fetch_with_retry("https://example.gov/data.json")

    assert result is None
    warnings = _cap_warnings(caplog)
    assert any("fetch_failed" in w for w in warnings)
    assert not any("Policy violation" in w for w in warnings)


def test_json_decode_error_keeps_its_own_label(monkeypatch, caplog):
    """JSONDecodeError là subclass của ValueError — nhánh riêng phải được giữ
    (thứ tự except sau fix: JSONDecodeError trước ValueError)."""
    _allow_egress(monkeypatch)

    def _fake_fetch(url, *, max_bytes=0, timeout=0.0):
        return b"not-json{"

    monkeypatch.setattr("scp.core.url_fetcher._safe_fetch_url", _fake_fetch)

    with caplog.at_level(logging.WARNING, logger="scp.api_utils"):
        result = api_utils.fetch_with_retry("https://example.gov/data.json")

    assert result is None
    warnings = _cap_warnings(caplog)
    assert any("JSON decode failed" in w for w in warnings)
    assert not any("fetch_failed" in w for w in warnings), warnings
