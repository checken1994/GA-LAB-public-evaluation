"""[Agent4 V3] Unified trace ledger writer/reader must share one runtime path.

Regression for the CWD-relative ``data/`` split-brain: before the fix,
``AskKernelAdapter._unified_ledger_path()`` resolved ``Path("data")`` against
the process CWD (with a repo-root fallback) while the /v3/trace reader
(``scp.api_server_parts._trace_impl``) resolves ``runtime_data_dir()``. With
``SCP_DATA_DIR`` set - or any CWD other than the repo root - terminal run
dispositions were appended to a file the trace reader never looks at, so
finished runs vanished from the audit trail (404 on lookup).

Contracts pinned here:
1. Default (no SCP_DATA_DIR): writer path == repo ``data/`` trace_ledger.jsonl
   - identical to the legacy default (no behavior change).
2. ``SCP_DATA_DIR`` set: writer path == ``$SCP_DATA_DIR/trace_ledger.jsonl``,
   i.e. the same candidate file the reader probes first.
3. Writer/reader agreement: appending through the writer path lands in a file
   the reader resolution yields.
The real ``data/`` ledger of the operator is never touched: only ``tmp_path``
locations are exercised.
"""
from __future__ import annotations

from pathlib import Path

from scp.ask_kernel_adapter import AskKernelAdapter
from scp.core import runtime_paths
from scp.core.runtime_paths import runtime_data_dir
from scp.trace_ledger import TraceLedger


def _repo_data_dir() -> Path:
    return Path(runtime_paths.__file__).resolve().parents[2] / "data"


def test_unified_ledger_default_matches_repo_data_dir(monkeypatch):
    monkeypatch.delenv("SCP_DATA_DIR", raising=False)
    expected = _repo_data_dir() / "trace_ledger.jsonl"
    assert AskKernelAdapter._unified_ledger_path() == expected


def test_unified_ledger_honors_scp_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("SCP_DATA_DIR", str(tmp_path))
    expected = Path(tmp_path) / "trace_ledger.jsonl"
    assert AskKernelAdapter._unified_ledger_path() == expected


def test_unified_ledger_writer_reader_agreement(monkeypatch, tmp_path):
    """Append via the writer path must land where the reader looks first."""
    monkeypatch.setenv("SCP_DATA_DIR", str(tmp_path))
    writer = AskKernelAdapter._unified_ledger_path()
    reader_first_candidate = runtime_data_dir() / "trace_ledger.jsonl"
    assert writer == reader_first_candidate
    TraceLedger(writer).append(trace_id="trace_agent4_probe", marker="v3-round2")
    assert reader_first_candidate.exists()
    found = TraceLedger(reader_first_candidate, verify_on_init=False).get_trace("trace_agent4_probe")
    assert found is not None
    assert found["fields"]["marker"] == "v3-round2"

def test_legacy_cwd_resolution_would_split_brain(monkeypatch, tmp_path):
    """Old-code-fails proof: the pre-fix CWD-relative algorithm resolves a
    DIFFERENT ledger than the /v3/trace reader when SCP_DATA_DIR is set (the
    split-brain this regression closes). Pins the failure mode itself."""
    monkeypatch.setenv("SCP_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)  # writer CWD-relative default would land here

    def _legacy_unified_ledger_path(module_file: Path) -> Path:
        _data_dir = Path("data")
        if not _data_dir.exists():
            _data_dir = module_file.resolve().parent.parent / "data"
        return _data_dir / "trace_ledger.jsonl"

    legacy_path = _legacy_unified_ledger_path(Path(AskKernelAdapter.__module__.replace(".", "\\") + ".py"))
    reader_path = runtime_data_dir() / "trace_ledger.jsonl"
    assert legacy_path != reader_path, "pre-fix algorithm must disagree with reader under SCP_DATA_DIR"
    assert AskKernelAdapter._unified_ledger_path() == reader_path
