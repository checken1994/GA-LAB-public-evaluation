import logging
from typing import Any

from scp.data_sources import PsychologyDataSource
from scp.runtime.slm_base import BaseSLM as Base

logger = logging.getLogger("scp.experts.psychology")

class Psychology(Base):
    """Domain Expert for Psychology using PsychologyDataSource."""

    def __init__(self, config: dict | None = None):
        super().__init__(name="Psychology", domain="psychology", config=config)
        self._ds = None
        try:
            self._ds = PsychologyDataSource()
        except Exception as e:
            logger.debug(f"Psychology PsychologyDataSource init failed: {e}", exc_info=True)

    def predict(self, question: str) -> Any:
        start = self._start_timer()
        answer = ""
        evidence = {}

        if self._ds and getattr(self._ds, "enabled", True):
            try:
                result = self._ds.query(question)
                if result and result.get("value"):
                    answer = f"{result['value']} (source: PsychologyDataSource)"
                    evidence = {"datasource": "Psychology", "raw": result}
            except Exception as e:
                logger.debug(f"Psychology query error: {e}", exc_info=True)

        resp = self._build_response(answer, 0.85 if answer else 0.1, "DataSource hit" if answer else "No hit", evidence)
        self._end_timer(start, bool(answer))
        return resp
