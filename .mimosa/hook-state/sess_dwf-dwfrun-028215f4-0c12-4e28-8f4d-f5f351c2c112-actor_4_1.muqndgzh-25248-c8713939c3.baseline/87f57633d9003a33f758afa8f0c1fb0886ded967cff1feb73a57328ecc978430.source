from pathlib import Path

"""Reality test for Fix 4-a-014: llm_gateway client init race condition.

Before fix: `_client` was lazily initialized with a bare check-then-set:
    if self._client is None:
        self._client = httpx.AsyncClient(...)
Two concurrent chat()/_call_model() calls could both see _client is None,
both create an httpx.AsyncClient, and one would leak (never closed).

After fix: asyncio.Lock + double-checked init. Only the first concurrent
caller creates _client; subsequent callers see it set + skip the lock
entirely (no contention on the hot path).

DNA principles exercised:
  #2  (vòng lặp khép kín — reality test of the fix, not just the fix)
  #9  (no harm — leaked httpx clients accumulate connections + FDs)
  #22 (PASS ≠ TRUE — old code "worked" but silently leaked under concurrency)
  #26 (reality test — execute + cross-check the lock pattern)
"""
import ast
import asyncio
import os
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

FILE = str(Path(__file__).resolve().parents[2]) + '/scp/llm_gateway/client.py'


def test_reality_4_a_014_ast():
    """Verify AST structure and absence of dead provider layers."""
    assert os.path.isfile(FILE), f"FAIL: file missing: {FILE}"

    with open(FILE, encoding="utf-8") as f:
        src = f.read()

    tree = ast.parse(src)
    classes = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    assert "OllamaProvider" not in classes, "FAIL: OllamaProvider still exists in the gateway"
    assert "OpenRouterProvider" in classes, "FAIL: OpenRouterProvider class not found"


@pytest.mark.asyncio
async def test_openrouter_provider_client_lock_concurrency():
    """Behavioral execution test: 10 concurrent requests for client share exactly 1 instance."""
    from scp.llm_gateway.client import OpenRouterProvider

    provider = OpenRouterProvider(task="test_concurrency")
    assert hasattr(provider, "_client_lock")
    assert isinstance(provider._client_lock, asyncio.Lock)
    assert provider._client is None

    # Launch 10 concurrent calls to _get_client()
    clients = await asyncio.gather(*[provider._get_client() for _ in range(10)])

    assert len(clients) == 10
    first_client = clients[0]
    assert isinstance(first_client, httpx.AsyncClient)

    # Every concurrent caller must receive the exact same object reference
    for c in clients:
        assert c is first_client
        assert id(c) == id(first_client)

    # Cleanup client
    await first_client.aclose()


if __name__ == "__main__":
    test_reality_4_a_014_ast()
    asyncio.run(test_openrouter_provider_client_lock_concurrency())
    print("PASS: reality_4-a-014 behavioral test succeeded")
