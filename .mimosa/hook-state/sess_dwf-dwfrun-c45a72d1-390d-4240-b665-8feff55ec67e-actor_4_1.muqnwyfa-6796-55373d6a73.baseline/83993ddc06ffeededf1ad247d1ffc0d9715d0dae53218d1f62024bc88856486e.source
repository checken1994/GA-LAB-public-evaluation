"""SCP V3.1 AI Orchestrator.

Cloud AI in the user's PC is accessed through an explicitly connected browser
session first. API/local fallbacks are explicit and never silently replace a
logged-in browser workflow.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from .browser_session import BrowserSession

logger = logging.getLogger(__name__)


class AIOrchestrator:
    AI_URLS = {
        "chatgpt": "https://chatgpt.com/",
        "claude": "https://claude.ai/",
        "gemini": "https://gemini.google.com/",
    }
    AI_HOSTS = {
        "chatgpt": ("chatgpt.com", "chat.openai.com"),
        "claude": ("claude.ai",),
        "gemini": ("gemini.google.com",),
    }

    def __init__(self, browser: BrowserSession | None = None) -> None:
        self.browser = browser or BrowserSession()

    async def status(self) -> dict[str, Any]:
        return {
            "orchestrator": "online",
            "browserFirst": True,
            "apiFallback": "explicit-only",
            "browser": await self.browser.status(),
        }

    async def _ask_via_browser(self, ai_name: str, question: str) -> dict[str, Any]:
        url = self.AI_URLS.get(ai_name)
        if not url:
            return {"success": False, "error": f"Unsupported browser AI: {ai_name}"}
        targets = await self.browser.targets()
        pages = [item for item in targets if item.get("type") == "page"]
        hosts = self.AI_HOSTS.get(ai_name, ())
        page = next((item for item in pages if any(host in str(item.get("url", "")).lower() for host in hosts)), None)
        if not page:
            return {"success": False, "error": f"Open a logged-in {ai_name} tab first; no matching AI hostname was found", "ai": ai_name, "availablePages": [{"title": item.get("title", ""), "url": item.get("url", "")} for item in pages]}
        prompt = json.dumps(question, ensure_ascii=False)
        await self.browser.type_and_submit(question, page)
        await __import__('asyncio').sleep(8)
        verification = f"""
        (() => {{
          const prompt = {prompt};
          const body = document.body?.innerText || '';
          const observed = body.includes(prompt);
          return {{ success: observed, sentVia: 'cdp-input-enter', title: document.title, text: body.slice(-20000) || '', error: observed ? undefined : 'Prompt was not observed in ChatGPT DOM after submit' }};
        }})()
        """
        result = await self.browser.evaluate(verification, page)
        return {"ai": ai_name, "question": question, "lineage": ai_name, "method": "logged-in-browser", "timestamp": time.time(), **(result or {})}

    async def ask_ai(self, ai_name: str, question: str, approved: bool = False, use_browser: bool = True, allow_api_fallback: bool = False) -> dict[str, Any]:
        if not question.strip():
            return {"success": False, "error": "Question is empty"}
        if use_browser:
            if not approved:
                return {"success": False, "error": "Asking a logged-in AI requires explicit approval", "ai": ai_name}
            result = await self._ask_via_browser(ai_name, question)
            if result.get("success") or not allow_api_fallback:
                return result
        return {"success": False, "error": "Browser session unavailable; explicit API fallback was not enabled", "ai": ai_name}

    async def cross_verify(self, question: str, scp_answer: str, ais: list[str] | None = None, approved: bool = False) -> dict[str, Any]:
        selected = ais or ["chatgpt", "claude"]
        results: dict[str, Any] = {}
        for ai_name in selected:
            try:
                results[ai_name] = await self.ask_ai(ai_name, question, approved=approved, use_browser=ai_name != "local_llm")
            except Exception as exc:
                logger.debug("ai_orchestrator: cross_verify ask_ai failed for %s: %s", ai_name, exc, exc_info=True)
                results[ai_name] = {"success": False, "error": str(exc)}
        successful = [value for value in results.values() if value.get("success") or value.get("answer")]
        return {
            "scpAnswer": scp_answer,
            "results": results,
            "successfulSources": len(successful),
            "consensus": None,
            "note": "Consensus is not treated as truth; Verifier must compare evidence and sources.",
            "timestamp": time.time(),
        }
