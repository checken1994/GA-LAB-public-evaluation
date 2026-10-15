#!/usr/bin/env python3
"""
Automated Live Cluster E2E Boot, Verification & Clean Shutdown Runner
====================================================================
1. Pre-cleans ports 8000, 8081, 3000. Listeners owned by Docker backend
   processes (com.docker.backend, vpnkit, docker-proxy, Docker Desktop path)
   are PROTECTED — identified and skipped, never killed (killing the Docker
   backend terminates Docker Desktop itself; FA-11, observed 2x in wave 1).
2. Boots LLM Bridge (8081), SCP API Server (8000), and Dashboard (3000) in background
   with log redirection to data/service-logs/ to prevent pipe buffering deadlocks.
3. Polls health endpoints with deadlines.
4. Executes live chat interaction with valid admin token, extracting backward-traceable trace_id.
5. Queries GET /v3/trace/{trace_id} with admin credentials and verifies ledger provenance and secret redaction.
6. Queries GET /v3/trace/{trace_id} without auth and verifies fail-closed HTTP 401.
7. Queries Dashboard Next.js API proxy GET /api/scp/v3/trace/{trace_id} and verifies credential forwarding.
8. Cleanly shuts down all spawned processes using process tree kill (taskkill /F /T /PID).
9. Verifies ports 8000, 8081, 3000 are completely free with 0 leftover zombie processes.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "data" / "service-logs"
TARGET_PORTS = (8000, 8081, 3000)


class OccupiedPortError(RuntimeError):
    """Raised when SCP_SMOKE_PORT_CLEAN=0 and a target port has a listener."""


def port_clean_enabled() -> bool:
    """SCP_SMOKE_PORT_CLEAN gate decision.

    Default '1' preserves the historical force-clean: kill whatever holds
    8000/8081/3000. '0' (or false/off/no) refuses to kill — on a shared CI
    runner a co-located service must never be killed by this smoke; clean_ports
    then FAILS with the owning PID(s) instead. Parsing mirrors the repo's
    other kill-switch envs (e.g. SCP_ASK_LEASE_HEARTBEAT).
    """
    return os.environ.get("SCP_SMOKE_PORT_CLEAN", "1").strip().lower() not in {"0", "false", "off", "no"}


def _open_service_log(name: str):
    """Open a fixed service log under data/service-logs.

    The path set is a closed allowlist rooted at the repository; anything
    else, or any path resolving outside ROOT, is refused fail-closed.
    """
    allowed = {
        "llm-bridge.log": LOG_DIR / "llm-bridge.log",
        "scp-server.log": LOG_DIR / "scp-server.log",
        "dashboard.log": LOG_DIR / "dashboard.log",
    }
    if name not in allowed:
        raise ValueError(f"unknown service log: {name}")
    path = allowed[name]
    if ROOT not in path.resolve().parents:
        raise ValueError(f"log path escapes repository root: {path}")
    return path.open("w", encoding="utf-8")


def kill_process_tree(pid: int) -> bool:
    """Terminate a process and all of its descendants.

    Returns True when the OS accepted the termination request (or the pid was
    falsy / already gone) and False when the kill was REFUSED (e.g. taskkill
    "Access is denied" against an elevated stale process). Callers must treat
    False as "this listener may still be alive" — a silent False previously
    let the boot proceed into a hijacked port (audit-20260930-131350: the
    dashboard proxy test answered plain-text 500 from a zombie bun on
    0.0.0.0:3000 while the fresh Next dev could only bind IPv6).

    [fix 2026-09-30 zombie-wmi-fallback] Observed live: taskkill /F /T refused
    an orphaned same-user bun zombie (dashboard on 0.0.0.0:3000, bridge on
    8081) with "Access is denied", leaving the hijacked-port condition in
    place, while WMI Win32_Process.Terminate on the exact same PID succeeded
    (ReturnValue 0) and the ports went free. taskkill's refusal is therefore
    not treated as the final verdict on Windows: before giving up, the WMI
    terminate path is attempted. This is strictly MORE cleanup capability —
    the post-kill survivor re-query in clean_ports (fail-closed OccupiedPortError)
    remains the real gate, and the "Access is denied" fallback can never turn a
    surviving listener into a green result.
    """
    if not pid:
        return True
    if sys.platform == "win32":
        res = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return True
        return _wmi_terminate_pid(pid)
    import signal
    try:
        os.kill(pid, signal.SIGKILL)
        return True
    except OSError:
        return False


def _wmi_terminate_pid(pid: int) -> bool:
    """Kill one PID via WMI Win32_Process.Terminate (Windows fallback).

    taskkill can be refused ("Access is denied") against an orphaned stale
    process even when the caller and the process share the same user (seen
    live 2026-09-30: bun zombies from a prior E2E run on 0.0.0.0:3000 /
    127.0.0.1:8081). WMI Terminate took the same PIDs down (ReturnValue 0),
    so it is the verified fallback of last resort. Fail-closed: only an
    explicit ReturnValue==0 counts as success — a missing process, a WMI
    error, or any non-zero result returns False and the caller's survivor
    re-query decides the verdict.
    """
    try:
        res = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Invoke-CimMethod -Query "
                f"'SELECT * FROM Win32_Process WHERE ProcessId={int(pid)}' "
                "-MethodName Terminate).ReturnValue -eq 0",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    return res.returncode == 0 and res.stdout.strip().lower().startswith("true")


# [FA-11 docker-backend protection, 2026-10-01] Port 8000 is the SCP API port,
# but it is ALSO the default publish port of a live `docker compose` deployment.
# When a Docker-published listener holds 8000, the owning process on Windows is
# Docker Desktop's backend (com.docker.backend.exe) — killing its process tree
# terminates Docker Desktop itself. This was observed twice for real in audit
# wave 1 (Docker Desktop died twice after clean_ports). These listeners must be
# IDENTIFIED and SKIPPED, never killed; the survivor re-query then fails the
# boot fail-closed instead of taking the Docker daemon down.
DOCKER_BACKEND_IDENTITY_MARKERS = (
    "com.docker.backend",
    "com.docker.build",
    "com.docker.dev-envs",
    "vpnkit",
    "docker-proxy",
    "docker desktop",
)
DOCKER_BACKEND_PATH_MARKERS = (
    "docker desktop",
    "docker\\resources",
    "docker/resources",
)


def is_docker_backend_identity(identity: str) -> bool:
    """Pure marker matcher over a process identity blob (name+path+cmdline).

    Kept separate from the OS query so unit tests can exercise the matching
    logic against fake command lines without spawning processes.
    """
    blob = identity.lower()
    if not blob:
        return False
    if any(marker in blob for marker in DOCKER_BACKEND_IDENTITY_MARKERS):
        return True
    return any(marker in blob for marker in DOCKER_BACKEND_PATH_MARKERS)


def get_process_identity(pid: int) -> str:
    """Return a lowercase 'name path commandline' blob for pid (best effort).

    Returns '' when the process cannot be inspected (gone, denied, non-Windows
    without /proc) — the caller then treats the process as NOT a Docker backend
    (identity unknown is never used to justify a kill of a live listener; the
    survivor re-query remains the fail-closed gate).
    """
    if sys.platform == "win32":
        cmd = (
            "$p = Get-CimInstance Win32_Process -Filter "
            f"'ProcessId={int(pid)}'; "
            "if ($p) { @($p.Name; $p.ExecutablePath; $p.CommandLine) -join ' ' }"
        )
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, ValueError, subprocess.SubprocessError):
            return ""
        return " ".join((res.stdout or "").lower().split())
    try:
        comm = (Path(f"/proc/{int(pid)}") / "comm").read_text(errors="replace")
        cmdline = (Path(f"/proc/{int(pid)}") / "cmdline").read_text(errors="replace")
    except OSError:
        return ""
    return " ".join((" ".join(comm.split()) + " " + " ".join(cmdline.split())).lower().split())


def is_docker_backend_process(pid: int) -> bool:
    """True when the PID's identity matches Docker backend markers."""
    return is_docker_backend_identity(get_process_identity(pid))


def get_listening_pids(ports: tuple[int, ...] = TARGET_PORTS) -> set[int]:
    """Retrieve PIDs listening on any of the target ports."""
    pids: set[int] = set()
    if sys.platform == "win32":
        port_csv = ",".join(str(p) for p in ports)
        cmd = f"Get-NetTCPConnection -LocalPort {port_csv} -State Listen -ErrorAction SilentlyContinue | ForEach-Object {{ $_.OwningProcess }}"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
        for line in res.stdout.splitlines():
            val = line.strip()
            if val.isdigit() and int(val) > 0:
                pids.add(int(val))
    else:
        for port in ports:
            res = subprocess.run(["lsof", "-t", f"-i:{port}"], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                val = line.strip()
                if val.isdigit():
                    pids.add(int(val))
    return pids


def clean_ports(ports: tuple[int, ...] = TARGET_PORTS) -> None:
    """Force kill all processes holding any target port, then VERIFY the kill.

    Gated by SCP_SMOKE_PORT_CLEAN (default '1' = historical behavior). With
    '0' the cleaner REFUSES to kill: when any target port is occupied it
    raises OccupiedPortError naming the owning PID(s) so the run fails loudly
    instead of killing a co-located service.

    [FA-11 docker-backend protection, 2026-10-01] A listener whose process
    identity matches Docker backend markers (com.docker.backend, vpnkit,
    docker-proxy, com.docker.build/dev-envs, Docker Desktop install path) is
    NEVER killed: the kill would terminate Docker Desktop itself (observed
    twice for real in audit wave 1 when a `docker compose` deployment held
    port 8000). Protected listeners are skipped with a clear log; the
    post-kill survivor re-query then raises OccupiedPortError (fail-closed)
    naming the protected PID(s) instead of booting over them.

    [audit-20260930-131350 fix] With the default gate the kill is no longer
    trusted blindly: taskkill can be refused ("Access is denied") against an
    elevated stale process, and Windows keeps delivering new IPv4 connections
    to the old 0.0.0.0 listener even after another process binds the port.
    The cleaner therefore re-queries the listeners after the kill pass and
    raises OccupiedPortError (fail-closed) if anything survived — booting on
    top of a zombie makes the readiness probes pass against the STALE
    services while the functional probes hit the zombie (the dashboard-proxy
    step of the audit failed with a plain-text 500 this way).
    """
    pids = get_listening_pids(ports)
    if pids and not port_clean_enabled():
        raise OccupiedPortError(
            f"SCP_SMOKE_PORT_CLEAN=0: refusing to kill listener(s) on ports {ports}; "
            f"owning PID(s): {sorted(pids)}"
        )
    refused: dict[int, str] = {}
    protected: dict[int, str] = {}
    for pid in pids:
        if is_docker_backend_process(pid):
            protected[pid] = "docker backend (protected: killing it terminates Docker Desktop)"
            print(
                f"[clean_ports] SKIP PID {pid}: identity matches Docker backend markers "
                "(com.docker.backend/vpnkit/docker-proxy/Docker Desktop). Killing it would "
                "terminate Docker Desktop itself (FA-11, observed 2x in wave 1). This "
                "listener is NOT killed; the boot will fail closed on the survivor check "
                "until the publishing container is stopped."
            )
            continue
        if not kill_process_tree(pid):
            refused[pid] = "kill request was refused (e.g. taskkill access denied)"
    time.sleep(1)
    survivors = get_listening_pids(ports)
    if survivors:
        detail = f"; kill failures: {refused}" if refused else ""
        if protected:
            detail += (
                f"; protected docker backend listener(s): {sorted(protected)} — NOT killed "
                "to keep Docker Desktop alive; free the port by stopping the publishing "
                "container (e.g. docker compose stop) or set SCP_SMOKE_PORT_CLEAN=0"
            )
        raise OccupiedPortError(
            f"Target ports {ports} still occupied after clean: surviving listener "
            f"PID(s) {sorted(survivors)}{detail}. Boot refused fail-closed: readiness "
            "probes would be answered by these stale processes instead of the services "
            "this run spawns (zombie-port hijack). Stop the listed process(es) from an "
            "elevated shell (or reboot the host) and re-run the smoke."
        )


def verify_ports_free(ports: tuple[int, ...] = TARGET_PORTS) -> bool:
    """Return True if no listener exists on any target port."""
    pids = get_listening_pids(ports)
    return len(pids) == 0


def load_env_token() -> str:
    """Load canonical auth token from .env file or environment."""
    # An explicit env boundary is authoritative.  Do not fall back to the
    # repository .env when an isolated test/runtime file was requested: that
    # could silently inject a real operator credential into a local probe.
    configured_env = os.environ.get("SCP_ENV_FILE", "").strip()
    env_file = Path(configured_env).expanduser() if configured_env else ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k in ("SCP_AUTH_TOKEN_SECRET", "SCP_ADMIN_KEY", "SCP_AUTH_PASSWORD") and v:
                return v
    token = (
        os.environ.get("SCP_AUTH_TOKEN_SECRET")
        or os.environ.get("SCP_ADMIN_KEY")
        or os.environ.get("SCP_AUTH_PASSWORD")
        or os.environ.get("SCP_ADMIN_TOKEN", "")
    )
    if not token:
        raise ValueError("SCP_ADMIN_TOKEN must be set")
    return token


async def run_e2e_verification() -> dict[str, Any]:
    """Execute complete cluster boot, verification, and teardown."""
    print("=== [1/5] Pre-cleaning ports (8000, 8081, 3000) ===")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    clean_ports(TARGET_PORTS)

    token = load_env_token()
    env = dict(os.environ)
    env["SCP_AUTH_TOKEN_SECRET"] = token
    env["SCP_ADMIN_KEY"] = token
    env["SCP_PORT"] = "8000"
    env["SCP_HOST"] = "127.0.0.1"

    spawned_procs: list[subprocess.Popen] = []
    file_handles: list[Any] = []
    verification_summary: dict[str, Any] = {
        "success": False,
        "bridge_ready": False,
        "server_ready": False,
        "dashboard_ready": False,
        "trace_id": None,
        "trace_record_verified": False,
        "secret_redacted": False,
        "unauth_blocked_401": False,
        "dashboard_proxy_verified": False,
        "ports_free": False,
    }

    try:
        # --- 1. Spawn LLM Bridge on 8081 ---
        print("=== [2/5] Booting services: LLM Bridge, SCP Server, Web Dashboard ===")
        bridge_log = _open_service_log("llm-bridge.log")
        file_handles.append(bridge_log)
        b_env = dict(env, SCP_LLM_BRIDGE_PORT="8081", ZAI_BRIDGE_PORT="8081", ZAI_BRIDGE_HOST="127.0.0.1")
        p_bridge = subprocess.Popen(
            ["bun", "run", "dev"],
            cwd=str(ROOT / "mini-services" / "llm-bridge"),
            env=b_env,
            stdout=bridge_log,
            stderr=bridge_log,
        )
        spawned_procs.append(p_bridge)

        # --- 2. Spawn SCP Python Server on 8000 ---
        server_log = _open_service_log("scp-server.log")
        file_handles.append(server_log)
        s_env = dict(env, SCP_PORT="8000", SCP_HOST="127.0.0.1")
        p_server = subprocess.Popen(
            [sys.executable, "-m", "scp", "8000"],
            cwd=str(ROOT),
            env=s_env,
            stdout=server_log,
            stderr=server_log,
        )
        spawned_procs.append(p_server)

        # --- 3. Spawn Web Dashboard on 3000 ---
        dash_log = _open_service_log("dashboard.log")
        file_handles.append(dash_log)
        # [P2-06 fix] The dashboard fail-closes its gated API in production
        # when no proxy secret is configured. The E2E harness stands in for
        # the reverse proxy: it holds the secret and injects the
        # x-scp-proxy-secret header on proxied calls below.
        d_env = dict(
            env,
            PORT="3000",
            SCP_INTERNAL_URL="http://127.0.0.1:8000",
            LLM_BRIDGE_URL="http://127.0.0.1:8081",
            SCP_DASHBOARD_PROXY_SECRET="e2e-proxy-secret-12345",
            SCP_AUTH_TOKEN_SECRET=token,
        )
        p_dash = subprocess.Popen(
            ["bun", "run", "dev"],
            cwd=str(ROOT / "dashboard"),
            env=d_env,
            stdout=dash_log,
            stderr=dash_log,
        )
        spawned_procs.append(p_dash)

        # --- 4. Readiness Polling ---
        print("=== [3/5] Polling health endpoints with strict deadlines ===")
        async with httpx.AsyncClient(timeout=3.0) as client:
            # Probe Bridge (8081) - /health or /api/tags
            for _ in range(25):
                try:
                    r = await client.get("http://127.0.0.1:8081/health")
                    if r.status_code == 200:
                        verification_summary["bridge_ready"] = True
                        break
                    r2 = await client.get("http://127.0.0.1:8081/api/tags")
                    if r2.status_code == 200:
                        verification_summary["bridge_ready"] = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(1)
            if p_bridge.poll() is not None:
                # [audit-20260930-131350 fix] A spawn that died at boot (e.g.
                # EADDRINUSE against an uncleaned stale listener) must fail
                # with its own cause, never as a generic readiness timeout.
                raise AssertionError(
                    "LLM Bridge process exited before becoming ready — see data/service-logs/llm-bridge.log"
                )
            assert verification_summary["bridge_ready"], "LLM Bridge failed to reach HTTP 200 on port 8081 within deadline"
            print("  -> LLM Bridge (8081) READY [HTTP 200]")

            # Probe SCP Server (8000) - /health
            for _ in range(45):
                try:
                    r = await client.get("http://127.0.0.1:8000/health")
                    if r.status_code == 200:
                        verification_summary["server_ready"] = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(1)
            if p_server.poll() is not None:
                raise AssertionError(
                    "SCP API Server process exited before becoming ready — see data/service-logs/scp-server.log"
                )
            assert verification_summary["server_ready"], "SCP API Server failed to reach HTTP 200 on port 8000 within deadline"
            print("  -> SCP Server (8000) READY [HTTP 200]")

            # Probe Web Dashboard (3000) - /
            for _ in range(45):
                try:
                    r = await client.get("http://127.0.0.1:3000/")
                    if r.status_code in (200, 304):
                        verification_summary["dashboard_ready"] = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(1)
            if p_dash.poll() is not None:
                raise AssertionError(
                    "Web Dashboard process exited before becoming ready — see data/service-logs/dashboard.log"
                )
            assert verification_summary["dashboard_ready"], "Web Dashboard failed to reach HTTP 200 on port 3000 within deadline"
            print("  -> Web Dashboard (3000) READY [HTTP 200]")

            # --- 5. Live Chat Interaction & Trace Extraction ---
            print("=== [4/5] Testing live chat, trace provenance, redaction & 401 auth boundary ===")
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            chat_payload = {
                "model": "scp-standard",
                "messages": [{"role": "user", "content": "What is 2+2?"}],
            }
            chat_resp = await client.post(
                "http://127.0.0.1:8000/v1/chat/completions",
                headers=headers,
                json=chat_payload,
                timeout=30.0,
            )
            assert chat_resp.status_code == 200, f"Chat failed with status {chat_resp.status_code}: {chat_resp.text}"
            chat_data = chat_resp.json()
            trace_id = chat_data.get("trace_id") or chat_resp.headers.get("X-SCP-Trace-ID")
            assert trace_id, f"No trace_id returned in chat response: body={chat_data}"
            verification_summary["trace_id"] = trace_id
            print(f"  -> Live chat completed successfully. Extracted trace_id: {trace_id}")

            # --- 6. Query GET /v3/trace/{trace_id} with Admin Auth ---
            trace_resp = await client.get(
                f"http://127.0.0.1:8000/v3/trace/{trace_id}",
                headers=headers,
                timeout=10.0,
            )
            assert trace_resp.status_code == 200, f"Authenticated trace lookup failed with status {trace_resp.status_code}"
            trace_record = trace_resp.json()
            assert trace_record.get("trace_id") == trace_id or trace_id in str(trace_record), (
                f"Trace record mismatch: expected {trace_id}, got {trace_record}"
            )
            verification_summary["trace_record_verified"] = True
            print(f"  -> GET /v3/trace/{trace_id} returned HTTP 200 with matching trace record")

            # Verify credential redaction: raw token must NOT appear in the response payload
            assert token not in trace_resp.text, "CRITICAL: Secret token leaked in trace response payload!"
            verification_summary["secret_redacted"] = True
            print("  -> Sensitive attribute redaction verified: zero token leakage in trace payload")

            # --- 7. Verify Fail-Closed Security Boundary (Unauthenticated) ---
            unauth_resp = await client.get(f"http://127.0.0.1:8000/v3/trace/{trace_id}", timeout=10.0)
            assert unauth_resp.status_code == 401, (
                f"Expected HTTP 401 for unauthenticated trace query, got {unauth_resp.status_code}"
            )
            verification_summary["unauth_blocked_401"] = True
            print("  -> Unauthenticated GET /v3/trace/{trace_id} correctly returned HTTP 401 Unauthorized")

            # --- 8. Verify Dashboard Next.js API Proxy ---
            # [P2-06 fix] harness = trusted reverse proxy (injects the secret)
            dash_headers = {
                "Authorization": f"Bearer {token}",
                "X-Forwarded-For": "127.0.0.1",
                "x-scp-proxy-secret": "e2e-proxy-secret-12345",
            }
            dash_proxy_resp = await client.get(
                f"http://127.0.0.1:3000/api/scp/v3/trace/{trace_id}",
                headers=dash_headers,
                timeout=15.0,
            )
            assert dash_proxy_resp.status_code == 200, f"Dashboard proxy failed with status {dash_proxy_resp.status_code}: {dash_proxy_resp.text}"
            dash_proxy_data = dash_proxy_resp.json()
            assert dash_proxy_data.get("trace_id") == trace_id or trace_id in str(dash_proxy_data)
            verification_summary["dashboard_proxy_verified"] = True
            print("  -> Dashboard Next.js trace proxy verified [HTTP 200, caller token forwarded]")

            # Verify that dashboard proxy rejects unauthenticated requests (fail-closed, no auto-injected credential)
            dash_unauth = await client.get(
                f"http://127.0.0.1:3000/api/scp/v3/trace/{trace_id}",
                headers={
                    "X-Forwarded-For": "127.0.0.1",
                    # proxy gate satisfied; backend auth still rejects (401)
                    "x-scp-proxy-secret": "e2e-proxy-secret-12345",
                },
                timeout=15.0,
            )
            assert dash_unauth.status_code == 401, f"Expected 401 from dashboard proxy without auth, got {dash_unauth.status_code}"
            print("  -> Dashboard Next.js trace proxy correctly rejected unauthenticated request [HTTP 401]")

            verification_summary["success"] = True

    finally:
        # --- 9. Clean Shutdown & Process Tree Kill ---
        print("=== [5/5] Shutting down cluster and verifying zero zombie processes ===")
        for proc in spawned_procs:
            try:
                kill_process_tree(proc.pid)
            except Exception:
                pass
        for fh in file_handles:
            try:
                fh.close()
            except Exception:
                pass

        try:
            clean_ports(TARGET_PORTS)
        except OccupiedPortError as exc:
            # SCP_SMOKE_PORT_CLEAN=0: a foreign listener is still holding a
            # port — report it (with PID) and let verify_ports_free below fail
            # the run; never kill it.
            print(f"  [SKIPPED] port clean refused: {exc}")
        ports_free = verify_ports_free(TARGET_PORTS)
        verification_summary["ports_free"] = ports_free
        if not ports_free:
            print("  [ERROR] Lingering listeners detected on target ports!")
        else:
            print("  -> All target ports (8000, 8081, 3000) completely free. Zero zombie processes.")

    return verification_summary


def main() -> None:
    """CLI entrypoint."""
    try:
        result = asyncio.run(run_e2e_verification())
        print("\n============================================================")
        print("  [RESULT] Live Cluster E2E Verification Complete")
        print("============================================================")
        print(json.dumps(result, indent=2))
        if not result.get("success") or not result.get("ports_free"):
            sys.exit(1)
        sys.exit(0)
    except Exception as exc:
        print(f"\n[E2E FATAL ERROR] {exc}", file=sys.stderr)
        if port_clean_enabled():
            clean_ports(TARGET_PORTS)
        sys.exit(1)


if __name__ == "__main__":
    main()
