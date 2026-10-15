import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

import re
from pathlib import Path


def test_dead_audit_r9_no_external_imports():
    """
    Hệ thống chết 'audit_r9' phải bị cách ly hoàn toàn.
    Không có file nào bên ngoài thư mục 'audit_r9/' được phép import nó.
    Nếu fail → Zombie Leak: code chết đang ảnh hưởng đến code sống.
    """
    root = Path(__file__).parent.parent / "scp"
    pat = re.compile(r"^(from|import)\s+scp\.audit_r9\b")
    all_py = list(root.rglob("*.py"))
    violations = []

    for py_file in all_py:
        norm = str(py_file).replace("\\", "/")
        if "/scp/audit_r9/" in norm:
            continue  # Bỏ qua file nội bộ của chính dead_sys
        try:
            for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
                if pat.search(line.strip()):
                    violations.append(f"  {py_file.name}:{lineno}: {line.strip()}")
        except Exception:
            pass

    if violations:
        raise AssertionError(
            "[GAP-DEAD-ZONE] 'audit_r9' bị zombie-import bởi:\n" + "\n".join(violations) +
            "\n\nHành động: xóa import hoặc dời module ra khỏi Dead Zone."
        )
