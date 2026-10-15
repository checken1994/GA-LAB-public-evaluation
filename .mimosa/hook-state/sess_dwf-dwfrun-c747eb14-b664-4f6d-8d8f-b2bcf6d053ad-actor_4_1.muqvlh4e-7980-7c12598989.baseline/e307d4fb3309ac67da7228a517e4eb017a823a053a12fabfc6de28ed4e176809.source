"""
SCP - Viet Nam | Self-Correcting Pipeline
 HeritageDataSource - Data source cho Di sản văn hóa
"""

import logging
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


class HeritageDataSource(IDataSource):
    """Data source cho Di sản văn hóa."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # UNESCO World Heritage Sites
        self._sites = {
            "cố đô huế": {
                "location": "Việt Nam",
                "year": 1993,
                "type": "Cultural",
                "description": "Complex of Nguyen Dynasty monuments"
            },
            "phố cổ hội an": {
                "location": "Việt Nam",
                "year": 1999,
                "type": "Cultural",
                "description": "Historic trading port town"
            },
            "thánh địa mai châu": {
                "location": "Việt Nam",
                "year": 2023,
                "type": "Cultural",
                "description": "Central role of Mỹ Church in Vietnamese spiritual life"
            },
            "hoàng thành thăng long": {
                "location": "Việt Nam",
                "year": 2010,
                "type": "Cultural",
                "description": "Historical royal capital"
            },
            "vịnh hạ long": {
                "location": "Việt Nam",
                "year": 1994,
                "type": "Natural",
                "description": "2000+ limestone islands"
            },
            "taj mahal": {
                "location": "India",
                "year": 1983,
                "type": "Cultural",
                "description": "Ivory-white marble mausoleum"
            },
            "machu picchu": {
                "location": "Peru",
                "year": 1983,
                "type": "Cultural",
                "description": "15th-century Inca citadel"
            },
            "great wall": {
                "location": "China",
                "year": 1987,
                "type": "Cultural",
                "description": "Ancient fortification system"
            },
            "petra": {
                "location": "Jordan",
                "year": 1985,
                "type": "Cultural",
                "description": "Rose-red city carved in rock"
            },
            "colosseum": {
                "location": "Italy",
                "year": 1980,
                "type": "Cultural",
                "description": "Ancient Roman amphitheater"
            },
        }

        # Vietnamese intangible heritage
        self._intangible = {
            "hội元宵": "Lễ hội đền Trần (Trần dynasty)",
            "nhã nhạc cung đình": "Royal court music (Vietnam)",
            "đờn ca tài tử": "Southern folk music",
            "ca trù": "Ceremonial music",
            "quan họ": "Folk singing (Northern Vietnam)",
        }

    def query(self, question: str) -> dict[str, Any]:
        q = question.lower().strip()
        if q in self._cache:
            return self._cache[q]

        result = {"found": False, "answer": None, "confidence": 0.0}

        for site, info in self._sites.items():
            if site in q:
                result = {
                    "found": True,
                    "answer": f"{site}: {info['location']}, UNESCO {info['year']}, {info['type']} - {info['description']}",
                    "confidence": 1.0,
                    "source": "UNESCO"
                }
                break

        if not result["found"]:
            for heritage, desc in self._intangible.items():
                if heritage in q:
                    result = {
                        "found": True,
                        "answer": f"{heritage}: {desc}",
                        "confidence": 0.9,
                        "source": "Vietnamese Heritage"
                    }
                    break

        self._cache[q] = result
        return result

    @property
    def name(self) -> str:
        return "HeritageDataSource"

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
            return {"value": result.get("answer", ""), "source": "Heritage", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True
