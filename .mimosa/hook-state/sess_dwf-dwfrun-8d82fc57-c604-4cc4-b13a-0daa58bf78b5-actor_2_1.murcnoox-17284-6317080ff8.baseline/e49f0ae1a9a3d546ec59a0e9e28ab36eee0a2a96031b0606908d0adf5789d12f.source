#!/usr/bin/env python3
"""Create consistent, auditable SQLite snapshots without mutating live DBs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def file_meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def source_state(path: Path) -> dict[str, Any]:
    return {
        "db": file_meta(path),
        "wal": file_meta(path.with_name(path.name + "-wal")),
        "shm": file_meta(path.with_name(path.name + "-shm")),
    }


def table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    names = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    # [SEC-S6] Literal SQL template: only the regex-validated table name from
    # sqlite_master introspection is substituted into a constant statement
    # (no f-string/format/concat of variables into SQL text).
    sql_count_template = 'SELECT COUNT(*) FROM "@TABLE@"'
    counts: dict[str, int] = {}
    for name in names:
        # [SEC-S4] Identifiers cannot be parameterized; names come from
        # sqlite_master introspection, so enforce a strict whitelist before
        # quoting (defense-in-depth against exotic schema entries).
        if not re.fullmatch(r"[A-Za-z0-9_]+", name):
            continue
        count_sql = sql_count_template.replace("@TABLE@", name)
        counts[name] = int(connection.execute(count_sql).fetchone()[0])  # identifier regex-validated above  # nosec B608
    return counts


def read_only_uri(path: Path) -> str:
    # Path.as_uri() handles Windows drive letters and spaces safely.
    return f"{path.resolve().as_uri()}?mode=ro"


def snapshot_one(source: Path, destination: Path) -> dict[str, Any]:
    if not source.is_file():
        raise FileNotFoundError(source)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    before = source_state(source)
    source_integrity: str | None = None
    destination_integrity: str | None = None
    counts: dict[str, int] = {}
    try:
        with sqlite3.connect(read_only_uri(source), uri=True, timeout=15) as live:
            source_integrity = str(live.execute("PRAGMA integrity_check").fetchone()[0])
            with sqlite3.connect(destination, timeout=15) as copy:
                live.backup(copy, pages=256, sleep=0.05)
                copy.commit()
                destination_integrity = str(
                    copy.execute("PRAGMA integrity_check").fetchone()[0]
                )
                counts = table_counts(copy)
        with destination.open("r+b") as handle:
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        after = source_state(source)

    return {
        "source": str(source.resolve()),
        "snapshot": str(destination.resolve()),
        "source_state_before": before,
        "source_state_after": after,
        "source_changed_during_snapshot": before != after,
        "source_integrity": source_integrity,
        "snapshot_integrity": destination_integrity,
        "snapshot_sha256": sha256(destination),
        "table_counts": counts,
    }


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--label", default="snapshot")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
    output_dir = (
        root
        / ".private-secrets"
        / "release-audit"
        / "scp-247"
        / "experiments"
        / "snapshots"
        / f"{stamp}-{args.label}"
    )
    output_dir.mkdir(parents=True, exist_ok=False)

    manifest: dict[str, Any] = {
        "schema": "scp.sqlite.snapshot.v2",
        "status": "INCOMPLETE",
        "snapshot_id": output_dir.name,
        "created_utc": utc_now(),
        "root": str(root),
        "label": args.label,
        "snapshots": [],
        "errors": [],
    }
    for relative in (Path("data/v13.db"), Path("data/kb_evolve.sqlite")):
        source = root / relative
        destination = output_dir / relative.name
        try:
            manifest["snapshots"].append(snapshot_one(source, destination))
        except Exception as exc:  # boundary: record and fail closed
            manifest["errors"].append(
                {
                    "source": str(source),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    all_ok = (
        len(manifest["snapshots"]) == 2
        and not manifest["errors"]
        and all(
            item["source_integrity"] == "ok" and item["snapshot_integrity"] == "ok"
            for item in manifest["snapshots"]
        )
    )
    manifest["status"] = "COMPLETE" if all_ok else "INCOMPLETE"
    manifest_path = output_dir / "manifest.json"
    atomic_json_write(manifest_path, manifest)
    print(json.dumps({"manifest": str(manifest_path), **manifest}, ensure_ascii=False, indent=2))
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
