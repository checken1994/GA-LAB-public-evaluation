#!/usr/bin/env python3
"""Reality test for Fix 4-d-023: streaming response is not falsely advertised.

DNA #22 (PASS ≠ TRUE — endpoint "supports" stream=true but doesn't really) +
#26 (Reality có quyền cuối cùng — Reality of fake streaming is hidden).

Before fix:
  - Bridge accepts `stream: true` (Ollama default = true) and returns NDJSON.
  - But the upstream OpenRouter call uses `stream: false` and the WHOLE
    content is buffered before the first NDJSON line is emitted (single
    chunk + done envelope).
  - Clients see "streaming" UX that's actually blocking — false advertisement.

After fix (accepted alternatives per spec):
  - EITHER: implement proper streaming pipe (OpenRouter SSE → Ollama NDJSON
    via ReadableStream/TransformStream), OR
  - Remove the false advertisement (document as non-streaming + explicit
    X-Stream-Mode header so clients can detect).
  This implementation chose the second: explicit `X-Stream-Mode: buffered-
  single-chunk` response header + honest docstring.

Tier-A (static-source) reality test + light runtime verification.
"""
import http.client
import os
import queue
import re
import subprocess
import sys
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
    str(Path(__file__).resolve().parents[2]) + '/mini-services/llm-bridge/core.ts'
)


def main() -> int:
    assert SOURCE_PATH.exists(), (
        f"FAIL: llm-bridge/index.ts not found at {SOURCE_PATH}"
    )
    src = SOURCE_PATH.read_text(encoding="utf-8")
    print(f"PASS [1/4]: file exists ({SOURCE_PATH.name})")

    # -------------------------------------------------------------------------
    # TEST 2 — must NOT falsely advertise streaming. Either:
    #   (a) proper streaming pipe (ReadableStream/TransformStream that pipes
    #       OpenRouter's SSE chunks incrementally to client), OR
    #   (b) explicit non-streaming advertisement (X-Stream-Mode header or
    #       honest docstring saying "buffered-single-chunk" / "not real
    #       streaming").
    # -------------------------------------------------------------------------
    # Approach (a): look for `response.body.getReader()` (consuming
    # OpenRouter's stream) + a TransformStream that converts to NDJSON
    # incrementally. This is the "proper pipe" approach.
    has_real_pipe = bool(
        re.search(r"response\.body\.getReader\s*\(", src)
    ) and bool(
        re.search(r"TransformStream|ReadableStream\s*\(", src)
    ) and bool(
        # And it must be ENQUEUED incrementally (not buffered-then-emitted).
        re.search(r"controller\.enqueue\s*\(", src)
    )
    # Approach (b): explicit X-Stream-Mode header or honest docstring.
    has_explicit_buffered_marker = (
        "X-Stream-Mode" in src
        and ("buffered" in src.lower())
    )
    has_honest_docstring = bool(
        re.search(
            r"(NOT real streaming|buffered-single-chunk|not.*real.*stream|fake.*stream|false advertisement)",
            src,
            re.IGNORECASE,
        )
    )
    assert (
        has_real_pipe or (has_explicit_buffered_marker or has_honest_docstring)
    ), (
        "FAIL: bridge neither pipes OpenRouter's stream through NOR explicitly "
        "marks the response as buffered — false advertisement persists"
    )
    if has_real_pipe:
        print("PASS [2/4]: proper streaming pipe (ReadableStream + getReader + enqueue)")
    else:
        print("PASS [2/4]: explicit buffered-mode marker (X-Stream-Mode / honest docstring)")

    # -------------------------------------------------------------------------
    # TEST 3 — if approach (b) is used, the X-Stream-Mode header (or
    # equivalent) must be present in the actual streaming response headers
    # (not just in a comment).
    # -------------------------------------------------------------------------
    if has_real_pipe:
        # Skip this check — proper pipe doesn't need the header.
        print("PASS [3/4]: (skipped — real pipe doesn't need X-Stream-Mode header)")
    else:
        # Look for `X-Stream-Mode` in actual response header assignments
        # (not just comments). Pattern: `"X-Stream-Mode": "..."`.
        header_in_response = bool(
            re.search(
                r'[\'"]X-Stream-Mode[\'"]\s*:\s*[\'"][^\'"]+[\'"]',
                src,
            )
        )
        # Fallback: header is set via a headers object literal in the
        # streaming response construction.
        if not header_in_response:
            header_in_response = bool(
                re.search(
                    r'headers\s*:\s*\{[^}]*[\'"]X-Stream-Mode[\'"]',
                    src,
                    re.DOTALL,
                )
            )
        assert header_in_response, (
            "FAIL: X-Stream-Mode header not set in streaming response headers "
            "— clients have no way to detect the buffered mode"
        )
        print("PASS [3/4]: X-Stream-Mode header set in streaming response (detectable)")

    # -------------------------------------------------------------------------
    # TEST 4 (runtime) — boot the bridge (no API key needed for OPTIONS or
    # for /api/tags). We can't easily test the streaming response without a
    # real OpenRouter key, but we can verify the bridge boots cleanly with
    # the streaming-related changes (no syntax errors / no broken imports).
    # -------------------------------------------------------------------------
    print("\n--- Runtime boot test (DNA #2 reality) ---")
    env = dict(os.environ)
    env["ZAI_BRIDGE_PORT"] = "11445"
    env["OPENROUTER_API_KEY"] = ""  # no real key needed for boot
    env["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000"

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
    try:
        # S17: enforceable boot wait (reader thread) + reworded-banner pin —
        # commit 3f1690d changed the banner to "[scp-llm-bridge] listening
        # (host/port from config env)" (no more "listening on" literal).
        boot_log, listening_seen = _collect_boot_log(proc, timeout_s=5.0, trigger="listening")
        assert listening_seen, (
            f"FAIL: bridge did not boot cleanly (no 'listening' within 5s) — boot_log: {boot_log!r}"
        )
        # GET /api/tags should work without an API key.
        conn = http.client.HTTPConnection("127.0.0.1", 11445, timeout=3)
        conn.request("GET", "/api/tags")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
        conn.close()
        assert resp.status == 200, f"FAIL: GET /api/tags returned {resp.status}"
        assert "models" in body, f"FAIL: /api/tags body missing 'models': {body[:200]!r}"
        print("PASS [4/4]: bridge boots cleanly + serves /api/tags (no syntax/import errors)")
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

    print("\n✓ Reality test 4-d-023 PASSED (4/4 assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
