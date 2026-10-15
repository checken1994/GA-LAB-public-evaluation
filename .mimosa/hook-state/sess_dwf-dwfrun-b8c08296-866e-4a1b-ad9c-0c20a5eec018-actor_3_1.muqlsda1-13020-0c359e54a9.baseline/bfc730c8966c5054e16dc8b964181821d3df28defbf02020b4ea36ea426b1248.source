from __future__ import annotations

import asyncio
import json

from scp.llm_gateway.client import OpenRouterProvider
from scp.security.dos_protection import DoSProtectionEngine


async def reproduce_openrouter_provider_429() -> dict:
    provider = OpenRouterProvider(task="default")
    provider._API_KEYS = ["k1"]
    provider._key_cycle = None
    provider._next_key = lambda: "k1"  # type: ignore[method-assign]
    paid = provider.model
    free = provider.free_fallback
    calls: list[str] = []

    async def fake_call(model: str, messages: list[dict], api_key: str):
        calls.append(model)
        if model == paid:
            return None, "HTTP 429 (quota/rate-limit)"
        if model == free:
            return "fallback answer", None
        return None, "HTTP 429 (quota/rate-limit)"

    provider._call_model = fake_call  # type: ignore[method-assign]
    answer, returned_provider = await provider.chat("test")
    return {"case": "openrouter_provider_429", "paid_model": paid, "free_model": free, "calls": calls, "answer": answer, "returned_provider": returned_provider, "fallback_succeeded": answer == "fallback answer" and returned_provider == f"openrouter:{free}"}


def reproduce_scp_api_429() -> dict:
    engine = DoSProtectionEngine()
    engine.MAX_REQUESTS_PER_MINUTE = 1
    first = engine.check_request("127.0.0.1")
    second = engine.check_request("127.0.0.1")
    return {"case": "scp_api_rate_limit_429", "first_allowed": first is None, "second_alert_type": second.alert_type if second else None, "second_status_code": second.status_code if second else None, "second_action": second.action_taken if second else None, "model_fallback_invoked": False, "reason": "DoSProtectionEngine rejects at HTTP service boundary before LLMGateway is called"}


async def main() -> None:
    print(json.dumps({"openrouter": await reproduce_openrouter_provider_429(), "scp_api": reproduce_scp_api_429()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
