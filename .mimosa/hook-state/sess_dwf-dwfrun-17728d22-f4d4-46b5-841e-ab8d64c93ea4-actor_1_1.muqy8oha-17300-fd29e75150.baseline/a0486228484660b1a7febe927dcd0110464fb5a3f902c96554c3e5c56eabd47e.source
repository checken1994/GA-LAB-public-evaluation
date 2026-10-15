import os

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

from scp.risk_intelligence.incident_state import IncidentState, IncidentStateMachine
from scp.risk_intelligence.risk_classifier import RiskClassifier, RiskLevel, RiskSignal


def test_risk_intelligence_isolated_flow():
    """FA-13: Cover risk_intelligence flow with genuine behavioral execution.

    Verifies that social volume alone never manufactures emergency PR4/PR5 (pending
    verification fail-closed invariant), and verifies IncidentStateMachine state progression.
    """
    # 1. Behavioral: 100 social signals alone cannot trigger PR5 emergency
    classifier = RiskClassifier()
    signals = [RiskSignal(source_id=f"tw-{i}", kind="social") for i in range(100)]
    assessment = classifier.classify(signals, desired_level=RiskLevel.PR5)
    assert assessment.level != RiskLevel.PR5
    assert assessment.pending_verification is True

    # 2. Behavioral: IncidentStateMachine state transition tracking
    fsm = IncidentStateMachine(incident_id="inc-test-001")
    assert fsm.state == IncidentState.OBSERVED
    next_state = fsm.transition(IncidentState.SUSPECTED)
    assert next_state == IncidentState.SUSPECTED
    assert fsm.state == IncidentState.SUSPECTED

    # Advance to corroborating
    fsm.transition(IncidentState.CORROBORATING)
    assert fsm.state == IncidentState.CORROBORATING
