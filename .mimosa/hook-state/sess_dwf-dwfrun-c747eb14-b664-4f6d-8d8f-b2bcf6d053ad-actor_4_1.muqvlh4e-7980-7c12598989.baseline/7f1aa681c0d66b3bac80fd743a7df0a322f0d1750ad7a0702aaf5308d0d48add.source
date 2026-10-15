"""[BROKEN-2] Regression: TraceLedger cross-process append + CHAIN_RECOVERY re-anchor.

2026-09-23 real-world corruption: two processes appended data/trace_ledger.jsonl
concurrently (no OS-level lock) -> seq forked 404->405->404 with divergent
prev_hash, 808+ entries misaligned, and nothing alerted.

Contracts pinned here (all on TEMP ledger files — the real data/ ledger is
operator evidence and is never touched by tests):
1. Two THREADS in one process appending concurrently -> chain stays valid.
2. Two PROCESSES appending concurrently -> chain stays valid (OS-level lock).
3. Hand-crafted fork file -> init logs the [TRACE-LEDGER-BLOCKER] error and
   appends exactly one CHAIN_RECOVERY anchor; the corrupted history is
   preserved byte-for-byte; subsequent appends verify as a new segment.
4. Clean ledgers and legacy verify() semantics are unchanged.
5. Append fails CLOSED when no OS locking primitive exists.
"""
from __future__ import annotations

import builtins
import json
import logging
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from scp.trace_ledger import TraceLedger, _hash

_LEDGER_SRC = Path(__file__).resolve().parents[2] / "scp" / "trace_ledger.py"


def _make_entry(seq: int, prev_hash: str | None, fields: dict, trace_id: str = "trace_x") -> dict:
    entry = {"trace_id": trace_id, "seq": seq, "prev_hash": prev_hash, "fields": fields}
    entry["hash"] = _hash(entry)
    return entry


def _seqs(path: Path) -> list[int]:
    return [json.loads(line)["seq"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# 1. In-process thread concurrency (in-process lock keeps the chain valid)
# ---------------------------------------------------------------------------


def test_threads_same_process_concurrent_appends_chain_valid(tmp_path: Path):
    ledger = TraceLedger(tmp_path / "threads.jsonl")

    def worker(wid: int) -> None:
        for i in range(25):
            ledger.append(worker=wid, i=i)

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    result = ledger.verify()
    assert result["entries"] == 200
    assert result["hash_chain_valid"] is True
    assert result["errors"] == []
    assert _seqs(tmp_path / "threads.jsonl") == list(range(1, 201))


# ---------------------------------------------------------------------------
# 2. Cross-process concurrency (OS-level lock keeps the chain valid)
# ---------------------------------------------------------------------------

_CHILD_SCRIPT = r"""
import importlib.util, sys, time
spec = importlib.util.spec_from_file_location("trace_ledger_child", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ledger = mod.TraceLedger(sys.argv[2])
for i in range(15):
    ledger.append(src="child", i=i)
    time.sleep(0.004)
"""


def test_two_processes_concurrent_appends_chain_valid(tmp_path: Path):
    """The 2026-09-23 fork root cause, replayed: two real processes append the
    same ledger concurrently. With the OS-level lock the chain must stay valid."""
    ledger_file = tmp_path / "xproc.jsonl"
    ledger = TraceLedger(ledger_file)
    ledger.append(src="parent", boot=True)  # file exists before the child boots

    proc = subprocess.Popen(
        [sys.executable, "-c", _CHILD_SCRIPT, str(_LEDGER_SRC), str(ledger_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path),
    )
    try:
        for i in range(30):
            ledger.append(src="parent", i=i)
            time.sleep(0.006)
    finally:
        stderr = proc.stderr.read() if proc.stderr else b""
        returncode = proc.wait(timeout=120)
    assert returncode == 0, f"child failed: {stderr.decode(errors='replace')[-500:]}"

    result = TraceLedger(ledger_file, verify_on_init=False).verify()
    assert result["hash_chain_valid"] is True, result["errors"][:10]
    assert result["entries"] == 46  # 1 boot + 30 parent + 15 child
    assert sorted(_seqs(ledger_file)) == list(range(1, 47))
    assert (tmp_path / "xproc.jsonl.lock").exists()


# ---------------------------------------------------------------------------
# 3. Corruption recovery: CHAIN_RECOVERY re-anchor, history never rewritten
# ---------------------------------------------------------------------------


def _write_fork_file(path: Path) -> tuple[list[str], dict, dict, dict, dict]:
    """3 valid entries + a 2-entry rival fork (hand-crafted, like the real one)."""
    e1 = _make_entry(1, None, {"k": 1})
    e2 = _make_entry(2, e1["hash"], {"k": 2})
    e3 = _make_entry(3, e2["hash"], {"k": 3})
    r3 = _make_entry(3, e2["hash"], {"k": "rival"}, trace_id="trace_rival")  # fork: seq 3 again
    r4 = _make_entry(4, r3["hash"], {"k": "rival4"}, trace_id="trace_rival")
    lines = [json.dumps(e, sort_keys=True) for e in (e1, e2, e3, r3, r4)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines, e1, e2, e3, r4


def test_corrupted_fork_recovers_with_chain_recovery_anchor(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    ledger_file = tmp_path / "forked.jsonl"
    original_lines, _e1, _e2, _e3, _r4 = _write_fork_file(ledger_file)

    with caplog.at_level(logging.ERROR, logger="scp.trace_ledger"):
        ledger = TraceLedger(ledger_file)  # boot path -> fail-loud + re-anchor

    # (a) BLOCKER-level error names the file, the first broken line/seq, action
    assert "[TRACE-LEDGER-BLOCKER]" in caplog.text
    assert str(ledger_file) in caplog.text
    assert "line=4" in caplog.text and "seq=3" in caplog.text  # first broken line/seq
    assert "CHAIN_RECOVERY" in caplog.text

    # (b) exactly ONE anchor appended; the 5 corrupted-history lines are untouched
    lines_now = ledger_file.read_text(encoding="utf-8").splitlines()
    assert len(lines_now) == 6
    assert lines_now[:5] == original_lines, "history must be preserved byte-for-byte (tamper evidence)"
    marker = json.loads(lines_now[5])
    assert marker["type"] == "CHAIN_RECOVERY"
    assert marker["broken_at_seq"] == 3
    assert marker["prev_hash"] is None
    assert marker["seq"] == 5  # max_seq (4) + 1

    # (c) verify() validates the new segment; history reported separately
    report = TraceLedger(ledger_file, verify_on_init=False).verify()
    assert report["hash_chain_valid"] is True
    assert report["history_valid"] is False  # tamper evidence stays visible
    assert "seq:4" in report["history_errors"]
    assert report["anchor"] == {"line": 6, "seq": 5, "broken_at_seq": 3}

    # (d) subsequent appends chain from the anchor and verify
    ledger.append(post_recovery=True)
    final = TraceLedger(ledger_file, verify_on_init=False).verify()
    assert final["hash_chain_valid"] is True
    assert final["entries"] == 7


def test_recovery_marker_chains_seq_beyond_history_duplicates(tmp_path: Path):
    """Marker seq = max_seq+1 (not tail+1): seq numbering stays monotonic even
    when the corrupted segment contains higher seqs than the tail."""
    ledger_file = tmp_path / "tail_backwards.jsonl"
    # Fork shaped like the real file: seq goes forward then BACKWARDS at the tail.
    e1 = _make_entry(1, None, {"k": 1})
    e2 = _make_entry(2, e1["hash"], {"k": 2})
    e3 = _make_entry(3, e2["hash"], {"k": 3})
    e_back = _make_entry(2, e2["hash"], {"k": "rollback"}, trace_id="trace_back")  # tail seq 2 < max 3
    path_lines = [json.dumps(e, sort_keys=True) for e in (e1, e2, e3, e_back)]
    ledger_file.write_text("\n".join(path_lines) + "\n", encoding="utf-8")

    TraceLedger(ledger_file)  # boot recovery
    ledger = TraceLedger(ledger_file, verify_on_init=False)
    report = ledger.verify()
    assert report["hash_chain_valid"] is True
    assert report["anchor"]["seq"] == 4  # max_seq (3) + 1, NOT tail (2) + 1

    ledger.append(k="after")
    final = ledger.verify()
    assert final["hash_chain_valid"] is True
    assert _seqs(ledger_file)[-1] == 5


def test_clean_ledger_init_does_not_recover(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    ledger_file = tmp_path / "clean.jsonl"
    ledger = TraceLedger(ledger_file)
    for i in range(5):
        ledger.append(k=i)
    before = ledger_file.read_text(encoding="utf-8")

    with caplog.at_level(logging.ERROR, logger="scp.trace_ledger"):
        TraceLedger(ledger_file)  # another instance, same clean file

    assert "[TRACE-LEDGER-BLOCKER]" not in caplog.text
    assert ledger_file.read_text(encoding="utf-8") == before  # nothing appended
    report = TraceLedger(ledger_file, verify_on_init=False).verify()
    assert report["hash_chain_valid"] is True
    assert report["history_valid"] is True
    assert report["anchor"] is None


def test_boot_verify_runs_once_per_process_per_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []
    monkeypatch.setattr(TraceLedger, "verify_and_recover", lambda self: calls.append(str(self.path)))
    p1 = tmp_path / "once.jsonl"
    TraceLedger(p1)
    TraceLedger(p1)
    TraceLedger(p1)
    assert calls == [str(p1)]  # O(file) boot check is once per path, not per instance
    TraceLedger(tmp_path / "other.jsonl")
    assert len(calls) == 2


def test_verify_on_init_false_is_read_only(tmp_path: Path):
    """Read-only callers must never trigger the boot recovery write."""
    p = tmp_path / "readonly.jsonl"
    p.write_text("garbage not json\n", encoding="utf-8")  # invalid -> would re-anchor if verified
    ledger = TraceLedger(p, verify_on_init=False)
    assert not Path(str(p) + ".lock").exists()  # boot check (the only lock user at init) never ran
    assert ledger.verify()["hash_chain_valid"] is False  # visible, not hidden


# ---------------------------------------------------------------------------
# 4. verify() robustness: parse errors are reported, never raised
# ---------------------------------------------------------------------------


def test_verify_reports_parse_error_instead_of_raising(tmp_path: Path):
    p = tmp_path / "torn.jsonl"
    e1 = _make_entry(1, None, {"k": 1})
    p.write_text(json.dumps(e1, sort_keys=True) + "\n" + "not-json{{{\n", encoding="utf-8")
    ledger = TraceLedger(p, verify_on_init=False)
    report = ledger.verify()
    assert report["hash_chain_valid"] is False
    assert "parse:2" in report["errors"]
    assert report["first_broken_line"] == 2


def test_recovery_after_torn_tail_starts_new_segment(tmp_path: Path):
    p = tmp_path / "torn_recover.jsonl"
    e1 = _make_entry(1, None, {"k": 1})
    p.write_text(json.dumps(e1, sort_keys=True) + "\n" + "not-json{{{\n", encoding="utf-8")

    TraceLedger(p)  # boot recovery: torn line stays, anchor appended
    ledger = TraceLedger(p, verify_on_init=False)
    report = ledger.verify()
    assert report["hash_chain_valid"] is True
    assert "parse:2" in report["history_errors"]
    assert report["anchor"]["line"] == 3

    ledger.append(k="after")  # chains from the anchor, not from the torn line
    final = ledger.verify()
    assert final["hash_chain_valid"] is True
    assert final["entries"] == 4


def test_append_after_crash_torn_last_line_without_newline(tmp_path: Path):
    """A crash mid-write can leave the last line without a trailing newline.
    The next append must start a FRESH line, not concatenate onto the torn one."""
    p = tmp_path / "no_trailing_newline.jsonl"
    e1 = _make_entry(1, None, {"k": 1})
    p.write_text(json.dumps(e1, sort_keys=True), encoding="utf-8")  # no trailing "\n"

    ledger = TraceLedger(p, verify_on_init=False)
    ledger.append(k="fresh-line")
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2  # torn line intact, new entry on its own line
    assert json.loads(lines[0])["seq"] == 1
    report = ledger.verify()
    assert report["hash_chain_valid"] is True
    assert report["entries"] == 2


# ---------------------------------------------------------------------------
# 5. Fail-closed when no OS locking primitive exists
# ---------------------------------------------------------------------------


def test_append_fails_closed_without_locking_primitive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ledger = TraceLedger(tmp_path / "nolock.jsonl")  # init: boot verify on empty file, fine
    monkeypatch.setitem(sys.modules, "msvcrt", None)
    monkeypatch.setitem(sys.modules, "fcntl", None)
    with pytest.raises(RuntimeError, match="fail-closed"):
        ledger.append(x=1)
    # fail-closed: NO partial entry was written
    assert ledger.verify()["entries"] == 0


# ---------------------------------------------------------------------------
# 6. Boot on an unwritable/invalid ledger location: skip + flag, never crash
#    (2026-09-26 Windows regression: TraceLedger("/tmp") resolves to "\tmp"
#    at the drive root; the init-time verify_and_recover raised
#    PermissionError [Errno 13] and crashed AskKernelAdapter boot.
#    Contract: OSError on the ledger location at construction time must be
#    surfaced as a WARNING + boot_skipped flag; construction CONTINUES and
#    appends fail-closed at use time. Writable paths still verify-and-recover
#    exactly as before — no gate is weakened.)
# ---------------------------------------------------------------------------


def _deny_mkdir(self: Path, parents: bool = False, exist_ok: bool = False) -> None:
    raise PermissionError(13, "Permission denied", str(self))


def test_unwritable_path_mkdir_denied_constructs_and_flags_boot_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    ledger_file = tmp_path / "unwritable" / "ledger.jsonl"
    monkeypatch.setattr(Path, "mkdir", _deny_mkdir)
    with caplog.at_level(logging.WARNING, logger="scp.trace_ledger"):
        ledger = TraceLedger(ledger_file)  # must NOT raise
    assert ledger.boot_skipped is True
    assert ledger.boot_verified is False
    assert "ledger boot verification skipped" in caplog.text
    assert str(ledger_file) in caplog.text  # the WARNING names the path
    assert "fail-closed" in caplog.text  # ...and the effect
    # fail-closed at use time: appends raise while the path stays unwritable
    with pytest.raises(OSError):
        ledger.append(k=1)


def test_boot_verify_oserror_skipped_not_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """mkdir succeeds but the ledger location is still unusable: OSError raised
    inside verify_and_recover (here: the cross-process lock file cannot be
    created) must not crash construction."""
    ledger_file = tmp_path / "locked_out.jsonl"
    real_open = builtins.open

    def _deny_lock_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if str(file) == str(ledger_file) + ".lock":
            raise PermissionError(13, "Permission denied", str(file))
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _deny_lock_open)
    with caplog.at_level(logging.WARNING, logger="scp.trace_ledger"):
        ledger = TraceLedger(ledger_file)  # must NOT raise
    assert ledger.boot_skipped is True
    assert ledger.boot_verified is False
    assert "ledger boot verification skipped" in caplog.text
    with pytest.raises(OSError):
        ledger.append(k=1)  # fail-closed at use time


def test_ledger_path_pointing_at_existing_directory_skips_boot(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    """The exact regression shape, replayed without any mock: the ledger path
    points at an EXISTING directory ('\tmp' on Windows). verify()'s read_text
    raises PermissionError (Windows) / IsADirectoryError (POSIX) at boot."""
    with caplog.at_level(logging.WARNING, logger="scp.trace_ledger"):
        ledger = TraceLedger(tmp_path)  # a directory, not a ledger file
    assert ledger.boot_skipped is True
    assert ledger.boot_verified is False
    assert "ledger boot verification skipped" in caplog.text
    with pytest.raises(OSError):
        ledger.append(k=1)  # fail-closed at use time


def test_boot_skip_outcome_is_shared_per_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Later instances on the same skipped path carry the outcome instead of
    re-running the O(file) boot check (once per process per path, both ways)."""
    ledger_file = tmp_path / "again" / "ledger.jsonl"
    monkeypatch.setattr(Path, "mkdir", _deny_mkdir)
    first = TraceLedger(ledger_file)
    second = TraceLedger(ledger_file)
    assert first.boot_skipped is True and first.boot_verified is False
    assert second.boot_skipped is True and second.boot_verified is False


def test_writable_path_boot_still_verifies_and_sets_flags(tmp_path: Path):
    """The healthy path is unchanged: a writable ledger still runs the boot
    verify-and-recover and records boot_verified=True (no gate weakened)."""
    ledger = TraceLedger(tmp_path / "healthy.jsonl")
    ledger.append(k=1)
    assert ledger.boot_verified is True
    assert ledger.boot_skipped is False
    report = TraceLedger(tmp_path / "healthy.jsonl").verify()
    assert report["hash_chain_valid"] is True
    assert report["entries"] == 1


# ---------------------------------------------------------------------------
# 7. Non-UTF-8 byte in the ledger file (2026-09-30 corrupt-byte regression):
#    verify() used read_text(encoding="utf-8") — ONE bad byte raised
#    UnicodeDecodeError (ValueError, NOT OSError) which escaped the boot
#    catch and crashed TraceLedger(path) AT CONSTRUCTION, violating the
#    documented contract "construction must not crash; fail-closed at use".
#    Contract now: a corrupt byte decodes to U+FFFD → that line is a parse
#    error → the existing CHAIN_RECOVERY re-anchor path handles it; a ValueError
#    from the boot verify is still never fatal to construction.
# ---------------------------------------------------------------------------


def test_non_utf8_byte_does_not_crash_construction_and_reanchors(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    p = tmp_path / "badbyte.jsonl"
    e1 = _make_entry(1, None, {"k": 1})
    good = json.dumps(e1, sort_keys=True).encode("utf-8")
    p.write_bytes(good + b"\n" + b"\xff\xfe binary garbage \x00\n")  # 1 bad byte

    with caplog.at_level(logging.ERROR, logger="scp.trace_ledger"):
        ledger = TraceLedger(p)  # must NOT raise (old: UnicodeDecodeError)

    assert ledger.boot_verified is True, "re-anchor path phải chạy thay vì crash"
    assert ledger.boot_skipped is False
    assert "[TRACE-LEDGER-BLOCKER]" in caplog.text  # corrupt byte fail-loud

    report = TraceLedger(p, verify_on_init=False).verify()
    assert report["hash_chain_valid"] is True  # active segment sau re-anchor
    assert report["history_valid"] is False  # corrupt line = tamper evidence
    assert any(e.startswith("parse:") for e in report["history_errors"])

    ledger.append(k="after")  # appends chain from the new anchor
    final = TraceLedger(p, verify_on_init=False).verify()
    assert final["hash_chain_valid"] is True
    assert final["entries"] == 4  # e1 + corrupt line (preserved) + anchor + append


def test_get_trace_survives_non_utf8_byte(tmp_path: Path):
    """Same corrupt-byte defect class on the read API: get_trace must skip the
    unparsable line instead of raising UnicodeDecodeError."""
    p = tmp_path / "badbyte_get.jsonl"
    e1 = _make_entry(1, None, {"task_id": "t1"})
    p.write_bytes(json.dumps(e1, sort_keys=True).encode("utf-8") + b"\n" + b"\xff\xfe\n")

    ledger = TraceLedger(p, verify_on_init=False)
    found = ledger.get_trace("t1")  # old: UnicodeDecodeError (ValueError)
    assert found is not None
    assert found["seq"] == 1


def test_boot_verify_valueerror_is_skipped_not_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """Defense in depth: một ValueError (UnicodeDecodeError ⊂ ValueError) bất
    kỳ từ boot verify không được phép crash construction — surface dạng
    boot_skipped WARNING (fail-closed visibility), construction tiếp tục."""
    ledger_file = tmp_path / "verror.jsonl"

    def _boom(self: TraceLedger) -> dict[str, Any]:
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr(TraceLedger, "verify_and_recover", _boom)
    with caplog.at_level(logging.WARNING, logger="scp.trace_ledger"):
        ledger = TraceLedger(ledger_file)  # must NOT raise
    assert ledger.boot_skipped is True
    assert ledger.boot_verified is False
    assert "ledger boot verification skipped" in caplog.text
