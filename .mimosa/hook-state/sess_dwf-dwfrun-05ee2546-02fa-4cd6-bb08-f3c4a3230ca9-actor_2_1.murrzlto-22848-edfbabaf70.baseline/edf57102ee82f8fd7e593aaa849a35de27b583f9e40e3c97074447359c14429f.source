#!/usr/bin/env python3
"""SCP-level acceptance suite.

This suite asks one question only: does the assembled SCP runtime preserve its
critical invariants when exercised through real process, HTTP, persistence and
failure boundaries?

It deliberately does not assert implementation details such as concrete model
names or private helper calls.  Unit/component tests remain diagnostic tools;
this runner emits the release-level behavioral evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import secrets
import socket
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUTPUT = ROOT / "reports" / "scp_acceptance_ci"
EXPECTED_SCENARIOS = tuple(f"SCP-A{number:02d}" for number in range(1, 13))
PROCESS_ENV_KEYS = frozenset({
    "PATH", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "PATHEXT",
    "TEMP", "TMP", "TMPDIR", "USERPROFILE", "LOCALAPPDATA", "APPDATA",
    "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "ALLUSERSPROFILE",
    "LANG", "LC_ALL", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE",
})
LOCAL_FALLBACK_SPEC = (
    "acceptance-independent:ACCEPTANCE_PROVIDER_KEY:"
    "ACCEPTANCE_PROVIDER_BASE_URL:ACCEPTANCE_PROVIDER_MODEL"
)

# Runtime-assembled credential for the loopback mock provider: the provider
# fixture never validates it, so a per-run random value is equivalent, and no
# credential-shaped literal sits in source. Mirrors the SECRET precedent in
# tests/T02_contract/test_llm_bridge_cache_auth.py.
MOCK_OPENROUTER_KEY = "acceptance-mock-" + secrets.token_hex(8)


class AcceptanceFailure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceFailure(message)


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def wait_port_free(port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not port_open(port):
            return True
        time.sleep(0.1)
    return not port_open(port)


def stable_task_id(idempotency_key: str, payload: dict[str, Any]) -> str:
    # [S19 mirror sync 2026-09-13] Derive the durable ask identity through the
    # product function (AskKernelAdapter.task_id_for) instead of a private
    # re-implementation of the hash formula. The old copy mirrored the
    # pre-fix server bug ("key replaces the question hash"); a mirror that
    # re-implements derivation is exactly how harness and product drift
    # apart. Assertions stay equally strict — same exact-ID lookup, same
    # journal verification.
    from scp.ask_kernel_adapter import AskKernelAdapter

    return AskKernelAdapter.task_id_for(
        payload["question"],
        list(payload.get("contexts") or []),
        str(payload.get("retrieved_context") or ""),
        payload.get("session_id"),
        idempotency_key,
    )


class ProviderController:
    """Deterministic loopback provider used as an external test double."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.mode = "pass"
        self.delay_seconds = 0.0
        self.calls: list[dict[str, Any]] = []

    def configure(self, mode: str, delay_seconds: float = 0.0) -> None:
        with self._lock:
            self.mode = mode
            self.delay_seconds = delay_seconds
            self.calls.clear()

    def snapshot(self) -> tuple[str, float]:
        with self._lock:
            return self.mode, self.delay_seconds

    def record(self, model: str, prompt: str) -> None:
        with self._lock:
            self.calls.append({"model": model, "prompt": prompt[:600], "ts": time.time()})

    def call_summary(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self.calls]


class ProviderFixture:
    def __init__(self, port: int) -> None:
        self.port = port
        self.controller = ProviderController()
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if port_open(self.port):
            raise RuntimeError(f"provider fixture port {self.port} already in use")
        controller = self.controller

        class Handler(BaseHTTPRequestHandler):
            server_version = "SCPAcceptanceProvider/1"

            def log_message(self, _format: str, *_args: object) -> None:
                return

            def _json(self, status: int, payload: dict[str, Any]) -> None:
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                try:
                    self.end_headers()
                    self.wfile.write(raw)
                except (ConnectionResetError, BrokenPipeError):
                    pass

            def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except Exception:
                    payload = {}
                model = str(payload.get("model", ""))
                messages = payload.get("messages") or []
                prompt = "\n".join(str(item.get("content", "")) for item in messages if isinstance(item, dict))
                controller.record(model, prompt)
                mode, delay = controller.snapshot()
                if delay > 0:
                    time.sleep(delay)
                if mode == "fail_all":
                    self._json(503, {"error": {"message": "acceptance provider unavailable"}})
                    return
                if mode == "fail_primary" and "primary" in model:
                    self._json(503, {"error": {"message": "controlled primary failure"}})
                    return
                content = "PASS"
                if mode == "semantic" and "100 degrees Celsius" in prompt and "zero degrees Celsius" in prompt:
                    content = "FAIL"
                self._json(
                    200,
                    {
                        "id": "acceptance-completion",
                        "object": "chat.completion",
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": content},
                                "finish_reason": "stop",
                            }
                        ],
                    },
                )

        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="scp-acceptance-provider")
        self.thread.start()

    def stop(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)
        self.server = None
        self.thread = None


class RuntimeHarness:
    def __init__(self, output_dir: Path, port: int, provider_port: int) -> None:
        self.output_dir = output_dir
        self.independent_provider_port = provider_port + 1
        ports = (port, provider_port, self.independent_provider_port)
        if len(set(ports)) != 3 or any(not 1 <= value <= 65535 for value in ports):
            raise ValueError("acceptance requires three distinct valid local ports")
        if output_dir.exists() and any(output_dir.iterdir()):
            raise FileExistsError("refusing to overwrite existing acceptance evidence; output directory must be empty")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.port = port
        self.provider_port = provider_port
        self.base = f"http://127.0.0.1:{port}"
        self.process: subprocess.Popen[str] | None = None
        self.generation = 0
        self.token: str | None = None
        self.db_path = output_dir / "ask_task_kernel.sqlite3"
        self.trace_path = output_dir / "ask_task_kernel_trace.jsonl"
        self.env_path = output_dir / "empty.env"
        self.env_path.touch(exist_ok=False)

    def environment(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items() if key.upper() in PROCESS_ENV_KEYS}
        env.update(
            {
                "PYTHONPATH": str(ROOT),
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
                "SCP_HOST": "127.0.0.1",
                "SCP_PORT": str(self.port),
                "PORT": str(self.port),
                "SCP_MODE": "test",
                "SCP_API_PROFILE": "full",
                "SCP_PRODUCTION_MODE": "0",
                "SCP_DEV_MODE": "0",
                "SCP_SKIP_STARTUP_GATE": "0",
                "SCP_FAST_LEARNING_THREAD": "0",
                "SCP_AUTOFIX_MODE": "observe",
                "SCP_EVOLUTION_AUTO": "0",
                "SCP_EGRESS_MODE": "deny",
                "SCP_WEB_FALLBACK": "0",
                "SCP_ASK_KERNEL_ENABLED": "1",
                "SCP_KERNEL_DB_PATH": str(self.db_path),
                "SCP_KERNEL_TRACE_PATH": str(self.trace_path),
                "SCP_DATA_DIR": str(self.output_dir),
                "SCP_REQUEST_RUN_LEDGER_PATH": str(self.output_dir / "request_runs.jsonl"),
                "SCP_CHAT_MEMORY_PATH": str(self.output_dir / "chat_memory.jsonl"),
                "SCP_TRACE_STORE_PATH": str(self.output_dir / "trace_store.sqlite3"),
                "SCP_HANDS_LOCAL_ONLY": "1",
                "SCP_ENV_FILE": str(self.env_path),
                "SCP_SIDECAR_ENV_FILE": str(self.env_path),
                "SCP_PC_CONTROLLER_TOKEN": "acceptance-pc-token",
                "SCP_JWT_SECRET": "acceptance-jwt-secret-not-for-production",
                "SCP_ADMIN_KEY": "acceptance-admin-key",
                "SCP_CAPABILITY_SECRET": "acceptance-test-capability-secret-32bytes",
                "OPENROUTER_API_KEY": MOCK_OPENROUTER_KEY,
                "OPENROUTER_BASE_URL": f"http://127.0.0.1:{self.provider_port}/v1",
                "OPENROUTER_MODEL": "acceptance-chat-primary",
                "OPENROUTER_MODEL_CHAT": "acceptance-chat-fallback",
                "OPENROUTER_MODEL_JUDGE": "acceptance-judge-fallback",
                "OPENROUTER_MODEL_JUDGE_PRIMARY": "acceptance-judge-primary",
                "OPENROUTER_MODEL_AUTOFIX": "acceptance-autofix-fallback",
                "OPENAI_API_KEY": "",
                "OPENAI_BASE_URL": f"http://127.0.0.1:{self.independent_provider_port}/v1",
                "OPENAI_MODEL": "acceptance-judge-secondary",
                "SCP_LLM_FALLBACK_PROVIDERS": LOCAL_FALLBACK_SPEC,
                "ACCEPTANCE_PROVIDER_KEY": "acceptance-independent-key",
                "ACCEPTANCE_PROVIDER_BASE_URL": f"http://127.0.0.1:{self.independent_provider_port}/v1",
                "ACCEPTANCE_PROVIDER_MODEL": "acceptance-independent-model",
                "SCP_MULTI_LLM_CROSSCHECK": "1",
                "SCP_LLM_BREAKER_THRESHOLD": "3",
                "SCP_LLM_BREAKER_COOLDOWN_SEC": "1",
            }
        )
        return env

    def start(self, timeout: float = 90.0) -> None:
        if self.process is not None:
            raise RuntimeError("SCP runtime already started")
        if port_open(self.port):
            raise RuntimeError(f"SCP acceptance port {self.port} already in use")
        self.generation += 1
        log_path = self.output_dir / f"scp-server-{self.generation}.log"
        log_handle = log_path.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "scp", str(self.port)],
            cwd=self.output_dir,
            env=self.environment(),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        setattr(self.process, "_acceptance_log_handle", log_handle)
        deadline = time.time() + timeout
        last_error = "not reachable"
        healthy = False
        while time.time() < deadline:
            if self.process.poll() is not None:
                break
            try:
                response = requests.get(f"{self.base}/health", timeout=2)
                if response.status_code == 200:
                    healthy = True
                    break
                last_error = f"health={response.status_code}"
            except requests.RequestException as exc:
                last_error = type(exc).__name__
            time.sleep(0.4)
        if not healthy:
            code = self.process.poll()
            self.stop(force=True)
            raise RuntimeError(f"SCP failed to become live: process={code}, last={last_error}, log={log_path}")

        ready_deadline = time.time() + 30.0
        ready = False
        while time.time() < ready_deadline:
            if self.process.poll() is not None:
                break
            try:
                response = requests.get(f"{self.base}/ready", timeout=2)
                if response.status_code == 200:
                    ready = True
                    break
                last_error = f"ready={response.status_code}"
            except requests.RequestException as exc:
                last_error = type(exc).__name__
            time.sleep(0.4)
        if not ready:
            code = self.process.poll()
            self.stop(force=True)
            raise RuntimeError(f"SCP failed to become ready: process={code}, last={last_error}, log={log_path}")

        self.login()
        return

    def stop(self, force: bool = False) -> None:
        process = self.process
        self.process = None
        self.token = None
        if process is None:
            return
        try:
            if process.poll() is None:
                if force:
                    process.kill()
                else:
                    process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        finally:
            log_handle = getattr(process, "_acceptance_log_handle", None)
            if log_handle is not None:
                log_handle.close()
        if not wait_port_free(self.port):
            raise RuntimeError(f"SCP port {self.port} remained open after stop")

    def login(self) -> None:
        response = requests.post(
            f"{self.base}/auth/token",
            json={"admin_key": "acceptance-admin-key"},
            timeout=10,
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise RuntimeError("auth/token returned no access_token")
        self.token = str(token)

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        auth: bool = True,
        pc_token: bool = False,
        idempotency_key: str | None = None,
        timeout: float = 45.0,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if auth:
            if not self.token:
                raise RuntimeError("runtime auth token unavailable")
            headers["Authorization"] = f"Bearer {self.token}"
        if pc_token:
            headers["X-SCP-PC-Token"] = "acceptance-pc-token"
        if idempotency_key:
            headers["X-SCP-Idempotency-Key"] = idempotency_key
        response = requests.request(
            method,
            f"{self.base}{path}",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        try:
            body: Any = response.json()
        except ValueError:
            body = None
        return {"status": response.status_code, "body": body, "text": response.text[:1200]}


class AcceptanceSuite:
    def __init__(self, output_dir: Path, port: int, provider_port: int, concurrency: int) -> None:
        self.output_dir = output_dir
        self.port = port
        self.provider_port = provider_port
        self.concurrency = concurrency
        self.provider = ProviderFixture(provider_port)
        self.runtime = RuntimeHarness(output_dir, port, provider_port)
        self.independent_provider = ProviderFixture(self.runtime.independent_provider_port)
        self.scenarios: list[dict[str, Any]] = []
        self.report_path = output_dir / "acceptance.json"

    def configure_providers(self, mode: str, delay_seconds: float = 0.0) -> None:
        for fixture in (self.provider, self.independent_provider):
            fixture.controller.configure(mode, delay_seconds)

    def provider_calls(self) -> list[dict[str, Any]]:
        return [dict(call, fixture_port=fixture.port)
                for fixture in (self.provider, self.independent_provider)
                for call in fixture.controller.call_summary()]

    def _write_report(self, final: bool = False) -> None:
        passed = sum(1 for scenario in self.scenarios if scenario["passed"])
        report = {
            "schema_version": "scp-acceptance-v1",
            "commit": self._commit(),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "runtime_port": self.port,
            "provider_fixture_port": self.provider_port,
            "total": len(self.scenarios),
            "passed": passed,
            "failed": len(self.scenarios) - passed,
            "overall_pass": final and passed == len(EXPECTED_SCENARIOS)
                and sorted(scenario["id"] for scenario in self.scenarios) == list(EXPECTED_SCENARIOS),
            "evidence_scope": "process/HTTP/storage with two synthetic provider-family fixtures",
            "independent_provider_fixture_port": self.independent_provider.port,
            "final": final,
            "scenarios": self.scenarios,
        }
        self.report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _commit() -> str:
        try:
            return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        except Exception:
            return "unknown"

    def scenario(self, scenario_id: str, title: str, fn: Callable[[], dict[str, Any] | None]) -> None:
        start = time.perf_counter()
        record: dict[str, Any] = {"id": scenario_id, "title": title, "critical": True, "passed": False}
        try:
            evidence = fn() or {}
            record["passed"] = True
            record["evidence"] = evidence
        except Exception as exc:
            record["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(limit=8),
            }
        record["duration_ms"] = round((time.perf_counter() - start) * 1000, 1)
        self.scenarios.append(record)
        self._write_report(final=False)
        status = "PASS" if record["passed"] else "FAIL"
        print(f"[{status}] {scenario_id} {title}", flush=True)

    def _task(self, idempotency_key: str, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        from scp.task_kernel import TaskKernel

        kernel = TaskKernel(self.runtime.db_path)
        try:
            task_id = stable_task_id(idempotency_key, payload)
            task = kernel.get_task(task_id)
            journal = kernel.verify_journal(task_id)
            return task, journal
        finally:
            kernel.close()

    def _wait_task(
        self,
        idempotency_key: str,
        states: set[str],
        payload: dict[str, Any],
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        from scp.task_kernel import TaskKernel

        task_id = stable_task_id(idempotency_key, payload)
        deadline = time.time() + timeout
        last: dict[str, Any] | None = None
        while time.time() < deadline:
            kernel = TaskKernel(self.runtime.db_path)
            try:
                try:
                    last = kernel.get_task(task_id)
                except Exception:
                    last = None
            finally:
                kernel.close()
            if last and last.get("state") in states:
                return last
            time.sleep(0.05)
        raise AcceptanceFailure(f"task {task_id} did not enter {sorted(states)}; last={last}")

    def _recover_judge_breakers(self, timeout: float = 30.0) -> dict[str, Any]:
        """Wait (bounded) for the LLM provider breakers to recover.

        TẠI SAO: SCP-A06 deliberately causes a total provider outage, which
        OPENS the per-provider circuit breakers (correct fail-closed product
        behavior, cooldown=1s in this suite's env). Scenarios that need a full
        judge cascade (SCP-A08's race winner must be verified by two distinct
        provider families) are only meaningful once the breakers have re-closed
        via their half-open probes. Without this gate the A08 winner depends on
        sub-second wall-clock luck after A06 (observed on GitHub runners: the
        openrouter family was still breaker-blocked and the winner escalated).
        This proves nothing less: A08 still requires exactly one PASS/one FAIL
        across a real concurrent race; a never-recovering gateway fails the
        scenario loudly (fail-closed), it is never skipped.
        """
        recovery_payload = self.verified_payload("breaker-recovery")
        deadline = time.time() + timeout
        attempts: list[dict[str, Any]] = []
        attempt = 0
        recovered = False
        while time.time() < deadline:
            attempt += 1
            response = self.runtime.request(
                "POST",
                "/ask",
                payload=recovery_payload,
                idempotency_key=f"scp-breaker-recovery-{attempt}",
                timeout=60,
            )
            body = response["body"] or {}
            attempts.append({
                "attempt": attempt,
                "status": response["status"],
                "verdict": body.get("verdict"),
            })
            if response["status"] == 200 and body.get("verdict") == "PASS":
                recovered = True
                break
            time.sleep(0.5)
        cancelled_leftovers = self._cancel_recovery_leftovers(attempt)
        if not recovered:
            raise AcceptanceFailure(
                f"judge providers did not recover after outage scenario "
                f"(no verified PASS within {timeout:.0f}s): {attempts}"
            )
        return {
            "recovered_on_attempt": attempt,
            "attempts": attempts,
            "escalated_leftovers_cancelled": cancelled_leftovers,
        }

    def _cancel_recovery_leftovers(self, attempts_made: int) -> list[str]:
        """Resolve recovery attempts that ended in HUMAN_REVIEW.

        An attempt made while a breaker is still open escalates (explicit
        unresolved evidence) and would otherwise extend the A12 exact
        nonterminal set. HUMAN_REVIEW -> CANCELLED is a legal product
        transition; the suite exercises it as the human authority that closes
        its own probe evidence. Every other state is terminal already.
        """
        from scp.task_kernel import TaskKernel

        cancelled: list[str] = []
        payload = self.verified_payload("breaker-recovery")
        kernel = TaskKernel(self.runtime.db_path)
        try:
            for attempt in range(1, attempts_made + 1):
                task_id = stable_task_id(f"scp-breaker-recovery-{attempt}", payload)
                try:
                    task = kernel.get_task(task_id)
                except Exception:
                    continue
                if task.get("state") == "HUMAN_REVIEW":
                    kernel.transition(
                        task_id,
                        "CANCELLED",
                        actor="acceptance-suite",
                        reason="breaker-recovery probe resolved by suite after recovery",
                    )
                    cancelled.append(task_id)
        finally:
            kernel.close()
        return cancelled

    @staticmethod
    def verified_payload(session: str) -> dict[str, Any]:
        context = "Water freezes at zero degrees Celsius at standard atmospheric pressure."
        return {
            "question": "At standard atmospheric pressure, at what temperature does water freeze?",
            "domain": "general",
            "rag_enabled": True,
            "contexts": [context],
            "retrieved_context": context,
            "ai_answer": context,
            "ground_truth": context,
            "session_id": session,
        }

    @staticmethod
    def contradiction_payload() -> dict[str, Any]:
        """Exact payload for SCP-A04; also used by A12 to derive the expected
        durable task id through the same product identity function."""
        context = "Water freezes at zero degrees Celsius at standard atmospheric pressure."
        return {
            "question": "At standard atmospheric pressure, at what temperature does water freeze?",
            "rag_enabled": True,
            "contexts": [context],
            "retrieved_context": context,
            "ai_answer": "Water freezes at 100 degrees Celsius at standard atmospheric pressure.",
            "session_id": "a04",
        }

    def run(self) -> bool:
        (self.output_dir / ".acceptance-started").touch(exist_ok=False)
        try:
            self.provider.start()
            self.independent_provider.start()
            self.runtime.start()

            def a01() -> dict[str, Any]:
                health = self.runtime.request("GET", "/health", auth=False)
                require(health["status"] == 200, f"health status={health['status']}")
                body = health["body"] or {}
                require(body.get("status") == "ok", f"health body={body}")
                identity = body.get("service_identity") or {}
                require(identity.get("configured_port") == self.port, f"wrong service identity: {identity}")
                deadline = time.time() + 60
                ready: dict[str, Any] | None = None
                while time.time() < deadline:
                    ready = self.runtime.request("GET", "/ready", auth=False)
                    if ready["status"] == 200:
                        break
                    time.sleep(0.5)
                require(ready is not None and ready["status"] == 200, f"readiness never reached 200: {ready}")
                return {"health": body, "ready": ready["body"]}

            self.scenario("SCP-A01", "boot, liveness and readiness", a01)

            def a02() -> dict[str, Any]:
                unauthorized_ask = self.runtime.request(
                    "POST", "/ask", payload=self.verified_payload("a02-no-auth"), auth=False
                )
                require(unauthorized_ask["status"] in {401, 403}, f"unauthorized /ask accepted: {unauthorized_ask}")
                hands_denied = self.runtime.request("GET", "/v3/hands/status", auth=False)
                require(hands_denied["status"] == 403, f"Hands without capability token was not denied: {hands_denied}")
                hands_allowed = self.runtime.request("GET", "/v3/hands/status", auth=False, pc_token=True)
                require(hands_allowed["status"] == 200, f"Hands with controller token failed: {hands_allowed}")
                return {
                    "ask_without_auth": unauthorized_ask["status"],
                    "hands_without_token": hands_denied["status"],
                    "hands_with_token": hands_allowed["status"],
                }

            self.scenario("SCP-A02", "authentication and capability boundary fail closed", a02)

            def a03() -> dict[str, Any]:
                self.configure_providers("pass")
                key = "scp-a03-verified-rag"
                payload = self.verified_payload("a03")
                response = self.runtime.request(
                    "POST",
                    "/ask",
                    payload=payload,
                    idempotency_key=key,
                )
                require(response["status"] == 200, f"verified ask HTTP failure: {response}")
                body = response["body"] or {}
                require(body.get("verdict") == "PASS", f"verified evidence did not PASS: {body}")
                require(not str(body.get("final_answer", "")).startswith("[SCP:"), f"verified answer was withheld: {body}")
                task, journal = self._task(key, payload)
                require(task.get("state") == "COMPLETED", f"verified task not completed: {task}")
                require(journal.get("hash_chain_valid") is True, f"journal invalid: {journal}")
                return {"response": body, "task": task, "journal": journal}

            self.scenario("SCP-A03", "verified evidence completes durably", a03)

            def a04() -> dict[str, Any]:
                self.configure_providers("semantic")
                key = "scp-a04-contradiction"
                payload = self.contradiction_payload()
                response = self.runtime.request("POST", "/ask", payload=payload, idempotency_key=key)
                require(response["status"] == 200, f"contradiction ask HTTP failure: {response}")
                body = response["body"] or {}
                require(body.get("verdict") != "PASS", f"contradiction escaped as PASS: {body}")
                require(str(body.get("final_answer", "")).startswith("[SCP:"), f"contradicted answer was exposed: {body}")
                task, journal = self._task(key, payload)
                require(task.get("state") != "COMPLETED", f"contradicted task completed: {task}")
                require(journal.get("hash_chain_valid") is True, f"journal invalid: {journal}")
                return {"response": body, "task": task}

            self.scenario("SCP-A04", "contradicted evidence cannot complete", a04)

            def a05() -> dict[str, Any]:
                self.configure_providers("fail_primary")
                key = "scp-a05-provider-failover"
                payload = self.verified_payload("a05")
                response = self.runtime.request(
                    "POST", "/ask", payload=payload, idempotency_key=key, timeout=60
                )
                body = response["body"] or {}
                require(response["status"] == 200, f"provider failover HTTP failure: {response}")
                require(body.get("verdict") == "PASS", f"fallback did not preserve verified behavior: {body}")
                task, _journal = self._task(key, payload)
                require(task.get("state") == "COMPLETED", f"failover task not completed: {task}")
                calls = self.provider_calls()
                require(any("primary" in str(call.get("model")) for call in calls), f"no primary attempt recorded: {calls}")
                require(any("fallback" in str(call.get("model")) or call.get("model") == "openrouter/free" for call in calls), f"no fallback attempt recorded: {calls}")
                return {"task": task, "provider_calls": calls}

            self.scenario("SCP-A05", "provider failure preserves behavior through fallback", a05)

            def a06() -> dict[str, Any]:
                self.configure_providers("fail_all")
                key = "scp-a06-provider-outage"
                payload = self.verified_payload("a06")
                payload["ai_answer"] = ""
                response = self.runtime.request("POST", "/ask", payload=payload, idempotency_key=key, timeout=90)
                require(response["status"] == 200, f"provider outage HTTP failure: {response}")
                body = response["body"] or {}
                require(body.get("verdict") != "PASS", f"provider outage fabricated PASS: {body}")
                require(str(body.get("final_answer", "")).startswith("[SCP:"), f"provider outage exposed unverified answer: {body}")
                task, _journal = self._task(key, payload)
                require(task.get("state") != "COMPLETED", f"provider outage completed task: {task}")
                return {"response": body, "task": task, "provider_calls": self.provider_calls()}

            self.scenario("SCP-A06", "total provider outage fails closed", a06)

            def a07() -> dict[str, Any]:
                self.configure_providers("pass")
                key = "scp-a07-ssrf"
                payload = self.verified_payload("a07")
                payload["image_url"] = f"http://127.0.0.1:{self.provider_port}/private"
                response = self.runtime.request("POST", "/ask", payload=payload, idempotency_key=key)
                require(response["status"] == 400, f"loopback SSRF was not rejected: {response}")
                task, journal = self._task(key, payload)
                require(task.get("state") == "FAILED", f"rejected request left unsafe task state: {task}")
                require(journal.get("hash_chain_valid") is True, f"journal invalid: {journal}")
                return {"http_status": response["status"], "task": task}

            self.scenario("SCP-A07", "SSRF rejection is coupled to safe task termination", a07)

            def a08() -> dict[str, Any]:
                self.configure_providers("pass", delay_seconds=0.4)
                # A06 opened the provider breakers; the race below needs the
                # judge cascade healthy (two distinct families must verify the
                # winner). Recover first — see _recover_judge_breakers.
                recovery = self._recover_judge_breakers()
                key = "scp-a08-idempotency"
                payload = self.verified_payload("a08")
                barrier = threading.Barrier(2)

                def send() -> dict[str, Any]:
                    barrier.wait(timeout=5)
                    return self.runtime.request("POST", "/ask", payload=payload, idempotency_key=key, timeout=90)

                with ThreadPoolExecutor(max_workers=2) as pool:
                    responses = list(pool.map(lambda _i: send(), range(2)))
                verdicts = [(response["body"] or {}).get("verdict") for response in responses]
                require(verdicts.count("PASS") == 1, f"idempotent race did not produce exactly one accepted execution: {responses}")
                require(verdicts.count("FAIL") == 1, f"duplicate was not rejected safely: {responses}")
                task, journal = self._task(key, payload)
                require(task.get("state") == "COMPLETED", f"winner task not completed: {task}")
                require(journal.get("hash_chain_valid") is True, f"journal invalid: {journal}")
                return {"verdicts": verdicts, "task": task, "breaker_recovery": recovery}

            self.scenario("SCP-A08", "concurrent duplicate request executes once", a08)

            def a09() -> dict[str, Any]:
                self.configure_providers("pass", delay_seconds=3.0)
                key = "scp-a09-hard-crash"
                payload = self.verified_payload("a09")
                outcome: dict[str, Any] = {}

                def request_worker() -> None:
                    try:
                        outcome["response"] = self.runtime.request(
                            "POST", "/ask", payload=payload, idempotency_key=key, timeout=30
                        )
                    except Exception as exc:
                        outcome["transport_error"] = type(exc).__name__

                worker = threading.Thread(target=request_worker, daemon=True)
                worker.start()
                before = self._wait_task(key, {"RUNNING", "VERIFYING"}, payload, timeout=12)
                self.runtime.stop(force=True)
                worker.join(timeout=10)
                self.configure_providers("pass")
                self.runtime.start()
                recovered = self._wait_task(key, {"HUMAN_REVIEW"}, payload, timeout=15)
                task, journal = self._task(key, payload)
                require(task.get("state") == "HUMAN_REVIEW", f"hard-crash task not recovered safely: {task}")
                require(journal.get("hash_chain_valid") is True, f"recovered journal invalid: {journal}")
                return {"before_kill": before, "after_restart": recovered, "transport": outcome, "journal": journal}

            self.scenario("SCP-A09", "hard crash and restart cannot silently complete uncertain work", a09)

            def a10() -> dict[str, Any]:
                from scp.task_kernel import TaskKernel

                db_path = self.output_dir / "tamper.sqlite3"
                kernel = TaskKernel(db_path)
                try:
                    kernel.create_task("acceptance-tamper", "acceptance", "tamper detection", "R0")
                    kernel.transition("acceptance-tamper", "PLANNING", actor="acceptance", reason="plan")
                    kernel.conn.execute(
                        "UPDATE events SET reason='tampered-after-write' WHERE task_id='acceptance-tamper' AND seq=1"
                    )
                    report = kernel.recover_on_boot()
                    task = kernel.get_task("acceptance-tamper")
                    require(any(item.get("task_id") == "acceptance-tamper" for item in report.get("corrupted", [])), f"tamper not detected: {report}")
                    require(task.get("state") == "PLANNING", f"corrupted evidence was auto-mutated: {task}")
                    return {"recovery": report, "task": task}
                finally:
                    kernel.close()

            self.scenario("SCP-A10", "tampered journal blocks automatic recovery", a10)

            def a11() -> dict[str, Any]:
                self.configure_providers("pass")
                count = max(2, self.concurrency)

                def send(index: int) -> tuple[int, dict[str, Any]]:
                    key = f"scp-a11-concurrent-{index}"
                    response = self.runtime.request(
                        "POST",
                        "/ask",
                        payload=self.verified_payload(f"a11-{index}"),
                        idempotency_key=key,
                        timeout=90,
                    )
                    return index, response

                results: list[tuple[int, dict[str, Any]]] = []
                with ThreadPoolExecutor(max_workers=count) as pool:
                    futures = [pool.submit(send, index) for index in range(count)]
                    for future in as_completed(futures):
                        results.append(future.result())
                failures = [
                    {"index": index, "response": response}
                    for index, response in results
                    if response["status"] != 200 or (response["body"] or {}).get("verdict") != "PASS"
                ]
                require(not failures, f"concurrent verified asks failed: {failures}")
                invalid_journals = []
                for index in range(count):
                    task, journal = self._task(
                        f"scp-a11-concurrent-{index}",
                        self.verified_payload(f"a11-{index}"),
                    )
                    if task.get("state") != "COMPLETED" or journal.get("hash_chain_valid") is not True:
                        invalid_journals.append({"index": index, "task": task, "journal": journal})
                require(not invalid_journals, f"concurrency damaged durable state: {invalid_journals}")
                return {"requests": count, "all_completed": True}

            self.scenario("SCP-A11", "parallel verified requests preserve durable consistency", a11)

            def a12() -> dict[str, Any]:
                from scp.task_kernel import TaskKernel

                kernel = TaskKernel(self.runtime.db_path)
                try:
                    integrity = kernel.verify_integrity()
                    require(integrity.get("quick_check") == "ok", f"SQLite quick_check failed: {integrity}")
                    rows = kernel.conn.execute("SELECT task_id, state FROM tasks ORDER BY created_at").fetchall()
                    invalid = []
                    for row in rows:
                        verification = kernel.verify_journal(row["task_id"])
                        if verification.get("hash_chain_valid") is not True:
                            invalid.append({"task_id": row["task_id"], "state": row["state"], "journal": verification})
                    require(not invalid, f"main acceptance journal contains invalid chains: {invalid}")
                    expected_review_ids = {
                        stable_task_id("scp-a04-contradiction", self.contradiction_payload()),
                        stable_task_id("scp-a06-provider-outage", self.verified_payload("a06")),
                        stable_task_id("scp-a09-hard-crash", self.verified_payload("a09")),
                    }
                    observed_nonterminal = {
                        (row["task_id"], row["state"])
                        for row in rows
                        if row["state"] not in {"COMPLETED", "FAILED", "CANCELLED"}
                    }
                    expected_nonterminal = {
                        (task_id, "HUMAN_REVIEW") for task_id in expected_review_ids
                    }
                    require(
                        observed_nonterminal == expected_nonterminal,
                        "acceptance nonterminal set differs from the exact expected "
                        f"human-review tasks: {observed_nonterminal}",
                    )
                    require(
                        kernel.pending_review_count() == len(expected_review_ids),
                        "TaskKernel review backlog no longer represents every "
                        "expected withheld (HUMAN_REVIEW) task",
                    )
                    return {
                        "quick_check": integrity.get("quick_check"),
                        "task_count": len(rows),
                        "expected_human_review_ids": sorted(expected_review_ids),
                        "states": [dict(row) for row in rows],
                    }
                finally:
                    kernel.close()

            self.scenario("SCP-A12", "suite leaves no hidden in-flight work and intact evidence", a12)
        finally:
            try:
                self.runtime.stop(force=False)
            finally:
                try:
                    self.provider.stop()
                finally:
                    try:
                        self.independent_provider.stop()
                    finally:
                        self._write_report(final=True)

        return all(scenario["passed"] for scenario in self.scenarios) and len(self.scenarios) == len(EXPECTED_SCENARIOS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SCP system-level acceptance scenarios")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--provider-port", type=int, default=18081)
    parser.add_argument("--concurrency", type=int, default=6)
    args = parser.parse_args()

    suite = AcceptanceSuite(args.output_dir.resolve(), args.port, args.provider_port, args.concurrency)
    passed = suite.run()
    print(f"SCP ACCEPTANCE: {'PASS' if passed else 'FAIL'} — evidence: {suite.report_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
