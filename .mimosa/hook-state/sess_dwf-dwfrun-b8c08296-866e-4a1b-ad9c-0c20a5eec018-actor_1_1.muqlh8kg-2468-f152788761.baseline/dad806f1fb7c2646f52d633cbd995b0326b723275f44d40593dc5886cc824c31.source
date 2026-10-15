"""
SCP - Viet Nam | Self-Correcting Pipeline
 ReligionDataSource - Data source cho Tôn giáo
"""

import logging
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


class ReligionDataSource(IDataSource):
    """Data source cho Tôn giáo."""

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._religions = {
            "phật giáo": {"followers": "500M+", "origin": "Ấn Độ, ~500 TCN", "founder": "Siddhartha Gautama"},
            "christianity": {"followers": "2.4B+", "origin": "Palestine, ~33 SCN", "founder": "Jesus Christ"},
            "islam": {"followers": "1.9B+", "origin": "Arabia, 610 SCN", "founder": "Muhammad"},
            "hinduism": {"followers": "1.2B+", "origin": "Ấn Độ, ~1500 TCN", "founder": "Nhiều người sáng lập"},
            "đạo trà": {"followers": "100M+", "origin": "Việt Nam", "founder": "Trần Nhân Tông"},
            "đạo hiếu": {"followers": "N/A", "origin": "Việt Nam", "founder": "Nhiều người"},
        }


    @property
    def name(self) -> str:
        return "ReligionDataSource"

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
            return {"value": result.get("answer", ""), "source": "Religion", "metadata": result}
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
        for religion, info in self._religions.items():
            if religion in q:
                result = {"found": True, "answer": f"{religion}: {info['followers']} followers, từ {info['origin']}", "confidence": 0.9, "source": "Religion Database"}
                break
        self._cache[q] = result
        return result
