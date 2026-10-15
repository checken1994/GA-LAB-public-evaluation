"""[AUDIT-FIX low-4 + info-5] Contract test — data_sources health fail-closed.

Root cause (external audit low-4, probe PROVED):
  * finance.py: `healthy = api_ok or bool(self._currencies)` → True kể cả khi
    MỌI egress bị deny (dict local hardcode luôn non-empty).
  * geography.py: cùng shape với self._local_data.
  * agriculture/biology/cybersecurity/astronomy: hardcode `return True`.
Fix: health_check trả tín hiệu live ping THẬT (`api_ok`); dữ liệu local/cache
chỉ là trạng thái degraded (báo qua log), KHÔNG OR vào kết quả.

Regression contract: SCP_EGRESS_MODE=deny → health_check() is False cho cả 6
nguồn; khi endpoint giả lập reachable → True (ping thật sự chi phối kết quả).
"""
import pytest

from scp.data_sources.agriculture import AgricultureDataSource
from scp.data_sources.astronomy import AstronomyDataSource
from scp.data_sources.biology import BiologyDataSource
from scp.data_sources.cybersecurity import CybersecurityDataSource
from scp.data_sources.finance import FinanceDataSource
from scp.data_sources.geography import GeographyDataSource
from scp.security import url_safety

SOURCES = [
    FinanceDataSource,
    GeographyDataSource,
    AgricultureDataSource,
    BiologyDataSource,
    CybersecurityDataSource,
    AstronomyDataSource,
]


class _FakeResponse:
    """Context manager giả lập response 200 của safe_urlopen."""

    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _fresh(source_cls):
    """Instance mới — tránh dính health cache 60s của instance khác."""
    return source_cls()


@pytest.fixture(autouse=True)
def _reset_shared_health_cache():
    """[V104.32] health pings giờ dùng SHARED cross-instance cache
    (scp.interfaces.data_source._SHARED_HEALTH_CACHE): `_fresh()` một mình
    không còn cách ly kết quả giữa các test nữa. Fixture này chỉ XOÁ CACHE giữa
    các test để mỗi test tự chứng minh bằng live ping của nó — KHÔNG đổi bất
    kỳ assertion nào (vẫn False-under-deny, True-under-reachable)."""
    from scp.interfaces.data_source import reset_shared_health_cache

    reset_shared_health_cache()
    yield
    reset_shared_health_cache()


@pytest.mark.parametrize("source_cls", SOURCES)
def test_health_check_is_false_when_egress_denied(source_cls, monkeypatch):
    """Egress deny → safe_urlopen raise → health_check phải False (fail-closed)."""
    monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
    assert _fresh(source_cls).health_check() is False


@pytest.mark.parametrize("source_cls", SOURCES)
def test_health_check_true_when_ping_reachable(source_cls, monkeypatch):
    """Ping giả lập 200 → True; chứng minh kết quả do live ping chi phối,
    không phải hardcode."""
    monkeypatch.setattr(url_safety, "safe_urlopen", lambda *a, **k: _FakeResponse())
    # finance/geography/biology import safe_urlopen ở module-top → patch cả
    # binding local của từng module (agriculture/cyber/astronomy import lười
    # trong hàm → binding url_safety ở trên là đủ).
    for module in (
        "scp.data_sources.finance",
        "scp.data_sources.geography",
        "scp.data_sources.biology",
    ):
        import importlib

        mod = importlib.import_module(module)
        monkeypatch.setattr(mod, "safe_urlopen", lambda *a, **k: _FakeResponse())
    assert _fresh(source_cls).health_check() is True


@pytest.mark.parametrize("source_cls", SOURCES)
def test_health_check_result_is_cached_60s(source_cls, monkeypatch):
    """Kết quả health được cache 60s trong self._cache (consistency với
    finance/geography pattern cũ)."""
    monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
    source = _fresh(source_cls)
    first = source.health_check()
    assert first is False
    assert source._cache.get("_health_cache") is False


# ---------------------------------------------------------------------------
# [AUDIT-FIX info-5] chemistry typo key 'ph的中性' → 'ph trung tính'
# ---------------------------------------------------------------------------
def test_chemistry_ph_trung_tinh_exact_key_lookup():
    from scp.data_sources.chemistry import ChemistryDataSource

    ds = ChemistryDataSource()
    result = ds.fetch("lookup", "pH trung tính")
    assert result is not None, "lookup pH trung tính phải hit exact key"
    assert result.get("value") == 7.0
    assert result.get("metadata", {}).get("constant_name") == "ph trung tính"


def test_chemistry_old_typo_key_removed():
    from scp.data_sources.chemistry import ChemistryDataSource

    ds = ChemistryDataSource()
    assert "ph的中性" not in ds._constants
