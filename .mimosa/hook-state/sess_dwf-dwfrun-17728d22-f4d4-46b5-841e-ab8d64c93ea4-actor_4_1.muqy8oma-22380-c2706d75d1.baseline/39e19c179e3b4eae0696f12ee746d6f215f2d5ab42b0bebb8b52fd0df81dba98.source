import logging
from typing import Any

from scp.data_sources import AudioVideoDataSource
from scp.runtime.slm_base import BaseSLM as Base

logger = logging.getLogger("scp.experts.audiovideo")

class AudioVideo(Base):
    """Domain Expert for AudioVideo using AudioVideoDataSource."""

    def __init__(self, config: dict | None = None):
        super().__init__(name="AudioVideo", domain="audiovideo", config=config)
        self._ds = None
        try:
            self._ds = AudioVideoDataSource()
        except Exception as e:
            logger.debug(f"AudioVideo AudioVideoDataSource init failed: {e}", exc_info=True)

    def predict(self, question: str) -> Any:
        start = self._start_timer()
        answer = ""
        evidence = {}

        if self._ds and getattr(self._ds, "enabled", True):
            try:
                result = self._ds.query(question)
                if result and result.get("value"):
                    answer = f"{result['value']} (source: AudioVideoDataSource)"
                    evidence = {"datasource": "AudioVideo", "raw": result}
            except Exception as e:
                logger.debug(f"AudioVideo query error: {e}", exc_info=True)

        resp = self._build_response(answer, 0.85 if answer else 0.1, "DataSource hit" if answer else "No hit", evidence)
        self._end_timer(start, bool(answer))
        return resp
