#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scp.history.semantic_gate import evaluate_candidate


def _rows(db: Path) -> list[dict[str, object]]:
    connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(
            "SELECT lesson_id, bug_type, bug_file, bug_line, fix_verified, success_rate FROM lessons ORDER BY lesson_id"
        )]
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit semantic evidence for persisted SCP lessons")
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    decisions = []
    for row in _rows(args.db):
        path = Path(str(row["bug_file"]))
        decision = evaluate_candidate(
            source_path=path,
            source_snapshot=None,
            expected_source_sha256=None,
            bug_type=str(row["bug_type"]),
            bug_line=int(row["bug_line"]),
            patched_source=None,
            semantic_tests_passed=False,
            independent_external_evidence=False,
        )
        decisions.append({
            "lesson_id": row["lesson_id"],
            "bug_type": row["bug_type"],
            "bug_file_basename": path.name,
            "bug_line": row["bug_line"],
            "fix_verified_record": row["fix_verified"],
            "success_rate_record": row["success_rate"],
            "source_exists": path.exists(),
            "source_sha256_current": decision.source_sha256,
            "target_is_bare_except_pass": decision.target_is_bare_except_pass,
            "status": decision.status,
            "promotion_allowed": decision.promotion_allowed,
            "reasons": list(decision.reasons),
        })
    result = {
        "schema": "scp-semantic-audit-r44",
        "lesson_count": len(decisions),
        "verified_record_count": sum(bool(row["fix_verified_record"]) for row in decisions),
        "promotion_allowed_count": sum(bool(row["promotion_allowed"]) for row in decisions),
        "classification_mismatch_count": sum("REJECT_CLASSIFICATION_MISMATCH" in row["reasons"] for row in decisions),
        "missing_snapshot_count": sum("REJECT_NO_SOURCE_SNAPSHOT" in row["reasons"] for row in decisions),
        "missing_external_evidence_count": sum("REJECT_NO_INDEPENDENT_EXTERNAL_EVIDENCE" in row["reasons"] for row in decisions),
        "policy_promotion": False,
        "decisions": decisions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "decisions"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
