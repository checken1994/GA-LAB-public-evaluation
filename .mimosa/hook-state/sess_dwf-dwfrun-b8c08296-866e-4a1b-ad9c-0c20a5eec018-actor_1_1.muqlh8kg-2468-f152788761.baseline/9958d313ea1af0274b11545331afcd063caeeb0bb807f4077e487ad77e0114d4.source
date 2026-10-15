import asyncio
import types

import pytest
from fastapi import HTTPException, WebSocketDisconnect

from scp.security import auth as auth_module

# ==============================================================================
# T03 - AUTH FAIL-CLOSED CONTRACT (Bước 0.8)
# ==============================================================================
# Canonical auth = scp/security/auth.py verify_admin + scp/api/chat.py ws auth.
# Contract under test (hermetic unit-level; transport stubbed only at the
# WebSocket driver boundary, config source stubbed as an input):
#   - nothing configured      -> 401, no dev bypass
#   - wrong token             -> 401
#   - exact token             -> accepted
#   - ws session_id ONLY      -> closed 1008 (session_id is NOT a credential;
#                                the dev-UI fallback was removed 2026-09-02)
#   - ws explicit valid token -> accepted, system message delivered
# 429 rate-limit behavior lives in _check_rate_limit/_record_auth_failure and is
# intentionally not driven here (timing-based, belongs to a runtime profile).
# ==============================================================================


class _StubWebSocket:
    """Transport stub: only what the ws /chat handler touches for auth."""

    def __init__(self, query_params):
        self.query_params = query_params
        self.accepted = False
        self.close_calls = []
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000):
        self.close_calls.append(code)

    async def send_json(self, payload):
        self.sent.append(payload)

    async def receive_text(self):
        raise WebSocketDisconnect(code=1000)


def _configure(monkeypatch, token="scp-test-token-123", password=""):
    monkeypatch.setattr(
        auth_module, "load_auth_config",
        lambda: types.SimpleNamespace(configured=bool(token or password), token=token, password=password),
    )
    monkeypatch.setattr(auth_module, "_auth_failures", {})


def test_verify_admin_denies_when_nothing_configured(monkeypatch):
    _configure(monkeypatch, token="", password="")
    with pytest.raises(HTTPException) as exc_info:
        auth_module.verify_admin(token=None, authorization="", request=None)
    assert exc_info.value.status_code == 401, "Unconfigured auth must deny (401), never allow"


def test_verify_admin_rejects_wrong_token(monkeypatch):
    _configure(monkeypatch)
    with pytest.raises(HTTPException) as exc_info:
        auth_module.verify_admin(token="wrong-token", authorization="", request=None)
    assert exc_info.value.status_code == 401


def test_verify_admin_accepts_exact_token(monkeypatch):
    _configure(monkeypatch)
    # [TQ-05] verify_admin returns True on success - pin the return value.
    accepted = auth_module.verify_admin(token="scp-test-token-123", authorization="", request=None)
    assert accepted is True, accepted


def test_ws_chat_rejects_session_id_only(monkeypatch):
    from scp.api import chat as chat_module
    monkeypatch.setattr(
        "scp.security.auth_config.load_auth_config",
        lambda: types.SimpleNamespace(configured=True, token="scp-test-token-123", password=""),
    )
    ws = _StubWebSocket({"session_id": "attacker-chosen-id"})
    asyncio.run(chat_module.scp_chat(ws))
    assert 1008 in ws.close_calls, (
        f"session_id-only connection was not rejected with 1008: {ws.close_calls}"
    )
    assert ws.sent == [], "Rejected connection must receive no data"


def test_ws_chat_accepts_explicit_valid_token(monkeypatch):
    from scp.api import chat as chat_module
    monkeypatch.setattr(
        "scp.security.auth_config.load_auth_config",
        lambda: types.SimpleNamespace(configured=True, token="scp-test-token-123", password=""),
    )
    ws = _StubWebSocket({"token": "scp-test-token-123", "session_id": "sess-1"})
    asyncio.run(chat_module.scp_chat(ws))
    assert ws.accepted is True, "Valid explicit token was not accepted"
    assert 1008 not in ws.close_calls, f"Valid token connection was rejected: {ws.close_calls}"
    assert ws.sent and ws.sent[0].get("type") == "system", (
        f"No system message after valid auth: {ws.sent[:1]}"
    )
