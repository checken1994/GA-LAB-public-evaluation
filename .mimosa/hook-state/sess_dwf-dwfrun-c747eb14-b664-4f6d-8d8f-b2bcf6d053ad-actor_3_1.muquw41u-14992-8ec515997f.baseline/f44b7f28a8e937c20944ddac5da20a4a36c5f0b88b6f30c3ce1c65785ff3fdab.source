from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUPPORTED = {
    "SOURCE_RELIABILITY",
    "DOMAIN_BIAS",
    "ERROR_FREQUENCY",
    "CONFIDENCE_TUNING",
    "ROUTE_OPTIMIZATION",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(lesson: dict[str, Any]) -> str:
    raw = "|".join(str(lesson.get(k, "")) for k in ("lesson_type", "policy_target", "policy_action"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _insert(conn: sqlite3.Connection, lesson: dict[str, Any]) -> bool:
    sha = _hash(lesson)
    try:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO experiences
            (timestamp, question, entity, domain, source, ai_answer, real_value,
             verdict, error_type, error_reason, lesson_type, lesson_description,
             policy_action, policy_target, policy_value, applied, sha256)
            VALUES (?, '', ?, ?, ?, '', '', ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                _now(), lesson.get("entity", ""), lesson.get("domain", ""), lesson.get("source", ""),
                lesson.get("verdict", ""), lesson.get("error_type", ""), lesson.get("error_reason", ""),
                lesson["lesson_type"], lesson["lesson_description"], lesson["policy_action"],
                lesson["policy_target"], lesson["policy_value"], sha,
            ),
        )
        return cursor.rowcount == 1
    except sqlite3.Error as exc:
        raise RuntimeError(f"experience lesson insert failed: {type(exc).__name__}") from exc


def reflect_and_store(db_path: str | Path) -> dict[str, Any]:
    db = Path(db_path)
    if not db.exists():
        raise RuntimeError(f"database missing: {db}")
    reflected: list[dict[str, Any]] = []
    with sqlite3.connect(str(db), timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        # Source reliability from knowledge. This is the V64/V96 lesson contract.
        try:
            rows = conn.execute(
                """
                SELECT source, COUNT(*) AS cnt,
                       AVG(confidence) AS avg_conf,
                       SUM(COALESCE(times_verified, 0)) AS total_verified,
                       SUM(COALESCE(times_wrong, 0)) AS total_wrong
                FROM knowledge GROUP BY source
                """
            ).fetchall()
        except sqlite3.Error:
            rows = []
        for row in rows:
            source = str(row["source"] or "")
            verified = int(row["total_verified"] or 0)
            wrong = int(row["total_wrong"] or 0)
            reliability = verified / (verified + wrong) if verified + wrong else float(row["avg_conf"] or 0)
            if reliability > 0.9:
                action = "PRIORITY_HIGH"
            elif reliability > 0.7:
                action = "PRIORITY_NORMAL"
            elif reliability > 0.4:
                action = "PRIORITY_LOW"
            else:
                action = "DISABLE"
            reflected.append({
                "lesson_type": "SOURCE_RELIABILITY",
                "lesson_description": f"Source '{source}' reliability={reliability:.0%}",
                "policy_action": action,
                "policy_target": source,
                "policy_value": str(round(reliability, 2)),
                "source": source,
            })
        # Domain bias, recurring errors and confidence tuning match legacy thresholds.
        try:
            rows = conn.execute(
                """SELECT frame, COUNT(*) AS total,
                   SUM(CASE WHEN final_verdict='FAIL' THEN 1 ELSE 0 END) AS fails
                   FROM error_history GROUP BY frame HAVING total >= 3"""
            ).fetchall()
        except sqlite3.Error:
            rows = []
        for row in rows:
            total = int(row["total"])
            fails = int(row["fails"] or 0)
            rate = fails / total if total else 0
            action = "INCREASE_TOLERANCE" if rate > 0.8 else "ADD_BIAS_CORRECTION" if rate > 0.5 else "MAINTAIN"
            reflected.append({
                "lesson_type": "DOMAIN_BIAS",
                "lesson_description": f"Domain '{row['frame']}' FAIL rate={rate:.0%}",
                "policy_action": action, "policy_target": str(row["frame"] or ""),
                "policy_value": str(round(rate, 2)), "domain": str(row["frame"] or ""),
            })
        try:
            rows = conn.execute(
                """SELECT question, COUNT(*) AS cnt FROM error_history
                   WHERE final_verdict='FAIL' GROUP BY question HAVING cnt >= 2
                   ORDER BY cnt DESC LIMIT 10"""
            ).fetchall()
        except sqlite3.Error:
            rows = []
        for row in rows:
            reflected.append({
                "lesson_type": "ERROR_FREQUENCY",
                "lesson_description": f"Recurring FAIL question count={int(row['cnt'])}",
                "policy_action": "FLAG_RECURRING", "policy_target": str(row["question"] or "")[:50],
                "policy_value": str(int(row["cnt"])), "verdict": "FAIL", "error_type": "recurring",
            })
        try:
            rows = conn.execute(
                """SELECT frame, COUNT(*) AS total,
                   SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active
                   FROM memory GROUP BY frame HAVING total >= 3"""
            ).fetchall()
        except sqlite3.Error:
            rows = []
        for row in rows:
            total = int(row["total"])
            active = int(row["active"] or 0)
            recovery = 1 - active / total if total else 0
            action = "LOWER_CONFIDENCE" if recovery < 0.3 else "MAINTAIN_CONFIDENCE"
            reflected.append({
                "lesson_type": "CONFIDENCE_TUNING",
                "lesson_description": f"Domain '{row['frame']}' recovery={recovery:.0%}",
                "policy_action": action, "policy_target": str(row["frame"] or ""),
                "policy_value": str(round(recovery, 2)), "domain": str(row["frame"] or ""),
            })
        try:
            rows = conn.execute(
                """SELECT entity, attribute, times_verified, confidence FROM knowledge
                   WHERE times_verified >= 3 AND confidence >= 0.8
                   ORDER BY times_verified DESC LIMIT 10"""
            ).fetchall()
        except sqlite3.Error:
            rows = []
        for row in rows:
            reflected.append({
                "lesson_type": "ROUTE_OPTIMIZATION",
                "lesson_description": f"Entity '{row['entity']}.{row['attribute']}' verified {int(row['times_verified'])}x",
                "policy_action": "USE_KB_FIRST",
                "policy_target": f"{row['entity']}.{row['attribute']}",
                "policy_value": str(int(row["times_verified"])),
                "entity": str(row["entity"] or ""), "domain": str(row["attribute"] or ""),
            })

        inserted = sum(1 for lesson in reflected if _insert(conn, lesson))
        conn.commit()
    return {
        "status": "REFLECTED",
        "db": str(db),
        "reflected": len(reflected),
        "inserted": inserted,
        "lesson_types": sorted({x["lesson_type"] for x in reflected}),
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(reflect_and_store(sys.argv[1]), ensure_ascii=False, sort_keys=True, indent=2))
