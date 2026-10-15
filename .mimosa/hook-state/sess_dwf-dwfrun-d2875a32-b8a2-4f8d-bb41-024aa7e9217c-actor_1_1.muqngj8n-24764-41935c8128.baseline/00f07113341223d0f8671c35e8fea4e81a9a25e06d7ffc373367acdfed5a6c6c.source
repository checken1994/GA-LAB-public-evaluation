import logging
from typing import Any

from scp.data_sources import DigitalMarketingDataSource
from scp.runtime.slm_base import BaseSLM as Base

logger = logging.getLogger("scp.experts.digitalmarketing")

class DigitalMarketing(Base):
    """Domain Expert for DigitalMarketing using DigitalMarketingDataSource."""

    def __init__(self, config: dict | None = None):
        super().__init__(name="DigitalMarketing", domain="digitalmarketing", config=config)
        self._ds = None
        try:
            self._ds = DigitalMarketingDataSource()
        except Exception as e:
            logger.debug(f"DigitalMarketing DigitalMarketingDataSource init failed: {e}", exc_info=True)

    def predict(self, question: str) -> Any:
        start = self._start_timer()
        answer = ""
        evidence = {}

        if self._ds and getattr(self._ds, "enabled", True):
            try:
                result = self._ds.query(question)
                if result and result.get("value"):
                    answer = f"{result['value']} (source: DigitalMarketingDataSource)"
                    evidence = {"datasource": "DigitalMarketing", "raw": result}
            except Exception as e:
                logger.debug(f"DigitalMarketing query error: {e}", exc_info=True)

        resp = self._build_response(answer, 0.85 if answer else 0.1, "DataSource hit" if answer else "No hit", evidence)
        self._end_timer(start, bool(answer))
        return resp
