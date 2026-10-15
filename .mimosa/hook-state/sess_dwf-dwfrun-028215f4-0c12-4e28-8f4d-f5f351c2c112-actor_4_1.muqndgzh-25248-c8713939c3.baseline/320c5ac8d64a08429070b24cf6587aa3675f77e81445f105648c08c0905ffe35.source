import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.autofix import BugClassifier, BugTier


def test_subsystem_autofix_importable():
    """AutoFix engine: verify bug classification and tier assignment."""
    classifier = BugClassifier()
    report = classifier.classify(
        file="core/sample.py",
        line=42,
        bug_type="SyntaxError",
        description="unexpected EOF while parsing",
        suggested_fix="pass",
    )
    assert report is not None
    assert report.file == "core/sample.py"
    assert report.line == 42
    assert report.tier in {
        BugTier.TIER_1_AUTO_FIX,
        BugTier.TIER_2_AUTO_FIX_LOG,
        BugTier.TIER_3_PERMISSION,
        BugTier.TIER_4_ATTACK_MODE,
    }


def test_subsystem_autofix_tier_hierarchy():
    """Verify BugTier values form valid numerical escalation tiers."""
    tiers = [t.value for t in BugTier]
    assert sorted(tiers) == [1, 2, 3, 4]
