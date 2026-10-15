"""
SCP - Viet Nam | Self-Correcting Pipeline
 MilitaryDataSource - Data source cho Quân sự
"""

import logging
import re
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


def _wb_match(key: str, text_lower: str) -> bool:
    """[ROOT-FIX 4] Word-boundary match — prevents 'usa' matching 'b**usa**',
    'uk' matching 'b**uk**'/'y**uk**'/'d**uk**e', etc.
    Uses Unicode-aware lookarounds so Vietnamese diacritics work too.
    """
    if not key or not text_lower:
        return False
    if key == text_lower:
        return True
    pattern = r'(?<![\wÀ-ỹ])' + re.escape(key) + r'(?![\wÀ-ỹ])'
    return bool(re.search(pattern, text_lower))


class MilitaryDataSource(IDataSource):
    """Data source cho Quân sự."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Nuclear weapons states
        self._nuclear = {
            "usa": {"warheads": "~3700", "status": "Active"},
            "russia": {"warheads": "~4400", "status": "Active"},
            "france": {"warheads": "~300", "status": "Active"},
            "china": {"warheads": "~350", "status": "Active"},
            "uk": {"warheads": "~200", "status": "Active"},
            "india": {"warheads": "~160", "status": "Active"},
            "pakistan": {"warheads": "~165", "status": "Active"},
            "israel": {"warheads": "~80-400", "status": "Undisclosed"},
            "north korea": {"warheads": "~30-40", "status": "Active"},
        }

        # Aircraft carriers by country
        self._carriers = {
            "usa": 11,
            "china": 3,
            "uk": 2,
            "italy": 2,
            "india": 2,
            "japan": 4,
            "france": 1,
            "russia": 1,
            "thailand": 1,
            "brazil": 1,
            "spain": 1,
            "south korea": 2,
        }

        # ICBM ranges
        self._icbm = {
            "minuteman iii": {"range": "13000 km", "country": "USA"},
            "topol m": {"range": "11000 km", "country": "Russia"},
            "df-41": {"range": "14000 km", "country": "China"},
            "ss-27": {"range": "11000 km", "country": "Russia"},
            "arsenal": {"range": "200-300 km", "country": "Various"},
        }

        # Major military exercises
        self._exercises = {
            "red flag": "US Air Force exercise, Alaska",
            "rim of the pacific": "US Navy, Hawaii",
            "cobras": "France-Brazil joint exercise",
            "malabar": "India-Japan-US-Australia",
            "bangkok": "SE Asian exercises",
        }

    def query(self, question: str) -> dict[str, Any]:
        q = question.lower().strip()
        if q in self._cache:
            return self._cache[q]

        result = {"found": False, "answer": None, "confidence": 0.0}

        # Check nuclear
        for country, info in self._nuclear.items():
            # [ROOT-FIX 4] Was `country in q` — substring match → 'usa' matched
            # 'abusan', 'uk' matched 'buk'/'yuk'/'duke', etc. Use word-boundary.
            if _wb_match(country, q):
                result = {
                    "found": True,
                    "answer": f"{country} nuclear: ~{info['warheads']} warheads, {info['status']}",
                    "confidence": 0.9,
                    "source": "Military Database"
                }
                break

        # Check carriers
        if not result["found"]:
            for country, count in self._carriers.items():
                # [ROOT-FIX 4] Same substring → word-boundary fix.
                if _wb_match(country, q) and (_wb_match("carrier", q) or "tàu sân bay" in q):
                    result = {
                        "found": True,
                        "answer": f"{country}: {count} aircraft carriers",
                        "confidence": 0.9,
                        "source": "Military Database"
                    }
                    break

        # Check ICBM
        if not result["found"]:
            for missile, info in self._icbm.items():
                # [ROOT-FIX 4] Same substring → word-boundary fix.
                # [V104.32 #15] was: OR clause matched generic ICBM, returned first missile
                if _wb_match(missile, q):
                    result = {
                        "found": True,
                        "answer": f"{missile}: tầm {info['range']} ({info['country']})",
                        "confidence": 0.9,
                        "source": "Military Database"
                    }
                    break

        self._cache[q] = result
        return result

    @property
    def name(self) -> str:
        return "MilitaryDataSource"

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
            return {"value": result.get("answer", ""), "source": "Military", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True
