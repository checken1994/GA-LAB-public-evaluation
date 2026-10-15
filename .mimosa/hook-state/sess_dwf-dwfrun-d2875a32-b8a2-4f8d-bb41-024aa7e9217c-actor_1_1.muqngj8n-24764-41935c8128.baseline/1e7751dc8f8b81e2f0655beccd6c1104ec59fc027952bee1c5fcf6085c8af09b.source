"""
[OPT-9] FREDDataSource — Federal Reserve Economic Data (St. Louis Fed).

DNA SCP: don't trust single source. WorldBank alone = SPOF for economics.
FRED provides US economic indicators (GDP, inflation, unemployment, interest rates).
Free API: https://fred.stlouisfed.org/docs/api/api_key.html
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.fred")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builder.
_FRED_OBS_URL = "https://api.stlouisfed.org/fred/series/observations"

# FRED series_id: chữ hoa + chữ số, 2–20 ký tự (vd GDP, GS10, CPIAUCSL,
# A191RL1Q225SBEA) — chặn dấu chấm/gạch chéo (path traversal).
_FRED_SERIES_RE = None  # lazy import re để giữ import-time nhẹ


def build_fred_observations_url(series_id: str, api_key: str,
                                limit: int = 1) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — series_id PHẢI fullmatch
    [A-Z0-9]{2,20} (input xấu → ValueError TRƯỚC KHI fetch, fail-closed);
    api_key được urlencode. Host cố định api.stlouisfed.org."""
    global _FRED_SERIES_RE
    if _FRED_SERIES_RE is None:
        import re as _re
        _FRED_SERIES_RE = _re.compile(r"^[A-Z0-9]{2,20}$")
    sid = str(series_id or "").strip()
    if not _FRED_SERIES_RE.fullmatch(sid):
        raise ValueError(f"invalid_fred_series_id:{sid[:32]!r}")
    return _FRED_OBS_URL + "?" + urllib.parse.urlencode({
        "series_id": sid,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": int(limit),
    })


class FREDDataSource(IDataSource):
    """FRED API — US economic indicators (GDP, inflation, unemployment, rates)."""

    BASE_URL = "https://api.stlouisfed.org/fred"

    # Common FRED series IDs — used to map question keywords → series
    SERIES_MAP = {
        "gdp": "GDP",                    # Gross Domestic Product
        "gdp growth": "A191RL1Q225SBEA", # Real GDP growth rate
        "inflation": "CPIAUCSL",          # Consumer Price Index
        "cpi": "CPIAUCSL",
        "unemployment": "UNRATE",         # Civilian Unemployment Rate
        "interest rate": "FEDFUNDS",      # Federal Funds Effective Rate
        "fed funds": "FEDFUNDS",
        "federal funds": "FEDFUNDS",
        "population": "POPTHM",           # Population
        "10 year treasury": "GS10",       # 10-Year Treasury Constant Maturity Rate
        "10-year treasury": "GS10",
        "house price": "CSUSHPINSA",      # S&P/Case-Shiller Home Price Index
    }

    def __init__(self):
        self.api_key = os.environ.get("FRED_API_KEY", "")
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.info("[FRED] disabled — set FRED_API_KEY to enable")

    @property
    def name(self) -> str:
        return "fred"

    @property
    def priority(self) -> int:
        return 10  # lower priority than AlphaVantage (priority 10) — equal weight

    @property
    def ttl(self) -> int:
        return 3600  # 1h cache

    def get_supported_intents(self) -> list[str]:
        return ["gdp", "inflation", "unemployment", "interest_rate", "economics"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        # Question-based (legacy compat)
        question = intent or ""
        q = question.lower()
        keywords = ["gdp", "inflation", "lạm phát", "unemployment", "thất nghiệp",
                    "interest rate", "lãi suất", "cpi", "federal funds", "fed funds",
                    "treasury", "federal reserve"]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (api.stlouisfed.org). Trước đây hardcode `return self.enabled`
        — constructor config, không phải live evidence (fail-open). Không có API key → False ngay (không thể serve — fail-closed); có key
        → reachability ping. Bất kỳ HTTP
        response nào (kể cả 4xx do thiếu key/tham số) chứng minh service
        sống; exception (egress denied, DNS, timeout) → False.

        Kết quả đi qua shared negative-result cache cross-instance
        (`shared_health_ping`): trong TTL (SCP_HEALTH_NEG_CACHE_TTL,
        default 60s) các lần gọi sau trả lại quan sát gần nhất — kể cả
        False (đó là reality gần nhất, không fake health) — mà KHÔNG
        re-ping."""
        if not self.enabled:
            # Không có API key → source không thể serve — fail-closed, không ping.
            return False
        return shared_health_ping(type(self).__name__, self._live_ping)

    def _live_ping(self) -> bool:
        """[V104.32] Ping thật — 1 network round-trip tới URL cố định,
        không chứa key; HTTP response nào cũng = endpoint sống."""
        return reachability_ping('https://api.stlouisfed.org/fred/series/observations')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            q = question.lower()
            # Find matching series
            for keyword, series_id in self.SERIES_MAP.items():
                if keyword in q:
                    return self._query_series(series_id, keyword)
            return None
        except Exception as e:
            logger.debug(f"[FRED] query failed: {e}", exc_info=True)
            return None

    def _query_series(self, series_id: str, label: str) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder fullmatch regex + safe_urlopen
            # thay raw httpx.get; input xấu → ValueError, non-200 → HTTPError.
            req = urllib.request.Request(
                build_fred_observations_url(series_id, api_key=self.api_key)
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            observations = data.get("observations", [])
            if observations:
                obs = observations[0]
                return {
                    "value": obs.get("value", ""),
                    "source": "fred",
                    "metadata": {
                        "series_id": series_id,
                        "label": label,
                        "date": obs.get("date", ""),
                        "realtime_start": obs.get("realtime_start", ""),
                    },
                }
        except Exception as e:
            logger.debug(f"[FRED] series {series_id} query failed: {e}", exc_info=True)
        return None
