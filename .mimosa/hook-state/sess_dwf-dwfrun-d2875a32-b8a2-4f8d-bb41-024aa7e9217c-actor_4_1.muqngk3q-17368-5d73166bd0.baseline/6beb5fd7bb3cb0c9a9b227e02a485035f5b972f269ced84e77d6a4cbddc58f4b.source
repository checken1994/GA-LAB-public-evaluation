"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.

WHY Engine, Recursive Why, MetaFalsifier, ProofGraph
License: See LICENSE file
"""

"""
ConversionDataSource - Data source cho Quy đổi đơn vị
Bao gồm: SI units, length, mass, temperature, time, energy, area, volume, speed.
"""
import logging
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


class ConversionDataSource(IDataSource):
    """Data source cho các câu hỏi quy đổi đơn vị."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

        #  Pressure -> Pascals
        self._pressure_to_pa = {
            'pa': 1, 'pascal': 1, 'pascals': 1,
            'kpa': 1000, 'kilopascal': 1000,
            'mpa': 1000000, 'megapascal': 1000000,
            'bar': 100000,
            'mbar': 100,
            'atm': 101325, 'atmosphere': 101325,
            'psi': 6894.76, 'pound per square inch': 6894.76,
            'torr': 133.322, 'mmhg': 133.322,
        }

        # Conversion factors to base unit
        # Length -> meters
        self._length_to_m = {
            'km': 1000, 'kilometer': 1000, 'kilomet': 1000,
            'm': 1, 'meter': 1, 'met': 1,
            'dm': 0.1, 'decimeter': 0.1,
            'cm': 0.01, 'centimeter': 0.01,
            'mm': 0.001, 'millimeter': 0.001,
            'µm': 1e-6, 'micrometer': 1e-6,
            'nm': 1e-9, 'nanometer': 1e-9,
            'mile': 1609.344, 'mi': 1609.344,
            'yard': 0.9144, 'yd': 0.9144,
            'foot': 0.3048, 'ft': 0.3048,
            'inch': 0.0254, 'in': 0.0254,
            'nautical mile': 1852, 'nmi': 1852,
            'ly': 9.461e15, 'light year': 9.461e15,
            'au': 1.496e11, 'astronomical unit': 1.496e11,
            'pc': 3.086e16, 'parsec': 3.086e16,
        }

        # Mass -> kg
        self._mass_to_kg = {
            'kg': 1, 'kilogram': 1, 'kilôgam': 1,
            'g': 0.001, 'gram': 0.001, 'gam': 0.001,
            'mg': 1e-6, 'milligram': 1e-6,
            'µg': 1e-9, 'microgram': 1e-9,
            'ton': 1000, 't': 1000, 'metric ton': 1000, 'tấn': 1000,
            'lb': 0.45359237, 'pound': 0.45359237, 'lbs': 0.45359237,
            'oz': 0.028349523125, 'ounce': 0.028349523125,
            'stone': 6.35029318,
            'carat': 0.0002, 'ct': 0.0002,
            'slug': 14.5939029372,
        }

        # Time -> seconds
        self._time_to_s = {
            's': 1, 'sec': 1, 'second': 1, 'giây': 1,
            'ms': 0.001, 'millisecond': 0.001,
            'µs': 1e-6, 'microsecond': 1e-6,
            'ns': 1e-9, 'nanosecond': 1e-9,
            'min': 60, 'minute': 60, 'phút': 60,
            'h': 3600, 'hr': 3600, 'hour': 3600, 'giờ': 3600,
            'day': 86400, 'ngày': 86400,
            'week': 604800, 'tuần': 604800,
            'month': 2629800, 'tháng': 2629800,  # avg 30.44 days
            'year': 31557600, 'yr': 31557600, 'năm': 31557600,
            'decade': 315576000,
            'century': 3155760000, 'thế kỷ': 3155760000,
        }

        # Speed -> m/s
        self._speed_to_ms = {
            'm/s': 1, 'mps': 1,
            'km/h': 0.277778, 'kph': 0.277778,
            'mph': 0.44704, 'mi/h': 0.44704,
            'ft/s': 0.3048, 'fps': 0.3048,
            'knot': 0.514444, 'kn': 0.514444,
            'mach': 340.29,  # at sea level, 15°C
        }

        # Area -> m²
        self._area_to_m2 = {
            'm²': 1, 'm2': 1, 'sqm': 1, 'square meter': 1,
            'km²': 1e6, 'km2': 1e6, 'sqkm': 1e6,
            'cm²': 1e-4, 'cm2': 1e-4,
            'mm²': 1e-6, 'mm2': 1e-6,
            'ha': 10000, 'hectare': 10000, 'hécta': 10000,
            'acre': 4046.8564224,
            'ft²': 0.092903, 'ft2': 0.092903, 'sqft': 0.092903,
            'in²': 0.00064516, 'in2': 0.00064516,
            'mile²': 2.59e6, 'mi2': 2.59e6,
            'dặm vuông': 2.59e6,
        }

        # Volume -> m³
        self._volume_to_m3 = {
            'm³': 1, 'm3': 1, 'cubic meter': 1,
            'l': 0.001, 'liter': 0.001, 'lít': 0.001,
            'ml': 1e-6, 'milliliter': 1e-6,
            'cl': 1e-5, 'centiliter': 1e-5,
            'dl': 1e-4, 'deciliter': 1e-4,
            'cm³': 1e-6, 'cm3': 1e-6, 'cc': 1e-6,
            'mm³': 1e-9, 'mm3': 1e-9,
            'ft³': 0.0283168, 'ft3': 0.0283168,
            'in³': 1.63871e-5, 'in3': 1.63871e-5,
            'gallon': 0.00378541, 'gal': 0.00378541,  # US
            'quart': 0.000946353, 'qt': 0.000946353,
            'pint': 0.000473176, 'pt': 0.000473176,
            'cup': 0.000236588,
            'floz': 2.95735e-5, 'fl oz': 2.95735e-5,
            'tablespoon': 1.47868e-5, 'tbsp': 1.47868e-5,
            'teaspoon': 4.92892e-6, 'tsp': 4.92892e-6,
            'barrel': 0.158987,  # oil barrel
        }

        # Energy -> Joule
        self._energy_to_j = {
            'j': 1, 'joule': 1,
            'kj': 1000, 'kilojoule': 1000,
            'mj': 1e6, 'megajoule': 1e6,
            'cal': 4.184, 'calorie': 4.184,
            'kcal': 4184, 'kilocalorie': 4184, 'Cal': 4184,
            'wh': 3600, 'watt-hour': 3600,
            'kwh': 3.6e6, 'kilowatt-hour': 3.6e6, 'số điện': 3.6e6,
            'mwh': 3.6e9,
            'gwh': 3.6e12,
            'btu': 1055.06,
            'ft-lb': 1.35582,
            'ev': 1.602176634e-19, 'electronvolt': 1.602176634e-19,
            'tnt': 4.184e9,  # ton TNT
        }

        # Power -> Watt
        self._power_to_w = {
            'w': 1, 'watt': 1,
            'kw': 1000, 'kilowatt': 1000,
            'mw': 1e6, 'megawatt': 1e6,
            'gw': 1e9, 'gigawatt': 1e9,
            'tw': 1e12, 'terawatt': 1e12,
            'hp': 745.7, 'horsepower': 745.7,
            'ps': 735.49875,  # metric horsepower
            'btu/h': 0.29307107,
        }

        # Temperature (special: needs offset, not just factor)
        self._temperature_scales = {
            'c': 'celsius', 'celsius': 'celsius', '°c': 'celsius', 'độ c': 'celsius',
            'f': 'fahrenheit', 'fahrenheit': 'fahrenheit', '°f': 'fahrenheit',
            'k': 'kelvin', 'kelvin': 'kelvin',
            'r': 'rankine', 'rankine': 'rankine',
        }

    @property
    def name(self) -> str:
        return "ConversionDataSource"

    @property
    def priority(self) -> int:
        return 1  # High priority - conversions are core

    @property
    def ttl(self) -> int:
        return 604800  # 1 week

    def get_supported_intents(self) -> list[str]:
        return [
            'unit_conversion',
            'length_conversion',
            'mass_conversion',
            'time_conversion',
            'speed_conversion',
            'area_conversion',
            'volume_conversion',
            'energy_conversion',
            'power_conversion',
            'temperature_conversion',
        ]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            entity_lower = entity.lower().strip()
            for table in (self._length_to_m, self._mass_to_kg, self._time_to_s,
                          self._speed_to_ms, self._area_to_m2, self._volume_to_m3,
                          self._energy_to_j, self._power_to_w, self._temperature_scales):
                if entity_lower in table:
                    return True
        return False

    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        """For unit conversion, returns the factor to base unit."""
        if not entity:
            return None

        entity_lower = entity.lower().strip()

        # Check each table
        for table_name, table in [
            ('length', self._length_to_m),
            ('mass', self._mass_to_kg),
            ('time', self._time_to_s),
            ('speed', self._speed_to_ms),
            ('area', self._area_to_m2),
            ('volume', self._volume_to_m3),
            ('energy', self._energy_to_j),
            ('power', self._power_to_w),
            ('pressure', self._pressure_to_pa),  #
        ]:
            if entity_lower in table:
                factor = table[entity_lower]
                return {
                    'value': factor,
                    'source': 'Local Conversion Database',
                    'metadata': {
                        'unit': entity_lower,
                        'category': table_name,
                        'base_unit': {
                            'length': 'meter',
                            'mass': 'kilogram',
                            'time': 'second',
                            'speed': 'm/s',
                            'area': 'm²',
                            'volume': 'm³',
                            'energy': 'joule',
                            'power': 'watt',
                            'pressure': 'pascal',  #
                        }[table_name],
                        'factor': factor,
                        'method': 'lookup',
                    }
                }

        # Temperature scale
        if entity_lower in self._temperature_scales:
            scale = self._temperature_scales[entity_lower]
            return {
                'value': scale,
                'source': 'Local Conversion Database',
                'metadata': {
                    'unit': entity_lower,
                    'category': 'temperature',
                    'scale': scale,
                    'method': 'lookup',
                }
            }

        return None

    def convert_temperature(self, value: float, from_scale: str, to_scale: str) -> float | None:
        """[V104.31 #8] Unknown scale → None (was: ValueError deep in else branch)."""
        if value is None:
            return None
        from_norm = self._temperature_scales.get(from_scale.lower())
        to_norm = self._temperature_scales.get(to_scale.lower())
        if from_norm is None:
            logger.warning(f"[Conversion] Unknown from_scale '{from_scale}' -> None")
            return None
        if to_norm is None:
            logger.warning(f"[Conversion] Unknown to_scale '{to_scale}' -> None")
            return None
        if from_norm == 'celsius':
            c = value
        elif from_norm == 'fahrenheit':
            c = (value - 32) * 5 / 9
        elif from_norm == 'kelvin':
            c = value - 273.15
        elif from_norm == 'rankine':
            c = (value - 491.67) * 5 / 9
        else:
            return None
        if to_norm == 'celsius':
            return c
        elif to_norm == 'fahrenheit':
            return c * 9 / 5 + 32
        elif to_norm == 'kelvin':
            return c + 273.15
        elif to_norm == 'rankine':
            return (c + 273.15) * 9 / 5
        else:
            return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True
