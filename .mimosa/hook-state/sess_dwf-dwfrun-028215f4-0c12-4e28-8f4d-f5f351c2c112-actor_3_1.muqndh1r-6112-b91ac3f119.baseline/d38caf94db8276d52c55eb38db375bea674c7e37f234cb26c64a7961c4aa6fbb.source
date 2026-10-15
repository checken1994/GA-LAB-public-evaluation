"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

"""
AstronomyDataSource - Data source cho Thiên văn học
Bao gồm: Hệ Mặt Trời (8 hành tinh + Mặt Trời + Mặt Trăng + các vệ tinh),
         các ngôi sao, thiên hà, constellations, astronomical constants.
"""
import logging
from typing import Any

from scp.core.wikipedia_client import fetch_summary as _wiki_fetch_summary  # [G3-CONSOLIDATE RE-05]
from scp.data_sources._matching import _token_boundary_match
from scp.interfaces.data_source import IDataSource, shared_health_ping

logger = logging.getLogger(__name__)
# [V104.32 #5] word-boundary matching for short keys


class AstronomyDataSource(IDataSource):
    """
    Data source cho các câu hỏi Thiên văn.
    Hỗ trợ: hành tinh, sao, thiên hà, vệ tinh, hằng số thiên văn.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # ---------------- Astronomical constants ----------------
        self._constants = {
            # Cosmological
            'hằng số hubble': 67.4,  # km/s/Mpc (Planck 2018)
            'hubble constant': 67.4,
            'h0': 67.4,
            'nhiệt độ CMB': 2.7255,  # K
            'cmb temperature': 2.7255,
            'tCMB': 2.7255,
            'tuổi vũ trụ': 13.8e9,  # years
            'age of universe': 13.8e9,
            'hằng số vũ trụ học': 1.1056e-52,  # m^-2
            'cosmological constant': 1.1056e-52,
            'vật chất tối tỷ lệ': 0.268,  # fraction
            'dark matter fraction': 0.268,
            'năng lượng tối tỷ lệ': 0.683,
            'dark energy fraction': 0.683,

            # Solar
            'khối lượng mặt trời': 1.989e30,  # kg
            'solar mass': 1.989e30,
            'm_sun': 1.989e30,
            'bán kính mặt trời': 6.96e8,  # m
            'solar radius': 6.96e8,
            'r_sun': 6.96e8,
            'độ sáng mặt trời': 3.828e26,  # W
            'solar luminosity': 3.828e26,
            'l_sun': 3.828e26,
            'nhiệt độ mặt trời': 5778,  # K (surface)
            'solar surface temperature': 5778,
            't_eff_sun': 5778,

            # Earth
            'khối lượng trái đất': 5.972e24,  # kg
            'earth mass': 5.972e24,
            'm_earth': 5.972e24,
            'bán kính trái đất': 6.371e6,  # m
            'earth radius': 6.371e6,
            'r_earth': 6.371e6,
            'tuổi trái đất': 4.54e9,  # years
            'age of earth': 4.54e9,
            'khoảng cách trái đất mặt trời': 1.496e11,  # m (1 AU)
            'astronomical unit': 1.496e11,
            'au': 1.496e11,

            # Moon
            'khối lượng mặt trăng': 7.342e22,  # kg
            'moon mass': 7.342e22,
            'm_moon': 7.342e22,
            'bán kính mặt trăng': 1.737e6,  # m
            'moon radius': 1.737e6,
            'r_moon': 1.737e6,
            'khoảng cách trái đất mặt trăng': 3.844e8,  # m
            'earth moon distance': 3.844e8,

            # Distances
            'năm ánh sáng': 9.461e15,  # m
            'light year': 9.461e15,
            'ly': 9.461e15,
            'parsecs': 3.086e16,  # m
            'parsec': 3.086e16,
            'pc': 3.086e16,

            # Time
            'năm julian': 3.15576e7,  # seconds
            'julian year': 3.15576e7,

            # Misc
            'độ trượt đỏ ngưỡng': 6.0,  # z for distant galaxies
            'số thiên hà ước tính': 2.0e12,  # 2 trillion galaxies
            'number of galaxies': 2.0e12,
        }

        # ---------------- Solar System (8 planets + Pluto + Sun + Moon) ----------------
        # Format: name -> {mass_kg, radius_m, semi_major_axis_m, orbital_period_s, mean_temp_k, moons, vi_name}
        self._planets = {
            'mercury': {
                'vi_name': 'Sao Thủy', 'type': 'terrestrial planet',
                'mass_kg': 3.3011e23, 'radius_m': 2.4397e6,
                'semi_major_axis_m': 5.79e10, 'orbital_period_s': 7.6e6,
                'mean_temp_k': 440, 'moons': 0, 'position': 1
            },
            'venus': {
                'vi_name': 'Sao Kim', 'type': 'terrestrial planet',
                'mass_kg': 4.8675e24, 'radius_m': 6.0518e6,
                'semi_major_axis_m': 1.082e11, 'orbital_period_s': 1.94e7,
                'mean_temp_k': 737, 'moons': 0, 'position': 2
            },
            'earth': {
                'vi_name': 'Trái Đất', 'type': 'terrestrial planet',
                'mass_kg': 5.972e24, 'radius_m': 6.371e6,
                'semi_major_axis_m': 1.496e11, 'orbital_period_s': 3.156e7,
                'mean_temp_k': 288, 'moons': 1, 'position': 3
            },
            'mars': {
                'vi_name': 'Sao Hỏa', 'type': 'terrestrial planet',
                'mass_kg': 6.4171e23, 'radius_m': 3.3895e6,
                'semi_major_axis_m': 2.279e11, 'orbital_period_s': 5.94e7,
                'mean_temp_k': 210, 'moons': 2, 'position': 4
            },
            'jupiter': {
                'vi_name': 'Sao Mộc', 'type': 'gas giant',
                'mass_kg': 1.8982e27, 'radius_m': 6.9911e7,
                'semi_major_axis_m': 7.785e11, 'orbital_period_s': 3.743e8,
                'mean_temp_k': 165, 'moons': 95, 'position': 5
            },
            'saturn': {
                'vi_name': 'Sao Thổ', 'type': 'gas giant',
                'mass_kg': 5.6834e26, 'radius_m': 5.8232e7,
                'semi_major_axis_m': 1.434e12, 'orbital_period_s': 9.296e8,
                'mean_temp_k': 134, 'moons': 146, 'position': 6
            },
            'uranus': {
                'vi_name': 'Sao Thiên Vương', 'type': 'ice giant',
                'mass_kg': 8.6810e25, 'radius_m': 2.5362e7,
                'semi_major_axis_m': 2.871e12, 'orbital_period_s': 3.136e9,
                'mean_temp_k': 76, 'moons': 27, 'position': 7
            },
            'neptune': {
                'vi_name': 'Sao Hải Vương', 'type': 'ice giant',
                'mass_kg': 1.02413e26, 'radius_m': 2.4622e7,
                'semi_major_axis_m': 4.495e12, 'orbital_period_s': 5.98e9,
                'mean_temp_k': 72, 'moons': 14, 'position': 8
            },
            'pluto': {
                'vi_name': 'Sao Diêm Vương', 'type': 'dwarf planet',
                'mass_kg': 1.303e22, 'radius_m': 1.1883e6,
                'semi_major_axis_m': 5.906e12, 'orbital_period_s': 7.822e9,
                'mean_temp_k': 44, 'moons': 5, 'position': 9
            },
            'sun': {
                'vi_name': 'Mặt Trời', 'type': 'star (G2V)',
                'mass_kg': 1.989e30, 'radius_m': 6.96e8,
                'semi_major_axis_m': 0, 'orbital_period_s': 0,
                'mean_temp_k': 5778, 'moons': 0, 'position': 0
            },
            'moon': {
                'vi_name': 'Mặt Trăng', 'type': 'satellite of Earth',
                'mass_kg': 7.342e22, 'radius_m': 1.737e6,
                'semi_major_axis_m': 3.844e8, 'orbital_period_s': 2.36e6,
                'mean_temp_k': 220, 'moons': 0, 'position': None
            },
        }

        # Vietnamese name reverse map
        for _en_name, data in list(self._planets.items()):
            self._planets[data['vi_name'].lower()] = data

        # ---------------- Notable stars ----------------
        self._stars = {
            'sirius': {
                'vi_name': 'Siri', 'type': 'binary star',
                'distance_ly': 8.6, 'apparent_mag': -1.46,
                'absolute_mag': 1.42, 'spectral_class': 'A1V',
                'mass_solar': 2.063, 'radius_solar': 1.711,
            },
            'canopus': {
                'vi_name': 'Canopus', 'type': 'star',
                'distance_ly': 309, 'apparent_mag': -0.74,
                'absolute_mag': -5.71, 'spectral_class': 'A9II',
                'mass_solar': 8.0, 'radius_solar': 71,
            },
            'arcturus': {
                'vi_name': 'Arcturus', 'type': 'red giant',
                'distance_ly': 36.7, 'apparent_mag': -0.05,
                'absolute_mag': -0.30, 'spectral_class': 'K0III',
                'mass_solar': 1.08, 'radius_solar': 25.4,
            },
            'alpha centauri': {
                'vi_name': 'Alpha Centauri', 'type': 'binary star',
                'distance_ly': 4.367, 'apparent_mag': -0.27,
                'absolute_mag': 4.38, 'spectral_class': 'G2V + K1V',
                'mass_solar': 2.0, 'radius_solar': 1.22 + 0.86,
            },
            'vega': {
                'vi_name': 'Vega', 'type': 'star',
                'distance_ly': 25.04, 'apparent_mag': 0.026,
                'absolute_mag': 0.58, 'spectral_class': 'A0V',
                'mass_solar': 2.135, 'radius_solar': 2.362,
            },
            'polaris': {
                'vi_name': 'Sao Bắc Cực', 'type': 'triple star',
                'distance_ly': 433, 'apparent_mag': 1.98,
                'absolute_mag': -3.6, 'spectral_class': 'F7Ib',
                'mass_solar': 5.4, 'radius_solar': 37.5,
            },
            'betelgeuse': {
                'vi_name': 'Betelgeuse', 'type': 'red supergiant',
                'distance_ly': 548, 'apparent_mag': 0.5,
                'absolute_mag': -5.85, 'spectral_class': 'M1-2Ia',
                'mass_solar': 11.6, 'radius_solar': 887,
            },
            'rigel': {
                'vi_name': 'Rigel', 'type': 'blue supergiant',
                'distance_ly': 863, 'apparent_mag': 0.13,
                'absolute_mag': -7.84, 'spectral_class': 'B8Ia',
                'mass_solar': 21.0, 'radius_solar': 78.9,
            },
            'proxima centauri': {
                'vi_name': 'Proxima Centauri', 'type': 'red dwarf',
                'distance_ly': 4.246, 'apparent_mag': 11.13,
                'absolute_mag': 15.6, 'spectral_class': 'M5.5Ve',
                'mass_solar': 0.1221, 'radius_solar': 0.1542,
            },
        }

        # ---------------- Notable galaxies ----------------
        self._galaxies = {
            'milky way': {
                'vi_name': 'Ngân Hà', 'type': 'barred spiral',
                'diameter_ly': 105700, 'stars': 2.0e11,
                'distance_ly': 0, 'constellation': None,
            },
            'andromeda': {
                'vi_name': 'Tiên Nữ', 'type': 'spiral',
                'diameter_ly': 220000, 'stars': 1.0e12,
                'distance_ly': 2.537e6, 'constellation': 'Andromeda',
            },
            'triangulum': {
                'vi_name': 'Tam Giác', 'type': 'spiral',
                'diameter_ly': 60000, 'stars': 4.0e10,
                'distance_ly': 2.73e6, 'constellation': 'Triangulum',
            },
            'magellanic cloud': {
                'vi_name': 'Đám Mây Magellan', 'type': 'dwarf irregular',
                'diameter_ly': 14000, 'stars': 3.0e10,
                'distance_ly': 1.63e5, 'constellation': None,
            },
            'sombrero galaxy': {
                'vi_name': 'Thiên Hà Sombrero', 'type': 'spiral',
                'diameter_ly': 50000, 'stars': 1.0e11,
                'distance_ly': 3.1e7, 'constellation': 'Virgo',
            },
            'whirlpool galaxy': {
                'vi_name': 'Thiên Hà Xoáy Nước', 'type': 'spiral',
                'diameter_ly': 76000, 'stars': 1.6e11,
                'distance_ly': 2.3e7, 'constellation': 'Canes Venatici',
            },
        }

        # ---------------- Moons of solar system ----------------
        self._moons = {
            'luna': {'parent': 'Earth', 'mass_kg': 7.342e22, 'radius_m': 1.737e6},
            'phobos': {'parent': 'Mars', 'mass_kg': 1.0659e16, 'radius_m': 1.1267e4},
            'deimos': {'parent': 'Mars', 'mass_kg': 1.4762e15, 'radius_m': 6.2e3},
            'io': {'parent': 'Jupiter', 'mass_kg': 8.9319e22, 'radius_m': 1.8216e6},
            'europa': {'parent': 'Jupiter', 'mass_kg': 4.7998e22, 'radius_m': 1.5608e6},
            'ganymede': {'parent': 'Jupiter', 'mass_kg': 1.4819e23, 'radius_m': 2.6341e6},
            'callisto': {'parent': 'Jupiter', 'mass_kg': 1.0759e23, 'radius_m': 2.4103e6},
            'titan': {'parent': 'Saturn', 'mass_kg': 1.3452e23, 'radius_m': 2.5747e6},
            'enceladus': {'parent': 'Saturn', 'mass_kg': 1.08022e20, 'radius_m': 2.521e5},
            'miranda': {'parent': 'Uranus', 'mass_kg': 6.59e19, 'radius_m': 2.358e5},
            'titania': {'parent': 'Uranus', 'mass_kg': 3.42e21, 'radius_m': 7.884e5},
            'triton': {'parent': 'Neptune', 'mass_kg': 2.14e22, 'radius_m': 1.3534e6},
            'charon': {'parent': 'Pluto', 'mass_kg': 1.586e21, 'radius_m': 6.06e5},
        }

        # ---------------- 88 Constellations (a subset of notable) ----------------
        self._constellations = {
            'orion': {'vi_name': 'Lạp Hộ', 'stars_visible': 81, 'best_viewed': 'winter'},
            'ursa major': {'vi_name': 'Đại Hùng', 'stars_visible': 209, 'best_viewed': 'spring'},
            'ursa minor': {'vi_name': 'Tiểu Hùng', 'stars_visible': 32, 'best_viewed': 'all year'},
            'cassiopeia': {'vi_name': 'Tiên Hậu', 'stars_visible': 157, 'best_viewed': 'autumn'},
            'cygnus': {'vi_name': 'Thiên Nga', 'stars_visible': 262, 'best_viewed': 'summer'},
            'lyra': {'vi_name': 'Thiên Cầm', 'stars_visible': 73, 'best_viewed': 'summer'},
            'andromeda': {'vi_name': 'Tiên Nữ', 'stars_visible': 152, 'best_viewed': 'autumn'},
            'scorpius': {'vi_name': 'Thiên Yết', 'stars_visible': 167, 'best_viewed': 'summer'},
            'sagittarius': {'vi_name': 'Nhân Mã', 'stars_visible': 286, 'best_viewed': 'summer'},
            'leo': {'vi_name': 'Sư Tử', 'stars_visible': 122, 'best_viewed': 'spring'},
        }

    @property
    def name(self) -> str:
        return "AstronomyDataSource"

    @property
    def priority(self) -> int:
        return 2

    @property
    def ttl(self) -> int:
        return 2592000  # 30 days - astronomical data very stable

    def get_supported_intents(self) -> list[str]:
        return [
            'planet_info',
            'star_info',
            'galaxy_info',
            'moon_info',
            'constellation_info',
            'astronomical_constant',
            'distance_info',
            'orbit_info',
        ]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            entity_lower = entity.lower().strip()
            if entity_lower in self._constants:
                return True
            if entity_lower in self._planets:
                return True
            if entity_lower in self._stars:
                return True
            if entity_lower in self._galaxies:
                return True
            if entity_lower in self._moons:
                return True
            if entity_lower in self._constellations:
                return True
            # Partial match
            for key in list(self._planets.keys()) + list(self._stars.keys()) + list(self._galaxies.keys()):
                if _token_boundary_match(key, entity_lower):
                    return True
        return False

    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        """Lấy dữ liệu thiên văn."""
        if not entity:
            return None

        entity_lower = entity.lower().strip()

        # Try constants
        if entity_lower in self._constants:
            value = self._constants[entity_lower]
            return {
                'value': value,
                'source': 'NASA / IAU (Local)',
                'metadata': {
                    'constant_name': entity_lower,
                    'method': 'lookup',
                }
            }
        for key, value in self._constants.items():
            if _token_boundary_match(key, entity_lower):
                return {
                    'value': value,
                    'source': 'NASA / IAU (Local)',
                    'metadata': {'constant_name': key, 'method': 'lookup'}
                }

        # Try planets
        if entity_lower in self._planets:
            data = self._planets[entity_lower]
            return {
                'value': data['mass_kg'],
                'source': 'NASA Planetary Fact Sheet (Local)',
                'metadata': {
                    'name_en': entity_lower,
                    'vi_name': data['vi_name'],
                    'type': data['type'],
                    'mass_kg': data['mass_kg'],
                    'radius_m': data['radius_m'],
                    'semi_major_axis_m': data['semi_major_axis_m'],
                    'orbital_period_s': data['orbital_period_s'],
                    'mean_temp_k': data['mean_temp_k'],
                    'moons': data['moons'],
                    'position': data['position'],
                    'unit': 'kg',
                }
            }
        # Partial planet match
        for key, data in self._planets.items():
            if _token_boundary_match(key, entity_lower):
                return {
                    'value': data['mass_kg'],
                    'source': 'NASA Planetary Fact Sheet (Local)',
                    'metadata': {
                        'name_en': key,
                        'vi_name': data['vi_name'],
                        'type': data['type'],
                        'mass_kg': data['mass_kg'],
                        'radius_m': data['radius_m'],
                        'semi_major_axis_m': data['semi_major_axis_m'],
                        'orbital_period_s': data['orbital_period_s'],
                        'mean_temp_k': data['mean_temp_k'],
                        'moons': data['moons'],
                        'position': data['position'],
                        'unit': 'kg',
                    }
                }

        # Try stars
        if entity_lower in self._stars:
            data = self._stars[entity_lower]
            return {
                'value': data['apparent_mag'],
                'source': 'Yale Bright Star Catalog (Local)',
                'metadata': data
            }
        # Try galaxies
        if entity_lower in self._galaxies:
            data = self._galaxies[entity_lower]
            return {
                'value': data['stars'],
                'source': 'NASA Extragalactic Database (Local)',
                'metadata': data
            }
        # Try moons
        if entity_lower in self._moons:
            data = self._moons[entity_lower]
            return {
                'value': data['mass_kg'],
                'source': 'NASA Planetary Fact Sheet (Local)',
                'metadata': data
            }
        # Try constellations
        if entity_lower in self._constellations:
            data = self._constellations[entity_lower]
            return {
                'value': data['stars_visible'],
                'source': 'IAU Constellation Catalog (Local)',
                'metadata': data
            }

        # Fallback: Wikipedia
        return self._fetch_from_wikipedia(entity)

    def _fetch_from_wikipedia(self, entity: str) -> dict[str, Any] | None:
        """Fallback: Lấy từ Wikipedia.

        [G3-CONSOLIDATE RE-05] Now delegates to scp.core.wikipedia_client
        (fetch_summary). Same return shape, same error→None contract.
        Previously this method made a raw requests.get() with timeout=5s
        and constructed the REST URL manually; now it goes through the
        canonical client which provides timeout=10s, 1 req/sec rate limit,
        LRU cache (256 entries), and proper User-Agent header.
        """
        # [G3-CONSOLIDATE RE-05] Now delegates to scp.core.wikipedia_client
        try:
            result = _wiki_fetch_summary(entity, lang="en")
            if result and result.get("extract"):
                return {
                    'value': result['extract'],
                    'source': 'Wikipedia',
                    'metadata': {
                        'title': result.get('title', ''),
                        'method': 'wikipedia'
                    }
                }
        except Exception as e:
            logger.warning(f"[Astronomy] Wikipedia fetch failed: {e}", exc_info=True)
        return None

    def health_check(self) -> bool:
        """[AUDIT-FIX low-4] Fail-closed: ping MediaWiki API của en.wikipedia.org
        (siteinfo — endpoint mà wikipedia_client fetch() thực sự dùng, không cần
        key). Trước đây hardcode `return True` — fail-open, không có
        bằng chứng. Bất kỳ HTTP response nào chứng minh service sống; exception
        (egress denied, DNS, timeout) → False.

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
            from scp.security.url_safety import safe_urlopen  # [AUDIT-FIX low-4]
            # [SSRF-S1] safe_urlopen cho health ping (URL cố định).
            with safe_urlopen(
                "https://en.wikipedia.org/w/api.php?action=query&meta=siteinfo&format=json",
                timeout=3,
            ):
                api_ok = True
        except Exception as e:
            logger.warning(f"[Astronomy] health ping failed: {e}", exc_info=True)
        if not api_ok:
            logger.warning(
                "[Astronomy] health_check: Wikipedia endpoint unreachable — báo "
                "unhealthy (fail-closed)"
            )
        return api_ok
