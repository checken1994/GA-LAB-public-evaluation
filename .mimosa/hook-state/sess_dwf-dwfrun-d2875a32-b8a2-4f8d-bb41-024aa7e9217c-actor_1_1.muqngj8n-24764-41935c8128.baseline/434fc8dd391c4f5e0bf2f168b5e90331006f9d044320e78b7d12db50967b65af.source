from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from r43_policy_materializer import PolicyMaterializer, PolicyMaterializerError


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SCP R43 policy handoff with staging-safe promotion and rollback")
    p.add_argument("--root", type=Path, required=True, help="SCP repository root")
    p.add_argument("--db", type=Path, default=None, help="learning DB; default <data-dir>/v13.db")
    p.add_argument("--data-dir", type=Path, default=None, help="policy/data directory; default <root>/data")
    p.add_argument("action", choices=["materialize", "promote", "apply", "rollback", "status"])
    p.add_argument("--candidate", type=Path, default=None)
    p.add_argument("--backup", type=Path, default=None)
    return p


def main() -> int:
    args = parser().parse_args()
    root = args.root.resolve()
    data_dir = (args.data_dir or root / "data").resolve()
    db_path = (args.db or data_dir / "v13.db").resolve()
    materializer = PolicyMaterializer(db_path=db_path, data_dir=data_dir)
    try:
        if args.action == "materialize":
            payload = materializer.materialize_candidate()
            print(json.dumps({
                "status": "MATERIALIZED",
                "candidate": str(materializer.candidate_path),
                "policy_sha256": payload["_meta"].get("policy_sha256"),
                "lessons_seen": payload["_meta"].get("lesson_count_seen", 0),
                "eligible_lessons": payload["_meta"].get("eligible_lesson_count", 0),
                "policy_key_counts": payload["_meta"].get("policy_key_counts", {}),
                "skipped_reasons": [x.get("reason") for x in payload["_meta"].get("skipped_lessons", [])],
            }, ensure_ascii=False, sort_keys=True))
            return 0
        if args.action == "promote":
            result = materializer.promote(args.candidate)
            print(json.dumps({"status": "PROMOTED", **result}, ensure_ascii=False, sort_keys=True))
            return 0
        if args.action == "apply":
            payload = materializer.materialize_candidate()
            eligible_ids = [int(x) for x in payload["_meta"].get("eligible_lesson_ids", [])]
            if not eligible_ids:
                print(json.dumps({
                    "status": "NO_ELIGIBLE_LESSONS",
                    "candidate": str(materializer.candidate_path),
                    "lessons_seen": payload["_meta"].get("lesson_count_seen", 0),
                    "skipped_reasons": [x.get("reason") for x in payload["_meta"].get("skipped_lessons", [])],
                }, ensure_ascii=False, sort_keys=True))
                return 3
            promoted = materializer.promote()
            applied = materializer.mark_applied(eligible_ids)
            materializer.record_applied(eligible_ids, applied)
            print(json.dumps({"status": "APPLIED", "applied_lessons": applied, **promoted}, ensure_ascii=False, sort_keys=True))
            return 0
        if args.action == "rollback":
            result = materializer.rollback(args.backup)
            print(json.dumps({"status": "ROLLED_BACK", **result}, ensure_ascii=False, sort_keys=True))
            return 0
        active = materializer.active_path
        candidate = materializer.candidate_path
        print(json.dumps({
            "status": "STATUS",
            "active_exists": active.exists(),
            "candidate_exists": candidate.exists(),
            "active": str(active),
            "candidate": str(candidate),
            "latest_backup": str(materializer._latest_backup()) if materializer._latest_backup() else None,
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except PolicyMaterializerError as exc:
        print(json.dumps({"status": "REJECTED", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
