""" DiplomacyDataSource"""
import logging
import re as _re

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)
# [V104.32 #7] word-boundary matching for short keys

class DiplomacyDataSource(IDataSource):
    def __init__(self):
        self._cache = {}
        self._orgs = {
            "UN": "United Nations, 193 members",
            "ASEAN": "Association of SE Asian Nations, 10 members",
            "EU": "European Union, 27 members",
            "NATO": "North Atlantic Treaty Organization, 31 members",
            "G7": "Group of 7: US, UK, France, Germany, Italy, Japan, Canada",
            "G20": "Group of 20: Major economies",
        }

    @property
    def name(self) -> str:
        return "DiplomacyDataSource"

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
            return {"value": result.get("answer", ""), "source": "Diplomacy", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True

    def query(self, q):
        if q in self._cache: return self._cache[q]
        result = {"found": False, "answer": None, "confidence": 0.0}
        for org, desc in self._orgs.items():
            if _re.search(r'\b' + _re.escape(org.lower()) + r'\b', q):
                result = {"found": True, "answer": f"{org}: {desc}", "confidence": 1.0}
                break
        self._cache[q] = result
        return result
