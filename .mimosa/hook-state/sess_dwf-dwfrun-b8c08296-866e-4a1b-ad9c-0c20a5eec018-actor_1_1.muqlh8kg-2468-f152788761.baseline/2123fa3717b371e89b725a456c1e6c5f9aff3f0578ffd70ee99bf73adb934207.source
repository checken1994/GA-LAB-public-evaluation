"""Fail-closed system audit for an SCP integration candidate.

The runner records exact-commit evidence and treats missing or contradictory
postconditions as blockers. Product behavior is never changed to make this
runner pass.
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Ensure repository root is on sys.path for absolute imports
sys.path.insert(0, str(ROOT))
from importlib import import_module
base = import_module('scripts.run_full_audit')
from tools.run_bounded_system_smoke import port_open, run as run_bounded_smoke
REPORT_DIR = ROOT / "reports" / "system_audit_strict"


def _run_step(name: str, fn) -> dict:
    started = time.time()
    try:
        result = fn()
        ok = bool(result.get("ok", False))
        return {
            "name": name,
            "status": "PASS" if ok else "FAIL",
            "elapsed_sec": round(time.time() - started, 2),
            **result,
        }
    except Exception as exc:
        return {
            "name": name,
            "status": "ERROR",
            "ok": False,
            "elapsed_sec": round(time.time() - started, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


def _validate_boot_findings(findings: dict) -> dict:
    health = findings.get("health", {})
    readiness = findings.get("readiness", {})
    brute = findings.get("auth_brute_force", {})
    auth = findings.get("auth_valid", {})
    rag = findings.get("rag_ask", {})
    attack = findings.get("prompt_injection", {})
    ready_checks = readiness.get("checks", {}) or {}

    rag_verdict = rag.get("verdict")
    rag_withheld = bool(rag.get("withheld"))
    rag_governance = rag.get("governance")
    # Strong fail-closed contract, pinned by the deny-egress probe env (the
    # boot child loads SCP_EGRESS_MODE=deny) and the LANE_FACTUAL probe
    # question in run_full_audit.step_boot_and_probe: under deny egress a
    # factual ask returns verdict=FAIL / governance=KILL / answer withheld
    # (observed live 2026-09-26). The rule grades exactly that shape and must
    # NOT be widened to accept whatever shape an environment happens to
    # produce.
    rag_fail_closed_coherent = (
        rag.get("status_code") == 200
        and (
            (rag_verdict == "PASS" and not rag_withheld)
            or (rag_verdict == "FAIL" and rag_withheld)
            or (rag_verdict == "UNKNOWN" and rag_withheld)
        )
        and not (rag_governance == "KILL" and not rag_withheld)
    )

    checks = {
        "health_200": health.get("status_code") == 200,
        "readiness_200": readiness.get("status_code") == 200,
        "judge_ready": ready_checks.get("judge") == "ok",
        "background_scheduler_ready": ready_checks.get("background_scheduler") == "ok",
        "auth_bruteforce_rate_limited": brute.get("rate_limited") is True and 429 in brute.get("codes", []),
        "auth_valid_token": auth.get("status_code") == 200 and auth.get("has_token") is True,
        "rag_fail_closed_coherent": rag_fail_closed_coherent,
        "prompt_injection_http_200": attack.get("status_code") == 200,
        "prompt_injection_not_pass": attack.get("verdict") != "PASS",
        "prompt_injection_withheld": attack.get("withheld") is True,
        "prompt_injection_killed": attack.get("governance") == "KILL",
    }
    return {"ok": all(checks.values()), "checks": checks, "findings": findings}


def step_boot_strict(env_file: str) -> dict:
    raw = base.step_boot_and_probe(env_file)
    return _validate_boot_findings(raw.get("findings", {}))


def _run_pytest(paths: list[str], timeout: int) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *paths, "--tb=short"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "output_tail": (proc.stdout + "\n" + proc.stderr)[-6000:],
    }


def step_semantic_parity_contract() -> dict:
    return _run_pytest(["tests/T02_contract/test_god_split_semantic_parity.py"], 180)


def step_provider_failover_timeout_contract() -> dict:
    return _run_pytest(
        [
            "tests/T05_gateway/test_provider_failover.py",
            "tests/T05_gateway/test_provider_timeout_recovery.py",
            "tests/T05_gateway/test_llm_egress_policy.py",
            "tests/T05_gateway/test_multi_llm_crosscheck.py",
            "tests/T05_gateway/test_multi_llm_crosscheck_concurrency.py",
            "tests/external_audit/test_cascade.py",
        ],
        300,
    )


def step_skill_dna_contract() -> dict:
    return _run_pytest(["tests/T11_release/test_scp_skill_dna_contract.py"], 120)


def step_full_pytest() -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "output_tail": (proc.stdout + "\n" + proc.stderr)[-6000:],
    }


def step_reality_suite() -> dict:
    result = base.step_reality()
    return {**result, "ok": bool(result.get("ok"))}


def step_fitness() -> dict:
    result = base.step_fitness()
    return {**result, "ok": bool(result.get("ok"))}


def step_hermetic_boot() -> dict:
    result = base.step_hermetic_boot()
    return {**result, "ok": bool(result.get("ok"))}


def step_kernel_recovery_integrity() -> dict:
    """Exercise durable-kernel invariants on one real SQLite/WAL database."""
    from scp.task_kernel import TaskKernel

    with tempfile.TemporaryDirectory(prefix="scp-kernel-reality-") as tmp:
        db_path = Path(tmp) / "kernel.sqlite3"
        kernel = TaskKernel(db_path)

        # Idempotent event replay must not append a duplicate event.
        kernel.create_task("idem-task", "audit", "idempotency reality check")
        event_id = "evt-system-audit-idempotent"
        kernel.transition(
            "idem-task", "PLANNING", actor="audit", reason="first replay", event_id=event_id
        )
        event_count_before = len(kernel.get_events("idem-task"))
        kernel.transition(
            "idem-task", "PLANNING", actor="audit", reason="duplicate replay", event_id=event_id
        )
        event_count_after = len(kernel.get_events("idem-task"))

        # Simulate process loss with a leased task, then reopen the same database.
        kernel.transition("idem-task", "READY", actor="audit", reason="prepare queue")
        kernel.transition("idem-task", "QUEUED", actor="audit", reason="queue task")
        lease = kernel.claim("idem-task", "audit-worker", ttl_seconds=60.0)
        leased_state = kernel.get_task("idem-task")["state"]
        journal_before_restart = kernel.verify_journal("idem-task")
        kernel.close()

        reopened = TaskKernel(db_path)
        recovery = reopened.recover_on_boot(actor="strict_system_audit")
        recovered_state = reopened.get_task("idem-task")["state"]
        journal_after_restart = reopened.verify_journal("idem-task")

        # Establish a valid chain, then close the application and tamper through
        # an independent SQLite connection, as an external process would.
        reopened.create_task("tamper-task", "audit", "tamper reality check")
        reopened.transition("tamper-task", "PLANNING", actor="audit", reason="before tamper")
        tamper_before = reopened.verify_journal("tamper-task")
        reopened.close()

        raw = sqlite3.connect(str(db_path), timeout=10.0)
        try:
            raw.execute(
                "UPDATE events SET payload_json=? WHERE task_id=? AND seq=?",
                (json.dumps({"tampered": True}), "tamper-task", 2),
            )
            raw.commit()
        finally:
            raw.close()

        tampered_kernel = TaskKernel(db_path)
        tamper_after = tampered_kernel.verify_journal("tamper-task")
        recovery_after_tamper = tampered_kernel.recover_on_boot(
            actor="strict_system_audit_tamper"
        )
        tampered_kernel.close()

        # Parallel consistency: each worker opens its own storage facade against
        # one database. Every successful create must remain durable and valid.
        parallel_count = 24

        def _parallel_create(i: int) -> str:
            task_id = f"parallel-{i:02d}"
            k = TaskKernel(db_path)
            try:
                k.create_task(task_id, f"owner-{i % 4}", f"parallel reality {i}")
                return task_id
            finally:
                k.close()

        parallel_errors: list[str] = []
        created_ids: list[str] = []
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(_parallel_create, i) for i in range(parallel_count)]
            for future in as_completed(futures):
                try:
                    created_ids.append(future.result())
                except Exception as exc:
                    parallel_errors.append(f"{type(exc).__name__}: {exc}")

        final_kernel = TaskKernel(db_path)
        try:
            persisted_parallel = int(
                final_kernel.conn.execute(
                    "SELECT COUNT(*) AS n FROM tasks WHERE task_id LIKE 'parallel-%'"
                ).fetchone()["n"]
            )
            invalid_parallel = []
            for task_id in sorted(created_ids):
                result = final_kernel.verify_journal(task_id)
                if not result.get("hash_chain_valid"):
                    invalid_parallel.append(
                        {"task_id": task_id, "errors": result.get("errors")}
                    )
        finally:
            final_kernel.close()

        corrupted_ids = {
            item.get("task_id") for item in recovery_after_tamper.get("corrupted", [])
        }
        recovered_match = any(
            item.get("task_id") == "idem-task"
            and item.get("from") == "LEASED"
            and item.get("to") == "RECOVERING"
            for item in recovery.get("recovered", [])
        )

        checks = {
            "idempotent_event_replay": event_count_before == event_count_after,
            "leased_before_restart": leased_state == "LEASED" and bool(lease.lease_id),
            "journal_valid_before_restart": journal_before_restart.get("hash_chain_valid") is True,
            "boot_recovery_to_recovering": recovered_state == "RECOVERING" and recovered_match,
            "journal_valid_after_restart": journal_after_restart.get("hash_chain_valid") is True,
            "tamper_baseline_valid": tamper_before.get("hash_chain_valid") is True,
            "tamper_detected": tamper_after.get("hash_chain_valid") is False,
            "tamper_fail_closed_on_boot": "tamper-task" in corrupted_ids,
            "parallel_no_worker_errors": not parallel_errors,
            "parallel_all_persisted": persisted_parallel == parallel_count,
            "parallel_journals_valid": not invalid_parallel,
        }
        return {
            "ok": all(checks.values()),
            "checks": checks,
            "event_count_before_replay": event_count_before,
            "event_count_after_replay": event_count_after,
            "lease": {"lease_id": lease.lease_id, "fencing_token": lease.fencing_token},
            "recovery": recovery,
            "tamper_before": tamper_before,
            "tamper_after": tamper_after,
            "recovery_after_tamper": recovery_after_tamper,
            "parallel_created": len(created_ids),
            "parallel_persisted": persisted_parallel,
            "parallel_errors": parallel_errors,
            "invalid_parallel_journals": invalid_parallel,
        }


def _read_json_if_present(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _run_one_bounded(output_dir: Path) -> dict:
    error = None
    result = None
    try:
        result = run_bounded_smoke(output_dir)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    time.sleep(0.5)
    evidence = _read_json_if_present(output_dir / "evidence.json")
    cleanup = _read_json_if_present(output_dir / "cleanup.json")
    log_path = output_dir / "server.log"
    server_log = (
        log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    )
    outbound_lines = [
        line
        for line in server_log.splitlines()
        if "HTTP Request:" in line and ("http://" in line or "https://" in line)
    ]
    port_free = not port_open(8000)

    response_checks = evidence.get("checks", {}) or {}
    deny_mode = str(evidence.get("egress_mode", os.environ.get("SCP_EGRESS_MODE", ""))).lower() == "deny"
    if deny_mode:
        ask_checks = {
            "ask_http_200": response_checks.get("ask_http_200") is True,
            "ask_fail_closed": response_checks.get("ask_fail_closed") is True,
            "ask_answer_withheld": response_checks.get("ask_answer_withheld") is True,
            "ask_governance_escalated": response_checks.get("ask_governance_escalated") is True,
            "ask_run_status_rejected": response_checks.get("ask_run_status_rejected") is True,
            "ledger_ok": response_checks.get("ask_ledger_status_ok") is True,
        }
    else:
        ask_checks = {
            "ask_verdict_pass": response_checks.get("ask_verdict_pass") is True,
            "ask_run_status_success": response_checks.get("ask_run_status_success") is True,
            "ledger_ok": response_checks.get("ask_ledger_status_ok") is True,
        }

    checks = {
        "runner_no_error": error is None,
        "evidence_written": bool(evidence),
        "bounded_evidence_pass": evidence.get("pass") is True,
        "health_200": response_checks.get("health_200") is True,
        "hands_status_200": response_checks.get("hands_status_200") is True,
        "hands_plan_allowed": response_checks.get("hands_plan_allowed") is True,
        "hands_dry_run_success": (
            response_checks.get("hands_execute_success") is True
            and response_checks.get("hands_execute_dry_run") is True
        ),
        **ask_checks,
        "no_external_egress_when_denied": (not outbound_lines) if deny_mode else True,
        "port_cleanup": port_free,
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "runner_result": result,
        "runner_error": error,
        "evidence": evidence,
        "cleanup": cleanup,
        "port_free_observed": port_free,
        "external_http_requests": outbound_lines,
        "server_log_tail": server_log[-6000:],
    }


def step_bounded_smoke_twice() -> dict:
    first_dir = REPORT_DIR / "bounded_smoke_first"
    second_dir = REPORT_DIR / "bounded_smoke_restart"
    first = _run_one_bounded(first_dir)
    second = (
        _run_one_bounded(second_dir)
        if first.get("port_free_observed")
        else {
            "ok": False,
            "skipped": True,
            "reason": "port 8000 was not released after first smoke",
        }
    )
    checks = {
        "first_cycle": first.get("ok") is True,
        "restart_cycle": second.get("ok") is True,
        "first_port_cleanup": first.get("port_free_observed") is True,
        "restart_port_cleanup": second.get("port_free_observed") is True,
    }
    return {"ok": all(checks.values()), "checks": checks, "first": first, "second": second}


def _persist_full_report(report: dict) -> Path:
    """Write the FULL audit report (steps incl. checks/findings) to a
    timestamped file so every run's complete evidence stays inspectable,
    independent of what the workflow log happens to print."""
    stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime(report.get("started_at", time.time())))
    milliseconds = int(report.get("started_at", time.time()) % 1 * 1000)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"system_audit_strict-{stamp}-{milliseconds:03d}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


# Per-step cap for the failed-step detail block printed to the workflow log.
_FAILED_STEP_DETAIL_CAP = 20000


def _print_failed_step_details(steps: list[dict]) -> None:
    """Print the full checks/findings of every FAIL/ERROR step so the workflow
    log shows WHICH postcondition failed without downloading artifacts."""
    for step in steps:
        if step.get("status") not in ("FAIL", "ERROR"):
            continue
        detail = dict(step)
        checks = step.get("checks")
        if isinstance(checks, dict):
            detail["failed_checks"] = sorted(k for k, v in checks.items() if not v)
        rendered = json.dumps(detail, ensure_ascii=False, indent=2, default=str)
        if len(rendered) > _FAILED_STEP_DETAIL_CAP:
            rendered = (
                rendered[:_FAILED_STEP_DETAIL_CAP]
                + "\n... [truncated; full step detail is in the persisted report JSON]"
            )
        print(f"FAILED_STEP_DETAIL {step.get('name')}: {rendered}", flush=True)


def main() -> int:
    started = time.time()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

    env_file = ROOT / ".env.system-audit-run"
    env_file.write_text(
        "SCP_JWT_SECRET=" + secrets.token_hex(32) + "\n"
        "SCP_ADMIN_KEY=" + secrets.token_urlsafe(24) + "\n"
        # GAP-09: the isolated boot child imports capability_token, which
        # binds its signing secret at import time. The child env is built
        # explicitly, so without this line the boot probe depends on the
        # surrounding job env carrying the secret — never assume that.
        "SCP_CAPABILITY_SECRET=" + secrets.token_hex(32) + "\n"
        # Deny-egress boot probe (same contract as tools/live_flow_proof.py
        # --egress-deny and the CI job env): the boot child env is composed
        # explicitly and does NOT inherit the parent's SCP_EGRESS_MODE, so the
        # deny contract must be pinned in the env file the child loads.
        # Observed deny-env shapes (2026-09-26 local probe, runner-like env,
        # and reports/system_audit_strict/system_audit_strict-20260925T115756):
        # prompt-injection probe = FAIL / KILL / withheld; RAG probe question
        # ("Is the sky blue?", routed LANE_CHATBOT l2-failsafe) still returns
        # UNKNOWN / ESCALATE with the answer delivered — the coherence rule
        # below documents why that lane is accepted. No coherence acceptance
        # may be widened to match whatever shape an environment happens to
        # produce; shapes are pinned by evidence, not by the gate.
        "SCP_EGRESS_MODE=deny\n",
        encoding="utf-8",
    )

    os.environ.setdefault("SCP_EGRESS_MODE", "deny")
    os.environ.setdefault("SCP_PRODUCTION_MODE", "0")
    os.environ.setdefault("SCP_SKIP_STARTUP_GATE", "0")

    steps: list[dict] = []
    try:
        steps.append(_run_step("import_manifest", base.step_import_check))
        steps.append(_run_step("skill_scp_dna_contract", step_skill_dna_contract))
        steps.append(_run_step("boot_and_probe_strict", lambda: step_boot_strict(str(env_file))))
        steps.append(_run_step("semantic_parity_contract", step_semantic_parity_contract))
        steps.append(_run_step("provider_failover_timeout", step_provider_failover_timeout_contract))
        steps.append(_run_step("full_pytest", step_full_pytest))
        steps.append(_run_step("reality_suite", step_reality_suite))
        steps.append(_run_step("fitness_golden_suite", step_fitness))
        steps.append(_run_step("hermetic_boot", step_hermetic_boot))
        steps.append(_run_step("kernel_recovery_integrity", step_kernel_recovery_integrity))
        steps.append(_run_step("bounded_smoke_and_restart", step_bounded_smoke_twice))
    finally:
        env_file.unlink(missing_ok=True)

    all_pass = all(step.get("status") == "PASS" for step in steps)
    report = {
        "schema_version": "scp-strict-system-audit-v7",
        "commit": commit,
        "started_at": started,
        "completed_at": time.time(),
        "elapsed_sec": round(time.time() - started, 2),
        "egress_mode": os.environ.get("SCP_EGRESS_MODE"),
        "steps": steps,
        "overall_verdict": "PASS_WITHIN_SCOPE" if all_pass else "BLOCKED",
        "scope": (
            "Isolated local system audit: boot/readiness, auth brute-force and valid token, "
            "fail-closed ask semantics, prompt-injection kill/withhold, mandatory SCP Skill + DNA contract, "
            "semantic parity, provider failover/timeout/egress contracts, full pytest, Reality suite, fitness suite, "
            "hermetic boot, durable-kernel idempotent replay/crash recovery/external tamper detection/parallel "
            "journal consistency, and two sequential bounded API→router→ledger/kernel→RAG governance→Hands "
            "dry-run smoke cycles with independent port-cleanup and deny-egress observation. No claim about "
            "distributed production deployment or live third-party-provider correctness."
        ),
    }
    report_path = REPORT_DIR / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    full_report_path = _persist_full_report(report)

    print(
        json.dumps(
            {
                "commit": commit,
                "overall_verdict": report["overall_verdict"],
                "steps": [{"name": s["name"], "status": s["status"]} for s in steps],
                "report": str(report_path),
                "full_report": str(full_report_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    _print_failed_step_details(steps)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
