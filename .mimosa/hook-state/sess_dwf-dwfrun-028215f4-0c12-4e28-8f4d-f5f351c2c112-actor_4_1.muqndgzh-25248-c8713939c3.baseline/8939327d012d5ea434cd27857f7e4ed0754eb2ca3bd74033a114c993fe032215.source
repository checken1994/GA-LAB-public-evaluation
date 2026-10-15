"""[IMP-15 FIX] Regression tests — REAL AST-based semantic-equivalence oracle.

BEFORE the fix:
  - verify_semantic_equiv() was a stub returning ok=True unconditionally
    (phase IMP-15 vacuous — any patch was "semantically equivalent");
  - the phase caller built _V3_SE_BugLoc(function_name=...) which raised
    TypeError (file_path/line required) that the phase's except swallowed
    into "semantic equivalence failed" -> spurious rollback whenever a
    backup + method_name existed;
  - the no-backup branch recorded ok=True "SKIPPED" — a skipped phase
    counted as a pass (manufactured green, DNA #22).
"""

from scp.autofix.runner_phases.post_fix_verify import run_full_post_fix_verify
from scp.autofix.runner_phases.semantic_equiv import BugLocation, verify_semantic_equiv

ORIG = 'def target_fn(x):\n    """Docs."""\n    return x + 1\n'
LOC = BugLocation(file_path="x.py", line=1, function_name="target_fn")


class TestSemanticEquivOracle:
    def test_equivalent_patch_is_ok(self):
        # Formatting + comments + docstring placement changes only.
        reformatted = (
            'def target_fn(x):\n'
            '    # a moved comment\n'
            '    """Docs."""\n'
            '    return x + 1\n'
        )
        result = verify_semantic_equiv(ORIG, reformatted, LOC)
        assert result.ok is True, result.reason
        assert result.equivalent is True
        assert result.critical is False
        assert result.over_broad is False

    def test_behavior_changing_patch_is_not_ok(self):
        changed = 'def target_fn(x):\n    """Docs."""\n    return x + 2\n'
        result = verify_semantic_equiv(ORIG, changed, LOC)
        assert result.ok is False
        assert result.equivalent is False
        assert "AST changed" in result.reason
        assert result.changed_statements, "diff reason must list what changed"

    def test_deleted_target_function_is_critical(self):
        gone = 'def other_fn(y):\n    return y\n'
        result = verify_semantic_equiv(ORIG, gone, LOC)
        assert result.ok is False
        assert result.critical is True

    def test_change_outside_target_function_is_over_broad(self):
        over_broad = ORIG + '\n\ndef helper_added():\n    return 99\n'
        result = verify_semantic_equiv(ORIG, over_broad, LOC)
        assert result.ok is False
        assert result.over_broad is True
        assert result.critical is False

    def test_unanchorable_target_fails_closed(self):
        result = verify_semantic_equiv(ORIG, ORIG, BugLocation(file_path="x.py", line=1, function_name="no_such_fn"))
        assert result.ok is False
        assert result.equivalent is False

    def test_parse_error_fails_closed(self):
        result = verify_semantic_equiv(ORIG, "def broken(:\n", LOC)
        assert result.ok is False


def _run_semantic_only(file_path: str, method_name):
    return run_full_post_fix_verify(
        bug_id=f"regression:{file_path}",
        file_path=file_path,
        method_name=method_name,
        run_vulture=False,
        run_import=False,
        run_hypothesis=False,
        run_reality_exercise=False,
        run_completeness=False,
        run_evidence_replay=False,
    )


class TestSemanticEquivPhase:
    def test_no_backup_is_skipped_not_implemented_and_not_counted_as_pass(self, tmp_path):
        target = tmp_path / "solo_mod.py"
        target.write_text(ORIG, encoding="utf-8")
        result = _run_semantic_only(str(target), "target_fn")

        phase = result["phases"]["semantic_equiv"]
        # A skipped phase is never presented as a pass.
        assert phase["status"] == "SKIPPED_NOT_IMPLEMENTED"
        assert phase["ok"] is False
        assert phase["skipped"] is True
        # ... and it is EXCLUDED from all_ok — it does not block the verdict.
        assert result["ok"] is True
        assert result["rollback"] is False

    def test_backup_with_changed_target_no_longer_spurious_typeerror_rollback(self, tmp_path):
        target = tmp_path / "mod2.py"
        target.write_text('def target_fn(x):\n    return x + 2\n', encoding="utf-8")
        # post_fix_verify / verify_mixin backup convention: <name>.py.tier3bak
        backup = tmp_path / "mod2.py.tier3bak"
        backup.write_text(ORIG, encoding="utf-8")

        result = _run_semantic_only(str(target), "target_fn")

        phase = result["phases"]["semantic_equiv"]
        # BEFORE: TypeError -> "semantic equivalence failed" -> ok False ->
        # all_ok False -> overall verification failed (spurious rollback path).
        assert phase["reason"] != "semantic equivalence failed"
        assert "AST changed" in phase["reason"]
        assert phase["critical"] is False
        assert phase["over_broad"] is False
        # A target-function change IS the fix itself — phase verdict holds.
        assert result["ok"] is True
        assert result["rollback"] is False

    def test_backup_with_deleted_target_rolls_back(self, tmp_path):
        target = tmp_path / "mod3.py"
        target.write_text('def other_fn(y):\n    return y\n', encoding="utf-8")
        backup = tmp_path / "mod3.py.tier3bak"
        backup.write_text(ORIG, encoding="utf-8")

        result = _run_semantic_only(str(target), "target_fn")

        phase = result["phases"]["semantic_equiv"]
        assert phase["critical"] is True
        assert result["ok"] is False
