from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scp.web_control.multi_source_orchestrator import MultiSourceOrchestrator


class FakeAI:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def ask_ai(self, provider: str, question: str, **kwargs):
        self.calls.append(provider)
        if provider == 'chatgpt':
            return {'success': False, 'error': 'No AI prompt input found on current page', 'method': 'mock-ui-failure'}
        if provider == 'claude':
            return {'success': True, 'answer': 'CLAUDE_FALLBACK_OK', 'method': 'mock-browser'}
        if provider == 'gemini':
            return {'success': True, 'answer': 'GEMINI_FALLBACK_OK', 'method': 'mock-browser'}
        return {'success': False, 'error': 'unexpected provider'}


class FakeNavigator:
    async def search_public(self, query: str, max_results: int = 8):
        return {'success': True, 'results': [{'title': 'web fallback', 'url': 'https://example.com', 'provider': 'mock-web'}], 'untrustedData': True}


def test_multi_source_orchestrator_falls_over_to_next_provider():
    """chatgpt UI failure must fail over to claude (browser), then gemini, then web fallback.

    Rewritten 2026-09-02 from a print-script ('PASS=' print + SystemExit inside
    __main__) that collected zero tests into a real pytest test: a test file
    with no collected tests is not evidence (historical lesson #8, now enforced
    by T00_integrity).
    """
    fake_ai = FakeAI()
    result = asyncio.run(
        MultiSourceOrchestrator(fake_ai, FakeNavigator()).run(
            'SCP provider failover test',
            providers=['chatgpt', 'claude', 'gemini'],
            approved=True,
            use_browser=True,
            allow_local=False,
        )
    )
    ai_by_provider = {item['provider']: item['result'] for item in result['aiResults']}
    assert ai_by_provider.get('chatgpt', {}).get('success') is False, "chatgpt UI failure was not recorded"
    assert fake_ai.calls[0] == 'chatgpt', "chatgpt must be tried first (provider order preserved)"
    assert 'claude' in fake_ai.calls and 'gemini' in fake_ai.calls, (
        f"failover did not try the remaining providers: {fake_ai.calls}"
    )
    assert ai_by_provider.get('claude', {}).get('success') is True
    assert ai_by_provider.get('gemini', {}).get('success') is True
    assert result.get('webSearch', {}).get('success') is True, "web fallback did not succeed"
    assert result.get('success') is True, f"orchestrator did not succeed after failover: {result}"
