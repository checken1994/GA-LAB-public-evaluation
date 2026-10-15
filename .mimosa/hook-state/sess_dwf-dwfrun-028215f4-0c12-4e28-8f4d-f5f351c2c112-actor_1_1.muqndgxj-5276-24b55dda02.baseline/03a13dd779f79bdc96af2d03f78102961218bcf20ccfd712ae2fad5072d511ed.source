"""
[OPT-10] WorldBankDataSource — World Bank Open Data API.

DNA SCP: cross-check FRED with World Bank for global indicators.
World Bank API is FREE, no API key needed — great fallback when FRED disabled.
Supports: country GDP, population, poverty stats for 200+ countries.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.worldbank")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builder.
_WORLDBANK_INDICATOR_URL = "https://api.worldbank.org/v2/country"

# Country/indicator codes: 3 chữ hoa ISO (hoặc 'all') / indicator path segment.
_COUNTRY_RE = None  # lazy import re để giữ import-time nhẹ


def build_worldbank_indicator_url(indicator_code: str,
                                  country: str = "all") -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — country PHẢI là 3 chữ cái
    (ISO alpha-3 hoặc 'all', fullmatch, chặn path traversal '..'); indicator
    được quote(safe='') để '/' và '.' không tạo path khác. Host cố định
    api.worldbank.org."""
    global _COUNTRY_RE
    if _COUNTRY_RE is None:
        import re as _re
        _COUNTRY_RE = _re.compile(r"^[A-Za-z]{3}$")
    c = str(country or "").strip()
    if not _COUNTRY_RE.fullmatch(c):
        raise ValueError(f"invalid_country_code:{c[:32]!r}")
    ind = urllib.parse.quote(str(indicator_code or ""), safe="")
    query = urllib.parse.urlencode({
        "format": "json",
        "per_page": 1,
        "date": "2020:2024",
        "sort": "desc",
    })
    return f"{_WORLDBANK_INDICATOR_URL}/{c}/indicator/{ind}?{query}"


class WorldBankDataSource(IDataSource):
    """World Bank API — global economic indicators (no key required)."""

    BASE_URL = "https://api.worldbank.org/v2"

    # World Bank indicator codes — see https://data.worldbank.org/indicator
    INDICATOR_MAP = {
        "gdp": "NY.GDP.MKTP.CD",          # GDP (current US$)
        "gdp per capita": "NY.GDP.PCAP.CD",  # GDP per capita (current US$)
        "population": "SP.POP.TOTL",       # Total population
        "life expectancy": "SP.DYN.LE00.IN",  # Life expectancy at birth
        "inflation": "FP.CPI.TOTL.ZG",     # Inflation, consumer prices (annual %)
        "unemployment": "SL.UEM.TOTL.ZS",  # Unemployment, total (% of labor force)
        "poverty": "SI.POV.DDAY",          # Poverty headcount ratio at $2.15/day
        "co2 emissions": "EN.ATM.CO2E.KT",  # CO2 emissions (kt)
        "internet users": "IT.NET.USER.ZS",  # Internet users (% of population)
    }

    # Common country names → ISO-2 codes
    COUNTRY_MAP = {
        "việt nam": "VN", "vietnam": "VN",
        "usa": "US", "mỹ": "US", "united states": "US",
        "china": "CN", "trung quốc": "CN",
        "japan": "JP", "nhật bản": "JP",
        "korea": "KR", "hàn quốc": "KR", "south korea": "KR",
        "india": "IN", "ấn độ": "IN",
        "germany": "DE", "đức": "DE",
        "france": "FR", "pháp": "FR",
        "uk": "GB", "anh": "GB", "united kingdom": "GB",
        "russia": "RU", "nga": "RU",
        "brazil": "BR", "bra-xin": "BR",
        "indonesia": "ID", "indo": "ID",
        "thailand": "TH", "thái lan": "TH",
    }

    def __init__(self):
        # World Bank API is free, no key needed
        self.enabled = True
        logger.info("[WorldBank] enabled (no API key required)")

    @property
    def name(self) -> str:
        return "worldbank"

    @property
    def priority(self) -> int:
        return 12  # lower priority than FRED (priority 10) — fallback

    @property
    def ttl(self) -> int:
        return 86400  # 24h cache — World Bank data doesn't change fast

    def get_supported_intents(self) -> list[str]:
        return ["gdp", "population", "inflation", "unemployment",
                "poverty", "life_expectancy", "economics"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        # Question-based (legacy compat)
        question = intent or ""
        q = question.lower()
        keywords = ["gdp", "population", "dân số", "inflation", "lạm phát",
                    "unemployment", "thất nghiệp", "poverty", "nghèo",
                    "life expectancy", "tuổi thọ", "co2", "internet users"]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (api.worldbank.org). Trước đây hardcode `return self.enabled`
        — constructor config, không phải live evidence (fail-open). Bất kỳ HTTP
        response nào (kể cả 4xx do thiếu key/tham số) chứng minh service
        sống; exception (egress denied, DNS, timeout) → False.

        Kết quả đi qua shared negative-result cache cross-instance
        (`shared_health_ping`): trong TTL (SCP_HEALTH_NEG_CACHE_TTL,
        default 60s) các lần gọi sau trả lại quan sát gần nhất — kể cả
        False (đó là reality gần nhất, không fake health) — mà KHÔNG
        re-ping."""
        return shared_health_ping(type(self).__name__, self._live_ping)

    def _live_ping(self) -> bool:
        """[V104.32] Ping thật — 1 network round-trip tới URL cố định,
        không chứa key; HTTP response nào cũng = endpoint sống."""
        return reachability_ping('https://api.worldbank.org/v2/country?format=json&per_page=1')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            q = question.lower()
            # Find matching indicator
            indicator_code = None
            indicator_label = None
            for keyword, code in self.INDICATOR_MAP.items():
                if keyword in q:
                    indicator_code = code
                    indicator_label = keyword
                    break
            if not indicator_code:
                return None
            # Find country
            country_code = None
            for name, code in self.COUNTRY_MAP.items():
                if name in q:
                    country_code = code
                    break
            return self._query_indicator(indicator_code, indicator_label, country_code)
        except Exception as e:
            logger.debug(f"[WorldBank] query failed: {e}", exc_info=True)
            return None

    def _query_indicator(self, indicator_code: str, label: str,
                          country_code: str | None = None) -> dict | None:
        try:
            country = country_code or "all"
            # [AUDIT-20260909 SSRF-S1] builder quote path + urlencode query +
            # safe_urlopen thay raw httpx.get; non-200 → HTTPError.
            req = urllib.request.Request(
                build_worldbank_indicator_url(indicator_code, country)
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            # World Bank returns [metadata, [observations]]
            if isinstance(data, list) and len(data) >= 2 and data[1]:
                obs = data[1][0]
                return {
                    "value": obs.get("value", ""),
                    "source": "worldbank",
                    "metadata": {
                        "indicator": label,
                        "indicator_code": indicator_code,
                        "country": obs.get("country", {}).get("value", country),
                        "country_code": country_code or "WLD",
                        "date": obs.get("date", ""),
                    },
                }
        except Exception as e:
            logger.debug(f"[WorldBank] indicator {indicator_code} query failed: {e}", exc_info=True)
        return None
