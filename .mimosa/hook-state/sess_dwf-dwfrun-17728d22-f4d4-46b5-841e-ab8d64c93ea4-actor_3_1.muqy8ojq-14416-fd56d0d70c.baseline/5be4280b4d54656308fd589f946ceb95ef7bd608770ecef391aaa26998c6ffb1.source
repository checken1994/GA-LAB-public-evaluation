"""
SCP - Viet Nam | Self-Correcting Pipeline
 EnvironmentDataSource - Data source cho Môi trường
"""

import logging
import re
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


def _wb_match(key: str, text_lower: str) -> bool:
    """[ROOT-FIX 4] Word-boundary match — prevents 'good' matching 'goodbye',
    'moderate' matching 'immoderate', 'tiger' matching 'tigerish', etc.
    Uses Unicode-aware lookarounds so Vietnamese diacritics work too.
    """
    if not key or not text_lower:
        return False
    if key == text_lower:
        return True
    pattern = r'(?<![\wÀ-ỹ])' + re.escape(key) + r'(?![\wÀ-ỹ])'
    return bool(re.search(pattern, text_lower))


class EnvironmentDataSource(IDataSource):
    """
    Data source cho các câu hỏi Môi trường.
    Hỗ trợ: khí hậu, ô nhiễm, sinh thái.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Environmental data
        self._climate = {
            "nhiệt độ trung bình trái đất": 15,  # °C
            "mực nước biển tăng": 3.7,  # mm/năm
            "CO2 hiện tại": 421,  # ppm
            "ozone layer": "300 DU",
        }

        # Endangered species
        self._endangered = {
            "tiger": {"population": 3900, "status": "Endangered"},
            "panda": {"population": 1800, "status": "Vulnerable"},
            "rhino": {"population": 27000, "status": "Vulnerable"},
            "elephant": {"population": 415000, "status": "Vulnerable"},
            "whale": {"population": 3000, "status": "Endangered"},
        }

        # Pollution levels
        self._pollution = {
            "AQI good": "0-50",
            "AQI moderate": "51-100",
            "AQI unhealthy sensitive": "101-150",
            "AQI unhealthy": "151-200",
            "AQI very unhealthy": "201-300",
        }


    @property
    def name(self) -> str:
        return "EnvironmentDataSource"

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
            return {"value": result.get("answer", ""), "source": "Environment", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True

    def query(self, question: str) -> dict[str, Any]:
        """Query environment data."""
        q = question.lower().strip()

        if q in self._cache:
            return self._cache[q]

        result = {"found": False, "answer": None, "confidence": 0.0}

        # Check climate
        for key, value in self._climate.items():
            # [ROOT-FIX 4] Was `key in q` — substring match. Use word-boundary.
            if _wb_match(key, q):
                result = {
                    "found": True,
                    "answer": f"{key}: {value}",
                    "confidence": 1.0,
                    "source": "Environmental Database"
                }
                break

        # Check endangered
        for species, info in self._endangered.items():
            # [ROOT-FIX 4] Was `species in q` — substring match → 'tiger' matched
            # 'tigerish', 'whale' matched 'whaler', etc. Use word-boundary.
            if _wb_match(species, q):
                result = {
                    "found": True,
                    "answer": f"{species}: ~{info['population']} cá thể, {info['status']}",
                    "confidence": 0.8,
                    "source": "IUCN Red List"
                }
                break

        # Check pollution
        for level, range_val in self._pollution.items():
            # [ROOT-FIX 4] Was `level.replace("AQI ", "") in q` — substring match
            # → 'good' matched 'goodbye', 'moderate' matched 'immoderate', 'unhealthy'
            # matched 'unhealthily'. Use word-boundary.
            if _wb_match(level.replace("AQI ", ""), q):
                result = {
                    "found": True,
                    "answer": f"{level}: {range_val}",
                    "confidence": 1.0,
                    "source": "Air Quality Index"
                }
                break

        self._cache[q] = result
        return result
