"""
SCP - Viet Nam | Self-Correcting Pipeline
 TourismDataSource - Data source cho Du lịch
"""

import logging
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


class TourismDataSource(IDataSource):
    """Data source cho Du lịch."""

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._destinations = {
            "vạn lý trường thành": "Trung Quốc",
            "machu picchu": "Peru",
            "taj mahal": "Ấn Độ",
            "petra": "Jordan",
            "colosseum": "Ý",
            "chichen itza": "Mexico",
            "vịnh hạ long": "Việt Nam",
            "phong nha": "Việt Nam",
        }
        self._visas = {
            "schengen": "26 nước châu Âu",
            "asean": "10 nước Đông Nam Á",
            "us visa": "10 năm multiple entry",
        }


    @property
    def name(self) -> str:
        return "TourismDataSource"

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
            return {"value": result.get("answer", ""), "source": "Tourism", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True

    def query(self, question: str) -> dict[str, Any]:
        q = question.lower().strip()
        if q in self._cache:
            return self._cache[q]
        result = {"found": False, "answer": None, "confidence": 0.0}
        for dest, country in self._destinations.items():
            if dest in q:
                result = {"found": True, "answer": f"{dest}: {country}", "confidence": 1.0, "source": "Tourism DB"}
                break
        for visa, countries in self._visas.items():
            if visa in q:
                result = {"found": True, "answer": f"{visa}: {countries}", "confidence": 1.0, "source": "Visa DB"}
                break
        self._cache[q] = result
        return result
