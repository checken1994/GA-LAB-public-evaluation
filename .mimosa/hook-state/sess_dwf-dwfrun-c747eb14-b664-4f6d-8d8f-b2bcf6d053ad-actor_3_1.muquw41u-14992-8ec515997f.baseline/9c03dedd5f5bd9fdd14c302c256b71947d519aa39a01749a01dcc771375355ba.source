import subprocess
import sys

import pytest

from scp.autofix.runner_phases.ast_scan import _build_bug_report, _scan_file
from scp.verifier import IndependentVerifier

# ==============================================================================
# T07 - EPISTEMIC MISSING-PIECE DISCOVERY
# ==============================================================================
# Focus: SCP must not overclaim ("no findings" != "no bugs exist"). Known bug
# classes must be found, clean code must not be flagged, the independent
# verifier must return honest verdicts, and when independent Reality
# contradicts a clean scan the epistemic system must record a missing piece.
#
# Failure classification contract (HARNESS_BROKEN / PRODUCT_BLOCKED / PRODUCT_FAIL):
# every target below is a real production interface verified to exist. A red
# result here means PRODUCT_BLOCKED or PRODUCT_FAIL, never a stubbed harness.
# ==============================================================================


def test_scanner_recall_on_known_class_and_precision_on_clean_code(tmp_path):
    """Real production AST scanners: a known bug class is found; clean code is not flagged."""
    buggy = tmp_path / "buggy.py"
    buggy.write_text(
        "def load(path):\n"
        "    try:\n"
        "        return open(path).read()\n"
        "    except:\n"
        "        pass\n",
        encoding="utf-8",
    )
    clean = tmp_path / "clean.py"
    clean.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    bug_reports = [_build_bug_report(str(buggy), finding) for finding in _scan_file(buggy)]
    clean_findings = _scan_file(clean)

    assert any(report.bug_type == "BareExceptPass" for report in bug_reports), (
        f"Scanner missed a known bug class inside its coverage: "
        f"{[report.bug_type for report in bug_reports]}"
    )
    assert clean_findings == [], (
        f"Scanner flagged clean code (precision failure): {clean_findings}"
    )


def test_independent_verifier_honest_epistemic_verdicts():
    """The real independent verifier must return honest verdicts, never a silent pass."""
    verifier = IndependentVerifier()
    postcondition = {
        "all": [{"kind": "artifact_hash", "value": "a" * 64}],
        "evidence_required": True,
    }

    contradicted = verifier.verify(
        postcondition,
        {"artifact_hash": "b" * 64, "evidence_ref": "evidence://observed"},
    )
    assert contradicted.verdict == "CONTRADICTED", (
        "Verifier accepted a post-state that contradicts the postcondition (PASS != TRUE)"
    )

    insufficient = verifier.verify(postcondition, {"artifact_hash": "a" * 64})
    assert insufficient.verdict == "INSUFFICIENT", (
        "Verifier claimed VERIFIED without the required evidence ref"
    )

    unknown = verifier.verify(
        {"all": [{"kind": "human_intent_matches", "value": "approved"}]},
        {"evidence_ref": "evidence://observed"},
    )
    # The epistemic contract is "never a silent pass": an unevaluable condition
    # must come back INSUFFICIENT (schema-level rejection) or UNKNOWN (runtime
    # unknown kind) - never VERIFIED.
    assert unknown.verdict in {"INSUFFICIENT", "UNKNOWN"}, (
        f"Verifier silently passed an unevaluable condition kind: {unknown.verdict}"
    )
    assert unknown.verdict != "VERIFIED"


def test_missing_piece_discovery_on_reality_contradiction(tmp_path):
    """
    Contract: when independent Reality contradicts a clean scan, the epistemic
    system must record a missing-piece finding (coverage claim + blind-spot
    disclosure) instead of letting the clean scan stand.

    Steps 1-3 exercise real production behavior. Step 4 is the product
    capability itself and is currently absent, so this test stays red as an
    explicit PRODUCT_BLOCKED signal that drives implementation.
    """
    # 1. Real scanner honesty: a semantic authorization bug is outside the
    #    scanner's coverage. A clean scan here is honest, but it must never be
    #    treated as proof that the code is safe.
    suspicious = tmp_path / "auth_flow.py"
    suspicious.write_text(
        "def auth(user):\n"
        "    # semantic bug invisible to AST scanners: no authorization check\n"
        "    return True\n",
        encoding="utf-8",
    )
    findings = _scan_file(suspicious)
    assert not any("auth" in finding["description"].lower() for finding in findings), (
        "Fixture assumption broken: scanner unexpectedly claims coverage of the semantic bug"
    )

    # 2. Independent Reality observation: execute the module and observe the
    #    real authorization bypass at runtime.
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import sys; sys.path.insert(0, r'{tmp_path}'); "
            "import auth_flow; print(auth_flow.auth('stranger'))",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert probe.returncode == 0, probe.stderr
    observation_text = probe.stdout.strip()
    assert observation_text == "True", f"Unexpected runtime probe output: {observation_text!r}"

    # 3. The independent verifier contradicts the clean scan using the real
    #    observation: unauthenticated access must not be granted.
    verifier = IndependentVerifier()
    verdict = verifier.verify(
        {
            "all": [{"kind": "text_contains", "value": "False"}],
            "evidence_required": True,
        },
        {"text": observation_text, "evidence_ref": "evidence://auth-probe"},
    )
    assert verdict.verdict == "CONTRADICTED", (
        "Reality contradicted the clean scan but the verifier did not flag the contradiction"
    )

    # 4. Missing-piece discovery: Reality contradicted the scan, so SCP must
    #    record a MissingPieceFinding that discloses the scanner's blind spot
    #    and revises its coverage claim.
    try:
        from scp.meta.epistemic_boundary import EpistemicBoundary
    except ImportError as exc:
        pytest.fail(
            "PRODUCT_BLOCKED: missing-piece discovery is not implemented in "
            f"production (import scp.meta.epistemic_boundary failed: {exc}). "
            "Required capability: given a clean scan plus an independent Reality "
            "contradiction, record a missing-piece finding that discloses the "
            "scanner's blind spot and revises its coverage claim. Do NOT create "
            "that module as a stub or a simulated state to make this test pass - "
            "it must expose the real contradiction-to-missing-piece behavior."
        )
