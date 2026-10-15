""" TransportDataSource"""
import logging

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)

class TransportDataSource(IDataSource):
    def __init__(self):
        self._cache = {}
        self._modes = {
            "máy bay": "800 km/h",
            "tàu cao tốc": "300 km/h",
            "xe hơi": "120 km/h",
            "xe đạp": "20 km/h",
            "chạy bộ": "10 km/h",
        }

    @property
    def name(self) -> str:
        return "TransportDataSource"

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
            return {"value": result.get("answer", ""), "source": "Transport", "metadata": result}
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
        for mode, speed in self._modes.items():
            if mode in q:
                result = {"found": True, "answer": f"{mode}: {speed}", "confidence": 1.0}
                break
        self._cache[q] = result
        return result
