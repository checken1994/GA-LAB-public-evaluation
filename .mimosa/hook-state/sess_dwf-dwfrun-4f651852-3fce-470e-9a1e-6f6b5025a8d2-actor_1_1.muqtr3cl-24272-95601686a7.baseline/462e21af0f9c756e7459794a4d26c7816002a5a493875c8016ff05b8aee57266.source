#!/usr/bin/env python3
"""Reality test for Fix 4-d-011: scheduler probes LLM bridge before SCP audit.

DNA #19 (Tầng kiểm toán bằng chứng — observation gap closed) + #2 (vòng lặp
khép kín — LLM step now visible to scheduler) + #22 (PASS ≠ TRUE).

Before fix:
  - Scheduler only probed SCP /health. If SCP process was alive but the
    LLM bridge (port 11434) was down (or OpenRouter was 429'd), every LLM
    call inside the audit failed → UNKNOWN verdicts for every question.
  - SCP still returned 200 with audit_complete:true → scheduler logged
    status: "ok". Dashboard showed "0 found · 0 fixed" → "all clear" lie.

After fix:
  - Scheduler probes LLM bridge /api/tags BEFORE triggering the audit.
  - If bridge is unreachable, logs status: "bridge_offline" + SKIPS the
    audit call — saves a full cycle of wasted LLM calls.

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
    print(f"PASS [1/5]: file exists ({SOURCE_PATH.name})")

    # -------------------------------------------------------------------------
    # TEST 2 — must reference port 11434 (the LLM bridge port) OR the
    # /api/tags endpoint OR LLM_BRIDGE_URL env var. At least one of these
    # signals that the scheduler is configured to probe the bridge.
    # -------------------------------------------------------------------------
    has_bridge_ref = (
        "11434" in src
        or "/api/tags" in src
        or "LLM_BRIDGE_URL" in src
        or "LLM_BRIDGE_TAGS_URL" in src
    )
    assert has_bridge_ref, (
        "FAIL: no reference to LLM bridge port (11434), /api/tags endpoint, "
        "or LLM_BRIDGE_URL env var — scheduler doesn't know where the bridge is"
    )
    print("PASS [2/5]: references LLM bridge (11434 / /api/tags / LLM_BRIDGE_URL)")

    # -------------------------------------------------------------------------
    # TEST 3 — must have a function that probes the bridge (e.g.
    # checkLlmBridgeLiveness, checkBridgeOnline, pingLlmBridge). Look for
    # an `async function` whose name contains 'bridge' or 'llm' or 'tags'.
    # -------------------------------------------------------------------------
    has_bridge_probe_fn = bool(
        re.search(
            r"async\s+function\s+\w*(?:bridge|llm|tags)\w*\s*\([^)]*\)\s*:\s*Promise<boolean>",
            src,
            re.IGNORECASE,
        )
    )
    assert has_bridge_probe_fn, (
        "FAIL: no `async function checkLlmBridgeLiveness()` (or similar) — "
        "scheduler has no bridge probe"
    )
    print("PASS [3/5]: bridge probe function declared (e.g. checkLlmBridgeLiveness)")

    # -------------------------------------------------------------------------
    # TEST 4 — the bridge probe must use fetch() against the bridge URL.
    # Pattern: a fetch of LLM_BRIDGE_TAGS_URL OR a fetch of an /api/tags URL
    # -------------------------------------------------------------------------
    fetches_bridge = bool(
        re.search(r"fetch\s*\(\s*LLM_BRIDGE_TAGS_URL", src)
    ) or bool(
        re.search(r"fetch\s*\(\s*[`\"'][^`\"']*/api/tags[`\"']", src)
    )
    assert fetches_bridge, (
        "FAIL: bridge probe function does not fetch /api/tags — probe is a no-op"
    )
    print("PASS [4/5]: bridge probe fetches /api/tags (live HTTP probe)")

    # -------------------------------------------------------------------------
    # TEST 5 — scheduler must SKIP the audit call when bridge is down.
    # Look for a "bridge_offline" status string (added to LoopRun.status
    # union) AND a return/break inside the "bridge not reachable" branch.
    # -------------------------------------------------------------------------
    has_bridge_offline_status = "bridge_offline" in src
    assert has_bridge_offline_status, (
        "FAIL: no 'bridge_offline' status string — bridge-down case is not "
        "distinguished from SCP-offline or normal-error"
    )
    # The "skip" logic: after detecting bridge down, scheduler must return
    # without calling SCP_AUDIT_URL. We accept either an explicit `return run`
    # inside the bridge-down branch, OR a `status: \"bridge_offline\"` field
    # on the run that gets returned (which short-circuits the audit call).
    # Look for the bridge-down branch: usually `if (!bridge_online)` or
    # `if (bridge_online === false)` followed by a return within ~600 chars.
    # Use a wide-window regex with DOTALL so the run-object literal's `}`
    # (which would terminate a [^}]* character class) doesn't break the match.
    bridge_skip_pattern = re.search(
        r"if\s*\(\s*!bridge_online\s*\)\s*\{(.{0,1200}?)return\s+run",
        src,
        re.DOTALL,
    )
    assert bridge_skip_pattern, (
        "FAIL: bridge-down branch does not skip the audit call (no "
        "`if (!bridge_online) { ... return run; }` pattern with "
        "status='bridge_offline')"
    )
    # And within that branch, status: "bridge_offline" must be set.
    branch_body = bridge_skip_pattern.group(1)
    assert "bridge_offline" in branch_body, (
        "FAIL: bridge-down branch returns run but doesn't set "
        "status='bridge_offline'"
    )
    print("PASS [5/5]: bridge-down branch skips audit + logs 'bridge_offline'")

    print("\n✓ Reality test 4-d-011 PASSED (5/5 assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
