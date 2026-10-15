"""
[OPT-18] Education — DomainExpert for education (uses ERIC DataSource).

SCP's "SLM" means "Specialized Logic Module" (deterministic dispatcher).
This SLM:
  1. Checks local knowledge (pedagogy, learning theory basics)
  2. Falls back to ERIC DataSource for research papers
  3. Returns SLMResponse with answer + confidence + source

NOTE: Distinct from existing Education (_Domain) — this version uses
the new ERIC API + has explicit local knowledge for education concepts.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from scp.runtime.slm_base import BaseSLM as Base
from scp.runtime.slm_base import SLMResponse

logger = logging.getLogger("scp.slms")


class Education(Base):
    """Education DomainExpert — pedagogy + learning theory + ERIC."""

    _LOCAL_KNOWLEDGE: dict[str, str] = {
        "what is pedagogy": "Pedagogy is the theory and practice of teaching. It encompasses "
                             "the strategies, methods, and approaches educators use to facilitate "
                             "learning. Key theorists: Comenius, Pestalozzi, Froebel, Dewey, "
                             "Piaget, Vygotsky.",
        "what is bloom's taxonomy": "Bloom's Taxonomy (Benjamin Bloom, 1956, revised by "
                                     "Anderson & Krathwohl, 2001) classifies educational "
                                     "learning objectives into 6 levels: Remember, Understand, "
                                     "Apply, Analyze, Evaluate, Create.",
        "what is constructivism": "Constructivism is a learning theory (Piaget, Vygotsky) "
                                   "arguing that learners actively construct knowledge through "
                                   "experiences and reflection, rather than passively receiving "
                                   "information. Key concepts: scaffolding, zone of proximal "
                                   "development (ZPD).",
        "what is montessori": "Montessori education (Maria Montessori, early 1900s) emphasizes "
                               "self-directed activity, hands-on learning, and collaborative "
                               "play. Mixed-age classrooms, specially designed materials.",
        "what is differentiated instruction": "Differentiated instruction (Carol Ann Tomlinson) "
                                                "tailors teaching to individual student needs — "
                                                "content, process, product, or learning environment "
                                                "adjusted based on student readiness, interest, "
                                                "or learning profile.",
        "what is formative assessment": "Formative assessment is ongoing assessment used to "
                                          "monitor student learning and provide feedback during "
                                          "instruction. Contrast with summative assessment "
                                          "(end-of-term, evaluative).",
        "what is zone of proximal development": "Zone of Proximal Development (ZPD, Vygotsky) "
                                                  "is the gap between what a learner can do "
                                                  "independently and what they can do with guidance. "
                                                  "Scaffolding bridges this gap.",
        "giáo dục là gì": "Giáo dục là quá trình đào tạo con người thông qua việc truyền thụ "
                          "kiến thức, kỹ năng, và giá trị. Ba loại hình: giáo dục chính quy, "
                          "thường xuyên, tự học.",
        "what is flipped classroom": "Flipped Classroom inverts traditional teaching: students "
                                       "learn content at home (videos, readings), and class "
                                       "time is used for active learning, discussion, problem-solving.",
        "what is stem": "STEM education integrates Science, Technology, Engineering, and "
                         "Mathematics. Extended as STEAM (adds Arts). Emphasizes "
                         "interdisciplinary, applied approach.",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(name="Education", domain="education", config=config)
        self._eric = None
        try:
            from scp.data_sources.eric import ERICDataSource
            self._eric = ERICDataSource()
        except Exception as e:
            logger.debug(f"Education ERIC init: {e}", exc_info=True)

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
                confidence = 0.75  # education theory, well-established
                reasoning = f"local_knowledge: {key}"
                evidence = {"value": val, "source": "local_knowledge", "key": key}
                break

        # Path 2: ERIC fallback for research-paper-style queries
        if not answer and self._eric and self._eric.enabled:
            try:
                result = self._eric.query(q)
                if result and result.get("value"):
                    meta = result.get("metadata", {})
                    top_results = meta.get("top_results", [])
                    if top_results:
                        first = top_results[0]
                        answer = (f"Top research paper found: '{first.get('title', '')}' "
                                  f"by {first.get('author', 'unknown')} "
                                  f"({first.get('publication_year', '?')}). "
                                  f"ERIC ID: {first.get('eric_id', '?')}. "
                                  f"Total results: {meta.get('total_results', 0)}.")
                        confidence = 0.6  # research paper, not verified claim
                        reasoning = f"ERIC: searched '{meta.get('search_term', '?')[:50]}'"
                        evidence = result
            except Exception as e:
                logger.debug(f"Education ERIC query: {e}", exc_info=True)

        if not answer:
            confidence = 0.0
            reasoning = "Education pattern not recognized — try 'What is pedagogy?' or 'Bloom's taxonomy?'"

        resp = SLMResponse(
            question=question, answer=answer, confidence=confidence,
            domain="education", reasoning=reasoning,
            evidence=evidence, slm_name=self.name,
            processing_time=time.time() - start,
        )
        self.cache_response(question, resp)
        self._end_timer(start, confidence > 0.3)
        return resp

    def get_confidence(self, question: str, answer: str) -> float:
        if not answer:
            return 0.0
        return 0.75 if "local_knowledge" in answer else 0.6


# [OPT-7] Alias — "SLM" in SCP means "Specialized Logic Module" (DomainExpert).
EducationExpert = Education
