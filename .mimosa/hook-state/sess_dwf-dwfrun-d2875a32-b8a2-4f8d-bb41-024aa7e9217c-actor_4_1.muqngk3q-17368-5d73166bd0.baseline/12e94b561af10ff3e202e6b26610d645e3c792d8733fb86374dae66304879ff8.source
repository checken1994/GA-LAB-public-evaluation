import logging
from typing import Any

from scp.data_sources import WeatherDataSource
from scp.runtime.slm_base import BaseSLM as Base

logger = logging.getLogger("scp.experts.weather")

class Weather(Base):
    """Domain Expert for Weather using WeatherDataSource."""

    def __init__(self, config: dict | None = None):
        super().__init__(name="Weather", domain="weather", config=config)
        self._ds = None
        try:
            self._ds = WeatherDataSource()
        except Exception as e:
            logger.debug(f"Weather WeatherDataSource init failed: {e}", exc_info=True)

    def predict(self, question: str) -> Any:
        start = self._start_timer()
        answer = ""
        evidence = {}

        if self._ds and getattr(self._ds, "enabled", True):
            try:
                result = self._ds.query(question)
                if result and result.get("value"):
                    answer = f"{result['value']} (source: WeatherDataSource)"
                    evidence = {"datasource": "Weather", "raw": result}
            except Exception as e:
                logger.debug(f"Weather query error: {e}", exc_info=True)

        resp = self._build_response(answer, 0.85 if answer else 0.1, "DataSource hit" if answer else "No hit", evidence)
        self._end_timer(start, bool(answer))
        return resp
