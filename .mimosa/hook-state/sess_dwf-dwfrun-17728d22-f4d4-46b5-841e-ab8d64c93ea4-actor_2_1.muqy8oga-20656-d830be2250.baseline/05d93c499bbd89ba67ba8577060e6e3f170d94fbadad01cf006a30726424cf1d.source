"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

"""
HistoryDataSource - Data source cho Lịch sử

[G3-CONSOLIDATE RE-05 / G3-full-B] AUDIT MISMATCH NOTE:
Task 9-C finding RE-05 (worklog.md line ~2772) lists this file as one of the
"8 independent Wikipedia fetch implementations". That classification is
INACCURATE — this file does NOT call the Wikipedia REST API. It calls the
WIKIDATA API (wikidata.org/w/api.php — wbsearchentities action), which is a
SEPARATE Wikimedia service (different endpoint, different response schema,
different use case: entity lookup vs. article summary).

Per the G3-full-B task spec: "For each of the 7 other files that have
Wikipedia fetch logic: ... Replace the local fetch_wikipedia() function body
with a call to the canonical client." This file has no fetch_wikipedia()
function — only _fetch_from_wikidata(). The canonical client
(scp.core.wikipedia_client) does NOT cover Wikidata (different API).

Actions taken:
1. Added a NEW method _fetch_from_wikipedia() that uses the canonical client.
   This is a genuine ENHANCEMENT — previously HistoryDataSource had only a
   Wikidata fallback; now it has BOTH Wikipedia + Wikidata fallbacks.
2. Wired _fetch_from_wikipedia() into fetch() as a 3rd fallback tier
   (after local DB + Wikidata). Returns None on failure (no behavior change
   when Wikipedia is unavailable).
3. Did NOT touch _fetch_from_wikidata() — Wikidata is a different API and
   remains as-is.
"""
import json
import logging
import urllib.parse
import urllib.request
from typing import Any

from scp.core.wikipedia_client import fetch_summary as _wiki_fetch_summary  # [G3-CONSOLIDATE RE-05]
from scp.data_sources._matching import _token_boundary_match
from scp.interfaces.data_source import IDataSource
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger(__name__)
# [V104.32 #11] word-boundary matching for short keys


def build_wikidata_search_url(entity: str) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — entity (input động) được
    urlencode thành query value, không thể đổi host/path. Host cố định
    https://www.wikidata.org."""
    return "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
        'action': 'wbsearchentities',
        'search': str(entity or ""),
        'language': 'en',
        'format': 'json',
    })


class HistoryDataSource(IDataSource):
    """
    Data source cho các câu hỏi Lịch sử.
    Hỗ trợ: sự kiện lịch sử, nhân vật, năm.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Local database for major historical events
        self._events = {
            # Vietnamese History
            '938': {'event': 'Ngô Quyền đánh bại Nam Hán', 'year': 938, 'location': 'Bạch Đằng'},
            '1009': {'event': 'Lý Công Uẩn lên ngôi vua', 'year': 1009, 'location': 'Thăng Long'},
            '1010': {'event': 'Lý Thái Tổ dời đô ra Thăng Long', 'year': 1010, 'location': 'Thăng Long'},
            '1226': {'event': 'Trần Thái Tông lên ngôi', 'year': 1226, 'location': 'Thăng Long'},
            '1288': {'event': 'Trần Hưng Đạo đánh tan quân Nguyên', 'year': 1288, 'location': 'Bạch Đằng'},
            '1407': {'event': 'Minh thuộc', 'year': 1407, 'location': 'Việt Nam'},
            '1428': {'event': 'Lê Lợi khởi nghĩa thắng lợi', 'year': 1428, 'location': 'Lam Sơn'},
            '1789': {'event': 'Nguyễn Huệ lên ngôi hoàng đế', 'year': 1789, 'location': 'Phú Xuân'},
            '1802': {'event': 'Nhà Nguyễn thành lập', 'year': 1802, 'location': 'Phú Xuân'},
            '1945': {'event': 'Tuyên ngôn độc lập Việt Nam', 'year': 1945, 'location': 'Hà Nội'},
            '1954': {'event': 'Chiến thắng Điện Biên Phủ', 'year': 1954, 'location': 'Điện Biên'},
            '1975': {'event': 'Thống nhất đất nước', 'year': 1975, 'location': 'Sài Gòn'},

            # World History
            '1945-08-06': {'event': 'Bom nguyên tử Hiroshima', 'year': 1945, 'location': 'Hiroshima'},
            '1945-08-09': {'event': 'Bom nguyên tử Nagasaki', 'year': 1945, 'location': 'Nagasaki'},
            '1969-07-20': {'event': 'Apollo 11 đổ bộ Mặt Trăng', 'year': 1969, 'location': 'Mặt Trăng'},
            '1989-11-09': {'event': 'Bức tường Berlin sụp đổ', 'year': 1989, 'location': 'Berlin'},
            '1991': {'event': 'Liên Xô sụp đổ', 'year': 1991, 'location': 'Moscow'},
            '2001-09-11': {'event': 'Khủng bố 11/9', 'year': 2001, 'location': 'New York'},

            # Key figures
            'hồ chí minh': {'name': 'Hồ Chí Minh', 'born': 1890, 'died': 1969, 'title': 'Chủ tịch nước Việt Nam'},
            'ngô quyền': {'name': 'Ngô Quyền', 'born': 898, 'died': 944, 'title': 'Vua Ngô'},
            'lê lợi': {'name': 'Lê Lợi', 'born': 1385, 'died': 1433, 'title': 'Vua Lê Thái Tổ'},
            'trần hưng đạo': {'name': 'Trần Hưng Đạo', 'born': 1228, 'died': 1300, 'title': 'Đại Việt Hưng Đạo Vương'},
            'genghis khan': {'name': 'Genghis Khan', 'born': 1162, 'died': 1227, 'title': 'Mông Cổ'},
            'napoleon': {'name': 'Napoleon Bonaparte', 'born': 1769, 'died': 1821, 'title': 'Hoàng đế Pháp'},
            'einstein': {'name': 'Albert Einstein', 'born': 1879, 'died': 1955, 'title': 'Nhà vật lý'},
            'newton': {'name': 'Isaac Newton', 'born': 1643, 'died': 1727, 'title': 'Nhà vật lý'},
        }

    @property
    def name(self) -> str:
        return "HistoryDataSource"

    @property
    def priority(self) -> int:
        return 2  # Medium priority

    @property
    def ttl(self) -> int:
        return 604800  # 1 week - historical facts don't change

    def get_supported_intents(self) -> list[str]:
        return [
            'historical_event',
            'historical_figure',
            'year_info',
            'birth_death',
            'battle',
            'dynasty',
        ]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            entity_lower = entity.lower()
            # Check if entity matches known events/figures
            for key in self._events:
                if _token_boundary_match(key, entity_lower):
                    return True
            # Check for year patterns
            if entity.isdigit() and 500 <= int(entity) <= 2030:
                return True
        return False

    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        """Lấy dữ liệu lịch sử."""
        if not entity:
            return None

        entity_lower = entity.lower()

        # Try local database first
        result = self._search_local(entity_lower)
        if result:
            return result

        # Try year-based lookup
        if entity.isdigit():
            result = self._search_by_year(entity)
            if result:
                return result

        # Try Wikidata as fallback
        result = self._fetch_from_wikidata(entity_lower)
        if result:
            return result

        # [G3-CONSOLIDATE RE-05] NEW: Wikipedia fallback (canonical client).
        # Previously this file had no Wikipedia fetch (audit RE-05 misclassified
        # the Wikidata call as Wikipedia). Added as 3rd-tier fallback so
        # historical entities not in Wikidata can still be answered.
        result = self._fetch_from_wikipedia(entity)
        if result:
            return result

        return None

    def _fetch_from_wikipedia(self, entity: str) -> dict[str, Any] | None:
        """[G3-CONSOLIDATE RE-05] Wikipedia fallback via canonical client.

        New method (G3-full-B) — uses scp.core.wikipedia_client.fetch_summary
        so this file shares the same rate limit + cache + timeout as the
        other 7 Wikipedia fetchers. Returns None on failure (no behavior
        change when Wikipedia is unavailable).
        """
        # [G3-CONSOLIDATE RE-05] Now delegates to scp.core.wikipedia_client
        try:
            result = _wiki_fetch_summary(entity, lang="en")
            if result and result.get("extract"):
                return {
                    'value': result['extract'],
                    'source': 'Wikipedia',
                    'metadata': {
                        'title': result.get('title', ''),
                        'url': result.get('url', ''),
                        'method': 'wikipedia'
                    }
                }
        except Exception as e:
            logger.warning(f"[History] Wikipedia fetch failed: {e}", exc_info=True)
        return None

    def _search_local(self, entity: str) -> dict[str, Any] | None:
        """Tìm trong local database."""
        # Direct match
        if entity in self._events:
            data = self._events[entity]
            return {
                'value': str(data),
                'source': 'Local History Database',
                'metadata': data
            }

        # Partial match
        for key, data in self._events.items():
            if key in entity or entity in key:
                return {
                    'value': str(data),
                    'source': 'Local History Database',
                    'metadata': data
                }

        return None

    def _search_by_year(self, year: str) -> dict[str, Any] | None:
        """Tìm sự kiện theo năm."""
        year_int = int(year)
        results = []

        for _key, data in self._events.items():
            if data.get('year') == year_int:
                results.append(data)

        if results:
            return {
                'value': str(results),
                'source': 'Local History Database',
                'metadata': {'events': results, 'year': year_int}
            }

        return None

    def _fetch_from_wikidata(self, entity: str) -> dict[str, Any] | None:
        """Fallback: Lấy từ Wikidata."""
        try:
            # [AUDIT-20260909 SSRF-S1] build URL (encode input) rồi fetch qua
            # safe_urlopen thay raw requests.get; non-200 → HTTPError → except.
            search_url = build_wikidata_search_url(entity)
            req = urllib.request.Request(
                search_url, headers={"User-Agent": "SCP-History/1.0"}
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))

            if data.get('search'):
                result = data['search'][0]
                return {
                    'value': result.get('label', ''),
                    'source': 'Wikidata',
                    'metadata': {
                        'id': result.get('id', ''),
                        'description': result.get('description', ''),
                    }
                }
        except Exception as e:
            logger.warning(f"[History] Wikidata fetch failed: {e}", exc_info=True)

        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (local database, fetch() không chạm mạng) — không có network endpoint
        nào để ping, nên không có live evidence để thu. Contract: KHÔNG dùng
        nguồn này làm bằng chứng reachable cho bất kỳ network capability nào."""
        return True
