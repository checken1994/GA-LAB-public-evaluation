"""
SCP Typed Evaluation API — TypeSafe SystemOne compatible (/v1/systemone, /v1/eval).

Allows LLM models, agents, and external systems to call SCP as an independent,
verifiable evaluation engine with structured questions:
  - 'noul': binary probability (0.0 to 1.0)
  - 'choice': classification with probability distribution and confidence
  - 'score': hierarchical scale rating along ordered criteria

Endpoints:
  POST /v1/systemone — Direct TypeSafe SystemOne wire format
  POST /v1/eval      — RESTful alias
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# [BLE001-fix] logger được định nghĩa local (cùng singleton "scp.api" như
# scp.api._shared) để ruff resolve được logging call trong except handler.
from scp.api._shared import get_judge

logger = logging.getLogger("scp.api")
from scp.core.request_run_ledger import RequestRunLedger, traced_request
from scp.llm_gateway import get_gateway
from scp.security.jwt_guard import security, verify_api_key, verify_jwt_token
from scp.security.tier1_guard import check as tier1_check

_EVAL_LEDGER = RequestRunLedger()
router = APIRouter(tags=["evaluation"])

# Dedicated rate limit for evaluation API (fail-closed bounded queue)
_EVAL_RATE_LIMIT_PER_MINUTE = int(os.environ.get("SCP_EVAL_RATE_LIMIT_PER_MINUTE", "60"))
_eval_request_history: dict[str, list[float]] = {}
_eval_rate_limit_lock = threading.Lock()


def _check_eval_rate_limit(client_id: str) -> bool:
    now = time.time()
    cutoff = now - 60.0
    with _eval_rate_limit_lock:
        timestamps = _eval_request_history.setdefault(client_id, [])
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)
        if len(timestamps) >= _EVAL_RATE_LIMIT_PER_MINUTE:
            return False
        timestamps.append(now)
        if len(_eval_request_history) > 1000:
            for k in list(_eval_request_history.keys())[:200]:
                _eval_request_history.pop(k, None)
        return True


def _get_evaluation_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    try:
        payload = verify_jwt_token(credentials)
        user = payload.get("sub")
        if user:
            return user
    except HTTPException as exc:
        logger.debug("JWT verification failed in _get_evaluation_user fallback: %s", exc)

    try:
        api_payload = verify_api_key(credentials)
        return api_payload.get("sub", "admin")
    except HTTPException as exc:
        logger.debug("API key verification failed in _get_evaluation_user fallback: %s", exc)

    raise HTTPException(status_code=401, detail="Invalid token")


class QuestionSpec(BaseModel):
    type: str = Field(..., description="Type of question: 'noul', 'choice', or 'score'")
    instructions: str = Field(..., description="Instruction or evaluation question")
    criteria: dict[str, Any] | list[str] | Any | None = Field(
        None, description="Criteria for choice (dict) or score (ordered list)"
    )


class EvaluationRequest(BaseModel):
    state: str = Field(..., description="The content or state to evaluate (text, code, diff, plan)")
    questions: dict[str, QuestionSpec] = Field(..., description="Dictionary of question specifications")
    model: str | None = Field("scp-eval-latest", description="Model requested")


class EvaluationResponse(BaseModel):
    model: str
    answers: dict[str, Any]
    verdict: str = "UNKNOWN"
    confidence: float = 0.0
    evidence: dict[str, Any] = Field(default_factory=dict)
    elapsed_ms: float = 0.0


def _clean_json_str(raw: str) -> str:
    """Strip markdown code fence if present."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


def _build_evaluation_prompt(state: str, questions: dict[str, QuestionSpec]) -> str:
    q_specs = {}
    for name, q in questions.items():
        spec = {"type": q.type, "instructions": q.instructions}
        if q.criteria is not None:
            spec["criteria"] = q.criteria
        q_specs[name] = spec

    sanitized_state = state[:20000].replace('"""', '\\"\\"\\"')
    sanitized_state = re.sub(r"<\s*/?\s*state_to_evaluate\s*>", "[ESCAPED_TAG: state_to_evaluate]", sanitized_state, flags=re.IGNORECASE)
    prompt = f"""You are the SCP Typed Evaluation Engine, conforming to the TypeSafe SystemOne evaluation standard.
Evaluate the following STATE objectively according to the given QUESTIONS.

<state_to_evaluate>
\"\"\"
{sanitized_state}
\"\"\"
</state_to_evaluate>

QUESTIONS TO EVALUATE:
{json.dumps(q_specs, ensure_ascii=False, indent=2)}

OUTPUT FORMAT RULES:
Return a single strictly valid JSON object with the following schema:
{{
  "answers": {{
    "<question_name>": {{
      // If type == "noul":
      "type": "noul",
      "noul": <float between 0.00 and 1.00>

      // If type == "choice":
      "type": "choice",
      "choice": "<selected_key_from_criteria>",
      "confidence": <float between 0.00 and 1.00>,
      "probabilities": {{ "<option_1>": <float>, ... }}

      // If type == "score":
      "type": "score",
      "score": <float rank on 1.0 to N.0 scale>,
      "confidence": <float between 0.00 and 1.00>,
      "legend": {{ "<level_1>": 1, ... }}
    }}
  }},
  "verdict": "PASS" | "FAIL" | "UNCERTAIN" | "UNKNOWN",
  "confidence": <float between 0.00 and 1.00>,
  "reasoning": "<brief summary rationale>"
}}
Do NOT output markdown commentary outside the JSON."""
    return prompt


def _fallback_answers(questions: dict[str, QuestionSpec], is_safe: bool) -> dict[str, Any]:
    """Fallback deterministic answers if LLM fails."""
    answers = {}
    for name, q in questions.items():
        q_type = (q.type or "").lower().strip()
        if q_type == "noul":
            answers[name] = {
                "type": "noul",
                "noul": 0.80 if is_safe else 0.20,
            }
        elif q_type == "choice":
            criteria_keys = list(q.criteria.keys()) if isinstance(q.criteria, dict) else ["PASS", "FAIL"]
            default_choice = criteria_keys[0] if criteria_keys else "UNKNOWN"
            probs = {k: round(1.0 / len(criteria_keys), 2) for k in criteria_keys} if criteria_keys else {}
            answers[name] = {
                "type": "choice",
                "choice": default_choice,
                "confidence": 0.50,
                "probabilities": probs,
            }
        elif q_type == "score":
            levels = q.criteria if isinstance(q.criteria, list) else ["low", "medium", "high"]
            legend = {lvl: idx + 1 for idx, lvl in enumerate(levels)}
            mid_score = (len(levels) + 1) / 2.0
            answers[name] = {
                "type": "score",
                "score": mid_score,
                "confidence": 0.50,
                "legend": legend,
            }
        else:
            answers[name] = {"type": q_type, "value": None}
    return answers


@router.post("/v1/systemone", response_model=EvaluationResponse)
@router.post("/v1/eval", response_model=EvaluationResponse)
@traced_request(_EVAL_LEDGER, require_write=False, action="scp_eval")
async def evaluate_systemone(
    req: EvaluationRequest,
    request: Request,
    current_user: str = Depends(_get_evaluation_user),
):
    """TypeSafe SystemOne compatible structured evaluation endpoint.

    Evaluates state against typed questions (noul/choice/score) with SCP evidence.
    """
    client_ip = getattr(getattr(request, "client", None), "host", "127.0.0.1") or "127.0.0.1"
    client_key = f"{current_user}:{client_ip}"
    if not _check_eval_rate_limit(client_key):
        raise HTTPException(
            status_code=429,
            detail=f"Evaluation API rate limit exceeded ({_EVAL_RATE_LIMIT_PER_MINUTE} req/min). Please try again later.",
        )

    t0 = time.perf_counter()
    state_text = (req.state or "").strip()
    if not state_text:
        raise HTTPException(status_code=422, detail="Field 'state' cannot be empty")
    if not req.questions:
        raise HTTPException(status_code=422, detail="Field 'questions' cannot be empty")

    has_tag_injection = bool(re.search(r"<\s*/\s*state_to_evaluate\s*>", state_text, flags=re.IGNORECASE))

    # 1. Tier 1 Structural & Safety Check on state
    t1 = tier1_check("evaluation", state_text, "")
    is_safe = t1.passed

    # 2. Consult SCP Knowledge Base for relevant internal truth/evidence
    judge = get_judge()
    kb_refs = []
    if hasattr(judge, "_consult_knowledge"):
        try:
            kb_refs = judge._consult_knowledge(state_text[:500])
        except Exception as e:
            logger.debug("Evaluation KB consult error: %s", e, exc_info=True)

    # 3. Call LLM Gateway with evaluation prompt
    prompt = _build_evaluation_prompt(state_text, req.questions)
    gateway = get_gateway()
    system_prompt = (
        "You are an impartial, highly accurate evaluation engine. "
        "Adhere strictly to TypeSafe SystemOne evaluation formats and probabilities."
    )

    llm_answer = None
    provider_used = "none"
    try:
        llm_answer, provider_used = await gateway.chat(
            question=prompt,
            context="",
            system_prompt=system_prompt,
            task="judge",
        )
    except Exception as exc:
        logger.warning("[EVAL] Gateway chat error: %s", exc, exc_info=True)

    answers: dict[str, Any] = {}
    verdict = "UNKNOWN" if is_safe else "FAIL"
    confidence = 0.0
    reasoning = "Evaluated via SCP Independent Verifier (fail-closed default)"

    if llm_answer:
        cleaned = _clean_json_str(llm_answer)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                raw_answers = parsed.get("answers", {})
                if isinstance(raw_answers, dict):
                    # Validate and map answers
                    for name, _q in req.questions.items():
                        if name in raw_answers:
                            answers[name] = raw_answers[name]
                if parsed.get("verdict"):
                    cand = str(parsed["verdict"]).strip().upper()
                    if cand in {"PASS", "FAIL", "UNCERTAIN", "UNKNOWN"}:
                        verdict = cand
                    else:
                        verdict = "UNKNOWN"
                if "confidence" in parsed:
                    try:
                        confidence = max(0.0, min(1.0, float(parsed["confidence"])))
                    except (ValueError, TypeError):
                        confidence = 0.0
                        logger.debug("Evaluation confidence float conversion ignored", exc_info=True)
                if parsed.get("reasoning"):
                    reasoning = str(parsed["reasoning"])
        except Exception as json_err:
            logger.warning("[EVAL] JSON parse error from LLM (%s): %s", provider_used, json_err, exc_info=True)

    # If any question missed in parsed answers, populate fallback
    if len(answers) < len(req.questions):
        fallbacks = _fallback_answers(req.questions, is_safe)
        for name, _spec in req.questions.items():
            if name not in answers and name in fallbacks:
                answers[name] = fallbacks[name]

    if not is_safe:
        verdict = "FAIL"
        confidence = 0.0
        reasoning += f" (Tier 1 check failed: {', '.join(t1.failures)})"
    elif has_tag_injection:
        verdict = "FAIL" if verdict == "FAIL" else "UNCERTAIN"
        confidence = 0.0
        reasoning += " (SecurityNotice: Prompt injection detected - contains closing tag </state_to_evaluate>)"

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return EvaluationResponse(
        model=req.model or "scp-eval-v1",
        answers=answers,
        verdict=verdict,
        confidence=confidence,
        evidence={
            "governance_decision": "UPHOLD" if verdict == "PASS" else "KILL",
            "tier1_passed": is_safe,
            "provider": provider_used,
            "reasoning": reasoning,
            "knowledge": kb_refs,
        },
        elapsed_ms=elapsed_ms,
    )
