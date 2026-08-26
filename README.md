# GA-LAB / SCP — Public Evaluation Evidence

> **Mục đích:** kho công khai này cung cấp bằng chứng có thể kiểm tra độc lập về một số cơ chế và cổng đánh giá của SCP. Đây là **evaluation evidence pack**, không phải bản sao đầy đủ của kho mã riêng GA-LAB và không phải tuyên bố production-ready.

## English summary

This repository is a sanitized, history-free evidence pack for independent evaluation of SCP (GA-LAB). It contains the current RAG-gate report, a 50-row independent LLM triage record, the 1,000-row Ragas admission audit, a one-row Ragas pilot record, canonical-root/archive provenance, and a reviewer-friendly CSV.

The repository intentionally does **not** contain private source history, `.env` files, tokens, runtime logs, local caches, raw PC archives, or unreviewed generated data. The private implementation repository remains at [checken1994/GA-LAB](https://github.com/checken1994/GA-LAB).

## What an external reviewer can verify

1. The exported evidence files are internally parseable and carry explicit scope/limitation statements.
2. The 50 reviewed candidates are **independent LLM review**, not human verification. The record reports zero original-question promotions and one static-core promotion; this does not create a human Gold set.
3. The 1,000-row Ragas admission audit is fail-closed and reports `BLOCKED_NO_VERIFIED_ROWS` when eligibility requirements are absent.
4. The one-row Ragas pilot is recorded as `RAGAS_PILOT_WITH_MISSING_METRIC`; its non-finite `answer_correctness` was normalized to `null`, so no release score is claimed.
5. The canonical development root and retired-workspace provenance are documented without publishing personal machine paths.

## What this repository does not prove

This evidence pack does not prove that SCP answers all 1,000 RAG questions correctly, has a human-verified Gold dataset, has a valid ARES score, is production-safe, is an Agent OS, has distributed or multi-host guarantees, or has eliminated every logic defect. It also does not claim that every file from the separate `scp-agent` repository has been merged into GA-LAB.

> A green test or an exported artifact is evidence for the stated test scope only. It is not proof of a stronger claim.

## Contents

| Path | Purpose |
|---|---|
| `REVIEW_SHEET_50.csv` | Reader-friendly 50-row review/triage table with provenance and independent-model label. |
| `PUBLIC_EXPORT_MANIFEST.json` | Machine-readable export scope and redaction assertions. |
| `artifacts/reports/PHASE3_RAG_GATE_STATUS_V3_20260826.md` | Current honest RAG gate status and limitations. |
| `artifacts/reports/FULL_FOLDER_AUDIT_20260826.md` | Sanitized full-folder audit: stale artifacts, duplicate classification, runtime-port alignment, and verification limits. |
| `artifacts/reports/phase3_rag_evidence_20260826/` | Sanitized admission audit, independent-review summary, and one-row pilot evidence. |
| `artifacts/reports/ROOT_SCP_SNAPSHOT_MANIFEST_20260826.json` | Snapshot provenance for the canonical private repository commit; local paths are redacted in this public copy. |
| `artifacts/reports/archived_workspaces_20260826/` | Provenance explaining why divergent workspaces were not blindly copied. |
| `REVIEW_PROTOCOL.md` | Instructions for a non-technical independent reviewer. |
| `SECURITY.md` | Reporting guidance for suspected security or privacy problems. |

## Reproduce the safe checks

These checks require Python 3.11+ and do not contact a model provider:

```bash
python3 -m json.tool PUBLIC_EXPORT_MANIFEST.json >/dev/null
python3 - <<'PY'
import csv, json
from pathlib import Path
with Path('REVIEW_SHEET_50.csv').open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 50
for p in Path('artifacts').rglob('*.json'):
    json.loads(p.read_text(encoding='utf-8-sig'))
print('public-evaluation checks: PASS')
PY
```

The private GA-LAB implementation has separate CI and runtime evidence. Reviewers should treat the commit hash embedded in the snapshot manifest as provenance and request an authorized source-level review if needed.

## Review outcome format

For each row or gate, record the exact artifact path, decision (`VERIFIED`, `REJECTED`, or `NEEDS_MORE_EVIDENCE`), reviewer identity or organization, UTC timestamp, and a short evidence quote or URL. A model-generated review is useful triage, but it must not be relabeled as human verification.

## License and attribution

This repository is published for evaluation and transparency. Individual reports and datasets may have different upstream rights and attribution requirements; inspect source/provenance fields before reusing them. No commercial-license representation is made here.
