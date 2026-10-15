"""
[OPT-16] Management — DomainExpert for management theory (local knowledge).

SCP's "SLM" means "Specialized Logic Module" (deterministic dispatcher).
Covers: strategy, HR, marketing theory, operations, organizational behavior.
No external DataSource needed — management theory is stable knowledge.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from scp.runtime.slm_base import BaseSLM as Base
from scp.runtime.slm_base import SLMResponse

logger = logging.getLogger("scp.slms")


class Management(Base):
    """Management DomainExpert — strategy/HR/marketing/operations theory."""

    _FRAMEWORKS: dict[str, str] = {
        "what is swot": "SWOT Analysis is a strategic planning framework that evaluates "
                        "Strengths, Weaknesses, Opportunities, and Threats. Developed by "
                        "Albert Humphrey in the 1960s at Stanford. Used for situational "
                        "analysis in business strategy.",
        "what is porter's 5 forces": "Porter's Five Forces is a framework for analyzing "
                                      "industry competition: (1) threat of new entrants, "
                                      "(2) bargaining power of suppliers, (3) bargaining "
                                      "power of buyers, (4) threat of substitutes, (5) "
                                      "rivalry among existing competitors. By Michael Porter, 1979.",
        "what is pest": "PEST Analysis examines Political, Economic, Social, and Technological "
                        "factors affecting an organization. Extended variants: PESTEL (adds "
                        "Environmental, Legal), STEEPLE (adds Ethical).",
        "what is bcg matrix": "BCG Matrix (Boston Consulting Group, 1970) classifies products "
                              "or business units into 4 categories based on market growth and "
                              "market share: Stars, Cash Cows, Question Marks, Dogs.",
        "what is kotter's 8 step": "Kotter's 8-Step Change Model (John Kotter, 1996): "
                                    "(1) Create urgency, (2) Form powerful coalition, (3) "
                                    "Create vision for change, (4) Communicate vision, (5) "
                                    "Remove obstacles, (6) Create short-term wins, (7) Build "
                                    "on change, (8) Anchor changes in corporate culture.",
        "what is maslow": "Maslow's Hierarchy of Needs (Abraham Maslow, 1943) is a motivational "
                          "theory with 5 levels: physiological, safety, love/belonging, esteem, "
                          "self-actualization. Lower needs must be met before higher ones.",
        "what is mcgregor theory x y": "McGregor's Theory X and Y (Douglas McGregor, 1960): "
                                        "Theory X assumes employees dislike work and need "
                                        "control; Theory Y assumes employees are self-motivated "
                                        "and seek responsibility.",
        "what is the marketing mix": "Marketing Mix (4 Ps): Product, Price, Place, Promotion. "
                                      "Concept by E. Jerome McCarthy (1960). Extended 7 Ps "
                                      "add: People, Process, Physical evidence.",
        "what is lean": "Lean management is a methodology focused on minimizing waste within "
                        "manufacturing systems while simultaneously maximizing productivity. "
                        "Originated from Toyota Production System (TPS).",
        "what is six sigma": "Six Sigma is a data-driven quality management methodology aiming "
                              "to reduce defects to 3.4 per million opportunities (6σ). "
                              "Developed by Motorola (Bill Smith) in 1986.",
    }

    _CONCEPTS: dict[str, str] = {
        "what is management": "Management is the coordination and administration of tasks to "
                               "achieve organizational goals. Functions (Fayol): planning, "
                               "organizing, commanding, coordinating, controlling.",
        "what is leadership": "Leadership is the ability to influence and guide others toward "
                               "achieving goals. Key styles: autocratic, democratic, "
                               "transformational, transactional, laissez-faire.",
        "what is strategic planning": "Strategic planning is the process of defining an "
                                       "organization's strategy, direction, and resource "
                                       "allocation. Typically spans 3-5 years.",
        "what is kpi": "KPI (Key Performance Indicator) is a measurable value that demonstrates "
                        "how effectively an organization achieves key business objectives.",
        "what is okr": "OKR (Objectives and Key Results) is a goal-setting framework: Objective "
                       "(qualitative goal) + 3-5 Key Results (quantitative metrics). Popularized "
                       "by Andy Grove at Intel, adopted by Google.",
        "what is change management": "Change management is a structured approach to transitioning "
                                       "individuals/organizations from current state to desired "
                                       "future state. Frameworks: Kotter 8-step, ADKAR, Lewin's 3-stage.",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(name="Management", domain="management", config=config)

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

        # Path 1: framework lookup
        for key, val in self._FRAMEWORKS.items():
            if key in q_lower:
                answer = val
                confidence = 0.8  # well-established management theory
                reasoning = f"local_knowledge: framework '{key}'"
                evidence = {"value": val, "source": "local_knowledge", "framework": key}
                break

        # Path 2: general concepts
        if not answer:
            for key, val in self._CONCEPTS.items():
                if key in q_lower:
                    answer = val
                    confidence = 0.75
                    reasoning = f"local_knowledge: concept '{key}'"
                    evidence = {"value": val, "source": "local_knowledge", "concept": key}
                    break

        if not answer:
            confidence = 0.0
            reasoning = "Management pattern not recognized — try 'What is SWOT?' or 'What is OKR?'"

        resp = SLMResponse(
            question=question, answer=answer, confidence=confidence,
            domain="management", reasoning=reasoning,
            evidence=evidence, slm_name=self.name,
            processing_time=time.time() - start,
        )
        self.cache_response(question, resp)
        self._end_timer(start, confidence > 0.3)
        return resp

    def get_confidence(self, question: str, answer: str) -> float:
        return 0.8 if answer else 0.0


# [OPT-7] Alias — "SLM" in SCP means "Specialized Logic Module" (DomainExpert).
ManagementExpert = Management
