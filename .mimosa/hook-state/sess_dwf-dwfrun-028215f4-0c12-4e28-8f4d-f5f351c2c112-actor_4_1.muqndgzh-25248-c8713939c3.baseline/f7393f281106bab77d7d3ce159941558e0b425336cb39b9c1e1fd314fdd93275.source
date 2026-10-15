"""[V104.32] Contract test — shared negative-result cache cho health pings.

Root cause (performance regression sau AUDIT-FIX low-4):
  * health_check() honest-ping thật qua mạng, nhưng cache 60s nằm trong
    self._cache (PER-INSTANCE). Test suite + /health consumers tạo instance
    MỚI mỗi call-chain → cache không bao giờ hit → hàng chục ping tuần tự,
    mỗi ping trả đầy đủ timeout mạng → suite crawl (26% trong 16 phút).
Fix:
  * scp.interfaces.data_source.shared_health_ping — cache PROCESS-WIDE theo
    source id, TTL SCP_HEALTH_NEG_CACHE_TTL (default 60s). Ping thật chạy lại
    sau TTL; kết quả cached (kể cả False) là quan sát thực tế gần nhất —
    KHÔNG fake health (fail-closed giữ nguyên: ping thất bại → False).

Regression contract (FA-13 coverage matrix cho nhánh nhân quả mới):
  1. Hai lần gọi trong TTL → transport được dùng ĐÚNG 1 lần, honest False
     cả hai lần (spy trên transport).
  2. Sau TTL expiry (monkeypatch time) → re-ping thật.
  3. Instance MỚI (cross-instance) vẫn hit cache — đây là regression gốc.
  4. TTL env override: SCP_HEALTH_NEG_CACHE_TTL=0 → re-ping mỗi lần.
  5. Mỗi source có cache entry ĐỘC LẬP (không dính chéo).
  6. reachability_ping: HTTPError (= ĐÃ nhận HTTP response) → sống;
     transport exception → False.
  7. ping() raise → False fail-closed (không propagate).
  8. Source key-gated không có API key → False KHÔNG ping (fail-closed).
"""
import threading
import types
import urllib.error
from importlib import import_module

import pytest

from scp.data_sources.noaa import NOAADataSource
from scp.data_sources.weather import WeatherDataSource
from scp.interfaces.data_source import (
    health_neg_cache_ttl,
    reset_shared_health_cache,
    shared_health_ping,
)
from scp.security import url_safety

health_iface = import_module("scp.interfaces.data_source")


@pytest.fixture(autouse=True)
def _isolated_shared_cache(monkeypatch):
    """Mỗi test bắt đầu/tắt với shared cache RỖNG — kết quả một test không
    được phép định đoạt kết quả test khác (test isolation, FA-01)."""
    reset_shared_health_cache()
    yield
    reset_shared_health_cache()


class _FakeResponse:
    """Context manager giả lập HTTP 200 của safe_urlopen."""

    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _transport_spy(monkeypatch, outcome="refused"):
    """Spy trên transport: đếm số lần safe_urlopen được gọi thật sự.

    outcome: 'ok' → response 200; 'refused' → URLError (transport fail);
    'http_error' → HTTPError 401 (ĐÃ nhận HTTP response)."""
    calls: list[str] = []

    def _fake(url, *args, **kwargs):
        calls.append(str(getattr(url, "full_url", url)))
        if outcome == "ok":
            return _FakeResponse()
        if outcome == "http_error":
            raise urllib.error.HTTPError(
                str(url), 401, "Unauthorized", hdrs=None, fp=None
            )
        raise urllib.error.URLError("connection refused (test)")

    monkeypatch.setattr(url_safety, "safe_urlopen", _fake)
    return calls


# ---------------------------------------------------------------------------
# 1 + 3 — hai lần gọi trong TTL: ping đúng 1 lần, honest False cả hai;
# cross-instance: instance MỚI vẫn hit cache (regression gốc V104.32).
# ---------------------------------------------------------------------------
def test_two_calls_within_ttl_ping_once_honest_false_both(monkeypatch):
    calls = _transport_spy(monkeypatch, outcome="refused")
    first = WeatherDataSource().health_check()
    second = WeatherDataSource().health_check()  # instance MỚI, cùng source id
    assert first is False, "transport refused phải honest False (fail-closed)"
    assert second is False, "cached negative phải giữ nguyên tín hiệu honest"
    assert len(calls) == 1, (
        f"hai lần gọi trong TTL phải chỉ ping 1 lần, thấy {len(calls)} ping — "
        "per-instance cache regression tái phát"
    )


def test_fresh_instance_hits_shared_cache_within_ttl(monkeypatch):
    calls = _transport_spy(monkeypatch, outcome="refused")
    assert WeatherDataSource().health_check() is False
    assert len(calls) == 1
    # Instance hoàn toàn mới — per-instance cache rỗng, shared cache phải chặn re-ping.
    fresh = WeatherDataSource()
    assert "_health_cache" not in fresh._cache, (
        "precondition: instance mới chưa từng thấy ping trong per-instance cache"
    )
    assert fresh.health_check() is False
    assert len(calls) == 1, "shared cache phải dedupe CROSS-INSTANCE trong TTL"


# ---------------------------------------------------------------------------
# 2 — sau TTL expiry: re-ping thật (monkeypatch clock của health module).
# ---------------------------------------------------------------------------
def test_ping_reruns_after_ttl_expiry(monkeypatch):
    calls = _transport_spy(monkeypatch, outcome="refused")
    clock = [1000.0]
    monkeypatch.setattr(
        health_iface, "time", types.SimpleNamespace(time=lambda: clock[0])
    )
    assert WeatherDataSource().health_check() is False
    assert len(calls) == 1

    clock[0] = 1030.0  # +30s < TTL 60s → vẫn cached
    assert WeatherDataSource().health_check() is False
    assert len(calls) == 1, "trong TTL không được re-ping"

    clock[0] = 1061.0  # +61s > TTL 60s → ping thật phải chạy lại
    assert WeatherDataSource().health_check() is False
    assert len(calls) == 2, "sau TTL expiry phải re-ping thật (không cache vĩnh viễn)"


def test_success_result_shared_and_honest(monkeypatch):
    """Ping 200 → True; lần 2 trong TTL không re-ping; sau TTL re-ping."""
    calls = _transport_spy(monkeypatch, outcome="ok")
    clock = [2000.0]
    monkeypatch.setattr(
        health_iface, "time", types.SimpleNamespace(time=lambda: clock[0])
    )
    assert WeatherDataSource().health_check() is True
    assert WeatherDataSource().health_check() is True
    assert len(calls) == 1
    clock[0] = 2061.0
    assert WeatherDataSource().health_check() is True
    assert len(calls) == 2


# ---------------------------------------------------------------------------
# 4 — TTL env override, đọc MỖI LẦN GỌI.
# ---------------------------------------------------------------------------
def test_ttl_env_zero_disables_cache(monkeypatch):
    calls = _transport_spy(monkeypatch, outcome="refused")
    monkeypatch.setenv("SCP_HEALTH_NEG_CACHE_TTL", "0")
    assert health_neg_cache_ttl() == 0.0
    assert WeatherDataSource().health_check() is False
    assert WeatherDataSource().health_check() is False
    assert len(calls) == 2, "TTL=0 phải tắt cache — mỗi lần gọi ping thật"


def test_ttl_env_override_extends_window(monkeypatch):
    calls = _transport_spy(monkeypatch, outcome="refused")
    clock = [3000.0]
    monkeypatch.setattr(
        health_iface, "time", types.SimpleNamespace(time=lambda: clock[0])
    )
    monkeypatch.setenv("SCP_HEALTH_NEG_CACHE_TTL", "120")
    assert WeatherDataSource().health_check() is False
    clock[0] = 3100.0  # +100s: vượt default 60 nhưng dưới TTL override 120
    assert WeatherDataSource().health_check() is False
    assert len(calls) == 1, "env override TTL phải có hiệu lực thật"


def test_ttl_env_invalid_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("SCP_HEALTH_NEG_CACHE_TTL", "khong-phai-so")
    assert health_neg_cache_ttl() == 60.0, (
        "env rác phải fallback default 60 (không crash, không 0)"
    )


# ---------------------------------------------------------------------------
# 5 — cache entry độc lập per source.
# ---------------------------------------------------------------------------
def test_sources_have_independent_cache_entries(monkeypatch):
    calls = _transport_spy(monkeypatch, outcome="refused")
    # Hai source public 1-endpoint: weather + usgs (đều qua reachability_ping).
    from scp.data_sources.usgs import USGSDataSource

    assert WeatherDataSource().health_check() is False
    assert USGSDataSource().health_check() is False  # source khác, chưa ping
    assert len(calls) == 2, "source khác phải ping riêng — không dính chéo cache"


# ---------------------------------------------------------------------------
# 6 — reachability_ping semantics: HTTP response nào cũng = sống.
# ---------------------------------------------------------------------------
def test_reachability_ping_http_error_means_alive(monkeypatch):
    _transport_spy(monkeypatch, outcome="http_error")
    assert health_iface.reachability_ping("https://example.test/x") is True, (
        "HTTPError = đã nhận HTTP response → endpoint sống"
    )


def test_reachability_ping_transport_exception_false(monkeypatch):
    _transport_spy(monkeypatch, outcome="refused")
    assert health_iface.reachability_ping("https://example.test/x") is False


def test_ping_exception_is_fail_closed_not_raised(monkeypatch):
    """ping() raise (bug/transport) → False, không propagate, được cache."""
    assert shared_health_ping("T-raising", lambda: 1 / 0) is False
    assert shared_health_ping("T-raising", lambda: pytest.fail("không được gọi lại")) is False


def test_reset_shared_health_cache_forces_reping(monkeypatch):
    calls = _transport_spy(monkeypatch, outcome="refused")
    assert WeatherDataSource().health_check() is False
    reset_shared_health_cache()
    assert WeatherDataSource().health_check() is False
    assert len(calls) == 2, "reset cache phải buộc re-ping thật"


def test_shared_cache_is_thread_safe(monkeypatch):
    """Nhiều thread gọi cùng lúc: không crash, không deadlock, kết quả honest."""
    _transport_spy(monkeypatch, outcome="refused")
    results: list[bool] = []
    lock = threading.Lock()

    def worker():
        r = WeatherDataSource().health_check()
        with lock:
            results.append(r)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert results == [False] * 8


# ---------------------------------------------------------------------------
# 8 — key-gated source không có API key: False ngay, KHÔNG tốn ping.
# ---------------------------------------------------------------------------
def test_gated_source_without_api_key_fails_closed_without_ping(monkeypatch):
    monkeypatch.delenv("NOAA_API_KEY", raising=False)
    calls = _transport_spy(monkeypatch, outcome="ok")
    source = NOAADataSource()
    if source.enabled:
        pytest.fail("test giả định NOAA không có key; môi trường đang có key")
    assert source.health_check() is False, "không có key → không thể serve — False"
    assert calls == [], "không có key thì KHÔNG được tốn network ping"


def test_converted_public_source_true_when_reachable(monkeypatch):
    """Source đã convert (weather, public) ping 200 → True — kết quả do live
    ping chi phối, không phải hardcode (FA-04: no manufactured VERIFIED)."""
    calls = _transport_spy(monkeypatch, outcome="ok")
    assert WeatherDataSource().health_check() is True
    assert calls, "phải có ping thật xảy ra"
