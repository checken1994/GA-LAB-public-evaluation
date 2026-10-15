"""
SCP - Viet Nam | Self-Correcting Pipeline
 EnergyDataSource - Data source cho Năng lượng
"""

import logging
import os
from typing import Any

from scp.core.api_utils import fetch_with_retry  # [V5.8-API]
from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


class EnergyDataSource(IDataSource):
    """
    Data source cho các câu hỏi Năng lượng.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}
        # [V5.8-API] EIA API key — register at https://www.eia.gov/opendata/register.php
        self._eia_api_key = os.environ.get("EIA_API_KEY", "").strip()

        # Energy types
        self._types = {
            "năng lượng mặt trời": "Solar energy - PV cells",
            "năng lượng gió": "Wind energy - turbines",
            "thủy điện": "Hydroelectric - dams",
            "địa nhiệt": "Geothermal - heat from earth",
            "sinh khối": "Biomass - organic materials",
            "hydro": "Hydrogen - fuel cells",
        }

        # Energy facts
        self._facts = {
            "efficiency solar": "15-22%",
            "efficiency wind": "30-45%",
            "efficiency nuclear": "90-95%",
            "efficiency coal": "30-40%",
            "cost solar": "0.06 USD/kWh",
            "cost wind": "0.05 USD/kWh",
            "cost nuclear": "0.08 USD/kWh",
        }


    @property
    def name(self) -> str:
        return "EnergyDataSource"

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
            return {"value": result.get("answer", ""), "source": "Energy", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True

    def query(self, question: str) -> dict[str, Any]:
        """Query energy data."""
        q = question.lower().strip()

        if q in self._cache:
            return self._cache[q]

        result = {"found": False, "answer": None, "confidence": 0.0}

        for energy_type, description in self._types.items():
            if energy_type in q:
                result = {
                    "found": True,
                    "answer": f"{energy_type}: {description}",
                    "confidence": 1.0,
                    "source": "Energy Database"
                }
                break

        for fact, value in self._facts.items():
            if fact in q:
                result = {
                    "found": True,
                    "answer": f"{fact}: {value}",
                    "confidence": 1.0,
                    "source": "Energy Database"
                }
                break

        # [V5.8-API] Local DB miss → try EIA (US electricity) / OpenNEM (AU).
        if not result.get("found"):
            api_result = self._fetch_from_eia_or_opennem(question)
            if api_result:
                result = api_result

        self._cache[q] = result
        return result

    # [V5.8-API] EIA + OpenNEM integration
    def _fetch_from_eia_or_opennem(self, question: str) -> dict[str, Any] | None:
        """
        [V5.8-API] Fetch energy statistics from EIA (US electricity retail sales)
        or OpenNEM (Australian facility generation). EIA requires an api_key
        (skipped if missing). OpenNEM is free, no key.
        """
        if not question or not question.strip():
            return None
        q = question.lower()

        # Heuristic: if question mentions Australia / opennem → use OpenNEM
        if any(kw in q for kw in ('australia', 'australian', 'opennem', 'nemo', 'aemo')):
            return self._fetch_opennem()

        # Default: EIA (requires API key)
        if self._eia_api_key:
            return self._fetch_eia()
        return None

    def _fetch_eia(self) -> dict[str, Any] | None:
        """[V5.8-API] EIA electricity retail-sales (most recent)."""
        url = (
            f"https://api.eia.gov/v2/electricity/retail-sales/data/"
            f"?api_key={self._eia_api_key}&frequency=monthly&data[0]=price&data[1]=sales"
            f"&sort[0][column]=period&sort[0][direction]=desc&length=5"
        )
        try:
            data = fetch_with_retry(url, headers={"User-Agent": "SCP/1.0"}, timeout=8)
            if not data:
                return None
            records = data.get('response', {}).get('data', [])
            if not records:
                return None
            lines = []
            for r in records[:5]:
                period = r.get('period', '')
                state = r.get('stateDescription', '')
                sector = r.get('sectorName', '')
                price = r.get('price', '')
                sales = r.get('sales', '')
                lines.append(
                    f"{period} | {state} | {sector} | price={price} | sales={sales}"
                )
            return {
                "found": True,
                "answer": "EIA US electricity retail-sales (latest): " + " ; ".join(lines),
                "confidence": 0.85,
                "source": "EIA API v2",
                "api": "eia_v2_electricity_retail_sales",
            }
        except Exception as e:
            logger.warning(f"[V5.8-API] EIA API fetch failed: {e}", exc_info=True)
            return None

    def _fetch_opennem(self) -> dict[str, Any] | None:
        """[V5.8-API] OpenNEM Australian facility network."""
        # The OpenNEM facilities endpoint returns the AU generation fleet
        url = "https://api.opennem.org.au/facilities"
        try:
            data = fetch_with_retry(url, headers={"User-Agent": "SCP/1.0"}, timeout=8)
            if not data:
                return None
            # Response shape can be a list or dict; handle both.
            facilities = data if isinstance(data, list) else data.get('data', [])
            if not facilities:
                return None
            lines = []
            for f in facilities[:5]:
                if not isinstance(f, dict):
                    continue
                name = f.get('name', '') or f.get('display_name', '')
                tech = f.get('technology_id', '') or f.get('fuel_tech', '')
                cap = f.get('capacity_regulated', '') or f.get('registered_capacity', '')
                if name:
                    lines.append(f"{name} [{tech}] cap={cap}")
            if not lines:
                return None
            return {
                "found": True,
                "answer": "OpenNEM AU facilities (top 5): " + " ; ".join(lines),
                "confidence": 0.8,
                "source": "OpenNEM API",
                "api": "opennem_facilities",
            }
        except Exception as e:
            logger.warning(f"[V5.8-API] OpenNEM API fetch failed: {e}", exc_info=True)
            return None
