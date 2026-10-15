"""
[OPT-20] Agriculture — DomainExpert for agriculture (uses existing AgricultureDataSource).

SCP's "SLM" means "Specialized Logic Module" (deterministic dispatcher).
This SLM:
  1. Checks local knowledge (crop yields, farming basics)
  2. Falls back to AgricultureDataSource.fetch() for specific entities
  3. Returns SLMResponse with answer + confidence + source
"""
from __future__ import annotations

import logging
import time
from typing import Any

from scp.runtime.slm_base import BaseSLM as Base
from scp.runtime.slm_base import SLMResponse

logger = logging.getLogger("scp.slms")


class Agriculture(Base):
    """Agriculture DomainExpert — crops, yields, farming practices."""

    _LOCAL_KNOWLEDGE: dict[str, str] = {
        "what is agriculture": "Agriculture is the practice of cultivating plants and "
                                "livestock for food, fiber, fuel, and other products. Major "
                                "branches: agronomy (crops), horticulture, animal husbandry, "
                                "agroforestry.",
        "rice yield": "Rice yield typically ranges 4-10 tons/ha globally. Vietnam average: "
                       "~5.5 t/ha (2022). China hybrid rice record: ~12 t/ha. Yields >15 t/ha "
                       "are implausible without specific high-tech conditions.",
        "năng suất lúa": "Năng suất lúa trung bình toàn cầu: 4-10 tấn/ha. Việt Nam: ~5.5 tấn/ha "
                          "(2022). Kỷ lục lúa lai Trung Quốc: ~12 tấn/ha. Năng suất >15 tấn/ha "
                          "là khó khả thi trừ khi có điều kiện đặc biệt.",
        "what is irrigation": "Irrigation is the artificial application of water to soil for "
                               "crop production. Methods: surface (furrow, basin), sprinkler, "
                               "drip, subsurface. Critical in arid regions.",
        "what is fertilizer": "Fertilizers are materials applied to soil or plants to supply "
                               "essential nutrients. Three primary macronutrients: N (nitrogen), "
                               "P (phosphorus), K (potassium). Expressed as N-P-K ratio.",
        "what is crop rotation": "Crop rotation is the practice of growing different crops in "
                                  "succession on the same land to improve soil health, reduce "
                                  "pests/diseases, and optimize nutrients. E.g., corn → soybean → wheat.",
        "what is organic farming": "Organic farming avoids synthetic fertilizers, pesticides, "
                                     "GMOs, and growth hormones. Emphasizes ecological balance, "
                                     "biodiversity, soil health. Certified by USDA Organic, EU Organic.",
        "what is precision agriculture": "Precision agriculture uses technology (GPS, sensors, "
                                          "drones, satellite imagery, IoT) to optimize crop "
                                          "yields and inputs (water, fertilizer, pesticides) "
                                          "on a site-specific basis.",
        "what is greenhouse": "A greenhouse is a structure with transparent roof/walls that "
                               "traps solar radiation to maintain warm growing conditions. "
                               "Enables year-round cultivation in cold climates.",
        "what is hydroponics": "Hydroponics is a method of growing plants without soil, using "
                                "mineral nutrient solutions in water. Advantages: faster growth, "
                                "less water, no soil-borne diseases.",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(name="Agriculture", domain="agriculture", config=config)
        self._ds = None
        try:
            from scp.data_sources.agriculture import AgricultureDataSource
            self._ds = AgricultureDataSource()
        except Exception as e:
            logger.debug(f"Agriculture AgricultureDataSource init: {e}", exc_info=True)

    def predict(self, question: str) -> SLMResponse:
        start = self._start_timer()
        cached = self.get_cached(question)
        if cached:
            self._end_timer(start, True)
            return cached

        q = question.strip()
        q_lower = q.lower()
        answer = ""
        confidence = 0.0
        reasoning = ""
        evidence: dict[str, Any] = {}

        # Path 1: local knowledge
        for key, val in self._LOCAL_KNOWLEDGE.items():
            if key in q_lower:
                answer = val
                confidence = 0.75  # well-established agricultural facts
                reasoning = f"local_knowledge: {key}"
                evidence = {"value": val, "source": "local_knowledge", "key": key}
                break

        # Path 2: AgricultureDataSource fallback
        if not answer and self._ds:
            try:
                entity = self._extract_entity(q)
                if entity:
                    for intent in self._ds.get_supported_intents():
                        if self._ds.can_handle(intent, entity):
                            result = self._ds.fetch(intent, entity)
                            if result and result.get("value"):
                                answer = str(result["value"])[:500]
                                confidence = 0.7
                                reasoning = f"AgricultureDataSource: {entity[:50]}"
                                evidence = {"source": result.get("source", ""),
                                            "entity": entity,
                                            "value": result.get("value", ""),
                                            **result.get("metadata", {})}
                                break
            except Exception as e:
                logger.debug(f"Agriculture DataSource query: {e}", exc_info=True)

        if not answer:
            confidence = 0.0
            reasoning = "Agriculture pattern not recognized — try 'rice yield?' or 'What is irrigation?'"

        resp = SLMResponse(
            question=question, answer=answer, confidence=confidence,
            domain="agriculture", reasoning=reasoning,
            evidence=evidence, slm_name=self.name,
            processing_time=time.time() - start,
        )
        self.cache_response(question, resp)
        self._end_timer(start, confidence > 0.3)
        return resp

    def _extract_entity(self, question: str) -> str:
        import re
        q = question.strip()
        q = re.sub(r'^(?:what\s+is|what\s+are|cho\s+biết|tìm\s+hiểu)\s+', '', q, flags=re.IGNORECASE)
        q = re.sub(r'^(.+?)\s+là\s+gì\??$', r'\1', q, flags=re.IGNORECASE)
        return q.rstrip('?').strip()

    def get_confidence(self, question: str, answer: str) -> float:
        if not answer:
            return 0.0
        return 0.75 if "local_knowledge" in answer else 0.7


# [OPT-7] Alias — "SLM" in SCP means "Specialized Logic Module" (DomainExpert).
AgricultureExpert = Agriculture
