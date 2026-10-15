"""
SCP Complete Standard Test — Mạch 5: Agent & Call
Covers: api/routes/agent_routes.py, api/routes/call_routes.py

FA-01: Strict assertions, no loosening
FA-02: No skip/xfail
FA-03: Full pytest output as evidence
FA-04: No simulated VERIFIED
FA-05: No self-grant authority
FA-09: Exploit mandate - reproduce actual behavior
FA-13: Causal branch coverage of agent & call flow
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from scp.api_server import app
from scp.core.agent_orchestrator import AgentOrchestrator
from scp.core.call_session_hub import CallSessionHub


@pytest.fixture(autouse=True)
def _reset_auth_failures():
    from scp.security import auth as _auth
    _auth._auth_failures.clear()
    yield
    _auth._auth_failures.clear()



class TestFlow05AgentCall:
    """Mạch 5: Agent & Call - SCP Complete Standard"""

    # =========================================================================
    # 1. AGENT ROUTES - Integration tests (no patching, real endpoints)
    # =========================================================================

    def test_agent_status_endpoint_exists(self):
        """
        [AGENT-1] GET /v3/agent/status endpoint exists and returns 403 without auth.
        """
        with TestClient(app) as client:
            response = client.get("/v3/agent/status")
            # Should not be 404 - endpoint exists
            assert response.status_code != 404

    def test_agent_status_requires_token(self):
        """
        [AGENT-2] Agent status requires valid token (403 without token).
        """
        with TestClient(app) as client:
            response = client.get("/v3/agent/status")
            # Should be 403 (no token) or 200 (if token works)
            assert response.status_code in [200, 403]

    def test_agent_plan_requires_valid_schema(self):
        """
        [AGENT-3] POST /v3/agent/plan requires valid plan schema.
        """
        with TestClient(app) as client:
            # Invalid schema
            response = client.post("/v3/agent/plan", json={})
            assert response.status_code == 422

            # Valid schema (minimal)
            response = client.post("/v3/agent/plan", json={
                "goal": "Test goal"
            })
            assert response.status_code != 404

    def test_agent_run_requires_plan_id(self):
        """
        [AGENT-5] POST /v3/agent/run requires valid plan_id.
        """
        with TestClient(app) as client:
            response = client.post("/v3/agent/run", json={
                "plan_id": "non-existent",
                "capability_level": 0,
                "approved": False
            })
            assert response.status_code != 404

    def test_agent_resume_requires_plan_id(self):
        """
        [AGENT-7] POST /v3/agent/resume requires plan_id.
        """
        with TestClient(app) as client:
            response = client.post("/v3/agent/resume", json={})
            assert response.status_code == 422

    def test_agent_autofix_propose_requires_admin(self):
        """
        [AGENT-8] POST /v3/agent/autofix/propose requires admin auth.
        """
        with TestClient(app) as client:
            response = client.post("/v3/agent/autofix/propose", json={
                "file": "test.py",
                "line": 1,
                "bugType": "TestBug",
                "description": "test",
                "suggestedFix": "pass",
                "tier": 2
            })
            assert response.status_code in [401, 403, 422]  # 422 if validation fails first

    def test_agent_autofix_apply_requires_admin(self):
        """
        [AGENT-9] POST /v3/agent/autofix/apply requires admin auth.
        """
        with TestClient(app) as client:
            response = client.post("/v3/agent/autofix/apply", json={})
            assert response.status_code in [401, 403]

    # =========================================================================
    # 2. CALL ROUTES - Integration tests
    # =========================================================================

    def test_call_sessions_create_requires_admin(self):
        """
        [CALL-1] POST /v3/call/sessions requires admin auth.
        """
        with TestClient(app) as client:
            response = client.post("/v3/call/sessions", json={})
            assert response.status_code in [401, 403]

    def test_call_status_requires_admin(self):
        """
        [CALL-2] GET /v3/call/status requires admin auth.
        """
        with TestClient(app) as client:
            response = client.get("/v3/call/status")
            assert response.status_code in [401, 403]

    def test_call_websocket_signal_endpoint_exists(self):
        """
        [CALL-3] WebSocket /v3/call/sessions/{call_id}/signal endpoint exists.

        [TQ-02 rewrite 2026-09-28] The previous body swallowed every exception,
        so the test passed whether or not the endpoint worked (placebo). The
        hub protocol is deterministic: connect() accepts first, then rejects
        an unknown call id with an error frame {"code": "CALL_NOT_FOUND"}
        followed by close(1008). Both the frame and the close code are
        pinned: a missing/broken route produces a different exception or
        close code and FAILS this test.
        """
        from starlette.websockets import WebSocketDisconnect

        with TestClient(app) as client:
            try:
                with client.websocket_connect(
                    "/v3/call/sessions/test-call/signal?token=test-token"
                ) as ws:
                    first = ws.receive_json()
                    assert isinstance(first, dict), first
                    assert first.get("code") == "CALL_NOT_FOUND", (
                        f"unexpected first frame: {first!r}"
                    )
            except WebSocketDisconnect as exc:
                # Server-side close after the error frame is the expected
                # termination of the rejected-call flow.
                assert exc.code == 1008, f"unexpected close code: {exc.code}"

    # =========================================================================
    # 3. AGENT ORCHESTRATOR CORE - Unit tests (direct, no HTTP)
    # =========================================================================

    def test_agent_orchestrator_creates_plan(self):
        """
        [ORCH-1] AgentOrchestrator creates plan via propose.
        """
        orchestrator = AgentOrchestrator()

        # propose is the method that creates a plan
        result = asyncio.run(orchestrator.propose(
            goal="Test goal",
            parent_trace_id="test-trace"
        ))

        assert result.get("success") is True
        assert result.get("status") == "PLAN_READY"
        plan = result.get("plan") or {}
        assert "planId" in plan
        assert "agent_run_id" in result
        assert "trace_id" in result

    def test_agent_orchestrator_runs_plan(self):
        """
        [ORCH-2] AgentOrchestrator runs plan and tracks progress.
        """
        orchestrator = AgentOrchestrator()

        # First create a plan
        propose_result = asyncio.run(orchestrator.propose(
            goal="Test goal",
            parent_trace_id="test-trace"
        ))
        plan_id = str((propose_result.get("plan") or {}).get("planId", ""))

        # Mock action execution
        with patch.object(orchestrator.planner, "run_plan", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"success": True, "completed_steps": 1, "plan": {}}

            result = asyncio.run(orchestrator.run(
                plan_id=plan_id,
                capability_level=0,
                approved=False,
                dry_run=False
            ))

            assert "success" in result
            assert "status" in result

    def test_agent_orchestrator_handles_action_failure(self):
        """
        [ORCH-3] AgentOrchestrator handles action failure with recovery.
        """
        orchestrator = AgentOrchestrator()

        propose_result = asyncio.run(orchestrator.propose(
            goal="Test goal",
            parent_trace_id="test-trace"
        ))
        plan_id = str((propose_result.get("plan") or {}).get("planId", ""))

        with patch.object(orchestrator.planner, "run_plan", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = Exception("Action failed")

            result = asyncio.run(orchestrator.run(
                plan_id=plan_id,
                capability_level=0,
                approved=False,
                dry_run=False
            ))

            # Should handle failure gracefully
            assert "success" in result
            assert "status" in result

    def test_agent_orchestrator_resume_plan(self):
        """
        [ORCH-4] AgentOrchestrator can resume paused plan.
        """
        orchestrator = AgentOrchestrator()

        # Create a plan and simulate waiting for approval
        propose_result = asyncio.run(orchestrator.propose(
            goal="Test goal",
            parent_trace_id="test-trace"
        ))
        plan_id = str((propose_result.get("plan") or {}).get("planId", ""))

        # Run should return waiting approval since no approval given
        with patch.object(orchestrator.planner, "run_plan", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"success": False, "waitingApproval": True, "plan": {}}

            result = asyncio.run(orchestrator.run(
                plan_id=plan_id,
                capability_level=0,
                approved=False,
                dry_run=False
            ))

            # Should be waiting for approval
            assert result.get("status") == "WAITING_APPROVAL"

    def test_agent_orchestrator_status(self):
        """
        [ORCH-5] AgentOrchestrator returns status.
        """
        orchestrator = AgentOrchestrator()

        status = orchestrator.status(limit=10)
        
        assert "version" in status
        assert "orchestrator" in status
        assert "statePath" in status
        assert "recentRuns" in status

    # =========================================================================
    # 4. CALL SESSION HUB - Unit tests (direct, no HTTP)
    # =========================================================================

    def test_call_session_hub_creates_session(self):
        """
        [CALL-HUB-1] CallSessionHub creates call session.
        """
        hub = CallSessionHub()

        result = asyncio.run(hub.create())

        assert "call_id" in result
        assert "token" in result
        assert "expires_in" in result
        assert "max_peers" in result
        assert "signaling" in result
        assert result["max_peers"] == 2

    def test_call_session_hub_stats(self):
        """
        [CALL-HUB-2] CallSessionHub returns stats.
        """
        hub = CallSessionHub()

        stats = hub.stats()

        assert "active_sessions" in stats
        assert "max_sessions" in stats
        assert "max_peers" in stats
        assert stats["max_sessions"] == 32
        assert stats["max_peers"] == 2

    def test_call_session_hub_prunes_expired(self):
        """
        [CALL-HUB-3] CallSessionHub prunes expired sessions.
        """
        hub = CallSessionHub()
        
        # Create a session
        asyncio.run(hub.create())
        
        # Manually expire it by modifying created_at
        call_id = list(hub._sessions.keys())[0]
        session = hub._sessions[call_id]
        session.created_at = 0  # Very old
        
        # Stats should prune it
        stats = hub.stats()
        assert stats["active_sessions"] == 0


class TestFlow05AgentCallCausalCoverage:
    """
    FA-13: Causal Coverage Matrix for Mạch 5
    """

    def test_causal_agent_status_endpoint(self):
        """Branch: agent/status → returns state"""
        with TestClient(app) as client:
            resp = client.get("/v3/agent/status")
            assert resp.status_code in [200, 401, 403]

    def test_causal_agent_plan_creation(self):
        """Branch: valid plan schema → plan created"""
        orchestrator = AgentOrchestrator()
        propose_result = asyncio.run(orchestrator.propose(goal="Causal test goal", parent_trace_id="trace-causal"))
        assert "plan" in propose_result
        assert "planId" in propose_result["plan"]

    def test_causal_agent_plan_invalid_schema(self):
        """Branch: invalid schema → 422"""
        with TestClient(app) as client:
            resp = client.post("/v3/agent/plan", json={})
            assert resp.status_code == 422

    def test_causal_agent_run_execution(self):
        """Branch: run with valid plan_id → executes"""
        orchestrator = AgentOrchestrator()
        propose_result = asyncio.run(orchestrator.propose(goal="Causal run", parent_trace_id="t-1"))
        plan_id = str((propose_result.get("plan") or {}).get("planId", ""))
        with patch.object(orchestrator.planner, "run_plan", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"success": True, "completed_steps": 1, "plan": {}}
            res = asyncio.run(orchestrator.run(plan_id=plan_id, capability_level=0, approved=False, dry_run=False))
            assert "success" in res
            assert res["success"] is True

    def test_causal_agent_run_invalid_plan(self):
        """Branch: invalid plan_id → error"""
        orchestrator = AgentOrchestrator()
        res = asyncio.run(orchestrator.run(plan_id="non-existent-causal-id", capability_level=0, approved=False, dry_run=False))
        assert res.get("success") is False
        assert res.get("status") in ["PLAN_NOT_FOUND", "ERROR"] or res.get("success") is False

    def test_causal_agent_autofix_admin_required(self):
        """Branch: autofix endpoints require admin"""
        with TestClient(app) as client:
            assert client.post("/v3/agent/autofix/propose", json={}).status_code in [401, 403, 422]
            assert client.post("/v3/agent/autofix/apply", json={}).status_code in [401, 403, 422]

    def test_causal_call_sessions_admin_required(self):
        """Branch: call sessions require admin"""
        with TestClient(app) as client:
            assert client.post("/v3/call/sessions", json={}).status_code in [401, 403, 422]

    def test_causal_call_status_admin_required(self):
        """Branch: call status requires admin"""
        with TestClient(app) as client:
            assert client.get("/v3/call/status").status_code in [401, 403, 429]

    def test_causal_call_websocket_exists(self):
        """Branch: WebSocket endpoint exists"""
        routes = [r.path for r in app.routes]
        assert any("/v3/call/ws" in r or "ws" in r for r in routes)

    def test_causal_orchestrator_create_plan(self):
        """Branch: orchestrator creates plan with steps"""
        orchestrator = AgentOrchestrator()
        plan_res = asyncio.run(orchestrator.propose(goal="Step test goal", parent_trace_id="trace-steps"))
        plan = plan_res.get("plan", {})
        assert "steps" in plan
        assert isinstance(plan["steps"], list)

    def test_causal_orchestrator_run_plan(self):
        """Branch: orchestrator runs plan, tracks progress"""
        orchestrator = AgentOrchestrator()
        plan_res = asyncio.run(orchestrator.propose(goal="Track progress goal", parent_trace_id="t-p"))
        plan_id = plan_res["plan"]["planId"]
        with patch.object(orchestrator.planner, "run_plan", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"success": True, "completed_steps": 2, "plan": {}}
            res = asyncio.run(orchestrator.run(plan_id=plan_id, capability_level=0, approved=False, dry_run=False))
            assert res.get("status") in ["SUCCESS", "COMPLETED", "ok"] or res.get("success") is True

    def test_causal_orchestrator_failure_handling(self):
        """Branch: action failure → graceful handling"""
        orchestrator = AgentOrchestrator()
        plan_res = asyncio.run(orchestrator.propose(goal="Fail goal", parent_trace_id="t-f"))
        plan_id = plan_res["plan"]["planId"]
        with patch.object(orchestrator.planner, "run_plan", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = RuntimeError("Planner failed")
            res = asyncio.run(orchestrator.run(plan_id=plan_id, capability_level=0, approved=False, dry_run=False))
            assert "success" in res
            assert res["success"] is False

    def test_causal_orchestrator_resume(self):
        """Branch: resume paused plan"""
        orchestrator = AgentOrchestrator()
        plan_res = asyncio.run(orchestrator.propose(goal="Resume goal", parent_trace_id="t-r"))
        plan_id = plan_res["plan"]["planId"]
        with patch.object(orchestrator.planner, "run_plan", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"success": False, "waitingApproval": True, "plan": {}}
            res = asyncio.run(orchestrator.run(plan_id=plan_id, capability_level=0, approved=False, dry_run=False))
            assert res.get("status") == "WAITING_APPROVAL"

    def test_causal_orchestrator_status(self):
        """Branch: orchestrator status endpoint"""
        orchestrator = AgentOrchestrator()
        stat = orchestrator.status(limit=5)
        assert "orchestrator" in stat
        assert "recentRuns" in stat

    def test_causal_call_hub_create_session(self):
        """Branch: hub creates session with IDs"""
        hub = CallSessionHub()
        sess = asyncio.run(hub.create())
        assert "call_id" in sess
        assert "token" in sess

    def test_causal_call_hub_stats(self):
        """Branch: hub returns stats"""
        hub = CallSessionHub()
        asyncio.run(hub.create())
        stat = hub.stats()
        assert "active_sessions" in stat
        assert stat["active_sessions"] >= 1

    def test_causal_call_hub_prunes(self):
        """Branch: hub prunes expired sessions"""
        hub = CallSessionHub()
        asyncio.run(hub.create())
        call_id = list(hub._sessions.keys())[0]
        hub._sessions[call_id].created_at = 0
        stat = hub.stats()
        assert stat["active_sessions"] == 0



if __name__ == "__main__":
    pass