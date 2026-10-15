#!/usr/bin/env python3
"""Bounded npm audit with evidence; registry errors never become a green gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_ATTEMPTS = 3
ATTEMPT_TIMEOUT = 120
NPM_AUDIT_VERSION = "11.19.1"
TRANSIENT_CODES = {"E429", "E500", "E502", "E503", "E504", "ETIMEDOUT", "ECONNRESET", "EAI_AGAIN"}
NPM_AUDIT_TIMEOUT_MESSAGES = {
    "network timeout at: https://registry.npmjs.org/-/npm/v1/security/advisories/bulk",
    "network timeout at: https://registry.npmjs.org/-/npm/v1/security/audits/quick",
}


def classify(returncode: int, stdout: str) -> str:
    """Only a complete, successful native audit report can pass."""
    try:
        report = json.loads(stdout)
    except (ValueError, TypeError):
        return "HARNESS_BROKEN"
    if not isinstance(report, dict):
        return "HARNESS_BROKEN"
    metadata = report.get("metadata")
    findings = metadata.get("vulnerabilities") if isinstance(metadata, dict) else None
    if isinstance(findings, dict):
        severities = ("info", "low", "moderate", "high", "critical", "total")
        if any(type(findings.get(key)) is not int or findings[key] < 0 for key in severities):
            return "HARNESS_BROKEN"
        if sum(findings[key] for key in severities[:-1]) != findings["total"]:
            return "HARNESS_BROKEN"
        if findings["high"] or findings["critical"]:
            return "PRODUCT_FAIL"
        if report.get("auditReportVersion") != 2 or not isinstance(report.get("vulnerabilities"), dict):
            return "HARNESS_BROKEN"
        return "PASS_WITHIN_SCOPE" if returncode == 0 and not report.get("error") else "HARNESS_BROKEN"
    error = report.get("error")
    if returncode != 0 and isinstance(error, dict) and error.get("code") in TRANSIENT_CODES:
        return "RETRYABLE_REGISTRY_ERROR"
    # npm 10 on the Windows runner emits a timeout with no error.code. Match
    # only its observed registry-audit signature, not arbitrary error prose.
    if (returncode != 0 and isinstance(error, dict) and not error.get("code")
            and report.get("message") in NPM_AUDIT_TIMEOUT_MESSAGES):
        return "RETRYABLE_REGISTRY_ERROR"
    return "HARNESS_BROKEN"


def audit_command() -> list[str]:
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    node = shutil.which("node")
    if not npm or not node:
        raise RuntimeError("Node/npm are required for the mandatory dashboard security gate")
    # Direct Node invocation makes timeout kill the audit process itself,
    # rather than leaving an npm.cmd child running on Windows.
    configured = os.environ.get("SCP_AUDIT_NPM_CLI", "")
    candidates = ([Path(configured)] if configured else
                  [Path(npm).resolve(), Path(npm).parent / "node_modules/npm/bin/npm-cli.js"])
    cli = next((path for path in candidates if path.name == "npm-cli.js" and path.is_file()), None)
    if cli is None:
        raise RuntimeError("cannot locate npm-cli.js for bounded direct execution")
    package = json.loads((cli.parent.parent / "package.json").read_text(encoding="utf-8"))
    if package.get("name") != "npm" or package.get("version") != NPM_AUDIT_VERSION:
        raise RuntimeError(f"audit requires pinned npm {NPM_AUDIT_VERSION}; legacy quick-audit fallback is unsupported")
    return [node, str(cli), "audit", "--omit=dev", "--audit-level=high", "--json",
            "--fetch-retries=0", "--fetch-timeout=30000"]


def sanitized_report(stdout: str) -> str:
    """Retain the native report without registry response cookies/auth headers."""
    try:
        payload = json.loads(stdout)
    except ValueError:
        return json.dumps({"unparseable_report": True}) + "\n"

    def scrub(value):
        if isinstance(value, dict):
            return {key: "[REDACTED]" if key.lower() in {
                "headers", "authorization", "cookie", "set-cookie", "token", "password", "_authtoken"
            } else scrub(item) for key, item in value.items()}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    return json.dumps(scrub(payload), indent=2) + "\n"


def run_audit(dashboard: Path, output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    command = audit_command()
    lockfile = dashboard / "package-lock.json"
    evidence = {
        "gate": "dashboard_build_audit",
        "sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "scope": "native npm production dependency audit; build is a separate required workflow command",
        "lock_sha256": hashlib.sha256(lockfile.read_bytes()).hexdigest(),
        "command": command,
        "max_attempts": MAX_ATTEMPTS,
        "npm_audit_version": NPM_AUDIT_VERSION,
        "attempt_timeout_seconds": ATTEMPT_TIMEOUT,
        "bindings": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in (
                ".agents/skills/release-gate-skill-dna-bindings.json",
                ".agents/skills/scp-dna/SKILL.md",
                ".agents/skills/scp-dna/references/dna-principles.md",
                ".agents/skills/scp-runtime-audit/SKILL.md",
            )
        },
        "attempts": [],
        "status": "BLOCKED",
    }
    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.monotonic()
        try:
            result = subprocess.run(command, cwd=dashboard, capture_output=True,
                                    text=True, encoding="utf-8", errors="replace",
                                    timeout=ATTEMPT_TIMEOUT, check=False)
            status = classify(result.returncode, result.stdout)
            # Native JSON is the evidence, not a self-reported PASS string.
            (output / f"attempt-{attempt}.json").write_text(sanitized_report(result.stdout), encoding="utf-8")
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            status, returncode = "RETRYABLE_REGISTRY_ERROR", 124
        evidence["attempts"].append({
            "attempt": attempt, "exit_code": returncode, "status": status,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        })
        evidence["status"] = "BLOCKED" if status == "RETRYABLE_REGISTRY_ERROR" else status
        (output / "summary.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(f"npm audit attempt {attempt}/{MAX_ATTEMPTS}: {status}; exit={returncode}", flush=True)
        if status == "PASS_WITHIN_SCOPE":
            if hashlib.sha256(lockfile.read_bytes()).hexdigest() != evidence["lock_sha256"]:
                evidence["status"] = "HARNESS_BROKEN"
                (output / "summary.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
                return 1
            return 0
        if status != "RETRYABLE_REGISTRY_ERROR" or attempt == MAX_ATTEMPTS:
            return 1
        time.sleep(5 * attempt)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return run_audit(Path.cwd(), args.output.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
