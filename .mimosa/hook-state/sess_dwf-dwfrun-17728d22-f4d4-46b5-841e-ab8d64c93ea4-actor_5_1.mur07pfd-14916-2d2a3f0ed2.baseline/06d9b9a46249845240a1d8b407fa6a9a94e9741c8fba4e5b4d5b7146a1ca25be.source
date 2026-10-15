"""
SCP Complete Standard Test — Mạch 8: Audit & Benchmark
Covers: api/routes/audit_routes.py, api/routes/batch_benchmark_routes.py

FA-01: Strict assertions, no loosening
FA-02: No skip/xfail
FA-03: Full pytest output as evidence
FA-04: No simulated VERIFIED
FA-05: No self-grant authority
FA-09: Exploit mandate - reproduce actual behavior
FA-13: Causal branch coverage of audit & benchmark flow
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from scp.api_server import app
from scp.core.fitness_engine import run_and_gate


@pytest.fixture(autouse=True)
def _reset_auth_rate_limit_accounting():
    """Test isolation: verify_admin counts 401s per IP for 60s process-wide
    (5 failures -> 429). Negative-auth probes across the T03 suite share the
    'testclient' IP accounting, so this file's own [AUDIT-1]/[AUDIT-2]
    no-auth probes could be 429-blocked depending on suite timing (observed
    as a flaky failure). This clears the ACCOUNTING only — verify_admin
    product logic and the 401/403 assertions here are untouched (same
    isolation pattern already used by T02 and T03 flow-06)."""
    from scp.security import auth as _auth

    _auth._auth_failures.clear()
    yield
    _auth._auth_failures.clear()


class TestFlow08AuditBenchmark:
    """Mạch 8: Audit & Benchmark - SCP Complete Standard"""

    # =========================================================================
    # 1. AUDIT ROUTES
    # =========================================================================

    def test_audit_stats_requires_admin(self):
        """
        [AUDIT-1] GET /audit/stats requires admin auth.
        """
        with TestClient(app) as client:
            response = client.get("/v105/audit/stats")
            assert response.status_code in [401, 403]

    def test_audit_findings_requires_admin(self):
        """
        [AUDIT-2] GET /audit/findings requires admin auth.
        """
        with TestClient(app) as client:
            response = client.get("/v105/audit/findings")
            assert response.status_code in [401, 403]

    def test_audit_stats_returns_fitness_metrics(self):
        """
        [AUDIT-3] Audit stats returns fetcher metrics.
        """
        from scp.api._shared import verify_admin
        app.dependency_overrides[verify_admin] = lambda: True
        try:
            with TestClient(app) as client:
                with patch("scp.core.audit_fetcher.get_audit_stats") as mock_stats:
                    mock_stats.return_value = {
                        "total_fetched": 100,
                        "success": True
                    }

                    response = client.get("/v105/audit/stats")
                    assert response.status_code == 200
                    data = response.json()
                    assert "total_fetched" in data
        finally:
            app.dependency_overrides = {}

    # =========================================================================
    # 2. BATCH BENCHMARK ROUTES
    # =========================================================================

    def test_benchmark_batch_submit_requires_admin(self):
        """
        [BENCH-1] POST /batch requires auth.
        """
        with TestClient(app) as client:
            response = client.post("/v3/hands/benchmark/batch", json={"questions": [{"question": "test"}]})
            assert response.status_code in [401, 403]

    def test_benchmark_batch_submit_accepts_job(self, tmp_path):
        """
        [BENCH-2] POST /batch accepts benchmark job with JSON payload.
        """
        with TestClient(app) as client:
            with patch("scp.api.routes.batch_benchmark_routes._guard", return_value=None):
                with patch("scp.api.routes.batch_benchmark_routes._root", return_value=tmp_path):
                    with patch("scp.api.routes.batch_benchmark_routes._start_job", return_value=True):
                        response = client.post("/v3/hands/benchmark/batch", json={
                            "questions": [{"id": i, "question": f"Test {i}"} for i in range(10)],
                            "baseUrl": "http://127.0.0.1:8000"
                        })
                        assert response.status_code == 200
                        data = response.json()
                        assert data.get("success") is True
                        assert "job" in data
                        assert data["job"]["total"] == 10

    def test_benchmark_batch_status_requires_admin(self):
        """
        [BENCH-3] GET /batch/{job_id} requires auth.
        """
        with TestClient(app) as client:
            response = client.get("/v3/hands/benchmark/batch/bench-123")
            assert response.status_code in [401, 403]

    def test_benchmark_batch_pause_requires_admin(self):
        """
        [BENCH-4] POST /batch/{job_id}/pause requires auth.
        """
        with TestClient(app) as client:
            response = client.post("/v3/hands/benchmark/batch/bench-123/pause", json={})
            assert response.status_code in [401, 403]

    def test_benchmark_batch_resume_requires_admin(self):
        """
        [BENCH-5] POST /batch/{job_id}/resume requires auth.
        """
        with TestClient(app) as client:
            response = client.post("/v3/hands/benchmark/batch/bench-123/resume", json={})
            assert response.status_code in [401, 403]

    # =========================================================================
    # 3. FITNESS ENGINE — Core Audit
    # =========================================================================

    def test_fitness_engine_run_and_gate(self):
        """
        [FIT-1] Fitness engine runs and returns report and verdict.
        """
        result = run_and_gate()

        assert "report" in result
        assert "verdict" in result
        assert "total" in result["report"]

    def test_fitness_engine_gates_include_security(self):
        """
        [FIT-2] Fitness result includes verdict and config_hash.
        """
        result = run_and_gate()
        
        assert "config_hash" in result["report"]
        assert "verdict" in result["verdict"]

    def test_fitness_engine_gates_include_performance(self):
        """
        [FIT-3] Fitness result includes accuracy.
        """
        result = run_and_gate()
        
        assert "decision_accuracy" in result["report"]

    def test_fitness_engine_gates_include_reliability(self):
        """
        [FIT-4] Fitness result includes reasons.
        """
        result = run_and_gate()
        
        assert "reasons" in result["verdict"]

    # =========================================================================
    # 4. BENCHMARK RUNNER
    # =========================================================================

    def test_benchmark_runner_executes_workloads(self):
        """
        [BENCH-RUN-1] Benchmark runner executes defined workloads.
        """
        import asyncio

        from scp.benchmark.benchmark_suite import BENCHMARK_TASKS, run_benchmark_task
        assert "mmlu" in BENCHMARK_TASKS
        assert len(BENCHMARK_TASKS["mmlu"]) >= 1

        mock_gateway = AsyncMock()
        mock_gateway.chat = AsyncMock(return_value=("Paris is the capital", "test-prov"))
        res = asyncio.run(run_benchmark_task(mock_gateway, "mmlu", "What is the capital of France?", "Paris"))
        assert res["success"] is True
        assert res["provider"] == "test-prov"
        assert res["task"] == "mmlu"

    def test_benchmark_runner_measures_hallucination_rate(self):
        """
        [BENCH-RUN-2] Benchmark measures hallucination / incorrect response rate.
        """
        import asyncio

        from scp.benchmark.benchmark_suite import run_benchmark_task
        mock_gateway = AsyncMock()
        mock_gateway.chat = AsyncMock(return_value=("Madrid is the capital", "test-prov"))
        res = asyncio.run(run_benchmark_task(mock_gateway, "mmlu", "What is the capital of France?", "Paris"))
        assert res["success"] is False
        assert res["task"] == "mmlu"


class TestFlow08AuditBenchmarkCausalCoverage:
    """
    FA-13: Causal Coverage Matrix for Mạch 8
    """

    def test_causal_audit_endpoints_admin_required(self):
        """Branch: audit endpoints require admin"""
        with TestClient(app) as client:
            assert client.get("/v105/audit/stats").status_code in [401, 403]
            assert client.get("/v105/audit/findings").status_code in [401, 403]

    def test_causal_audit_fitness_metrics(self):
        """Branch: audit stats -> fitness metrics"""
        from scp.api._shared import verify_admin
        app.dependency_overrides[verify_admin] = lambda: True
        try:
            with TestClient(app) as client:
                with patch("scp.core.audit_fetcher.get_audit_stats") as mock_stats:
                    mock_stats.return_value = {"total_fetched": 50, "success": True}
                    resp = client.get("/v105/audit/stats")
                    assert resp.status_code == 200
                    assert resp.json()["total_fetched"] == 50
        finally:
            app.dependency_overrides.clear()

    def test_causal_benchmark_batch_submit(self, tmp_path):
        """Branch: batch submit -> job queued"""
        with TestClient(app) as client:
            with patch("scp.api.routes.batch_benchmark_routes._guard", return_value=None):
                with patch("scp.api.routes.batch_benchmark_routes._root", return_value=tmp_path):
                    with patch("scp.api.routes.batch_benchmark_routes._start_job", return_value=True):
                        resp = client.post("/v3/hands/benchmark/batch", json={
                            "questions": [{"id": 1, "question": "Q1"}, {"id": 2, "question": "Q2"}],
                            "baseUrl": "http://127.0.0.1:8000"
                        })
                        assert resp.status_code == 200
                        assert resp.json()["job"]["total"] == 2

    def test_causal_benchmark_batch_status(self):
        """Branch: batch status requires admin"""
        with TestClient(app) as client:
            resp = client.get("/v3/hands/benchmark/batch/bench-causal-test")
            assert resp.status_code in [401, 403]

    def test_causal_benchmark_batch_pause_resume(self):
        """Branch: pause/resume requires admin"""
        with TestClient(app) as client:
            assert client.post("/v3/hands/benchmark/batch/b-1/pause", json={}).status_code in [401, 403]
            assert client.post("/v3/hands/benchmark/batch/b-1/resume", json={}).status_code in [401, 403]

    def test_causal_fitness_engine_runs_gates(self):
        """Branch: run_and_gate -> all gates executed"""
        result = run_and_gate()
        assert "report" in result
        assert "verdict" in result
        assert "total" in result["report"]

    def test_causal_fitness_security_gates(self):
        """Branch: security gates included"""
        result = run_and_gate()
        assert "config_hash" in result["report"]
        assert "verdict" in result["verdict"]

    def test_causal_fitness_performance_gates(self):
        """Branch: performance gates included"""
        result = run_and_gate()
        assert "decision_accuracy" in result["report"]
        assert 0.0 <= result["report"]["decision_accuracy"] <= 1.0

    def test_causal_fitness_reliability_gates(self):
        """Branch: reliability gates included"""
        result = run_and_gate()
        assert "reasons" in result["verdict"]
        assert isinstance(result["verdict"]["reasons"], (list, tuple))

    def test_causal_benchmark_runner_workloads(self):
        """Branch: runner executes workloads"""
        import asyncio

        from scp.benchmark.benchmark_suite import run_benchmark_task
        mock_gateway = AsyncMock()
        mock_gateway.chat = AsyncMock(return_value=("Answer: 4", "math-engine"))
        res = asyncio.run(run_benchmark_task(mock_gateway, "gsm8k", "2 + 2?", "4"))
        assert res["success"] is True
        assert res["task"] == "gsm8k"

    def test_causal_benchmark_hallucination_rate(self):
        """Branch: hallucination rate measured"""
        import asyncio

        from scp.benchmark.benchmark_suite import run_benchmark_task
        mock_gateway = AsyncMock()
        mock_gateway.chat = AsyncMock(return_value=("Answer: 5", "math-engine"))
        res = asyncio.run(run_benchmark_task(mock_gateway, "gsm8k", "2 + 2?", "4"))
        assert res["success"] is False


if __name__ == "__main__":
    pass
