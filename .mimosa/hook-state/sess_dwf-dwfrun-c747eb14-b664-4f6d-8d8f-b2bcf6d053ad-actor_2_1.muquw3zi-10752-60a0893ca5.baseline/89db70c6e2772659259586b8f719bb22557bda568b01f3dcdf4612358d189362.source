#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scp.history.regression_corpus import CorpusConfig, build_cases, write_corpus


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_rows(path: Path, table: str, limit: int) -> list[dict[str, Any]]:
    # [SEC-S4] `table` comes from --table (argv). Identifiers cannot be
    # parameterized, so only a strict [A-Za-z0-9_]+ slug is accepted.
    if not re.fullmatch(r"[A-Za-z0-9_]+", table):
        raise ValueError(f"unsafe table name: {table!r}")
    # [SEC-S6] Literal SQL templates: only regex-validated identifiers from a
    # fixed column whitelist are substituted into constant statements (no
    # f-string/format/concat of variables into SQL text).
    pragma_template = 'PRAGMA table_info("@TABLE@")'
    select_template = 'SELECT @COLUMNS@ FROM "@TABLE@" LIMIT ?'
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        pragma_sql = pragma_template.replace("@TABLE@", table)
        names = {row[1] for row in connection.execute(pragma_sql)}  # identifier regex-validated above  # nosec B608
        if not names:
            raise ValueError(f"missing table: {table}")
        allowed = [
            "id", "event_id", "question_id", "question", "prompt", "input",
            "source", "verdict", "domain", "question_type",
        ]
        selected = [name for name in allowed if name in names]
        if not selected:
            raise ValueError(f"table has no supported fields: {table}")
        columns = ", ".join(f'"{name}"' for name in selected)
        select_sql = select_template.replace("@COLUMNS@", columns).replace("@TABLE@", table)
        rows = connection.execute(select_sql, (limit,)).fetchall()  # identifiers regex-validated above  # nosec B608
        return [dict(row) for row in rows]
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build bounded SCP R44 regression corpus")
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--table", default="question_events")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=10_000)
    args = parser.parse_args(argv)
    if args.limit < 1 or args.limit > 100_000:
        parser.error("--limit must be in [1, 100000]")
    rows = _read_rows(args.db, args.table, args.limit)
    source_sha256 = _file_sha256(args.db)
    cases = build_cases(
        rows,
        str(args.db),
        source_sha256,
        CorpusConfig(max_cases=args.limit, include_unknown=True),
    )
    manifest = write_corpus(
        cases,
        args.output,
        [{"path": str(args.db), "sha256": source_sha256, "table": args.table}],
    )
    print(json.dumps({
        "status": "BUILT",
        "cases": len(cases),
        "output": str(args.output),
        "corpus_sha256": manifest["corpus_sha256"],
        "lineage_counts": manifest["lineage_counts"],
        "ground_truth_count": manifest["ground_truth_count"],
        "policy_promotion": manifest["policy_promotion"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
