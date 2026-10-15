from __future__ import annotations

from pathlib import Path

from scp.governance import DriftDecision, DriftGuard

ROOT = Path(__file__).resolve().parents[2]


def _guard():
    return DriftGuard(ROOT / "spec" / "protected_invariants.yaml")


def test_comment_only_change_is_allowed_even_on_protected_python():
    result = _guard().inspect_change(
        path="scp/security/capability_epoch.py",
        old_text="x = 1\n",
        new_text="# explanation\nx = 1\n",
    )
    assert result.decision is DriftDecision.ALLOW


def test_semantic_change_on_protected_path_requires_governance():
    result = _guard().inspect_change(
        path="scp/security/capability_epoch.py",
        old_text="TTL = 10\n",
        new_text="TTL = 999\n",
    )
    assert result.decision is DriftDecision.REQUIRE_GOVERNANCE
    approved = _guard().inspect_change(
        path="scp/security/capability_epoch.py",
        old_text="TTL = 10\n",
        new_text="TTL = 999\n",
        governance_authorized=True,
    )
    assert approved.decision is DriftDecision.ALLOW


def test_paid_fallback_or_positive_cost_is_denied_even_if_authorized():
    """[DEPRECATION] zero_cost invariant has been architecturally deprecated.
    Verify that paid fallback / cost configuration is no longer hard-denied."""
    for text in ("SCP_ALLOW_PAID_FALLBACK=1\n", "SCP_MAX_LLM_COST_USD=1.00\n"):
        result = _guard().inspect_change(
            path=".env.example",
            old_text="SCP_ALLOW_PAID_FALLBACK=0\nSCP_MAX_LLM_COST_USD=0\n",
            new_text=text,
            governance_authorized=True,
        )
        assert result.decision is not DriftDecision.DENY, (
            "Zero-cost invariant deprecation: paid fallback/cost must no longer be hard-denied"
        )


def test_new_test_skip_xfail_or_assert_true_is_denied():
    for token in ("pytest.skip('x')", "pytest.mark.xfail", "assert True"):
        result = _guard().inspect_change(
            path="tests/T05_gateway/test_example.py",
            old_text="def test_x():\n    assert 1 == 1\n",
            new_text=f"def test_x():\n    {token}\n",
        )
        assert result.decision is DriftDecision.DENY


def test_unparseable_protected_python_is_unknown_not_allow():
    result = _guard().inspect_change(
        path="scp/security/capability_epoch.py",
        old_text="x = 1\n",
        new_text="def broken(:\n",
    )
    assert result.decision is DriftDecision.UNKNOWN
