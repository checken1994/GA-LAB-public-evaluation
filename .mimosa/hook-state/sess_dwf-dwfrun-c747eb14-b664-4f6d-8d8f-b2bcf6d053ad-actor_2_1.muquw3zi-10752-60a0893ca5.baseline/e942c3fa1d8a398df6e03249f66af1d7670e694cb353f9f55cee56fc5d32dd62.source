"""
SCP Contract Test: Typed Evaluation API (TypeSafe SystemOne compatible).
Covers: scp/api/routes/evaluation_routes.py (/v1/systemone, /v1/eval).

Invariants:
- FA-01: Strict assertions, no loosening
- FA-02: No skip/xfail
- FA-03: Full pytest output as evidence
- Fail-closed auth: 401 on missing/invalid token
- Validation: 422 on empty state or questions
- Output shape matches TypeSafe SystemOne wire format
"""
from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from scp.api_server import app
from scp.api_server_parts import helpers as _scp_helpers

logger = logging.getLogger("tests.T02.evaluation_api")


def _suppress_threads(*args, **kwargs):
    pass


_scp_helpers.start_crawl_thread = _suppress_threads
if getattr(_scp_helpers, "start_fast_learning_thread", None) is not None:
    _scp_helpers.start_fast_learning_thread = _suppress_threads

TEST_JWT_SECRET = "eval-test-jwt-secret-0123456789abcdef-40chars"
TEST_ADMIN_KEY = "scp-eval-static-api-key-test-value-12345"


def _auth_jwt(monkeypatch) -> dict:
    monkeypatch.setenv("SCP_JWT_SECRET", TEST_JWT_SECRET)
    from scp.security.jwt_guard import create_access_token

    token = create_access_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}


def _auth_api_key(monkeypatch) -> dict:
    monkeypatch.setenv("SCP_ADMIN_KEY", TEST_ADMIN_KEY)
    monkeypatch.setenv("SCP_JWT_SECRET", TEST_JWT_SECRET)
    return {"Authorization": f"Bearer {TEST_ADMIN_KEY}"}


class TestEvaluationApiContract:
    def test_unauthenticated_request_is_rejected(self):
        """[EVAL-AUTH-1] Requests without valid Bearer credentials fail closed (401)."""
        with TestClient(app) as client:
            resp = client.post(
                "/v1/systemone",
                json={"state": "hello", "questions": {"q1": {"type": "noul", "instructions": "Is valid?"}}},
            )
            assert resp.status_code == 401

    def test_invalid_bearer_token_is_rejected(self, monkeypatch):
        """[EVAL-AUTH-2] Invalid Bearer token fails closed (401)."""
        monkeypatch.setenv("SCP_JWT_SECRET", TEST_JWT_SECRET)
        with TestClient(app) as client:
            resp = client.post(
                "/v1/systemone",
                json={"state": "hello", "questions": {"q1": {"type": "noul", "instructions": "Is valid?"}}},
                headers={"Authorization": "Bearer completely-invalid-key-xyz"},
            )
            assert resp.status_code == 401

    def test_empty_state_returns_422(self, monkeypatch):
        """[EVAL-VAL-1] Empty state returns 422 Unprocessable Entity."""
        headers = _auth_jwt(monkeypatch)
        with TestClient(app) as client:
            resp = client.post(
                "/v1/systemone",
                json={"state": "   ", "questions": {"q1": {"type": "noul", "instructions": "Is valid?"}}},
                headers=headers,
            )
            assert resp.status_code == 422

    def test_empty_questions_returns_422(self, monkeypatch):
        """[EVAL-VAL-2] Empty questions dict returns 422 Unprocessable Entity."""
        headers = _auth_jwt(monkeypatch)
        with TestClient(app) as client:
            resp = client.post(
                "/v1/systemone",
                json={"state": "some text to evaluate", "questions": {}},
                headers=headers,
            )
            assert resp.status_code == 422

    def test_static_api_key_bearer_auth(self, monkeypatch):
        """[EVAL-AUTH-3] Static API key (SCP_ADMIN_KEY) is accepted directly as Bearer token."""
        headers = _auth_api_key(monkeypatch)
        with TestClient(app) as client:
            resp = client.post(
                "/v1/systemone",
                json={
                    "state": "The capital of Vietnam is Hanoi.",
                    "questions": {
                        "is_factual": {"type": "noul", "instructions": "Is this factually accurate?"}
                    },
                },
                headers=headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "answers" in data
            assert "is_factual" in data["answers"]
            assert data["answers"]["is_factual"]["type"] == "noul"
            assert isinstance(data["answers"]["is_factual"]["noul"], (int, float))

    def test_eval_alias_endpoint(self, monkeypatch):
        """[EVAL-ROUTE-1] /v1/eval acts as an alias to /v1/systemone."""
        headers = _auth_jwt(monkeypatch)
        with TestClient(app) as client:
            resp = client.post(
                "/v1/eval",
                json={
                    "state": "Sample system prompt and rules for testing.",
                    "questions": {
                        "is_safe": {"type": "noul", "instructions": "Is this state safe?"}
                    },
                },
                headers=headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["verdict"] in ("PASS", "FAIL", "UNKNOWN")
            assert "confidence" in data
            assert "evidence" in data
            assert "elapsed_ms" in data

    def test_wire_format_noul_choice_score_types(self, monkeypatch):
        """[EVAL-WIRE-1] Supports all 3 TypeSafe SystemOne question types with schema compliance."""
        headers = _auth_jwt(monkeypatch)
        with TestClient(app) as client:
            payload = {
                "state": "def add(a, b): return a + b",
                "model": "scp-eval-latest",
                "questions": {
                    "is_syntactically_valid": {
                        "type": "noul",
                        "instructions": "Is this valid Python code?",
                    },
                    "risk_tier": {
                        "type": "choice",
                        "instructions": "Select risk level",
                        "criteria": {"low": None, "medium": None, "high": None},
                    },
                    "code_quality": {
                        "type": "score",
                        "instructions": "Rate code quality",
                        "criteria": ["poor", "acceptable", "good", "flawless"],
                    },
                },
            }
            resp = client.post("/v1/systemone", json=payload, headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["model"] == "scp-eval-latest"

            answers = data["answers"]
            # 1. noul question
            assert "is_syntactically_valid" in answers
            noul_ans = answers["is_syntactically_valid"]
            assert noul_ans["type"] == "noul"
            assert 0.0 <= float(noul_ans["noul"]) <= 1.0

            # 2. choice question
            assert "risk_tier" in answers
            choice_ans = answers["risk_tier"]
            assert choice_ans["type"] == "choice"
            assert choice_ans["choice"] in ("low", "medium", "high", "UNKNOWN")
            assert "probabilities" in choice_ans

            # 3. score question
            assert "code_quality" in answers
            score_ans = answers["code_quality"]
            assert score_ans["type"] == "score"
            assert isinstance(score_ans["score"], (int, float))
            assert "legend" in score_ans
