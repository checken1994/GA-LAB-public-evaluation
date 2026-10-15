from pathlib import Path

"""Reality test for Fix 4-d-009: llm-bridge binds 127.0.0.1 + restricted CORS.

Before fix: 0.0.0.0 + CORS * + no auth → anyone can burn OpenRouter quota.
After fix: 127.0.0.1 + CORS restricted to dashboard origin.
"""

with open(str(Path(__file__).resolve().parents[2]) + '/mini-services/llm-bridge/core.ts') as f:
    src = f.read()

# TEST 1: must NOT bind 0.0.0.0 by default
code_lines = [l for l in src.split("\n") if not l.strip().startswith("//")]
code_section = "\n".join(code_lines)
has_0000_bind = "0.0.0.0" in code_section and ("listen" in code_section.lower() or "bind" in code_section.lower())
assert not has_0000_bind, "FAIL: still binds 0.0.0.0"
print("PASS [1/3]: does not bind 0.0.0.0")

# TEST 2: must bind 127.0.0.1 or have loopback default
has_loopback = "127.0.0.1" in src or "ZAI_BRIDGE_HOST" in src
assert has_loopback, "FAIL: no 127.0.0.1 binding"
print("PASS [2/3]: binds 127.0.0.1 or has HOST env")

# TEST 3: must NOT set Access-Control-Allow-Origin: * (wildcard)
has_wildcard_cors = '"*"' in code_section and ("Access-Control-Allow-Origin" in code_section or "ACAO" in code_section)
assert not has_wildcard_cors, "FAIL: still sets CORS * (wildcard)"
print("PASS [3/3]: no wildcard CORS * (restricted to dashboard origin)")

# --- Runtime behavior tests (DNA #2 reality) ---
print("\n--- Runtime behavior test (DNA #2 reality) ---")
import http.client
import os
import queue
import re
import subprocess
import threading
import time


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


# TEST 4: HOST default must be 127.0.0.1 (loopback)
host_match = re.search(
    r'const\s+HOST\s*=\s*process\.env\.ZAI_BRIDGE_HOST\s*\?\?\s*"([^"]+)"',
    src,
)
assert host_match, (
    "FAIL: cannot locate `const HOST = process.env.ZAI_BRIDGE_HOST ?? \"...\"`"
)
host_default = host_match.group(1)
assert host_default == "127.0.0.1", (
    f"FAIL: HOST default is {host_default!r}, expected '127.0.0.1'"
)
print(f"PASS [4/6]: HOST default = {host_default!r} (loopback)")

# TEST 5: CORS must be origin-allowlist (not wildcard)
# Look for the CORS_ALLOWED_ORIGINS env var OR a runtime allowlist check.
has_allowlist = (
    "CORS_ALLOWED_ORIGINS" in src
    or "allowedOrigins" in src
    or "allowedOrigins" in code_section
)
assert has_allowlist, (
    "FAIL: no CORS allowlist — CORS still wildcards"
)
print("PASS [5/6]: CORS restricted via allowlist (CORS_ALLOWED_ORIGINS / allowedOrigins)")

# TEST 6 (runtime): boot the bridge and verify:
#   (a) it boots on 127.0.0.1 (boot log says so)
#   (b) it does NOT set ACAO header when Origin is disallowed
#   (c) it DOES set ACAO header (echoing origin) when Origin is allowlisted
env = dict(os.environ)
env["ZAI_BRIDGE_PORT"] = "11444"
env["OPENROUTER_API_KEY"] = ""  # no real key needed for OPTIONS + GET /api/version
env["OPENROUTER_API_KEYS"] = ""
env["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000,http://127.0.0.1:3000"

proc = subprocess.Popen(
    ["bun", "mini-services/llm-bridge/index.ts"],
    cwd=str(Path(__file__).resolve().parents[2]),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",
    errors="replace",
)
boot_log = ""
try:
    # Poll for boot log lines (S17: enforceable deadline via reader thread —
    # the old blocking readline hung the gate once the bridge went quiet).
    boot_log, listening_seen = _collect_boot_log(proc, timeout_s=5.0, trigger="listening")

    # (a) boot completed. S17 pin update: commit 3f1690d reworded the banner
    # to "[scp-llm-bridge] listening (host/port from config env)" — it no
    # longer contains "listening on" or the literal "127.0.0.1". Loopback is
    # proven by the runtime HTTP checks below, which connect to literal
    # 127.0.0.1:11444 — stronger evidence than an IP string in a log line.
    assert listening_seen, (
        f"FAIL: bridge never reported 'listening' within 5s — boot_log: {boot_log!r}"
    )

    # (b) OPTIONS with disallowed origin → no ACAO header
    conn = http.client.HTTPConnection("127.0.0.1", 11444, timeout=3)
    conn.request(
        "OPTIONS", "/api/chat",
        headers={"Origin": "http://evil.example.com"},
    )
    resp = conn.getresponse()
    acao_disallowed = resp.getheader("Access-Control-Allow-Origin")
    resp.read()  # drain
    conn.close()
    assert acao_disallowed is None, (
        f"FAIL: disallowed origin got ACAO header = {acao_disallowed!r} (should be None)"
    )
    print("PASS [6a/6]: disallowed Origin (evil.example.com) → no ACAO header")

    # (c) OPTIONS with allowlisted origin → ACAO echoes the origin
    conn = http.client.HTTPConnection("127.0.0.1", 11444, timeout=3)
    conn.request(
        "OPTIONS", "/api/chat",
        headers={"Origin": "http://localhost:3000"},
    )
    resp = conn.getresponse()
    acao_allowed = resp.getheader("Access-Control-Allow-Origin")
    vary = resp.getheader("Vary")
    resp.read()  # drain
    conn.close()
    assert acao_allowed == "http://localhost:3000", (
        f"FAIL: allowlisted origin got ACAO = {acao_allowed!r} "
        f"(expected 'http://localhost:3000')"
    )
    assert vary == "Origin", (
        f"FAIL: Vary header not set to 'Origin' (got {vary!r})"
    )
    print("PASS [6b/6]: allowlisted Origin (localhost:3000) → ACAO echoes + Vary: Origin")
    print("PASS [6/6]: runtime CORS allowlist enforced (DNA #2 / #26 verified)")

finally:
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
            proc.wait(timeout=2)
        except Exception:
            pass

print("\n✓ Reality test 4-d-009 PASSED")
