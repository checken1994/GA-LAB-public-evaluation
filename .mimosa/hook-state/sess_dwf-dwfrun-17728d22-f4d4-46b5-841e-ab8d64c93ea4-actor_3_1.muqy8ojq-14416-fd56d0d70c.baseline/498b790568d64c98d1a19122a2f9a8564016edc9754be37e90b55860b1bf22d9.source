# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
"""GoalParser for SCP Hands v3.7.

The parser proposes an allowlisted plan from natural language. It never
executes a plan and never grants approval. Local LLM parsing is preferred; a
small deterministic fallback keeps the API usable when the local model is
offline.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from .planner import PLAN_VERSION, HandsPlanner

logger = logging.getLogger(__name__)



class GoalParser:
    """Convert natural-language goals to validated, reviewable plan proposals."""

    def __init__(self, planner: HandsPlanner | None = None) -> None:
        self.planner = planner or HandsPlanner()
        self.model_label = os.environ.get("SCP_MODEL_VERSION", "1.6")

    def _schema(self) -> dict[str, Any]:
        actions = self.planner.executor.registry.list()
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "goal": {"type": "string"},
                "steps": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "stepId": {"type": "string"},
                            "action": {"type": "string", "enum": actions},
                            "params": {"type": "object", "additionalProperties": True},
                            "capabilityLevel": {"type": "integer", "minimum": 0, "maximum": 5},
                            "approved": {"type": "boolean"},
                            "dependsOn": {"type": "array", "items": {"type": "string"}},
                            "precondition": {"type": "object", "additionalProperties": True},
                            "postcondition": {"type": "object", "additionalProperties": True},
                            "retryPolicy": {"type": "object", "additionalProperties": True},
                        },
                        "required": ["stepId", "action", "params", "dependsOn"],
                    },
                },
                "reasoning": {"type": "string"},
                "risks": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["goal", "steps", "reasoning", "risks"],
        }

    def _prompt(self, goal: str) -> str:
        actions = [item["name"] for item in self.planner.executor.registry.list()]
        return f"""Bạn là GoalParser của SCP Hands {PLAN_VERSION}. Chỉ đề xuất kế hoạch, không thực thi và không tự cấp approval.
Mục tiêu người dùng: {goal}

Chỉ được dùng action trong allowlist sau: {json.dumps(actions, ensure_ascii=False)}.
Mỗi step phải có stepId, action, params, dependsOn. Dùng precondition/postcondition/retryPolicy khi hữu ích.
Không tạo action mới, không dùng shell tùy ý, không truy cập credential/cookie/CAPTCHA, không gửi dữ liệu riêng tư.
Các action requires approval phải giữ approved=false và đưa lý do vào risks. Kế hoạch phải ngắn, tuần tự hoặc DAG an toàn.
Trả về JSON đúng schema, không markdown. Mục tiêu không chắc chắn thì đề xuất bước quan sát an toàn trước, không đoán.
"""

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any] | None:
        text = str(text or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
        try:
            value = json.loads(text)
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            logger.debug('GoalParser._extract_json: json.JSONDecodeError ignored', exc_info=True)
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                return None
            try:
                value = json.loads(match.group(0))
                return value if isinstance(value, dict) else None
            except json.JSONDecodeError:
                logger.debug('GoalParser._extract_json: json.JSONDecodeError ignored', exc_info=True)
                return None

    def _deterministic_fallback(self, goal: str) -> dict[str, Any]:
        lowered = goal.lower()
        if any(token in lowered for token in ("tìm", "tra cứu", "search", "nguồn", "internet")):
            steps = [{"stepId": "search", "action": "web.search_public", "params": {"query": goal, "maxResults": 8}, "dependsOn": [], "postcondition": {"type": "verification_passed"}}]
            reasoning = "Nhận diện mục tiêu tìm kiếm công khai; chỉ đề xuất web.search_public an toàn."
        else:
            steps = [{"stepId": "status", "action": "pc.status", "params": {}, "dependsOn": [], "postcondition": {"type": "verification_passed"}}]
            reasoning = "Không đủ tín hiệu để suy diễn hành động thay đổi trạng thái; đề xuất quan sát pc.status trước."
        return {"goal": goal, "steps": steps, "reasoning": reasoning, "risks": ["Đây là plan đề xuất; cần người dùng review trước khi chạy."]}

    def _validate_proposal(self, proposal: dict[str, Any], goal: str) -> dict[str, Any]:
        if not isinstance(proposal.get("steps"), list) or not proposal["steps"]:
            raise ValueError("GoalParser returned no steps")
        sanitized: list[dict[str, Any]] = []
        for index, raw in enumerate(proposal["steps"][:20]):
            if not isinstance(raw, dict):
                raise ValueError(f"GoalParser step {index + 1} is not an object")
            step = dict(raw)
            step["stepId"] = str(step.get("stepId") or f"step-{index + 1:02d}")[:80]
            step["action"] = str(step.get("action", "")).strip()
            step["params"] = step.get("params") if isinstance(step.get("params"), dict) else {}
            step["dependsOn"] = [str(item) for item in step.get("dependsOn", [])]
            definition = self.planner.executor.registry.get(step["action"])
            if definition is None:
                raise ValueError(f"GoalParser proposed unknown action: {step['action']}")
            step["capabilityLevel"] = max(0, min(int(step.get("capabilityLevel", definition.capability_level)), 5))
            # Parser cannot grant approval, even if a model emits approved=true.
            step["approved"] = False
            sanitized.append(step)
        normalized = {
            "goal": str(proposal.get("goal") or goal).strip()[:1000],
            "steps": sanitized,
            "reasoning": str(proposal.get("reasoning") or "")[:2000],
            "risks": [str(item)[:500] for item in proposal.get("risks", []) if str(item).strip()][:20],
        }
        # Let the same Planner schema validate dependencies/conditions/retry limits.
        preview = self.planner.create_plan(normalized["goal"], normalized["steps"], {"source": "goal_parser", "model": self.model_label, "proposalOnly": True})
        normalized["plan"] = preview
        normalized["proposalOnly"] = True
        normalized["approved"] = False
        normalized["model"] = self.model_label
        return normalized

    async def parse(self, goal: str) -> dict[str, Any]:
        """Parse a goal into a validated proposal.

        [2026-08-29] The local-LLM path (_ask_local_json via LLM_BRIDGE_URL
        11434) was deleted together with the Ollama layer: the bridge is gone
        from the deployment, so planning is deterministic-only.
        """
        goal = str(goal or "").strip()
        if not goal:
            return {"success": False, "error": "Goal is empty", "proposalOnly": True}
        started = time.perf_counter()
        lineage = "deterministic_fallback"
        errors: list[str] = []
        proposal: dict[str, Any] | None = self._deterministic_fallback(goal)
        try:
            result = self._validate_proposal(proposal, goal)
            result.update({"success": True, "lineage": lineage, "durationMs": round((time.perf_counter() - started) * 1000, 2), "errors": errors})
            return result
        except (TypeError, ValueError, KeyError) as exc:
            return {"success": False, "error": str(exc), "lineage": lineage, "durationMs": round((time.perf_counter() - started) * 1000, 2), "errors": errors, "proposalOnly": True}
