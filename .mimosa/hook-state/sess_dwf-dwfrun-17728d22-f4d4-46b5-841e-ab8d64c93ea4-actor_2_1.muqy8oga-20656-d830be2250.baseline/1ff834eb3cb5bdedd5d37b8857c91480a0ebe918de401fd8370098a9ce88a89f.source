"""Run the bounded local SCP smoke used by the release evidence gate.

This deliberately binds only to 127.0.0.1:8000, denies external egress, uses
isolated temporary state, and checks both startup behavior and post-stop port
cleanup. In deny-egress mode semantic verification is expected to fail closed
when independent providers are unavailable. It is a bounded proof, not a
production or distributed benchmark.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests
try:
    from _net_guard import safe_request  # [S6b] boundary-validated egress
except ModuleNotFoundError:  # imported as a module (tools.run_bounded_system_smoke)
    from tools._net_guard import safe_request
import jwt

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


SMOKE_JWT_SECRET = "bounded-smoke-jwt-secret-32-bytes-long"
SMOKE_PC_TOKEN = "bounded-smoke-pc-controller-token"
# Self-contained credentials: the smoke must boot on a machine whose parent
# env carries NO SCP_* variables (the config contract requires SCP_JWT_SECRET
# and SCP_ADMIN_KEY; GAP-09 requires a capability signing secret).
SMOKE_ADMIN_KEY = "bounded-smoke-admin-key-urlsafe-24b"
SMOKE_CAPABILITY_SECRET = secrets.token_hex(32)
SMOKE_TOKEN = jwt.encode({"sub": "smoke-tester", "exp": time.time() + 3600}, SMOKE_JWT_SECRET, algorithm="HS256")
# One effective capability secret shared by the booted server and the local
# token mint, so minting never depends on the parent process env.
EFFECTIVE_CAPABILITY_SECRET = os.environ.get("SCP_CAPABILITY_SECRET", "").strip() or SMOKE_CAPABILITY_SECRET
# scp.core.capability_token binds its signing secret at import time (GAP-09,
# pinned by tests/T03_capability/test_capability_secret_fail_closed.py), so
# the smoke's own process must carry the secret before it imports the
# authority — setdefault keeps an operator-provided secret authoritative.
os.environ.setdefault("SCP_CAPABILITY_SECRET", EFFECTIVE_CAPABILITY_SECRET)


def _mint_hands_capability_token(action: str, state_dir: Path | None = None) -> dict | None:
    """Mint a Zero-Trust capability token for one Hands action via the product
    authority.

    [Fix 2026-09-25, pre-rc 36110802706] TẠI SAO: the hands executor enforces
    FA-05 fail-closed — every action requires a capability token signed with
    the server's SCP_CAPABILITY_SECRET at the server's CURRENT revocation
    epoch. The previous smoke sent no token and only ever "passed" while the
    server crashed earlier at boot (GAP-09) — the check was unreachable. Using
    CapabilityAuthority.issue() over the SAME state file (ROOT/data/hands/
    capability_state.json) the server reads keeps epoch/signature handling in
    ONE product implementation (no mirrored crypto). Missing secret → the
    smoke fails loudly (the server could not have booted either); revocation
    state → issue() raises fail-closed and the smoke reports it.
    """
    try:
        from scp.security.capability_epoch import CapabilityAuthority

        # SCP_HANDS_DATA_DIR (set for the server below) keeps the epoch state
        # inside this run's output dir. In that isolated dir the smoke is the
        # operator: a revoked state (e.g. left behind by an earlier CI step
        # sharing the workspace) is cleared via the legal product transition
        # before minting. Without the env override the operator's real state
        # file is used and a revocation fails the smoke loudly — never
        # auto-restored.
        # state_dir is the SAME isolated dir handed to the booted server
        # (run() passes output_dir/hands). In that dir the smoke is the
        # operator: a revoked state (e.g. left behind by an earlier CI step
        # sharing the workspace) is cleared via the legal product transition
        # before minting. With no state_dir the operator's real state file is
        # used and a revocation fails the smoke loudly — never auto-restored.
        effective_state_dir = state_dir or (ROOT / "data" / "hands")
        authority = CapabilityAuthority(effective_state_dir / "capability_state.json", secret=EFFECTIVE_CAPABILITY_SECRET)
        if state_dir is not None and authority.status().get("revoked"):
            authority.restore(reason="bounded-smoke-reset", actor="bounded-smoke")
        return authority.issue(f"hands:{action}").to_dict()
    except Exception as exc:
        raise RuntimeError(f"capability token mint failed for hands:{action} (FA-05 fail-closed): {exc}") from exc

def _request(method: str, path: str, payload: dict | None = None, headers: dict | None = None) -> dict:
    req_headers = {
        "Authorization": f"Bearer {SMOKE_TOKEN}",
        "x-scp-pc-token": SMOKE_PC_TOKEN,
    }
    if headers:
        req_headers.update(headers)
    # [Fix 2026-09-25, pre-rc 36110802706] _net_guard.safe_get fail-closed
    # rejects unsupported egress kwargs — and a `json=None` kwarg on a GET
    # is exactly that. Only attach a JSON body when the check actually has
    # a payload (POST); GET requests must go out bodyless.
    guard_kwargs: dict = {"headers": req_headers, "timeout": 30, "allow_internal": True}
    if payload is not None:
        guard_kwargs["json"] = payload
    response = safe_request(method, f"{BASE}{path}", **guard_kwargs)
    item: dict[str, object] = {"http_status": response.status_code}
    try:
        item["body"] = response.json()
    except ValueError:
        item["body_text"] = response.text[:1000]
    return item


def run(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.iterdir():
        if path.is_file():
            path.unlink()
    if port_open(8000):
        raise RuntimeError("refused: port 8000 already in use")

    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "SCP_HOST": "127.0.0.1",
            "SCP_PORT": "8000",
            "SCP_MODE": "test",
            "SCP_EGRESS_MODE": "deny",
            "SCP_WEB_FALLBACK": "0",
            "SCP_ASK_KERNEL_ENABLED": "1",
            "SCP_KERNEL_DB_PATH": str(output_dir / "kernel.sqlite3"),
            "SCP_KERNEL_TRACE_PATH": str(output_dir / "kernel_trace.jsonl"),
            "SCP_REQUEST_RUN_LEDGER_PATH": str(output_dir / "request_runs.jsonl"),
            "SCP_HANDS_LOCAL_ONLY": "1",
            "SCP_HANDS_DATA_DIR": str(output_dir / "hands"),
            "SCP_ENV_FILE": str(output_dir / "empty.env"),
            "SCP_JWT_SECRET": SMOKE_JWT_SECRET,
            "SCP_ADMIN_KEY": SMOKE_ADMIN_KEY,
            "SCP_CAPABILITY_SECRET": EFFECTIVE_CAPABILITY_SECRET,
            "SCP_PC_CONTROLLER_TOKEN": SMOKE_PC_TOKEN,
        }
    )
    (output_dir / "empty.env").write_text("", encoding="utf-8")
    log_path = output_dir / "server.log"
    log = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "scp", "8000"],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    responses: dict[str, dict] = {}
    report: dict[str, object] | None = None
    try:
        ready = False
        for _ in range(60):
            try:
                response = requests.get(f"{BASE}/health", timeout=2)
                if response.status_code == 200:
                    ready = True
                    responses["health"] = {
                        "http_status": response.status_code,
                        "body": response.json(),
                    }
                    break
            except requests.RequestException:
                pass
            time.sleep(0.5)
        if not ready:
            raise RuntimeError("health did not become ready")

        checks_to_run = [
            ("hands_status", "GET", "/v3/hands/status", None),
            ("hands_actions", "GET", "/v3/hands/actions", None),
            (
                "hands_plan",
                "POST",
                "/v3/hands/plan",
                {"action": "pc.status", "params": {}, "capabilityLevel": 1, "approved": True, "dryRun": True},
            ),
            (
                "hands_execute_dry_run",
                "POST",
                "/v3/hands/execute",
                {
                    "action": "pc.status",
                    "params": {},
                    "capabilityLevel": 1,
                    "approved": True,
                    "dryRun": True,
                    # [Fix 2026-09-25, pre-rc 36110802706] FA-05: hands actions
                    # require an authorized capability token (fail-closed).
                    # Once SCP_CAPABILITY_SECRET is provided (CI) the boundary
                    # ENFORCES instead of crashing at boot — so the smoke must
                    # present a token minted through the product authority over
                    # the SAME state path + secret the server validates against.
                    "capabilityToken": _mint_hands_capability_token("pc.status", state_dir=output_dir / "hands"),
                },
            ),
            (
                "ask_rag",
                "POST",
                "/ask",
                {
                    "question": "What is spaced repetition?",
                    "domain": "consumer_travel_education",
                    "rag_enabled": True,
                    "contexts": [
                        "Spaced repetition is an evidence-based learning technique that is usually performed with flashcards."
                    ],
                    "retrieved_context": "Spaced repetition is an evidence-based learning technique that is usually performed with flashcards.",
                    "ai_answer": "Spaced repetition is an evidence-based learning technique that is usually performed with flashcards.",
                    "ground_truth": "Spaced repetition is an evidence-based learning technique that is usually performed with flashcards.",
                    "session_id": "release-gate-bounded-smoke",
                },
            ),
        ]
        ask_retries = 0
        for name, method, path, payload in checks_to_run:
            response = _request(method, path, payload)
            # [Fix 2026-09-25, pre-rc 36110802706] Judge initialization is
            # asynchronous: /ask answers 503 judge_initializing (+retry_after)
            # until the semantic judge finishes booting — deterministic on slow
            # GitHub runners. Retry bounded instead of failing the whole gate;
            # the fail-closed verdict checks below still apply to the FINAL
            # response (an ask that never initializes still fails the gate).
            if name == "ask_rag":
                deadline = time.time() + 60.0
                while (
                    response.get("http_status") == 503
                    and str((response.get("body") or {}).get("reason", "")) == "judge_initialization_pending"
                    and time.time() < deadline
                ):
                    ask_retries += 1
                    time.sleep(min(5.0, float((response.get("body") or {}).get("retry_after_seconds") or 2.0)))
                    response = _request(method, path, payload)
            responses[name] = response

        ask_body = responses["ask_rag"].get("body", {})
        ask_answer = str(ask_body.get("final_answer", ""))
        checks = {
            "health_200": responses["health"]["http_status"] == 200,
            "hands_status_200": responses["hands_status"]["http_status"] == 200,
            "hands_actions_200": responses["hands_actions"]["http_status"] == 200,
            "hands_plan_200": responses["hands_plan"]["http_status"] == 200,
            "hands_plan_allowed": responses["hands_plan"].get("body", {}).get("allowed") is True,
            "hands_execute_200": responses["hands_execute_dry_run"]["http_status"] == 200,
            "hands_execute_success": responses["hands_execute_dry_run"].get("body", {}).get("success") is True,
            "hands_execute_dry_run": responses["hands_execute_dry_run"].get("body", {}).get("dryRun") is True,
            "ask_http_200": responses["ask_rag"]["http_status"] == 200,
            "ask_fail_closed": ask_body.get("verdict") != "PASS",
            "ask_answer_withheld": "withheld" in ask_answer.lower(),
            "ask_governance_escalated": ask_body.get("governance_decision") == "ESCALATE",
            "ask_run_status_rejected": ask_body.get("run_status") == "REJECTED",
            "ask_ledger_status_ok": ask_body.get("ledger_status") == "OK",
        }
        report = {
            "schema_version": "scp-bounded-system-smoke-v3",
            "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "host": "127.0.0.1",
            "port": 8000,
            "port_8000_used": False,
            "egress_mode": "deny",
            "responses": responses,
            "ask_rag_retries": ask_retries,
            "checks": checks,
            "pass": all(checks.values()),
            "scope": "Bounded deny-egress local smoke: API→router→ledger/kernel→RAG governance→Hands read-only dry-run. Semantic verification must fail closed when independent providers are unavailable. No external write, provider availability claim, distributed deployment, or factual benchmark claim.",
        }
        (output_dir / "evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if not report["pass"]:
            raise RuntimeError("bounded system smoke checks failed")
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()

    time.sleep(0.5)
    cleanup = {
        "process_returncode": process.returncode,
        "port_8000_free": not port_open(8000),
    }
    (output_dir / "cleanup.json").write_text(json.dumps(cleanup, indent=2) + "\n", encoding="utf-8")
    if not cleanup["port_8000_free"]:
        raise RuntimeError(f"port cleanup failed: {cleanup}")
    return {"evidence": str(output_dir / "evidence.json"), "cleanup": cleanup}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "bounded_system_smoke_ci")
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
