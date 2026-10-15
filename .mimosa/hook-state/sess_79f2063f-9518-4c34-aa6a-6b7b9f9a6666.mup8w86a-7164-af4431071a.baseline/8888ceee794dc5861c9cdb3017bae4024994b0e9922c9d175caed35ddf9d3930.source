"""T11 Release Gate - Edge CE-S10-04: Release-grade external alert routing & evidence binding.

Evidence level: C / Release verification
Authority path: [RiskAuthority, EvidenceBundleAuthority, HumanComprehension, HumanAuthority, ExternalAuthorityConnector]
Covered capabilities:
  - risk.external_alert
  - risk.early_warning
Gates: T03, T09, T11
Must not effect: [automatic_external_broadcast]
"""
from __future__ import annotations

from scp.risk_intelligence.alert_router import (
    DEFAULT_ROUTES,
    FORBIDDEN_BROADCAST_OPERATIONS,
    AlertRouter,
)
from scp.risk_intelligence.evidence_bundle import EmergencyEvidenceBundle


def test_ce_s10_04_release_default_routes_contain_all_critical_risk_types() -> None:
    """Verifies that release defaults cover all standardized risk categories

    and route strictly to designated professional bodies rather than public endpoints.
    """
    expected_categories = {"CYBER", "HEALTH", "FIRE", "INFRASTRUCTURE", "INTERNAL"}
    assert expected_categories.issubset(set(DEFAULT_ROUTES.keys())), (
        f"Missing critical risk routing categories: {expected_categories - set(DEFAULT_ROUTES.keys())}"
    )
    for category, target in DEFAULT_ROUTES.items():
        assert target in {
            "SOC",
            "HEALTH_AUTHORITY",
            "AUTHORIZED_EMERGENCY_CONTACT",
            "UTILITY_OPERATOR",
            "SCP_ADMIN",
        }, f"Unapproved release target for category {category}: {target}"


def test_ce_s10_04_release_enforces_fail_closed_on_unauthorized_external_channels() -> None:
    """Verifies release invariant: SCP never broadcasts externally without

    tamper-evident bundle provenance and explicit human authorization.
    """
    bundle = EmergencyEvidenceBundle(
        incident_id="INC-RELEASE-GATE-001",
        risk_type="INFRASTRUCTURE",
        level="PR5",
        independent_lineages=2,
        official_confirmation=True,
        claims=("Grid overload detected on sub-station 4",),
        source_hashes=("sha256:11223344556677889900aabbccddeeff",),
    )

    # 1. Unconfigured release connector yields BUNDLE_ONLY
    router = AlertRouter(channels={})
    res_unconf = router.route(bundle)
    assert res_unconf["decision"] == "BUNDLE_ONLY"
    assert res_unconf["deliveries"] == []

    # 2. Configured requiring approval yields WAITING_APPROVAL
    router_gov = AlertRouter(
        channels={"UTILITY_OPERATOR": {"configured": True, "requires_approval": True}}
    )
    res_gov = router_gov.route(bundle)
    assert res_gov["decision"] == "WAITING_APPROVAL"
    assert res_gov["deliveries"] == []

    # 3. Forbidden operations are permanently denied even if channel claimed pre-authorized
    router_preauth = AlertRouter(
        channels={
            "UTILITY_OPERATOR": {
                "configured": True,
                "requires_approval": False,
                "pre_authorized": True,
            }
        }
    )
    for forbidden_op in FORBIDDEN_BROADCAST_OPERATIONS:
        denied = router_preauth.route(bundle, requested_operation=forbidden_op)
        assert denied["decision"] == "DENY_FORBIDDEN_OPERATION"
        assert denied["deliveries"] == []

    # 4. Legitimate authorized dispatch yields bounded report with lineage preserved
    authorized = router_preauth.route(bundle, requested_operation="report_incident")
    assert authorized["decision"] == "SUBMITTED"
    assert authorized["target"] == "UTILITY_OPERATOR"
    assert len(authorized["deliveries"]) == 1
    assert authorized["deliveries"][0]["kind"] == "bounded_incident_report"
