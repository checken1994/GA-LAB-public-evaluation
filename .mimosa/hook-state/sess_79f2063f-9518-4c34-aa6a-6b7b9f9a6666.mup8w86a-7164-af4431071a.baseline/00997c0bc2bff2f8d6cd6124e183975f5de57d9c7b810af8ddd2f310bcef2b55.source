#!/usr/bin/env python3
"""SCP Guardrail — Install git hooks"""
import os
import stat
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = PROJECT_ROOT / ".git" / "hooks"

PRE_COMMIT_HOOK = """\
#!/bin/sh
# SCP T00 Meta-Audit Tripwire (L2)

echo "[SCP] Running T00 Meta-Audit..."
python tools/t00_meta_audit.py
if [ $? -ne 0 ]; then
    echo "COMMIT BLOCKED by T00 Test-Integrity Authority."
    exit 1
fi
exit 0
"""

def main() -> int:
    if not HOOKS_DIR.exists():
        print(f"Error: Git hooks dir not found at {HOOKS_DIR}")
        return 1

    hook_path = HOOKS_DIR / "pre-commit"
    if hook_path.exists():
        backup = hook_path.with_suffix(".backup")
        hook_path.rename(backup)

    hook_path.write_text(PRE_COMMIT_HOOK, encoding="utf-8")
    if os.name != "nt":
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

    print(f"Pre-commit hook installed. L2 Tripwire active.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
