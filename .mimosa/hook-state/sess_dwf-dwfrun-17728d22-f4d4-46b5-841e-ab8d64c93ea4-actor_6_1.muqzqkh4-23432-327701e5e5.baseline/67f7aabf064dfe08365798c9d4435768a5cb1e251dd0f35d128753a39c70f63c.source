from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

root = Path(sys.argv[1])
stage = root / ".private-secrets" / "release-audit" / "policy-runtime-integration-r43"
if stage.exists():
    shutil.rmtree(stage)
stage.mkdir(parents=True)
source_db = root / "data" / "v13.db"
stage_db = stage / "v13.db"
shutil.copy2(source_db, stage_db)
sys.path.insert(0, str(root))

import scp.core.db_manager as db_manager
# Isolate all legacy ExperienceEngine DB helpers in this child process.
db_manager.DATA_DIR = str(stage)
db_manager.DB_PATH = str(stage_db)

from scp.experience.experience import ExperienceEngine
engine = ExperienceEngine()
report = engine.run_reflection_cycle()

with sqlite3.connect(str(stage_db), timeout=5) as con:
    con.row_factory = sqlite3.Row
    counts = con.execute(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN applied=1 THEN 1 ELSE 0 END) AS applied,
                  SUM(CASE WHEN applied=0 THEN 1 ELSE 0 END) AS unapplied
           FROM experiences"""
    ).fetchone()

active = stage / "active_policies.json"
ledger = stage / "policy_handoff_ledger.jsonl"
result = {
    "status": "PASS" if report.get("policy_handoff", {}).get("status") in {"APPLIED", "NO_ELIGIBLE_POLICY_LESSONS", "NO_UNAPPLIED_LESSONS"} else "FAIL",
    "policy_handoff": report.get("policy_handoff"),
    "active_policy_exists": active.exists(),
    "ledger_exists": ledger.exists(),
    "experience_counts": dict(counts),
    "stage": str(stage),
}
(stage / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, default=str))
raise SystemExit(0 if result["status"] == "PASS" else 1)
