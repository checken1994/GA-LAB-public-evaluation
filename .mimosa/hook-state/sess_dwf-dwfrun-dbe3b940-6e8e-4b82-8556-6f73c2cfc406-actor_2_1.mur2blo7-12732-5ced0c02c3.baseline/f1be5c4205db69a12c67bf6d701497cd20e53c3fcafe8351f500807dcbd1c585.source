"""[Agent4-DataSteward F1 regression 2026-09-29] The unified trace-ledger
WRITER (ask_kernel_adapter._unified_ledger_path) and the /v3/trace READER
(api_server_parts._trace_impl) must resolve the SAME ledger file under
SCP_DATA_DIR.

Old-code behavior (pre-fix): the writer used CWD-relative Path("data") with a
repo-root fallback and ignored SCP_DATA_DIR, while the reader used
runtime_data_dir() (SCP_DATA_DIR-aware). With SCP_DATA_DIR set to a foreign
directory (or CWD != repo root), the writer and reader split-brained: an ask
appended to <repo>/data/trace_ledger.jsonl while GET /v3/trace/<id> resolved
<SCP_DATA_DIR>/trace_ledger.jsonl -> 404 for a freshly written entry
(missing traceability, not missing user data).

Old code FAILS the writer-side assertion below (parent != SCP_DATA_DIR);
new code PASSES both. Reader behavior @ _trace_impl.py:38 already pinned by
tests/T02_contract/test_trace_runtime_paths.py.
"""
from __future__ import annotations

import pytest


@pytest.mark.parametrize("use_explicit_data_dir", [False, True])
def test_unified_ledger_writer_matches_trace_reader_data_dir(monkeypatch, tmp_path, use_explicit_data_dir):
    from scp.ask_kernel_adapter import AskKernelAdapter
    from scp.core.runtime_paths import runtime_data_dir

    if use_explicit_data_dir:
        monkeypatch.setenv("SCP_DATA_DIR", str(tmp_path / "runtime-state"))
        expected = tmp_path / "runtime-state"
    else:
        monkeypatch.delenv("SCP_DATA_DIR", raising=False)
        expected = runtime_data_dir()

    writer = AskKernelAdapter._unified_ledger_path()

    assert writer == expected / "trace_ledger.jsonl"
    assert writer.parent == expected
    # The reader-side path for the same ledger must agree byte-for-byte.
    reader = runtime_data_dir() / "trace_ledger.jsonl"
    assert writer == reader
