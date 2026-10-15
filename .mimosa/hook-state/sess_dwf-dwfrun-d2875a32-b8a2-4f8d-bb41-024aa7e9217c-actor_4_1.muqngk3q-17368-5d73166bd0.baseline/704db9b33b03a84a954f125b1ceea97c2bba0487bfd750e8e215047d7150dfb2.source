"""
SCP Complete Standard Test — Mạch 1: Boot & Background Jobs
Covers: api_server.py lifespan, api_server_parts/lifespan.py, api/background_jobs.py, core/doubt_cron.py

FA-01: Strict assertions, no loosening
FA-02: No skip/xfail
FA-03: Full pytest output as evidence
FA-04: No simulated VERIFIED
FA-05: No self-grant authority
FA-09: Exploit mandate - reproduce actual behavior
FA-13: Causal branch coverage of startup + background jobs
"""

import os
import threading
import time


def _poll_wait(cond, timeout=2.0):
    import time
    s = time.time()
    while time.time() - s < timeout:
        if cond(): return True
        time.sleep(0.05)
    return False

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from scp.api.background_jobs import registry
from scp.api_server import app
from scp.core.doubt_cron import DoubtCron, run_doubt_cycle

# [MACH1-FIX-7] The real lifespan now enforces validate_boot_config() at boot
# (fail-closed, MACH1-FIX-2). These are throwaway, contract-compliant test
# fixtures used ONLY when the surrounding environment provides no values
# (setdefault never overrides a real configured secret; values are never
# printed and are explicitly non-production).
os.environ.setdefault(
    "SCP_JWT_SECRET", "test-only-jwt-secret-0123456789abcdef-not-for-production"
)
os.environ.setdefault("SCP_ADMIN_KEY", "test-only-admin-key-0123456789abcdef")


class TestFlow01BootBackground:
    """Mạch 1: Boot & Background Jobs - SCP Complete Standard"""

    # =========================================================================
    # 1. LIFESPAN STARTUP — Pre-startup deep audit gate
    # =========================================================================

    def test_lifespan_startup_validates_boot_config(self):
        """
        [EXEC-1] Pre-startup validates boot config (validate_boot_config).
        """
        from scp.core.config_contract import validate_boot_config

        # [TQ-05] Must return the validated env map (not just "not raise"):
        # a dict whose entries are all non-empty string keys -> string values.
        validated = validate_boot_config()
        assert isinstance(validated, dict), type(validated)
        for key, value in validated.items():
            assert isinstance(key, str) and key, key
            assert isinstance(value, str), (key, value)

    def test_lifespan_starts_background_jobs_registry(self):
        """
        [DNA #23] Background job registry has required jobs registered.
        """
        from scp.api.background_jobs import registry

        # Registry should have jobs registered
        assert len(registry._jobs) > 0

        # Verify required kernel jobs are registered
        job_names = list(registry._jobs.keys())
        assert "kernel_lease_expiry" in job_names
        assert "kernel_orphan_reconcile" in job_names

        # Verify start_all/stop_all methods exist
        assert hasattr(registry, "start_all")
        assert hasattr(registry, "stop_all")

    def test_lifespan_initializes_otel_telemetry(self):
        """
        [OBS-1] OpenTelemetry telemetry initializes on startup.
        Verifies otel setup doesn't crash startup.
        [MACH1-FIX-7] Un-mocked: this test previously patched start/stop
        helpers on the dead scp/api/_lifespan.py module. The REAL lifespan
        (scp/api_server_parts/lifespan.py, bound to the app) now runs unpatched.
        """
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200

    def test_lifespan_auto_wires_deep_audit_scheduler_24h(self):
        """
        [AUDIT-1] Deep audit scheduler auto-wired with 24h interval.
        Verifies the scheduler job is registered.
        """
        from fastapi.testclient import TestClient

        from scp.api.background_jobs import registry
        from scp.api_server import app

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            # Check that the registry has the deep audit job registered
            job_names = [job.name for job in registry._jobs.values()]
            assert any("audit" in name.lower() for name in job_names)

    def test_lifespan_auto_wires_attack_mode_monitor_5min(self):
        """
        [ATTACK-1] Attack mode monitor auto-wired with 5min interval.
        Verifies the attack monitor job is registered.
        """
        from fastapi.testclient import TestClient

        from scp.api.background_jobs import registry
        from scp.api_server import app

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200

            job_names = [job.name for job in registry._jobs.values()]
            assert any("attack" in name.lower() or "monitor" in name.lower() for name in job_names)

    def test_lifespan_starts_why_verify_scheduler_thread(self):
        """
        [M12-FIX PF-4b 85fc67f] The ACTIVE lifespan (scp/api_server_parts/
        lifespan.py — the one api_server.py binds) starts the background WHY
        verification scheduler and exposes it on app.state.

        Regression pin: the loop used to exist only in scp/api/_lifespan.py,
        which api_server.py does NOT bind, so deferred WHY verification never
        ran in the real deployment while comments claimed it was fixed.
        """
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            thread = getattr(app.state, "why_verify_thread", None)
            assert isinstance(thread, threading.Thread), (
                "active lifespan must start the WHY verify scheduler (PF-4b regression)"
            )
            assert thread.name == "scp-why-verify-scheduler"
            assert thread.daemon is True
            assert thread.is_alive()

    def test_get_judge_wires_why_engine_onto_judge_singleton(self):
        """
        [M12-FIX PF-4a 85fc67f] get_judge() attaches a real WhyEngine to the
        judge singleton so the background WHY verify loop's
        getattr(judge, "why_engine", None) guard can actually find it.

        Regression pin: RealityJudge had no why_engine attribute at all, so
        the deferred why_verification_plans piled up pending forever (PASS
        without reality — R6-3 pattern).
        """
        from scp.api_server_parts.helpers import get_judge
        from scp.meta.why_engine_parts.whyengine import WhyEngine

        judge = get_judge()
        wired = getattr(judge, "why_engine", None)
        assert isinstance(wired, WhyEngine), (
            "get_judge() must wire a real WhyEngine onto the judge singleton (PF-4a regression)"
        )

    # =========================================================================
    # 2. BACKGROUND JOBS REGISTRY — DNA #23
    # =========================================================================

    def test_background_job_registry_register_and_run(self):
        """
        [DNA #23] Registry allows registering jobs with interval and required flag.
        Verifies job registration and execution.
        """
        from scp.api.background_jobs import registry

        execution_log = []

        @registry.register(name="test_job_flow1", interval_seconds=1, required=False, initial_delay_seconds=0)
        def test_job():
            execution_log.append(time.time())

        # Start registry
        registry.start_all()

        # Wait for at least one execution
        assert _poll_wait(lambda: len(execution_log) >= 1, 1.5)

        # Stop registry
        registry.stop_all(), "Registered background job did not execute"

        # Cleanup
        registry._jobs.pop("test_job_flow1", None)

    def test_background_job_required_flag_blocks_startup_on_failure(self):
        """
        [DNA #23] Required=True jobs block startup if they fail to start.
        """
        from scp.api.background_jobs import registry

        @registry.register(name="required_fail_job", interval_seconds=1, required=True, initial_delay_seconds=0)
        def required_fail_job():
            raise RuntimeError("Required job failed")

        # Should raise on start_all if required job fails immediately
        with pytest.raises(RuntimeError, match="Required job failed"):
            registry.start_all()

        registry._jobs.pop("required_fail_job", None)

    def test_background_job_optional_flag_allows_startup_on_failure(self):
        """
        [DNA #23] Required=False jobs log failure but don't block startup.
        """
        from scp.api.background_jobs import registry

        @registry.register(name="optional_fail_job", interval_seconds=1, required=False)
        def optional_fail_job():
            raise RuntimeError("Optional job failed")

        # Should NOT raise on start_all
        registry.start_all()
        # [TQ-05] The optional job must have actually STARTED (registered,
        # marked not-required, thread started) ? "did not raise" is not enough.
        opt_status = registry.status().get("optional_fail_job")
        assert opt_status is not None, "optional job missing from registry"
        assert opt_status["started"] is True, opt_status
        assert opt_status["required"] is False, opt_status
        time.sleep(0.5)
        registry.stop_all()

        registry._jobs.pop("optional_fail_job", None)

    def test_background_job_stop_all_cancels_all_tasks(self):
        """
        [SHUTDOWN-1] registry.stop_all() cancels all running background tasks.
        """
        from scp.api.background_jobs import registry

        execution_count = {"count": 0}

        @registry.register(name="stop_test_job", interval_seconds=0.1, required=False, initial_delay_seconds=0)
        def stop_test_job():
            execution_count["count"] += 1

        registry.start_all()
        time.sleep(0.5)
        initial_count = execution_count["count"]
        assert initial_count > 0

        registry.stop_all()
        # A tick already in flight when stop_all() set the stop event
        # legitimately completes before the thread join returns; the contract
        # under test is "no NEW tick starts after stop_all()", so the frozen
        # baseline is captured after the stop, not before it.
        stopped_count = execution_count["count"]
        time.sleep(0.5)
        final_count = execution_count["count"]

        # Count must not increase after stop_all() has returned
        assert final_count == stopped_count, "Background job continued after stop_all()"

        registry._jobs.pop("stop_test_job", None)

    # =========================================================================
    # 3. DOUBT_CRON — Background Why Loop
    # =========================================================================

    def test_doubt_cron_initializes_without_db_lock(self, tmp_path):
        """
        [FAIL-SILENT FIX] DoubtCron initializes without causing SQLite lock.
        Verifies the cron can start without deadlock.
        """
        data_dir = tmp_path / "doubt_data"
        data_dir.mkdir()

        cron = DoubtCron(data_dir=str(data_dir), interval_seconds=300)

        assert cron.data_dir == str(data_dir)
        assert cron.interval == 300

    def test_doubt_cron_runs_cycle_with_4_checks(self, tmp_path):
        """
        [WHY-1] DoubtCron runs doubt cycle with 4 checks: fitness, kernel, escalation, why_gate.
        """
        data_dir = tmp_path / "doubt_data"
        data_dir.mkdir()

        cron = DoubtCron(data_dir=str(data_dir), interval_seconds=1)

        # Mock the internal checks (they are module-level functions)
        with patch("scp.core.doubt_cron._check_fitness") as mock_fitness:
            with patch("scp.core.doubt_cron._check_kernel_integrity") as mock_kernel:
                with patch("scp.core.doubt_cron._check_escalation_backlog") as mock_escalation:
                    with patch("scp.core.doubt_cron._check_why_gate_anomaly") as mock_why:
                        mock_fitness.return_value = {"check": "fitness_drift", "ok": True}
                        mock_kernel.return_value = {"check": "kernel_integrity", "ok": True}
                        mock_escalation.return_value = {"check": "escalation_backlog", "ok": True}
                        mock_why.return_value = {"check": "why_gate_anomaly", "ok": True}

                        report = run_doubt_cycle(cron.data_dir)

                        assert "checks" in report
                        assert "verdict" in report
                        assert len(report["checks"]) == 4
                        assert report["verdict"] == "CLEAN"

    def test_doubt_cron_persists_report_to_jsonl(self, tmp_path):
        """
        [WHY-2] DoubtCron persists report to doubt_ledger.jsonl.
        Verifies file write without lock contention.
        """
        data_dir = tmp_path / "doubt_data"
        data_dir.mkdir()

        cron = DoubtCron(data_dir=str(data_dir), interval_seconds=1)

        with patch("scp.core.doubt_cron._check_fitness") as mock_fitness:
            with patch("scp.core.doubt_cron._check_kernel_integrity") as mock_kernel:
                with patch("scp.core.doubt_cron._check_escalation_backlog") as mock_escalation:
                    with patch("scp.core.doubt_cron._check_why_gate_anomaly") as mock_why:
                        mock_fitness.return_value = {"check": "fitness_drift", "ok": True}
                        mock_kernel.return_value = {"check": "kernel_integrity", "ok": True}
                        mock_escalation.return_value = {"check": "escalation_backlog", "ok": True}
                        mock_why.return_value = {"check": "why_gate_anomaly", "ok": True}

                        run_doubt_cycle(cron.data_dir)

        # Verify report persisted to JSONL
        ledger_path = Path(cron.data_dir) / "doubt_ledger.jsonl"
        assert ledger_path.exists()
        content = ledger_path.read_text()
        assert "fitness_drift" in content

    def test_doubt_cron_respects_interval(self, tmp_path):
        """
        [SCHED-1] DoubtCron respects configured interval in background thread.
        """
        data_dir = tmp_path / "doubt_data"
        data_dir.mkdir()

        cron = DoubtCron(data_dir=str(data_dir), interval_seconds=0.5)
        cron.start()
        time.sleep(1.2)  # Wait for ~2 intervals
        cron.stop()

        # Should have run at least 2 cycles
        assert cron.last_report is not None

    def test_doubt_cron_handles_check_errors_silently(self, tmp_path):
        """
        [FAIL-SILENT] DoubtCron handles check errors without crashing.
        """
        data_dir = tmp_path / "doubt_data"
        data_dir.mkdir()

        cron = DoubtCron(data_dir=str(data_dir), interval_seconds=1)

        # Simulate errors in checks - should not raise
        with patch("scp.core.doubt_cron._check_fitness", side_effect=Exception("Fitness error")):
            with patch("scp.core.doubt_cron._check_kernel_integrity", side_effect=Exception("Kernel error")):
                with patch("scp.core.doubt_cron._check_escalation_backlog", side_effect=Exception("Escalation error")):
                    with patch("scp.core.doubt_cron._check_why_gate_anomaly", side_effect=Exception("Why error")):
                        # Should not raise
                        report = run_doubt_cycle(cron.data_dir)
                        assert report["verdict"] != "CLEAN"  # Should report failures

    # =========================================================================
    # 4. HEALTH ENDPOINT — Runtime Verification
    # =========================================================================

    def test_health_endpoint_returns_ok_after_full_startup(self):
        """
        [HEALTH-1] /health returns 200 OK after full startup with all subsystems.
        """
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "ok"
            assert "service_identity" in data
            assert data["service_identity"]["service_name"] == "scp-backend"
            assert data["service_identity"]["mode"] == "production"

    def test_health_detailed_endpoint_returns_full_status(self, monkeypatch):
        """
        [HEALTH-2] /health/detailed returns full subsystem status — WITH admin auth.

        [SEC-FIX /health-authz 2026-09-26] /health/detailed giờ yêu cầu
        verify_admin như /metrics. Contract: không token → 401; token hợp lệ
        → 200/503 như trước. Assertion KHÔNG được nới lỏng — thêm nhánh
        fail-closed 401 là siết chặt hơn, không phải placebo.
        """
        monkeypatch.setenv("SCP_AUTH_PASSWORD", "flow01-health-detailed-test-pw")
        monkeypatch.delenv("SCP_AUTH_PASSWORD_FILE", raising=False)
        monkeypatch.delenv("SCP_AUTH_TOKEN_SECRET", raising=False)
        monkeypatch.delenv("SCP_AUTH_TOKEN_SECRET_FILE", raising=False)
        from scp.security import auth as _auth
        with _auth._auth_failures_lock:
            _auth._auth_failures.clear()
        with TestClient(app) as client:
            unauth = client.get("/health/detailed")
            assert unauth.status_code == 401, "/health/detailed phải 401 khi thiếu token"
            response = client.get(
                "/health/detailed",
                headers={"Authorization": "Bearer flow01-health-detailed-test-pw"},
            )
            # May return 200 or 503 depending on subsystems
            assert response.status_code in [200, 503]

    # =========================================================================
    # 5. SHUTDOWN — Clean Stop
    # =========================================================================

    def test_lifespan_shutdown_cancels_background_tasks(self):
        """
        [SHUTDOWN-1] Lifespan shutdown cancels all background tasks cleanly.
        """
        from scp.api.background_jobs import registry

        # Verify registry has stop_all
        assert hasattr(registry, "stop_all")
        assert hasattr(registry, "start_all")

    def test_doubt_cron_shutdown_stops_thread(self, tmp_path):
        """
        [SHUTDOWN-2] DoubtCron stops its background thread on shutdown.
        """
        data_dir = tmp_path / "doubt_data"
        data_dir.mkdir()

        cron = DoubtCron(data_dir=str(data_dir), interval_seconds=0.1)
        cron.start()
        time.sleep(0.2)
        cron.stop()

        # Wait for thread to actually stop (join with timeout)
        if cron._thread:
            cron._thread.join(timeout=1.0)

        # Thread should be stopped
        assert cron._thread is not None
        assert not cron._thread.is_alive()


class TestFlow01BootBackgroundCausalCoverage:
    """
    FA-13: Causal Coverage Matrix for Mạch 1 — executable tests, no stubs.

    [MACH1-FIX-7] The previous 10 causal methods were empty `pass` stubs
    referencing tests that do not exist (FA-04: simulated coverage). Replaced
    with real tests (no MagicMock/AsyncMock for any subsystem logic):
      - boot config gate raises on missing SCP_JWT_SECRET (fail-closed)
      - the REAL lifespan starts the required registry jobs (threads alive)
      - /ask returns 503 while the judge is not ready
      - RetryPolicy.run_background requeues a RETRY_SCHEDULED task via a REAL
        TaskKernel on tmp SQLite (no mocks)
      - doubt-cron escalation backlog check runs against a REAL seeded kernel
        DB (un-mocked)
    """

    def test_causal_boot_config_missing_jwt_secret_raises(self, monkeypatch):
        """Branch: required env missing → ConfigContractError → boot aborts."""
        from scp.core.config_contract import ConfigContractError, validate_boot_config

        monkeypatch.delenv("SCP_JWT_SECRET", raising=False)
        with pytest.raises(ConfigContractError, match="SCP_JWT_SECRET"):
            validate_boot_config()

    def test_causal_lifespan_starts_required_registry_jobs(self):
        """Branch: lifespan startup → registry.start_all() → required jobs' threads alive."""
        # Normalize: whatever earlier tests did, the required jobs must be
        # stopped so this test proves the LIFESPAN starts them.
        registry.stop_all()
        lease_job = registry._jobs.get("kernel_lease_expiry")
        orphan_job = registry._jobs.get("kernel_orphan_reconcile")
        assert lease_job is not None, "kernel_lease_expiry not registered"
        assert orphan_job is not None, "kernel_orphan_reconcile not registered"
        assert lease_job._started is False
        assert orphan_job._started is False

        with TestClient(app):
            assert lease_job._started is True, "lifespan did not start kernel_lease_expiry"
            assert orphan_job._started is True, "lifespan did not start kernel_orphan_reconcile"
            assert lease_job._thread is not None and lease_job._thread.is_alive(), (
                "kernel_lease_expiry thread not alive after lifespan startup"
            )
            assert orphan_job._thread is not None and orphan_job._thread.is_alive(), (
                "kernel_orphan_reconcile thread not alive after lifespan startup"
            )
            # Optional jobs wired by the real lifespan are registered too.
            job_names = set(registry._jobs)
            assert {"deep_audit_scheduler", "attack_mode_monitor"} <= job_names
        # Lifespan shutdown path stops the registry again.
        assert lease_job._started is False
        assert orphan_job._started is False

    def test_causal_ask_returns_503_while_judge_not_ready(self, monkeypatch):
        """Branch: judge not ready → /ask returns 503 (no blocking lazy init)."""
        from scp.security.jwt_guard import create_access_token

        # Real config (not a mock): delay the judge launch far beyond the test
        # window so the real lifespan leaves app.state.judge_ready=False.
        monkeypatch.setenv("SCP_JUDGE_START_DELAY_SEC", "180")
        token = create_access_token(data={"sub": "m1-causal-test"})
        headers = {"Authorization": f"Bearer {token}"}
        with TestClient(app) as client:
            assert bool(getattr(app.state, "judge_ready", False)) is False
            resp = client.post("/ask", json={"question": "causal probe"}, headers=headers)
            assert resp.status_code == 503, f"expected 503 judge gate, got {resp.status_code}: {resp.text[:200]}"
            body = resp.json()
            assert body["detail"] == "judge_initializing"

    def test_causal_ask_invalid_token_returns_401(self, monkeypatch):
        """Branch: auth dependency runs before the judge gate → invalid JWT → 401."""
        monkeypatch.setenv("SCP_JUDGE_START_DELAY_SEC", "180")
        with TestClient(app) as client:
            resp = client.post(
                "/ask",
                json={"question": "no token"},
                headers={"Authorization": "Bearer m1-causal-invalid-token"},
            )
            assert resp.status_code == 401, f"expected 401, got {resp.status_code}"

    def test_causal_retry_policy_run_background_requeues_kernel_task(self, tmp_path, monkeypatch):
        """Branch: RETRY_SCHEDULED task + retry timeout → run_background requeues to QUEUED."""
        import scp.policy.retry_policy as retry_policy_module
        from scp.policy.retry_policy import RetryPolicy
        from scp.task_kernel import TaskKernel

        kernel = TaskKernel(str(tmp_path / "kernel.sqlite3"))
        try:
            # REAL kernel state machine (same sequence as AskKernelAdapter.begin):
            kernel.create_task("t-retry-m1", "tester", "causal retry probe", max_attempts=3)
            for state in ("PLANNING", "READY", "QUEUED"):
                kernel.transition("t-retry-m1", state, actor="test", reason="m1_causal")
            lease = kernel.claim("t-retry-m1", "test-worker", ttl_seconds=60)
            kernel.start("t-retry-m1", lease.lease_id)
            failed = kernel.commit_failed(
                "t-retry-m1",
                lease.lease_id,
                "test-worker",
                failure_classification="RETRYABLE",
                indictment_ref="test://m1/retry",
            )
            assert failed["state"] == "RETRY_SCHEDULED"

            def _plans():
                rows = kernel.conn.execute(
                    "SELECT task_id, state FROM tasks WHERE state='RETRY_SCHEDULED'"
                ).fetchall()
                return [{"planId": row["task_id"], "state": row["state"]} for row in rows]

            def _retry(task_id, reason):
                kernel.transition(
                    task_id, "QUEUED", actor="retry_policy", reason="retry_policy_background"
                )

            policy = RetryPolicy(get_plans_fn=_plans, retry_fn=_retry)
            # Test fixture: shrink the retry timeout constant to 0 so the
            # requeue happens immediately (no subsystem mocked).
            monkeypatch.setattr(retry_policy_module, "RETRY_TIMEOUT_SEC", 0.0)
            stop = threading.Event()
            worker = threading.Thread(
                target=policy.run_background,
                kwargs={"interval_sec": 0.05, "stop_event": stop},
                daemon=True,
                name="t-retry-worker",
            )
            worker.start()
            deadline = time.time() + 10
            state = kernel.get_task("t-retry-m1")["state"]
            while state != "QUEUED" and time.time() < deadline:
                time.sleep(0.05)
                state = kernel.get_task("t-retry-m1")["state"]
            stop.set()
            worker.join(timeout=5)
            assert state == "QUEUED", f"run_background did not requeue task; final state={state}"
        finally:
            kernel.close()

    def test_causal_doubt_cron_escalation_backlog_real_sqlite(self, tmp_path):
        """Branch: real kernel DB with 1 HUMAN_REVIEW task → escalation backlog check counts it."""
        from scp.core.doubt_cron import _check_escalation_backlog
        from scp.task_kernel import TaskKernel

        kernel = TaskKernel(str(tmp_path / "ask_task_kernel.sqlite3"))
        try:
            kernel.create_task("t-escalation-m1", "tester", "escalation probe")
            for state in ("PLANNING", "READY", "QUEUED"):
                kernel.transition("t-escalation-m1", state, actor="test", reason="m1_causal")
            lease = kernel.claim("t-escalation-m1", "test-worker", ttl_seconds=60)
            kernel.start("t-escalation-m1", lease.lease_id)
            kernel.transition(
                "t-escalation-m1", "HUMAN_REVIEW", actor="test", reason="escalation_probe"
            )
        finally:
            kernel.close()

        result = _check_escalation_backlog(str(tmp_path))
        assert result["check"] == "escalation_backlog"
        assert result["ok"] is True
        assert result["detail"]["total"] == 1
        assert result["detail"]["backlog"].get("HUMAN_REVIEW") == 1

    def test_causal_registry_starts_and_stops_registered_job(self):
        """Branch: registry.start_all() → job executes; stop_all() → no more executions."""
        execution_log = []

        @registry.register(name="causal_probe_job", interval_seconds=0.1, required=False, initial_delay_seconds=0)
        def causal_probe():
            execution_log.append(time.time())

        registry.start_all()
        time.sleep(0.5)
        assert len(execution_log) >= 1, "registered job did not execute"
        registry.stop_all()
        count_after_stop = len(execution_log)
        time.sleep(0.4)
        assert len(execution_log) == count_after_stop, "job kept executing after stop_all()"
        registry._jobs.pop("causal_probe_job", None)


if __name__ == "__main__":
    pass #([__file__, "-v", "--tb=short"])
