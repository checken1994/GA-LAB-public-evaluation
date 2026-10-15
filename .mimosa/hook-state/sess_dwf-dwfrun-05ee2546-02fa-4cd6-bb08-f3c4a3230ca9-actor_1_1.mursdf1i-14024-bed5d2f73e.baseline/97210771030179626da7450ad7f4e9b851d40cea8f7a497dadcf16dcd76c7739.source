import subprocess
from pathlib import Path

import pytest

# ==============================================================================
# T11 - SHA EVIDENCE BINDING & RELEASE AUTHORITY - ISOLATED HARNESS
# ==============================================================================
# The main checkout is NEVER touched: all git operations run in a temp repo
# created with its own identity (the 2026-09-01 harness mutated the live
# checkout with commit + reset --hard - that class of harness is now forbidden
# by T00). EvidenceAuthority (dynamic, runtime evidence binding) does not
# exist in production (audit 2026-09-01) so the dynamic half stays RED as an
# explicit PRODUCT_BLOCKED, with the isolated harness kept as its ready-made
# contract.
# ==============================================================================


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def test_sha_evidence_binding_rejects_stale_head_in_isolated_repo(tmp_path):
    """Evidence bound to SHA X must be REJECTED once HEAD is Y - inside a throwaway repo."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "t11@isolated.test")
    _git(repo, "config", "user.name", "T11 Isolated Harness")
    (repo / "artifact.txt").write_text("evidence-payload", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "base evidence snapshot")
    sha_a = _git(repo, "rev-parse", "HEAD")

    (repo / "artifact.txt").write_text("changed-payload", encoding="utf-8")
    _git(repo, "commit", "-am", "next commit moves HEAD")
    sha_b = _git(repo, "rev-parse", "HEAD")
    assert sha_a != sha_b and len(sha_a) == 40

    try:
        from scp.release.evidence_authority import EvidenceAuthority
    except ImportError as exc:
        pytest.fail(
            "PRODUCT_BLOCKED: no runtime evidence authority exists in production "
            f"(import scp.release.evidence_authority failed: {exc}). Required "
            "contract, exercised on the isolated repo above: "
            "EvidenceAuthority(repo_path=...).generate_evidence(output, tested_sha) "
            "must bind evidence to the tested SHA plus DNA hash, skill hashes and "
            "test-profile/config/manifest hashes; validate_evidence(..., "
            "current_head=...) must REJECT evidence whose tested_sha != "
            "current_head. Static workflow guards alone are A-level evidence, "
            "not the C-level dynamic binding Complete SCP requires."
        )

    authority = EvidenceAuthority(repo_path=str(repo))
    evidence_file = tmp_path / "evidence.json"
    authority.generate_evidence(output=str(evidence_file), tested_sha=sha_a)
    is_valid = authority.validate_evidence(str(evidence_file), current_head=sha_b)
    assert is_valid is False, (
        "EvidenceAuthority accepted evidence from a stale SHA (violates PASS != TRUE)"
    )
