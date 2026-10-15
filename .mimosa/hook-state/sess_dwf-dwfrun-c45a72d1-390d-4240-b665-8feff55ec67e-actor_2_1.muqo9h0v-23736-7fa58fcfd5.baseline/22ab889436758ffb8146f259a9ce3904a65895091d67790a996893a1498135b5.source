#!/usr/bin/env python3
"""Render the SCP 24/7 dashboard from real ops data (ledger + DB).

Runs after each monitor cycle; reads the latest metrics + alerts and fills
the static HTML template. Data source of truth: ops_ledger.jsonl.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "ops"
LEDGER = DATA_DIR / "ops_ledger.jsonl"
DB_PATH = DATA_DIR / "ops_metrics.sqlite"
TEMPLATE = ROOT / "scripts" / "ops" / "ops_dashboard_template.html"
OUT = ROOT / "data" / "ops" / "dashboard.html"

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def last_metrics(limit: int = 4) -> list[dict]:
    rows: list[dict] = []
    if not DB_PATH.exists():
        return rows
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cur = db.execute(
            """SELECT service, ts, up, health_status, latency_ms, pid,
                      pid_uptime_seconds, new_errors
               FROM metrics ORDER BY id DESC LIMIT ?""",
            (limit,),
        )
        for r in cur:
            rows.append(dict(r))
    return rows


def latest_alerts(limit: int = 8) -> list[dict]:
    rows: list[dict] = []
    pending = DATA_DIR / "alerts" / "pending.jsonl"
    if pending.exists():
        with pending.open(encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows[-limit:]


def render() -> Path:
    html = TEMPLATE.read_text(encoding="utf-8")
    metrics = last_metrics()
    alerts = latest_alerts()

    svc_rows = []
    latest_by_svc = {}
    for m in metrics:
        latest_by_svc.setdefault(m["service"], m)
    for svc, m in sorted(latest_by_svc.items()):
        state = "UP" if m["up"] else "DOWN"
        hours = (
            f"{m['pid_uptime_seconds'] / 3600:.1f}h"
            if m.get("pid_uptime_seconds")
            else "—"
        )
        svc_rows.append(
            f'<div class="svc {state}"><div class="name">{svc}</div>'
            f'<div class="status">{state}</div>'
            f'<div class="meta">health {m["health_status"] or "—"} · '
            f'latency {m["latency_ms"] if m["latency_ms"] is not None else "—"}ms · '
            f'pid {m["pid"] or "—"} · uptime {hours}</div></div>'
        )
    html = html.replace("<!-- rows -->", "".join(svc_rows), 1)

    m_rows = []
    for m in reversed(metrics):
        m_rows.append(
            f"<tr><td>{m['service']}</td><td>{m['health_status'] or '—'}</td>"
            f"<td>{m['latency_ms'] if m['latency_ms'] is not None else '—'} ms</td>"
            f"<td>{m['pid'] or '—'}</td>"
            f"<td>{(m['pid_uptime_seconds'] or 0) / 3600:.1f}</td>"
            f"<td>{m['new_errors']}</td></tr>"
        )
    html = html.replace("<!-- rows -->", "".join(m_rows), 1)

    a_rows = []
    for a in reversed(alerts):
        a_rows.append(
            f"<tr><td>{a.get('ts', '—')}</td><td>{a.get('rule', '—')}</td>"
            f"<td>{a.get('severity', '—')}</td><td>{a.get('detail', '—')}</td></tr>"
        )
    if not a_rows:
        a_rows.append(
            '<tr><td colspan="4">Không có cảnh báo nào được ghi.</td></tr>'
        )
    html = html.replace("<!-- rows -->", "".join(a_rows), 1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    out = render()
    print(f"dashboard rendered: {out}")
