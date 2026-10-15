#!/usr/bin/env python3
"""SCP Hourly Monitor & Silent Error Auditor.

Thu thập dữ liệu, giám sát trạng thái toàn bộ dịch vụ của SCP,
phát hiện lỗi âm thầm (silent failure) và tự động dừng SCP nếu phát hiện bất thường.
Tuân thủ nguyên tắc SCP DNA: Reality over Model, Fail-Closed.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# [SEC-S6] SSRF guard: every HTTP fetch in this monitor is a loopback
# self-probe and must go through the repo's validated fetch choke point.
sys.path.insert(0, str(ROOT))
from scp.security.url_safety import safe_urlopen

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _fetch_json(url: str, timeout: float = 5.0) -> tuple[int, dict[str, Any] | None, str | None]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SCP-Hourly-Monitor/1.0", "Accept": "application/json"},
    )
    try:
        # [SEC-S6] SSRF guard: monitor probes target loopback services only.
        with safe_urlopen(req, timeout=timeout, allow_internal=True) as resp:
            code = resp.status
            body = resp.read().decode("utf-8", errors="ignore")
            try:
                data = json.loads(body)
                return code, data, None
            except Exception as exc:
                return code, None, f"JSON parse error: {exc}"
    except urllib.error.HTTPError as exc:
        return exc.code, None, f"HTTPError: {exc.code} {exc.reason}"
    except Exception as exc:
        return 0, None, str(exc)


def check_sqlite_integrity(db_path: Path) -> tuple[bool, str]:
    if not db_path.exists():
        return True, "DB does not exist yet (clean state)"
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchone()
        conn.close()
        if res and res[0] == "ok":
            return True, "ok"
        return False, f"Integrity failed: {res}"
    except Exception as exc:
        return False, f"DB check error: {exc}"


def stop_scp_services() -> None:
    print("[SCP-MONITOR] DUNG TOAN BO SERVICES SCP...")
    stop_bat = ROOT / "stop-scp.bat"
    if stop_bat.exists() and sys.platform == "win32":
        try:
            subprocess.run(["cmd.exe", "/c", str(stop_bat)], cwd=str(ROOT), timeout=15, capture_output=True)
        except Exception as exc:
            print(f"[SCP-MONITOR] Loi khi chay stop-scp.bat: {exc}")
    # Force kill leftover listeners on Windows
    if sys.platform == "win32":
        _kill_port_listeners()


# Fixed allowlist of operational ports the monitor may clear.
_MONITOR_PORTS = frozenset({8000, 3030, 3000, 11434})


def _kill_port_listeners() -> None:
    """Kill processes LISTENING on the fixed ``_MONITOR_PORTS`` allowlist.

    [SEC] No shell string: the fixed binaries are resolved via
    ``shutil.which`` and executed with an argv list; netstat rows are
    parsed in Python and PIDs are digit-validated before taskkill.
    Fail-closed: unexpected rows are skipped, never executed.
    """
    netstat = shutil.which("netstat")
    taskkill = shutil.which("taskkill")
    if not netstat or not taskkill:
        print("[SCP-MONITOR] netstat/taskkill khong kha dung; bo qua buoc don port.")
        return
    try:
        probe = subprocess.run(
            [netstat, "-aon"], capture_output=True, text=True, timeout=15
        )
    except Exception as exc:
        print(f"[SCP-MONITOR] Loi khi chay netstat: {exc}")
        return
    if probe.returncode != 0:
        return
    for line in probe.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[3] != "LISTENING":
            continue
        local_addr = parts[1]
        if ":" not in local_addr:
            continue
        port_str = local_addr.rsplit(":", 1)[-1]
        if not port_str.isdigit() or int(port_str) not in _MONITOR_PORTS:
            continue
        pid = parts[-1]
        if not pid.isdigit() or pid == "0":
            continue
        try:
            subprocess.run(
                [taskkill, "/f", "/pid", pid], capture_output=True, text=True, timeout=10
            )
        except Exception:
            pass


# Allowlist shape for generated incident report filenames.
_INCIDENT_FILENAME_RE = re.compile(r"^SCP_ALERT_\d{8}_\d{6}\.json$")


def _safe_incident_report_path(base_dir: Path, filename: str) -> Path:
    """Validate the incident-report write target against a fixed allowlist.

    [SEC] Fail-closed path-traversal guard: rejects path separators,
    explicit ".." parts, any name outside the SCP_ALERT_*.json allowlist,
    and any path that escapes ``base_dir`` after resolve() (parents
    containment check).
    """
    if not filename or "/" in filename or "\\" in filename:
        raise ValueError(f"Rejected unsafe incident report filename: {filename!r}")
    parts = Path(filename).parts
    if ".." in parts or len(parts) != 1:
        raise ValueError(f"Rejected unsafe incident report filename: {filename!r}")
    if not _INCIDENT_FILENAME_RE.fullmatch(filename):
        raise ValueError(f"Incident report filename not in allowlist: {filename!r}")
    resolved_base = base_dir.resolve()
    resolved = (resolved_base / filename).resolve()
    if resolved.parent != resolved_base:
        raise ValueError(f"Resolved incident report path escapes {resolved_base}")
    return resolved


def _write_incident_report(base_dir: Path, filename: str, payload: dict[str, Any]) -> Path:
    """Validate the write target, then write the JSON report fail-closed."""
    report_file = _safe_incident_report_path(base_dir, filename)
    with report_file.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2)
    return report_file


def run_monitor(stop_on_error: bool = True) -> int:
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"\n============================================================")
    print(f"  SCP HOURLY MONITOR & SILENT AUDITOR — {timestamp}")
    print(f"============================================================\n")

    findings: list[str] = []
    status_report: dict[str, Any] = {
        "timestamp": timestamp,
        "services": {},
        "sqlite": {},
        "scheduler": {},
        "verdict": "UNKNOWN",
    }

    # 1. Probe FastAPI Backend (Port 8000)
    c_8000, d_8000, err_8000 = _fetch_json("http://127.0.0.1:8000/health")
    if c_8000 == 200 and d_8000 and d_8000.get("status") == "ok":
        commit = d_8000.get("service_identity", {}).get("commit", "unknown")[:8]
        pid = d_8000.get("service_identity", {}).get("pid", "unknown")
        status_report["services"]["fastapi"] = {"status": "ONLINE", "commit": commit, "pid": pid}
        print(f" [PASS] FastAPI Backend (port 8000): ONLINE (commit: {commit}, pid: {pid})")
    else:
        findings.append(f"FastAPI backend (port 8000) unreachable or unhealthy: code={c_8000}, err={err_8000}")
        status_report["services"]["fastapi"] = {"status": "OFFLINE", "error": err_8000}
        print(f" [FAIL] FastAPI Backend (port 8000): OFFLINE ({err_8000})")

    # 2. Probe Loop Scheduler (Port 3030)
    c_3030, d_3030, err_3030 = _fetch_json("http://127.0.0.1:3030/")
    if c_3030 == 200 and d_3030 and d_3030.get("service") == "scp-loop-scheduler":
        paused = d_3030.get("paused", False)
        scp_online = d_3030.get("scp_online", False)
        total_runs = d_3030.get("total_runs", 0)
        status_report["services"]["loop_scheduler"] = {
            "status": "ONLINE",
            "paused": paused,
            "scp_online": scp_online,
            "total_runs": total_runs,
        }
        print(f" [PASS] Loop Scheduler (port 3030): ONLINE (total_runs: {total_runs}, paused: {paused})")
        if not scp_online:
            findings.append("Loop Scheduler reports SCP backend is offline from its perspective")
    else:
        findings.append(f"Loop Scheduler (port 3030) unreachable: code={c_3030}, err={err_3030}")
        status_report["services"]["loop_scheduler"] = {"status": "OFFLINE", "error": err_3030}
        print(f" [FAIL] Loop Scheduler (port 3030): OFFLINE ({err_3030})")

    # 3. Probe Dashboard Composite Health (Port 3000)
    c_3000, d_3000, err_3000 = _fetch_json("http://127.0.0.1:3000/api/scp/health")
    if c_3000 == 200 and d_3000:
        overall = d_3000.get("overall", False)
        scp_state = d_3000.get("scp", "offline")
        status_report["services"]["dashboard"] = {"status": "ONLINE", "overall": overall, "scp_state": scp_state}
        print(f" [PASS] Dashboard (port 3000): ONLINE (composite state: {scp_state}, overall: {overall})")
    else:
        findings.append(f"Dashboard (port 3000) unreachable: code={c_3000}, err={err_3000}")
        status_report["services"]["dashboard"] = {"status": "OFFLINE", "error": err_3000}
        print(f" [FAIL] Dashboard (port 3000): OFFLINE ({err_3000})")

    # 4. Probe LLM Bridge (Port 11434)
    c_11434, d_11434, err_11434 = _fetch_json("http://127.0.0.1:11434/api/tags")
    if c_11434 == 200:
        status_report["services"]["llm_bridge"] = {"status": "ONLINE"}
        print(f" [PASS] LLM Bridge (port 11434): ONLINE")
    else:
        status_report["services"]["llm_bridge"] = {"status": "STANDBY/OFFLINE", "note": "Optional local provider"}
        print(f" [INFO] LLM Bridge (port 11434): STANDBY/OFFLINE ({err_11434})")

    # 5. Check SQLite Databases Integrity
    db_paths = [
        ROOT / "data" / "task_kernel.sqlite3",
        ROOT / "data" / "ask_task_kernel.sqlite3",
        ROOT / "data" / "knowledge.sqlite3",
    ]
    for db in db_paths:
        if db.exists():
            ok, msg = check_sqlite_integrity(db)
            status_report["sqlite"][db.name] = {"ok": ok, "message": msg}
            if ok:
                print(f" [PASS] SQLite {db.name}: Integrity OK")
            else:
                findings.append(f"SQLite database {db.name} corrupt or locked: {msg}")
                print(f" [FAIL] SQLite {db.name}: CORRUPT ({msg})")

    # 6. Check Loop Runs Log for Silent Failures
    loop_log = ROOT / "data" / "loop_runs.jsonl"
    if loop_log.exists():
        try:
            with open(loop_log, "r", encoding="utf-8", errors="ignore") as fp:
                lines = fp.readlines()
            recent = [json.loads(l.strip()) for l in lines[-10:] if l.strip()]
            failures = [r for r in recent if r.get("status") in ("error", "failed", "crash")]
            if len(failures) >= 3:
                findings.append(f"Loop Scheduler has {len(failures)} recent failed runs in data/loop_runs.jsonl")
                print(f" [WARN] Loop Scheduler recent failures: {len(failures)}")
            else:
                print(f" [PASS] Loop Runs Log: {len(recent)} recent runs checked, error count normal ({len(failures)})")
        except Exception as exc:
            findings.append(f"Could not read data/loop_runs.jsonl: {exc}")

    # Verdict Evaluation
    print("\n------------------------------------------------------------")
    if findings:
        status_report["verdict"] = "FAIL"
        status_report["findings"] = findings
        print(f"[VERDICT] PHAT HIEN {len(findings)} LOI HOAC BAT THUONG:")
        for f in findings:
            print(f"  - {f}")
        
        # Save incident report
        incidents_dir = ROOT / "reports" / "incidents"
        incidents_dir.mkdir(parents=True, exist_ok=True)
        report_name = f"SCP_ALERT_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file = _write_incident_report(incidents_dir, report_name, status_report)
        print(f"\n[REPORT] Da ghi bao cao loi tai: {report_file}")

        if stop_on_error:
            stop_scp_services()
            print("[ACTION] Da dung SCP de bao ve he thong va chuan bi sua chua.")
        return 1
    else:
        status_report["verdict"] = "PASS"
        print("[VERDICT] TOAN BO DICH VU SCP HOAT DONG BINH THUONG (HEALTHY)")
        print("Không phát hiện lỗi âm thầm. Hệ thống ổn định.")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SCP Hourly Monitor")
    parser.add_argument("--no-stop", action="store_true", help="Do not stop services on failure")
    args = parser.parse_args()
    sys.exit(run_monitor(stop_on_error=not args.no_stop))
