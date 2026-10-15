#!/usr/bin/env python3
"""Reality test for Fix 4-d-019: pause state persisted across restarts.

DNA #8 (KB accumulation — pause decision logged durably) + #17 (Hành động
khi chưa biết hết — restart behavior no longer surprises operator).

Before fix:
  - state.paused was in-memory only.
  - If operator called /pause then scheduler restarted (crash, deploy),
    it resumed the loop automatically → operator's intention silently
    overridden. Especially bad during maintenance: pause for a deploy,
    scheduler crashes, fires an audit mid-deploy.

After fix:
  - /pause writes {"paused": true, "paused_at": <ts>} to LOOP_STATE_PATH.
  - /resume writes {"paused": false}.
  - On boot, main() reads the file and restores state.paused BEFORE
    startLoop() — paused scheduler stays paused across restarts.

Tier-A (static-source) reality test + light runtime verification.
"""
import http.client
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


def _collect_boot_log(proc: "subprocess.Popen[str]", timeout_s: float, trigger: str = "listening"):
    """Collect child boot output until `trigger` appears or the deadline expires.

    S17 harness repair: the previous `proc.stdout.readline()` loop inside
    `while time.time() < deadline` could hang FOREVER once the child went
    quiet — a blocking read cannot observe a deadline. A daemon reader thread
    + queue keeps the deadline enforceable so the reality gate cannot be
    blocked by a silent child.
    """
    lines_queue: queue.Queue[str] = queue.Queue()
    threading.Thread(
        target=lambda: [lines_queue.put(line) for line in iter(proc.stdout.readline, "")],
        daemon=True,
    ).start()
    collected: list[str] = []
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            line = lines_queue.get(timeout=0.1)
        except queue.Empty:
            if proc.poll() is not None:
                break  # child exited — no further output will arrive
            continue
        collected.append(line)
        if trigger in line:
            return "".join(collected), True
    return "".join(collected), False

SOURCE_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/mini-services/loop-scheduler/index.ts'
)


def main() -> int:
    assert SOURCE_PATH.exists(), (
        f"FAIL: loop-scheduler/index.ts not found at {SOURCE_PATH}"
    )
    src = SOURCE_PATH.read_text(encoding="utf-8")
    print(f"PASS [1/6]: file exists ({SOURCE_PATH.name})")

    # -------------------------------------------------------------------------
    # TEST 2 — must import fs functions for read/write (readFile, writeFile,
    # mkdir from "node:fs/promises" OR readFileSync/writeFileSync from "fs").
    # -------------------------------------------------------------------------
    has_fs_persistence = bool(
        re.search(r"readFile\s*\(", src)
        and re.search(r"writeFile\s*\(", src)
    ) or bool(
        re.search(r"readFileSync\s*\(", src)
        and re.search(r"writeFileSync\s*\(", src)
    )
    assert has_fs_persistence, (
        "FAIL: no readFile/writeFile (or Sync variants) imports — pause "
        "state is still in-memory only"
    )
    print("PASS [2/6]: fs read/write functions imported (persistence available)")

    # -------------------------------------------------------------------------
    # TEST 3 — must reference a state file path (e.g. scheduler-state.json
    # or LOOP_STATE_PATH env var).
    # -------------------------------------------------------------------------
    has_state_path = (
        "scheduler-state.json" in src
        or "LOOP_STATE_PATH" in src
        or "STATE_FILE_PATH" in src
    )
    assert has_state_path, (
        "FAIL: no scheduler-state.json reference / LOOP_STATE_PATH env var — "
        "pause state has no durable file path"
    )
    print("PASS [3/6]: pause state file path referenced (scheduler-state.json / LOOP_STATE_PATH)")

    # -------------------------------------------------------------------------
    # TEST 4 — must have explicit persist + restore functions.
    # Pattern: `savePersistedState` (or `saveState`) + `loadPersistedState`
    # (or `loadState`).
    # -------------------------------------------------------------------------
    has_save_fn = bool(
        re.search(r"(?:async\s+)?function\s+(?:savePersistedState|saveState)\s*\(", src)
    )
    has_load_fn = bool(
        re.search(r"(?:async\s+)?function\s+(?:loadPersistedState|loadState)\s*\(", src)
    )
    assert has_save_fn and has_load_fn, (
        f"FAIL: persist/restore functions missing "
        f"(save={has_save_fn}, load={has_load_fn})"
    )
    print("PASS [4/6]: savePersistedState + loadPersistedState functions declared")

    # -------------------------------------------------------------------------
    # TEST 5 — the persist functions must be CALLED in the right places:
    #   - /pause handler calls save (with paused:true)
    #   - /resume handler calls save (with paused:false)
    #   - main()/boot calls load (to restore)
    # -------------------------------------------------------------------------
    pause_handler_saves = bool(
        re.search(
            r'path\s*===\s*"/pause".*?savePersistedState\s*\(\s*\{[^}]*paused\s*:\s*true',
            src,
            re.DOTALL,
        )
    )
    resume_handler_saves = bool(
        re.search(
            r'path\s*===\s*"/resume".*?savePersistedState\s*\(\s*\{[^}]*paused\s*:\s*false',
            src,
            re.DOTALL,
        )
    )
    boot_loads = bool(
        re.search(r"loadPersistedState\s*\(\s*\)", src)
    )
    assert pause_handler_saves, (
        "FAIL: /pause handler does not call savePersistedState({paused:true})"
    )
    assert resume_handler_saves, (
        "FAIL: /resume handler does not call savePersistedState({paused:false})"
    )
    assert boot_loads, (
        "FAIL: boot sequence does not call loadPersistedState() — paused "
        "state is never restored"
    )
    print("PASS [5/6]: /pause saves, /resume saves, boot loads (wired end-to-end)")

    # -------------------------------------------------------------------------
    # TEST 6 (runtime) — boot the scheduler, POST /pause, kill + restart,
    # verify GET / reports paused:true. Uses a stub SCP + LLM bridge that
    # are unreachable (so triggerAudit returns scp_offline immediately,
    # no audit fires).
    # -------------------------------------------------------------------------
    print("\n--- Runtime persistence test (DNA #2 reality) ---")
    env = dict(os.environ)
    _test_env_file = tempfile.NamedTemporaryFile("w", delete=False, suffix=".env")
    _test_env_file.close()
    env["LOOP_INTERVAL_SEC"] = "3600"  # don't fire cron during test
    env["SCP_BASE_URL"] = "http://127.0.0.1:65530"  # unreachable
    env["LLM_BRIDGE_URL"] = "http://127.0.0.1:65531"  # unreachable
    env["LOOP_SCHEDULER_PORT"] = "3041"
    env["LOOP_STATE_PATH"] = "/tmp/test-4-d-019-state.json"
    env["LOOP_LOG_PATH"] = "/tmp/test-4-d-019-runs.jsonl"
    env["SCP_ENV_FILE"] = _test_env_file.name
    env["SCP_SCHEDULER_ADMIN_TOKEN_FILE"] = ""
    env["SCP_SCHEDULER_ADMIN_TOKEN"] = "test-only-scheduler-token"

    # Clean slate
    for p in [env["LOOP_STATE_PATH"], env["LOOP_LOG_PATH"]]:
        try:
            os.unlink(p)
        except FileNotFoundError:
            pass

    # Boot #1
    proc1 = subprocess.Popen(
        ["bun", "mini-services/loop-scheduler/index.ts"],
        cwd=str(Path(__file__).resolve().parents[2]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        # Wait for boot (S17: trigger "listening" — commit 3f1690d reworded
        # the banner to "listening (loopback only — DNA #6; ...)"; deadline
        # is now enforceable via reader thread, no more gate hang).
        boot_log1, listening_seen = _collect_boot_log(proc1, timeout_s=4.0, trigger="listening")
        assert listening_seen, (
            f"FAIL: scheduler (boot #1) never reported 'listening' within 4s — boot_log: {boot_log1!r}"
        )
        # POST /pause
        conn = http.client.HTTPConnection("127.0.0.1", 3041, timeout=3)
        conn.request("POST", "/pause", headers={"Authorization": "Bearer " + env["SCP_SCHEDULER_ADMIN_TOKEN"]})
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
        conn.close()
        assert resp.status == 200, f"FAIL: /pause returned {resp.status}"
        assert '"paused": true' in body, f"FAIL: /pause body: {body!r}"
        print("PASS [6a/6]: POST /pause returned paused:true")

        # Verify state file was written
        with open(env["LOOP_STATE_PATH"]) as f:
            persisted = json.load(f)
        assert persisted.get("paused") is True, (
            f"FAIL: state file not written or paused != true: {persisted}"
        )
        print(f"PASS [6b/6]: state file persisted ({persisted})")
    finally:
        proc1.terminate()
        try:
            proc1.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc1.kill()
            proc1.wait(timeout=2)

    # Boot #2 — should restore paused=true from state file
    proc2 = subprocess.Popen(
        ["bun", "mini-services/loop-scheduler/index.ts"],
        cwd=str(Path(__file__).resolve().parents[2]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        # S17: enforceable boot wait (reader thread) + reworded-banner pin.
        boot_log2, listening_seen2 = _collect_boot_log(proc2, timeout_s=4.0, trigger="listening")
        assert listening_seen2, (
            f"FAIL: scheduler (boot #2) never reported 'listening' within 4s — boot_log: {boot_log2!r}"
        )
        # GET / — must report paused:true
        conn = http.client.HTTPConnection("127.0.0.1", 3041, timeout=3)
        conn.request("GET", "/")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
        conn.close()
        assert resp.status == 200, f"FAIL: GET / returned {resp.status}"
        assert '"paused": true' in body or '"paused":true' in body, (
            f"FAIL: scheduler did NOT restore paused state — body: {body[:300]!r}"
        )
        print("PASS [6c/6]: scheduler restored paused:true across restart (DNA #8 verified)")
    finally:
        proc2.terminate()
        try:
            proc2.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc2.kill()
            proc2.wait(timeout=2)

    # Cleanup
    for p in [env["LOOP_STATE_PATH"], env["LOOP_LOG_PATH"]]:
        try:
            os.unlink(p)
        except FileNotFoundError:
            pass

    try:
        os.unlink(_test_env_file.name)
    except FileNotFoundError:
        pass

    print("\n✓ Reality test 4-d-019 PASSED (6/6 assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
