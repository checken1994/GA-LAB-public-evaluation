from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from scp.contracts.time import now_utc_iso
from scp.knowledge.knowledge_control_db import KnowledgeControlDB


class DecisionAction(str, Enum):
    PROMOTE = "PROMOTE"
    HOLD = "HOLD"
    UNDER_REVIEW = "UNDER_REVIEW"
    DEMOTE = "DEMOTE"
    RETIRE = "RETIRE"
    BLOCKED = "BLOCKED"

@dataclass
class PromotionDecision:
    action: DecisionAction | str
    knowledge_id: str
    from_status: str
    target_status: str
    decided_status: str
    reason_codes: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    missing_pieces: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    decision_timestamp: str = ""
    decision_id: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.action, str):
            self.action = DecisionAction(self.action.upper())
        if not self.decision_timestamp:
            self.decision_timestamp = now_utc_iso()


class PromotionAuthority:
    """
    P1-03 Promotion Authority.
    Uses YAML contract to evaluate if a knowledge claim can transition statuses.
    Records decisions and events immutably to KnowledgeControlDB.
    """
    def __init__(self, db: KnowledgeControlDB, policy_path: str | Path):
        self.db = db
        self.policy_path = Path(policy_path)
        with open(self.policy_path, encoding="utf-8") as f:
            self.policy_data = yaml.safe_load(f)

    def assess(
        self,
        knowledge_id: str,
        current_status: str,
        target_status: str,
        context: dict[str, Any],
        profile_name: str = "factual_general"
    ) -> PromotionDecision:

        transition_key = f"{current_status}_TO_{target_status}".upper()

        try:
            profile = self.policy_data["profiles"][profile_name]
        except KeyError:
            return PromotionDecision(
                action=DecisionAction.BLOCKED,
                knowledge_id=knowledge_id,
                from_status=current_status,
                target_status=target_status,
                decided_status=current_status,
                reason_codes=["BLOCKED_UNKNOWN_PROMOTION_POLICY"],
                missing_pieces=[f"profile {profile_name} not found"]
            )

        if transition_key not in profile:
            # We don't have a specific upward rule for this in YAML, maybe it's not an upward path
            # For simplicity, if it's not defined, we block it unless we add default rules.
            return PromotionDecision(
                action=DecisionAction.BLOCKED,
                knowledge_id=knowledge_id,
                from_status=current_status,
                target_status=target_status,
                decided_status=current_status,
                reason_codes=["INVALID_TRANSITION"],
                missing_pieces=[f"transition {transition_key} not in profile"]
            )

        rules = profile[transition_key].get("require", {})
        missing = []

        # Evaluate each rule against context
        for rule_key, expected_val in rules.items():
            actual_val = context.get(rule_key)
            if actual_val != expected_val:
                missing.append(f"{rule_key} (expected {expected_val}, got {actual_val})")

        if missing:
            return PromotionDecision(
                action=DecisionAction.HOLD,
                knowledge_id=knowledge_id,
                from_status=current_status,
                target_status=target_status,
                decided_status=current_status,
                reason_codes=["REQUIREMENTS_NOT_MET"],
                missing_pieces=missing
            )

        return PromotionDecision(
            action=DecisionAction.PROMOTE,
            knowledge_id=knowledge_id,
            from_status=current_status,
            target_status=target_status,
            decided_status=target_status,
            reason_codes=["ALL_REQUIREMENTS_MET"]
        )

    def commit(self, decision: PromotionDecision) -> str:
        """
        Records the decision and executes the status event transition if allowed.
        """
        # 1. Record decision
        dec_dict = {
            "knowledge_id": decision.knowledge_id,
            "from_status": decision.from_status,
            "requested_status": decision.target_status,
            "decided_status": decision.decided_status,
            "decision_type": decision.action.value,
            "verdict": "APPROVED" if decision.action == DecisionAction.PROMOTE else "DENIED",
            "reason_codes": decision.reason_codes,
            "missing_piece_refs": decision.missing_pieces
        }
        decision_id = self.db.record_promotion_decision(dec_dict)
        decision.decision_id = decision_id

        # 2. Record status event if status changed
        if decision.decided_status != decision.from_status:
            event_dict = {
                "knowledge_id": decision.knowledge_id,
                "from_status": decision.from_status,
                "to_status": decision.decided_status,
                "decision_id": decision_id,
                "reason_codes": decision.reason_codes
            }
            self.db.record_status_event(event_dict)

        return decision_id

