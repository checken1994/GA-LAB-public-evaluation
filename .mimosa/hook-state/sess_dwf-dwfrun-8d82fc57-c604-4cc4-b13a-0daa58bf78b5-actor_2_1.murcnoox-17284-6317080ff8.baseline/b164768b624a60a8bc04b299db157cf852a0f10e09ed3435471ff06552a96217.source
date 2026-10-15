"""[ZONE-FIX 2026-09-26] Regression — post-fix Phase E (semantic equivalence)
must read the pre-fix source from the ShadowSnapshot manifest (or buggy_source)
instead of only dead .tier3bak/.audit_fix_backup files.

BEFORE the fix: the engine stopped writing in-tree backups (shadow snapshots
now), so Phase E reported SKIPPED_NOT_IMPLEMENTED on every run — a fail-open
skip of the over_broad/critical oracle. Probe-verified with a real
shadow-snapshot transaction (manifest.json + backup_file): the phase still
skipped. AFTER: discovery mirrors verify_mixin._find_pre_patch_backup.
"""
from __future__ import annotations

import json

from scp.autofix.runner_phases.post_fix_verify import run_full_post_fix_verify

BUGGY = '''def compute(a, b):
    if a is None:
        a = 0
    return a + b
'''

FIXED_OVER_BROAD = '''def compute(a, b):
    if a is None:
        a = 0
    return a + b


def unrelated_refactor(x):
    return [i for i in range(x) if i % 2 == 0]
'''

FIXED_EQUIVALENT_LOGIC = '''def compute(a, b):
    # comment-only change inside the target function
    if a is None:
        a = 0
    return a + b
'''


def _run_phase_only(target, method="compute"):
    return run_full_post_fix_verify(
        bug_id="zonefix-test",
        file_path=str(target),
        method_name=method,
        run_vulture=False,
        run_import=False,
        run_hypothesis=False,
        run_reality_exercise=False,
        run_completeness=False,
        run_evidence_replay=False,
    )


def test_phase_e_runs_from_shadow_snapshot_and_flags_over_broad(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from scp.autofix.shadow_snapshot import get_shadow_snapshot_manager

    target = tmp_path / "probe_target.py"
    target.write_text(BUGGY, encoding="utf-8")

    mgr = get_shadow_snapshot_manager()
    tx_id = mgr.begin([target], bug_id="zonefix-test")
    manifest = json.loads(
        (mgr.active_dir / tx_id / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["target_files"][0]["backup_file"], "test setup: no backup recorded"

    target.write_text(FIXED_OVER_BROAD, encoding="utf-8")

    result = _run_phase_only(target)
    phase = result.get("phases", {}).get("semantic_equiv", {})
    assert not phase.get("skipped"), (
        f"Phase E skipped despite a live shadow-snapshot backup: {phase}"
    )
    assert phase.get("over_broad") is True, (
        "Phase E did not flag the over-broad change from the shadow backup"
    )
    assert result.get("ok") is not True


def test_phase_e_falls_back_to_buggy_source_parameter(tmp_path):
    target = tmp_path / "no_shadow_target.py"
    target.write_text(FIXED_OVER_BROAD, encoding="utf-8")

    result = run_full_post_fix_verify(
        bug_id="zonefix-test",
        file_path=str(target),
        method_name="compute",
        run_vulture=False,
        run_import=False,
        run_hypothesis=False,
        run_reality_exercise=False,
        run_completeness=False,
        run_evidence_replay=False,
        buggy_source=BUGGY,
    )
    phase = result.get("phases", {}).get("semantic_equiv", {})
    assert not phase.get("skipped"), f"buggy_source fallback ignored: {phase}"
    assert phase.get("over_broad") is True


def test_phase_e_skips_only_when_no_pre_fix_source_exists(tmp_path):
    target = tmp_path / "orphan_target.py"
    target.write_text(FIXED_OVER_BROAD, encoding="utf-8")

    result = _run_phase_only(target)
    phase = result.get("phases", {}).get("semantic_equiv", {})
    assert phase.get("skipped") is True
    assert phase.get("ok") is False
    assert "SKIPPED_NOT_IMPLEMENTED" in phase.get("status", "")
