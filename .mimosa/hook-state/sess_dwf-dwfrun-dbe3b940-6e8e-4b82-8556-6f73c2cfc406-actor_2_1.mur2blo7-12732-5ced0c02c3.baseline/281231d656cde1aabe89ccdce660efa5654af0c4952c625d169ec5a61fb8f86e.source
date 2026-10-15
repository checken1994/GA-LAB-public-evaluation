"""
SCP - Viet Nam | Self-Correcting Pipeline
[V96+V5.8-API] AgricultureDataSource - Data source cho Nông nghiệp

[V5.8-API] NEW data source (was missing in v5.7 — registered in __init__.py).
Wires USDA NASS QuickStats API (crop/livestock stats) with local DB fallback.
"""

import logging
import os
from typing import Any

from scp.core.api_utils import fetch_with_retry  # [V5.8-API]
from scp.interfaces.data_source import IDataSource, shared_health_ping

logger = logging.getLogger(__name__)


class AgricultureDataSource(IDataSource):
    """
    Data source cho các câu hỏi Nông nghiệp.
    Hỗ trợ: crop data, livestock stats, commodity prices, agricultural facts.
    [V5.8-API] USDA NASS QuickStats integration with local DB fallback.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}
        # [V5.8-API] USDA NASS QuickStats API key
        # Register at https://quickstats.nass.usda.gov/api (free)
        self._usda_api_key = os.environ.get("USDA_API_KEY", "").strip()

        # Local DB (fallback when API key missing or call fails)
        self._crops = {
            "rice": {"vi": "Lúa", "unit": "cwt/acre", "season": "annual"},
            "lúa": {"vi": "Lúa", "en": "Rice", "unit": "cwt/acre", "season": "annual"},
            "wheat": {"vi": "Lúa mì", "unit": "bu/acre", "season": "annual"},
            "corn": {"vi": "Ngô", "unit": "bu/acre", "season": "annual"},
            "ngô": {"vi": "Ngô", "en": "Corn", "unit": "bu/acre", "season": "annual"},
            "soybean": {"vi": "Đậu nành", "unit": "bu/acre", "season": "annual"},
            "coffee": {"vi": "Cà phê", "unit": "lb/acre", "season": "annual"},
            "cà phê": {"vi": "Cà phê", "en": "Coffee", "unit": "lb/acre", "season": "annual"},
            "cotton": {"vi": "Bông", "unit": "lb/acre", "season": "annual"},
            "sugarcane": {"vi": "Mía", "unit": "ton/acre", "season": "annual"},
        }

        # Livestock
        self._livestock = {
            "cattle": {"vi": "Bò", "unit": "head", "top_producers": ["India", "Brazil", "China"]},
            "bò": {"vi": "Bò", "en": "Cattle", "unit": "head"},
            "pigs": {"vi": "Lợn", "unit": "head", "top_producers": ["China", "USA", "Spain"]},
            "lợn": {"vi": "Lợn", "en": "Pigs", "unit": "head"},
            "heo": {"vi": "Heo", "en": "Pigs", "unit": "head"},
            "chickens": {"vi": "Gà", "unit": "head"},
            "gà": {"vi": "Gà", "en": "Chickens", "unit": "head"},
            "sheep": {"vi": "Cừu", "unit": "head"},
            "goats": {"vi": "Dê", "unit": "head"},
        }

        # Common facts
        self._facts = {
            "paddy rice vietnam yield": "5.8 ton/ha (Vietnam avg)",
            "coffee vietnam production": "~1.8M bags (60kg) — #2 exporter globally",
            "rice world production": "~500M metric tons annually",
            "wheat world production": "~770M metric tons annually",
            "corn world production": "~1.1B metric tons annually",
        }

    @property
    def name(self) -> str:
        return "AgricultureDataSource"

    @property
    def priority(self) -> int:
        return 5

    @property
    def ttl(self) -> int:
        return 86400

    def get_supported_intents(self) -> list[str]:
        return ["lookup", "query", "fact", "agriculture_crop", "agriculture_livestock"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            e = entity.lower().strip()
            for table in (self._crops, self._livestock, self._facts):
                if e in table:
                    return True
        return True  # permissive — let fetch() try API + local

    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        result = self.query(entity or intent)
        if result.get("found"):
            return {
                "value": result.get("answer", ""),
                "source": "Agriculture",
                "metadata": result,
            }
        return None

    def health_check(self) -> bool:
        """[AUDIT-FIX low-4] Fail-closed: ping REACHABILITY của endpoint USDA
        NASS QuickStats mà fetch() thực sự dùng. Trước đây
        hardcode `return True` — fail-open, không có bằng chứng. Bất kỳ HTTP
        response nào (kể cả 4xx do thiếu key) chứng minh service sống; exception
        (egress denied, DNS, timeout) → False. Local dataset không được OR vào
        kết quả — nó là trạng thái degraded, chỉ báo qua log.

        [V104.32] Kết quả ping đi qua shared negative-result cache
        cross-instance (`shared_health_ping`): trong TTL
        (SCP_HEALTH_NEG_CACHE_TTL, default 60s) các lần gọi sau trả lại quan
        sát gần nhất — kể cả False (đó là reality gần nhất, không fake health)
        — mà KHÔNG re-ping."""
        import time
        healthy = shared_health_ping(type(self).__name__, self._live_ping)
        self._cache['_health_cache'] = healthy
        self._cache['_health_cache_ts'] = time.time()
        return healthy

    def _live_ping(self) -> bool:
        """[V104.32] Ping thật (1 network round-trip) — chỉ gọi qua
        shared_health_ping để được dedupe theo TTL."""
        api_ok = False
        try:
            from scp.security.url_safety import safe_urlopen  # [AUDIT-FIX low-4]
            # URL cố định, không chứa key — ping reachability thuần.
            with safe_urlopen("https://quickstats.nass.usda.gov/api/api_GET/?format=JSON", timeout=3):
                api_ok = True
        except Exception as e:
            logger.warning(f"[Agriculture] health ping failed: {e}", exc_info=True)
        if not api_ok:
            logger.warning(
                "[Agriculture] health_check: USDA endpoint unreachable — báo unhealthy "
                "(fail-closed); local dataset vẫn trả lời được query (degraded)"
            )
        return api_ok

    def query(self, question: str) -> dict[str, Any]:
        """Query agriculture data."""
        q = question.lower().strip() if isinstance(question, str) else ""

        if q in self._cache:
            return self._cache[q]

        result: dict[str, Any] = {"found": False, "answer": None, "confidence": 0.0}

        # Check crops
        for crop, info in self._crops.items():
            if crop in q:
                result = {
                    "found": True,
                    "answer": f"{crop}: {info.get('vi', crop)} ({info.get('unit', 'n/a')})",
                    "confidence": 1.0,
                    "source": "Agriculture Local Database",
                }
                break

        # Check livestock
        if not result.get("found"):
            for animal, info in self._livestock.items():
                if animal in q:
                    result = {
                        "found": True,
                        "answer": f"{animal}: {info.get('vi', animal)} ({info.get('unit', 'n/a')})",
                        "confidence": 1.0,
                        "source": "Agriculture Local Database",
                    }
                    break

        # Check facts
        if not result.get("found"):
            for fact, value in self._facts.items():
                if fact in q:
                    result = {
                        "found": True,
                        "answer": f"{fact}: {value}",
                        "confidence": 1.0,
                        "source": "Agriculture Local Database",
                    }
                    break

        # [V5.8-API] Local DB miss → try USDA NASS QuickStats.
        if not result.get("found"):
            api_result = self._fetch_from_usda(question)
            if api_result:
                result = api_result

        self._cache[q] = result
        return result

    # [V5.8-API] USDA NASS QuickStats integration
    def _fetch_from_usda(self, question: str) -> dict[str, Any] | None:
        """
        [V5.8-API] Query USDA NASS QuickStats API for crop/livestock statistics.
        Endpoint: https://quickstats.nass.usda.gov/api/api_GET/?key={KEY}&...
        Requires USDA_API_KEY. Skips gracefully when key is missing.
        """
        if not self._usda_api_key:
            # Without key USDA rejects — skip silently (local DB is fallback)
            return None
        if not question or not question.strip():
            return None

        # Extract commodity term from the question (strip stopwords)
        import re
        text = question.strip()
        cleaned = re.sub(
            r'\b(what|is|the|a|an|of|for|on|about|price|production|yield|stats|'
            r'thống|kê|của|về|sản|lượng|giá|cả|là|gì|tìm)\b',
            ' ', text, flags=re.IGNORECASE,
        ).strip()
        commodity = re.sub(r'\s+', ' ', cleaned).strip()
        if len(commodity) < 3:
            return None

        from urllib.parse import quote
        url = (
            f"https://quickstats.nass.usda.gov/api/api_GET/"
            f"?key={self._usda_api_key}"
            f"&commodity_desc={quote(commodity)}"
            f"&format=JSON&statisticcat_desc=PRODUCTION"
            f"&year__GE=2020&limit=5"
        )
        try:
            data = fetch_with_retry(url, headers={"User-Agent": "SCP/1.0"}, timeout=10)
            if not data:
                return None
            # USDA returns {"data": [ {commodity_desc, year, Value, unit_desc, ...}, ... ]}
            records = data.get('data', [])
            if not records:
                return None
            entries = []
            for r in records[:5]:
                comp = r.get('commodity_desc', '')
                year = r.get('year', '')
                val = r.get('Value', '')
                unit = r.get('unit_desc', '')
                state = r.get('state_name', '') or r.get('location_name', '')
                parts = [comp, str(year)]
                if state:
                    parts.append(state)
                if val:
                    parts.append(f"{val} {unit}".strip())
                entries.append(" — ".join(parts))
            if not entries:
                return None
            return {
                "found": True,
                "answer": "USDA QuickStats: " + " | ".join(entries),
                "confidence": 0.85,
                "source": "USDA NASS QuickStats API",
                "api": "usda_nass_quickstats",
                "commodity": commodity,
            }
        except Exception as e:
            logger.warning(f"[V5.8-API] USDA QuickStats fetch failed for '{commodity}': {e}", exc_info=True)
            return None
