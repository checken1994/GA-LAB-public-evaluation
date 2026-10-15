""" CartographyDataSource"""
import logging
import re

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


def _wb_match(key: str, text_lower: str) -> bool:
    """[ROOT-FIX 4] Word-boundary match — prevents 'UTM' matching 'b**utm**us',
    'peters' matching 'petersen', etc. Uses Unicode-aware lookarounds.
    """
    if not key or not text_lower:
        return False
    if key == text_lower:
        return True
    pattern = r'(?<![\wÀ-ỹ])' + re.escape(key) + r'(?![\wÀ-ỹ])'
    return bool(re.search(pattern, text_lower))

class CartographyDataSource(IDataSource):
    def __init__(self):
        self._cache = {}
        self._projections = {
            "mercator": "Preserves angles, distorts size",
            "peters": "Equal area, distorts shape",
            "robinson": "Compromise projection",
            "UTM": "Universal Transverse Mercator",
        }

    @property
    def name(self) -> str:
        return "CartographyDataSource"

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
            return {"value": result.get("answer", ""), "source": "Cartography", "metadata": result}
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
        for proj, desc in self._projections.items():
            # [ROOT-FIX 4] Was `proj in q` — substring match → 'UTM' (3 chars)
            # matched 'butmus'/'cutmost', 'peters' matched 'petersen'. Use word-boundary.
            if _wb_match(proj.lower(), q.lower()):
                result = {"found": True, "answer": f"{proj}: {desc}", "confidence": 1.0}
                break
        self._cache[q] = result
        return result
