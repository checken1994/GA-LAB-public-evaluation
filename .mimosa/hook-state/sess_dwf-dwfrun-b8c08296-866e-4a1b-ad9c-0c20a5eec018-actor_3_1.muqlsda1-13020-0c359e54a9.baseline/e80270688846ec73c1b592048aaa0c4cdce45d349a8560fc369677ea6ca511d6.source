"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

"""
GeographyDataSource - Data source cho Địa lý
"""
import json
import logging
import urllib.parse
import urllib.request
from typing import Any

from scp.interfaces.data_source import IDataSource, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger(__name__)

# [AUDIT-20260909 SSRF-S1] Host cố định cho REST Countries fetch.
_RESTCOUNTRIES_BASE = "https://restcountries.com/v3.1/name"


def build_restcountries_url(entity: str) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — entity (input động) được
    quote(safe='') → '/', '..', '?', '&' bị encode, không thể đổi host hay
    thêm path segment. Host cố định restcountries.com."""
    quoted = urllib.parse.quote(str(entity or ""), safe="")
    return f"{_RESTCOUNTRIES_BASE}/{quoted}"


class GeographyDataSource(IDataSource):
    """
    Data source cho các câu hỏi Địa lý.
    Hỗ trợ: dân số, diện tích, thủ đô, tọa độ.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Local database for common geography data (fallback)
        self._local_data = {
            # Countries - Capital
            'việt nam': {'capital': 'Hà Nội', 'population': 97000000, 'area': 331212},
            'vietnam': {'capital': 'Hanoi', 'population': 97000000, 'area': 331212},
            'hanoi': {'capital': 'Hà Nội', 'population': 8000000, 'area': 0},
            'tp hcm': {'capital': 'Hồ Chí Minh', 'population': 9000000, 'area': 0},
            'ho chi minh': {'capital': 'Hồ Chí Minh', 'population': 9000000, 'area': 0},
            'thành phố hồ chí minh': {'capital': 'Hồ Chí Minh', 'population': 9000000, 'area': 0},

            # Major cities
            'paris': {'capital': 'Paris', 'population': 2161000, 'area': 105},
            'london': {'capital': 'London', 'population': 8982000, 'area': 1572},
            'tokyo': {'capital': 'Tokyo', 'population': 13960000, 'area': 2194},
            'new york': {'capital': 'Washington D.C.', 'population': 8336817, 'area': 783},
            'sydney': {'capital': 'Canberra', 'population': 5312000, 'area': 12368},
            'berlin': {'capital': 'Berlin', 'population': 3644826, 'area': 892},
            'moscow': {'capital': 'Moscow', 'population': 11920000, 'area': 2561},
            'beijing': {'capital': 'Beijing', 'population': 21540000, 'area': 16411},
            'singapore': {'capital': 'Singapore', 'population': 5450000, 'area': 733},
            'dubai': {'capital': 'Abu Dhabi', 'population': 3331000, 'area': 1287},

            # Countries
            'usa': {'capital': 'Washington D.C.', 'population': 331000000, 'area': 9833520},
            'united states': {'capital': 'Washington D.C.', 'population': 331000000, 'area': 9833520},
            'uk': {'capital': 'London', 'population': 67330000, 'area': 242495},
            'united kingdom': {'capital': 'London', 'population': 67330000, 'area': 242495},
            'japan': {'capital': 'Tokyo', 'population': 125800000, 'area': 377975},
            'france': {'capital': 'Paris', 'population': 67750000, 'area': 640679},
            'germany': {'capital': 'Berlin', 'population': 83240000, 'area': 357022},
            'australia': {'capital': 'Canberra', 'population': 25980000, 'area': 7692024},
            'china': {'capital': 'Beijing', 'population': 1412000000, 'area': 9596961},
            'russia': {'capital': 'Moscow', 'population': 144100000, 'area': 17098242},
            'india': {'capital': 'New Delhi', 'population': 1380000000, 'area': 3287263},
            'brazil': {'capital': 'Brasília', 'population': 212600000, 'area': 8515767},
        }

    @property
    def name(self) -> str:
        return "GeographyDataSource"

    @property
    def priority(self) -> int:
        return 2  # Medium priority

    @property
    def ttl(self) -> int:
        return 86400  # 1 day - geography data changes slowly

    def get_supported_intents(self) -> list[str]:
        return [
            'population',
            'capital',
            'area',
            'coordinates',
            'country_info',
            'city_info',
        ]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            entity_lower = entity.lower()
            return entity_lower in self._local_data
        return False

    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        """Lấy dữ liệu địa lý."""
        if not entity:
            return None

        entity_lower = entity.lower()

        # [V104.31 #5] Unsupported intent → None (was: silent fallback to capital)
        supported = set(self.get_supported_intents())
        if intent not in supported:
            return None

        # Try local database first
        if entity_lower in self._local_data:
            data = self._local_data[entity_lower]
            if intent not in data:
                pass  # fall through to API
            else:
                value = data.get(intent)
                # [V104.25 #7] area/population == 0 → None sentinel
                if intent in ('area', 'population') and (value == 0 or value is None):
                    return None
                return {
                    'value': value,
                    'source': 'Local Geography Database',
                    'metadata': data
                }

        # Try to fetch from REST Countries API
        result = self._fetch_from_api(entity_lower, intent)
        if result:
            return result

        return None

    def _fetch_from_api(self, entity: str, intent: str = 'capital') -> dict[str, Any] | None:
        """Fallback: Lấy từ REST Countries API."""
        # [V104.31 #1] Map intent → field (was: always returns capital)
        INTENT_TO_FIELD = {
            'capital': 'capital', 'population': 'population', 'area': 'area',
            'country_info': 'region', 'city_info': 'capital',
        }
        target_field = INTENT_TO_FIELD.get(intent)
        if target_field is None:
            return None

        try:
            # [AUDIT-20260909 SSRF-S1] entity (input động) được quote(safe='')
            # TRƯỚC khi vào URL path → không thể đổi host hay thêm path segment.
            url = build_restcountries_url(entity)
            req = urllib.request.Request(
                url, headers={"User-Agent": "SCP-Geography/1.0"}
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=5) as response:
                if getattr(response, "status", 200) != 200:
                    return None
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            if data:
                country = data[0]
                capital_val = country.get('capital', [''])[0] if country.get('capital') else ''
                population_val = country.get('population', 0) or 0
                area_val = country.get('area', 0) or 0
                region_val = country.get('region', '')

                if target_field == 'capital':
                    value = capital_val
                elif target_field == 'population':
                    value = population_val if population_val > 0 else None
                elif target_field == 'area':
                    value = area_val if area_val > 0 else None
                elif target_field == 'region':
                    value = region_val if region_val else None
                else:
                    value = None

                return {
                    'value': value,
                    'source': 'REST Countries API',
                    'metadata': {
                        'population': population_val if population_val > 0 else None,
                        'area': area_val if area_val > 0 else None,
                        'capital': capital_val,
                        'region': region_val,
                    }
                }
        except Exception as e:
            logger.warning(f"[Geography] API fetch failed: {e}", exc_info=True)
        return None

    def health_check(self) -> bool:
        """[V104.31 #4] Real ping — REST Countries API.

        [V104.32] Kết quả ping đi qua shared negative-result cache
        cross-instance (`shared_health_ping`): trong TTL
        (SCP_HEALTH_NEG_CACHE_TTL, default 60s) các lần gọi sau trả lại quan
        sát gần nhất — kể cả False (đó là reality gần nhất, không fake health)
        — mà KHÔNG re-ping."""
        import time
        healthy = shared_health_ping(type(self).__name__, self._live_ping)
        self._cache['_health_cache'] = healthy
        self._cache['_health_cache_ts'] = time.time()
        return healthy

    def _live_ping(self) -> bool:
        """[V104.32] Ping thật (1 network round-trip) — chỉ gọi qua
        shared_health_ping để được dedupe theo TTL."""
        api_ok = False
        try:
            # [AUDIT-20260909 SSRF-S1] safe_urlopen cho health ping (URL cố định).
            req = urllib.request.Request(
                "https://restcountries.com/v3.1/name/vietnam?fields=capital",
                headers={"User-Agent": "SCP-Geography/1.0"},
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=3) as response:
                api_ok = getattr(response, "status", 200) == 200
        except Exception:
            logger.warning('GeographyDataSource.health_check: Exception not handled', exc_info=True)
            api_ok = False
        # [AUDIT-FIX low-4] Fail-closed: health = tín hiệu live ping THẬT, KHÔNG
        # OR với dict local (từng là `api_ok or bool(self._local_data)` → luôn
        # True kể cả khi egress denied). Local data vẫn trả lời được query
        # nhưng là trạng thái DEGRADED — báo qua log, không báo healthy.
        healthy = api_ok
        if not api_ok and bool(self._local_data):
            logger.warning(
                "[Geography] health_check: live API ping failed; local dataset "
                "vẫn có (degraded) — báo unhealthy theo contract fail-closed"
            )
        return healthy
