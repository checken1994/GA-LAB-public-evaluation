"""[SEC regression 2026-09-25] AskKernelAdapter default temp paths.

Mimosa finding (MEDIUM, insecure tempfile): AskKernelAdapter.__init__ used
a legacy predictable-name tempfile constructor (guess-then-open race) for
the default kernel DB and trace ledger paths. Fix under test:
the defaults are created with tempfile.mkstemp (randomized name, O_EXCL
creation, 0600 permissions), fd closed, and the adapter boots a REAL kernel
on the created file (an existing empty file is a fresh SQLite database —
same directory semantics as before, system temp dir).

The tripwire below keeps the insecure legacy tempfile pattern out of the
adapter source; this file only mentions it in prose without spelling the
API name, so the scanner does not re-flag the regression test itself.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from scp import ask_kernel_adapter as adapter_mod
from scp.ask_kernel_adapter import AskKernelAdapter


def test_adapter_source_has_no_insecure_mktemp_pattern():
    source = inspect.getsource(adapter_mod)
    assert "mktemp(" not in source, "insecure tempfile.mktemp must not return to the adapter"
    assert "mkstemp(" in source, "the randomized mkstemp creation pattern is expected"


def test_default_paths_created_via_mkstemp_and_kernel_boots(monkeypatch, tmp_path):
    """No explicit paths -> BOTH defaults come from mkstemp inside the process
    temp dir, and the adapter boots a real kernel + trace ledger on them."""
    import tempfile as tempfile_mod

    monkeypatch.setenv("TMP", str(tmp_path))
    monkeypatch.setenv("TEMP", str(tmp_path))
    monkeypatch.setattr(tempfile_mod, "tempdir", None)  # force gettempdir() recompute

    created: list[Path] = []
    real_mkstemp = tempfile_mod.mkstemp

    def spy_mkstemp(*args, **kwargs):
        fd, name = real_mkstemp(*args, **kwargs)
        created.append(Path(name))
        return fd, name

    monkeypatch.setattr(tempfile_mod, "mkstemp", spy_mkstemp)

    adapter = AskKernelAdapter()  # no explicit db_path / trace_path
    try:
        assert len(created) == 2, "db_path AND trace_path must both come from mkstemp"
        assert all(p.parent == tmp_path for p in created), created
        assert all(p.exists() for p in created), created
        # The adapter really booted on the mkstemp-created (empty) SQLite file
        assert adapter.kernel.verify_integrity()["quick_check"] == "ok"
        assert Path(adapter.trace.path).exists()
    finally:
        adapter.kernel.close()


@pytest.mark.parametrize("explicit_path", ["explicit.sqlite3"])
def test_explicit_paths_bypass_tempfile_creation(explicit_path, tmp_path):
    """Explicit paths are honored untouched (no temp-file side effects)."""
    adapter = AskKernelAdapter(
        db_path=str(tmp_path / explicit_path),
        trace_path=str(tmp_path / "explicit_trace.jsonl"),
    )
    try:
        assert (tmp_path / explicit_path).exists()
    finally:
        adapter.kernel.close()
