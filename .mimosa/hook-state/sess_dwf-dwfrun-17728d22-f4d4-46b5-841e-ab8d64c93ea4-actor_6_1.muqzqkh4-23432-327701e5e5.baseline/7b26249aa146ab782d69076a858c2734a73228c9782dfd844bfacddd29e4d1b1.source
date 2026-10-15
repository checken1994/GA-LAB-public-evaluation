"""Alert Router (S10.6): SCP has NO default right to alert the public.

Routing: CYBER->SOC, HEALTH->health authority, FIRE->authorized emergency
contact, INFRASTRUCTURE->utility operator, INTERNAL->SCP admin.
Unconfigured connector  -> evidence bundle only.
Configured + approval   -> WAITING_APPROVAL.
Pre-authorized machine channel -> bounded incident report.

Public broadcast primitives (social posts, mass SMS, emergency calls) are
FORBIDDEN operations for the risk subsystem - enforced here and probed by T03.
"""
from __future__ import annotations

FORBIDDEN_BROADCAST_OPERATIONS = (
    "post_social",
    "mass_sms",
    "emergency_call",
    "public_alarm",
)

DEFAULT_ROUTES = {
    "CYBER": "SOC",
    "HEALTH": "HEALTH_AUTHORITY",
    "FIRE": "AUTHORIZED_EMERGENCY_CONTACT",
    "INFRASTRUCTURE": "UTILITY_OPERATOR",
    "INTERNAL": "SCP_ADMIN",
}


class AlertRouter:
    def __init__(self, channels: dict | None = None) -> None:
        # channels: {name: {"configured": bool, "requires_approval": bool,
        #                   "pre_authorized": bool}}
        self.channels = dict(channels or {})

    def route(self, bundle, *, requested_operation: str = "report_incident") -> dict:
        if requested_operation in FORBIDDEN_BROADCAST_OPERATIONS:
            return {
                "decision": "DENY_FORBIDDEN_OPERATION",
                "requested_operation": requested_operation,
                "reason": "public broadcast is a forbidden operation for the risk subsystem",
                "bundle_only": True,
                "deliveries": [],
            }
        risk_type = str(getattr(bundle, "risk_type", "INTERNAL") or "INTERNAL").upper()
        target = DEFAULT_ROUTES.get(risk_type, "SCP_ADMIN")
        channel = self.channels.get(target) or {}
        configured = bool(channel.get("configured"))
        requires_approval = bool(channel.get("requires_approval"))
        pre_authorized = bool(channel.get("pre_authorized"))

        if not configured:
            return {
                "decision": "BUNDLE_ONLY",
                "target": target,
                "bundle_id": getattr(bundle, "bundle_id", ""),
                "reason": "connector not configured - produce evidence bundle only",
                "deliveries": [],
            }
        if requires_approval and not pre_authorized:
            return {
                "decision": "WAITING_APPROVAL",
                "target": target,
                "bundle_id": getattr(bundle, "bundle_id", ""),
                "deliveries": [],
            }
        return {
            "decision": "SUBMITTED",
            "target": target,
            "bundle_id": getattr(bundle, "bundle_id", ""),
            "deliveries": [{"channel": target, "kind": "bounded_incident_report"}],
        }
