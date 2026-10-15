from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
RC = WORKFLOWS / "scp-rc-promotion.yml"
PRE_RC = WORKFLOWS / "scp-release-gate.yml"
BASELINE = WORKFLOWS / "ci.yml"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing workflow: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def test_rc_promotion_is_the_only_workflow_allowed_to_emit_release_verdicts() -> None:
    rc = _read(RC)
    pre_rc = _read(PRE_RC)
    baseline = _read(BASELINE)
    assert "'verdict': 'RC_DONE'" in rc
    assert "'verdict': 'CUSTOMER_HANDOFF_PASS'" in rc
    for path, text in ((PRE_RC, pre_rc), (BASELINE, baseline)):
        assert "RC_DONE" not in text, f"{path.name} must not emit/fake RC authority"
        assert "CUSTOMER_HANDOFF_PASS" not in text, f"{path.name} must not emit/fake customer-handoff authority"


def test_non_authoritative_workflows_are_named_and_scoped_truthfully() -> None:
    pre_rc = _read(PRE_RC)
    baseline = _read(BASELINE)
    assert pre_rc.startswith("name: SCP Pre-RC Verification (Non-Authoritative)\n")
    assert baseline.startswith("name: SCP CI Baseline (Non-Authoritative)\n")
    assert "verify_snapshot_manifest.py reports/manifests_202608/ROOT_SCP_SNAPSHOT_MANIFEST_20260826.json" not in pre_rc
    assert "scp-rc-promotion.yml" in pre_rc
    assert "scp-rc-promotion.yml" in baseline


def test_authoritative_workflow_keeps_human_frozen_sha_and_immutable_main_lineage_guards() -> None:
    rc = _read(RC)
    for marker in (
        "approve_main_merge:",
        "inputs.approve_main_merge == true",
        'test "$CURRENT" = "$FROZEN_SHA"',
        'test "$PR_HEAD" = "$FROZEN_SHA"',
        '-f sha="$FROZEN_SHA"',
        "main-lineage-authority:",
        "needs.main-lineage-authority.result == 'success'",
        "'fresh_full_system_verification': True",
    ):
        assert marker in rc, f"authoritative release workflow lost guard: {marker}"
    assert "INTEGRATION_SHA=\"$(gh api" not in rc, (
        "post-merge lineage must not depend on a mutable integration branch tip"
    )
