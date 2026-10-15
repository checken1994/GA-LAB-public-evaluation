"""
[OPT-19] Military — DomainExpert for military (uses existing MilitaryDataSource).

SCP's "SLM" means "Specialized Logic Module" (deterministic dispatcher).
This SLM:
  1. Checks local knowledge (military ranks, doctrines, history basics)
  2. Falls back to MilitaryDataSource.fetch() for specific entities
  3. Returns SLMResponse with answer + confidence + source

NOTE: Distinct from existing Military (_Domain) — this version has
explicit local knowledge for military concepts and ranks.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from scp.runtime.slm_base import BaseSLM as Base
from scp.runtime.slm_base import SLMResponse

logger = logging.getLogger("scp.slms")


class Military(Base):
    """Military DomainExpert — ranks, doctrines, history."""

    _LOCAL_KNOWLEDGE: dict[str, str] = {
        "what is strategy": "Military strategy is the planning and coordination of military "
                             "operations to achieve national security objectives. Levels: "
                             "tactical (battlefield), operational (campaign), strategic (war).",
        "what is doctrine": "Military doctrine is the formal expression of military knowledge "
                             "and philosophy, guiding how forces are organized, trained, and "
                             "employed. Each nation develops its own.",
        "what is nato": "NATO (North Atlantic Treaty Organization) is an intergovernmental "
                         "military alliance formed in 1949. Currently 32 member states. "
                         "Core principle: collective defense (Article 5).",
        "what is geneva convention": "Geneva Conventions are 4 treaties (1949) + 3 protocols "
                                      "establishing standards of international humanitarian "
                                      "law. Protect non-combatants, prisoners of war, wounded.",
        "us military ranks": "US military ranks (in ascending order for officers): "
                              "O-1 Second Lieutenant, O-2 First Lieutenant, O-3 Captain, "
                              "O-4 Major, O-5 Lieutenant Colonel, O-6 Colonel, O-7 Brigadier "
                              "General, O-8 Major General, O-9 Lieutenant General, O-10 General.",
        "vietnam military ranks": "Vietnam People's Army ranks (officers): "
                                    "Thiếu úy, Trung úy, Thượng úy, Đại úy, Thiếu tá, "
                                    "Trung tá, Thượng tá, Đại tá, Thiếu tướng, Trung tướng, "
                                    "Thượng tướng, Đại tướng.",
        "what is asymmetric warfare": "Asymmetric warfare is conflict between belligerents of "
                                        "vastly different military capabilities or strategies. "
                                        "Weaker side uses unconventional tactics (guerrilla, "
                                        "terrorism, insurgency).",
        "what is blitzkrieg": "Blitzkrieg ('lightning war') is a military doctrine of fast, "
                               "concentrated attacks using armored forces and close air support. "
                               "Associated with Nazi Germany in WWII (1939-1941).",
        "what is deterrence": "Deterrence is a strategy to prevent an adversary from taking "
                               "an action by threatening unacceptable consequences. Two types: "
                               "deterrence by punishment (retaliation) and by denial (defense).",
        "what is insurgency": "Insurgency is an organized movement aiming to overthrow a "
                                "constituted government through subversion, guerrilla warfare, "
                                "or terrorism. Often asymmetric.",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(name="Military", domain="military", config=config)
        self._ds = None
        try:
            from scp.data_sources.military import MilitaryDataSource
            self._ds = MilitaryDataSource()
        except Exception as e:
            logger.debug(f"Military MilitaryDataSource init: {e}", exc_info=True)

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
                confidence = 0.75  # well-established military facts
                reasoning = f"local_knowledge: {key}"
                evidence = {"value": val, "source": "local_knowledge", "key": key}
                break

        # Path 2: MilitaryDataSource fallback
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
                                reasoning = f"MilitaryDataSource: {entity[:50]}"
                                evidence = {"source": result.get("source", ""),
                                            "entity": entity,
                                            "value": result.get("value", ""),
                                            **result.get("metadata", {})}
                                break
            except Exception as e:
                logger.debug(f"Military DataSource query: {e}", exc_info=True)

        if not answer:
            confidence = 0.0
            reasoning = "Military pattern not recognized — try 'What is NATO?' or 'Vietnam military ranks?'"

        resp = SLMResponse(
            question=question, answer=answer, confidence=confidence,
            domain="military", reasoning=reasoning,
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
MilitaryExpert = Military
