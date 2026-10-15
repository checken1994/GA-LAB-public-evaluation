import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from urllib.parse import urlparse

from scp.data_sources.free_api_catalog import (
    ALLOWED_HOSTS,
    CATALOG_SOURCE_URL,
    FreeAPICatalog,
)

# Canonical 5-column public-apis README shape (first table keeps the leading
# pipe, later tables drop it — both shapes are accepted by parse_catalog_md).
_SAMPLE_CATALOG_MD = """\
# Public APIs

### Weather

| API | Description | Auth | HTTPS | CORS |
| [Open-Meteo](https://open-meteo.com/) | Global weather forecast without a key | No | Yes | Yes |
| [Visual Crossing Weather](https://www.visualcrossing.com/) | Historical and forecast weather data | Yes | Yes | Yes |

### Machine Learning

API | Description | Auth | HTTPS | CORS |
| [Clarifai](https://www.clarifai.com/) | Computer vision and LLM APIs | Yes | Yes | Yes |
"""


def test_subsystem_data_sources_importable(tmp_path):
    """Free API catalog: verify durable cache, catalog entries, and search indexing.

    Hermetic (không mạng, không đụng ``data/`` của repo): cache
    ``data/free_api_catalog.json`` là artifact dev-machine (gitignored, không
    commit) — pre-RC run 36102606213 cho thấy test cũ phụ thuộc nó
    (``cached=False, count=0`` trên runner sạch). Transport inject + ``tmp_path``
    giữ nguyên chuỗi nhân quả thật của product: refresh → parse_catalog_md →
    durable cache → status → search. ``SCP_TOP_SYSTEMS_EGRESS=0`` (module-level
    setdefault) không ảnh hưởng: transport inject không đi qua ``_http_get``.
    """
    fetched_urls = []

    def transport(url: str) -> bytes:
        fetched_urls.append(url)
        return _SAMPLE_CATALOG_MD.encode("utf-8")

    cat = FreeAPICatalog(data_dir=str(tmp_path), transport=transport)
    refreshed = cat.refresh(force=True)
    assert refreshed["ok"] is True, f"catalog refresh failed: {refreshed}"
    # SSRF-by-construction: catalog chỉ được fetch đúng host allowlisted cố định
    assert fetched_urls == [CATALOG_SOURCE_URL]
    assert urlparse(CATALOG_SOURCE_URL).hostname in ALLOWED_HOSTS

    status = cat.status()
    assert isinstance(status, dict)
    assert status.get("cached") is True
    assert status.get("count", 0) > 0

    # Functional search
    results = cat.search("weather")
    assert isinstance(results, list)
    assert len(results) > 0
    assert "name" in results[0]
    assert "url" in results[0]
    assert "category" in results[0]

    # Durable cache: một instance mới trên cùng data_dir phải phục vụ từ cache
    # (không được chạm mạng nữa — transport fail-loud nếu bị gọi).
    def _network_must_not_be_used(url: str) -> bytes:
        raise RuntimeError("catalog must be served from durable cache on reopen")

    reopened = FreeAPICatalog(data_dir=str(tmp_path), transport=_network_must_not_be_used)
    res_reopened = reopened.refresh()
    assert res_reopened["ok"] is True
    assert res_reopened["served"] == "cache_fresh"
    assert reopened.status()["cached"] is True
    assert reopened.status()["count"] > 0
