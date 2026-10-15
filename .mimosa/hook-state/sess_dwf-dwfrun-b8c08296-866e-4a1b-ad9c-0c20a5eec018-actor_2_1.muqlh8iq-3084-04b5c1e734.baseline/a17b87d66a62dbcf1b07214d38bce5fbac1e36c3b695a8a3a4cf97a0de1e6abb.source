"""
[OPT-17] NOAADataSource — NOAA NCDC Climate Data Online (CDO) API.

DNA SCP: SuperGPQA Earth Science discipline had no primary weather/climate
DataSource (only generic weather.py). NOAA's CDO API is the authoritative
source for US weather history, climate normals, and severe weather events.
Requires NOAA_API_KEY (free token at https://www.ncdc.noaa.gov/cdo-web/token).
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.noaa")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builder.
_NOAA_DATA_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2/data"


def build_noaa_data_url(params: dict) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — mọi param (datasetid,
    startdate, enddate, locationid...) được urlencode; host cố định
    www.ncdc.noaa.gov. locationid chỉ nhận CDO location format `FIPS:nn`
    hoặc `CITY:...` từ LOCATION_MAP nội bộ."""
    clean = {str(k): v for k, v in (params or {}).items()}
    return _NOAA_DATA_URL + "?" + urllib.parse.urlencode(clean)


class NOAADataSource(IDataSource):
    """NOAA NCDC CDO API — weather & climate data (requires NOAA_API_KEY)."""

    BASE_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
    TOKEN_URL = "https://www.ncdc.noaa.gov/cdo-web/token"  # noqa: S105,S106  # nosec B105 — URL path contains word "token", not a credential

    # Common dataset IDs
    DATASET_MAP = {
        "ghcn": "GHCND",          # Daily summaries (stations worldwide)
        "daily": "GHCND",
        "normals": "NORMAL_DLY",  # Climate normals daily
        "climate normals": "NORMAL_DLY",
        "precipitation": "GHCND",
        "temperature": "GHCND",
    }

    # Location ID prefixes
    LOCATION_MAP = {
        "usa": "FIPS:US",
        "us": "FIPS:US",
        "new york": "CITY:US360019",
        "los angeles": "CITY:US060037",
        "chicago": "CITY:US1714000",
        "houston": "CITY:US4823000",
        "phoenix": "CITY:US0450000",
        "seattle": "CITY:US5300160",
    }

    def __init__(self):
        self.api_key = os.environ.get("NOAA_API_KEY", "")
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.info("[NOAA] disabled — set NOAA_API_KEY (free token at "
                        f"{self.TOKEN_URL}) to enable")

    @property
    def name(self) -> str:
        return "noaa"

    @property
    def priority(self) -> int:
        return 12  # mid — earth_science primary when enabled

    @property
    def ttl(self) -> int:
        return 3600  # 1h — weather changes frequently

    def get_supported_intents(self) -> list[str]:
        return ["weather", "climate", "temperature", "precipitation",
                "weather_history", "climate_normals", "earth_science"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        question = intent or ""
        q = question.lower()
        keywords = [
            "weather", "thời tiết",
            "climate", "khí hậu",
            "temperature", "nhiệt độ",
            "precipitation", "lượng mưa",
            "rainfall", "snowfall",
            "humidity", "độ ẩm",
            "wind speed", "tốc độ gió",
            "noaa", "ncdc",
            "climate normal", "chuẩn khí hậu",
            "storm", "bão",
            "drought", "hạn hán",
        ]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (www.ncdc.noaa.gov). Trước đây hardcode `return self.enabled`
        — constructor config, không phải live evidence (fail-open). Không có API key → False ngay (không thể serve — fail-closed); có key
        → reachability ping. Bất kỳ HTTP
        response nào (kể cả 4xx do thiếu key/tham số) chứng minh service
        sống; exception (egress denied, DNS, timeout) → False.

        Kết quả đi qua shared negative-result cache cross-instance
        (`shared_health_ping`): trong TTL (SCP_HEALTH_NEG_CACHE_TTL,
        default 60s) các lần gọi sau trả lại quan sát gần nhất — kể cả
        False (đó là reality gần nhất, không fake health) — mà KHÔNG
        re-ping."""
        if not self.enabled:
            # Không có API key → source không thể serve — fail-closed, không ping.
            return False
        return shared_health_ping(type(self).__name__, self._live_ping)

    def _live_ping(self) -> bool:
        """[V104.32] Ping thật — 1 network round-trip tới URL cố định,
        không chứa key; HTTP response nào cũng = endpoint sống."""
        return reachability_ping('https://www.ncdc.noaa.gov/cdo-web/api/v2/data')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            return self._query_data(question)
        except Exception as e:
            logger.debug(f"[NOAA] query failed: {e}", exc_info=True)
            return None

    def _query_data(self, question: str) -> dict | None:
        try:
            q = question.lower()
            # Pick dataset
            dataset = "GHCND"
            for keyword, ds in self.DATASET_MAP.items():
                if keyword in q:
                    dataset = ds
                    break
            # Pick location
            location_id = None
            for name, loc_id in self.LOCATION_MAP.items():
                if name in q:
                    location_id = loc_id
                    break
            params = {
                "datasetid": dataset,
                "startdate": "2024-01-01",
                "enddate": "2024-01-07",
                "limit": 5,
                "units": "metric",
            }
            if location_id:
                params["locationid"] = location_id
            # [AUDIT-20260909 SSRF-S1] builder urlencode + safe_urlopen thay
            # raw httpx.get; non-200 → HTTPError.
            req = urllib.request.Request(
                build_noaa_data_url(params),
                headers={"token": self.api_key},
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            results = data.get("results", [])
            if not results:
                return None
            # Summarize top results
            return {
                "value": f"{len(results)} observations",
                "source": "noaa",
                "metadata": {
                    "dataset": dataset,
                    "location": location_id or "global",
                    "results": [
                        {
                            "date": r.get("date", ""),
                            "datatype": r.get("datatype", ""),
                            "station": r.get("station", ""),
                            "value": r.get("value", ""),
                        } for r in results[:3]
                    ],
                    "result_count": data.get("metadata", {}).get("resultset", {}).get("count", 0),
                },
            }
        except Exception as e:
            logger.debug(f"[NOAA] data query failed: {e}", exc_info=True)
            return None
