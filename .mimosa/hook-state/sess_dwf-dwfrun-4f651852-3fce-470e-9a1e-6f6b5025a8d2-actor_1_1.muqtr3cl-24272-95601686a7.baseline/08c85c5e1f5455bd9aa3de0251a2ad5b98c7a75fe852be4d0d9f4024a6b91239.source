"""Regression tests for the webhook judge-result normalization + context whitelist.

[AUDIT-FIX 2026-09-24]

Item A: External audit probe PROVED that judge_with_react_fallback returns a
plain DICT (contract scp/runtime/judge.py) while webhook.py read
`getattr(verdict, "verdict", "UNKNOWN")` / `getattr(verdict, "confidence", 0.0)`
— always UNKNOWN/0.0, so every prompt (even a legit PASS) got action="block".

Item B: `v98_context={..., **req.context}` let a client override the
security-metadata keys (ip, system_id, body, ...) with arbitrary values.

Fail-closed contract pinned here: dict verdicts drive allow/block correctly,
and only allowlisted context keys survive the merge.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import scp.api._shared as api_shared
import scp.api.webhook as webhook_module
from scp.api.webhook import router


@pytest.fixture()
def client(monkeypatch):
    """FastAPI app with the webhook router and stubbed admin auth."""
    monkeypatch.setattr(api_shared, "verify_admin", lambda token=None, request=None: True)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class _RecordingJudge:
    """Judge stub returning the REAL RealityJudge dict contract + recording calls."""

    def __init__(self, result):
        self.result = result
        self.calls = []

    async def judge_with_react_fallback(self, **kwargs):
        self.calls.append(kwargs)
        return self.result

    def judge(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _mount_judge(monkeypatch, judge):
    monkeypatch.setattr(api_shared, "get_judge", lambda: judge)


PASS_DICT = {
    "verdict": "PASS",
    "confidence": 0.9,
    "reasoning": "fixture pass",
    "cycle_count": 0,
    "failures": [],
    "final_answer": "safe answer",
    "slm_responses": [],
    "evidence": {
        "governance_decision": "UPHOLD",
        "knowledge": [],
        "v102_unified_detection": {"matched_patterns": ["benign_pattern"]},
    },
}

FAIL_DICT = {
    "verdict": "FAIL",
    "confidence": 0.82,
    "reasoning": "fixture fail",
    "cycle_count": 0,
    "failures": ["semantic_judge_fail"],
    "final_answer": "",
    "slm_responses": [],
    "evidence": {"governance_decision": "KILL"},
}


def test_pass_dict_verdict_is_allowed(client, monkeypatch):
    """A legit PASS (dict contract) must be allowed — pre-fix it was blocked."""
    judge = _RecordingJudge(PASS_DICT)
    _mount_judge(monkeypatch, judge)
    resp = client.post("/api/analyze", json={"prompt": "hello", "system_id": "s1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "allow"
    assert body["verdict"] == "PASS"
    assert body["confidence"] == pytest.approx(0.9)
    assert body["scp_answer"] == "safe answer"
    assert body["threats"] == ["benign_pattern"]


def test_fail_dict_verdict_is_blocked(client, monkeypatch):
    judge = _RecordingJudge(FAIL_DICT)
    _mount_judge(monkeypatch, judge)
    resp = client.post("/api/analyze", json={"prompt": "evil", "system_id": "s1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "block"
    assert body["verdict"] == "FAIL"
    assert body["confidence"] == pytest.approx(0.82)


def test_unknown_dict_verdict_with_zero_confidence_is_blocked(client, monkeypatch):
    judge = _RecordingJudge({"verdict": "UNKNOWN", "confidence": 0.0, "evidence": {}})
    _mount_judge(monkeypatch, judge)
    resp = client.post("/api/analyze", json={"prompt": "meh", "system_id": "s1"})
    assert resp.json()["action"] == "block"


def test_attribute_style_verdict_still_supported(client, monkeypatch):
    """Legacy attribute-style judge results keep working (getattr fallback)."""
    from types import SimpleNamespace

    judge = _RecordingJudge(SimpleNamespace(verdict="PASS", confidence=0.7, evidence={}, final_answer="ok"))
    _mount_judge(monkeypatch, judge)
    resp = client.post("/api/analyze", json={"prompt": "hello", "system_id": "s1"})
    body = resp.json()
    assert body["action"] == "allow"
    assert body["verdict"] == "PASS"


def test_client_cannot_override_reserved_context_keys(client, monkeypatch):
    """req.context must not override ip/system_id or inject reserved keys."""
    judge = _RecordingJudge(PASS_DICT)
    _mount_judge(monkeypatch, judge)
    resp = client.post(
        "/api/analyze",
        json={
            "prompt": "hello",
            "system_id": "real-system",
            "context": {
                "ip": "6.6.6.6",
                "system_id": "spoofed",
                "body": "injected-body",
                "endpoint": "/injected",
                "user_id": "u-42",
                "session": "sess-1",
            },
        },
    )
    assert resp.status_code == 200
    v98_context = judge.calls[0]["v98_context"]
    assert v98_context["ip"] != "6.6.6.6"
    assert v98_context["system_id"] == "real-system"
    assert "body" not in v98_context
    assert "endpoint" not in v98_context
    assert v98_context["user_id"] == "u-42"
    assert v98_context["session"] == "sess-1"


def test_context_whitelist_is_fail_closed_by_construction():
    """Reserved security keys must never appear in the client allowlist."""
    allowlist = getattr(webhook_module, "_WEBHOOK_CONTEXT_ALLOWED_KEYS", None)
    assert allowlist is not None, (
        "webhook.py must define _WEBHOOK_CONTEXT_ALLOWED_KEYS — "
        "without it req.context can override security-metadata keys"
    )
    for reserved in ("ip", "system_id", "body", "endpoint", "session_id", "conversation_history"):
        assert reserved not in allowlist
