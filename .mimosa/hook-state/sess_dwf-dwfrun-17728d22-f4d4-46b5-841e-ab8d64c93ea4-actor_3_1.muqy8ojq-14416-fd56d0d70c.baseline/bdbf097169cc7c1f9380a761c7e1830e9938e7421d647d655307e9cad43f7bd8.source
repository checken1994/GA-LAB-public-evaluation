"""
SCP - Viet Nam | Self-Correcting Pipeline
 PhysicsDataSource - Data source cho Vật lý
"""

import logging
import re as _re
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)
# [V104.32 #2] word-boundary matching for short keys


class PhysicsDataSource(IDataSource):
    """
    Data source cho các câu hỏi Vật lý.
    Hỗ trợ: hằng số vật lý, công thức, đơn vị.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Physical constants (CODATA 2018)
        self._constants = {
            # Speed and mechanics
            "tốc độ ánh sáng": 299792458,  # m/s
            "speed of light": 299792458,
            "c": 299792458,
            "g": 9.80665,  # gravitational acceleration (m/s²)
            "hằng số hấp dẫn": 6.67430e-11,  # G (m³/(kg·s²))
            "gravitational constant": 6.67430e-11,
            "G": 6.67430e-11,
            "khối lượng electron": 9.1093837015e-31,  # kg
            "electron mass": 9.1093837015e-31,
            "me": 9.1093837015e-31,
            "khối lượng proton": 1.67262192369e-27,  # kg
            "proton mass": 1.67262192369e-27,
            "mp": 1.67262192369e-27,
            "khối lượng neutron": 1.67493e-27,  # kg
            "neutron mass": 1.67493e-27,

            # Electromagnetic
            "hằng số Planck": 6.62607015e-34,  # J·s
            "Planck constant": 6.62607015e-34,
            "h": 6.62607015e-34,
            "hbar": 1.054571817e-34,
            "hằng số Boltzmann": 1.380649e-23,  # J/K
            "Boltzmann constant": 1.380649e-23,
            "k": 1.380649e-23,
            "hằng số Faraday": 96485.33212,  # C/mol
            "Faraday constant": 96485.33212,
            "F": 96485.33212,
            "trở kháng chân không": 376.730313668,  # ohm
            "vacuum impedance": 376.730313668,
            "Z0": 376.730313668,

            # Thermodynamic
            "hằng số khí lý tưởng": 8.314462618,  # J/(mol·K)
            "ideal gas constant": 8.314462618,
            "R": 8.314462618,
            "nhiệt độ Planck": 1.416784e32,  # K
            "Planck temperature": 1.416784e32,
            "nhiệt dung riêng nước": 4186,  # J/(kg·K)

            # Atomic
            "bán kính Bohr": 5.29177210903e-11,  # m
            "Bohr radius": 5.29177210903e-11,
            "a0": 5.29177210903e-11,
            "số Rydberg": 10973731.568160,  # 1/m
            "Rydberg constant": 10973731.568160,
            "Ry": 10973731.568160,

            #宇宙
            "tuổi vũ trụ": 13.8e9,  # years
            "age of universe": 13.8e9,
            "bán kính Hubble": 4.4e26,  # m
            "Hubble radius": 4.4e26,
        }

        # SI prefixes
        self._prefixes = {
            "yotta": 1e24, "Z": 1e21, "exa": 1e18, "peta": 1e15,
            "tera": 1e12, "giga": 1e9, "mega": 1e6, "kilo": 1e3,
            "hecto": 1e2, "deca": 1e1, "deci": 1e-1, "centi": 1e-2,
            "milli": 1e-3, "micro": 1e-6, "nano": 1e-9, "pico": 1e-12,
            "femto": 1e-15, "atto": 1e-18, "zepto": 1e-21, "yocto": 1e-24,
        }


    @property
    def name(self) -> str:
        return "PhysicsDataSource"

    @property
    def priority(self) -> int:
        return 5

    @property
    def ttl(self) -> int:
        return 86400

    def get_supported_intents(self) -> list[str]:
        return ["lookup", "query", "fact"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        return True

    def fetch(self, intent: str, entity: str, **kwargs):
        result = self.query(entity or intent)
        if result.get("found"):
            return {"value": result.get("answer", ""), "source": "Physics", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True

    def query(self, question: str) -> dict[str, Any]:
        """Query physics data."""
        q = question.lower().strip()

        # Check cache
        if q in self._cache:
            return self._cache[q]

        result = {"found": False, "answer": None, "confidence": 0.0}

        # Check constants
        for name, value in self._constants.items():
            if (len(name) >= 3 and _re.search(r'\b' + _re.escape(name) + r'\b', q)) or name == q:
                result = {
                    "found": True,
                    "answer": f"{name} = {value}",
                    "confidence": 1.0,
                    "unit": self._get_unit(name),
                    "source": "CODATA 2018"
                }
                break

        # Check SI prefixes
        for prefix, factor in self._prefixes.items():
            if prefix in q:
                result = {
                    "found": True,
                    "answer": f"1 {prefix} = {factor}",
                    "confidence": 1.0,
                    "source": "SI Standard"
                }
                break

        self._cache[q] = result
        return result

    def _get_unit(self, constant_name: str) -> str:
        """Get unit for constant."""
        units = {
            "tốc độ ánh sáng": "m/s", "speed of light": "m/s", "c": "m/s",
            "g": "m/s²", "hằng số hấp dẫn": "m³/(kg·s²)", "gravitational constant": "m³/(kg·s²)",
            "khối lượng electron": "kg", "electron mass": "kg",
            "khối lượng proton": "kg", "proton mass": "kg",
            "hằng số Planck": "J·s", "Planck constant": "J·s",
            "hằng số Boltzmann": "J/K",
            "nhiệt độ Planck": "K", "Planck temperature": "K",
        }
        return units.get(constant_name, "")

    def get_constant(self, name: str) -> float | None:
        """Get constant by name."""
        return self._constants.get(name.lower())
