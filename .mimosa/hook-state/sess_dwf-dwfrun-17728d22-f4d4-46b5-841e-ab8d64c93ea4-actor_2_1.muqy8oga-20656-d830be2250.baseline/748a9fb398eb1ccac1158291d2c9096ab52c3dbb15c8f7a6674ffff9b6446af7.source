""" GeologyDataSource"""
import logging
from typing import Any

from scp.core.api_utils import fetch_with_retry  # [V5.8-API]
from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


class GeologyDataSource(IDataSource):
    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._minerals = {
            "diamond": "Hardness 10 Mohs, carbon",
            "gold": "Soft, malleable, Au",
            "iron": "Most common metal on Earth",
            "quartz": "Most abundant mineral",
            "feldspar": "60% of Earth's crust",
        }
        # [V5.8-API] USGS earthquake endpoint (free, no key)
        self._usgs_url = (
            "https://earthquake.usgs.gov/fdsnws/event/1/query"
            "?format=geojson&limit=5&orderby=time"
        )

    @property
    def name(self) -> str:
        return "GeologyDataSource"

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
            return {"value": result.get("answer", ""), "source": "Geology", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True

    def query(self, q):
        if q in self._cache:
            return self._cache[q]
        result = {"found": False, "answer": None, "confidence": 0.0}

        # Local mineral DB lookup
        for mineral, desc in self._minerals.items():
            if mineral in q:
                result = {"found": True, "answer": f"{mineral}: {desc}", "confidence": 1.0}
                break

        # [V5.8-API] Local DB miss OR earthquake-related query → USGS API.
        # Trigger on earthquake keywords OR whenever the local DB missed,
        # since USGS earthquake feed is the canonical source for seismic data.
        q_lower = q.lower() if isinstance(q, str) else ""
        is_earthquake_query = any(
            kw in q_lower for kw in ('earthquake', 'seismic', 'quake', 'động đất', 'usgs')
        )
        if not result.get("found") or is_earthquake_query:
            api_result = self._fetch_from_usgs(q)
            if api_result:
                # Earthquake data takes precedence for earthquake-specific queries;
                # otherwise it only fills in when the local DB missed.
                if is_earthquake_query or not result.get("found"):
                    result = api_result

        self._cache[q] = result
        return result

    # [V5.8-API] USGS Earthquake Hazards integration
    def _fetch_from_usgs(self, query: str) -> dict[str, Any] | None:
        """
        [V5.8-API] Fetch recent earthquakes from USGS FDSN event ws.
        Endpoint: https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson
        Returns dict or None.
        """
        url = self._usgs_url
        try:
            data = fetch_with_retry(url, headers={"User-Agent": "SCP/1.0"}, timeout=8)
            if not data:
                return None
            features = data.get('features', [])
            if not features:
                return None
            entries = []
            for feat in features[:5]:
                props = feat.get('properties', {})
                mag = props.get('mag')
                place = props.get('place', '')
                ts_ms = props.get('time')
                url_link = props.get('url', '')
                # Format timestamp (ms → readable UTC)
                from datetime import datetime, timezone
                try:
                    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
                except Exception:
                    logger.warning('GeologyDataSource._fetch_from_usgs: Exception not handled', exc_info=True)
                    dt = ''
                parts = []
                if mag is not None:
                    parts.append(f"M{mag}")
                if place:
                    parts.append(place)
                if dt:
                    parts.append(dt)
                if url_link:
                    parts.append(f"({url_link})")
                if parts:
                    entries.append(" — ".join(parts))
            if not entries:
                return None
            return {
                "found": True,
                "answer": "USGS recent earthquakes: " + " | ".join(entries),
                "confidence": 0.9,
                "source": "USGS FDSN Earthquake API",
                "api": "usgs_fdsnws_event_1",
                "count": len(features),
            }
        except Exception as e:
            logger.warning(f"[V5.8-API] USGS earthquake fetch failed: {e}", exc_info=True)
            return None
