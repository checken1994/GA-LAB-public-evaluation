from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SECRET_WORDS = ("secret", "token", "password", "cookie", "api_key", "authorization", "private_key")

_CHAIN_RECOVERY_TYPE = "CHAIN_RECOVERY"


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: "[REDACTED]" if any(w in str(k).lower() for w in _SECRET_WORDS) else _redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, str) and any(w in value.lower() for w in _SECRET_WORDS):
        return "[REDACTED_STRING]"
    return value


def _hash(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class _CrossProcessFileLock:
    """OS-level exclusive advisory lock on a dedicated lock file.

    Windows: ``msvcrt.locking(LK_LOCK)`` on one byte of ``<ledger>.lock``.
    POSIX: ``fcntl.flock(LOCK_EX)``.
    Fail-closed: if neither primitive is importable on the platform, acquiring
    raises RuntimeError instead of silently continuing unsynchronized.

    NOT reentrant at the OS level (a second acquire of the same byte from the
    same process fails on Windows): callers must hold the per-path in-process
    lock (see ``_LedgerState``) first and must not nest acquisitions.
    """

    def __init__(self, lock_path: str | Path) -> None:
        self._lock_path = Path(lock_path)
        self._fh: Any = None
        self._locked = False
        self._msvcrt: Any = None
        self._fcntl: Any = None

    def __enter__(self) -> _CrossProcessFileLock:
        # "a+b" creates the lock file if missing and never truncates it.
        self._fh = open(self._lock_path, "a+b")
        try:
            try:
                import msvcrt  # type: ignore[import-not-found]  (Windows)
                self._msvcrt = msvcrt
            except ImportError:
                self._msvcrt = None
            if self._msvcrt is None:
                try:
                    import fcntl  # type: ignore[import-not-found]  (POSIX)
                    self._fcntl = fcntl
                except ImportError:
                    self._fcntl = None
            if self._msvcrt is not None:
                # Non-blocking lock + fine-grained retry loop: bounded wait
                # (10s) then raise — contention beyond that fails closed,
                # loudly, instead of hanging the append path.
                deadline = time.monotonic() + 10.0
                while True:
                    try:
                        self._msvcrt.locking(self._fh.fileno(), self._msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(0.005)
            elif self._fcntl is not None:
                self._fcntl.flock(self._fh.fileno(), self._fcntl.LOCK_EX)
            else:
                raise RuntimeError(
                    "TraceLedger cross-process locking unavailable: neither msvcrt "
                    f"nor fcntl is importable on this platform ({sys.platform}); "
                    "refusing unsynchronized ledger writes (fail-closed)"
                )
            self._locked = True
            return self
        except BaseException:
            self._fh.close()
            self._fh = None
            raise

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            if self._locked and self._msvcrt is not None:
                try:
                    self._msvcrt.locking(self._fh.fileno(), self._msvcrt.LK_UNLCK, 1)
                except OSError as exc:
                    # Visibility over silence (T00 silent_except_pass): closing
                    # the handle releases the OS lock anyway, but the anomaly
                    # must not vanish silently.
                    logger.debug("TraceLedger lock unlock failed on %s: %s", self._lock_path, exc)
            elif self._locked and self._fcntl is not None:
                try:
                    self._fcntl.flock(self._fh.fileno(), self._fcntl.LOCK_UN)
                except OSError as exc:
                    logger.debug("TraceLedger flock unlock failed on %s: %s", self._lock_path, exc)
        finally:
            self._locked = False
            if self._fh is not None:
                self._fh.close()
                self._fh = None


def _validate_segment(parsed: list[Any], lo: int, hi: int, *, anchored: bool) -> dict[str, Any]:
    """Validate ledger lines ``lo..hi`` (1-based, inclusive).

    anchored=False -> legacy global rule: each entry's seq must equal its
    1-based line index and line ``lo`` must have ``prev_hash`` None.
    anchored=True  -> the segment starts at a CHAIN_RECOVERY anchor whose
    ``prev_hash`` must be None; following entries must increment seq by 1
    from the anchor's seq (line index no longer equals seq after a re-anchor).

    Unparsable/non-dict lines are reported as ``parse:<line>`` errors instead
    of raising, so corruption is always visible in the report (fail-loud).
    """
    errors: list[str] = []
    prev: Any = None
    expected_seq: int | None = None
    first_broken_line: int | None = None
    first_broken_seq: int | None = None
    for i in range(lo, hi + 1):
        e = parsed[i - 1]
        if not isinstance(e, dict):
            errors.append(f"parse:{i}")
            # The chain is broken at this line: force the next entry's
            # prev_hash check to fail loudly instead of silently resyncing.
            prev = None
        else:
            seq = e.get("seq")
            seq_is_int = isinstance(seq, int) and not isinstance(seq, bool)
            if not seq_is_int:
                errors.append(f"seq:{i}")
            elif not anchored:
                if seq != i:
                    errors.append(f"seq:{i}")
            else:
                if expected_seq is not None and seq != expected_seq:
                    errors.append(f"seq:{i}")
                if seq_is_int:
                    expected_seq = seq + 1  # next anchored entry must be seq+1
            if anchored and i == lo:
                if e.get("type") != _CHAIN_RECOVERY_TYPE:
                    errors.append(f"recovery_anchor:{i}")
                if e.get("prev_hash") is not None:
                    errors.append(f"prev_hash:{i}")
            elif e.get("prev_hash") != prev:
                errors.append(f"prev_hash:{i}")
            body = {k: v for k, v in e.items() if k != "hash"}
            if _hash(body) != e.get("hash"):
                errors.append(f"hash:{i}")
            serialized = json.dumps(e, ensure_ascii=False)
            if any(w in serialized.lower() and "[redacted" not in serialized.lower() for w in _SECRET_WORDS):
                errors.append(f"secret:{i}")
            prev = e.get("hash")
        if errors and first_broken_line is None:
            first_broken_line = i
            first_broken_seq = parsed[i - 1].get("seq") if isinstance(parsed[i - 1], dict) else None
    return {
        "errors": errors,
        "first_broken_line": first_broken_line,
        "first_broken_seq": first_broken_seq,
    }


class _LedgerState:
    """State shared by all TraceLedger instances on one canonical path."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        # Boot integrity check runs at most once per process per path:
        # init-time verify() is O(file) and must not tax the per-append path.
        # boot_verified=True: the check RAN on this path in this process.
        # boot_skipped=True: the check was SKIPPED because the ledger location
        # raised OSError (unwritable/invalid) — appends fail-closed at use.
        self.boot_verified = False
        self.boot_skipped = False


_ledger_states: dict[str, _LedgerState] = {}
_meta_lock = threading.Lock()


def _get_ledger_state(canonical_path: str) -> _LedgerState:
    with _meta_lock:
        if canonical_path not in _ledger_states:
            _ledger_states[canonical_path] = _LedgerState()
        return _ledger_states[canonical_path]


class TraceLedger:
    """Append-only, hash-chained JSONL audit ledger.

    Tamper-EVIDENT, not tamper-PROOF (see trust note at the end).

    Concurrency model
    -----------------
    - In-process: one RLock per canonical path (threads serialize).
    - Cross-process: EVERY append re-reads the tail and writes while holding
      an OS-level exclusive lock on a dedicated ``<path>.lock`` file (msvcrt
      on Windows, fcntl.flock on POSIX; RuntimeError if neither exists —
      fail-closed). Two processes therefore can no longer fork the chain by
      appending concurrently (root cause of the 2026-09-23
      data/trace_ledger.jsonl corruption: two processes appended at the same
      seq with divergent prev_hash, misaligning 808+ entries).
    - The tail is re-read under the cross-process lock on EVERY append, so a
      process never reuses a stale seq after another process appended.
    - verify() reads WITHOUT the OS lock (report-only; a concurrent in-flight
      line may rarely be observed as a parse error — fail-loud, never silent).

    Corruption policy — CHAIN_RECOVERY re-anchor (history is NEVER rewritten)
    ------------------------------------------------------------------------
    At init (once per process per path; opt out with ``verify_on_init=False``
    for read-only callers) verify() runs once. If the chain is invalid, an
    error log named ``[TRACE-LEDGER-BLOCKER]`` reports the file, the first
    broken line/seq and the recovery action, then ONE explicit anchor entry
    is appended and a NEW chain segment starts from it::

        {"type": "CHAIN_RECOVERY", "seq": <max_seq + 1>,
         "broken_at_seq": <first broken seq>, "prev_hash": null,
         "hash": <fresh anchor>}

    The corrupted history stays on disk untouched as tamper evidence — never
    delete or rewrite it. verify() then validates the active segment from the
    last CHAIN_RECOVERY marker (``hash_chain_valid`` covers that segment
    only); the pre-anchor history is reported via ``history_valid`` /
    ``history_errors`` and never counted as current-chain failure.

    Unwritable/invalid ledger locations (OSError such as PermissionError or
    FileNotFoundError at init — e.g. a POSIX-style ``/tmp`` path on Windows
    resolving to ``\tmp`` at the drive root) do NOT crash construction: the
    boot check is skipped with a WARNING and ``boot_skipped=True`` is set on
    the instance. Appends then raise (fail-closed at use time) while the
    path stays unwritable. A non-UTF-8 byte in the ledger file never crashes
    construction either: reads are decode-safe (errors="replace") and the
    corrupt line is a parse error handled by the CHAIN_RECOVERY re-anchor
    path; a residual ValueError from the boot check still only marks
    boot_skipped. Valid writable ledgers still verify and recover
    normally at boot — no gate is weakened.

    Trust note: any writer who can append to the file can also append a fresh
    CHAIN_RECOVERY anchor. The ledger proves continuity between appends; it
    cannot defend against a writer with filesystem write access (layered
    HMAC provenance lives in scp/core/autonomous_ledger.py).
    """

    def __init__(self, path: str | Path, *, verify_on_init: bool = True) -> None:
        self.path = Path(path)
        self.boot_verified = False
        self.boot_skipped = False
        self._state = _get_ledger_state(str(self.path.resolve()))
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            # Unwritable/invalid ledger location (e.g. a POSIX-style "/tmp"
            # path on Windows resolves to "\tmp" at the drive root):
            # construction must not crash. The failure is surfaced at USE
            # time instead — appends raise while the path stays unwritable,
            # which is the fail-closed point (never a silent bypass).
            self._mark_boot_skipped(exc)
            return
        if verify_on_init:
            self._boot_verify_once()

    def _mark_boot_skipped(self, exc: Exception) -> None:
        """Record a skipped boot verification (instance + per-path state)."""
        self.boot_verified = False
        self.boot_skipped = True
        self._state.boot_verified = False
        self._state.boot_skipped = True
        logger.warning(
            "[TRACE-LEDGER] ledger boot verification skipped: %s "
            "(ledger path: %s); appends will fail-closed if the path stays unwritable",
            exc,
            str(self.path),
        )

    def _lock_path(self) -> Path:
        return self.path.with_name(self.path.name + ".lock")

    def _boot_verify_once(self) -> None:
        """Boot-time fail-loud integrity check (once per process per path)."""
        if self._state.boot_verified or self._state.boot_skipped:
            # Already attempted once for this path in this process: carry the
            # recorded outcome onto this instance instead of re-running O(file).
            self.boot_verified = self._state.boot_verified
            self.boot_skipped = self._state.boot_skipped
            return
        try:
            self.verify_and_recover()
        except (OSError, ValueError) as exc:
            # Unwritable/invalid ledger location (e.g. a POSIX-style "/tmp"
            # path on Windows resolves to "\tmp" at the drive root, or a lock
            # file that cannot be created): construction must not crash. The
            # failure surfaces at USE time — appends raise while the path
            # stays unwritable, which is the fail-closed point.
            # [CORRUPT-BYTE 2026-09-30] ValueError (UnicodeDecodeError ⊂
            # ValueError) is caught too as defense in depth: a decode failure
            # inside verify() must never crash construction — it surfaces as
            # boot_skipped (visible WARNING) and appends fail-closed at use.
            # The primary fix keeps verify() itself decode-safe (see
            # _read_lines_utf8), so a corrupt byte takes the CHAIN_RECOVERY
            # re-anchor path instead of landing here.
            self._mark_boot_skipped(exc)
            return
        self._state.boot_verified = True
        self.boot_verified = True

    def _read_tail(self) -> tuple[int, str | None]:
        """Read the last record in O(1) by seeking backwards from EOF in binary mode."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            return 0, None
        try:
            with open(self.path, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                pos = size
                buffer_size = 4096
                remainder = b""
                while pos > 0:
                    read_len = min(buffer_size, pos)
                    pos -= read_len
                    f.seek(pos)
                    chunk = f.read(read_len) + remainder
                    lines = chunk.splitlines()
                    if len(lines) > 1:
                        for line in reversed(lines):
                            line = line.strip()
                            if line:
                                try:
                                    data = json.loads(line.decode("utf-8"))
                                    return int(data.get("seq", 0)), data.get("hash")
                                except Exception as exc:
                                    logger.debug("Failed parsing tail record line: %s", exc, exc_info=True)
                                    continue
                    remainder = lines[0] if lines else b""
                if remainder.strip():
                    try:
                        data = json.loads(remainder.decode("utf-8"))
                        return int(data.get("seq", 0)), data.get("hash")
                    except Exception as exc:
                        logger.debug("Failed parsing tail remainder record: %s", exc, exc_info=True)
        except OSError as exc:
            logger.debug("Error reading trace tail from %s: %s", self.path, exc)
        return 0, None

    def _write_entry(self, entry: dict[str, Any]) -> None:
        """Durably append one serialized entry (caller MUST hold state.lock + OS lock)."""
        prefix = ""
        if self.path.exists() and self.path.stat().st_size > 0:
            with open(self.path, "rb") as fb:
                fb.seek(-1, os.SEEK_END)
                if fb.read(1) != b"\n":
                    # A previous crash tore the last line mid-write: start a
                    # fresh line instead of concatenating onto the torn one.
                    prefix = "\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(prefix + json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def append(self, **fields: Any) -> dict[str, Any]:
        """Append one entry chained from the CURRENT on-disk tail.

        The tail is re-read under the cross-process lock on every append so
        two processes can never both claim the same seq. On a historically
        corrupted (not yet re-anchored) file the append would chain from the
        file tail; the boot recovery at init is what re-anchors legacy
        corruption before regular appends continue.
        """
        with self._state.lock:
            with _CrossProcessFileLock(self._lock_path()):
                seq, prev_hash = self._read_tail()
                new_seq = seq + 1
                entry = {
                    "trace_id": fields.pop("trace_id", None) or "trace_" + secrets.token_hex(8),
                    "seq": new_seq,
                    "prev_hash": prev_hash,
                    "fields": _redact(fields),
                }
                entry["hash"] = _hash(entry)
                self._write_entry(entry)
                return entry

    def _append_recovery_marker(self, *, broken_at_seq: Any, anchor_seq: int) -> dict[str, Any]:
        """Write the CHAIN_RECOVERY anchor (caller MUST hold state.lock + OS lock)."""
        entry = {
            "trace_id": "trace_recovery_" + secrets.token_hex(8),
            "type": _CHAIN_RECOVERY_TYPE,
            "seq": int(anchor_seq),
            "broken_at_seq": broken_at_seq if isinstance(broken_at_seq, int) else None,
            "prev_hash": None,
            "recovered_at": datetime.now(timezone.utc).isoformat(),
        }
        entry["hash"] = _hash(entry)
        self._write_entry(entry)
        return entry

    def verify_and_recover(self) -> dict[str, Any]:
        """verify() once under the cross-process lock; re-anchor if broken.

        Returns the post-recovery verify() report. When the chain is already
        valid this is a plain verify() and nothing is written. On an invalid
        chain a ``[TRACE-LEDGER-BLOCKER]`` error names the file, the first
        broken line/seq and the recovery action, then a single
        CHAIN_RECOVERY anchor is appended (new chain segment); the corrupted
        history remains on disk as tamper evidence.
        """
        with self._state.lock:
            with _CrossProcessFileLock(self._lock_path()):
                report = self.verify()
                if report["hash_chain_valid"]:
                    return report
                anchor_seq = int(report.get("max_seq", 0)) + 1
                logger.error(
                    "[TRACE-LEDGER-BLOCKER] ledger %s hash chain INVALID "
                    "(first broken line=%s seq=%s; %d active-segment errors, %d history errors) — "
                    "appending CHAIN_RECOVERY anchor (seq=%s) and starting a NEW chain segment; "
                    "corrupted history is preserved on disk as tamper evidence and must NOT be "
                    "rewritten or deleted; operator action: review history_errors before "
                    "trusting pre-anchor entries",
                    str(self.path),
                    report.get("first_broken_line"),
                    report.get("first_broken_seq"),
                    len(report.get("errors", [])),
                    len(report.get("history_errors", [])),
                    anchor_seq,
                )
                marker = self._append_recovery_marker(
                    broken_at_seq=report.get("first_broken_seq"),
                    anchor_seq=anchor_seq,
                )
                after = self.verify()
                after["recovery"] = {
                    "appended": True,
                    "anchor_seq": marker["seq"],
                    "broken_at_seq": marker.get("broken_at_seq"),
                    "anchor_line": after["entries"],
                }
                if not after["hash_chain_valid"]:
                    logger.error(
                        "[TRACE-LEDGER-BLOCKER] post-recovery verify STILL invalid for %s: %s",
                        str(self.path),
                        after.get("errors", [])[:20],
                    )
                return after

    def _read_lines_utf8(self) -> list[str]:
        """Read the ledger as text lines WITHOUT ever raising on a bad byte.

        [CORRUPT-BYTE 2026-09-30] One non-UTF-8 byte must not crash verify()/
        get_trace() with UnicodeDecodeError (a ValueError — it escaped the
        boot OSError catch and killed TraceLedger(path) AT CONSTRUCTION,
        violating the documented contract "construction must not crash;
        fail-closed at use"). The file is read as BYTES and decoded with
        errors="replace": a corrupt byte becomes U+FFFD inside its line,
        json.loads fails on exactly that line and it is counted as a
        ``parse:<line>`` error — fail-loud, and the existing CHAIN_RECOVERY
        re-anchor path handles it. Read errors (OSError) still propagate.
        """
        if not self.path.exists():
            return []
        return self.path.read_bytes().decode("utf-8", errors="replace").splitlines()

    def verify(self) -> dict[str, Any]:
        """Validate the ledger and return a detailed report.

        ``hash_chain_valid`` covers ONLY the active segment: the whole file
        when no CHAIN_RECOVERY anchor exists (legacy semantics: seq == line
        index), or the longest valid suffix from the last CHAIN_RECOVERY
        anchor. The pre-anchor history is never rewritten and is reported
        separately via ``history_valid`` / ``history_errors``.
        """
        with self._state.lock:
            # [CORRUPT-BYTE 2026-09-30] decode-safe read (was:
            # read_text(encoding="utf-8") — one bad byte crashed verify()).
            lines = self._read_lines_utf8()
            parsed: list[Any] = []
            max_seq = 0
            for _line_no, line in enumerate(lines, 1):
                try:
                    e = json.loads(line)
                except Exception:
                    # [VERIFY-VISIBILITY] (K-03) Unparsable lines are already
                    # counted as `parse:<line>` errors by _validate_segment;
                    # they must not also vanish into debug logs.
                    logger.warning(
                        "trace_ledger.verify: unparsable JSON line %d in %s "
                        "(counted as parse error)", _line_no, self.path
                    )
                    e = None
                parsed.append(e)
                if isinstance(e, dict):
                    seq = e.get("seq")
                    if isinstance(seq, int) and not isinstance(seq, bool) and seq > max_seq:
                        max_seq = seq
            anchor_idx: int | None = None
            for i, e in enumerate(parsed, 1):
                if isinstance(e, dict) and e.get("type") == _CHAIN_RECOVERY_TYPE:
                    anchor_idx = i  # the LAST anchor wins
            active = _validate_segment(parsed, anchor_idx or 1, len(parsed), anchored=anchor_idx is not None)
            if anchor_idx is not None and anchor_idx > 1:
                history = _validate_segment(parsed, 1, anchor_idx - 1, anchored=False)
            else:
                history = {"errors": [], "first_broken_line": None, "first_broken_seq": None}
            first_broken_line = history["first_broken_line"] or active["first_broken_line"]
            if history["first_broken_line"] is not None:
                first_broken_seq: Any = history["first_broken_seq"]
            else:
                first_broken_seq = active["first_broken_seq"]
            report: dict[str, Any] = {
                "entries": len(lines),
                "hash_chain_valid": not active["errors"],
                "errors": active["errors"],
                "history_valid": not history["errors"],
                "history_errors": history["errors"],
                "max_seq": max_seq,
                "anchor": None,
                "first_broken_line": first_broken_line,
                "first_broken_seq": first_broken_seq,
            }
            if anchor_idx is not None:
                marker = parsed[anchor_idx - 1]
                report["anchor"] = {
                    "line": anchor_idx,
                    "seq": marker.get("seq") if isinstance(marker, dict) else None,
                    "broken_at_seq": marker.get("broken_at_seq") if isinstance(marker, dict) else None,
                }
            return report

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        with self._state.lock:
            # [CORRUPT-BYTE 2026-09-30] decode-safe read — same defect class
            # as verify(): a bad byte must skip that line, not raise.
            for line in reversed(self._read_lines_utf8()):
                if not line.strip():
                    continue
                try:
                    e = json.loads(line)
                    if (
                        e.get("trace_id") == trace_id
                        or e.get("fields", {}).get("task_id") == trace_id
                        or e.get("fields", {}).get("trace_id") == trace_id
                    ):
                        return e
                except Exception as exc:
                    logger.debug(f"get_trace ignored: {exc}", exc_info=True)
                    continue
            return None


__all__ = ["TraceLedger"]
