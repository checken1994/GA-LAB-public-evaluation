"""Provider-independent orchestration for SCP.

The orchestrator treats browser AIs, local models, and public web retrieval as
separate evidence channels. A failed or unavailable AI never blocks web search.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from .ai_orchestrator import AIOrchestrator
from .web_navigator import WebNavigator

logger = logging.getLogger(__name__)



class MultiSourceOrchestrator:
    DEFAULT_PROVIDERS = ["local_llm", "chatgpt", "claude", "gemini"]
    BROWSER_PROVIDERS = {"chatgpt", "claude", "gemini"}

    def __init__(self, ai: AIOrchestrator | None = None, navigator: WebNavigator | None = None) -> None:
        self.navigator = navigator or WebNavigator()
        self.ai = ai or AIOrchestrator(self.navigator.browser)

    async def run(
        self,
        question: str,
        providers: list[str] | None = None,
        approved: bool = False,
        use_browser: bool = False,
        allow_local: bool = True,
        max_results: int = 8,
    ) -> dict[str, Any]:
        question = question.strip()
        if not question:
            return {"success": False, "error": "Question is empty", "aiResults": [], "webSearch": None}

        selected = providers or list(self.DEFAULT_PROVIDERS)
        ai_results: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []
        for provider in selected:
            provider = provider.strip().lower()
            if provider == "local_llm" and not allow_local:
                skipped.append({"provider": provider, "reason": "local model disabled"})
                continue
            if provider in self.BROWSER_PROVIDERS and not use_browser:
                skipped.append({"provider": provider, "reason": "browser provider disabled"})
                continue
            if provider in self.BROWSER_PROVIDERS and not approved:
                skipped.append({"provider": provider, "reason": "browser approval required"})
                continue
            try:
                result = await self.ai.ask_ai(
                    provider,
                    question,
                    approved=approved,
                    use_browser=provider in self.BROWSER_PROVIDERS,
                    allow_api_fallback=False,
                )
                ai_results.append({"provider": provider, "result": result})
            except Exception as exc:
                logger.warning('MultiSourceOrchestrator.run: Exception not handled: %s', exc, exc_info=True)
                ai_results.append({"provider": provider, "result": {"success": False, "error": str(exc)}})

        web_search = await self.navigator.search_public(question, max_results=max_results)
        successful_ai = [item for item in ai_results if item.get("result", {}).get("success") or item.get("result", {}).get("answer")]
        return {
            "success": bool(successful_ai or web_search.get("success")),
            "question": question,
            "aiResults": ai_results,
            "skippedProviders": skipped,
            "webSearch": web_search,
            "successfulAIProviders": [item["provider"] for item in successful_ai],
            "truthPolicy": "No single AI answer is treated as truth; compare sources and inspect citations.",
            "fallbackOrder": ["selected AI providers", "public web search", "manual review"],
            "method": "multi-source-orchestration",
            "timestamp": time.time(),
        }
