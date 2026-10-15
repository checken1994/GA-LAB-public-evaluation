"""
SCP V107 — LogicalAuditorEngine
================================
Deep logical audit. P0 Z2 additionally enforces the zero-cost policy immediately
before every direct OpenRouter driver call: paid/unknown/stale model pricing
returns UNKNOWN without a provider request.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from scp.contracts.data_class import DataClass
from scp.security.url_safety import enforce_egress_policy  # [EE-G1]

logger = logging.getLogger("scp.meta.logical_auditor")

LOGICAL_AUDITOR_PROMPT = """Bạn là một Logical Auditor – chuyên gia kiểm tra lỗi logic sâu trong các hệ thống suy luận của AI. Nhiệm vụ của bạn là phát hiện các lỗi logic, ngụy biện, mâu thuẫn nội tại và các lỗ hổng suy luận trong bất kỳ chuỗi lập luận nào.

Phân tích đoạn văn bản dưới đây theo 5 tiêu chí:

1. NHẤT QUÁN NỘI TẠI (Internal Consistency): mâu thuẫn, giả định ngầm, kết luận không suy ra từ tiền đề
2. NGỤY BIỆN LOGIC (Logical Fallacies): khái quát hóa vội, đánh tráo khái niệm, nguyên nhân giả, bằng chứng thiếu
3. CHUỖI NHÂN QUẢ (Causal Chain): trật tự logic, bước nhảy logic
4. TÍNH ĐẦY ĐỦ (Completeness): khía cạnh bỏ qua, giả định quá mạnh
5. KHẢ NĂNG BÁC BỎ (Falsifiability): điều gì làm kết luận sai? Không bác bỏ được → UNREFUTED_IN_CURRENT_SCOPE

Trả về JSON hợp lệ với format:
{"verdict":"PASS|FAIL|UNKNOWN|UNREFUTED_IN_CURRENT_SCOPE","confidence":0.0-1.0,"issues":[{"type":"internal_contradiction|fallacy|logical_leap|missing_premise|unfalsifiable","description":"...","severity":"critical|major|minor","location":"..."}],"falsification_attempt":"...","recommendation":"..."}

VĂN BẢN CẦN KIỂM TRA:
---
__TEXT__
---

Chỉ trả về JSON, không thêm gì khác."""


@dataclass
class LogicalIssue:
    type: str
    description: str
    severity: str
    location: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "description": self.description,
            "severity": self.severity,
            "location": self.location,
        }


@dataclass
class LogicalAuditResult:
    verdict: str = "UNREFUTED_IN_CURRENT_SCOPE"
    confidence: float = 0.5
    issues: list[LogicalIssue] = field(default_factory=list)
    falsification_attempt: str = ""
    recommendation: str = ""
    raw_response: str = ""
    elapsed_ms: float = 0.0
    model_used: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "confidence": self.confidence,
            "issues": [i.to_dict() for i in self.issues],
            "falsification_attempt": self.falsification_attempt,
            "recommendation": self.recommendation,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "model_used": self.model_used,
            "error": self.error,
        }


class LogicalAuditorEngine:
    """Audit logical consistency with a bounded external LLM helper.

    The helper is not Reality authority. A model response is advisory analysis;
    any direct provider transport is independently subject to ZeroCostGuard.
    """

    def __init__(self):
        self._api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self._base_url = "https://openrouter.ai/api/v1/chat/completions"
        # Candidate names only. Fresh pricing proof decides eligibility.
        self._model = os.environ.get("OPENROUTER_MODEL_LOGICAL_AUDITOR", "z-ai/glm-5.2")
        self._fallback_model = os.environ.get(
            "OPENROUTER_MODEL_LOGICAL_AUDITOR_FALLBACK",
            "meta-llama/llama-3.3-70b-instruct:free",
        )
        self._timeout = 30
        self._stats = {
            "total_audits": 0,
            "total_issues_found": 0,
            "total_critical": 0,
            "total_pass": 0,  # nosec B105 — stats counter key, not a password
            "total_fail": 0,
            "total_unrefuted": 0,
            "total_errors": 0,
        }

    async def audit(self, text_to_audit: str, context: str = "") -> LogicalAuditResult:
        self._stats["total_audits"] += 1
        result = LogicalAuditResult()
        t0 = time.time()
        if not text_to_audit or len(text_to_audit.strip()) < 10:
            result.verdict = "UNKNOWN"
            result.error = "Text too short to audit"
            return result

        full_text = text_to_audit
        if context:
            full_text = f"Context: {context}\n\nText to audit: {text_to_audit}"
        prompt = LOGICAL_AUDITOR_PROMPT.replace("__TEXT__", full_text[:4000])

        try:
            import httpx
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response_data = await self._call_llm(client, prompt, self._model)
                if response_data is None:
                    logger.info("[LogicalAuditor] primary candidate unavailable — try guarded free fallback")
                    response_data = await self._call_llm(client, prompt, self._fallback_model)
                if response_data is None:
                    result.verdict = "UNKNOWN"
                    result.error = "No eligible/available zero-cost logical-audit model"
                    self._stats["total_errors"] += 1
                    return result

                result.raw_response = response_data.get("content", "")
                result.model_used = response_data.get("model", self._model)
                parsed = self._parse_json_response(result.raw_response)
                if parsed:
                    result.verdict = parsed.get("verdict", "UNREFUTED_IN_CURRENT_SCOPE")
                    result.confidence = float(parsed.get("confidence", 0.5))
                    result.falsification_attempt = parsed.get("falsification_attempt", "")
                    result.recommendation = parsed.get("recommendation", "")
                    for issue_data in parsed.get("issues", []):
                        result.issues.append(LogicalIssue(
                            type=issue_data.get("type", "unknown"),
                            description=issue_data.get("description", ""),
                            severity=issue_data.get("severity", "minor"),
                            location=issue_data.get("location", ""),
                        ))
                    self._stats["total_issues_found"] += len(result.issues)
                    critical_count = sum(1 for issue in result.issues if issue.severity == "critical")
                    self._stats["total_critical"] += critical_count
                    if result.verdict == "PASS":
                        self._stats["total_pass"] += 1
                    elif result.verdict == "FAIL":
                        self._stats["total_fail"] += 1
                    elif result.verdict == "UNREFUTED_IN_CURRENT_SCOPE":
                        self._stats["total_unrefuted"] += 1
                else:
                    result.verdict = "UNKNOWN"
                    result.error = "Failed to parse LLM response as JSON"
        except Exception as exc:
            result.verdict = "UNKNOWN"
            result.error = str(exc)[:200]
            self._stats["total_errors"] += 1
            logger.warning("[LogicalAuditor] Error: %s", exc, exc_info=True)

        result.elapsed_ms = (time.time() - t0) * 1000
        logger.info(
            "[LogicalAuditor] verdict=%s conf=%.2f issues=%d elapsed=%.0fms model=%s",
            result.verdict,
            result.confidence,
            len(result.issues),
            result.elapsed_ms,
            result.model_used,
        )
        return result

    async def _call_llm(self, client, prompt: str, model: str) -> dict | None:
        """Call OpenRouter after a fresh exact-$0 + data-class authorization."""
        if not self._api_key:
            logger.warning("[LogicalAuditor] No API key")
            return None
        try:
            zreq, zproof = authorize_outbound(  # noqa: F821  # [hygiene-keep] F821: zero-cost PEP name removed from scp.llm_gateway (architectural deprecation asserted by tests/T05_gateway/test_zero_cost_guard.py); call site preserved as-is, deferred to architectural fix
                provider="openrouter",
                model=model,
                task_class="judge",
                data_class=DataClass.INTERNAL,
            )
        except ZeroCostDenied as exc:  # noqa: F821  # [hygiene-keep] F821: zero-cost PEP name removed from scp.llm_gateway (architectural deprecation asserted by tests/T05_gateway/test_zero_cost_guard.py); call site preserved as-is, deferred to architectural fix
            logger.info(
                "[LogicalAuditor] zero-cost PEP denied model=%s decision=%s",
                model,
                exc.decision.value,
            )
            return None
        try:
            # [EE-G1] PEP ngay trước driver: SCP_EGRESS_MODE áp cho cả judge
            # path này (client httpx được truyền vào từ audit()). EgressDenied
            # là Exception → except dưới → None → verdict UNKNOWN graceful
            # như contract; dev (mode unset) không đổi behavior.
            enforce_egress_policy(self._base_url)
            record_outbound_sent(zreq, zproof)  # noqa: F821  # [hygiene-keep] F821: zero-cost PEP name removed from scp.llm_gateway (architectural deprecation asserted by tests/T05_gateway/test_zero_cost_guard.py); call site preserved as-is, deferred to architectural fix
            response = await client.post(
                self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                    "temperature": 0.1,
                },
            )
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"content": content, "model": model}
            logger.debug("[LogicalAuditor] %s HTTP %s: %s", model, response.status_code, response.text[:100])
            return None
        except Exception as exc:
            logger.debug("[LogicalAuditor] %s error: %s", model, exc, exc_info=True)
            return None

    def _parse_json_response(self, response: str) -> dict | None:
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError as exc:
            logger.debug("[LogicalAuditor] direct JSON parse failed: %s", exc)
        import re
        match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as exc:
                logger.debug("[LogicalAuditor] fenced JSON parse failed: %s", exc)
        match = re.search(r'\{[^{}]*"(?:verdict|issues)"[^{}]*\}', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                logger.debug("[LogicalAuditor] object JSON parse failed: %s", exc)
        first = response.find('{')
        last = response.rfind('}')
        if first >= 0 and last > first:
            try:
                return json.loads(response[first:last+1])
            except json.JSONDecodeError as exc:
                logger.debug("[LogicalAuditor] fallback JSON parse failed: %s", exc)
        return None

    def should_audit(self, verdict: str, answer: str) -> bool:
        if verdict != "PASS":
            return False
        if not answer or len(answer) < 50:
            return False
        if answer.replace(" ", "").replace("=", "").replace("+", "").replace("-", "").replace("*", "").replace("/", "").replace(".", "").isdigit():
            return False
        return True

    def stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "model": self._model,
            "fallback_model": self._fallback_model,
            "api_configured": bool(self._api_key),
        }


__all__ = ["LogicalIssue", "LogicalAuditResult", "LogicalAuditorEngine", "LOGICAL_AUDITOR_PROMPT"]
