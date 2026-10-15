import os

from scp.autofix.classifier import BugReport, BugTier
from scp.autofix.engine import AutoFixEngine

# ==============================================================================
# T07 - AUTOFIX BEHAVIORAL CONTRACT
# ==============================================================================
# Focus: Testing real behavior of the AutoFix Engine, especially Tier 3 guards
# and Catastrophic Forgetting/Relaxation prevention.
# ==============================================================================

def test_autofix_engine_refuses_to_relax_security(tmp_path):
    """
    Contract: AutoFixEngine must NEVER auto-approve a fix that relaxes security,
    even if the environment is configured to auto-approve Tier 3 bugs.
    This is the Catastrophic Forgetting Guard (S9) in practice.
    """
    os.environ["SCP_AUTO_APPROVE_TIER3"] = "1"
    try:
        engine = AutoFixEngine(str(tmp_path))
        
        # Create a bug report that attempts to relax a security policy
        bug = BugReport(
            file="scp/security/policy.py",
            line=10,
            bug_type="HardcodedTimeout",
            description="Timeout is too short",
            suggested_fix="Increase timeout",
            tier=BugTier.TIER_3_PERMISSION
        )
        # Manually force the relaxation flag which the Classifier would normally set
        bug.is_relaxation = True
        
        # It MUST NOT be auto-approved
        assert engine._should_auto_approve_tier3(bug) is False, "AutoFixEngine allowed a security relaxation to bypass Tier 3 manual approval (Violates S9)!"
        
        # The process flow must request permission, not auto-fix
        result = engine.process_bug(bug)
        assert result["action"] in ("permission_requested", "skipped", "blocked")
        
    finally:
        if "SCP_AUTO_APPROVE_TIER3" in os.environ:
            del os.environ["SCP_AUTO_APPROVE_TIER3"]

def test_autofix_engine_bare_except_pass_cooldown(tmp_path):
    """
    Contract: AutoFixEngine must recognize known bad patch patterns from the LLM
    (e.g., introducing BareExceptPass) and refuse to auto-approve them, forcing human review.
    """
    os.environ["SCP_AUTO_APPROVE_TIER3"] = "1"
    try:
        engine = AutoFixEngine(str(tmp_path))
        
        bug = BugReport(
            file="scp/utils.py",
            line=20,
            bug_type="BareExceptPass", # This is explicitly blocked in _should_auto_approve_tier3
            description="Empty except block",
            suggested_fix="Log error",
            tier=BugTier.TIER_3_PERMISSION
        )
        
        assert engine._should_auto_approve_tier3(bug) is False, "AutoFixEngine auto-approved a BareExceptPass fix, which is known to cause rollbacks."
        
    finally:
        if "SCP_AUTO_APPROVE_TIER3" in os.environ:
            del os.environ["SCP_AUTO_APPROVE_TIER3"]
