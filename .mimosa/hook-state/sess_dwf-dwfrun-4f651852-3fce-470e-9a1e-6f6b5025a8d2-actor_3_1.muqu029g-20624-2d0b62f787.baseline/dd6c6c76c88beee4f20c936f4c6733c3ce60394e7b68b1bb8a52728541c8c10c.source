#!/usr/bin/env python3
"""Silent background process launcher for Windows (Zero-Window Execution).

Used by Windows Scheduled Tasks to execute PowerShell / batch scripts with
ZERO console window flashes.

Why this works (DNA #26 Reality > Model):
- When Task Scheduler launches `pythonw.exe`, Windows kernel treats it as a GUI app
  (SUBSYSTEM:WINDOWS) and NEVER allocates a console host (`conhost.exe`).
- `run_silent.py` then invokes the child command passing `CREATE_NO_WINDOW` (0x08000000),
  guaranteeing that the child (e.g. `pwsh.exe`, `py.exe`) NEVER allocates a console window.
"""

import sys
import subprocess


def main():
    if len(sys.argv) < 2:
        sys.exit(0)

    cmd = sys.argv[1:]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0

    try:
        res = subprocess.run(
            cmd,
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            capture_output=True,
        )
        sys.exit(res.returncode)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
