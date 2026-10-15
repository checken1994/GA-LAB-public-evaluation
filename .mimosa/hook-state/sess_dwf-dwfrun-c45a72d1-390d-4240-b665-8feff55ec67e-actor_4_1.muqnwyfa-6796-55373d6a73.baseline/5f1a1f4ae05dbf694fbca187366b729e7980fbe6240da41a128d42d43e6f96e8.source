"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.

WHY Engine, Recursive Why, MetaFalsifier, ProofGraph
License: See LICENSE file
"""

"""
WeatherDataSource - Data source cho Thời tiết & Khí hậu
Bao gồm: local climate data + API fallbacks (Open-Meteo, OpenWeatherMap).
"""
import json
import logging
import math
import urllib.parse
import urllib.request
from typing import Any

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger(__name__)

# [AUDIT-20260909 SSRF-S1] Host cố định cho Open-Meteo fetch.
_OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def build_open_meteo_url(lat: float, lon: float) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — lat/lon PHẢI là số hữu hạn
    (float) và được urlencode vào query. Input xấu → ValueError TRƯỚC KHI
    fetch. Host cố định api.open-meteo.com."""
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        raise ValueError(f"invalid_coordinates:{lat!r},{lon!r}")
    if not (math.isfinite(lat_f) and math.isfinite(lon_f)):
        raise ValueError(f"non_finite_coordinates:{lat!r},{lon!r}")
    query = urllib.parse.urlencode({
        "latitude": lat_f,
        "longitude": lon_f,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
    })
    return f"{_OPEN_METEO_FORECAST_URL}?{query}"


class WeatherDataSource(IDataSource):
    """Data source cho các câu hỏi thời tiết."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Major Vietnamese cities - lat/lon for API calls
        self._cities = {
            'hà nội': {'lat': 21.0285, 'lon': 105.8542, 'country': 'VN'},
            'hanoi': {'lat': 21.0285, 'lon': 105.8542, 'country': 'VN'},
            'hồ chí minh': {'lat': 10.8231, 'lon': 106.6297, 'country': 'VN'},
            'ho chi minh': {'lat': 10.8231, 'lon': 106.6297, 'country': 'VN'},
            'sài gòn': {'lat': 10.8231, 'lon': 106.6297, 'country': 'VN'},
            'saigon': {'lat': 10.8231, 'lon': 106.6297, 'country': 'VN'},
            'đà nẵng': {'lat': 16.0544, 'lon': 108.2022, 'country': 'VN'},
            'da nang': {'lat': 16.0544, 'lon': 108.2022, 'country': 'VN'},
            'hải phòng': {'lat': 20.8449, 'lon': 106.6881, 'country': 'VN'},
            'cần thơ': {'lat': 10.0452, 'lon': 105.7469, 'country': 'VN'},
            'huế': {'lat': 16.4637, 'lon': 107.5909, 'country': 'VN'},
            'nha trang': {'lat': 12.2388, 'lon': 109.1967, 'country': 'VN'},
            'đà lạt': {'lat': 11.9404, 'lon': 108.4583, 'country': 'VN'},
            'vũng tàu': {'lat': 10.9827, 'lon': 107.0831, 'country': 'VN'},
            'quy nhơn': {'lat': 13.7820, 'lon': 109.2193, 'country': 'VN'},
            # International
            'tokyo': {'lat': 35.6762, 'lon': 139.6503, 'country': 'JP'},
            'new york': {'lat': 40.7128, 'lon': -74.0060, 'country': 'US'},
            'london': {'lat': 51.5074, 'lon': -0.1278, 'country': 'UK'},
            'paris': {'lat': 48.8566, 'lon': 2.3522, 'country': 'FR'},
            'singapore': {'lat': 1.3521, 'lon': 103.8198, 'country': 'SG'},
            'beijing': {'lat': 39.9042, 'lon': 116.4074, 'country': 'CN'},
            'sydney': {'lat': -33.8688, 'lon': 151.2093, 'country': 'AU'},
            'moscow': {'lat': 55.7558, 'lon': 37.6173, 'country': 'RU'},
        }

        # Climate normals (long-term averages)
        self._climate_normals = {
            'hà nội': {'annual_temp_c': 23.6, 'annual_rain_mm': 1676, 'humidity_avg': 79},
            'hồ chí minh': {'annual_temp_c': 27.0, 'annual_rain_mm': 1949, 'humidity_avg': 79},
            'đà nẵng': {'annual_temp_c': 25.5, 'annual_rain_mm': 2505, 'humidity_avg': 83},
            'tokyo': {'annual_temp_c': 15.4, 'annual_rain_mm': 1529, 'humidity_avg': 65},
            'london': {'annual_temp_c': 11.3, 'annual_rain_mm': 601, 'humidity_avg': 75},
            'new york': {'annual_temp_c': 12.7, 'annual_rain_mm': 1199, 'humidity_avg': 64},
        }

        # Beaufort scale
        self._beaufort = {
            0: {'name': 'Calm', 'vi_name': 'Lặng gió', 'wind_kmh': '< 1'},
            1: {'name': 'Light air', 'vi_name': 'Gió nhẹ', 'wind_kmh': '1-5'},
            2: {'name': 'Light breeze', 'vi_name': 'Hơi thổi', 'wind_kmh': '6-11'},
            3: {'name': 'Gentle breeze', 'vi_name': 'Gió dịu', 'wind_kmh': '12-19'},
            4: {'name': 'Moderate breeze', 'vi_name': 'Gió vừa', 'wind_kmh': '20-28'},
            5: {'name': 'Fresh breeze', 'vi_name': 'Gói tươi', 'wind_kmh': '29-38'},
            6: {'name': 'Strong breeze', 'vi_name': 'Gió mạnh', 'wind_kmh': '39-49'},
            7: {'name': 'High wind', 'vi_name': 'Gió cao', 'wind_kmh': '50-61'},
            8: {'name': 'Gale', 'vi_name': 'Gió bão', 'wind_kmh': '62-74'},
            9: {'name': 'Strong gale', 'vi_name': 'Bão mạnh', 'wind_kmh': '75-88'},
            10: {'name': 'Storm', 'vi_name': 'Bão', 'wind_kmh': '89-102'},
            11: {'name': 'Violent storm', 'vi_name': 'Bão dữ', 'wind_kmh': '103-117'},
            12: {'name': 'Hurricane', 'vi_name': 'Cuồng phong', 'wind_kmh': '> 117'},
        }

    @property
    def name(self) -> str:
        return "WeatherDataSource"

    @property
    def priority(self) -> int:
        return 2

    @property
    def ttl(self) -> int:
        return 600  # 10 minutes - weather changes frequently

    def get_supported_intents(self) -> list[str]:
        return [
            'current_weather',
            'forecast',
            'climate_normal',
            'beaufort_scale',
            'temperature',
            'humidity',
            'wind_speed',
        ]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            entity_lower = entity.lower().strip()
            if entity_lower in self._cities:
                return True
            if entity_lower in self._climate_normals:
                return True
            for key in list(self._cities.keys()) + list(self._climate_normals.keys()):
                if key in entity_lower or entity_lower in key:
                    return True
        return False

    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        if not entity:
            return None

        entity_lower = entity.lower().strip()

        # Beaufort
        if entity_lower.startswith('beaufort') and entity_lower.split()[-1].isdigit():
            b = int(entity_lower.split()[-1])
            if b in self._beaufort:
                data = self._beaufort[b]
                return {
                    'value': data['wind_kmh'],
                    'source': 'Beaufort Scale (Local)',
                    'metadata': data
                }

        # Climate normals
        if entity_lower in self._climate_normals:
            data = self._climate_normals[entity_lower]
            return {
                'value': data.get('annual_temp_c'),
                'source': 'Climate Normals (Local)',
                'metadata': data
            }

        # Live weather - try Open-Meteo (no API key required)
        city = self._cities.get(entity_lower)
        if not city:
            # Partial match
            for key, c in self._cities.items():
                if key in entity_lower or entity_lower in key:
                    city = c
                    break

        if city:
            result = self._fetch_from_open_meteo(city['lat'], city['lon'])
            if result:
                return result

        return None

    def _fetch_from_open_meteo(self, lat: float, lon: float) -> dict[str, Any] | None:
        """Lấy thời tiết hiện tại từ Open-Meteo."""
        try:
            # [AUDIT-20260909 SSRF-S1] URL build (encode + validate) tách khỏi
            # fetch; fetch qua safe_urlopen thay raw requests.get.
            url = build_open_meteo_url(lat, lon)
            req = urllib.request.Request(
                url, headers={"User-Agent": "SCP-Weather/1.0"}
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=8) as response:
                if getattr(response, "status", 200) != 200:
                    return None
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            cur = data.get('current', {})
            return {
                'value': cur.get('temperature_2m'),
                'source': 'Open-Meteo API',
                'metadata': {
                    'temperature_c': cur.get('temperature_2m'),
                    'humidity_pct': cur.get('relative_humidity_2m'),
                    'wind_speed_kmh': cur.get('wind_speed_10m'),
                    'weather_code': cur.get('weather_code'),
                    'method': 'open_meteo',
                }
            }
        except Exception as e:
            logger.warning(f"[Weather] Open-Meteo fetch failed: {e}", exc_info=True)
        return None

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (api.open-meteo.com). Trước đây hardcode `return True`
        — hardcode, không có live evidence (fail-open). Bất kỳ HTTP
        response nào (kể cả 4xx do thiếu key/tham số) chứng minh service
        sống; exception (egress denied, DNS, timeout) → False.

        Kết quả đi qua shared negative-result cache cross-instance
        (`shared_health_ping`): trong TTL (SCP_HEALTH_NEG_CACHE_TTL,
        default 60s) các lần gọi sau trả lại quan sát gần nhất — kể cả
        False (đó là reality gần nhất, không fake health) — mà KHÔNG
        re-ping."""
        return shared_health_ping(type(self).__name__, self._live_ping)

    def _live_ping(self) -> bool:
        """[V104.32] Ping thật — 1 network round-trip tới URL cố định,
        không chứa key; HTTP response nào cũng = endpoint sống."""
        return reachability_ping('https://api.open-meteo.com/v1/forecast?latitude=21.03&longitude=105.85&current_weather=true')
