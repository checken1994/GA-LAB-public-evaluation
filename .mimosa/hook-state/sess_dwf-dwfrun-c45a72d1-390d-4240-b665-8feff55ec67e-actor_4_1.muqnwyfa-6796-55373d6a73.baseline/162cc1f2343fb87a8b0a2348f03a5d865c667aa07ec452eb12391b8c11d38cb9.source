from __future__ import annotations

from pathlib import Path

import yaml

RC_WORKFLOW = Path(".github/workflows/scp-rc-promotion.yml")
PRE_RC_WORKFLOW = Path(".github/workflows/scp-release-gate.yml")
WORKFLOW_DIR = Path(".github/workflows")


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(data: dict):
    # PyYAML 1.1 may deserialize the YAML key `on` as boolean True.
    return data.get("on") if "on" in data else data.get(True, {})


def _has_push(data: dict) -> bool:
    triggers = _triggers(data)
    if triggers == "push":
        return True
    if isinstance(triggers, dict):
        return "push" in triggers
    if isinstance(triggers, list):
        return "push" in triggers
    return False


def _step_using(steps: list[dict], action_prefix: str) -> dict:
    matches = [step for step in steps if str(step.get("uses", "")).startswith(action_prefix)]
    assert len(matches) == 1, f"expected exactly one {action_prefix} step, found {len(matches)}"
    return matches[0]


def _step_named(steps: list[dict], name: str) -> dict:
    matches = [step for step in steps if step.get("name") == name]
    assert len(matches) == 1, f"expected exactly one {name!r} step, found {len(matches)}"
    return matches[0]


def test_rc_promotion_declares_push_trigger() -> None:
    assert _has_push(_load(RC_WORKFLOW)), "authoritative RC workflow must continue to run on push"


def test_push_release_gates_provision_declared_runtimes_unconditionally() -> None:
    jobs = _load(RC_WORKFLOW)["jobs"]

    platform_steps = jobs["platform-gates"]["steps"]
    platform_python = _step_using(platform_steps, "actions/setup-python@")
    platform_node = _step_using(platform_steps, "actions/setup-node@")

    assert platform_python["with"]["python-version"] == "3.12"
    assert "if" not in platform_python
    assert str(platform_node["with"]["node-version"]) == "20"
    assert "if" not in platform_node

    python_verify = str(_step_named(platform_steps, "Verify Python 3.12 runtime")["run"])
    node_verify = str(_step_named(platform_steps, "Verify Node 20 runtime")["run"])
    assert "sys.version_info[:2] == (3, 12)" in python_verify
    assert "process.versions.node.split('.')[0] !== '20'" in node_verify

    manifest_steps = jobs["manifest-provenance"]["steps"]
    manifest_python = _step_using(manifest_steps, "actions/setup-python@")
    assert manifest_python["with"]["python-version"] == "3.12"
    assert "if" not in manifest_python


def test_no_push_workflow_event_gates_runtime_setup() -> None:
    """A push-capable workflow must not hide runtime setup behind workflow_dispatch only."""
    for workflow_path in sorted(WORKFLOW_DIR.glob("*.yml")):
        data = _load(workflow_path)
        if not _has_push(data):
            continue

        for job_name, job in data.get("jobs", {}).items():
            for step in job.get("steps", []):
                uses = str(step.get("uses", ""))
                if not (uses.startswith("actions/setup-python@") or uses.startswith("actions/setup-node@")):
                    continue
                condition = str(step.get("if", ""))
                assert "workflow_dispatch" not in condition or "push" in condition, (
                    f"{workflow_path.name}:{job_name} gates {uses} with {condition!r}; "
                    "push would be able to skip runtime provisioning"
                )


def test_pre_rc_mutation_budget_matches_authoritative_release_gate() -> None:
    rc_steps = _load(RC_WORKFLOW)["jobs"]["security-and-durability"]["steps"]
    pre_rc_steps = _load(PRE_RC_WORKFLOW)["jobs"]["pre-rc-verification"]["steps"]

    rc_command = str(_step_named(rc_steps, "Live mutation testing gate")["run"])
    pre_rc_command = str(_step_named(pre_rc_steps, "Bounded live mutation score gate")["run"])

    for command in (rc_command, pre_rc_command):
        assert "--max-mutants 15" in command
        assert "--min-score 0.40" in command


def test_authoritative_workflow_pytest_paths_exist() -> None:
    import re

    root = Path(__file__).resolve().parents[2]
    for workflow_path in (RC_WORKFLOW, PRE_RC_WORKFLOW):
        content = _load(workflow_path)
        missing: list[str] = []
        for job_name, job in content.get("jobs", {}).items():
            for step in job.get("steps", []):
                cmd = str(step.get("run", ""))
                for match in re.finditer(r"(tests/[\w/]+\.py)", cmd):
                    rel_path = match.group(1)
                    if not (root / rel_path).is_file():
                        missing.append(f"{workflow_path}:{job_name} -> {rel_path}")
                for match in re.finditer(r"python\s+((?:tools|scripts)/[\w/]+\.py)", cmd):
                    rel_path = match.group(1)
                    if not (root / rel_path).is_file():
                        missing.append(f"{workflow_path}:{job_name} -> {rel_path}")
        assert not missing, f"Workflow references non-existent test/script paths: {missing}"


def test_acceptance_fixture_does_not_disable_semantic_crosscheck_or_share_state() -> None:
    source = Path("scripts/run_scp_acceptance.py").read_text(encoding="utf-8")

    assert '"SCP_MULTI_LLM_CROSSCHECK": "0"' not in source
    assert '"OPENAI_MODEL": "acceptance-judge-secondary"' in source


def test_acceptance_fixture_seeds_isolated_distinct_family_pricing_proofs(tmp_path: Path) -> None:
    source = Path("scripts/run_scp_acceptance.py").read_text(encoding="utf-8")
    assert '"OPENROUTER_MODEL_JUDGE_PRIMARY": "acceptance-judge-primary"' in source
    assert '"OPENAI_MODEL": "acceptance-judge-secondary"' in source
    assert "SCP_LLM_FALLBACK_PROVIDERS" in source

