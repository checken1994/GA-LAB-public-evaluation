#!/usr/bin/env python3
"""Remove blank lines from a JSONL file without changing non-blank bytes.

Safe defaults:
- dry-run unless --apply is provided
- only accepts supervisor-ledger.jsonl unless --force is provided
- creates a timestamped backup before atomic replacement
- refuses --apply when a non-blank line is not valid JSON if --check-json is used

Run this only after the writer is quiescent (Supervisor and Watchdog stopped/disabled),
because an atomic replacement while another process appends can lose newly appended lines.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect(path: Path, check_json: bool) -> tuple[int, int, int, int, str]:
    total = 0
    blank = 0
    nonblank = 0
    invalid = 0
    with path.open("rb") as source:
        for raw in source:
            total += 1
            if not raw.strip():
                blank += 1
                continue
            nonblank += 1
            if check_json:
                try:
                    json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    invalid += 1
    return total, blank, nonblank, invalid, sha256(path)


def clean_atomic(path: Path, backup_dir: Path) -> tuple[Path, str]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backup_dir / f"{path.name}.{stamp}.before-clean.bak"
    shutil.copy2(path, backup)

    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as source_out:
            with path.open("rb") as source:
                for raw in source:
                    if raw.strip():
                        source_out.write(raw)
            source_out.flush()
            os.fsync(source_out.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return backup, sha256(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="replace the ledger after creating a backup")
    parser.add_argument("--check-json", action="store_true", help="validate every non-blank line as JSON")
    parser.add_argument("--force", action="store_true", help="allow a filename other than supervisor-ledger.jsonl")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.ledger.expanduser().resolve()
    if not path.is_file():
        print(f"ERROR=ledger_not_found path={path}", file=sys.stderr)
        return 2
    if path.name != "supervisor-ledger.jsonl" and not args.force:
        print("ERROR=refusing_non_supervisor_ledger_use_--force_to_override", file=sys.stderr)
        return 2

    total, blank, nonblank, invalid, before_hash = inspect(path, args.check_json)
    print(f"LEDGER={path}")
    print(f"TOTAL_LINES={total}")
    print(f"BLANK_LINES={blank}")
    print(f"NONBLANK_LINES={nonblank}")
    print(f"INVALID_JSON_LINES={invalid}")
    print(f"BEFORE_SHA256={before_hash}")

    if args.check_json and invalid:
        print("ACTION=REFUSED_INVALID_JSON", file=sys.stderr)
        return 3
    if not args.apply:
        print("ACTION=DRY_RUN_NO_FILE_CHANGED")
        return 0
    if blank == 0:
        print("ACTION=NOOP_NO_BLANK_LINES")
        return 0

    backup_dir = args.backup_dir or path.parent / "ledger-cleanup-backups"
    backup, after_hash = clean_atomic(path, backup_dir)
    after_total, after_blank, after_nonblank, after_invalid, _ = inspect(path, args.check_json)
    if after_blank or after_nonblank != nonblank or (args.check_json and after_invalid):
        print("ERROR=postcondition_failed_restore_backup", file=sys.stderr)
        shutil.copy2(backup, path)
        return 4
    print(f"ACTION=APPLIED")
    print(f"BACKUP={backup}")
    print(f"AFTER_LINES={after_total}")
    print(f"AFTER_BLANK_LINES={after_blank}")
    print(f"AFTER_SHA256={after_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
