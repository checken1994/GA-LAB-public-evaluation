from dataclasses import dataclass
from typing import ClassVar

ALLOWED_ACTIONS = {'block_ip', 'tighten_rate_limit', 'enable_honeypot', 'log_forensic', 'alert_human', 'alert_cert', 'canary_inject', 'quarantine', 'isolate', 'forensic_snapshot'}
FORBIDDEN_ACTIONS = {'hack_back', 'data_destruction', 'preemptive_strike', 'counter_attack', 'reverse_exploit'}

@dataclass
class Playbook:
    name: str
    severity: str
    actions: list[str]
    timeout_min: int
    requires_human_approval: bool

    def validate(self):
        for action in self.actions:
            if action in FORBIDDEN_ACTIONS:
                raise ValueError(f"Forbidden action '{action}' in playbook '{self.name}'")

class PlaybookRegistry:
    """[SCP-DNA-FIX R5-3] Registry for incident-response playbooks + guardrail enforcer.

    Previously this entire 57-line module was NEVER imported anywhere →
    FORBIDDEN_ACTIONS (hack_back, data_destruction, preemptive_strike,
    counter_attack, reverse_exploit) were defined but NEVER enforced. Now wired
    into scp.security.escalation.execute_defensive_playbook (every action is
    validated against FORBIDDEN_ACTIONS before being executed).
    """
    DEFAULT_PLAYBOOKS: ClassVar[dict] = {
        'ddos_volumetric': Playbook(
            name='ddos_volumetric',
            severity='high',
            actions=['block_ip', 'tighten_rate_limit', 'alert_human'],
            timeout_min=0,
            requires_human_approval=False
        ),
        'prompt_injection': Playbook(
            name='prompt_injection',
            severity='medium',
            actions=['log_forensic', 'canary_inject', 'alert_human'],
            timeout_min=0,
            requires_human_approval=False
        ),
        'apt_predicted': Playbook(
            name='apt_predicted',
            severity='high',
            actions=['block_ip', 'enable_honeypot', 'forensic_snapshot'],
            timeout_min=30,
            requires_human_approval=True
        ),
        'supply_chain_attack': Playbook(
            name='supply_chain_attack',
            severity='critical',
            actions=['alert_human', 'quarantine'],
            timeout_min=1440,
            requires_human_approval=False
        ),
        'zero_day_exploit': Playbook(
            name='zero_day_exploit',
            severity='critical',
            actions=['isolate', 'alert_cert'],
            timeout_min=0,
            requires_human_approval=False
        )
    }

    @classmethod
    def validate_action(cls, action: str) -> bool:
        """[SCP-DNA-FIX R5-3] Reject FORBIDDEN_ACTIONS before any counter-response.

        Args:
            action: a single action name (e.g. 'block_ip', 'hack_back').

        Returns:
            True if action is ALLOWED (safe to execute).
            False if action is FORBIDDEN (caller MUST skip it + log alert).

        Raises:
            Nothing — returns False for forbidden actions so callers can
            fail-safe (skip) instead of fail-open (execute then discover).

        Usage (from escalation.execute_defensive_playbook):
            if not PlaybookRegistry.validate_action(action):
                logger.warning(f"[guardrail] refused forbidden action: {action}")
                continue
        """
        if not action or not isinstance(action, str):
            return False
        if action in FORBIDDEN_ACTIONS:
            return False
        # Action is either in ALLOWED_ACTIONS (known-safe) or unknown
        # (let caller decide — fail-open for novel defensive actions,
        # fail-closed only for explicit FORBIDDEN_ACTIONS).
        return True

    @classmethod
    def get_playbook(cls, threat_type: str) -> "Playbook | None":
        """Look up a playbook by threat_type. Returns None if no match."""
        return cls.DEFAULT_PLAYBOOKS.get(threat_type)
