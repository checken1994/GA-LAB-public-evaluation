"""Live Cluster End-to-End Boot, Verification & Clean Shutdown Test.

Spawns the full live cluster:
- LLM Bridge on port 8081
- SCP API Server on port 8000
- Web Dashboard on port 3000

Verifies:
1. Health readiness on all 3 services.
2. Backward-traceable chat interaction yielding trace_id.
3. Authenticated trace retrieval with sensitive secret redaction.
4. Fail-closed HTTP 401 when queried without credentials.
5. Complete process termination with zero leftover zombie processes.
"""
from __future__ import annotations

import subprocess

import pytest

from tools import e2e_live_cluster_verifier
from tools.e2e_live_cluster_verifier import (
    OccupiedPortError,
    clean_ports,
    port_clean_enabled,
    run_e2e_verification,
)


@pytest.mark.asyncio
async def test_live_cluster_e2e_boot_verify_and_shutdown():
    """Verify live cluster lifecycle end-to-end."""
    result = await run_e2e_verification()
    assert result["success"] is True, f"Live cluster E2E verification failed: {result}"
    assert result["bridge_ready"] is True
    assert result["server_ready"] is True
    assert result["dashboard_ready"] is True
    assert result["trace_id"], "No trace_id extracted from live chat"
    assert result["trace_record_verified"] is True
    assert result["secret_redacted"] is True
    assert result["unauth_blocked_401"] is True
    assert result["ports_free"] is True, "Target ports 8000, 8081, 3000 were not cleanly released!"


class TestPortCleanGate:
    """SCP_SMOKE_PORT_CLEAN gate decision logic (no real processes touched)."""

    @pytest.mark.parametrize("raw,expected_enabled", [
        (None, True),          # default: historical force-clean preserved
        ("1", True),
        ("", True),            # empty -> default behavior
        ("true", True),
        ("0", False),          # refuse to kill
        ("false", False),
        ("off", False),
        ("no", False),
    ])
    def test_gate_decision(self, monkeypatch, raw, expected_enabled):
        if raw is None:
            monkeypatch.delenv("SCP_SMOKE_PORT_CLEAN", raising=False)
        else:
            monkeypatch.setenv("SCP_SMOKE_PORT_CLEAN", raw)
        assert port_clean_enabled() is expected_enabled

    def test_gate_enabled_keeps_killing_occupied_ports(self, monkeypatch):
        monkeypatch.setenv("SCP_SMOKE_PORT_CLEAN", "1")
        killed: list[int] = []
        queries = {"n": 0}

        def fake_pids(ports=None):
            # first query finds the listener; the post-kill re-query sees it gone
            queries["n"] += 1
            return {4242} if queries["n"] == 1 else set()

        monkeypatch.setattr(e2e_live_cluster_verifier, "get_listening_pids", fake_pids)
        monkeypatch.setattr(e2e_live_cluster_verifier, "is_docker_backend_process", lambda pid: False)
        monkeypatch.setattr(
            e2e_live_cluster_verifier, "kill_process_tree", lambda pid: killed.append(pid) or True
        )
        monkeypatch.setattr(e2e_live_cluster_verifier.time, "sleep", lambda _s: None)
        clean_ports((8000, 8081, 3000))
        assert killed == [4242], "default gate must preserve the historical kill behavior"

    def test_gate_enabled_fails_closed_when_kill_refused(self, monkeypatch):
        """[audit-20260930-131350] taskkill 'Access is denied' (elevated stale
        process) must fail the run BEFORE boot: booting into a hijacked port
        made readiness probes pass against the zombie while functional probes
        (dashboard trace proxy) hit it and returned plain-text 500s."""
        monkeypatch.setenv("SCP_SMOKE_PORT_CLEAN", "1")
        monkeypatch.setattr(e2e_live_cluster_verifier, "get_listening_pids", lambda ports=None: {4242})
        monkeypatch.setattr(e2e_live_cluster_verifier, "is_docker_backend_process", lambda pid: False)
        monkeypatch.setattr(
            e2e_live_cluster_verifier, "kill_process_tree", lambda pid: False
        )  # kill refused, listener survives
        monkeypatch.setattr(e2e_live_cluster_verifier.time, "sleep", lambda _s: None)
        with pytest.raises(OccupiedPortError) as exc_info:
            clean_ports((8000, 8081, 3000))
        message = str(exc_info.value)
        assert "4242" in message, "surviving PID must be named"
        assert "refused" in message or "fail-closed" in message

    def test_gate_enabled_fails_closed_when_listener_survives_kill(self, monkeypatch):
        """A kill that reports success but leaves a listener (Windows dual-bind
        zombie) must still fail the boot: the post-kill re-query is the real
        gate, not the taskkill exit code."""
        monkeypatch.setenv("SCP_SMOKE_PORT_CLEAN", "1")
        queries = {"n": 0}

        def fake_pids(ports=None):
            queries["n"] += 1
            return {4242} if queries["n"] == 1 else {4242, 5353}

        monkeypatch.setattr(e2e_live_cluster_verifier, "get_listening_pids", fake_pids)
        monkeypatch.setattr(e2e_live_cluster_verifier, "is_docker_backend_process", lambda pid: False)
        monkeypatch.setattr(
            e2e_live_cluster_verifier, "kill_process_tree", lambda pid: True
        )  # OS accepted, yet the listener is still there afterwards
        monkeypatch.setattr(e2e_live_cluster_verifier.time, "sleep", lambda _s: None)
        with pytest.raises(OccupiedPortError) as exc_info:
            clean_ports((8000, 8081, 3000))
        message = str(exc_info.value)
        for pid in (4242, 5353):
            assert str(pid) in message, f"surviving PID {pid} must appear in the error"

    def test_gate_disabled_refuses_to_kill_and_names_pid(self, monkeypatch):
        monkeypatch.setenv("SCP_SMOKE_PORT_CLEAN", "0")
        killed: list[int] = []
        monkeypatch.setattr(e2e_live_cluster_verifier, "get_listening_pids", lambda ports=None: {4242, 5353})
        monkeypatch.setattr(e2e_live_cluster_verifier, "kill_process_tree", lambda pid: killed.append(pid))
        with pytest.raises(OccupiedPortError) as exc_info:
            clean_ports((8000, 8081, 3000))
        assert killed == [], "gate=0 must never kill a co-located listener"
        message = str(exc_info.value)
        assert "SCP_SMOKE_PORT_CLEAN=0" in message
        for pid in (4242, 5353):
            assert str(pid) in message, f"owning PID {pid} must appear in the error"

    def test_gate_disabled_is_noop_when_ports_free(self, monkeypatch):
        monkeypatch.setenv("SCP_SMOKE_PORT_CLEAN", "0")
        monkeypatch.setattr(e2e_live_cluster_verifier, "get_listening_pids", lambda ports=None: set())
        monkeypatch.setattr(
            e2e_live_cluster_verifier, "kill_process_tree",
            lambda pid: pytest.fail("kill must not be called when ports are free"),
        )
        clean_ports((8000, 8081, 3000))  # must not raise

    def test_docker_backend_listener_is_skipped_and_fails_closed(self, monkeypatch):
        """[FA-11 docker-backend protection, 2026-10-01] A Docker-published
        listener on port 8000 is owned by com.docker.backend — killing its
        process tree terminates Docker Desktop itself (observed 2x for real
        in audit wave 1). clean_ports must SKIP the protected PID and then
        fail closed on the survivor re-query instead of taking the daemon
        down or booting over the docker listener."""
        monkeypatch.setenv("SCP_SMOKE_PORT_CLEAN", "1")
        monkeypatch.setattr(e2e_live_cluster_verifier, "get_listening_pids", lambda ports=None: {4242})
        monkeypatch.setattr(
            e2e_live_cluster_verifier, "is_docker_backend_process", lambda pid: pid == 4242
        )
        killed: list[int] = []
        monkeypatch.setattr(
            e2e_live_cluster_verifier, "kill_process_tree", lambda pid: killed.append(pid) or True
        )
        monkeypatch.setattr(e2e_live_cluster_verifier.time, "sleep", lambda _s: None)
        with pytest.raises(OccupiedPortError) as exc_info:
            clean_ports((8000,))
        assert killed == [], "docker backend process must NEVER be killed by clean_ports"
        message = str(exc_info.value)
        assert "4242" in message, "protected docker PID must be named"
        assert "docker" in message.lower(), "failure must explain the docker protection"

    def test_non_docker_listener_is_still_killed_despite_docker_check(self, monkeypatch):
        """The protection is additive: a plain SCP/bridge/dashboard listener
        keeps the historical kill behavior (identity lookup must not swallow
        ordinary cleanup)."""
        monkeypatch.setenv("SCP_SMOKE_PORT_CLEAN", "1")
        queries = {"n": 0}

        def fake_pids(ports=None):
            queries["n"] += 1
            return {4242} if queries["n"] == 1 else set()

        monkeypatch.setattr(e2e_live_cluster_verifier, "get_listening_pids", fake_pids)
        monkeypatch.setattr(e2e_live_cluster_verifier, "is_docker_backend_process", lambda pid: False)
        killed: list[int] = []
        monkeypatch.setattr(
            e2e_live_cluster_verifier, "kill_process_tree", lambda pid: killed.append(pid) or True
        )
        monkeypatch.setattr(e2e_live_cluster_verifier.time, "sleep", lambda _s: None)
        clean_ports((8000,))
        assert killed == [4242]

    def test_taskkill_refusal_falls_back_to_wmi_and_succeeds(self, monkeypatch):
        """[fix 2026-09-30 zombie-wmi-fallback] taskkill "Access is denied"
        against an orphaned same-user zombie is not the final verdict: the WMI
        Terminate fallback must be attempted and its explicit success must
        count as a kill. Live evidence 2026-09-30: taskkill refused the stale
        bun zombies on 0.0.0.0:3000 / 127.0.0.1:8081 (the direct cause of the
        plain-text 500 on the dashboard trace proxy), while WMI Terminate
        returned 0 and freed both ports."""
        calls: list[str] = []

        def fake_run(cmd, **_kwargs):
            calls.append(cmd[0])
            if cmd[0] == "taskkill":
                return subprocess.CompletedProcess(
                    args=cmd, returncode=1, stdout="", stderr="Access is denied"
                )
            assert cmd[0] == "powershell", f"unexpected fallback command: {cmd[0]}"
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="True\r\n", stderr="")

        monkeypatch.setattr(e2e_live_cluster_verifier.subprocess, "run", fake_run)
        monkeypatch.setattr(e2e_live_cluster_verifier.sys, "platform", "win32")
        assert e2e_live_cluster_verifier.kill_process_tree(19156) is True
        assert calls == ["taskkill", "powershell"], (
            "WMI fallback must run only after a taskkill refusal"
        )

    def test_taskkill_refusal_and_wmi_failure_stays_fail_closed(self, monkeypatch):
        """If BOTH taskkill and the WMI fallback fail, the kill must report
        False so clean_ports' survivor re-query raises OccupiedPortError —
        the fallback must never manufacture a green kill."""

        def fake_run(cmd, **_kwargs):
            if cmd[0] == "taskkill":
                return subprocess.CompletedProcess(
                    args=cmd, returncode=1, stdout="", stderr="Access is denied"
                )
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="False", stderr="")

        monkeypatch.setattr(e2e_live_cluster_verifier.subprocess, "run", fake_run)
        monkeypatch.setattr(e2e_live_cluster_verifier.sys, "platform", "win32")
        assert e2e_live_cluster_verifier.kill_process_tree(19156) is False


class TestDockerBackendIdentity:
    """FA-11 marker matching over fake process identities (no OS queries).

    [audit-r2 CI fix 2026-10-01] This class was previously inserted in the
    middle of TestPortCleanGate, which silently re-parented the two
    test_taskkill_refusal_* methods and changed their collected nodeids
    (T00 FA-02 flagged the baseline nodeids as deleted). The class now lives
    after them so the original TestPortCleanGate nodeids are restored.
    """

    @pytest.mark.parametrize("identity", [
        # Windows Docker Desktop backend holding a published port
        "com.docker.backend.exe c:\\program files\\docker\\docker\\resources\\com.docker.backend.exe "
        "com.docker.backend -watchdog -kill-switch",
        "com.docker.build.exe c:\\program files\\docker\\docker\\resources\\com.docker.build.exe",
        "vpnkit.exe c:\\program files\\docker\\docker\\resources\\vpnkit.exe --listen 127.0.0.1",
        "docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 8000 -container-port 8000",
        "com.docker.dev-envs.exe c:\\program files\\docker\\docker\\resources\\com.docker.dev-envs.exe",
        # identity known only by install path (name mangled)
        "someproc.exe c:\\program files\\docker\\docker\\resources\\bin\\listener.exe",
        "someproc.exe c:\\program files\\docker\\docker\\resources/bin/listener.exe",
        "docker desktop.exe \"c:\\program files\\docker\\docker\\docker desktop.exe\"",
    ])
    def test_docker_identities_match(self, identity):
        assert e2e_live_cluster_verifier.is_docker_backend_identity(identity) is True

    @pytest.mark.parametrize("identity", [
        # the services this runner spawns itself
        "bun.exe c:\\bun\\bun.exe bun run mini-services/llm-bridge/index.ts",
        "python.exe c:\\python\\python.exe -m scp.server --port 8000",
        "node.exe c:\\node\\node.exe node_modules/next/dist/bin/next dev -p 3000",
        "python.exe tools/e2e_live_cluster_verifier.py",
        # empty / unknown identity (process gone, denied) is NOT docker
        "",
        "   ",
    ])
    def test_non_docker_identities_do_not_match(self, identity):
        assert e2e_live_cluster_verifier.is_docker_backend_identity(identity) is False

    def test_real_identity_lookup_of_missing_pid_is_empty(self):
        """get_process_identity of a practically-nonexistent PID returns ''
        (best-effort, never raises) and therefore never claims docker."""
        assert e2e_live_cluster_verifier.get_process_identity(4_000_000_000) == ""
        assert e2e_live_cluster_verifier.is_docker_backend_process(4_000_000_000) is False
