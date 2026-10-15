""" SocialDataSource"""
import logging

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)

class SocialDataSource(IDataSource):
    def __init__(self):
        self._cache = {}
        self._platforms = {
            "facebook": "2.9B users",
            "youtube": "2.2B users",
            "whatsapp": "2B users",
            "instagram": "1.4B users",
            "tiktok": "1B users",
            "twitter/x": "500M users",
            "zalo": "70M users (VN)",
        }

    @property
    def name(self) -> str:
        return "SocialDataSource"

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
            return {"value": result.get("answer", ""), "source": "Social", "metadata": result}
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
        for platform, users in self._platforms.items():
            if platform in q:
                result = {"found": True, "answer": f"{platform}: {users}", "confidence": 1.0}
                break
        self._cache[q] = result
        return result
