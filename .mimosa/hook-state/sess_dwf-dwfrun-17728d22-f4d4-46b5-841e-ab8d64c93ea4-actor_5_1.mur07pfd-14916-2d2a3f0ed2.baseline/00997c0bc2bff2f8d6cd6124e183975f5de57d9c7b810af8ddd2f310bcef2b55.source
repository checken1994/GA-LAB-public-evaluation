#!/usr/bin/env python3
"""SCP Guardrail — Install git hooks.

[M-12 fix 2026-10-01] The installer used to BLINDLY overwrite any existing
pre-commit hook (rename to pre-commit.backup + write the SCP hook). That
destroyed foreign hook content installed by other tooling. Fail-closed
behavior now:

- No existing pre-commit hook      -> install the SCP T00 tripwire hook.
- Existing hook IS the SCP hook    -> idempotent reinstall (same content,
  no backup churn, exit 0).
- Existing foreign hook            -> DO NOT touch it. Fail loudly (exit 1)
  with merge instructions so a human composes the chain.
"""
import os
import stat
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = PROJECT_ROOT / ".git" / "hooks"

SCP_HOOK_MARKER = "SCP T00 Meta-Audit Tripwire (L2)"

PRE_COMMIT_HOOK = f"""\
#!/bin/sh
# {SCP_HOOK_MARKER}

# [harness note 2026-10-01] git exports GIT_DIR/GIT_INDEX_FILE/GIT_WORK_TREE to
# hook processes; T00's run_git_cmd() scrubs those before any child git call
# (HARNESS-FIX for pre-commit worktree ENOENT), so this hook stays a plain
# pass-through — no env surgery here that could shadow T00's own scrubbing.

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
        try:
            existing = hook_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"Error: cannot read existing pre-commit hook ({exc}); refusing to overwrite.")
            return 1
        if SCP_HOOK_MARKER in existing:
            # Idempotent reinstall of our own hook — content identical.
            hook_path.write_text(PRE_COMMIT_HOOK, encoding="utf-8")
            print("Pre-commit hook already the SCP tripwire; reinstalled idempotently. L2 Tripwire active.")
            return 0
        print(
            "Error: an existing NON-SCP pre-commit hook was found at "
            f"{hook_path}. It was NOT overwritten (fail-closed, audit M-12).\n"
            "To compose a chain yourself, edit .git/hooks/pre-commit so it calls both, e.g.:\n"
            "\n"
            "    #!/bin/sh\n"
            "    python tools/t00_meta_audit.py || exit 1\n"
            "    exec /path/to/your/existing-hook\n"
            "\n"
            "Then re-run this installer; it will recognize only the SCP marker hook."
        )
        return 1

    hook_path.write_text(PRE_COMMIT_HOOK, encoding="utf-8")
    if os.name != "nt":
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

    print("Pre-commit hook installed. L2 Tripwire active.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
