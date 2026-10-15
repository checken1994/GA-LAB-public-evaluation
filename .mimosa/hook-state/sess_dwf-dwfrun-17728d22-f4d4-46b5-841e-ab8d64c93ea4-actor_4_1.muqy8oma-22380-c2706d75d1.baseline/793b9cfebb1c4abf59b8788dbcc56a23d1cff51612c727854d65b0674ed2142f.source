"""
[OPT-13] Economics — DomainExpert for economics (uses FRED + WorldBank).

SCP's "SLM" means "Specialized Logic Module" (deterministic dispatcher),
NOT "Small Language Model". This SLM:
  1. Checks local knowledge (GDP/inflation/interest rate basics)
  2. Falls back to FRED (US indicators) or WorldBank (global) DataSource
  3. Returns SLMResponse with answer + confidence + source

Pattern: Base subclass with local knowledge dict + DataSource fallback.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from scp.runtime.slm_base import BaseSLM as Base
from scp.runtime.slm_base import SLMResponse

logger = logging.getLogger("scp.slms")


class Economics(Base):
    """Economics DomainExpert — routes to FRED (US) + WorldBank (global)."""

    # Local knowledge: basic economic facts (fast path, no API call)
    _LOCAL_KNOWLEDGE: dict[str, str] = {
        "what is gdp": "GDP (Gross Domestic Product) is the total monetary value of all "
                       "finished goods and services produced within a country's borders in a "
                       "specific time period (typically annually or quarterly).",
        "gdp là gì": "GDP (Tổng sản phẩm quốc nội) là tổng giá trị tiền tệ của tất cả "
                     "hàng hóa và dịch vụ cuối cùng được sản xuất trong phạm vi một quốc gia "
                     "trong một thời kỳ nhất định (thường là năm hoặc quý).",
        "what is inflation": "Inflation is the rate at which the general level of prices for "
                              "goods and services rises, eroding purchasing power. Measured by "
                              "CPI (Consumer Price Index).",
        "lạm phát là gì": "Lạm phát là tỷ lệ tăng mức giá chung của hàng hóa và dịch vụ "
                          "theo thời gian, làm giảm sức mua của đồng tiền. Đo bằng CPI.",
        "what is interest rate": "Interest rate is the amount charged by a lender to a borrower "
                                  "for the use of assets, expressed as a percentage of principal.",
        "lãi suất là gì": "Lãi suất là tỷ lệ phần trăm tiền vay phải trả cho người cho vay, "
                          "tính trên gốc tiền vay.",
        "what is cpi": "CPI (Consumer Price Index) measures the average change over time in "
                       "prices paid by consumers for a basket of goods and services.",
        "what is unemployment": "Unemployment rate is the percentage of the labor force that is "
                                 "without work but available for and seeking employment.",
        "thất nghiệp là gì": "Tỷ lệ thất nghiệp là phần trăm lực lượng lao động không có việc "
                             "làm nhưng đang tìm kiếm việc.",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(name="Economics", domain="economics", config=config)
        # Lazy-load DataSources (fail gracefully if API key missing)
        self._fred = None
        self._worldbank = None
        try:
            from scp.data_sources.fred import FREDDataSource
            self._fred = FREDDataSource()
        except Exception as e:
            logger.debug(f"Economics FRED init: {e}", exc_info=True)
        try:
            from scp.data_sources.worldbank import WorldBankDataSource
            self._worldbank = WorldBankDataSource()
        except Exception as e:
            logger.debug(f"Economics WorldBank init: {e}", exc_info=True)

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

        # Fast path 1: local knowledge
        for key, val in self._LOCAL_KNOWLEDGE.items():
            if key in q_lower:
                answer = val
                confidence = 0.7  # local knowledge baseline
                reasoning = f"local_knowledge: {key}"
                evidence = {"value": val, "source": "local_knowledge", "key": key}
                break

        # Fallback path: try FRED then WorldBank
        if not answer:
            # Try FRED (US-specific indicators)
            if self._fred and self._fred.enabled:
                try:
                    result = self._fred.query(q)
                    if result and result.get("value"):
                        answer = (f"{result['value']} (source: FRED, "
                                  f"series: {result.get('metadata', {}).get('label', '?')}, "
                                  f"date: {result.get('metadata', {}).get('date', '?')})")
                        confidence = 0.8
                        reasoning = f"FRED: {result.get('metadata', {}).get('series_id', '?')}"
                        evidence = result
                except Exception as e:
                    logger.debug(f"Economics FRED query: {e}", exc_info=True)

            # Try WorldBank (global indicators)
            if not answer and self._worldbank and self._worldbank.enabled:
                try:
                    result = self._worldbank.query(q)
                    if result and result.get("value"):
                        meta = result.get("metadata", {})
                        answer = (f"{result['value']} (source: WorldBank, "
                                  f"indicator: {meta.get('indicator', '?')}, "
                                  f"country: {meta.get('country', '?')}, "
                                  f"year: {meta.get('date', '?')})")
                        confidence = 0.8
                        reasoning = f"WorldBank: {meta.get('indicator_code', '?')}"
                        evidence = result
                except Exception as e:
                    logger.debug(f"Economics WorldBank query: {e}", exc_info=True)

        if not answer:
            confidence = 0.0
            reasoning = "Economics pattern not recognized (no local match + no DataSource hit)"

        resp = SLMResponse(
            question=question, answer=answer, confidence=confidence,
            domain="economics", reasoning=reasoning,
            evidence=evidence, slm_name=self.name,
            processing_time=time.time() - start,
        )
        self.cache_response(question, resp)
        self._end_timer(start, confidence > 0.3)
        return resp

    def get_confidence(self, question: str, answer: str) -> float:
        # Local knowledge: 0.7; DataSource hit: 0.8; none: 0.0
        if not answer:
            return 0.0
        return 0.8 if "FRED" in answer or "WorldBank" in answer else 0.7


# [OPT-7] Alias — "SLM" in SCP means "Specialized Logic Module" (DomainExpert).
EconomicsExpert = Economics
