"""
[OPT-17] Law — DomainExpert for law (uses existing LegalDataSource).

SCP's "SLM" means "Specialized Logic Module" (deterministic dispatcher).
This SLM:
  1. Checks local knowledge (Vietnamese + international law basics)
  2. Falls back to LegalDataSource.fetch() for specific entities
  3. Returns SLMResponse with answer + confidence + source

NOTE: Distinct from existing Legal (_Domain) — this version has explicit
local knowledge and is meant as the "DomainExpert" pattern reference.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from scp.runtime.slm_base import BaseSLM as Base
from scp.runtime.slm_base import SLMResponse

logger = logging.getLogger("scp.slms")


class Law(Base):
    """Law DomainExpert — Vietnamese + international law."""

    _LOCAL_KNOWLEDGE: dict[str, str] = {
        "what is a contract": "A contract is a legally binding agreement between two or more "
                               "parties that creates mutual obligations. Essential elements: "
                               "offer, acceptance, consideration, mutual assent, capacity, "
                               "legality of purpose.",
        "hợp đồng là gì": "Hợp đồng là sự thỏa thuận giữa các bên về việc xác lập, thay đổi "
                          "hoặc chấm dứt quyền và nghĩa vụ dân sự. Yếu tố bắt buộc: chủ thể, "
                          "nội dung, hình thức phù hợp luật.",
        "what is statute of limitations": "Statute of limitations is the maximum time after "
                                            "an event within which legal proceedings may be "
                                            "initiated. Varies by jurisdiction and case type.",
        "thời hiệu là gì": "Thời hiệu là khoảng thời gian do pháp luật quy định mà trong thời "
                            "gian đó, một chủ thể có quyền yêu cầu cơ quan nhà nước có thẩm "
                            "quyền bảo vệ quyền của mình.",
        "what is intellectual property": "Intellectual property (IP) refers to creations of "
                                          "the mind — inventions, literary/artistic works, "
                                          "designs, names, images. Protected by patents, "
                                          "copyrights, trademarks, trade secrets.",
        "what is human rights": "Human rights are universal rights inherent to all human "
                                 "beings regardless of nationality, sex, race, ethnicity, "
                                 "religion. Codified in UDHR (1948), ICCPR, ICESCR.",
        "quyền con người là gì": "Quyền con người là những quyền tự nhiên, vốn có của mỗi "
                                 "cá nhân, không phụ thuộc quốc tịch, giới tính, chủng tộc. "
                                 "Được pháp điển hóa trong UDHR 1948.",
        "what is criminal law": "Criminal law is the body of law relating to crime. It "
                                 "regulates social conduct and prescribes threatening, "
                                 "harming, or otherwise endangering health/safety/moral "
                                 "welfare of people.",
        "what is civil law": "Civil law deals with disputes between individuals/organizations, "
                              "in areas like contracts, property, family law, torts. Goal: "
                              "compensation rather than punishment.",
        "udhr": "Universal Declaration of Human Rights (UDHR), adopted by UN General Assembly "
                "on December 10, 1948. 30 articles. Foundation of international human rights law.",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(name="Law", domain="law", config=config)
        self._ds = None
        try:
            from scp.data_sources.legal import LegalDataSource
            self._ds = LegalDataSource()
        except Exception as e:
            logger.debug(f"Law LegalDataSource init: {e}", exc_info=True)

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
                confidence = 0.75  # legal facts, well-established
                reasoning = f"local_knowledge: {key}"
                evidence = {"value": val, "source": "local_knowledge", "key": key}
                break

        # Path 2: LegalDataSource fallback for specific entities
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
                                reasoning = f"LegalDataSource: {entity[:50]}"
                                evidence = {"source": result.get("source", ""),
                                            "entity": entity,
                                            "value": result.get("value", ""),
                                            **result.get("metadata", {})}
                                break
                    if answer:
                        pass
            except Exception as e:
                logger.debug(f"Law DataSource query: {e}", exc_info=True)

        if not answer:
            confidence = 0.0
            reasoning = "Law pattern not recognized — try 'What is a contract?' or 'UDHR?'"

        resp = SLMResponse(
            question=question, answer=answer, confidence=confidence,
            domain="law", reasoning=reasoning,
            evidence=evidence, slm_name=self.name,
            processing_time=time.time() - start,
        )
        self.cache_response(question, resp)
        self._end_timer(start, confidence > 0.3)
        return resp

    def _extract_entity(self, question: str) -> str:
        """Extract entity from question (basic heuristic)."""
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
LawExpert = Law
