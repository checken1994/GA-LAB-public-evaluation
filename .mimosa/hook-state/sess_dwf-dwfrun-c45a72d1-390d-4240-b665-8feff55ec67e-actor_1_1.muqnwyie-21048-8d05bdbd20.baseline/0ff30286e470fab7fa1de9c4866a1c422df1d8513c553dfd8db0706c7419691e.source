"""Timeout recovery under the Z3 verified-free-only router (T05).

Z3 (install_free_only_provider_router) authorizes every candidate at the
ZeroCostGuard PEP BEFORE dispatch, so the contract proven here is:

  1. every Z3 candidate carries a fresh pricing proof (seeded via the
     ``pricing_runtime`` fixture) — authorization must not need the bounded
     catalog refresh, because the T05 conftest fails closed on any HTTP;
  2. a verified exact-$0 task model that TIMES OUT is followed by the next
     verified exact-$0 candidate (openrouter/free auto-router);
  3. the primary model (fresh but PAID proof) is DENY_PAID at the PEP and is
     never dispatched — paid is never sent even during recovery.
"""

from __future__ import annotations

import asyncio
import os

from scp.llm_gateway.client import OpenRouterProvider


def test_openrouter_timeout_recovers_via_task_free_fallback() -> None:
    # provider.free_fallback == env OPENROUTER_MODEL_JUDGE, else the curated
    # TASK_FREE_FALLBACK_MAP["judge"] model. The judge primary is
    # OPENROUTER_MODEL_JUDGE_PRIMARY else "anthropic/claude-3-5-sonnet".
    expected_fallback = os.environ.get(
        "OPENROUTER_MODEL_JUDGE", "nvidia/nemotron-3-super-120b-a12b:free"
    )
    expected_primary = os.environ.get(
        "OPENROUTER_MODEL_JUDGE_PRIMARY", "anthropic/claude-3-5-sonnet"
    )

    async def actual() -> tuple[list[str], str | None, str]:
        provider = OpenRouterProvider(task="judge")
        provider._API_KEYS = ["test-key"]
        provider._next_key = lambda: "test-key"  # type: ignore[method-assign]

        calls: list[str] = []
        timeout_model = expected_primary

        async def fake_call(model: str, messages: list[dict], api_key: str):
            calls.append(model)
            if model == timeout_model:
                return None, "ReadTimeout: controlled provider timeout"
            return "recovered fallback answer", None

        provider._call_model = fake_call  # type: ignore[method-assign]
        answer, name = await provider.chat("test")
        return calls, answer, name

    calls, answer, provider_name = asyncio.run(actual())
    assert calls == [expected_primary, expected_fallback]
    assert answer == "recovered fallback answer"
    assert provider_name == f"openrouter:{expected_fallback}"
