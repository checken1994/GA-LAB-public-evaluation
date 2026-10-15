"""Human review queue and fail-closed decision importer for RAG evidence.

This module never promotes candidates automatically. A VERIFIED decision requires
reviewer identity, UTC time, source URL, evidence quote, a matching decision hash,
and (when configured) an HMAC signature key supplied by the reviewing organization.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import html
import json
import os
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

DECISIONS = {"VERIFIED", "REJECTED", "NEEDS_MORE_EVIDENCE"}
QUEUE_FIELDS = [
    "question_id",
    "question",
    "candidate_answer",
    "source_url",
    "source_title",
    "source_excerpt",
    "source_excerpt_sha256",
    "current_or_high_stakes",
    "human_review_required",
    "decision",
    "evidence_quote",
    "reviewer_id",
    "reviewed_at_utc",
    "reviewer_note",
    "decision_hash",
    "review_signature",
]
SIGNED_FIELDS = [
    "question_id",
    "decision",
    "evidence_quote",
    "source_url",
    "reviewer_id",
    "reviewed_at_utc",
    "reviewer_note",
]


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def canonical_decision(row: dict[str, Any]) -> bytes:
    payload = {field: str(row.get(field, "")).strip() for field in SIGNED_FIELDS}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def decision_hash(row: dict[str, Any]) -> str:
    return sha256_text(canonical_decision(row).decode("utf-8"))


def decision_signature(row: dict[str, Any], key: str) -> str:
    return "hmac-sha256:" + hmac.new(key.encode("utf-8"), canonical_decision(row), hashlib.sha256).hexdigest()


def _first(row: dict[str, Any], names: tuple[str, ...], default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value)
    return default


def _is_current(row: dict[str, Any]) -> bool:
    raw = _first(row, ("high_stakes_or_current", "current_or_high_stakes", "temporal_scope"), "")
    normalized = raw.lower().replace("-", "_").replace(" ", "_")
    return normalized in {"true", "1", "yes", "current", "high_stakes", "current_or_high_stakes", "temporal_or_static_unproven"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def build_queue(rows: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    queue: list[dict[str, str]] = []
    for row in rows:
        excerpt = _first(row, ("gold_evidence_quote", "source_excerpt", "evidence_quote"))
        queue.append(
            {
                "question_id": _first(row, ("question_id",)),
                "question": _first(row, ("question",)),
                "candidate_answer": _first(row, ("candidate_answer", "provisional_answer", "answer")),
                "source_url": _first(row, ("source_url", "proposed_canonical_source_url", "legacy_source_url")),
                "source_title": _first(row, ("source_title", "proposed_source_title", "legacy_source_title")),
                "source_excerpt": excerpt,
                "source_excerpt_sha256": sha256_text(excerpt) if excerpt else "",
                "current_or_high_stakes": "true" if _is_current(row) else "false",
                "human_review_required": "true",
                "decision": "",
                "evidence_quote": "",
                "reviewer_id": "",
                "reviewed_at_utc": "",
                "reviewer_note": "",
                "decision_hash": "",
                "review_signature": "",
            }
        )
    return queue


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUEUE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: str(row.get(field, "")).rstrip() for field in QUEUE_FIELDS} for row in rows)


def finalize_decisions_csv(input_path: Path, output_path: Path, signing_key: str | None = None) -> int:
    """Add integrity fields to reviewer-supplied decisions without inventing them."""
    with input_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    finalized = 0
    for row in rows:
        if str(row.get("decision", "")).strip():
            row["decision"] = str(row.get("decision", "")).strip().upper()
            row["decision_hash"] = decision_hash(row)
            row["review_signature"] = decision_signature(row, signing_key) if signing_key else ""
            finalized += 1
    write_csv(output_path, rows)
    return finalized


def _textarea(value: str) -> str:
    return html.escape(value, quote=True)


def write_html(path: Path, rows: list[dict[str, str]]) -> None:
    cards = []
    for index, row in enumerate(rows):
        hidden = "".join(
            f'<input type="hidden" name="{field}" value="{_textarea(row.get(field, ""))}">'
            for field in (
                "question_id", "question", "candidate_answer", "source_url", "source_title",
                "source_excerpt", "source_excerpt_sha256", "current_or_high_stakes",
                "human_review_required",
            )
        )
        cards.append(
            f"""<article class="review-card" data-index="{index}">
<h2>{_textarea(row['question_id'])}</h2>
{hidden}
<p><strong>Câu hỏi:</strong> {_textarea(row['question'])}</p>
<p><strong>Câu trả lời ứng viên:</strong> {_textarea(row['candidate_answer'])}</p>
<p><strong>Nguồn:</strong> <a rel="noreferrer" target="_blank" href="{_textarea(row['source_url'])}">{_textarea(row['source_title'] or row['source_url'])}</a></p>
<p><strong>Đoạn nguồn đang có:</strong> {_textarea(row['source_excerpt']) or '<em>Chưa có đoạn trích — không được VERIFIED.</em>'}</p>
<p><label>Quyết định
<select name="decision"><option value="">Chưa review</option><option>VERIFIED</option><option>REJECTED</option><option>NEEDS_MORE_EVIDENCE</option></select></label></p>
<p><label>Đoạn bằng chứng đã kiểm tra<br><textarea name="evidence_quote" rows="3"></textarea></label></p>
<p><label>Ghi chú<br><textarea name="reviewer_note" rows="2"></textarea></label></p>
</article>"""
        )
    content = """<!doctype html>
<html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SCP Human Review Queue</title>
<style>body{font-family:system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;line-height:1.45;background:#f6f7f9}.toolbar{position:sticky;top:0;background:white;padding:1rem;border:1px solid #ddd;border-radius:8px;z-index:2}.review-card{background:white;border:1px solid #ddd;border-radius:8px;padding:1rem;margin:1rem 0}.review-card textarea{width:100%;box-sizing:border-box}.review-card select{padding:.4rem}.warn{color:#8a3b12}</style>
<div class="toolbar"><h1>SCP — Review bằng chứng</h1><p class="warn">Không chọn VERIFIED nếu chưa mở và đọc nguồn. Review của model không phải human verification.</p><label>Reviewer ID <input id="reviewer_id" required></label> <button id="export">Xuất CSV đã review</button></div>
<section id="cards">__CARDS__</section>
<script>
const fields=['question_id','question','candidate_answer','source_url','source_title','source_excerpt','source_excerpt_sha256','current_or_high_stakes','human_review_required','decision','evidence_quote','reviewer_id','reviewed_at_utc','reviewer_note','decision_hash','review_signature'];
function esc(v){return '"'+String(v??'').replaceAll('"','""')+'"'}
document.querySelectorAll('.review-card').forEach(card=>{card.querySelector('select').addEventListener('change',e=>{if(e.target.value==='VERIFIED' && card.querySelector('textarea[name=evidence_quote]').value.trim()==='') alert('VERIFIED cần đoạn bằng chứng.');});});
document.querySelector('#export').addEventListener('click',()=>{const reviewer=document.querySelector('#reviewer_id').value.trim();if(!reviewer){alert('Cần Reviewer ID');return;}const now=new Date().toISOString();const rows=[fields];document.querySelectorAll('.review-card').forEach(card=>{const values={};fields.forEach(f=>{const el=card.querySelector('[name='+f+']');values[f]=el?el.value:''});values.question_id=card.querySelector('h2').textContent;values.question=card.querySelector('p').textContent.replace('Câu hỏi: ','');values.reviewer_id=reviewer;values.reviewed_at_utc=now;rows.push(fields.map(f=>values[f]||''));});const csv=rows.map(r=>r.map(esc).join(',')).join('\\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(['\\ufeff'+csv],{type:'text/csv;charset=utf-8'}));a.download='scp-human-review-decisions.csv';a.click();});
</script></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.replace("__CARDS__", "\n".join(cards)), encoding="utf-8")


def validate_decisions(candidates: Iterable[dict[str, Any]], decisions: Iterable[dict[str, Any]], signing_key: str | None = None) -> dict[str, Any]:
    candidate_by_id = {str(row.get("question_id", "")): row for row in candidates}
    results: list[dict[str, Any]] = []
    eligible = 0
    for decision in decisions:
        qid = str(decision.get("question_id", ""))
        errors: list[str] = []
        candidate = candidate_by_id.get(qid)
        if candidate is None:
            errors.append("question_id_not_in_candidates")
        value = str(decision.get("decision", "")).strip().upper()
        if value not in DECISIONS:
            errors.append("invalid_decision")
        reviewer = str(decision.get("reviewer_id", "")).strip()
        reviewed_at = str(decision.get("reviewed_at_utc", "")).strip()
        evidence = str(decision.get("evidence_quote", "")).strip()
        source_url = str(decision.get("source_url", "")).strip()
        if not reviewer:
            errors.append("reviewer_id_required")
        try:
            parsed = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                errors.append("reviewed_at_must_have_timezone")
        except ValueError:
            errors.append("reviewed_at_invalid_iso8601")
        if not source_url:
            errors.append("source_url_required")
        if value == "VERIFIED" and not evidence:
            errors.append("evidence_quote_required_for_verified")
        if candidate is not None:
            expected_source = _first(candidate, ("source_url", "proposed_canonical_source_url", "legacy_source_url"))
            if expected_source and source_url != expected_source:
                errors.append("source_url_mismatch")
        expected_hash = decision_hash(decision)
        if str(decision.get("decision_hash", "")) != expected_hash:
            errors.append("decision_hash_mismatch")
        signature = str(decision.get("review_signature", "")).strip()
        signature_status = "NOT_CHECKED"
        if signing_key:
            signature_status = "VALID" if hmac.compare_digest(signature, decision_signature(decision, signing_key)) else "INVALID"
            if signature_status != "VALID":
                errors.append("review_signature_invalid")
        elif value == "VERIFIED":
            signature_status = "KEY_REQUIRED"
            errors.append("signing_key_required_for_verified")
        ok = not errors
        if ok:
            eligible += 1
        results.append({"question_id": qid, "decision": value, "eligible": ok, "signature_status": signature_status, "errors": errors})
    return {
        "schema_version": "scp-human-review-validation-v1",
        "rows": len(results),
        "eligible_for_gold": eligible,
        "status": "PASS_WITHIN_SCOPE" if results and eligible == len(results) else "BLOCKED",
        "results": results,
        "human_review_required": True,
        "note": "This validator verifies reviewer-supplied records; it never creates human decisions.",
    }


def cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build-queue")
    build.add_argument("input_jsonl", type=Path)
    build.add_argument("output_csv", type=Path)
    build.add_argument("output_html", type=Path)
    finalize = sub.add_parser("finalize-decisions")
    finalize.add_argument("input_csv", type=Path)
    finalize.add_argument("output_csv", type=Path)
    validate = sub.add_parser("validate-decisions")
    validate.add_argument("candidates_jsonl", type=Path)
    validate.add_argument("decisions_csv", type=Path)
    validate.add_argument("output_json", type=Path)
    args = parser.parse_args()
    if args.command == "finalize-decisions":
        finalized = finalize_decisions_csv(args.input_csv, args.output_csv, os.environ.get("SCP_REVIEW_HMAC_KEY"))
        print(json.dumps({"finalized_rows": finalized, "output": str(args.output_csv), "signed": bool(os.environ.get("SCP_REVIEW_HMAC_KEY"))}, ensure_ascii=False))
        return 0
    if args.command == "build-queue":
        queue = build_queue(load_jsonl(args.input_jsonl))
        write_csv(args.output_csv, queue)
        write_html(args.output_html, queue)
        print(json.dumps({"rows": len(queue), "csv": str(args.output_csv), "html": str(args.output_html), "human_review_required": True}, ensure_ascii=False))
        return 0
    with args.decisions_csv.open(encoding="utf-8-sig", newline="") as handle:
        decisions = list(csv.DictReader(handle))
    report = validate_decisions(load_jsonl(args.candidates_jsonl), decisions, os.environ.get("SCP_REVIEW_HMAC_KEY"))
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": report["rows"], "eligible_for_gold": report["eligible_for_gold"]}, ensure_ascii=False))
    return 0 if report["status"] == "PASS_WITHIN_SCOPE" else 2


if __name__ == "__main__":
    raise SystemExit(cli())
