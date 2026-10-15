"""
[OPT-13] UNESCODataSource — UNESCO Institute for Statistics (UIS) API.

DNA SCP: SuperGPQA Education discipline needs verifiable global education
indicators (literacy rates, school enrollment, teacher-pupil ratios, gender
parity). ERIC covers research papers; UNESCO UIS covers country-level stats.
Basic UIS queries are free without an API key — fills the stats gap.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.unesco")

# [AUDIT-20260909 SSRF-S1] indicator/country code dạng ràng buộc (dù đến từ
# fixed maps, builder vẫn fail-closed với mọi input khác).
_UNESCO_INDICATOR_RE = re.compile(r"^[A-Za-z0-9._]{2,32}$")
_UNESCO_COUNTRY_RE = re.compile(r"^[A-Za-z]{2,3}$")
_UNESCO_DATA_URL = "https://api.uis.unesco.org/public/publicdata/report"


def build_unesco_indicator_url(indicator_code: str,
                               country_code: str | None = None) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — indicator PHẢI khớp
    ^[A-Za-z0-9._]{2,32}$, country (nếu có) ^[A-Za-z]{2,3}$; input xấu →
    ValueError TRƯỚC KHI fetch. Host cố định api.uis.unesco.org."""
    ind = str(indicator_code or "")
    if not _UNESCO_INDICATOR_RE.fullmatch(ind):
        raise ValueError(f"invalid_indicator_code:{ind[:32]!r}")
    params = {
        "indicator": ind,
        "format": "json",
        "sort": "desc",
        "max": 1,
    }
    if country_code is not None:
        cc = str(country_code or "")
        if not _UNESCO_COUNTRY_RE.fullmatch(cc):
            raise ValueError(f"invalid_country_code:{cc[:16]!r}")
        params["country"] = cc
    return f"{_UNESCO_DATA_URL}?{urllib.parse.urlencode(params)}"


class UNESCODataSource(IDataSource):
    """UNESCO UIS API — education statistics, literacy, enrollment (no key)."""

    BASE_URL = "https://api.uis.unesco.org"
    # UIS public data endpoint — returns JSON
    DATA_URL = "https://api.uis.unesco.org/public/publicdata/report"

    # Indicator codes (UIS SDG / education indicators)
    INDICATOR_MAP = {
        "literacy": "LR.LIT.TOTL.ZS",  # Adult literacy rate
        "literacy rate": "LR.LIT.TOTL.ZS",
        "youth literacy": "LR.LIT.YOUT.ZS",
        "adult literacy": "LR.LIT.ADLT.ZS",
        "primary enrollment": "SE.PRM.ENRR",  # Primary school net enrollment
        "secondary enrollment": "SE.SEC.ENRR",
        "tertiary enrollment": "SE.TER.ENRR",
        "pupil teacher": "SE.PRM.ENRL.TC.ZS",
        "teacher pupil": "SE.PRM.ENRL.TC.ZS",
        "gender parity": "UIS.GPI.1",
        "out of school": "RO.PT.OOS.1",
        "compulsory education": "ED.UNI.EDAGE",
    }

    COUNTRY_MAP = {
        "việt nam": "VN", "vietnam": "VN",
        "usa": "US", "united states": "US",
        "china": "CN", "trung quốc": "CN",
        "japan": "JP", "nhật bản": "JP",
        "india": "IN", "ấn độ": "IN",
        "indonesia": "ID",
        "brazil": "BR",
        "nigeria": "NG",
        "pakistan": "PK",
        "bangladesh": "BD",
        "ethiopia": "ET",
        "philippines": "PH",
        "germany": "DE",
        "france": "FR",
        "uk": "GB", "united kingdom": "GB",
    }

    def __init__(self):
        # UNESCO UIS basic queries are free, no key required
        self.enabled = True
        logger.info("[UNESCO] enabled (no API key required)")

    @property
    def name(self) -> str:
        return "unesco"

    @property
    def priority(self) -> int:
        return 15  # mid-low — education stats niche

    @property
    def ttl(self) -> int:
        return 86400  # 24h — UIS publishes annually

    def get_supported_intents(self) -> list[str]:
        return ["education", "literacy", "school_enrollment", "teacher_ratio",
                "gender_parity", "education_stats"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        question = intent or ""
        q = question.lower()
        keywords = [
            "literacy", "xóa mù chữ", "biết chữ",
            "enrollment", "nhập học",
            "school", "trường học",
            "pupil teacher", "giáo viên học sinh",
            "gender parity", "bình đẳng giới",
            "education stats", "thống kê giáo dục",
            "unesco", "out of school",
            "compulsory education", "giáo dục bắt buộc",
        ]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (api.uis.unesco.org). Trước đây hardcode `return self.enabled`
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
        return reachability_ping('https://api.uis.unesco.org/public/publicdata/report')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            q = question.lower()
            indicator_code = None
            indicator_label = None
            for keyword, code in self.INDICATOR_MAP.items():
                if keyword in q:
                    indicator_code = code
                    indicator_label = keyword
                    break
            if not indicator_code:
                return None
            country_code = None
            for name, code in self.COUNTRY_MAP.items():
                if name in q:
                    country_code = code
                    break
            return self._query_indicator(indicator_code, indicator_label, country_code)
        except Exception as e:
            logger.debug(f"[UNESCO] query failed: {e}", exc_info=True)
            return None

    def _query_indicator(self, indicator_code: str, label: str,
                          country_code: str | None = None) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder validate + urlencode codes rồi
            # fetch qua safe_urlopen thay raw httpx.get.
            url = build_unesco_indicator_url(indicator_code, country_code)
            req = urllib.request.Request(
                url, headers={"User-Agent": "SCP-Verifier/1.0"}
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            # UIS JSON shape varies; try common keys
            records = (data.get("result", {}).get("data", [])
                       if isinstance(data, dict)
                       else (data[1] if isinstance(data, list) and len(data) >= 2 else []))
            if isinstance(records, list) and records:
                rec = records[0]
                return {
                    "value": rec.get("value") or rec.get("Value") or "",
                    "source": "unesco",
                    "metadata": {
                        "indicator": label,
                        "indicator_code": indicator_code,
                        "country": rec.get("country") or rec.get("Country") or
                                   (country_code or "WLD"),
                        "year": rec.get("year") or rec.get("Year") or "",
                        "unit": rec.get("unit") or rec.get("Unit") or "%",
                    },
                }
            return None
        except Exception as e:
            logger.debug(f"[UNESCO] indicator {indicator_code} query failed: {e}", exc_info=True)
            return None
