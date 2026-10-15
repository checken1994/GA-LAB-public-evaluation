"""Regression: trace GET over an oversized legacy ledger must stay bounded.

Audit 2026-09-29 (Agent4 - Data Steward, SCP round 3): production
``data/request_runs.jsonl`` reached ~110 MB (append-only, no size bound).
The legacy fallback in ``scp.api_server_parts._trace_impl`` called
``TraceLedger.get_trace()``, which reads the WHOLE file on every admin GET -
an O(file) cost that grows without limit (self-inflicted DoS / latency spike).

Fix: ``_load_ledger_record`` keeps the exact previous behavior for files
<= ``_LEDGER_SCAN_LIMIT_BYTES`` and switches to a bounded most-recent-first
scan (``_scan_recent_match``) for oversized files. Matching semantics mirror
``TraceLedger.get_trace`` (entry ``trace_id``, ``fields.task_id``,
``fields.trace_id``).

Old-code-fail / new-code-pass is proven by counting actual bytes read from
the ledger across BOTH read paths (Path.read_text for the legacy scan,
io.BufferedReader.read for the bounded window): the legacy path reads more
than the limit; the fixed path never does; both return the same entry for
a recent trace. (F7: the earlier counter instrumented only read_text, so
the bounded assertion passed vacuously.)

Note: a concurrent reviewer refactored ``_load_ledger_record`` to take the
ledger class explicitly (``ledger_cls``) instead of a local lazy import;
the route still lazy-imports ``TraceLedger``. Tests pass it explicitly.
"""
from __future__ import annotations

import io
import json
import pathlib
from pathlib import Path

from scp.api_server_parts import _trace_impl
from scp.api_server_parts._trace_impl import (
    _LEDGER_SCAN_LIMIT_BYTES,
    _load_ledger_record,
    _scan_recent_match,
)
from scp.trace_ledger import TraceLedger, _hash

LEDGER_NAME = "request_runs.jsonl"  # same identity as the production file


def _write_synthetic_ledger(path: Path, *, fill_entries: int, payload_pad: int) -> dict:
    """Write a canonical-format hash-chained ledger without 200k fsyncs."""
    seq = 0
    prev = None
    target = None
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for i in range(fill_entries):
            seq += 1
            entry = {
                "trace_id": f"trace-fill-{i}",
                "seq": seq,
                "prev_hash": prev,
                "fields": {"note": i, "payload": "x" * payload_pad},
            }
            entry["hash"] = _hash(entry)
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
            prev = entry["hash"]
        # The most-recent match: two fill entries follow the target so the
        # scan must walk backwards over non-matching recent lines.
        for j in range(2):
            seq += 1
            if j == 0:
                target = {
                    "trace_id": "trace-agent4-oversize-target",
                    "seq": seq,
                    "prev_hash": prev,
                    "fields": {"task_id": "trace-agent4-oversize-target", "payload": "t" * payload_pad},
                }
                entry = target
            else:
                entry = {
                    "trace_id": f"trace-tail-{j}",
                    "seq": seq,
                    "prev_hash": prev,
                    "fields": {"note": f"tail-{j}", "payload": "z" * payload_pad},
                }
            entry["hash"] = _hash(entry)
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
            prev = entry["hash"]
    assert target is not None
    return target


class _LedgerBytesCounter:
    """Count bytes actually read from the ledger file across BOTH read paths.

    [F7 fix] The previous counter only instrumented ``Path.read_text``, but
    the bounded fallback reads via a binary handle — its assertion passed
    vacuously (Agent5 MEDIUM). This counter patches BOTH ``Path.read_text``
    (the legacy ``TraceLedger.get_trace`` read) and ``io.BufferedReader.read``
    (the bounded window's ``handle.read(window)``), attributing every byte
    actually returned from the ledger file, so the boundedness claim is
    measured, not assumed.
    """

    def __init__(self, ledger_path: Path) -> None:
        self.ledger_path = ledger_path.resolve()
        self.bytes_read = 0
        self._original_read_text = pathlib.Path.read_text
        self._original_open = io.open

    def __enter__(self) -> _LedgerBytesCounter:
        counter = self
        original_read_text = self._original_read_text
        original_open = io.open

        def counting_read_text(self_path, *args, **kwargs):
            data = original_read_text(self_path, *args, **kwargs)
            try:
                if Path(self_path).resolve() == counter.ledger_path:
                    counter.bytes_read += len(data.encode("utf-8", errors="replace"))
            except (TypeError, ValueError, OSError):
                pass
            return data

        class _CountingReader:
            """Thin proxy recording bytes returned by the wrapped reader."""

            def __init__(self, handle: io.BufferedReader) -> None:
                self._handle = handle

            def __getattr__(self, name):
                return getattr(self._handle, name)

            def read(self, size=-1, /, *args, **kwargs):
                data = self._handle.read(size, *args, **kwargs)
                if data:
                    counter.bytes_read += len(data)
                return data

            def __enter__(self, *a, **k):
                self._handle.__enter__(*a, **k)
                return self

            def __exit__(self, *a, **k):
                return self._handle.__exit__(*a, **k)

        def counting_open(file, mode="r", *args, **kwargs):
            handle = original_open(file, mode, *args, **kwargs)
            if "b" in mode:
                try:
                    if Path(file).resolve() == counter.ledger_path:
                        return _CountingReader(handle)
                except (TypeError, ValueError, OSError):
                    pass
            return handle

        pathlib.Path.read_text = counting_read_text  # type: ignore[method-assign]
        io.open = counting_open  # type: ignore[method-assign]
        return self

    def __exit__(self, *exc) -> None:
        pathlib.Path.read_text = self._original_read_text  # type: ignore[method-assign]
        io.open = self._original_open  # type: ignore[method-assign]


def test_oversized_ledger_get_is_bounded_and_finds_recent_trace(tmp_path, monkeypatch):
    monkeypatch.setattr(_trace_impl, "_LEDGER_SCAN_LIMIT_BYTES", 4 * 1024 * 1024)
    ledger_path = tmp_path / LEDGER_NAME
    target = _write_synthetic_ledger(ledger_path, fill_entries=20_000, payload_pad=300)
    assert ledger_path.stat().st_size > 4 * 1024 * 1024, "test setup must exceed the scan limit"

    # OLD behavior: full-file read - strictly more bytes than the limit.
    with _LedgerBytesCounter(ledger_path) as old_counter:
        old_record = TraceLedger(ledger_path, verify_on_init=False).get_trace(
            "trace-agent4-oversize-target"
        )
    assert old_record is not None and old_record["hash"] == target["hash"]
    assert old_counter.bytes_read > 4 * 1024 * 1024, (
        "old behavior must be O(file): it read the whole oversized ledger"
    )

    # NEW behavior: bounded window - never more than the limit.
    with _LedgerBytesCounter(ledger_path) as new_counter:
        new_record = _load_ledger_record(ledger_path, "trace-agent4-oversize-target", TraceLedger)
    assert new_record is not None
    assert new_record["hash"] == target["hash"]
    assert new_record["seq"] == target["seq"]
    assert new_counter.bytes_read <= 4 * 1024 * 1024, (
        "fixed behavior must never read more than the bounded window"
    )

    # Miss on an oversized ledger stays a miss (404-equivalent), still bounded.
    with _LedgerBytesCounter(ledger_path) as miss_counter:
        assert _load_ledger_record(ledger_path, "trace-not-present", TraceLedger) is None
    assert miss_counter.bytes_read <= 4 * 1024 * 1024


def test_small_ledger_get_keeps_legacy_semantics(tmp_path):
    """Files under the limit must behave exactly like TraceLedger.get_trace."""
    ledger_path = tmp_path / LEDGER_NAME
    TraceLedger(ledger_path, verify_on_init=False).append(trace_id="trace-agent4-small-1", fields_note=1)
    TraceLedger(ledger_path, verify_on_init=False).append(trace_id="trace-agent4-small-2", fields_note=2)
    reference = TraceLedger(ledger_path, verify_on_init=False)

    for trace_id in ("trace-agent4-small-1", "trace-agent4-small-2"):
        assert _load_ledger_record(ledger_path, trace_id, TraceLedger) == reference.get_trace(trace_id)
    assert _load_ledger_record(ledger_path, "trace-agent4-missing", TraceLedger) is None
    assert reference.get_trace("trace-agent4-missing") is None


def test_dosed_scan_skips_torn_first_line_without_raising(tmp_path, monkeypatch):
    """A line torn by the window cut must be skipped, not raised (read path)."""
    monkeypatch.setattr(_trace_impl, "_LEDGER_SCAN_LIMIT_BYTES", 4 * 1024 * 1024)
    ledger_path = tmp_path / LEDGER_NAME
    target = _write_synthetic_ledger(ledger_path, fill_entries=20_000, payload_pad=300)

    # Simulate the window cut: drop a partial prefix of the first line.
    raw = ledger_path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    lines[0] = lines[0][len(lines[0]) // 2:]  # torn JSON
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    record = _scan_recent_match(ledger_path, "trace-agent4-oversize-target")
    assert record is not None
    assert record["hash"] == target["hash"]


def test_production_default_limit_is_bounded():
    """The shipped default must be a positive, bounded scan window."""
    assert 0 < _LEDGER_SCAN_LIMIT_BYTES <= 64 * 1024 * 1024
    assert _LEDGER_SCAN_LIMIT_BYTES == 32 * 1024 * 1024