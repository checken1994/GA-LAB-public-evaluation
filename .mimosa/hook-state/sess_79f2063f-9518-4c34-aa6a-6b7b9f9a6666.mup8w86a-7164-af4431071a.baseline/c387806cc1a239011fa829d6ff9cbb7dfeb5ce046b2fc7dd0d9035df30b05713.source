"""[EVIDENCE-FLOW-FIX] Regression tests — ctx.pairs / ctx evidence must flow.

Root cause (autofix_mixin.py): ``locals().get("ctx.pairs", [])`` (and the
"ctx.before_hash" / "ctx.after_hash" / "ctx.rollback_token" /
"ctx.reality_test_result" variants) ALWAYS returned the default because
locals() keys never contain dots. Consequences before the fix:

  - ctx.sim_patched stayed None -> the IMP-14 confidence ranker and the
    IMP-23 shadow canary NEVER ran;
  - every "fixed" result dict reported before_hash/after_hash = "n/a" and
    reality_test_result = "skipped" even when the real evidence existed.

The tests below drive the REAL engine._auto_fix flow (same mocking pattern
as test_autofix_shadow_rollback.py::test_autofix_end_to_end_rollback_on_verify_failure)
with a SEARCH/REPLACE patch so ctx.pairs is genuinely populated, and assert
the ranker + canary execute and the result fields carry the real values.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from scp.autofix.classifier import BugReport
from scp.autofix.engine import AutoFixEngine


@pytest.fixture(autouse=True)
def deterministic_why_gate(monkeypatch):
    """Pin WHY gate to its deterministic layer (see test_autofix_shadow_rollback)."""
    monkeypatch.setenv("SCP_WHY_LLM_ENABLED", "0")


SUGGESTED_FIX = (
    "<<<<<<< SEARCH\n"
    "LIMIT = 1\n"
    "=======\n"
    "LIMIT = 2\n"
    ">>>>>>>"
)


def _make_bug(target) -> BugReport:
    return BugReport(
        file=str(target),
        line=1,
        bug_type="BareExceptPass",
        description="constant needs a controlled bump",
        suggested_fix=SUGGESTED_FIX,
        tier=2,
    )


def test_pairs_flow_to_ranker_canary_and_result_fields(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    target = tmp_path / "cfg_mod.py"
    # [CANARY-FIXTURE-FIX] The engine reads pre_fix_content with newline=""
    # (raw bytes preserved — deliberate CRLF-safety fix at autofix_mixin.py
    # ~line 355). A default write_text() on Windows hits disk as CRLF, so the
    # mocked pipeline produced 'LIMIT = 2\r\n' and the fake canary's LF assert
    # raised AssertionError (canary fail-closed → patch blocked). Write with
    # newline="" so pre/post content is genuinely consistent.
    target.write_text("LIMIT = 1\n", encoding="utf-8", newline="")
    engine = AutoFixEngine(data_dir=str(data_dir))
    bug = _make_bug(target)

    rank_calls = []
    canary_calls = []

    def fake_make_fix(**kwargs):
        cand = SimpleNamespace(confidence=0.9, disposition="auto_apply")
        for k, v in kwargs.items():
            setattr(cand, k, v)
        return cand

    def fake_best_fix(candidates, bug_type=""):
        rank_calls.append(bug_type)
        assert candidates, "ranker must receive the simulated candidate"
        assert candidates[0].patched_source == "LIMIT = 2\n"
        return candidates[0]

    def fake_shadow_compare(target_file, fix, canary_suite):
        canary_calls.append(fix)
        assert fix.patched_source == "LIMIT = 2\n", f"canary got {getattr(fix, 'patched_source', None)!r}"
        return MagicMock(
            passed=True, reason="", diffs=[], tests_run=3, flagged_for_review=False,
        )

    rtv = MagicMock()
    rtv.ok = True
    rtv.reason = "OK  3 inputs tested, 0 violations"
    rtv.inputs_tested = 3
    rtv.violations = []

    def fake_apply_fix(fp, fix):
        # newline="": mirror the engine's own raw-bytes write convention so
        # the post-patch file content matches the simulated patched_source.
        fp.write_text("LIMIT = 2\n", encoding="utf-8", newline="")
        return True

    with patch("scp.autofix.confidence_ranker.make_fix", side_effect=fake_make_fix), \
         patch("scp.autofix.confidence_ranker.best_fix", side_effect=fake_best_fix), \
         patch("scp.autofix.runner_phases.shadow_canary.shadow_apply_and_compare",
               side_effect=fake_shadow_compare), \
         patch("scp.autofix.realtime_verifier.verify_patch_realtime", return_value=rtv), \
         patch("scp.autofix.runner_phases.post_fix_verify.run_full_post_fix_verify",
               return_value={"ok": True, "phases": {}, "rollback": False,
                             "escalate_to_tier3": False, "reason": "mocked"}), \
         patch("scp.core.code_evolution_agent.CodeEvolutionAgent._apply_fix",
               side_effect=fake_apply_fix), \
         patch.object(engine, "_verify_fix", return_value=(True, "fix verified OK (mock)")):
        result = engine._auto_fix(bug, report=False)

    assert result["action"] == "fixed", result

    # [FIX] ctx.pairs flows: confidence ranker ran on the simulated source.
    assert rank_calls, (
        "confidence ranker never ran — locals().get('ctx.pairs') returned [] "
        "and the IMP-14 gate stayed vacuous"
    )

    # [FIX] ctx.pairs flows: shadow canary ran on the simulated source.
    assert canary_calls, (
        "shadow canary never ran — ctx.sim_patched stayed None because "
        "locals().get('ctx.pairs') returned []"
    )

    # [FIX] Result dict carries the REAL evidence, not the dotted-key defaults.
    assert result["before_hash"] != "n/a", result
    assert result["after_hash"] != "n/a", result
    assert result["reality_test_result"] == "pass", result
