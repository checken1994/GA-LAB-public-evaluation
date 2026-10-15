#!/usr/bin/env python3
"""SCP 24/7 Fail-Closed Recovery Watchdog in pure Python.

Zero-window execution on Windows when launched with pythonw.exe.
"""

import os
import sys
import json
import subprocess
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_DIR = ROOT / ".private-secrets" / "release-audit" / "scp-247"
KILL_SWITCH = PRIVATE_DIR / "KILL"
LEDGER = PRIVATE_DIR / "supervisor-ledger.jsonl"
SUPERVISOR_TASK = "SCP-247-Supervisor"
WATCHDOG_TASK = "SCP-247-Recovery-Watchdog"

try:
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass


def write_ledger(event: dict):
    try:
        event["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        event["watchdog_task"] = WATCHDOG_TASK
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass


def main():
    if KILL_SWITCH.exists():
        write_ledger({"event": "WATCHDOG_SUPPRESSED", "reason": "kill_switch_present"})
        return

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    try:
        res = subprocess.run(
            ["schtasks", "/query", "/tn", SUPERVISOR_TASK, "/fo", "CSV", "/nh"],
            capture_output=True,
            text=True,
            creationflags=flags,
            timeout=10,
        )
        output = res.stdout.strip()
    except Exception as e:
        write_ledger({"event": "WATCHDOG_RECOVERY_FAIL", "reason": f"query_error: {e}"})
        return

    if "Running" in output:
        return

    if "Disabled" in output:
        write_ledger({"event": "WATCHDOG_BLOCKED", "reason": "supervisor_task_disabled"})
        return

    try:
        subprocess.run(
            ["schtasks", "/run", "/tn", SUPERVISOR_TASK],
            capture_output=True,
            creationflags=flags,
            timeout=10,
        )
        write_ledger({"event": "WATCHDOG_RECOVERY_START", "reason": f"supervisor_state={output[:80]}"})
    except Exception as e:
        write_ledger({"event": "WATCHDOG_RECOVERY_FAIL", "reason": f"start_error: {e}"})


if __name__ == "__main__":
    main()
