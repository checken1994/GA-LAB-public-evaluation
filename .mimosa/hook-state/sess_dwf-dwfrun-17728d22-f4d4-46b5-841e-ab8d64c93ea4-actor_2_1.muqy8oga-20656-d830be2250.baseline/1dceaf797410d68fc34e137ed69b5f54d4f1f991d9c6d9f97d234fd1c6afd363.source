#!/usr/bin/env python3
"""SCP 24/7 Ops Monitor — heartbeat, metrics, alerts, evaluation.

Vòng theo dõi khép kín cho SCP chạy 24/7 trên PC (goal 002dda17):
- Mỗi chu kỳ (mặc định 60s) thu thập: trạng thái 4 dịch vụ, uptime pid,
  health status, độ trễ probe, số ERROR mới trong log, sản lượng request.
- Ghi mọi chỉ số + sự kiện vào ledger JSONL (append-only, có dấu thời gian
  UTC, nguồn, định danh phiên) — dữ liệu kỹ thuật, không chứa secret/PII.
- Đánh giá bộ quy tắc cảnh báo theo ngưỡng; cảnh báo được ghi ledger và
  ghi ra file alerts/pending để kênh thông báo (AutoClaw patrol) đọc.
- Tổng hợp báo cáo hằng ngày/hằng tuần (--report daily|weekly) từ ledger.
- --verify: kiểm tra tính liên tục heartbeat (gap > ngưỡng = FAIL).

Fail-closed: monitor không bao giờ tự sửa service; chỉ quan sát + cảnh báo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scp.security.url_safety import safe_urlopen  # noqa: E402 — repo egress choke point

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "ops"
LEDGER = DATA_DIR / "ops_ledger.jsonl"
ALERT_DIR = DATA_DIR / "alerts"
REPORT_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "ops_metrics.sqlite"

SERVICES = {
    "api": {"port": 8000, "health": "http://127.0.0.1:8000/health"},
    "bridge": {"port": 8081, "health": "http://127.0.0.1:8081/health"},
    "scheduler": {"port": 3030, "health": "http://127.0.0.1:3030/healthz"},
    "dashboard": {"port": 3000, "health": "http://127.0.0.1:3000/"},
}

# Alert thresholds (documented in SOP; user-adjustable)
THRESHOLDS = {
    "service_down": True,          # any service not LISTEN / health != 200
    "health_latency_ms": 2000,     # health probe slower than this
    "error_burst": 10,             # >10 new ERROR lines in log window
    "heartbeat_gap_seconds": 300,  # ledger gap tolerance (5 min)
}

SESSION_ID = os.environ.get("SCP_OPS_SESSION", f"ops-{dt.datetime.now(dt.UTC):%Y%m%d-%H%M%S}")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def utcnow() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="milliseconds")


def append_ledger(event: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    event.setdefault("ts", utcnow())
    event.setdefault("session", SESSION_ID)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS metrics (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   ts TEXT NOT NULL,
                   session TEXT NOT NULL,
                   service TEXT NOT NULL,
                   up INTEGER NOT NULL,
                   health_status INTEGER,
                   latency_ms INTEGER,
                   pid INTEGER,
                   pid_uptime_seconds INTEGER,
                   new_errors INTEGER NOT NULL DEFAULT 0
               )"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS alerts (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   ts TEXT NOT NULL,
                   session TEXT NOT NULL,
                   rule TEXT NOT NULL,
                   severity TEXT NOT NULL,
                   detail TEXT NOT NULL,
                   acknowledged INTEGER NOT NULL DEFAULT 0
               )"""
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS ix_metrics_ts ON metrics(ts)"
        )


def log_errors_since(path: Path, since_ts: float) -> int:
    """Count ERROR/Traceback lines appended to a log file since a timestamp."""
    if not path.exists():
        return 0
    try:
        if path.stat().st_mtime < since_ts:
            return 0
        text = path.read_text(encoding="utf-8", errors="replace")
        return sum(
            1
            for line in text.splitlines()
            if ("ERROR" in line or "Traceback" in line)
            and not line.startswith("WARNING")
        )
    except OSError:
        return 0


def pid_uptime(pid: int) -> int | None:
    try:
        import subprocess

        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-Process -Id {pid} -ErrorAction Stop).StartTime",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        start = dt.datetime.fromisoformat(out)
        return int((dt.datetime.now() - start).total_seconds())
    except Exception:
        return None


def probe_service(name: str, cfg: dict) -> dict:
    port = cfg["port"]
    up = 0
    status = None
    latency = None
    pid = None
    try:
        import subprocess as sp

        ps_out = sp.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "$c = Get-NetTCPConnection -LocalPort "
                f"{port} -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; "
                "if ($c) { $c.OwningProcess }",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        if ps_out.isdigit():
            pid = int(ps_out)
            up = 1
    except Exception:
        pass

    if up:
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(cfg["health"], method="GET")
            # [SEC] Same choke point as _fetch_json: cfg URLs go through the
            # egress gate (scheme allowlist + private-IP pinning).
            with safe_urlopen(req, timeout=5, allow_internal=True) as resp:
                status = resp.status
        except Exception:
            status = None
        latency = int((time.perf_counter() - t0) * 1000)
        if status != 200:
            up = 0

    return {
        "service": name,
        "up": up,
        "health_status": status,
        "latency_ms": latency,
        "pid": pid,
        "pid_uptime_seconds": pid_uptime(pid) if pid else None,
    }


def evaluate_alerts(metrics: list[dict], state: dict) -> list[dict]:
    alerts: list[dict] = []
    now = time.time()

    for m in metrics:
        if not m["up"]:
            alerts.append(
                {
                    "rule": "service_down",
                    "severity": "critical",
                    "detail": f"{m['service']} DOWN (port probe/health failed)",
                }
            )
        elif (
            m["latency_ms"] is not None
            and m["latency_ms"] > THRESHOLDS["health_latency_ms"]
        ):
            alerts.append(
                {
                    "rule": "health_latency_ms",
                    "severity": "warning",
                    "detail": f"{m['service']} health latency {m['latency_ms']}ms > {THRESHOLDS['health_latency_ms']}ms",
                }
            )
        if m["new_errors"] >= THRESHOLDS["error_burst"]:
            alerts.append(
                {
                    "rule": "error_burst",
                    "severity": "warning",
                    "detail": f"{m['service']} {m['new_errors']} new ERROR lines in log window",
                }
            )

    gap = now - state.get("last_heartbeat_epoch", now)
    if gap > THRESHOLDS["heartbeat_gap_seconds"]:
        alerts.append(
            {
                "rule": "heartbeat_gap",
                "severity": "critical",
                "detail": f"monitor gap {int(gap)}s > {THRESHOLDS['heartbeat_gap_seconds']}s",
            }
        )
    return alerts


def emit_alert(alert: dict) -> None:
    append_ledger({"kind": "alert", **alert})
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO alerts (ts, session, rule, severity, detail) VALUES (?,?,?,?,?)",
            (utcnow(), SESSION_ID, alert["rule"], alert["severity"], alert["detail"]),
        )
    ALERT_DIR.mkdir(parents=True, exist_ok=True)
    pending = ALERT_DIR / "pending.jsonl"
    with pending.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": utcnow(), "session": SESSION_ID, **alert}, ensure_ascii=False) + "\n")


def one_cycle(state: dict) -> None:
    cycle_ts = time.time()
    metrics = []
    for name, cfg in SERVICES.items():
        m = probe_service(name, cfg)
        m["new_errors"] = log_errors_since(
            ROOT / "data" / "service-logs" / f"{'backend' if name == 'api' else name}.log",
            state.get("last_cycle_epoch", cycle_ts - 60),
        )
        metrics.append(m)
        append_ledger({"kind": "metric", **m})

    with sqlite3.connect(DB_PATH) as db:
        db.executemany(
            """INSERT INTO metrics (ts, session, service, up, health_status,
                                     latency_ms, pid, pid_uptime_seconds, new_errors)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            [
                (
                    utcnow(), SESSION_ID, m["service"], m["up"],
                    m["health_status"], m["latency_ms"], m["pid"],
                    m["pid_uptime_seconds"], m["new_errors"],
                )
                for m in metrics
            ],
        )

    for alert in evaluate_alerts(metrics, state):
        emit_alert(alert)

    append_ledger(
        {
            "kind": "heartbeat",
            "services_up": sum(m["up"] for m in metrics),
            "services_total": len(metrics),
            "alerts_this_cycle": 0,
        }
    )
    state["last_cycle_epoch"] = cycle_ts
    state["last_heartbeat_epoch"] = time.time()
    state["cycles"] = state.get("cycles", 0) + 1

    if state["cycles"] % 10 == 0 or state.get("alerts_seen") != state.get("alerts_total"):
        summary = " | ".join(
            f"{m['service']}={'UP' if m['up'] else 'DOWN'}" for m in metrics
        )
        print(f"[{utcnow()}] cycle {state['cycles']}: {summary}", flush=True)


def verify_continuity() -> int:
    """Check heartbeat continuity: no gap above threshold. Returns exit code."""
    if not LEDGER.exists():
        print("NO_LEDGER")
        return 1
    beats = []
    with LEDGER.open(encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("kind") == "heartbeat":
                beats.append(
                    dt.datetime.fromisoformat(e["ts"]).timestamp()
                )
    if len(beats) < 2:
        print(f"INSUFFICIENT_HEARTBEATS: {len(beats)}")
        return 1
    beats.sort()
    gaps = [b2 - b1 for b1, b2 in zip(beats, beats[1:])]
    max_gap = max(gaps)
    tolerance = THRESHOLDS["heartbeat_gap_seconds"]
    violations = [(round(g),) for g in gaps if g > tolerance]
    print(
        f"heartbeats={len(beats)} max_gap={max_gap:.0f}s tolerance={tolerance}s "
        f"violations={len(violations)}"
    )
    for v in violations[:5]:
        print("  gap_over:", v)
    return 0 if not violations else 2


def build_report(period: str, out_path: Path) -> dict:
    """Aggregate ledger+DB into an evaluation report for day/week."""
    if period == "daily":
        since = dt.datetime.now(dt.UTC) - dt.timedelta(days=1)
    else:
        since = dt.datetime.now(dt.UTC) - dt.timedelta(days=7)
    since_s = since.timestamp()

    total, up_count, down_events, alert_count, beats = 0, 0, 0, 0, 0
    per_service: dict[str, dict] = {}
    with LEDGER.open(encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = dt.datetime.fromisoformat(e["ts"]).timestamp()
            if ts < since_s:
                continue
            if e.get("kind") == "metric":
                total += 1
                svc = e.get("service", "?")
                d = per_service.setdefault(svc, {"up": 0, "total": 0, "err": 0})
                d["total"] += 1
                d["up"] += int(e.get("up", 0))
                d["err"] += int(e.get("new_errors", 0))
            elif e.get("kind") == "alert":
                alert_count += 1
                down_events += 1 if e.get("rule") == "service_down" else 0
            elif e.get("kind") == "heartbeat":
                beats += 1

    uptime_by_service = {
        svc: f"{(d['up'] / d['total'] * 100):.1f}% ({d['up']}/{d['total']})"
        for svc, d in per_service.items()
    }
    report = {
        "period": period,
        "window_start": since.isoformat(),
        "generated_at": utcnow(),
        "session": SESSION_ID,
        "heartbeats": beats,
        "metric_samples": total,
        "alerts": alert_count,
        "service_down_events": down_events,
        "uptime_by_service": uptime_by_service,
        "verdict": (
            "OK" if alert_count == 0 and down_events == 0 else "ATTENTION_NEEDED"
        ),
        "notes": (
            "Auto-generated from ops_ledger.jsonl; every number is traceable "
            "back to timestamped ledger entries (traceability contract)."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    # also render a small HTML snapshot (Fathom navy/grey audit style)
    html_path = out_path.with_suffix(".html")
    rows = "".join(
        f"<tr><td>{svc}</td><td>{d['up']}/{d['total']}</td>"
        f"<td>{(d['up']/max(d['total'],1)*100):.1f}%</td><td>{d['err']}</td></tr>"
        for svc, d in per_service.items()
    )
    html_path.write_text(
        f"""<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8">
<title>SCP Ops Report — {period}</title><style>
body{{font-family:'Segoe UI',Arial,sans-serif;background:#f4f6f9;color:#1c2733;margin:0;padding:32px}}
.wrap{{max-width:900px;margin:0 auto}}
h1{{font-size:22px;color:#14243c;border-bottom:3px solid #14243c;padding-bottom:8px}}
table{{border-collapse:collapse;width:100%;font-size:13px;background:#fff}}
th{{background:#14243c;color:#e8edf4;padding:8px 10px;text-align:left}}
td{{border-bottom:1px solid #d7dde6;padding:6px 10px}}
.kpi{{display:flex;gap:12px;margin:16px 0;flex-wrap:wrap}}
.kpi div{{background:#14243c;color:#fff;padding:12px 18px;border-radius:4px}}
.kpi b{{display:block;font-size:20px}}</style></head><body><div class="wrap">
<h1>SCP Ops Evaluation — {period}</h1>
<p>Window: {since.isoformat()} → {utcnow()}<br>Session: {SESSION_ID}</p>
<div class="kpi"><div><b>{beats}</b><span>heartbeats</span></div>
<div><b>{alert_count}</b><span>alerts</span></div>
<div><b>{down_events}</b><span>service-down events</span></div>
<div><b>{report['verdict']}</b><span>verdict</span></div></div>
<table><tr><th>Service</th><th>UP/Total</th><th>Uptime</th><th>New ERRORs</th></tr>
{rows}</table>
<p style="font-size:12px;color:#5b6a7d">Mọi số liệu truy vết được về
ops_ledger.jsonl (timestamp UTC + session id). Sinh tự động.</p>
</div></body></html>""",
        encoding="utf-8",
    )
    print(f"report written: {out_path} (+ .html)")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="SCP 24/7 ops monitor")
    ap.add_argument("--interval", type=int, default=60, help="seconds between cycles")
    ap.add_argument("--once", action="store_true", help="run a single cycle")
    ap.add_argument("--verify", action="store_true", help="verify heartbeat continuity")
    ap.add_argument("--report", choices=["daily", "weekly"], dest="report_period")
    args = ap.parse_args()

    if args.verify:
        return verify_continuity()
    if getattr(args, "report_period", None):
        out = REPORT_DIR / f"ops-report-{args.report_period}-{dt.datetime.now(dt.UTC):%Y%m%d-%H%M}.json"
        r = build_report(args.report_period, out)
        print(json.dumps({k: v for k, v in r.items() if k != "notes"}, indent=1)[:600])
        return 0

    init_db()
    state: dict = {"cycles": 0, "last_cycle_epoch": 0.0, "last_heartbeat_epoch": time.time()}
    append_ledger({"kind": "monitor_start", "interval_s": args.interval})
    print(f"monitor start session={SESSION_ID} interval={args.interval}s", flush=True)
    if args.once:
        one_cycle(state)
        return 0
    while True:
        try:
            one_cycle(state)
        except Exception as exc:
            append_ledger({"kind": "monitor_error", "error": str(exc)[:200]})
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    sys.exit(main())
