# Auto-extracted from llm_fix.py
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

def _call_smart_llm(prompt: str, bug_type: str, max_tokens: int=4000) -> str | None:
    """Call LLM via gateway with task="autofix" (multi-model routing).

    [ROOT-FIX 44-A] Gateway routes task="autofix" → deepseek-r1:8b
    (user's strongest code-reasoning model). Cloud fallback to OpenRouter
    happens automatically if Ollama is down/unavailable.

    [OPT-17] bug_type is now used for STATS logging only (complexity tier),
    not for provider selection. deepseek-r1:8b handles all bug types well.

    Falls back to direct _call_openrouter() if gateway is unavailable
    (e.g. httpx not installed). This preserves backward compatibility —
    existing tests that mock _call_openrouter still work.
    """
    if bug_type in _SIMPLE_BUG_TYPES:  # noqa: F821  # [hygiene-keep] _SIMPLE_BUG_TYPES injected by llm_fix.py rebind/wire
        complexity_tier = 'simple'
    elif bug_type in _COMPLEX_BUG_TYPES:  # noqa: F821  # [hygiene-keep] _COMPLEX_BUG_TYPES injected by llm_fix.py rebind/wire
        complexity_tier = 'complex'
    elif bug_type in _MEDIUM_BUG_TYPES:  # noqa: F821  # [hygiene-keep] _MEDIUM_BUG_TYPES injected by llm_fix.py rebind/wire
        complexity_tier = 'medium'
    else:
        complexity_tier = 'unknown'
    logger.info(f'[llm_fix] [46] AutoFix routing: bug_type={bug_type} complexity={complexity_tier} → task=autofix → OpenRouter V4 flash (primary) + Ollama R1:8b (fallback)')
    system_prompt = 'You are a Python code fixer. Output ONLY a search-replace block in this exact format (no markdown fences, no explanation):\n\n<<<<<<< SEARCH\n<exact current code>\n=======\n<fixed code>\n>>>>>>> REPLACE\n\nRules: (1) SEARCH must match the file exactly including indentation; (2) REPLACE must be valid Python; (3) if you cannot fix, output NO_FIX_POSSIBLE. Example:\n<<<<<<< SEARCH\n    except Exception as e:\n        pass\n=======\n    except Exception as e:\n        logger.warning(e)\n>>>>>>> REPLACE'
    try:
        from scp.llm_gateway import chat_sync
        answer, provider_used = chat_sync(prompt, system_prompt=system_prompt, task='autofix')
        if answer:
            logger.debug(f'[llm_fix] [44-A] Gateway returned via provider={provider_used} (task=autofix, complexity={complexity_tier})')
            return answer
        logger.debug('[llm_fix] [44-A] Gateway returned empty answer, falling back to direct OpenRouter call')
    except Exception as e:
        logger.debug(f'[llm_fix] [44-A] Gateway call failed ({e}), falling back to direct OpenRouter call', exc_info=True)
    return _call_openrouter(prompt, max_tokens=max_tokens)  # noqa: F821  # [hygiene-keep] _call_openrouter injected by llm_fix.py rebind/wire
