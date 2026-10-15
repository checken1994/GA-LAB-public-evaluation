"""
[OPT-21] Art — DomainExpert for art (uses existing ArtsDataSource).

SCP's "SLM" means "Specialized Logic Module" (deterministic dispatcher).
This SLM:
  1. Checks local knowledge (art movements, famous artists, techniques)
  2. Falls back to ArtsDataSource.fetch() for specific entities
  3. Returns SLMResponse with answer + confidence + source

NOTE: Distinct from existing Arts (_Domain) — this version has explicit
local knowledge for art movements and famous artists.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from scp.runtime.slm_base import BaseSLM as Base
from scp.runtime.slm_base import SLMResponse

logger = logging.getLogger("scp.slms")


class Art(Base):
    """Art DomainExpert — movements, artists, techniques."""

    _LOCAL_KNOWLEDGE: dict[str, str] = {
        "what is impressionism": "Impressionism was a 19th-century art movement (1860s-1890s) "
                                  "characterized by small, thin brush strokes, open composition, "
                                  "emphasis on light and its changing qualities. Key artists: "
                                  "Monet, Renoir, Degas, Cassatt.",
        "what is cubism": "Cubism (early 20th century) was pioneered by Pablo Picasso and "
                          "Georges Braque (1907-1914). Objects analyzed, broken up, reassembled "
                          "in abstracted form. Two phases: Analytic, Synthetic.",
        "what is surrealism": "Surrealism (1920s) sought to channel the unconscious to unlock "
                               "the power of the imagination. Influenced by Freud. Key artists: "
                               "Dalí, Magritte, Ernst, Miró, Kahlo.",
        "what is renaissance art": "Renaissance art (14th-17th century) emphasized realism, "
                                     "perspective, classical themes, humanism. Key artists: "
                                     "Leonardo da Vinci, Michelangelo, Raphael, Botticelli.",
        "what is baroque art": "Baroque art (1600-1750) is characterized by drama, deep colors, "
                                "intense light/dark contrast (chiaroscuro), and emotional "
                                "intensity. Key artists: Caravaggio, Rembrandt, Vermeer, Bernini.",
        "what is abstract expressionism": "Abstract Expressionism (1940s-50s, NYC) emphasized "
                                            "spontaneous, automatic, or subconscious creation. "
                                            "Key artists: Pollock, Rothko, de Kooning, Kline.",
        "who is leonardo da vinci": "Leonardo da Vinci (1452-1519) was an Italian polymath of "
                                      "the High Renaissance. Famous works: Mona Lisa, The Last "
                                      "Supper, Vitruvian Man. Also a scientist, inventor, anatomist.",
        "who is picasso": "Pablo Picasso (1881-1973) was a Spanish painter, sculptor, and "
                           "co-founder of Cubism. Prolific: ~13,500 paintings, 100,000 prints, "
                           "34,000 illustrations. Famous works: Les Demoiselles d'Avignon, Guernica.",
        "who is van gogh": "Vincent van Gogh (1853-1890) was a Dutch Post-Impressionist painter. "
                            "Created ~2,100 artworks in just over a decade. Famous works: The "
                            "Starry Night, Sunflowers, Self-Portrait. Sold only one painting in life.",
        "what is oil painting": "Oil painting uses pigments bound with drying oil (linseed, "
                                  "walnut, poppy). Slow drying allows blending and layering. "
                                  "Popular since the Renaissance (Jan van Eyck, 15th century).",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(name="Art", domain="arts", config=config)
        self._ds = None
        try:
            from scp.data_sources.arts import ArtsDataSource
            self._ds = ArtsDataSource()
        except Exception as e:
            logger.debug(f"Art ArtsDataSource init: {e}", exc_info=True)

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
                confidence = 0.8  # well-established art history facts
                reasoning = f"local_knowledge: {key}"
                evidence = {"value": val, "source": "local_knowledge", "key": key}
                break

        # Path 2: ArtsDataSource fallback
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
                                reasoning = f"ArtsDataSource: {entity[:50]}"
                                evidence = {"source": result.get("source", ""),
                                            "entity": entity,
                                            "value": result.get("value", ""),
                                            **result.get("metadata", {})}
                                break
            except Exception as e:
                logger.debug(f"Art DataSource query: {e}", exc_info=True)

        if not answer:
            confidence = 0.0
            reasoning = "Art pattern not recognized — try 'What is cubism?' or 'Who is Picasso?'"

        resp = SLMResponse(
            question=question, answer=answer, confidence=confidence,
            domain="arts", reasoning=reasoning,
            evidence=evidence, slm_name=self.name,
            processing_time=time.time() - start,
        )
        self.cache_response(question, resp)
        self._end_timer(start, confidence > 0.3)
        return resp

    def _extract_entity(self, question: str) -> str:
        import re
        q = question.strip()
        q = re.sub(r'^(?:what\s+is|what\s+are|who\s+is|cho\s+biết|tìm\s+hiểu)\s+', '', q, flags=re.IGNORECASE)
        q = re.sub(r'^(.+?)\s+là\s+gì\??$', r'\1', q, flags=re.IGNORECASE)
        q = re.sub(r'^(.+?)\s+là\s+ai\??$', r'\1', q, flags=re.IGNORECASE)
        return q.rstrip('?').strip()

    def get_confidence(self, question: str, answer: str) -> float:
        if not answer:
            return 0.0
        return 0.8 if "local_knowledge" in answer else 0.7


# [OPT-7] Alias — "SLM" in SCP means "Specialized Logic Module" (DomainExpert).
ArtExpert = Art
