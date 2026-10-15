"""Cross-provider semantic verification.

A semantic consensus is only accepted when two distinct provider families
produce parseable verdicts for the same prompt. Task labels or model names are
not treated as evidence of independence.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("scp.runtime.multi_llm_crosscheck")


def _candidate_providers(gateway: Any) -> list[Any]:
    """Return enabled judge candidates without inventing provider diversity."""
    public = getattr(gateway, "provider_candidates", None)
    if callable(public):
        candidates = list(public("judge") or [])
    else:
        internal = getattr(gateway, "_provider_chain", None)
        candidates = list(internal("judge") or []) if callable(internal) else []

    enabled: list[Any] = []
    for provider in candidates:
        try:
            if bool(getattr(provider, "enabled", False)):
                enabled.append(provider)
        except Exception as exc:
            logger.warning(
                "[MULTI-LLM] provider readiness failed (%s): %s",
                getattr(provider, "PROVIDER_NAME", "unknown"),
                type(exc).__name__,
            exc_info=True)
    return enabled


def _missing_opinion() -> dict[str, Any]:
    """Explicit unresolved opinion; never expose a shape that implies success."""
    return {"family": "", "provider": "none", "verdict": None}


async def cross_verify(
    question: str,
    ai_answer: str,
    context: str = "",
    verdict_tier1: bool = True,
    *,
    gateway: Any | None = None,
) -> dict[str, Any]:
    """Verify one answer using two genuinely distinct provider families.

    Returns ``final=PASS|FAIL`` only when two different provider families
    return parseable and equal verdicts. Missing diversity, provider failure,
    ambiguous output, or disagreement all fail closed with ``final=None``.

    ``gateway`` is injectable so the independence rule can be tested without
    external network access; production callers continue to use get_gateway().
    ``verdict_tier1`` is retained for backward compatibility.
    """
    del verdict_tier1

    from scp.runtime.judge_llm import _parse_verdict

    if gateway is None:
        from scp.llm_gateway import get_gateway

        gateway = get_gateway()

    prompt = (
        f"System Identity: The AI assistant being evaluated is named SCP (Self-Correcting Process), an intelligent AI assistant.\n"
        f"Question: {question}\nContext: {context}\nAI Answer: {ai_answer}\n"
        "Evaluate if the AI Answer correctly answers the Question based ONLY on "
        "the Context (if provided), the System Identity, or general knowledge. Output only PASS or FAIL."
    )
    system = (
        "You are a factual judge. You MUST output exactly the word PASS or FAIL "
        "and nothing else."
    )

    seen_families: set[str] = set()
    attempts: list[dict[str, Any]] = []
    valid: list[dict[str, Any]] = []

    for provider in _candidate_providers(gateway):
        family = str(getattr(provider, "PROVIDER_NAME", "")).strip().lower()
        if not family or family in seen_families:
            continue
        # Mark before the request: a second instance of the same family is not
        # an independent opinion, even when the first instance errors.
        seen_families.add(family)

        try:
            content, provider_label = await provider.chat(
                prompt,
                system_prompt=system,
            )
            verdict = _parse_verdict(content)
            attempt = {
                "family": family,
                "provider": provider_label,
                "verdict": verdict,
            }
        except Exception as exc:
            # per-attempt error is logged below, recorded in the attempt record ('provider': error:<Exc>) and returned to the caller
            logger.debug("LLM crosscheck attempt failed for family '%s': %s", family, exc, exc_info=True)
            attempt = {
                "family": family,
                "provider": f"error:{type(exc).__name__}",
                "verdict": None,
            }

        attempts.append(attempt)
        if attempt["verdict"] in {"PASS", "FAIL"}:
            valid.append(attempt)
            if len(valid) == 2:
                break

    primary = valid[0] if valid else _missing_opinion()
    secondary = valid[1] if len(valid) > 1 else _missing_opinion()

    if len(valid) < 2:
        consensus = "missing_distinct_providers"
        final = None
    elif primary["verdict"] == secondary["verdict"]:
        consensus = "agree"
        final = primary["verdict"]
    else:
        consensus = "disagree"
        final = None

    logger.info(
        "[MULTI-LLM] primary(%s)=%s secondary(%s)=%s consensus=%s final=%s",
        primary["provider"],
        primary["verdict"],
        secondary["provider"],
        secondary["verdict"],
        consensus,
        final,
    )
    return {
        "consensus": consensus,
        "primary": primary,
        "secondary": secondary,
        "final": final,
        "attempts": attempts,
        "distinct_families_attempted": [item["family"] for item in attempts],
    }
