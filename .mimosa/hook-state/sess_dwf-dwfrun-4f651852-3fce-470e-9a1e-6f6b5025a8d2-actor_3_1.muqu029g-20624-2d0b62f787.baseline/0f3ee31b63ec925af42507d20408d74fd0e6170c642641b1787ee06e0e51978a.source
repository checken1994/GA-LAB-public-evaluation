"""
[Task 8-A] V8.0-WHY analysis modes — extracted from why_engine.py

TẠI SAO: WhyEngine class had 3 large V8.0-WHY analysis modes (~345 LOC inline).
Extracted as standalone functions taking `engine` as first arg (for access to
_v80_why_llm_call, _v80_why_extract_json, _v80_normalize_cwe helpers).

Backward-compatible — WhyEngine.{type_inference_why, data_flow_why,
security_threat_why} become thin wrappers.

Modes:
  type_inference_why    — "Tại sao biến này là type X?" (TypeMismatch analysis)
  data_flow_why         — "Tại sao data đi từ A→B?" (data flow/taint analysis)
  security_threat_why   — "Tại sao code này unsafe?" (CWE security analysis)

All 3 modes are OPT-IN via env vars (SCP_WHY_TYPE_INFERENCE=1,
SCP_WHY_DATA_FLOW=1, SCP_WHY_SECURITY_THREAT=1) — default OFF to not break
existing flow.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("scp.why.v80_modes")


def type_inference_why(
    engine,
    var_name: str,
    expected_type: str,
    actual_type: str,
    context: str,
) -> dict:
    """[V8.0-WHY] WHY mode 1: type mismatch analysis.

    WHY asks "Tại sao biến này là type X?" — trace type flow to detect
    type bugs. Called by AutoFix when TypeContractScanner detects a
    TypeMismatch (function returns dict but caller expects int, etc.).

    WHY flow:
      1. "Tại sao result là dict?" → trace function return type
      2. "Tại sao caller expect int?" → trace usage pattern
      3. "Có thể cả hai đúng không?" → check if API contract changed

    Args:
        engine: WhyEngine instance (for _v80_why_llm_call, _v80_why_extract_json)
        var_name: variable name with type mismatch (e.g. "result")
        expected_type: type caller expects (e.g. "int")
        actual_type: type function actually returns (e.g. "dict")
        context: surrounding code (function signature + caller site)

    Returns:
        {
            "why_question": "Tại sao {var} được kỳ vọng là {expected} nhưng thực tế là {actual}?",
            "root_cause": str,
            "fix_direction": "change caller" | "change function" | "add type check",
            "confidence": float (0.0-1.0),
            "llm_used": bool,
        }

    Env:
        SCP_WHY_TYPE_INFERENCE=1 — OPT-IN (default OFF — don't break flow).
    """
    why_q = (
        f"Tại sao {var_name} được kỳ vọng là {expected_type} "
        f"nhưng thực tế là {actual_type}?"
    )
    # Defensive default — returned if env OFF or LLM fails.
    default_result = {
        "why_question": why_q,
        "root_cause": "",
        "fix_direction": "add type check",
        "confidence": 0.0,
        "llm_used": False,
    }
    # Guard 1: opt-in env var (default OFF — don't break existing flow).
    if os.environ.get("SCP_WHY_TYPE_INFERENCE", "0") != "1":
        logger.debug(
            "[V8.0-WHY] type_inference_why skipped — SCP_WHY_TYPE_INFERENCE!=1"
        )
        return default_result

    prompt = f"""Bạn là WHY engine của SCP. Phân tích type mismatch:

Variable: {var_name}
Expected type: {expected_type}
Actual type: {actual_type}
Context (code):
{context[:800]}

Hỏi: "Tại sao mismatch?" — root cause là gì? Có thể cả hai đúng (API contract changed)?
Fix direction: đổi caller (đổi kỳ vọng) hay function (đổi return type) hay add type check?

Output JSON:
{{
  "root_cause": "<1-2 câu giải thích>",
  "fix_direction": "change caller" | "change function" | "add type check",
  "confidence": 0.0
}}

Output ONLY the JSON object, no markdown fences, no explanation."""

    response = engine._v80_why_llm_call(prompt, max_tokens=400)
    if not response:
        return default_result

    parsed = engine._v80_why_extract_json(response)
    if not parsed:
        return default_result

    # Normalize fields with defensive defaults.
    root_cause = str(parsed.get("root_cause", "")).strip()
    fix_direction = str(parsed.get("fix_direction", "add type check")).strip().lower()
    if fix_direction not in ("change caller", "change function", "add type check"):
        fix_direction = "add type check"
    try:
        confidence = float(parsed.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError) as exc:
        # silent-by-design: unparseable LLM confidence falls back to the documented 0.0 default.
        logger.debug("why_v80_modes: confidence unparseable, using 0.0: %s", exc, exc_info=True)
        confidence = 0.0

    result = {
        "why_question": why_q,
        "root_cause": root_cause,
        "fix_direction": fix_direction,
        "confidence": confidence,
        "llm_used": True,
    }
    logger.info(
        f"[V8.0-WHY] type_inference_why — var={var_name!r}, "
        f"fix_direction={fix_direction}, confidence={confidence:.2f}"
    )
    return result


def data_flow_why(
    engine,
    source: str,
    sink: str,
    path: list[str],
    context: str,
) -> dict:
    """[V8.0-WHY] WHY mode 2: data flow analysis.

    WHY asks "Tại sao data đi từ A→B?" — trace data path to detect
    logic bugs. Called by AutoFix when suspicious data flow is detected
    (e.g., user input → SQL query without sanitize).

    WHY flow:
      1. "Tại sao user_input đi thẳng vào SQL?" → check if sanitize missing
      2. "Tại sao data không qua validation?" → check if validator skipped
      3. "Có thể inject malicious data không?" → security check

    Args:
        engine: WhyEngine instance (for _v80_why_llm_call, _v80_why_extract_json)
        source: where data originates (e.g. "request.body")
        sink: where data ends up (e.g. "SQL query")
        path: intermediate steps (list of strings)
        context: surrounding code

    Returns:
        {
            "why_question": "Tại sao data từ {source} đến {sink} mà không qua sanitize?",
            "sanitize_missing": bool,
            "risk_level": "high" | "medium" | "low",
            "fix_direction": str,
            "confidence": float (0.0-1.0),
            "llm_used": bool,
        }

    Env:
        SCP_WHY_DATA_FLOW=1 — OPT-IN (default OFF).
    """
    path_str = " → ".join(path) if path else "(no intermediate)"
    why_q = (
        f"Tại sao data từ {source} đến {sink} mà không qua sanitize? "
        f"Path: {path_str}"
    )
    default_result = {
        "why_question": why_q,
        "sanitize_missing": True,
        "risk_level": "high",
        "fix_direction": "add validation at source",
        "confidence": 0.0,
        "llm_used": False,
    }

    if os.environ.get("SCP_WHY_DATA_FLOW", "0") != "1":
        logger.debug(
            "[V8.0-WHY] data_flow_why skipped — SCP_WHY_DATA_FLOW!=1"
        )
        return default_result

    path_lines = "\n".join(f"- {step}" for step in (path or [])) or "(none)"
    prompt = f"""Bạn là WHY engine của SCP. Phân tích data flow:

Source: {source}
Sink: {sink}
Path (intermediate steps):
{path_lines}

Context (code):
{context[:800]}

Hỏi:
1. "Tại sao data đi thẳng vào sink?" — sanitize step có bị thiếu không?
2. "Tại sao data không qua validation?" — validator có bị skip không?
3. "Có thể inject malicious data không?" — security check.

Output JSON:
{{
  "sanitize_missing": true | false,
  "risk_level": "high" | "medium" | "low",
  "fix_direction": "<1 câu: add validation at step X>",
  "confidence": 0.0
}}

Output ONLY the JSON object, no markdown fences, no explanation."""

    response = engine._v80_why_llm_call(prompt, max_tokens=400)
    if not response:
        return default_result

    parsed = engine._v80_why_extract_json(response)
    if not parsed:
        return default_result

    try:
        sanitize_missing = bool(parsed.get("sanitize_missing", True))
    except (TypeError, ValueError) as exc:
        # silent-by-design: unparseable flag falls back to the documented True default.
        logger.debug("why_v80_modes: sanitize_missing unparseable, using True: %s", exc, exc_info=True)
        sanitize_missing = True
    risk_level = str(parsed.get("risk_level", "high")).strip().lower()
    if risk_level not in ("high", "medium", "low"):
        risk_level = "high"
    fix_direction = (
        str(parsed.get("fix_direction", "add validation at source")).strip()
        or "add validation at source"
    )
    try:
        confidence = float(parsed.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError) as exc:
        # silent-by-design: unparseable LLM confidence falls back to the documented 0.0 default.
        logger.debug("why_v80_modes: confidence unparseable, using 0.0: %s", exc, exc_info=True)
        confidence = 0.0

    result = {
        "why_question": why_q,
        "sanitize_missing": sanitize_missing,
        "risk_level": risk_level,
        "fix_direction": fix_direction,
        "confidence": confidence,
        "llm_used": True,
    }
    logger.info(
        f"[V8.0-WHY] data_flow_why — source={source!r}, sink={sink!r}, "
        f"risk={risk_level}, sanitize_missing={sanitize_missing}, conf={confidence:.2f}"
    )
    return result


def security_threat_why(
    engine,
    code_pattern: str,
    cwe_id: str,
    context: str,
) -> dict:
    """[V8.0-WHY] WHY mode 3: security threat analysis.

    WHY asks "Tại sao code này unsafe?" — security threat analysis.
    Called by AutoFix when SecurityScanner detects a CWE pattern
    (e.g. CWE-89 SQL injection, CWE-79 XSS).

    WHY flow:
      1. "Tại sao code này unsafe?" → identify CWE category + root cause
      2. "Tại sao attacker có thể exploit?" → attack vector analysis
      3. "Tại sao fix này an toàn?" → verify fix doesn't introduce new vuln

    Args:
        engine: WhyEngine instance (for _v80_why_llm_call, _v80_why_extract_json, _v80_normalize_cwe)
        code_pattern: the unsafe code snippet
        cwe_id: CWE identifier (e.g. "CWE-89", "89")
        context: surrounding code

    Returns:
        {
            "why_question": "Tại sao code này unsafe (CWE-{id})?",
            "attack_vector": str,
            "fix_verify": str,
            "risk_after_fix": "low" | "medium" | "high",
            "confidence": float (0.0-1.0),
            "llm_used": bool,
        }

    Env:
        SCP_WHY_SECURITY_THREAT=1 — OPT-IN (default OFF).
    """
    cwe_clean = engine._v80_normalize_cwe(cwe_id)
    why_q = f"Tại sao code này unsafe (CWE-{cwe_clean})?"
    default_result = {
        "why_question": why_q,
        "attack_vector": "",
        "fix_verify": "",
        "risk_after_fix": "high",
        "confidence": 0.0,
        "llm_used": False,
    }

    if os.environ.get("SCP_WHY_SECURITY_THREAT", "0") != "1":
        logger.debug(
            "[V8.0-WHY] security_threat_why skipped — SCP_WHY_SECURITY_THREAT!=1"
        )
        return default_result

    prompt = f"""Bạn là WHY engine của SCP — security threat analyst.

CWE: CWE-{cwe_clean}
Unsafe code:
{code_pattern[:800]}

Context (surrounding code):
{context[:600]}

Hỏi:
1. "Tại sao code này unsafe (CWE-{cwe_clean})?" — identify CWE category + root cause.
2. "Tại sao attacker có thể exploit?" — attack vector (1-2 câu).
3. "Tại sao fix này an toàn?" — verify fix không introduce new vuln.

Output JSON:
{{
  "attack_vector": "<1-2 câu: attacker làm gì để exploit>",
  "fix_verify": "<1 câu: fix có an toàn không? có introduce new vuln không?>",
  "risk_after_fix": "low" | "medium" | "high",
  "confidence": 0.0
}}

Output ONLY the JSON object, no markdown fences, no explanation."""

    response = engine._v80_why_llm_call(prompt, max_tokens=500)
    if not response:
        return default_result

    parsed = engine._v80_why_extract_json(response)
    if not parsed:
        return default_result

    attack_vector = str(parsed.get("attack_vector", "")).strip()
    fix_verify = str(parsed.get("fix_verify", "")).strip()
    risk_after_fix = str(parsed.get("risk_after_fix", "high")).strip().lower()
    if risk_after_fix not in ("low", "medium", "high"):
        risk_after_fix = "high"
    try:
        confidence = float(parsed.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError) as exc:
        # silent-by-design: unparseable LLM confidence falls back to the documented 0.0 default.
        logger.debug("why_v80_modes: confidence unparseable, using 0.0: %s", exc, exc_info=True)
        confidence = 0.0

    result = {
        "why_question": why_q,
        "attack_vector": attack_vector,
        "fix_verify": fix_verify,
        "risk_after_fix": risk_after_fix,
        "confidence": confidence,
        "llm_used": True,
    }
    logger.info(
        f"[V8.0-WHY] security_threat_why — CWE-{cwe_clean}, "
        f"risk_after_fix={risk_after_fix}, conf={confidence:.2f}"
    )
    return result
