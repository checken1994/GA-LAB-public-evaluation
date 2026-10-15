# Auto-extracted from llm_fix.py
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from scp.security.provider_keys import ProviderCredentialError, load_openrouter_keys
from scp.security.url_safety import safe_urlopen

logger = logging.getLogger(__name__)


def _call_openrouter(prompt: str, max_tokens: int=4000) -> str | None:
    """Call OpenRouter only when a fresh exact-$0 proof authorizes the model.

    P0 Z2: authorization sits immediately before the urllib network driver.
    Unknown/stale/paid pricing or disallowed data class returns None with ZERO
    provider request. This direct legacy path cannot bypass the central wall.
    """
    try:
        _provider_keys = load_openrouter_keys()
    except ProviderCredentialError as exc:
        logger.warning('[llm_fix] Provider credential configuration rejected: %s', str(exc))
        _provider_keys = []
    api_key = _provider_keys[0] if _provider_keys else ''
    if not api_key:
        logger.warning('[llm_fix] No OpenRouter provider key configured; cannot generate fix')
        return None
    base_url = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    model = os.environ.get('OPENROUTER_MODEL_AUTOFIX', os.environ.get('OPENROUTER_MODEL', 'openrouter/free'))

    payload = {'model': model, 'messages': [{'role': 'system', 'content': 'You are a Python code fixer. Output ONLY a search-replace block in this exact format (no markdown fences, no explanation):\n\n<<<<<<< SEARCH\n<exact current code>\n=======\n<fixed code>\n>>>>>>> REPLACE\n\nRules: (1) SEARCH must match the file exactly including indentation; (2) REPLACE must be valid Python; (3) if you cannot fix, output NO_FIX_POSSIBLE.'}, {'role': 'user', 'content': prompt}], 'max_tokens': max_tokens, 'temperature': 0.1}
    try:
        validated_base_url = _validate_openrouter_base_url(base_url)  # noqa: F821  # [hygiene-keep] _validate_openrouter_base_url injected by llm_fix.py rebind/wire
        full_url = f'{validated_base_url}/chat/completions'
        req = urllib.request.Request(full_url, data=json.dumps(payload).encode('utf-8'), headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json', 'HTTP-Referer': 'https://scp-vietnam.local', 'X-Title': 'SCP AutoFix'}, method='POST')
        # [S6b security sweep] safe_urlopen (scheme + host + resolved-IP boundary
        # inside scp/security/url_safety.py) thay raw urlopen — allow_internal=True
        # giữ behavior override localhost/127.0.0.1 mà _validate_openrouter_base_url
        # đã cho phép; host công khai đi qua boundary check như thường.
        with safe_urlopen(req, timeout=30, allow_internal=True) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('choices', [{}])[0].get('message', {}).get('content', '')
    except urllib.error.HTTPError as e:
        logger.warning(f"[llm_fix] OpenRouter HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}")
        return None
    except Exception as e:
        logger.warning(f'[llm_fix] OpenRouter call failed: {e}', exc_info=True)
        return None
