"""[ZONE-FIX 2026-09-26] Regression — PermissionGate.check_permission must not
re-read the whole append-only JSONL on every poll.

BEFORE the fix every check_permission() call re-parsed the entire
permission_requests.jsonl (O(n) per call, O(n^2) across a session — probe
measured 20.19 ms/poll on a 5k-record file). AFTER: an in-memory index plus
incremental tail scan — an UNCHANGED file is answered with a stat-only cache
hit (zero file opens), appended records are picked up (tail scan), human
in-place edits / rewrites are picked up (full index rescan), and
"last record wins" + append-only audit semantics are preserved.
"""
from __future__ import annotations

import json
import os
import sys

from scp.autofix.classifier import BugReport, BugTier
from scp.autofix.permission import PermissionGate


def _seed(gate: PermissionGate, count: int) -> str:
    target_id = ""
    for i in range(count):
        bug = BugReport(
            file=f"src/mod_{i}.py",
            line=i,
            bug_type="logic",
            description=f"bug {i}",
            suggested_fix=f"fix {i}",
            tier=BugTier.TIER_3_PERMISSION,
        )
        rid = gate.request_permission(bug)
        if i == count - 1:
            target_id = rid
    assert target_id
    return target_id


def test_unchanged_file_polls_do_not_reopen_the_file(tmp_path):
    gate = PermissionGate(data_dir=str(tmp_path))
    target_id = _seed(gate, 300)
    assert gate.check_permission(target_id) == "pending"

    requests_file = str(gate.requests_file)
    open_events: list[str] = []

    def _hook(event, args):
        if event == "open":
            path = str(args[0]) if args else ""
            if path == requests_file:
                open_events.append(path)

    sys.addaudithook(_hook)
    for _ in range(50):
        assert gate.check_permission(target_id) == "pending"
    assert not open_events, (
        f"check_permission re-read the whole requests file on every poll "
        f"({len(open_events)} opens in 50 polls of an unchanged file)"
    )


def test_appended_human_approval_is_picked_up(tmp_path):
    gate = PermissionGate(data_dir=str(tmp_path))
    target_id = _seed(gate, 20)
    assert gate.check_permission(target_id) == "pending"

    req = gate._pending[target_id]
    record = json.loads(json.dumps({
        "request_id": target_id,
        "timestamp": req.timestamp,
        "file": req.file,
        "line": req.line,
        "bug_type": req.bug_type,
        "description": req.description,
        "suggested_fix": req.suggested_fix,
        "status": "approved",
        "human_note": "manual edit approval",
        "decided_at": 123.0,
        "decided_by": "human",
    }))
    with gate.requests_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    assert gate.check_permission(target_id) == "approved"


def test_in_place_edit_and_rewrite_are_picked_up(tmp_path):
    gate = PermissionGate(data_dir=str(tmp_path))
    target_id = _seed(gate, 5)
    assert gate.check_permission(target_id) == "pending"

    # Same-size in-place edit of the TARGET's line (human edits a past line
    # without resizing).
    lines = gate.requests_file.read_text(encoding="utf-8").splitlines()
    line_index = next(
        i for i, line in enumerate(lines)
        if json.loads(line).get("request_id") == target_id
    )
    original = lines[line_index]
    record = json.loads(original)
    original_size = len(original.encode("utf-8"))
    record["status"] = "denied"
    record["decided_by"] = "human"
    fitted = None
    for candidate_len in range(200):
        record["description"] = "x" * candidate_len
        candidate = json.dumps(record, ensure_ascii=False)
        if len(candidate.encode("utf-8")) == original_size:
            fitted = candidate
            break
    assert fitted is not None, "test could not build a same-size edited line"
    lines[line_index] = fitted
    # [RUNNER-DETERMINISTIC 2026-10-01] Capture the pre-edit signature so the
    # post-edit mtime can be forced deterministically. os.utime(path, None)
    # asks for "now", but file timestamps come from the kernel coarse clock
    # (Linux current_time() ticks per jiffy ~1-4 ms; Windows system-time tick
    # ~0.5-15.6 ms — probe: 200 rapid utime() calls on one file produced only
    # 69 distinct mtime_ns values, 5 consecutive calls sharing one value). On
    # a fast, idle CI runner the whole seed->edit sequence fits inside a
    # single tick, so a "now" bump can leave (st_mtime_ns, st_size) unchanged
    # and the documented stat-only fast path legitimately reports "unchanged".
    # Real human edits happen seconds after the gate's last write, so the
    # signature always moves in production; the test must establish that
    # documented precondition explicitly. +2 s guarantees a different stored
    # mtime on any filesystem with timestamp granularity <= 2 s (ext4 ns,
    # NTFS 100 ns, FAT 2 s). Detection strictness is unchanged: the same-size
    # in-place edit is real and must still be picked up via the full-rescan
    # correctness path on the very next poll.
    pre_edit_st = gate.requests_file.stat()
    gate.requests_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.utime(
        gate.requests_file,
        ns=(pre_edit_st.st_atime_ns, pre_edit_st.st_mtime_ns + 2_000_000_000),
    )
    assert gate.check_permission(target_id) == "denied", (
        "same-size in-place edit of a past line was not detected"
    )

    # Full rewrite (truncate + write) with a new status.
    record = json.loads(gate.requests_file.read_text(encoding="utf-8").splitlines()[0])
    record["request_id"] = target_id
    record["status"] = "approved"
    gate.requests_file.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    assert gate.check_permission(target_id) == "approved", (
        "rewritten file status was not picked up"
    )


def test_unknown_request_id_still_unknown(tmp_path):
    gate = PermissionGate(data_dir=str(tmp_path))
    _seed(gate, 3)
    assert gate.check_permission("nonexistent-id") == "unknown"


def test_append_landing_in_load_window_is_picked_up(tmp_path):
    """[SIG-ORDER 2026-09-30] _load_pending phải stat() TRƯỚC _scan_file():
    sig (mtime_ns, size) phải mô tả ĐÚNG phần bytes mà lần scan phủ. Trước fix
    stat() nằm SAU scan — một append rơi vào cửa sổ giữa scan và stat làm sig
    phủ cả những bytes CHƯA scan → mọi refresh sau thấy sig "unchanged" và bỏ
    qua tail MÃI MÃI (approval của human không bao giờ được nhìn thấy)."""
    gate = PermissionGate(data_dir=str(tmp_path))
    target_id = _seed(gate, 3)
    assert gate.check_permission(target_id) == "pending"

    # Mô phỏng DETERMINISTIC đúng cửa sổ race: reset trạng thái scan rồi gọi
    # lại _load_pending với _scan_file bị bọc sao cho bản ghi approved được
    # append NGAY SAU khi scan kết thúc nhưng TRƯỚC khi stat() chạy.
    req = gate._pending[target_id]
    approved = {
        "request_id": target_id,
        "timestamp": req.timestamp,
        "file": req.file,
        "line": req.line,
        "bug_type": req.bug_type,
        "description": req.description,
        "suggested_fix": req.suggested_fix,
        "status": "approved",
        "human_note": "approval landed inside the load window",
        "decided_at": 123.0,
        "decided_by": "human",
    }
    gate._pending.clear()
    gate._index.clear()
    gate._scan_pos = 0
    gate._file_sig = None
    real_scan = gate._scan_file

    def scan_then_append(start_offset: int, update_pending: bool = False) -> None:
        real_scan(start_offset, update_pending=update_pending)
        with gate.requests_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(approved, ensure_ascii=False) + "\n")

    gate._scan_file = scan_then_append  # type: ignore[method-assign]
    gate._load_pending()
    gate._scan_file = real_scan  # type: ignore[method-assign]

    # Refresh kế tiếp PHẢI thấy bản ghi append trong cửa sổ. Old code: sig đã
    # phủ cả bytes chưa scan → stat-only hit → "pending" mãi mãi.
    assert gate.check_permission(target_id) == "approved", (
        "append rơi vào cửa sổ scan→stat của _load_pending bị bỏ qua vĩnh viễn "
        "(_file_sig mô tả vượt phạm vi phần đã scan)"
    )
