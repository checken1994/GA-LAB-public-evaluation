"""[M-01 + A12 M-07] Scanner hygiene pins — audit remediation round 2.

M-01: ``api_wiring_scanner.py`` nhúng ``value[:8]`` (8 ký tự ĐẦU của API key
trong .env) vào BugReport description -> prefix leak vào report/log/dashboard.
Contract sau fix: BugReport chỉ giữ TÊN BIẾN — không bất kỳ phần nào của giá
trị secret.

A12 M-07: ``evolution_modes/__init__.py`` chứa BẢN SAO verbatim 193 dòng của
``pattern_fixers.py`` (5 fixers + FIXERS) — dead duplicate. Census: production
path đi qua ``pattern_fixers``; consumer duy nhất của ``__init__`` là import
``parameterize_sql``. Sau fix: ``__init__`` chỉ re-export (một nguồn sự thật)
— identity pin bảo đảm KHÔNG còn bản sao function object riêng.
"""
from __future__ import annotations

from pathlib import Path

import scp.autofix.evolution_modes as evolution_modes
from scp.autofix.evolution_modes import pattern_fixers
from scp.autofix.scanners.api_wiring_scanner import APIWiringScanner

SECRET_VALUE = "sk-totally-secret-key-0123456789"


# ================================================================
# M-01 — không leak secret vào BugReport
# ================================================================

def test_api_wiring_gap_report_contains_no_secret_slice(tmp_path):
    """Key .env có value nhưng không được reference -> BugReport KHÔNG chứa
    bất kỳ slice nào của secret (kể cả 8 ký tự đầu)."""
    env_path = tmp_path / ".env"
    env_path.write_text(
        f"UNREFERENCED_TEST_API_KEY={SECRET_VALUE}\n", encoding="utf-8"
    )
    scanner = APIWiringScanner(env_path=env_path, data_sources_dir=tmp_path)
    bugs = scanner.scan()

    gaps = [b for b in bugs if b.bug_type == "APIWiringGap"
            and "UNREFERENCED_TEST_API_KEY" in b.description]
    assert len(gaps) == 1, "scanner phải vẫn phát hiện wiring gap (guard không được tê liệt chức năng báo)"
    description = gaps[0].description
    assert "UNREFERENCED_TEST_API_KEY" in description  # tên biến được giữ
    # mọi slice tiềm năng của secret đều vắng mặt
    assert SECRET_VALUE not in description
    assert SECRET_VALUE[:8] not in description
    assert SECRET_VALUE[:4] not in description
    for word in description.split():
        assert word not in SECRET_VALUE or len(word) < 4, (
            f"fragment '{word}' của secret xuất hiện trong BugReport"
        )


def test_api_wiring_gap_report_keeps_var_name_for_operator(tmp_path):
    """Fix M-01 không được làm mất khả năng định vị của operator."""
    env_path = tmp_path / ".env"
    env_path.write_text("ORPHAN_KEY_API_KEY=value123\n", encoding="utf-8")
    scanner = APIWiringScanner(env_path=env_path, data_sources_dir=tmp_path)
    bugs = scanner.scan()
    assert any(
        "ORPHAN_KEY_API_KEY" in b.description and b.bug_type == "APIWiringGap"
        for b in bugs
    )


# ================================================================
# A12 M-07 — dead duplicate removal: identity re-export
# ================================================================

def test_evolution_modes_init_reexports_pattern_fixers_identity():
    """Fixers public qua package PHẢI là cùng function object với
    pattern_fixers — cấm bản sao định nghĩa riêng (2 nguồn sự thật)."""
    for name in ("fix_type_mismatch", "add_null_check", "add_lock",
                 "parameterize_sql", "add_context_manager", "fix_logic_flow"):
        assert getattr(evolution_modes, name) is getattr(pattern_fixers, name), (
            f"evolution_modes.{name} không còn là re-export — duplicate đã quay lại"
        )
    assert evolution_modes.FIXERS is pattern_fixers.FIXERS


def test_evolution_modes_registry_maps_identity():
    """FIXERS registry qua package vẫn map đúng 5 fixer identity."""
    assert evolution_modes.FIXERS["parameterize_sql"] is pattern_fixers.parameterize_sql
    assert evolution_modes.FIXERS["add_null_check"] is pattern_fixers.add_null_check


def test_init_source_no_longer_duplicates_fixer_logic():
    """Pin tĩnh: __init__ không chứa SEARCH/REPLACE fixer logic (bản sao cũ
    193 dòng) — chỉ re-export."""
    init_src = Path(evolution_modes.__file__).read_text(encoding="utf-8")
    assert "<<<<<<< SEARCH" not in init_src
    assert "re.match" not in init_src
