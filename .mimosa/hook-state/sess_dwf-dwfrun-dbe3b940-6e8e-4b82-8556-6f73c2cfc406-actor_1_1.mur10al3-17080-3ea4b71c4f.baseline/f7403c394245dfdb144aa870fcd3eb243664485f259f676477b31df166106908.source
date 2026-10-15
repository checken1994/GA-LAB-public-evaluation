#!/usr/bin/env python3
"""Reality test for Fix 4-d-004: llm-bridge must NOT self-call.

DNA #2 (vòng lặp khép kín) + #22 (PASS≠TRUE) + #26 (reality test).

Before fix: R19-FIX-2 added an "ollama" fallback whose default URL was
  http://127.0.0.1:11434  — which IS the bridge's own port. When OpenRouter
  AND Groq both failed, callProviderDirect() POSTed to /api/chat on the
  bridge itself → callZaiChat → OpenRouter failed again → fell through to
  the ollama entry → itself → infinite recursion → stack overflow / OOM.

After fix (Task 2-C):
  1. The "ollama" entry is REMOVED from LLM_PROVIDERS (default no longer
     self-targets). Operators who genuinely run a separate Ollama on a
     different port can re-add it via env.
  2. A recursion guard is added at the top of handleChat(): if the incoming
     request carries `X-LLM-Bridge-Internal: 1`, the bridge returns 503
     immediately. This catches ANY future self-call loop even if someone
     re-adds a self-targeting provider URL.

This script does STATIC analysis of the TypeScript source (no service
required to be running). DNA #23: honest limit — runtime verification of
the 503 short-circuit requires the bridge to be running; that is left as
a Tier B check (see tests/reality-check.sh). This Tier A check proves the
fix is present in source and the self-targeting default is gone.

Run:
    python3 tests/reality-tests/reality_4-d-004.py
"""

import re
import sys
from pathlib import Path

SOURCE_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/mini-services/llm-bridge/core.ts'
)


def main() -> int:
    src = SOURCE_PATH.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # TEST 1 — the default Ollama URL must NOT be 127.0.0.1:11434 (the
    # bridge's own port). Look for the old pattern:
    #     url: process.env.OLLAMA_BASE_URL || "http://127.0.0.1:11434"
    # in CODE only (exclude comment lines so the fix-explaining comment we
    # added doesn't false-positive — DNA #19 calibration learned in Phase 1).
    # -------------------------------------------------------------------------
    self_target_pattern = re.compile(
        r'url:\s*process\.env\.OLLAMA_BASE_URL\s*\|\|\s*'
        r'["\']http://127\.0\.0\.1:11434["\']'
    )
    code_lines = [
        line
        for line in src.split("\n")
        if not line.strip().startswith("//")
        and not line.strip().startswith("*")
    ]
    code_section = "\n".join(code_lines)
    matches = self_target_pattern.findall(code_section)
    assert not matches, (
        f"FAIL: self-targeting Ollama URL still present in code: {matches}"
    )
    print("PASS: no self-targeting http://127.0.0.1:11434 default URL in code")

    # -------------------------------------------------------------------------
    # TEST 2 — recursion guard header check must be present in CODE.
    # We look for the actual runtime check (header read + 503 response).
    # We allow the comment to also satisfy this (defense in depth) but prefer
    # the runtime check — verify the runtime check is present.
    # -------------------------------------------------------------------------
    has_guard_header = (
        'req.headers.get("X-LLM-Bridge-Internal")' in code_section
        or "req.headers.get('X-LLM-Bridge-Internal')" in code_section
    )
    assert has_guard_header, (
        "FAIL: no X-LLM-Bridge-Internal header check in code (recursion guard missing)"
    )
    has_503 = "status: 503" in code_section or "status:503" in code_section
    assert has_503, (
        "FAIL: recursion guard present but no 503 response (guard is incomplete)"
    )
    has_self_call_msg = "self-call blocked" in code_section
    assert has_self_call_msg, (
        "FAIL: recursion guard present but no 'self-call blocked' message "
        "(operator would not be able to identify the failure mode — DNA #19)"
    )
    print("PASS: recursion guard (X-LLM-Bridge-Internal → 503) present in code")

    # -------------------------------------------------------------------------
    # TEST 3 — the fix explanation should explain WHY (DNA #22 — claim vs
    # reality: a fix without a "why" comment is a claim with no audit trail).
    # We accept the fix-ID tag OR a self-call/recursion mention in the comments.
    # -------------------------------------------------------------------------
    has_explanation = (
        "Fix 4-d-004" in src
        or "self-call" in src.lower()
        or "recursion" in src.lower()
    )
    assert has_explanation, (
        "FAIL: no fix explanation present in source comments (DNA #22 violation)"
    )
    print("PASS: fix explanation present in source comments")

    # -------------------------------------------------------------------------
    # TEST 4 (bonus) — the ollama entry must NOT be in LLM_PROVIDERS as a
    # live entry. We look for the literal `{ name: "ollama"` or `name:"ollama"`
    # in code, which would mean someone re-added it. Comment mentions are OK.
    # -------------------------------------------------------------------------
    ollama_entry_pattern = re.compile(
        r'name\s*:\s*["\']ollama["\']'
    )
    ollama_in_code = ollama_entry_pattern.findall(code_section)
    assert not ollama_in_code, (
        f"FAIL: 'ollama' provider entry still present in LLM_PROVIDERS: "
        f"{ollama_in_code}"
    )
    print("PASS: 'ollama' provider entry removed from LLM_PROVIDERS")

    print("\n✓ Reality test 4-d-004 PASSED (4/4 assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
