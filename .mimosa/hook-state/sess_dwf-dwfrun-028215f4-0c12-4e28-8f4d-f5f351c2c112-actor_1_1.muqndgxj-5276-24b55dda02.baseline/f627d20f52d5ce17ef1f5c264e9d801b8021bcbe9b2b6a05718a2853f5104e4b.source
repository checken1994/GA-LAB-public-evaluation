"""
[OPT-14] Philosophy — DomainExpert for philosophy (local knowledge).

SCP's "SLM" means "Specialized Logic Module" (deterministic dispatcher).
This SLM uses local knowledge only — no external DataSource needed for
basic philosophical concepts, schools of thought, and logical fallacies.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from scp.runtime.slm_base import BaseSLM as Base
from scp.runtime.slm_base import SLMResponse

logger = logging.getLogger("scp.slms")


class Philosophy(Base):
    """Philosophy DomainExpert — Greek/Eastern/local philosophy knowledge."""

    # Local knowledge: key philosophical concepts and schools
    _PHILOSOPHERS: dict[str, str] = {
        "socrates": "Socrates (470-399 BCE) was a Greek philosopher credited as one of the "
                    "founders of Western philosophy. Known for the Socratic method (dialectic "
                    "questioning). He wrote nothing; we know him through Plato's dialogues.",
        "plato": "Plato (428/427-348/347 BCE) was a Greek philosopher, student of Socrates, "
                 "founder of the Academy in Athens. Known for Theory of Forms, allegory of the "
                 "cave, and dialogues like 'The Republic'.",
        "aristotle": "Aristotle (384-322 BCE) was a Greek philosopher, student of Plato, tutor "
                     "to Alexander the Great. Founded the Lyceum. Known for syllogistic logic, "
                     "ethics (Nicomachean Ethics), and empirical approach.",
        "confucius": "Confucius (551-479 BCE) was a Chinese philosopher, founder of Confucianism. "
                     "Emphasized personal and governmental morality, correctness of social "
                     "relationships, justice, and sincerity.",
        "laozi": "Laozi (6th century BCE) was a semi-legendary Chinese philosopher, reputed "
                 "author of the Tao Te Ching and founder of Daoism. Emphasized wu wei "
                 "(non-action) and harmony with the Tao (the Way).",
        "immanuel kant": "Immanuel Kant (1724-1804) was a German philosopher, central figure "
                         "in modern philosophy. Known for Critique of Pure Reason, categorical "
                         "imperative, and synthesis of rationalism and empiricism.",
        "nietzsche": "Friedrich Nietzsche (1844-1900) was a German philosopher known for "
                     "critique of religion, 'God is dead', will to power, Übermensch, and "
                     "eternal recurrence. Works: Thus Spoke Zarathustra, Beyond Good and Evil.",
        "rene descartes": "René Descartes (1596-1650) was a French philosopher, mathematician, "
                          "and scientist. Father of modern philosophy. Known for 'Cogito, ergo "
                          "sum' (I think, therefore I am) and mind-body dualism.",
        "descartes": "René Descartes (1596-1650) — see full entry under 'rene descartes'.",
        "john locke": "John Locke (1632-1704) was an English philosopher, founder of British "
                      "empiricism. Known for theory of mind as tabula rasa, natural rights "
                      "(life, liberty, property), and social contract.",
    }

    _CONCEPTS: dict[str, str] = {
        "what is ethics": "Ethics is the branch of philosophy that involves systematizing, "
                          "defending, and recommending concepts of right and wrong behavior. "
                          "Major branches: meta-ethics, normative ethics, applied ethics.",
        "what is metaphysics": "Metaphysics is the branch of philosophy that examines the "
                                "fundamental nature of reality, including existence, objects "
                                "and their properties, space and time, cause and effect.",
        "what is epistemology": "Epistemology is the branch of philosophy concerned with "
                                 "knowledge — its nature, sources, limits, and validity.",
        "what is logic": "Logic is the systematic study of valid forms of inference. It "
                         "distinguishes good from bad reasoning. Branches: formal, informal, "
                         "symbolic, mathematical.",
        "what is existentialism": "Existentialism is a philosophy emphasizing individual "
                                    "existence, freedom, and choice. Key figures: Kierkegaard, "
                                    "Nietzsche, Sartre, Camus. 'Existence precedes essence.'",
        "what is stoicism": "Stoicism is a Hellenistic philosophy founded in Athens by Zeno of "
                            "Citium c. 300 BCE. Teaches virtue as the only good, destructive "
                            "emotions as the only evil, and acceptance of what we cannot control.",
        "what is utilitarianism": "Utilitarianism is an ethical theory holding that the best "
                                    "action is the one that maximizes overall happiness or "
                                    "utility. Key figures: Bentham, Mill.",
        "what is a fallacy": "A logical fallacy is a flaw in reasoning that renders an argument "
                              "invalid or unsound. Common types: ad hominem, straw man, false "
                              "dichotomy, slippery slope, circular reasoning.",
        "ngụy biện là gì": "Ngụy biện (fallacy) là lỗi suy luận khiến cho lập luận không hợp "
                          "logic. Các loại phổ biến: ngụy biện cá nhân (ad hominem), người rơm "
                          "(straw man), lưỡng đề sai (false dichotomy).",
        "what is daoism": "Daoism (Taoism) is a Chinese philosophy emphasizing living in "
                          "harmony with the Tao (the Way). Founded by Laozi (Tao Te Ching). "
                          "Key concepts: wu wei (non-action), yin-yang, simplicity.",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(name="Philosophy", domain="philosophy", config=config)

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

        # Path 1: philosopher lookup
        for name, info in self._PHILOSOPHERS.items():
            if name in q_lower:
                answer = info
                confidence = 0.85  # factual data, well-sourced
                reasoning = f"local_knowledge: philosopher '{name}'"
                evidence = {"value": info, "source": "local_knowledge", "philosopher": name}
                break

        # Path 2: concept lookup
        if not answer:
            for key, val in self._CONCEPTS.items():
                if key in q_lower:
                    answer = val
                    confidence = 0.85
                    reasoning = f"local_knowledge: concept '{key}'"
                    evidence = {"value": val, "source": "local_knowledge", "concept": key}
                    break

        if not answer:
            confidence = 0.0
            reasoning = "Philosophy pattern not recognized — try 'Who was Socrates?' or 'What is ethics?'"

        resp = SLMResponse(
            question=question, answer=answer, confidence=confidence,
            domain="philosophy", reasoning=reasoning,
            evidence=evidence, slm_name=self.name,
            processing_time=time.time() - start,
        )
        self.cache_response(question, resp)
        self._end_timer(start, confidence > 0.3)
        return resp

    def get_confidence(self, question: str, answer: str) -> float:
        return 0.85 if answer else 0.0


# [OPT-7] Alias — "SLM" in SCP means "Specialized Logic Module" (DomainExpert).
PhilosophyExpert = Philosophy
