"""Live flow proof: boot SCP from the current working tree, run one real /ask
end-to-end, verify the task kernel rows at the physical SQLite layer, shut down.

Reusable evidence tool for the question "da chay SCP that chua?" — every claim
it prints comes from a real HTTP/socket/SQLite observation made during THIS run.
No secret values are ever printed (keys are read from .env at runtime, only
their length is shown).

Usage:
    python tools/live_flow_proof.py [port]           # default port 8091
    python tools/live_flow_proof.py [port] --egress-deny
                                                     # boot with SCP_EGRESS_MODE=deny
                                                     # (temp env composed from repo .env)
                                                     # and prove the LLM ask fails closed
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scp.security.url_safety import safe_urlopen  # noqa: E402 — repo SSRF choke point

DEFAULT_PORT = 8091
BASE = "http://127.0.0.1:%d"


def _compose_deny_env() -> Path:
    """Copy the repo .env into a temp env file with SCP_EGRESS_MODE=deny.

    Used only for the deny-path proof; the temp file holds the owner's local
    config for the duration of one boot and is deleted in the caller's finally.
    """
    lines = (ROOT / ".env").read_text(encoding="utf-8").splitlines()
    out = ["SCP_EGRESS_MODE=deny"]
    for line in lines:
        if line.strip().startswith("SCP_EGRESS_MODE="):
            continue
        out.append(line)
    fd, name = tempfile.mkstemp(prefix="scp-egress-deny-", suffix=".env")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    return Path(name)


def _http(method: str, url: str, timeout: float = 10, headers: dict | None = None, body: dict | None = None):
    """Loopback-only request through the repository SSRF guard."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with safe_urlopen(req, timeout=timeout, allow_internal=True) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception:
            return exc.code, {}
    except Exception:
        return 0, {}


def main() -> int:
    args = [a for a in sys.argv[1:]]
    egress_deny = "--egress-deny" in args
    args = [a for a in args if a != "--egress-deny"]
    port = int(args[0]) if args else DEFAULT_PORT
    base = BASE % port
    print("HEAD:", subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                  text=True, cwd=str(ROOT)).stdout.strip()[:12])

    deny_env_file = _compose_deny_env() if egress_deny else None
    boot_env = dict(os.environ)
    if deny_env_file is not None:
        boot_env["SCP_ENV_FILE"] = str(deny_env_file)
        print("MODE  egress-deny proof: SCP_EGRESS_MODE=deny composed (temp env file, deleted at exit)")

    # [SEC] boot log stays inside the system temp dir (same guard as run_full_audit).
    boot_log_path = Path(tempfile.gettempdir()) / f"scp-live-flow-proof-{int(time.time())}.log"
    if not boot_log_path.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise ValueError(f"rejected unsafe boot log path: {boot_log_path}")
    log_handle = boot_log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "-m", "scp", str(port)],
                            cwd=str(ROOT), stdout=log_handle, stderr=subprocess.STDOUT, env=boot_env)
    try:
        code, health = 0, {}
        for _ in range(40):
            code, health = _http("GET", f"{base}/health", timeout=4)
            if code == 200:
                break
            time.sleep(1)
        sid = health.get("service_identity", {})
        # [FIX 2026-09-26] service_identity KHÔNG có key 'version' (keys:
        # service_name/mode/host/configured_port/pid/commit/config_hash/argv) —
        # 'version' nằm top-level trong /health body. In key thật, không in rỗng.
        print("BOOT  /health:", code, "| commit:", str(sid.get("commit", ""))[:12],
              "| port:", sid.get("configured_port"), "| version:", health.get("version", ""))
        if code != 200:
            print("FAIL: service did not become healthy; boot log tail:")
            print(boot_log_path.read_text(encoding="utf-8", errors="replace")[-1200:])
            return 1

        # Readiness gate: /ask before judge+scheduler are ready returns 503.
        ready_code, ready = 0, {}
        for _ in range(60):
            ready_code, ready = _http("GET", f"{base}/ready", timeout=4)
            checks = ready.get("checks", {}) if isinstance(ready, dict) else {}
            if ready_code == 200 and checks.get("judge") == "ok" and checks.get("background_scheduler") == "ok":
                break
            time.sleep(0.5)
        print("READY /ready:", ready_code, "| checks:", ready.get("checks", {}))

        admin_key = ""
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("SCP_ADMIN_KEY="):
                admin_key = line.split("=", 1)[1].strip()
        print("KEY   SCP_ADMIN_KEY: loaded len=%d (value never printed)" % len(admin_key) if admin_key else "KEY   NOT FOUND")

        code, token_res = _http("POST", f"{base}/auth/token", body={"admin_key": admin_key})
        token = token_res.get("access_token", "")
        print("AUTH  /auth/token:", code, "| JWT len=%d (value never printed)" % len(token) if token else "| NO TOKEN")
        if code != 200 or not token:
            return 1

        headers = {"Authorization": f"Bearer {token}"}
        question = "If a train travels 60 km in 45 minutes, what is its average speed in km/h?"
        t0 = time.time()
        code, answer = _http("POST", f"{base}/ask", timeout=120, headers=headers,
                             body={"question": question, "session_id": f"live-flow-proof-{int(time.time())}"})
        elapsed = time.time() - t0
        print("ASK   /ask: HTTP %s in %.1fs" % (code, elapsed))
        if code != 200:
            print("      body:", json.dumps(answer)[:300])
        print("      verdict      =", answer.get("verdict"))
        print("      governance   =", answer.get("governance_decision"))
        print("      confidence   =", answer.get("confidence"))
        print("      final_answer =", str(answer.get("final_answer", ""))[:200])
        print("      run_id       =", answer.get("run_id"))

        if egress_deny:
            # Deny-path expectation: provider hosts are blocked, so the ask
            # must fail closed (no delivered LLM answer, no confident PASS).
            log_text = boot_log_path.read_text(encoding="utf-8", errors="replace").lower()
            deny_signals = [m for m in ("egress", "deny", "blocked") if m in log_text]
            fail_closed = (
                answer.get("verdict") != "PASS"
                or answer.get("governance_decision") in ("ESCALATE", "KILL")
                or "withheld" in str(answer.get("final_answer", "")).lower()
            )
            print("DENY  provider calls blocked -> ask failed closed:",
                  "YES" if fail_closed else "NO (FAIL: answer delivered under deny mode)")
            print("DENY  boot-log signals (egress/deny/blocked):", deny_signals or "none found")

        db_path = ROOT / "data" / "ask_task_kernel.sqlite3"
        if db_path.exists():
            db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
            try:
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                print("DB    kernel sqlite:", db_path.name, "| tables:", sorted(tables)[:10])
                newest = None
                if "tasks" in tables:
                    cols = [c[1] for c in db.execute("PRAGMA table_info(tasks)")]
                    row = db.execute("SELECT * FROM tasks ORDER BY rowid DESC LIMIT 1").fetchone()
                    newest = dict(zip(cols, row)) if row else None
                    shown = {k: newest.get(k) for k in newest
                             if k.lower() in ("id", "task_id", "state", "status", "created_at", "updated_at")}
                    print("DB    newest task row:", shown)
                if "events" in tables:
                    ev_cols = [c[1] for c in db.execute("PRAGMA table_info(events)")]
                    tid = (newest or {}).get("task_id")
                    id_col = "task_id" if "task_id" in ev_cols else ev_cols[0]
                    kind_col = "event_type" if "event_type" in ev_cols else ("type" if "type" in ev_cols else ev_cols[1])
                    rows = db.execute(f"SELECT {kind_col} FROM events WHERE {id_col} = ? ORDER BY rowid",
                                      (tid,)).fetchall()
                    chain = " -> ".join(str(r[0]) for r in rows)
                    print("DB    events for newest task (%d):" % len(rows), chain)
                integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
                print("DB    integrity_check:", integrity)
            finally:
                db.close()
        else:
            print("DB    kernel sqlite not found at", db_path)
    finally:
        # Kill the whole process tree: the launcher may spawn children that
        # would otherwise keep serving after the parent dies.
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True, text=True)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        log_handle.close()
        time.sleep(1)
        try:
            boot_log_path.unlink()
        except OSError:
            pass
        if deny_env_file is not None:
            try:
                deny_env_file.unlink()
            except OSError:
                pass

    code_after, _ = _http("GET", f"{base}/health", timeout=3)

    print("SHUTDOWN: /health after kill ->", (code_after or "000"), "(000/0 = connection refused, service down)")
    print("DONE  - boot log removed; all observations above are from THIS run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
