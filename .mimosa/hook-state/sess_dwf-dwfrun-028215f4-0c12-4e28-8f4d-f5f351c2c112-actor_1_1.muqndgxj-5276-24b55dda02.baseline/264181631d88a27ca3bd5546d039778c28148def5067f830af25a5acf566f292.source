import os
from pathlib import Path

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

from scp.release.evidence_authority import (
    EvidenceAuthority,
    ReleaseEvidenceAuthority,
    _canonical_json,
    _sha256,
)


def test_release_isolated_flow(tmp_path: Path):
    """FA-13: Cover release flow with genuine behavioral execution.

    Verifies canonical JSON serialization, deterministic SHA-256 digests,
    EvidenceAuthority commit hashing, and ReleaseEvidenceAuthority claim generation.
    """
    # 1. Behavioral: Canonical JSON sorts keys deterministically
    raw_dict = {"z": 100, "b": 20, "a": [3, 2, 1]}
    canon_bytes = _canonical_json(raw_dict)
    assert canon_bytes == b'{"a":[3,2,1],"b":20,"z":100}'

    # 2. Behavioral: SHA-256 digest is exact and deterministic
    assert _sha256(b"hello") == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    # 3. Behavioral: EvidenceAuthority resolves commit and repository path
    auth = EvidenceAuthority(".")
    assert auth.repo_path.exists()
    head_sha = auth._resolve_commit("HEAD")
    assert isinstance(head_sha, str)
    assert len(head_sha) == 40

    # 4. Behavioral: ReleaseEvidenceAuthority generates release claim bound to commit
    rel_auth = ReleaseEvidenceAuthority(repo_path=".")
    claim = rel_auth.generate_release_claim(tested_sha=head_sha)
    assert claim["schema_version"] == "scp-evidence-authority-v1"
    assert claim["tested_sha"] == head_sha
    assert "artifact_hashes" in claim
    assert "evidence_digest" in claim
    assert isinstance(claim["artifact_hashes"], dict)
