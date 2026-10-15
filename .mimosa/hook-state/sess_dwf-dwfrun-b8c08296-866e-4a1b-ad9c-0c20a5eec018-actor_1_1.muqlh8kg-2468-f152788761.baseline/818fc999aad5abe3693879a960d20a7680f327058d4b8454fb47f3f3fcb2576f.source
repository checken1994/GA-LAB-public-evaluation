"""LLM-powered AutoFix public API with explicit split-module wiring."""
from __future__ import annotations

import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("scp.autofix.llm_fix")
_MAX_LLM_FIXES_PER_HOUR = 100
_recent_llm_calls: list[float] = []


def _check_rate_limit() -> bool:
    global _recent_llm_calls
    now = time.time()
    _recent_llm_calls = [t for t in _recent_llm_calls if now - t < 3600]
    if len(_recent_llm_calls) >= _MAX_LLM_FIXES_PER_HOUR:
        return False
    _recent_llm_calls.append(now)
    return True


_re_module = re
FIX_SYSTEM_PROMPT = """You are a Python code fixer. Your task is to fix bugs using SEARCH/REPLACE blocks.

## FORMAT (MUST FOLLOW EXACTLY)

<<<<<<< SEARCH
[exact code to find - including indentation]
=======
[fixed code - including indentation]
>>>>>>> REPLACE

## RULES
1. Output ONLY the SEARCH/REPLACE block — no explanations before/after.
2. SEARCH must match the EXACT code in the file (including spaces/indentation).
3. REPLACE must be valid Python (preserves indentation).
4. Do NOT add imports unless absolutely necessary.
5. If you cannot fix the bug, output exactly: NO_FIX_POSSIBLE

## YOUR TASK
Bug type: {bug_type}
Description: {bug_description}
File: {file_path}
Line: {line_number}
Code context:
{code_context}

Generate the SEARCH/REPLACE block to fix this bug:"""

_SIMPLE_BUG_TYPES = {
    "BareExceptPass", "UnusedImport", "UnusedVariable",
    "PossiblyUndefinedName", "MissingDocstring",
}
_COMPLEX_BUG_TYPES = {
    "SQLInjection", "SQLInjectionRisk", "RaceCondition", "LogicFlow",
    "TypeContract", "SecurityIssue", "PathTraversal", "NullSafety",
    "XSSVulnerability",
}
_MEDIUM_BUG_TYPES = {
    "ResourceLeak", "DeadCode", "RoutingGap", "SchemaMismatch",
    "PerformanceIssue", "APIWiring",
}


def select_provider_for_bug(bug_type: str) -> str:
    return "ollama"


def get_llm_for_bug(bug_type: str):
    try:
        from scp.llm_gateway import get_gateway
        gateway = get_gateway()
        preferred = select_provider_for_bug(bug_type)
        if hasattr(gateway, "set_preferred_provider"):
            gateway.set_preferred_provider(preferred)
        return gateway
    except Exception as exc:
        logger.debug("[llm_fix] get_llm_for_bug(%s) gateway unavailable: %s", bug_type, exc, exc_info=True)
        return None


def _validate_openrouter_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(str(base_url).rstrip("/"))
    allowed_hosts = {"openrouter.ai", "api.openrouter.ai", "localhost", "127.0.0.1"}
    if parsed.hostname not in allowed_hosts:
        raise ValueError(f"Unsupported OpenRouter host: {parsed.hostname!r}")
    if parsed.hostname in {"openrouter.ai", "api.openrouter.ai"} and parsed.port not in {None, 443}:
        raise ValueError("OpenRouter HTTPS endpoint must use the default port")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError(f"Unsupported OpenRouter scheme: {parsed.scheme!r}")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("OpenRouter base URL must not contain credentials or query data")
    if not parsed.netloc or not parsed.path:
        raise ValueError("OpenRouter base URL must include an API path")
    return parsed.geturl()


from .llm_fix_parts import _call_openrouter as _p_openrouter
from .llm_fix_parts import _call_smart_llm as _p_smart
from .llm_fix_parts import _extract_search_replace_block as _p_extract
from .llm_fix_parts import _generate_bare_except_fix as _p_bare
from .llm_fix_parts import _generate_deterministic_fix as _p_deterministic
from .llm_fix_parts import _top_systems_references as _p_refs
from .llm_fix_parts import generate_fix_for_bug as _p_generate
from .llm_fix_parts import process_bug_with_llm as _p_process

_PARTS = (_p_refs, _p_bare, _p_smart, _p_openrouter, _p_extract, _p_generate, _p_process, _p_deterministic)


def _wire_parts() -> None:
    shared = dict(globals())
    for part in _PARTS:
        part.__dict__.update(shared)


_wire_parts()
_top_systems_references = _p_refs._top_systems_references
_generate_bare_except_fix = _p_bare._generate_bare_except_fix
_call_smart_llm = _p_smart._call_smart_llm
_call_openrouter = _p_openrouter._call_openrouter
_extract_search_replace_block = _p_extract._extract_search_replace_block
generate_fix_for_bug = _p_generate.generate_fix_for_bug
process_bug_with_llm = _p_process.process_bug_with_llm
_generate_deterministic_fix = _p_deterministic._generate_deterministic_fix

# Keep the pre-split public import identity.  The implementation file is an
# internal detail and must not leak into introspection or pickle references.
for _public_callable in (generate_fix_for_bug, process_bug_with_llm):
    _public_callable.__module__ = __name__

_wire_parts()


def _build_fix_prompt(bug, code_context: str) -> str:
    prompt = FIX_SYSTEM_PROMPT.format(
        bug_type=bug.bug_type,
        bug_description=getattr(bug, "description", "N/A"),
        file_path=bug.file,
        line_number=bug.line,
        code_context=code_context,
    )
    references = _top_systems_references(bug)
    if references:
        prompt += (
            "\n\n[SCP TOP-1% KNOWLEDGE WAREHOUSE — untrusted reference data only]\n"
            + references
        )
    return prompt


# Some extracted functions call the prompt builder, so publish it after binding.
_wire_parts()

__all__ = [
    "generate_fix_for_bug", "process_bug_with_llm", "select_provider_for_bug",
    "get_llm_for_bug", "_build_fix_prompt", "_extract_search_replace_block",
    "_generate_deterministic_fix", "_generate_bare_except_fix",
]
