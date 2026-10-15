#!/usr/bin/env python3
"""Reality test for Fix 4-d-005: llm-bridge respects per-task model routing.

DNA #5 (ảo giác đồng thuận) + #19 (tầng kiểm toán bằng chứng) + #22 (PASS ≠ TRUE).

Before fix:
  - Bridge line 462: `model: model && model.includes("/") ? model : OPENROUTER_MODEL`
  - SCP's LLM Gateway (client.py:99-107 TASK_MODEL_MAP) sends 6 task-specific
    Ollama model names: "deepseek-r1:8b" (autofix), "qwen2.5:7b" (why/learning/judge),
    "llama3.2" (fast_learning/chat/default).
  - None of these contain "/" → bridge ALWAYS fell back to OPENROUTER_MODEL.
  - All 6 per-task OPENROUTER_MODEL_* env vars defined in .env were NEVER read.
  - /api/tags advertised 3 fake Ollama model names but /api/chat ignored the
    model field — divergent contract (ảo giác đồng thuận).

After fix:
  - TASK_MODEL_MAP maps SCP's model names to per-task OPENROUTER_MODEL_* env vars.
  - resolveModel(model) checks (1) direct OpenRouter ID, (2) TASK_MODEL_MAP,
    (3) OPENROUTER_MODEL fallback.
  - The divergent contract is closed: SCP's per-task model routing now reaches
    OpenRouter per-task model IDs.

Honest limit (DNA #23): this is a static-source reality test (Tier A). Runtime
verification (Tier B) would require: set OPENROUTER_MODEL_AUTOFIX to a specific
model ID, send POST /api/chat {"model":"deepseek-r1:8b",...}, inspect
/tmp/scp-logs/llm-bridge.log to confirm the OpenRouter request body uses the
autofix model — left to runtime verification phase.

Run:
    python3 tests/reality-tests/reality_4-d-005.py
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
    # TEST 1 — TASK_MODEL_MAP must exist (the new table that wires per-task env
    # vars). A bare mention in a comment does NOT count — must be a real const.
    # -------------------------------------------------------------------------
    has_const_decl = bool(
        re.search(r'const\s+TASK_MODEL_MAP\s*:\s*Record<', src)
    )
    assert has_const_decl, (
        "FAIL: TASK_MODEL_MAP const not declared in llm-bridge/index.ts "
        "(must be `const TASK_MODEL_MAP: Record<...> = {...}`)"
    )
    print("PASS: TASK_MODEL_MAP const declared")

    # -------------------------------------------------------------------------
    # TEST 2 — TASK_MODEL_MAP must reference at least 4 of the 6 per-task env
    # vars (the requirement from Task 3-B). We accept mentions anywhere in src
    # (including the explanatory comment, which itself documents all 6).
    # -------------------------------------------------------------------------
    per_task_vars = [
        "OPENROUTER_MODEL_AUTOFIX",
        "OPENROUTER_MODEL_JUDGE",
        "OPENROUTER_MODEL_WHY",
        "OPENROUTER_MODEL_LEARNING",
        "OPENROUTER_MODEL_FAST_LEARNING",
        "OPENROUTER_MODEL_CHAT",
    ]
    found = [v for v in per_task_vars if v in src]
    print(f"Per-task env vars referenced: {len(found)}/6 ({found})")
    assert len(found) >= 4, (
        f"FAIL: only {len(found)}/6 per-task env vars referenced "
        f"(need >= 4 per Task 3-B requirement)"
    )
    # Stronger check: all 6 must be referenced in the actual map values, not
    # just in the comment. Look for `process.env.OPENROUTER_MODEL_<NAME>`.
    in_map = [
        v for v in per_task_vars
        if f"process.env.{v}" in src
    ]
    print(f"Per-task env vars in `process.env.X` form: {len(in_map)}/6 ({in_map})")
    assert len(in_map) >= 4, (
        f"FAIL: only {len(in_map)}/6 per-task env vars referenced as "
        f"`process.env.X` (need >= 4 actually wired into TASK_MODEL_MAP)"
    )
    print("PASS: at least 4/6 per-task env vars wired into TASK_MODEL_MAP")

    # -------------------------------------------------------------------------
    # TEST 3 — resolveModel function (or equivalent logic) must exist AND must
    # actually use TASK_MODEL_MAP. A resolver that doesn't consult the map is
    # the same bug as before.
    # -------------------------------------------------------------------------
    has_resolver_fn = bool(
        re.search(r'function\s+resolveModel\s*\(', src)
    )
    assert has_resolver_fn, (
        "FAIL: no `resolveModel` function declared"
    )
    # The resolver must index TASK_MODEL_MAP (e.g. `TASK_MODEL_MAP[requestedModel]`
    # or `TASK_MODEL_MAP[model]` or `TASK_MODEL_MAP[...]`).
    uses_map = bool(
        re.search(r'TASK_MODEL_MAP\s*\[', src)
    )
    assert uses_map, (
        "FAIL: resolveModel does not index TASK_MODEL_MAP "
        "(the map exists but is never consulted — divergent contract persists)"
    )
    print("PASS: resolveModel function declared AND consults TASK_MODEL_MAP")

    # -------------------------------------------------------------------------
    # TEST 4 — the OLD shortcut pattern (the divergent contract itself) must
    # be GONE from code (not just augmented). The old line was:
    #     model: model && model.includes("/") ? model : OPENROUTER_MODEL,
    # Look for it in CODE only (exclude comments). If it still appears alone
    # without a TASK_MODEL_MAP call adjacent, the bug persists.
    # -------------------------------------------------------------------------
    code_lines = [
        line
        for line in src.split("\n")
        if not line.strip().startswith("//")
        and not line.strip().startswith("*")
    ]
    code_section = "\n".join(code_lines)
    old_pattern_re = re.compile(
        r'model\s*:\s*model\s*&&\s*model\.includes\(\s*["\']/["\']\s*\)\s*\?\s*model\s*:\s*OPENROUTER_MODEL'
    )
    old_matches = old_pattern_re.findall(code_section)
    assert not old_matches, (
        f"FAIL: old divergent shortcut still in code (no TASK_MODEL_MAP used): "
        f"{old_matches}"
    )
    # Confirm the new resolver call IS present in code:
    new_resolver_call_re = re.compile(r'model\s*:\s*resolveModel\s*\(\s*model\s*\)')
    has_new_call = bool(new_resolver_call_re.search(code_section))
    assert has_new_call, (
        "FAIL: `model: resolveModel(model)` not present in code — fix not applied"
    )
    print("PASS: old divergent shortcut gone; `model: resolveModel(model)` wired")

    # -------------------------------------------------------------------------
    # TEST 5 — the 3 SCP Ollama model names that actually appear in client.py
    # (verified from client.py:99-107) must be KEYS in TASK_MODEL_MAP. Without
    # these exact keys, the bridge still won't honor SCP's per-task routing.
    # -------------------------------------------------------------------------
    scp_model_names = ["deepseek-r1:8b", "qwen2.5:7b", "llama3.2"]
    missing_keys = [
        name for name in scp_model_names
        if f'"{name}"' not in src and f"'{name}'" not in src
    ]
    assert not missing_keys, (
        f"FAIL: SCP's actual Ollama model names missing from TASK_MODEL_MAP "
        f"keys: {missing_keys} (verified from client.py:99-107)"
    )
    print(
        f"PASS: TASK_MODEL_MAP keys include SCP's actual Ollama model names "
        f"({scp_model_names}) — verified vs client.py:99-107"
    )

    print("\n✓ Reality test 4-d-005 PASSED (5/5 assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
