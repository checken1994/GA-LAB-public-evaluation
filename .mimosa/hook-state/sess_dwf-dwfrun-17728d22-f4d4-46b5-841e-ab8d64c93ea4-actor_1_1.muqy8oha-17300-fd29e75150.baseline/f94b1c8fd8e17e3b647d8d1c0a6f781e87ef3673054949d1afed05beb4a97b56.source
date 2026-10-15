# Auto-extracted from llm_fix.py
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("scp.autofix.llm_fix")

def generate_fix_for_bug(bug) -> str | None:
    """Generate a code fix for a BugReport using LLM.

    Args:
        bug: BugReport with file, line, bug_type, description, suggested_fix

    Returns:
        Search-replace block string (ready for AutoFix._apply_fix), or None.

    [IMP-8 R7-Full] LLM fix caching: same-pattern bugs (same bug_type +
    same description + same surrounding code context) reuse a cached fix
    instead of re-querying the LLM. Cache is on-disk JSON with 24h TTL.
    Env SCP_LLM_FIX_CACHE_DISABLED=1 disables caching (always call LLM).
    """
    try:
        from scp.autofix.llm_fix_cache import compute_cache_key, get_llm_fix_cache, is_cache_enabled
        if is_cache_enabled():
            _cache = get_llm_fix_cache()
            _cache_key = compute_cache_key(bug)
            _cached = _cache.get(_cache_key)
            if _cached is not None:
                logger.info(f"[IMP-8] LLM fix cache HIT for {getattr(bug, 'bug_type', '?')} at {getattr(bug, 'file', '?')}:{getattr(bug, 'line', '?')} (key={_cache_key[:8]}) — skipping LLM call")
                return _cached
    except ImportError:
        logger.debug('[IMP-8] llm_fix_cache module unavailable — no caching')
    except Exception as _cache_err:
        logger.debug(f'[IMP-8] cache lookup failed (non-fatal): {_cache_err}', exc_info=True)
    if not _check_rate_limit():  # noqa: F821  # [hygiene-keep] _check_rate_limit injected by llm_fix.py rebind/wire
        logger.warning('[llm_fix] Rate limit reached — skipping LLM fix generation')
        return None
    filepath = Path(bug.file)
    if not filepath.exists():
        logger.warning(f'[llm_fix] File not found: {filepath}')
        return None
    try:
        source = filepath.read_text(encoding='utf-8', errors='replace')
        lines = source.splitlines()
        bug_line_idx = max(0, bug.line - 1)
        max_lines = int(os.environ.get('SCP_LLM_CONTEXT_LINES', '2000'))
        if len(lines) <= max_lines:
            context_lines = []
            for i, line in enumerate(lines):
                marker = ' >>>' if i == bug_line_idx else '    '
                context_lines.append(f'# line {i + 1}{marker}\n{line}')
            context = '\n'.join(context_lines)
        else:
            start = max(0, bug_line_idx - 250)
            end = min(len(lines), bug_line_idx + 250)
            context_lines = [f'# NOTE: Showing lines {start + 1}-{end} of {len(lines)} (file truncated)']
            for i in range(start, end):
                marker = ' >>>' if i == bug_line_idx else '    '
                context_lines.append(f'# line {i + 1}{marker}\n{lines[i]}')
            context = '\n'.join(context_lines)
    except Exception as e:
        logger.warning(f'[llm_fix] Could not read {filepath}: {e}', exc_info=True)
        return None
    prompt = _build_fix_prompt(bug, context)  # noqa: F821  # [hygiene-keep] _build_fix_prompt injected by llm_fix.py rebind/wire
    llm_response = _call_smart_llm(prompt, bug.bug_type, max_tokens=4000)  # noqa: F821  # [hygiene-keep] _call_smart_llm injected by llm_fix.py rebind/wire
    if not llm_response:
        return None
    fix_block = _extract_search_replace_block(llm_response)  # noqa: F821  # [hygiene-keep] _extract_search_replace_block injected by llm_fix.py rebind/wire
    if fix_block:
        logger.info(f'[llm_fix] Generated fix for {filepath.name}:{bug.line}')
        try:
            from scp.autofix.llm_fix_cache import compute_cache_key, get_llm_fix_cache, is_cache_enabled
            if is_cache_enabled():
                _cache = get_llm_fix_cache()
                _cache_key = compute_cache_key(bug)
                _cache.set(_cache_key, fix_block, bug=bug)
        except ImportError as cache_import_err:
            # silent-by-design: optional cache component missing — fix generation
            # proceeds uncached (documented disable path).
            logger.debug('[IMP-8] llm_fix_cache module unavailable — no caching: %s', cache_import_err, exc_info=True)
            pass
        except Exception as _cache_set_err:
            logger.debug(f'[IMP-8] cache set failed (non-fatal): {_cache_set_err}', exc_info=True)
        return fix_block
    else:
        logger.info('[llm_fix] No search-replace block found, returning raw LLM response')
        return llm_response
