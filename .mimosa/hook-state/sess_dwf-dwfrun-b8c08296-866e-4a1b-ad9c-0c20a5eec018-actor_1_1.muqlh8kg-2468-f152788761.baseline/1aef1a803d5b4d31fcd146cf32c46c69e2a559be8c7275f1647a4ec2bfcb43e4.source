from pathlib import Path

"""Reality test for Fix 4-d-016: 6 OPENROUTER_MODEL_* keys in .env.example.

Before fix: per-task model keys used by bridge but not documented.
After fix: all 6 in .env.example with documented defaults.

DNA principles:
  #16 (học nói phạm vi — env vars consumed by llm-bridge must be documented
       in .env.example; the template is the operator-facing contract)
  #22 (PASS ≠ TRUE — Phase 3-B fix 4-d-005 wired the env vars into
       TASK_MODEL_MAP but the .env.example template never listed them, so a
       new deploy copying .env.example → .env silently lost per-task routing)
  #25 (missing piece — undocumented env vars are a missing piece that
       breaks capability invisibly)
"""
import os

env_example_paths = [
    str(Path(__file__).resolve().parents[2]) + '/.env.example',
    str(Path(__file__).resolve().parents[2]) + '/scp/.env.example',
]
found = False
for p in env_example_paths:
    if not os.path.exists(p):
        continue
    with open(p) as f:
        src = f.read()
    required_keys = [
        "OPENROUTER_MODEL_AUTOFIX",
        "OPENROUTER_MODEL_CHAT",
        "OPENROUTER_MODEL_JUDGE",
        "OPENROUTER_MODEL_LEARNING",
        "OPENROUTER_MODEL_FAST_LEARNING",
        "OPENROUTER_MODEL_WHY",
    ]
    missing = [k for k in required_keys if k not in src]
    assert not missing, f"FAIL: missing keys in {p}: {missing}"
    print(f"PASS: all 6 OPENROUTER_MODEL_* keys in {os.path.basename(p)}")
    found = True
    break
if not found:
    assert False, "FAIL: no .env.example found"
print("\n✓ Reality test 4-d-016 PASSED")
