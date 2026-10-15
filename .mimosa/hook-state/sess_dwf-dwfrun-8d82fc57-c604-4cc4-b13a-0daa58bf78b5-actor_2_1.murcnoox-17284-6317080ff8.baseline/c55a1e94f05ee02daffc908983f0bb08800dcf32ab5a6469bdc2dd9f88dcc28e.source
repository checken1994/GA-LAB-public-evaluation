from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screening", type=Path, required=True)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument("--output-queue", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-summary", type=Path, required=True)
    parser.add_argument("--review-size", type=int, default=200)
    parser.add_argument("--min-count", type=int, default=1)
    parser.add_argument("--min-coverage", type=float, default=0.08)
    args = parser.parse_args()

    screening = load_jsonl(args.screening)
    base_by_id = {str(row.get("question_id")): row for row in load_jsonl(args.review_queue)}
    eligible = [
        row for row in screening
        if row.get("chosen_source") != "none"
        and int(row.get("shared_term_count") or 0) >= args.min_count
        and float(row.get("coverage") or 0) >= args.min_coverage
    ]
    eligible.sort(key=lambda row: (float(row.get("selection_score") or 0), int(row.get("shared_term_count") or 0), float(row.get("coverage") or 0), str(row.get("question_id"))), reverse=True)
    selected = eligible[: args.review_size]
    output_rows: list[dict[str, Any]] = []
    for rank, row in enumerate(selected, start=1):
        base = dict(base_by_id.get(str(row.get("question_id")), {}))
        high_signal = int(row.get("shared_term_count") or 0) >= 2 and float(row.get("coverage") or 0) >= 0.20
        base.update(
            {
                "question_id": row.get("question_id"),
                "question": row.get("question"),
                "domain": row.get("domain", "general"),
                "candidate_alignment_shared_term_count": int(row.get("shared_term_count") or 0),
                "candidate_alignment_shared_terms": row.get("shared_terms") or [],
                "candidate_alignment_coverage": row.get("coverage") or 0.0,
                "candidate_alignment_selection_score": row.get("selection_score") or 0.0,
                "candidate_alignment_short_query": row.get("short_query") or "",
                "candidate_alignment_source": row.get("chosen_source") or "",
                "candidate_alignment_source_url": row.get("chosen_url") or "",
                "candidate_alignment_source_title": row.get("chosen_title") or "",
                "candidate_ddg_status": row.get("ddg_status") or "",
                "candidate_ddg_abstract_source": row.get("ddg_abstract_source") or "",
                "candidate_ddg_abstract_text": row.get("ddg_abstract_text") or "",
                "candidate_alignment_band": "HIGH_SIGNAL" if high_signal else "REVIEW_SIGNAL",
                "candidate_alignment_review_rank": rank,
                "gold_chunk_ids": base.get("gold_chunk_ids") or [],
                "gold_answer": base.get("gold_answer") or "",
                "gold_status": "SOURCE_FETCHED_NOT_REVIEWED",
                "review_method": "human_review_after_ddg_short_alignment",
                "reviewer_notes": "Pre-review filter only. HIGH_SIGNAL means >=2 shared terms and >=0.20 coverage; REVIEW_SIGNAL means it passed the relaxed shortlist threshold and still requires independent source/gold verification. No row is accepted as gold automatically.",
            }
        )
        output_rows.append(base)
    args.output_queue.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary.parent.mkdir(parents=True, exist_ok=True)
    args.output_queue.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in output_rows) + "\n", encoding="utf-8")
    fields = ["question_id", "question", "domain", "candidate_alignment_band", "candidate_alignment_review_rank", "candidate_alignment_shared_term_count", "candidate_alignment_shared_terms", "candidate_alignment_coverage", "candidate_alignment_selection_score", "candidate_alignment_short_query", "candidate_alignment_source", "candidate_alignment_source_url", "candidate_alignment_source_title", "candidate_ddg_status", "candidate_ddg_abstract_source", "candidate_ddg_abstract_text", "candidate_chunks", "gold_chunk_ids", "gold_answer", "gold_status", "review_method", "reviewer_notes"]
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in output_rows:
            writer.writerow({field: json.dumps(row.get(field), ensure_ascii=False) if isinstance(row.get(field), (list, dict)) else row.get(field, "") for field in fields})
    high = sum(row["candidate_alignment_band"] == "HIGH_SIGNAL" for row in output_rows)
    summary = {
        "screening_rows": len(screening),
        "eligible_rows": len(eligible),
        "selected_rows": len(output_rows),
        "target_rows": args.review_size,
        "high_signal_rows": high,
        "review_signal_rows": len(output_rows) - high,
        "min_shared_term_count": args.min_count,
        "min_coverage": args.min_coverage,
        "selection_cutoff_score": output_rows[-1].get("candidate_alignment_selection_score") if output_rows else None,
        "selection_cutoff_shared_term_count": output_rows[-1].get("candidate_alignment_shared_term_count") if output_rows else None,
        "source_note": "DDG HTML search was bot-challenged; DDG Instant Answer API plus existing canonical fetch were used. This is a shortlist, not gold evidence.",
        "output_queue": str(args.output_queue),
        "output_csv": str(args.output_csv),
    }
    args.output_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
