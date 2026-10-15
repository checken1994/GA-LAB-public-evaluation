#!/usr/bin/env python3
"""Reality test for Fix 4-d-012: scheduler fire-and-forget (no 120s timeout).

DNA #9 (No harm — duplicate side effects) + #17 (Hành động khi chưa biết hết)
+ #19 (observation gap — scheduler doesn't know the audit continued).

Before fix:
  - SCP_FETCH_TIMEOUT_MS = 120_000 (2 min).
  - SCP audits can run 5-10 minutes.
  - On 120s timeout: client-side fetch aborts → state.running cleared →
    next cron tick (5 min later) fires another triggerAudit → SCP receives
    a SECOND concurrent audit POST → race on deep_audit_results.jsonl,
    duplicate LLM calls, conflicting rollback tokens.

After fix (accepted alternatives per spec):
  - EITHER: timeout >= 600_000 (10 min) so the scheduler stays "busy"
    during the audit (next cron tick can't fire while previous is running).
  - OR: fire-and-forget pattern (POST without awaiting response body)
    + cooldown so the next cron tick waits.

This implementation chose: timeout raised to 600_000 (10 min) + comment
explaining why fire-and-forget was rejected (loses audit summary, SCP's
endpoint is synchronous, no 202 + job ID available without SCP-side changes).

Tier-A (static-source) reality test.
"""
import re
import sys
from pathlib import Path

SOURCE_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/mini-services/loop-scheduler/index.ts'
)


def main() -> int:
    assert SOURCE_PATH.exists(), (
        f"FAIL: loop-scheduler/index.ts not found at {SOURCE_PATH}"
    )
    src = SOURCE_PATH.read_text(encoding="utf-8")
    print(f"PASS [1/4]: file exists ({SOURCE_PATH.name})")

    # -------------------------------------------------------------------------
    # TEST 2 — the old 120_000 timeout literal MUST be gone from code.
    # We check the code section (excluding comments) because the explanatory
    # comment may still mention "120_000" as historical context.
    # -------------------------------------------------------------------------
    code_lines = [
        line
        for line in src.split("\n")
        if not line.strip().startswith("//")
        and not line.strip().startswith("*")
    ]
    code_section = "\n".join(code_lines)
    # Look for `SCP_FETCH_TIMEOUT_MS = 120_000` (assignment) OR
    # `AbortSignal.timeout(120_000)` (usage) in code.
    has_120s_timeout = bool(
        re.search(r"SCP_FETCH_TIMEOUT_MS\s*=\s*120[_\d]*\b", code_section)
    ) or bool(
        re.search(r"AbortSignal\.timeout\s*\(\s*120[_\d]*\s*\)", code_section)
    )
    assert not has_120s_timeout, (
        "FAIL: SCP_FETCH_TIMEOUT_MS is still 120s (or 120_000 literal still "
        "in code) — duplicate-trigger bug from 4-d-012 persists"
    )
    print("PASS [2/4]: no 120s timeout literal in code (old value removed)")

    # -------------------------------------------------------------------------
    # TEST 3 — EITHER:
    #   (a) SCP_FETCH_TIMEOUT_MS >= 600_000 (10 min, the spec's accepted
    #       "increase timeout" alternative), OR
    #   (b) fire-and-forget pattern: the audit fetch is NOT awaited (the
    #       scheduler doesn't hold the request open).
    # -------------------------------------------------------------------------
    # Pattern (a): look for SCP_FETCH_TIMEOUT_MS = <number> in code, parse it.
    timeout_match = re.search(
        r"SCP_FETCH_TIMEOUT_MS\s*=\s*(\d[\d_]*)",
        code_section,
    )
    fire_and_forget_markers = (
        "fire-and-forget" in src.lower()
        or "fire_and_forget" in src.lower()
        or "cooldown_until" in code_section
        or "audit_triggered" in code_section
    )
    if timeout_match:
        timeout_val = int(timeout_match.group(1).replace("_", ""))
        assert timeout_val >= 600_000 or fire_and_forget_markers, (
            f"FAIL: SCP_FETCH_TIMEOUT_MS = {timeout_val} (< 600_000) AND no "
            f"fire-and-forget pattern — duplicate-trigger bug persists"
        )
        if timeout_val >= 600_000:
            print(
                f"PASS [3/4]: SCP_FETCH_TIMEOUT_MS = {timeout_val} ms "
                f"(>= 600_000, covers worst-case 10-min audit)"
            )
        else:
            print(
                f"PASS [3/4]: fire-and-forget pattern active "
                f"(timeout={timeout_val}, cooldown marker present)"
            )
    else:
        # No explicit SCP_FETCH_TIMEOUT_MS const — must be fire-and-forget.
        assert fire_and_forget_markers, (
            "FAIL: no SCP_FETCH_TIMEOUT_MS const AND no fire-and-forget "
            "markers — neither accepted alternative is present"
        )
        print("PASS [3/4]: fire-and-forget pattern (no SCP_FETCH_TIMEOUT_MS)")

    # -------------------------------------------------------------------------
    # TEST 4 — the SCP fetch must use the timeout (if approach (a)) OR
    # must NOT hold the request open (if approach (b)). We check that the
    # SCP_AUDIT_URL fetch is wrapped with a timeout signal OR not awaited.
    # -------------------------------------------------------------------------
    # Approach (a) verification: SCP_AUDIT_URL fetch uses AbortSignal.timeout
    # with the SCP_FETCH_TIMEOUT_MS variable (or fetchWithTimeout).
    uses_timeout_on_audit_fetch = bool(
        re.search(
            r"fetch\s*\(\s*SCP_AUDIT_URL.*?AbortSignal\.timeout\s*\(\s*SCP_FETCH_TIMEOUT_MS\s*\)",
            src,
            re.DOTALL,
        )
    ) or bool(
        re.search(
            r"fetchWithTimeout\s*\(\s*SCP_AUDIT_URL",
            src,
        )
    )
    # Approach (b) verification: fire-and-forget — the SCP fetch promise is
    # NOT awaited (void fetch(...) pattern) OR the triggerAudit body
    # explicitly skips awaiting.
    not_awaited = bool(
        re.search(r"void\s+fetch\s*\(\s*SCP_AUDIT_URL", src)
    ) or bool(
        # .then(...) without await
        re.search(
            r"fetch\s*\(\s*SCP_AUDIT_URL.*?\)\.then\s*\(",
            src,
            re.DOTALL,
        )
    )
    assert uses_timeout_on_audit_fetch or not_awaited, (
        "FAIL: SCP_AUDIT_URL fetch is neither wrapped with a timeout signal "
        "nor fired-and-forgotten — old 120s timeout behavior persists"
    )
    if uses_timeout_on_audit_fetch:
        print("PASS [4/4]: SCP audit fetch uses timeout signal (approach a)")
    else:
        print("PASS [4/4]: SCP audit fetch is fire-and-forget (approach b)")

    print("\n✓ Reality test 4-d-012 PASSED (4/4 assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
