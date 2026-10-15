from __future__ import annotations

import json
import subprocess

import pytest

from tools import run_dashboard_audit as audit


def clean_report(**counts):
    severities = dict.fromkeys(("info", "low", "moderate", "high", "critical"), 0)
    severities.update(counts)
    severities["total"] = sum(severities.values())
    return {"auditReportVersion": 2, "vulnerabilities": {},
            "metadata": {"vulnerabilities": severities}}


@pytest.mark.parametrize("code,report,expected", [
    (0, clean_report(), "PASS_WITHIN_SCOPE"),
    (0, clean_report(moderate=2), "PASS_WITHIN_SCOPE"),
    (1, clean_report(), "HARNESS_BROKEN"),
    (0, clean_report(high=1), "PRODUCT_FAIL"),
    (1, clean_report(critical=1), "PRODUCT_FAIL"),
    (1, {"error": {"code": "E503"}}, "RETRYABLE_REGISTRY_ERROR"),
    (1, {"error": {"code": "ETIMEDOUT"}}, "RETRYABLE_REGISTRY_ERROR"),
    (0, {"error": {"code": "E503"}}, "HARNESS_BROKEN"),
    (1, {"error": {"code": "E401"}}, "HARNESS_BROKEN"),
    (1, {"error": {"code": "ENOLOCK"}}, "HARNESS_BROKEN"),
    (0, {}, "HARNESS_BROKEN"),
    (0, {"metadata": None}, "HARNESS_BROKEN"),
    (0, [], "HARNESS_BROKEN"),
])
def test_native_audit_outcome_remains_fail_closed(code, report, expected):
    assert audit.classify(code, json.dumps(report)) == expected


def test_incomplete_or_contradictory_report_cannot_pass():
    assert audit.classify(0, "PASS") == "HARNESS_BROKEN"
    for field, value in (("high", "0"), ("high", -1), ("total", 1), ("high", False)):
        report = clean_report()
        report["metadata"]["vulnerabilities"][field] = value
        assert audit.classify(0, json.dumps(report)) == "HARNESS_BROKEN"


def test_observed_windows_npm_timeout_without_code_is_retryable_not_green():
    report = {"message": "network timeout at: https://registry.npmjs.org/-/npm/v1/security/audits/quick",
              "error": {"summary": "", "detail": ""}}
    assert audit.classify(1, json.dumps(report)) == "RETRYABLE_REGISTRY_ERROR"
    assert audit.classify(0, json.dumps(report)) == "HARNESS_BROKEN"
    report["message"] = "network timeout at: https://untrusted.example/audit"
    assert audit.classify(1, json.dumps(report)) == "HARNESS_BROKEN"


@pytest.mark.parametrize("outcomes,expected_exit,expected_calls", [
    ([(1, {"error": {"code": "E503"}}), (0, clean_report())], 0, 2),
    ([(1, {"error": {"code": "E503"}})] * 3, 1, 3),
    ([(1, clean_report(high=1)), (0, clean_report())], 1, 1),
    ([(1, {"error": {"code": "E401"}}), (0, clean_report())], 1, 1),
    (["timeout"] * 3, 1, 3),
])
def test_retries_are_finite_and_never_retry_security_findings(tmp_path, monkeypatch,
                                                            outcomes, expected_exit, expected_calls):
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    command = ["node", "npm-cli.js", "audit", "--omit=dev", "--audit-level=high", "--json"]
    monkeypatch.setattr(audit, "audit_command", lambda: command)
    monkeypatch.setattr(audit.subprocess, "check_output", lambda *a, **k: "a" * 40)
    monkeypatch.setattr(audit.time, "sleep", lambda *a: None)
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        assert kwargs["timeout"] == 120
        outcome = outcomes[len(calls) - 1]
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(cmd, 120)
        code, report = outcome
        return subprocess.CompletedProcess(cmd, code, json.dumps(report), "")

    monkeypatch.setattr(audit.subprocess, "run", run)
    output = tmp_path / "evidence"
    assert audit.run_audit(tmp_path, output) == expected_exit
    assert len(calls) == expected_calls
    summary = json.loads((output / "summary.json").read_text())
    assert summary["sha"] == "a" * 40
    assert len(summary["attempts"]) == expected_calls
    assert bool(summary["status"] == "PASS_WITHIN_SCOPE") is (expected_exit == 0)
    assert len(summary["bindings"]) == 4


def test_production_threshold_is_not_configurable_downward():
    from pathlib import Path
    source = Path(audit.__file__).read_text(encoding="utf-8")
    assert '"--omit=dev"' in source and '"--audit-level=high"' in source
    assert "MAX_ATTEMPTS = 3" in source


def test_registry_response_credentials_are_not_written_to_evidence():
    report = {"error": {"code": "E503"}, "headers": {"set-cookie": "fixture-cookie-must-not-persist"},
              "nested": [{"authorization": "fixture-auth-must-not-persist"}]}
    rendered = audit.sanitized_report(json.dumps(report))
    assert "fixture-cookie-must-not-persist" not in rendered
    assert "fixture-auth-must-not-persist" not in rendered
    assert json.loads(rendered)["error"]["code"] == "E503"
    assert json.loads(audit.sanitized_report(json.dumps(clean_report()))) == clean_report()
    assert json.loads(audit.sanitized_report("raw invalid response")) == {"unparseable_report": True}


def test_legacy_npm_cannot_silently_reintroduce_quick_audit_fallback(tmp_path, monkeypatch):
    cli = tmp_path / "bin" / "npm-cli.js"
    cli.parent.mkdir()
    cli.write_text("// fixture", encoding="utf-8")
    package = tmp_path / "package.json"
    monkeypatch.setenv("SCP_AUDIT_NPM_CLI", str(cli))
    monkeypatch.setattr(audit.shutil, "which", lambda name: str(tmp_path / name))
    package.write_text(json.dumps({"name": "npm", "version": "10.8.2"}))
    with pytest.raises(RuntimeError, match="pinned npm"):
        audit.audit_command()
    package.write_text(json.dumps({"name": "npm", "version": "11.19.1"}))
    assert str(cli) in audit.audit_command()


def test_both_dashboard_workflows_install_the_pinned_bulk_only_auditor():
    from pathlib import Path

    import yaml
    for filename, job_name, step_name in (
        ("scp-rc-promotion.yml", "platform-gates", "Dashboard install, security audit, and build"),
        ("scp-release-gate.yml", "pre-rc-verification", "Dashboard install, production audit, and build"),
    ):
        workflow = yaml.safe_load(Path(".github/workflows", filename).read_text(encoding="utf-8"))
        step = next(step for step in workflow["jobs"][job_name]["steps"] if step.get("name") == step_name)
        assert "npm@11.19.1" in step["run"]
        assert "SCP_AUDIT_NPM_CLI" in step["env"]
        assert "python " + "." * 2 + "/tools/run_dashboard_audit.py" in step["run"]
        assert "npm run build" in step["run"]
