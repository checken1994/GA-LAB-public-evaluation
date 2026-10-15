"""[SECURITY-REASON 2026-09-26] Kernel reason phải phân loại security.

Live sweep: injection runs nhận cùng kernel reason
'ask_evidence_insufficient_or_contradicted' với benign evidence-insufficient
runs — audit không phân biệt được security kill với thiếu bằng chứng lành
thiểu. Fix: scp/ask_kernel_adapter.py::_verification_fail_reason trả
'ask_security_escalate' khi security lane quyết định kết quả (LANE_SECURITY /
security_blocked guard / governance KILL), còn benign giữ reason cũ.

Helper này là chính là hàm finalize() dùng để đặt reason cho kernel event
(_escalate_to_human_review / commit_failed details), nên unit test tại đây
chính là test decision thật của kernel reason, không phải assertion hình thức.
"""
from __future__ import annotations

from scp.ask_kernel_adapter import _verification_fail_reason


def test_injection_shaped_security_lane_uses_security_reason():
    """Injection-shaped ask (security lane) → kernel reason chứa 'security'."""
    security_response = {
        "lane": "LANE_SECURITY",
        "verdict": "FAIL",
        "final_answer": "[SCP: Answer withheld]",
        "governance_decision": "KILL",
    }
    assert _verification_fail_reason(security_response) == "ask_security_escalate"


def test_security_blocked_guard_uses_security_reason():
    """security_blocked trong v98_guard là security signal độc lập với lane."""
    response = {
        "lane": "LANE_FACTUAL",
        "verdict": "FAIL",
        "governance_decision": "ESCALATE",
        "v98_guard": {"security_blocked": True},
    }
    assert _verification_fail_reason(response) == "ask_security_escalate"


def test_governance_kill_alone_is_security_determined():
    """Governance KILL (judge-level, trước _safe_response) = security kill."""
    response = {
        "lane": "LANE_FACTUAL",
        "verdict": "FLAGGED",
        "governance_decision": "KILL",
    }
    assert _verification_fail_reason(response) == "ask_security_escalate"


def test_benign_insufficient_evidence_keeps_historical_reason():
    """Benign evidence-insufficient (judge FAIL/UNKNOWN, UPHOLD/ALLOW) giữ
    nguyên reason cũ — không bị dán nhãn security oan."""
    benign_response = {
        "lane": "LANE_FACTUAL",
        "verdict": "UNKNOWN",
        "governance_decision": "UPHOLD",
        "v98_guard": {"security_blocked": False},
    }
    assert (
        _verification_fail_reason(benign_response)
        == "ask_evidence_insufficient_or_contradicted"
    )


def test_chatbot_lane_insufficient_evidence_keeps_historical_reason():
    benign_chat = {
        "lane": "LANE_CHATBOT",
        "verdict": "FAIL",
        "governance_decision": "ALLOW",
    }
    assert (
        _verification_fail_reason(benign_chat)
        == "ask_evidence_insufficient_or_contradicted"
    )


def test_missing_fields_default_to_benign_reason():
    """Response thiếu lane/governance (payload cũ) → reason cũ, không crash."""
    assert (
        _verification_fail_reason({})
        == "ask_evidence_insufficient_or_contradicted"
    )
