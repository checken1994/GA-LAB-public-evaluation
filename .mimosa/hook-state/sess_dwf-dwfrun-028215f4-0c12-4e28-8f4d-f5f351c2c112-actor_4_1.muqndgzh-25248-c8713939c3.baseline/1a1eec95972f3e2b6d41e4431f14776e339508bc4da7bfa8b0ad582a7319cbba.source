import logging
from typing import Any

from scp.data_sources import LogicDataSource
from scp.runtime.slm_base import BaseSLM as Base

logger = logging.getLogger("scp.experts.logic")

class Logic(Base):
    """Domain Expert for Logic using LogicDataSource."""

    def __init__(self, config: dict | None = None):
        super().__init__(name="Logic", domain="logic", config=config)
        self._ds = None
        try:
            self._ds = LogicDataSource()
        except Exception as e:
            logger.debug(f"Logic LogicDataSource init failed: {e}", exc_info=True)

    def predict(self, question: str) -> Any:
        start = self._start_timer()
        answer = ""
        evidence = {}

        if self._ds and getattr(self._ds, "enabled", True):
            try:
                result = self._ds.query(question)
                if result and result.get("value"):
                    answer = f"{result['value']} (source: LogicDataSource)"
                    evidence = {"datasource": "Logic", "raw": result}
            except Exception as e:
                logger.debug(f"Logic query error: {e}", exc_info=True)

        resp = self._build_response(answer, 0.85 if answer else 0.1, "DataSource hit" if answer else "No hit", evidence)
        self._end_timer(start, bool(answer))
        return resp
