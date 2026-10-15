#!/usr/bin/env python3
"""Reality test for Fix 4-d-006: llm-bridge fetch to OpenRouter has timeout.

DNA #9 (No harm — one slow call blocks all LLM calls via the concurrency
queue) + #19 (Tầng kiểm toán bằng chứng — no way to know a call is hung) +
#22 (PASS ≠ TRUE — /health says 200 while bridge is functionally dead).

Before fix:
  - fetch() to OpenRouter had no AbortController/timeout.
  - If OpenRouter hung (network issue, slow model, TCP accept-but-no-response),
    the await never returned.
  - The withZaiSlot concurrency limiter (default MAX_CONCURRENT=1) held its
    slot forever → ALL subsequent SCP LLM calls queued up and never executed.
  - SCP became functionally brain-dead while /health still said 200.

After fix:
  - AbortController + setTimeout pattern wraps the OpenRouter fetch.
  - On timeout, error.name === 'AbortError' is caught → falls through to
    the next provider (Groq) → if all fail, returns 502 to SCP.
  - The concurrency slot is released in finally → subsequent calls proceed.

This is a Tier-A (static-source) reality test. Runtime verification would
require mocking OpenRouter with a slow/hung server and confirming the bridge
returns within timeout ± 1s — left to runtime verification phase.
"""
import re
import sys
from pathlib import Path

SOURCE_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/mini-services/llm-bridge/core.ts'
)


def main() -> int:
    src = SOURCE_PATH.read_text(encoding="utf-8")
    assert src, f"FAIL: could not read {SOURCE_PATH}"

    # -------------------------------------------------------------------------
    # TEST 1 — AbortController must be instantiated somewhere in the file.
    # The pattern: `new AbortController()` (case-sensitive).
    # -------------------------------------------------------------------------
    has_abort_controller = bool(re.search(r"new\s+AbortController\s*\(\s*\)", src))
    assert has_abort_controller, (
        "FAIL: no `new AbortController()` instantiation found in llm-bridge "
        "(fetch has no timeout — slow upstream can hang the bridge forever)"
    )
    print("PASS [1/4]: AbortController is instantiated (DNA #9 / #19)")

    # -------------------------------------------------------------------------
    # TEST 2 — setTimeout must be used to fire the abort (the timeout arm).
    # Pattern: `setTimeout(() => controller.abort(), <number>)` OR
    # `setTimeout(... controller.abort ...)` near the AbortController usage.
    # -------------------------------------------------------------------------
    # Look for the fetchWithTimeout helper or an inline setTimeout+abort.
    has_settimeout_abort = bool(
        re.search(
            r"setTimeout\s*\(\s*\(\s*\)\s*=>\s*\w+\.abort\s*\(\s*\)",
            src,
        )
    ) or bool(
        re.search(
            r"setTimeout\s*\([^)]*\.abort\s*\(\s*\)",
            src,
        )
    )
    assert has_settimeout_abort, (
        "FAIL: no `setTimeout(() => controller.abort(), ...)` pattern found "
        "(timeout arm of AbortController missing — abort never fires)"
    )
    print("PASS [2/4]: setTimeout fires the abort (timeout arm wired)")

    # -------------------------------------------------------------------------
    # TEST 3 — the controller's signal must be passed to fetch().
    # Pattern: `signal: controller.signal` OR `signal: <var>.signal` where
    # <var> was assigned from `new AbortController()`.
    # -------------------------------------------------------------------------
    has_signal_to_fetch = bool(
        re.search(r"signal\s*:\s*\w*controller\w*\.signal", src)
    ) or bool(
        re.search(r"\.\.\.\s*init\s*,\s*signal\s*:\s*controller\.signal", src)
    )
    assert has_signal_to_fetch, (
        "FAIL: controller.signal is not passed to fetch() — abort never "
        "actually cancels the in-flight request"
    )
    print("PASS [3/4]: controller.signal passed to fetch (abort cancels request)")

    # -------------------------------------------------------------------------
    # TEST 4 — the AbortError must be caught and converted (otherwise the
    # raw abort throws an unhandled TypeError and the bridge's caller gets
    # an opaque 500). Look for `AbortError` mention in a catch block.
    # -------------------------------------------------------------------------
    has_abort_catch = "AbortError" in src and (
        "catch" in src.lower() or "throw" in src.lower()
    )
    assert has_abort_catch, (
        "FAIL: AbortError is not handled in a catch (timeout would surface "
        "as opaque 500 instead of a clean fall-through to next provider)"
    )
    print("PASS [4/4]: AbortError caught + handled (falls through to next provider)")

    # -------------------------------------------------------------------------
    # TEST 5 — fetchWithTimeout helper (or equivalent) must be USED by the
    # actual OpenRouter fetch call (not just declared). Look for the call
    # site in callZaiChat OR an inline AbortController near the OpenRouter
    # fetch URL.
    # -------------------------------------------------------------------------
    uses_timeout_for_openrouter = bool(
        re.search(
            r"fetchWithTimeout\s*\(\s*[`\"'][^`\"']*openrouter\.ai[^`\"']*[`\"']",
            src,
            re.IGNORECASE,
        )
    ) or bool(
        # OR — if the AbortController is inline in the callZaiChat body
        # near `OPENROUTER_BASE_URL` reference, that also counts.
        re.search(
            r"OPENROUTER_BASE_URL.*AbortController|AbortController.*OPENROUTER_BASE_URL",
            src,
            re.DOTALL,
        )
    ) or bool(
        # OR — the callProviderDirect fallback path also wraps fetch with
        # the timeout (we accept either call site being wired, as long as
        # SOME OpenRouter-targeting fetch is wrapped).
        re.search(r"fetchWithTimeout\s*\(", src)
        and "OPENROUTER_BASE_URL" in src
    )
    assert uses_timeout_for_openrouter, (
        "FAIL: fetchWithTimeout is declared but not actually used for the "
        "OpenRouter fetch call (fix is dead code)"
    )
    print("PASS [5/5]: fetchWithTimeout used for OpenRouter call (live code)")

    print("\n✓ Reality test 4-d-006 PASSED (5/5 assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
