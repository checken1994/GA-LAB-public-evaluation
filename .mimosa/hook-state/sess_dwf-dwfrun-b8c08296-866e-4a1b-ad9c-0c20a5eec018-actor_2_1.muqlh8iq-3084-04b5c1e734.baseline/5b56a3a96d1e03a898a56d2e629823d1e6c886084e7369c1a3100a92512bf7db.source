"""SCP Evolution Modes — package façade.

[A12 M-07] Trước đây file này chứa BẢN SAO verbatim 193 dòng của
``pattern_fixers.py`` (5 deterministic pattern fixers + ``FIXERS`` registry).
Census (commit fix(audit-r2)): toàn bộ production path đã đi thẳng vào
``scp.autofix.evolution_modes.pattern_fixers`` —

  - ``scp/autofix/evolution.py`` (6 method) import từ ``pattern_fixers``;
  - ``scp/autofix/llm_fix_parts/process_bug_with_llm.py`` resolve qua
    ``getattr(evo, fixer_name)`` -> evolution methods -> ``pattern_fixers``;
  - consumer duy nhất của bản sao ``__init__`` là
    ``tests/T03_capability/test_security_sweep_s3.py`` (import
    ``parameterize_sql`` từ package).

Bản sao 2 bản của cùng logic fixer là bẫy Catastrophic-Forgetting ngược:
sửa 1 bản, quên bản kia -> hai "nguồn sự thật" lệch nhau âm thầm. Package
``__init__`` giờ chỉ re-export từ ``pattern_fixers`` (một nguồn sự thật) và
giữ nguyên public API cho consumer hiện hữu.
"""
from __future__ import annotations

from scp.autofix.evolution_modes.pattern_fixers import (
    FIXERS,
    add_context_manager,
    add_lock,
    add_null_check,
    fix_logic_flow,
    fix_type_mismatch,
    parameterize_sql,
)

__all__ = [
    "FIXERS",
    "add_context_manager",
    "add_lock",
    "add_null_check",
    "fix_logic_flow",
    "fix_type_mismatch",
    "parameterize_sql",
]
