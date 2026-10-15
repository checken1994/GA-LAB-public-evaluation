import logging
from typing import Any

from scp.data_sources import ArchitectureDataSource
from scp.runtime.slm_base import BaseSLM as Base

logger = logging.getLogger("scp.experts.architecture")

class Architecture(Base):
    """Domain Expert for Architecture using ArchitectureDataSource."""

    def __init__(self, config: dict | None = None):
        super().__init__(name="Architecture", domain="architecture", config=config)
        self._ds = None
        try:
            self._ds = ArchitectureDataSource()
        except Exception as e:
            logger.debug(f"Architecture ArchitectureDataSource init failed: {e}", exc_info=True)

    def predict(self, question: str) -> Any:
        start = self._start_timer()
        answer = ""
        evidence = {}

        if self._ds and getattr(self._ds, "enabled", True):
            try:
                result = self._ds.query(question)
                if result and result.get("value"):
                    answer = f"{result['value']} (source: ArchitectureDataSource)"
                    evidence = {"datasource": "Architecture", "raw": result}
            except Exception as e:
                logger.debug(f"Architecture query error: {e}", exc_info=True)

        resp = self._build_response(answer, 0.85 if answer else 0.1, "DataSource hit" if answer else "No hit", evidence)
        self._end_timer(start, bool(answer))
        return resp
