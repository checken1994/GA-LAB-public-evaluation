"""
[OPT-22] Engineering — DomainExpert for engineering
(uses Aerospace + Architecture + Technology DataSources).

SCP's "SLM" means "Specialized Logic Module" (deterministic dispatcher).
This SLM:
  1. Checks local knowledge (engineering disciplines, principles)
  2. Falls back to multiple DataSources (aerospace, architecture, technology)
  3. Returns SLMResponse with answer + confidence + source
"""
from __future__ import annotations

import logging
import time
from typing import Any

from scp.runtime.slm_base import BaseSLM as Base
from scp.runtime.slm_base import SLMResponse

logger = logging.getLogger("scp.slms")


class Engineering(Base):
    """Engineering DomainExpert — aerospace, architecture, technology."""

    _LOCAL_KNOWLEDGE: dict[str, str] = {
        "what is engineering": "Engineering is the application of scientific, economic, and "
                                "practical knowledge to design, build, and maintain structures, "
                                "machines, systems, and processes. Major branches: civil, "
                                "mechanical, electrical, chemical, aerospace, software.",
        "what is aerospace engineering": "Aerospace engineering deals with design, development, "
                                          "testing, and production of aircraft and spacecraft. "
                                          "Two branches: aeronautical (atmosphere), astronautical (space).",
        "what is mechanical engineering": "Mechanical engineering applies physics, engineering "
                                           "mathematics, and materials science to design, analyze, "
                                           "manufacture, and maintain mechanical systems. Oldest "
                                           "and broadest engineering discipline.",
        "what is electrical engineering": "Electrical engineering deals with study and application "
                                           "of electricity, electronics, electromagnetism. Subfields: "
                                           "power, control, electronics, microelectronics, signal "
                                           "processing, telecommunications, computers.",
        "what is civil engineering": "Civil engineering deals with design, construction, and "
                                      "maintenance of the physical and naturally built environment: "
                                      "roads, bridges, canals, dams, buildings. Oldest engineering "
                                      "discipline after military engineering.",
        "what is chemical engineering": "Chemical engineering applies chemistry, physics, "
                                         "biology, and math to produce materials, chemicals, and "
                                         "energy. Key processes: distillation, crystallization, "
                                         "reactor design, mass/heat transfer.",
        "what is software engineering": "Software engineering is the systematic application of "
                                          "engineering approaches to software development. Key "
                                          "methodologies: Agile, Waterfall, DevOps. IEEE defines it "
                                          "as a profession since 1968 NATO conference.",
        "what is structural engineering": "Structural engineering is a sub-discipline of civil "
                                            "engineering that designs structures to withstand "
                                            "loads (gravity, wind, seismic). Key concepts: stress, "
                                            "strain, elasticity, plasticity, buckling.",
        "what is mach number": "Mach number is the ratio of an object's speed to the speed of "
                                "sound in the surrounding medium. Mach 1 = speed of sound "
                                "(~343 m/s in air at 20°C). Subsonic <0.8, transonic 0.8-1.2, "
                                "supersonic 1.2-5.0, hypersonic >5.0.",
        "what is finite element analysis": "Finite Element Analysis (FEA) is a numerical method "
                                             "for solving complex structural, thermal, and fluid "
                                             "problems by dividing a large system into smaller, "
                                             "simpler parts (finite elements). Used in CAD/CAE.",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(name="Engineering", domain="engineering", config=config)
        # Lazy-load multiple DataSources
        self._data_sources = []
        for ds_module, ds_class_name in [
            ("scp.data_sources.aerospace", "AerospaceDataSource"),
            ("scp.data_sources.architecture", "ArchitectureDataSource"),
            ("scp.data_sources.technology", "TechnologyDataSource"),
        ]:
            try:
                mod = __import__(ds_module, fromlist=[ds_class_name])
                ds_class = getattr(mod, ds_class_name)
                self._data_sources.append(ds_class())
            except Exception as e:
                logger.debug(f"Engineering {ds_class_name} init: {e}", exc_info=True)

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
                confidence = 0.8  # well-established engineering principles
                reasoning = f"local_knowledge: {key}"
                evidence = {"value": val, "source": "local_knowledge", "key": key}
                break

        # Path 2: Try each DataSource (aerospace, architecture, technology)
        if not answer and self._data_sources:
            try:
                entity = self._extract_entity(q)
                if entity:
                    for ds in self._data_sources:
                        ds_name = getattr(ds, "name", type(ds).__name__)
                        try:
                            for intent in ds.get_supported_intents():
                                if ds.can_handle(intent, entity):
                                    result = ds.fetch(intent, entity)
                                    if result and result.get("value"):
                                        answer = str(result["value"])[:500]
                                        confidence = 0.7
                                        reasoning = f"{ds_name}DataSource: {entity[:50]}"
                                        evidence = {"source": result.get("source", ""),
                                                    "entity": entity,
                                                    "datasource": ds_name,
                                                    "value": result.get("value", ""),
                                                    **result.get("metadata", {})}
                                        break
                            if answer:
                                break
                        except Exception as e:
                            logger.debug(f"Engineering {ds_name} fetch: {e}", exc_info=True)
            except Exception as e:
                logger.debug(f"Engineering entity extraction: {e}", exc_info=True)

        if not answer:
            confidence = 0.0
            reasoning = "Engineering pattern not recognized — try 'What is aerospace engineering?' or 'Mach number?'"

        resp = SLMResponse(
            question=question, answer=answer, confidence=confidence,
            domain="engineering", reasoning=reasoning,
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
        return 0.8 if "local_knowledge" in answer else 0.7


# [OPT-7] Alias — "SLM" in SCP means "Specialized Logic Module" (DomainExpert).
EngineeringExpert = Engineering
