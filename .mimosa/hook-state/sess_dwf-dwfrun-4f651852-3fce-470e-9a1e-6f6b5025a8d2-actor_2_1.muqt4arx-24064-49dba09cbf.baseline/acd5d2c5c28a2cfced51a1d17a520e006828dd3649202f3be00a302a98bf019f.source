from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKTREE = ROOT
CANDIDATE = WORKTREE / "benchmark" / "gold_anchor_50_v2_candidates.jsonl"
OUT = WORKTREE / "benchmark" / "ares_preconditions_v2.json"

rows = [json.loads(line) for line in CANDIDATE.read_text(encoding="utf-8").splitlines() if line.strip()]
verified = [row for row in rows if row.get("eligible_for_ragas") is True and row.get("review_status") in {"HUMAN_VERIFIED", "INDEPENDENT_LLM_REVIEWED"}]
annotation_candidates = list(ROOT.glob("**/*human*annot*")) + list(ROOT.glob("**/*validation*"))
preconditions = {
    "human_annotated_set_at_least_50": False,
    "few_shot_examples_available": False,
    "unlabeled_query_document_answer_set_available": False,
    "verified_gold_non_abstain_rows_available": bool(verified),
    "candidate_rows": len(rows),
    "verified_rows": len(verified),
    "package_importable": bool(importlib.util.find_spec("ares")),
    "annotation_candidate_paths_observed": [str(path) for path in annotation_candidates[:20]],
}
failed = [name for name, value in preconditions.items() if name in {"human_annotated_set_at_least_50", "few_shot_examples_available", "unlabeled_query_document_answer_set_available", "verified_gold_non_abstain_rows_available", "package_importable"} and not value]
report = {
    "schema_version": "phase3-ares-preconditions-v2",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "method": "precondition_audit_only",
    "preconditions": preconditions,
    "failed_preconditions": failed,
    "execution_status": "BLOCKED_PRECONDITIONS",
    "score": None,
    "score_release_allowed": False,
    "note": "No ARES score was produced. Package presence alone is insufficient; ARES requires human-annotated calibration/validation data and appropriate unlabeled query-document-answer inputs.",
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
