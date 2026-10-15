#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scp.history import HistoryMigration, MigrationConfig
from scp.history.migration import HistoryMigrationError


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SCP R44 evidence-gated historical migration scan")
    p.add_argument("--db", action="append", type=Path, default=[])
    p.add_argument("--jsonl", action="append", type=Path, default=[])
    p.add_argument("--evolution-db", type=Path)
    p.add_argument("--static-knowledge", type=Path)
    p.add_argument("--reality-results", type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--max-jsonl-rows", type=int, default=100_000)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    migration = HistoryMigration(MigrationConfig(max_jsonl_rows=args.max_jsonl_rows))
    try:
        for path in args.db:
            migration.scan_sqlite(path)
        for path in args.jsonl:
            migration.scan_jsonl(path)
        if args.evolution_db:
            migration.scan_evolution_db(args.evolution_db)
        if args.static_knowledge:
            migration.scan_static_knowledge(args.static_knowledge)
        if args.reality_results:
            migration.scan_reality_results(args.reality_results)
        output = migration.write_manifest(args.output)
        print(json.dumps({
            "status": "SCANNED",
            "output": str(output),
            "artifact_count": len(migration.artifacts),
            "candidate_count": len(migration.candidates),
            "quarantine_count": len(migration.quarantine),
            "mutating": False,
            "policy_promotion": False,
        }, ensure_ascii=False, indent=2))
        return 0
    except (HistoryMigrationError, OSError, ValueError) as exc:
        print(json.dumps({"status": "REJECTED", "error": type(exc).__name__}, ensure_ascii=False), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
