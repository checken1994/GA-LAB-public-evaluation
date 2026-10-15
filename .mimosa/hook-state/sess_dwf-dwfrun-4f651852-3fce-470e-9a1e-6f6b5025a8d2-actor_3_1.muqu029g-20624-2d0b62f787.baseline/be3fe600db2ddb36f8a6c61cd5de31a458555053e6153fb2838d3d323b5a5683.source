"""[A12 H-1] Scanner coverage cap pins — audit remediation round 2.

Bằng chứng bắt buộc cho mỗi walk-site quét cây ``scp/``:
  1. Cap >= 1000 file (cây scp/ có ~630 file .py — cap 500/400 cũ cắt im lặng
     ~20% cây).
  2. Walk deterministic: sort theo path TRƯỚC khi cap (thứ tự ``rglob`` phụ
     thuộc OS).
  3. WARNING tường minh khi truncation xảy ra — cấm cắt im lặng.
  4. Full-coverage: với cap mặc định trên cây scp/ thật, số file quét được ==
     số file eligible đếm độc lập (không bị cắt).
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

import scp.autofix.runner_phases.ast_scan as ast_scan
import scp.autofix.runner_phases.blast_radius as blast_radius
import scp.autofix.scanners.security_scanner as security_scanner
import scp.autofix.type_flow_verifier as type_flow_verifier
from scp.autofix.callgraph_delta import MAX_FILES_PER_BUILD

SCP_ROOT = Path(security_scanner._SCP_ROOT)

# (module, cap attr name) — mọi walk-site thuộc scope A12 H-1
_CAP_SITES = [
    (security_scanner, "_MAX_FILES"),
    (ast_scan, "_MAX_SCAN_FILES"),
    (blast_radius, "MAX_FILES_TO_SCAN"),
    (type_flow_verifier, "MAX_FILES_TO_SCAN"),
]


def _eligible_py_files(root: Path, skip_dirs: set[str]) -> list[Path]:
    """Đếm độc lập các file .py eligible (bỏ qua cache/venv/tests noise)."""
    return sorted(
        p for p in root.rglob("*.py")
        if not any(part in skip_dirs for part in p.parts)
    )


@pytest.mark.parametrize("module,attr", _CAP_SITES)
def test_cap_at_least_1000(module, attr):
    """Cap cũ 500/400 cắt ~20% cây scp/ — cap mới phải >= 1000."""
    cap = getattr(module, attr)
    assert isinstance(cap, int) and cap >= 1000, (
        f"{module.__name__}.{attr}={cap} < 1000 — scanner lại cắt im lặng cây scp/"
    )


def test_callgraph_delta_cap_at_least_1000():
    assert MAX_FILES_PER_BUILD >= 1000


def test_security_scanner_iter_is_deterministic_sorted():
    """Walk phải sort theo path — hai lần chạy cùng tree cùng thứ tự."""
    files_a = list(security_scanner._iter_python_files(SCP_ROOT))
    files_b = list(security_scanner._iter_python_files(SCP_ROOT))
    assert files_a == files_b
    assert files_a == sorted(files_a)
    assert len(files_a) > 0


def test_security_scanner_warns_and_truncates_on_cap_exceeded(tmp_path, caplog):
    """Cap vượt phải WARNING tường minh + trả đúng `limit` file (injectable)."""
    for i in range(5):
        (tmp_path / f"mod_{i}.py").write_text("x = 1\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="scp.autofix.scanners.security"):
        files = list(security_scanner._iter_python_files(tmp_path, limit=2))
    assert len(files) == 2  # truncation thật
    assert files == sorted(files)[:2]  # deterministic: 2 file đầu theo sort
    assert any("[scanner-cap]" in r.message for r in caplog.records), (
        "truncation xảy ra nhưng KHÔNG có warning — cắt im lặng (A12 H-1)"
    )


def test_ast_scan_iter_warns_on_truncation(tmp_path, caplog):
    for i in range(5):
        (tmp_path / f"mod_{i}.py").write_text("x = 1\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="scp.autofix.runner"):
        files = list(ast_scan._iter_python_files(tmp_path, limit=3))
    assert len(files) == 3
    assert any("[scanner-cap]" in r.message for r in caplog.records)


def test_type_flow_iter_warns_on_truncation(tmp_path, caplog, monkeypatch):
    for i in range(5):
        (tmp_path / f"mod_{i}.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(type_flow_verifier, "MAX_FILES_TO_SCAN", 3)
    with caplog.at_level(logging.WARNING, logger="scp.autofix.type_flow_verifier"):
        files = type_flow_verifier._iter_python_files(str(tmp_path))
    assert len(files) == 3
    assert any("[scanner-cap]" in r.message for r in caplog.records)


def test_blast_radius_iter_bounded_signal_and_warning(tmp_path, caplog):
    for i in range(5):
        (tmp_path / f"mod_{i}.py").write_text("x = 1\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="scp.autofix.blast_radius"):
        pairs = list(blast_radius._iter_python_files(tmp_path, max_files=3))
    assert len(pairs) == 4  # 3 file thường + 1 bounded-signal pair (contract cũ)
    assert pairs[-1][1] is True
    assert all(p[1] is False for p in pairs[:3])
    assert any("[scanner-cap]" in r.message for r in caplog.records)


def test_full_coverage_on_real_scp_tree():
    """Trên cây scp/ thật: cap không cắt — số file quét == số file eligible.

    Independent lineage: đếm rglob riêng với cùng bộ filter, không đi qua
    code của scanner.
    """
    eligible = _eligible_py_files(
        SCP_ROOT,
        skip_dirs={"__pycache__", ".venv", "venv", "node_modules",
                   ".pytest_cache", ".mypy_cache", ".ruff_cache"},
    )
    assert len(eligible) >= 500, (
        f"cây scp/ chỉ có {len(eligible)} file .py eligible — kiểm tra lại tree"
    )
    files = list(security_scanner._iter_python_files(SCP_ROOT))
    # filter riêng của security scanner (tests/examples/scripts/attack_payloads)
    expected = [
        p for p in eligible
        if "tests" not in p.parts
        and not p.name.startswith("test_")
        and not any(part in ("examples", "scripts", "attack_payloads") for part in p.parts)
    ]
    assert len(files) == len(expected), (
        f"scanner quét {len(files)}/{len(expected)} file eligible — "
        f"còn truncation dù cap=1000 (A12 H-1)"
    )
