"""
[OPT-18] USGSDataSource — USGS Earthquake Hazards FDSNWS API.

DNA SCP: SuperGPQA Earth Science discipline needs real-time earthquake data
for verification (magnitude, depth, location, time). USGS FDSNWS event API is
the authoritative global earthquake feed (no key required). Short TTL=1800s
because earthquake feeds update continuously. Cross-checks
earthquake_magnitude_check antibody (added in Task 29-B).
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.usgs")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builder.
_USGS_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def build_usgs_query_url(params: dict) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — mọi param (starttime,
    endtime, minmagnitude...) được urlencode; host cố định earthquake.usgs.gov.
    starttime/enddate chỉ nhận YYYY-MM-DD (từ strftime nội bộ)."""
    clean = {str(k): v for k, v in (params or {}).items()}
    return _USGS_QUERY_URL + "?" + urllib.parse.urlencode(clean)


class USGSDataSource(IDataSource):
    """USGS FDSNWS Earthquake API — global quake events (no key required)."""

    BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1"

    def __init__(self):
        # USGS earthquake API is free, no key needed
        self.enabled = True
        logger.info("[USGS] enabled (no API key required)")

    @property
    def name(self) -> str:
        return "usgs"

    @property
    def priority(self) -> int:
        return 11  # high-mid — earth_science primary (quake data authoritative)

    @property
    def ttl(self) -> int:
        return 1800  # 30min — quake feeds update continuously

    def get_supported_intents(self) -> list[str]:
        return ["earthquake", "seismic", "magnitude", "quake",
                "geology", "earth_science", "seismology"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        question = intent or ""
        q = question.lower()
        keywords = [
            "earthquake", "động đất",
            "seismic", "địa chấn",
            "magnitude", "độ lớn",
            "quake", "rung chấn",
            "richter", "ring-ten",
            "usgs", "fault line",
            "tectonic", "kiến tạo",
            "seismology", "địa chấn học",
            "epicenter", "tâm chấn",
            "tsunami", "sóng thần",
            "geology", "địa chất",
        ]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (earthquake.usgs.gov). Trước đây hardcode `return self.enabled`
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
        return reachability_ping('https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=1')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            import re
            q = question.lower()
            # Extract magnitude if present (e.g., "magnitude 7.5")
            m = re.search(r'(?:magnitude\s*|mag\s*|mw\s*|ml\s*|richter\s*)(\d+\.?\d*)', q)
            if m:
                return self._query_min_magnitude(float(m.group(1)))
            # Extract date (e.g., "yesterday", "today", "last week")
            if "today" in q:
                return self._query_recent(days=1)
            if "yesterday" in q or "recent" in q:
                return self._query_recent(days=7)
            if "last week" in q or "past week" in q:
                return self._query_recent(days=7)
            if "last month" in q or "past month" in q:
                return self._query_recent(days=30)
            # Default — recent significant events (M >= 4.5)
            return self._query_min_magnitude(4.5)
        except Exception as e:
            logger.debug(f"[USGS] query failed: {e}", exc_info=True)
            return None

    def _query_min_magnitude(self, min_mag: float) -> dict | None:
        from datetime import datetime, timedelta, timezone

        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=30)
            # [AUDIT-20260909 SSRF-S1] builder urlencode + safe_urlopen thay
            # raw httpx.get; non-200 → HTTPError.
            req = urllib.request.Request(build_usgs_query_url({
                "format": "geojson",
                "starttime": start.strftime("%Y-%m-%d"),
                "endtime": end.strftime("%Y-%m-%d"),
                "minmagnitude": min_mag,
                "limit": 5,
                "orderby": "magnitude",
            }))
            with safe_urlopen(req, timeout=10) as r:  # noqa: S310 — validated by safe_urlopen
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            features = data.get("features", [])
            if not features:
                return None
            top = features[0]
            props = top.get("properties", {})
            geom = top.get("geometry", {})
            coords = geom.get("coordinates", [None, None, None])
            return {
                "value": f"M{props.get('mag', '?')} - {props.get('place', '?')}",
                "source": "usgs",
                "metadata": {
                    "magnitude": props.get("mag"),
                    "mag_type": props.get("magType", ""),
                    "place": props.get("place", ""),
                    "time": props.get("time"),
                    "updated": props.get("updated"),
                    "url": props.get("url", ""),
                    "tsunami": props.get("tsunami", 0) == 1,
                    "sig": props.get("sig", 0),
                    "depth_km": coords[2] if len(coords) >= 3 else None,
                    "longitude": coords[0] if len(coords) >= 1 else None,
                    "latitude": coords[1] if len(coords) >= 2 else None,
                    "felt_reports": props.get("felt", 0),
                    "result_count": data.get("metadata", {}).get("count", len(features)),
                },
            }
        except Exception as e:
            logger.debug(f"[USGS] min_mag query failed: {e}", exc_info=True)
            return None

    def _query_recent(self, days: int = 7) -> dict | None:
        from datetime import datetime, timedelta, timezone

        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=days)
            # [AUDIT-20260909 SSRF-S1] builder urlencode + safe_urlopen thay
            # raw httpx.get; non-200 → HTTPError.
            req = urllib.request.Request(build_usgs_query_url({
                "format": "geojson",
                "starttime": start.strftime("%Y-%m-%d"),
                "endtime": end.strftime("%Y-%m-%d"),
                "minmagnitude": 2.5,
                "limit": 10,
                "orderby": "time",
            }))
            with safe_urlopen(req, timeout=10) as r:  # noqa: S310 — validated by safe_urlopen
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            features = data.get("features", [])
            if not features:
                return None
            return {
                "value": f"{len(features)} quakes (M≥2.5) in last {days}d",
                "source": "usgs",
                "metadata": {
                    "time_window_days": days,
                    "result_count": len(features),
                    "top_events": [
                        {
                            "magnitude": f.get("properties", {}).get("mag"),
                            "place": f.get("properties", {}).get("place", ""),
                            "time": f.get("properties", {}).get("time"),
                        } for f in features[:5]
                    ],
                },
            }
        except Exception as e:
            logger.debug(f"[USGS] recent query failed: {e}", exc_info=True)
            return None
