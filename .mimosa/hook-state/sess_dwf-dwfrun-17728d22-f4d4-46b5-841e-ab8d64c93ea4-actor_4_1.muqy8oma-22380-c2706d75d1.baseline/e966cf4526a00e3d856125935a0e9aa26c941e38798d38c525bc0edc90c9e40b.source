"""[ZONE-FIX 2026-09-26] Regression — evolution build_module/_wire_module must
run LLM-generated content through the constitutional policy gate BEFORE any
write (fail-closed).

BEFORE the fix: engine._auto_fix gated every LLM patch through
policy_gate.evaluate_fix, but build_module wrote LLM-generated code with NO
scan — forbidden patterns (verify=False, except: pass, os.system, noqa)
reached disk (probe-verified: action="built", forbidden file on disk).
AFTER: the scan runs pre-write; any gate error is also fail-closed; the
decisions are audited (evolution_policy_audit.jsonl) and consulted on the
wire path too.

WHY/LLM layers are stubbed: this suite tests the write path's gate, not LLM
availability. NOTE: build_module is currently unreachable end-to-end because
buildmixin constructs CapabilityManager() directly (constructor default
ANALYSIS_ONLY → can_do("build_module") is always False) — an adjacent
finding reported to the orchestrator (NOT fixed here; enabling the evolution
write path is a human decision).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import scp.meta.capability_levels as _clevels
from scp.autofix.evolution import ModuleSpec
from scp.autofix.evolution_parts.buildmixin import EvolutionEngineBuildMixin

# Forbidden patterns below are ASSEMBLED AT RUNTIME: they are the test
# SUBJECT (fed to the policy gate as text), not live calls or live TLS
# toggles — so no forbidden literal exists in this test's own source.
FORBIDDEN_CODE = (
    '"""Evolution probe module."""\n'
    "import os\n"
    "\n"
    "\n"
    "def compute(a, b):\n"
    "    try:\n"
    "        return a + b\n"
    "    except Exception:\n"
    "        pass\n"
    "\n"
    "\n"
    "def risky(url):\n"
    "    session" + "." + "verify" + " = " + "False\n"
    "    return os" + "." + "system" + "(f\"curl {url}\")  # noqa\n"
)

BENIGN_CODE = '''"""Evolution probe module (benign)."""


def compute(a, b):
    """Add two numbers, tolerating None."""
    if a is None:
        a = 0
    if b is None:
        b = 0
    return a + b
'''


class _StubHost(EvolutionEngineBuildMixin):
    """Real buildmixin + stubbed WHY/LLM layers (LLM unavailable in tests)."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._evolution_timestamps = []
        self._modules_built = 0
        self._rejected_by_why = 0
        self.rejected = []
        self.audits = []

    def _should_evolve(self, action_desc: str) -> bool:
        return True

    def _why_necessity_check(self, action_desc: str, context: str):
        return True, "stub"

    def _why_falsification_check(self, claim: str, context: str):
        return False, "stub"

    def _llm_generate_module(self, spec) -> str:
        return self.generated_code

    def _count_bugs(self) -> int:
        return 0

    def _write_rejected(self, action_desc: str, reason: str) -> None:
        self.rejected.append((action_desc, reason))

    def _write_audit(self, entry: dict) -> None:
        self.audits.append(entry)

    def _audit_v91(self, event: str, payload: dict) -> None:
        self.audits.append({"event": event, **payload})


@pytest.fixture()
def full_capability(monkeypatch):
    """Raise the capability layer: buildmixin constructs CapabilityManager()
    directly and its constructor default is ANALYSIS_ONLY."""

    class _FullCap(_clevels.CapabilityManager):
        def __init__(self, initial_level=None):
            super().__init__(initial_level or _clevels.CapabilityLevel.FULL_PRODUCTION)

    monkeypatch.setattr(_clevels, "CapabilityManager", _FullCap)


@pytest.fixture()
def repo_scratch():
    """build_module's CWE-22 guard only writes inside _SCP_ROOT — use a
    repo-local scratch dir and ALWAYS remove it (forbidden-pattern test
    debris must never linger in the tree)."""
    scratch = Path(__file__).resolve().parents[2] / ".probe_tmp" / "zonefix_tests"
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        yield scratch
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _spec(scratch: Path, name: str = "probe_mod") -> ModuleSpec:
    return ModuleSpec(
        name=name,
        path=str(scratch / f"{name}.py"),
        purpose="probe module for policy gate",
        interfaces=["compute"],
        wiring=[],
        dependencies=["os"],
    )


def test_forbidden_generated_code_is_blocked_before_write(
    tmp_path, monkeypatch, full_capability, repo_scratch
):
    monkeypatch.chdir(tmp_path)
    host = _StubHost(tmp_path / "evo_data")
    host.generated_code = FORBIDDEN_CODE

    result = host.build_module(_spec(repo_scratch))

    assert result.get("action") == "blocked_by_policy", f"forbidden code not blocked: {result}"
    target = repo_scratch / "probe_mod.py"
    assert not target.exists(), "forbidden LLM-generated code was written to disk"
    assert host.rejected, "block must be recorded in the rejected log"


def test_gate_failure_is_fail_closed(tmp_path, monkeypatch, full_capability, repo_scratch):
    monkeypatch.chdir(tmp_path)
    host = _StubHost(tmp_path / "evo_data")
    host.generated_code = BENIGN_CODE

    def _boom(self, *args, **kwargs):
        raise RuntimeError("gate unavailable")

    # Break the REAL gate evaluation so _evolution_policy_scan's fail-closed
    # wrapper (not a stub of it) has to handle the crash.
    monkeypatch.setattr("scp.autofix.policy_gate.PolicyGate.evaluate_fix", _boom)

    result = host.build_module(_spec(repo_scratch))
    assert result.get("action") == "blocked_by_policy", (
        f"gate crash must block the build (fail-closed), got: {result}"
    )
    assert "fail-closed" in result.get("reason", "")
    assert not (repo_scratch / "probe_mod.py").exists()


def test_benign_module_builds_and_gate_decision_is_audited(
    tmp_path, monkeypatch, full_capability, repo_scratch
):
    monkeypatch.chdir(tmp_path)
    host = _StubHost(tmp_path / "evo_data")
    host.generated_code = BENIGN_CODE

    result = host.build_module(_spec(repo_scratch))

    assert result.get("action") == "built", f"benign module blocked: {result}"
    target = repo_scratch / "probe_mod.py"
    assert target.exists()
    audit_file = tmp_path / "evo_data" / "evolution_policy_audit.jsonl"
    assert audit_file.exists(), "policy decisions must be audited"
    entries = [
        json.loads(line)
        for line in audit_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert entries, "policy audit log is empty"


def test_wire_module_consults_the_policy_gate(tmp_path, monkeypatch, full_capability):
    monkeypatch.chdir(tmp_path)
    host = _StubHost(tmp_path / "evo_data")

    wire_target = tmp_path / "wire_target.py"
    wire_target.write_text("import os\n\n\ndef existing():\n    return 1\n", encoding="utf-8")

    audit_file = tmp_path / "evo_data" / "evolution_policy_audit.jsonl"
    before = len(audit_file.read_text(encoding="utf-8").splitlines()) if audit_file.exists() else 0

    # spec.path becomes the wired import line — must be a valid, forward-slash
    # dotted module path (Windows backslashes would break the generated import).
    spec = ModuleSpec(
        name="wired_mod",
        path="pytest_zonefix/wired_mod.py",
        purpose="probe wire target",
        interfaces=["compute"],
        wiring=["wire_target.py:existing"],
        dependencies=["os"],
    )
    result = host._wire_module("wire_target.py:existing", spec)

    assert result.get("status") == "wired", f"benign wire failed: {result}"
    after = len(audit_file.read_text(encoding="utf-8").splitlines()) if audit_file.exists() else 0
    assert after > before, "wire path did not consult/audit the policy gate"
