import os

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_R8_DATA = REPO_ROOT / "docs" / "audit_history" / "audit_r8"

# audit_r8 is a still-isolated, data-only audit round zone. Authority: commit
# e40af00 (2026-09-22) relocated the round data from scp/audit_r8 to
# docs/audit_history/audit_r8 (pure rename, content unchanged), so the zone no
# longer lives inside the scp package. The isolation contract stays fail-closed:
# the round artifact must exist, stay data-only, and no product module may
# zombie-import scp.audit_r8.
_ZOMBIE_IMPORT = re.compile(r"^(from|import)\s+scp\.audit_r8\b")


def test_audit_r8_isolated_flow():
    '''FA-13: Cover audit_r8 flow (isolated, data-only audit round zone)'''
    assert AUDIT_R8_DATA.is_dir(), (
        f"audit_r8 must be present and connected to the audit history: "
        f"round artifacts missing at {AUDIT_R8_DATA}"
    )
    assert any(AUDIT_R8_DATA.iterdir()), "audit_r8 round artifacts directory is empty"

    py_files = list(AUDIT_R8_DATA.rglob("*.py"))
    assert not py_files, f"audit_r8 must stay data-only, found Python files: {py_files}"

    # Zombie-import scan: no module under scp/ may import the isolated zone.
    violations = []
    for py_file in (REPO_ROOT / "scp").rglob("*.py"):
        if "/scp/audit_r8/" in py_file.as_posix():
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue
        for line in content.splitlines():
            stripped = line.strip()
            if _ZOMBIE_IMPORT.search(stripped):
                violations.append(f"{py_file}: {stripped}")
    assert not violations, (
        "audit_r8 must be importable and connected: isolated zone zombie-imported by:\n"
        + "\n".join(violations)
    )
