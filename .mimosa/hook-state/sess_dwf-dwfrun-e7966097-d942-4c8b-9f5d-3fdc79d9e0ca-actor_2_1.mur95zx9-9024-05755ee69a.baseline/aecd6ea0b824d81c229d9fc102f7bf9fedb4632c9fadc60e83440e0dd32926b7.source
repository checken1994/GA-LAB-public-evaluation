"""[EGRESS-DEGRADE 2026-09-26] openlibrary/wikidata: không còn WARNING mỗi ask.

Live sweep: 2 nguồn này không nằm trong allowlist compose pass (.env là
owner-owned — product không được sửa), nên mỗi ask từng đốt WARNING egress
(qua fetch_with_retry ở cross_verify, và trực tiếp ở why_sources.wikidata).

Fix fail-quiet-by-design: mỗi nguồn khai báo host tĩnh, probe egress (không
raise) trước khi fetch; bị từ chối → CACHE-ONLY (không I/O) + INFO đúng MỘT
lần mỗi process. Owner thêm host vào SCP_EGRESS_ALLOWLIST → nguồn tự mở lại.
"""
from __future__ import annotations

import logging

import pytest

from scp.core import cross_verify
from scp.meta.why_sources import wikidata as why_wikidata


@pytest.fixture()
def _egress_denied(monkeypatch):
    """Egress policy từ chối 2 host ngoài (mô phỏng deployment không allowlist)."""
    from scp.policy.egress import EgressDeniedError

    def _deny(url, extra_allowed_hosts=None):
        if "openlibrary.org" in url or "wikidata.org" in url:
            raise EgressDeniedError(url, "host not in allowlist", url=url)

    monkeypatch.setattr("scp.security.url_safety.enforce_egress_policy", _deny)


@pytest.fixture(autouse=True)
def _reset_once_flags():
    yield
    cross_verify._EGRESS_DEGRADED_LOGGED.clear()
    why_wikidata._wikidata_cache_only_logged = False


def test_wikidata_degraded_no_fetch_and_single_info(monkeypatch, caplog, _egress_denied):
    calls: list[str] = []

    def _spy_fetch(url, *a, **k):
        calls.append(url)

    monkeypatch.setattr(cross_verify, "fetch_with_retry", _spy_fetch)

    with caplog.at_level(logging.INFO, logger="scp.cross_verify"):
        first = cross_verify._fetch_wikidata("Bitcoin")
        second = cross_verify._fetch_wikidata("Ethereum")

    assert first is None and second is None
    assert calls == [], "cache-only mode: KHÔNG được attempt fetch khi egress từ chối"
    degrade_infos = [
        r.getMessage() for r in caplog.records
        if r.levelno == logging.INFO and "degraded to cache-only" in r.getMessage()
    ]
    assert len(degrade_infos) == 1, f"INFO phải log đúng 1 lần/process, thấy: {degrade_infos}"
    warnings = [
        r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING
    ]
    assert not any("wikidata" in w.lower() and "egress" in w.lower() for w in warnings)


def test_wikidata_active_when_egress_allows(monkeypatch, caplog):
    """Non-degrade path: egress cho phép → fetch chạy bình thường."""

    def _allow(url, extra_allowed_hosts=None):
        return None

    def _fake_fetch(url, *a, **k):
        return {"search": [{"label": "Bitcoin", "description": "cryptocurrency"}]}

    monkeypatch.setattr("scp.security.url_safety.enforce_egress_policy", _allow)
    monkeypatch.setattr(cross_verify, "fetch_with_retry", _fake_fetch)

    result = cross_verify._fetch_wikidata("Bitcoin")
    assert result == "Bitcoin: cryptocurrency"


def test_openlibrary_degraded_in_cross_verify_book(monkeypatch, caplog, _egress_denied):
    calls: list[str] = []

    def _spy_fetch(url, *a, **k):
        calls.append(url)

    monkeypatch.setattr(cross_verify, "fetch_with_retry", _spy_fetch)
    # Các nguồn còn lại của cross_verify_book: cô lập khỏi network.
    monkeypatch.setattr(cross_verify, "_fetch_wikipedia", lambda title: None)
    monkeypatch.setattr(cross_verify, "_fetch_wikidata", lambda entity: None)

    with caplog.at_level(logging.INFO, logger="scp.cross_verify"):
        result = cross_verify.cross_verify_book("Dune")

    assert calls == [], "openlibrary cache-only: không attempt fetch title= lẫn q="
    assert not any(r["source"] == "OpenLibrary" for r in result.get("raw_results", []))
    degrade_infos = [
        r.getMessage() for r in caplog.records
        if r.levelno == logging.INFO and "openlibrary" in r.getMessage().lower()
        and "degraded to cache-only" in r.getMessage()
    ]
    assert len(degrade_infos) == 1


def test_why_sources_wikidata_degraded_single_info(monkeypatch, caplog, _egress_denied):
    def _fail_urlopen(*a, **k):  # defensive: nếu bị gọi là test fail
        raise AssertionError("cache-only mode must not attempt any fetch")

    monkeypatch.setattr(why_wikidata, "safe_urlopen", _fail_urlopen)

    with caplog.at_level(logging.INFO, logger="scp.why.sources.wikidata"):
        first = why_wikidata.query_wikidata("water", "boiling point?")
        second = why_wikidata.query_wikidata("gold", "melting point?")

    assert first is None and second is None
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(infos) == 1, f"INFO đúng 1 lần/process, thấy {len(infos)}"
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert not warnings, f"không còn WARNING egress mỗi ask: {[w.getMessage() for w in warnings]}"


def test_why_sources_wikidata_active_when_egress_allows(monkeypatch):
    """Non-degrade path: egress cho phép → fetch thật (mocked transport) chạy."""

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"search": [{"label": "water", "description": "chemical compound"}]}'

    def _allow(url, extra_allowed_hosts=None):
        return None

    monkeypatch.setattr("scp.security.url_safety.enforce_egress_policy", _allow)
    monkeypatch.setattr(why_wikidata, "safe_urlopen", lambda *a, **k: _Resp())

    result = why_wikidata.query_wikidata("water", "what?")
    assert result == "chemical compound"
