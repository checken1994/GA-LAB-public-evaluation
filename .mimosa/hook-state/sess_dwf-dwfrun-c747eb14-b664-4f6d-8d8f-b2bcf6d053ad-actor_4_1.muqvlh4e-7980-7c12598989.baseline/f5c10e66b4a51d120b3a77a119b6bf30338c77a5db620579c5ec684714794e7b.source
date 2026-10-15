#!/usr/bin/env python3
"""Reality test for Fix 4-d-022: max_tokens read from request (not hardcoded 2000).

DNA #16 (Học nói phạm vi — underruns output silently) + #22 (PASS ≠ TRUE —
"2000 is enough" assumed not verified).

Before fix:
  - Both OpenRouter calls (`callZaiChat` and `callProviderDirect`) hardcoded
    `max_tokens: 2000` in the request body.
  - SCP's autofix LLM prompts (full file content + AST + bug description)
    frequently exceed 2000 output tokens → truncated JSON → SCP's LLM-fix
    parser sees incomplete code → "no fix found" or worse, applies a
    broken fix.

After fix (accepted alternatives per spec):
  - EITHER: read max_tokens from the request body (SCP sends it).
  - OR: default to >= 4000 if absent (or remove the cap entirely).
  This implementation does BOTH: reads body.max_tokens, falls back to
  LLM_MAX_TOKENS_DEFAULT (4000, was 2000).

Tier-A (static-source) reality test.
"""
import re
import sys
from pathlib import Path

SOURCE_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/mini-services/llm-bridge/core.ts'
)


def main() -> int:
    assert SOURCE_PATH.exists(), (
        f"FAIL: llm-bridge/index.ts not found at {SOURCE_PATH}"
    )
    src = SOURCE_PATH.read_text(encoding="utf-8")
    print(f"PASS [1/4]: file exists ({SOURCE_PATH.name})")

    # -------------------------------------------------------------------------
    # TEST 2 — the literal `max_tokens: 2000` MUST be gone from code (in
    # the active fetch bodies). We check code only (exclude comments, which
    # may mention the historical value).
    # -------------------------------------------------------------------------
    code_lines = [
        line
        for line in src.split("\n")
        if not line.strip().startswith("//")
        and not line.strip().startswith("*")
    ]
    code_section = "\n".join(code_lines)
    has_hardcoded_2000 = bool(
        re.search(r"max_tokens\s*:\s*2000\b", code_section)
    )
    assert not has_hardcoded_2000, (
        "FAIL: `max_tokens: 2000` literal still in code — long responses "
        "still get truncated → broken JSON → UNKNOWN verdicts"
    )
    print("PASS [2/4]: no hardcoded `max_tokens: 2000` literal in code")

    # -------------------------------------------------------------------------
    # TEST 3 — must EITHER:
    #   (a) read max_tokens from the request body (e.g. body?.max_tokens
    #       or body?.maxTokens), OR
    #   (b) use a default >= 4000 (e.g. LLM_MAX_TOKENS_DEFAULT = 4000).
    # -------------------------------------------------------------------------
    reads_from_body = bool(
        re.search(r"body\s*\?\.\s*max_tokens", src)
    ) or bool(
        re.search(r"body\s*\?\.\s*maxTokens", src)
    )
    # Look for a numeric default >= 4000 in code.
    default_match = re.search(
        r"(?:LLM_MAX_TOKENS_DEFAULT|MAX_TOKENS)\s*=\s*Number\s*\(\s*process\.env\.\w+\s*\?\?\s*(\d[\d_]*)",
        src,
    )
    default_ge_4000 = False
    if default_match:
        default_val = int(default_match.group(1).replace("_", ""))
        default_ge_4000 = default_val >= 4000
    else:
        # Fallback: look for any max_tokens default assignment >= 4000.
        default_match2 = re.search(
            r"max_tokens\s*\?\?\s*(\d[\d_]*)",
            src,
        )
        if default_match2:
            default_val = int(default_match2.group(1).replace("_", ""))
            default_ge_4000 = default_val >= 4000
    assert reads_from_body or default_ge_4000, (
        "FAIL: max_tokens is neither read from request body nor default >= 4000 — "
        f"reads_from_body={reads_from_body}, default_ge_4000={default_ge_4000}"
    )
    methods = []
    if reads_from_body: methods.append("reads body.max_tokens")
    if default_ge_4000: methods.append(f"default >= 4000 ({default_match.group(1) if default_match else '?'})")
    print(f"PASS [3/4]: max_tokens is {' + '.join(methods)}")

    # -------------------------------------------------------------------------
    # TEST 4 — the callZaiChat function signature must accept a max_tokens
    # parameter (so handleChat can pass body.max_tokens through to OpenRouter).
    # -------------------------------------------------------------------------
    has_maxtokens_param = bool(
        re.search(
            r"function\s+callZaiChat\s*\([^)]*maxTokens\s*[\?\:]",
            src,
        )
    )
    assert has_maxtokens_param, (
        "FAIL: callZaiChat does not accept a maxTokens parameter — even if "
        "handleChat reads body.max_tokens, it can't pass it through to the "
        "fetch body (still uses the hardcoded default)"
    )
    print("PASS [4/4]: callZaiChat accepts maxTokens parameter (plumbs request → OpenRouter)")

    print("\n✓ Reality test 4-d-022 PASSED (4/4 assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
