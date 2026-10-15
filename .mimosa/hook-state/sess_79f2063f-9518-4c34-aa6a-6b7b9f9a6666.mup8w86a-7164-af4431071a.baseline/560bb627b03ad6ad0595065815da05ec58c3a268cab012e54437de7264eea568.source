from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import time
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ỹĐđ]{2,}", re.UNICODE)
STOPWORDS = {
    "các", "cách", "cho", "của", "được", "để", "đến", "điều", "giải", "gì", "hay",
    "hiện", "khi", "là", "làm", "một", "mới", "nhất", "nào", "năm", "nay", "những",
    "qua", "sao", "sớm", "theo", "thế", "thì", "trên", "trong", "tại", "từ", "và", "về",
    "với", "ý", "nghĩa", "online", "mã", "question", "what", "which", "when", "where",
    "how", "the", "and", "for", "with", "from", "this", "that", "latest", "year",
}
SEARCH_HOSTS = {"duckduckgo.com", "www.duckduckgo.com", "bing.com", "www.bing.com", "google.com", "www.google.com"}
USER_AGENT = "SCP-DDG-Short-Review/2.0"


def norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).lower()


def terms(value: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for token in TOKEN_RE.findall(norm(value)):
        if token in STOPWORDS or token.startswith("ch-") or (token.isdigit() and len(token) < 4):
            continue
        if token not in seen:
            seen.add(token)
            out.append(token)
    return out


def query_for(question: str, max_terms: int = 8) -> tuple[str, list[str]]:
    cleaned = re.sub(r"\(\s*mã\s*ch-\d+\s*\)", " ", question, flags=re.IGNORECASE)
    question_terms = terms(cleaned)
    return " ".join(question_terms[:max_terms]), question_terms


def host_bonus(url: str) -> float:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith(".gov.vn") or host.endswith(".gov") or host.endswith(".edu.vn"):
        return 8.0
    if "wikipedia.org" in host or host.endswith(".edu"):
        return 5.0
    return 0.0


def valid_source(url: str) -> bool:
    parsed = urlparse(str(url or ""))
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and host not in SEARCH_HOSTS


def ddg_lookup(query: str, timeout: float) -> dict[str, Any]:
    if not query:
        return {"status": "NO_QUERY", "text": "", "url": "", "title": "", "related": []}
    try:
        timeout = max(3.0, float(timeout))
        command = [
            "curl", "-L", "--silent", "--show-error", "--compressed",
            "--connect-timeout", str(max(2, int(timeout / 2))),
            "--max-time", str(max(3, int(timeout))),
            "--user-agent", USER_AGENT,
            "--get", "https://api.duckduckgo.com/",
            "--data-urlencode", f"q={query}",
            "--data-urlencode", "format=json",
            "--data-urlencode", "no_html=1",
            "--data-urlencode", "skip_disambig=1",
            "--data-urlencode", "kl=vn-vn",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 5, check=False)
        if completed.returncode != 0:
            return {"status": "DDG_REQUEST_ERROR", "text": "", "url": "", "title": "", "related": [], "error": f"curl_exit_{completed.returncode}"}
        data = json.loads(completed.stdout)
        related: list[dict[str, Any]] = []
        for item in data.get("RelatedTopics") or []:
            if not isinstance(item, dict):
                continue
            if item.get("Topics"):
                related.extend(x for x in item.get("Topics") or [] if isinstance(x, dict))
            else:
                related.append(item)
        text_parts = [data.get("Heading", ""), data.get("AbstractText", "")]
        text_parts.extend(item.get("Text", "") for item in related)
        return {
            "status": "DDG_API_OK",
            "text": " ".join(str(x) for x in text_parts if x),
            "url": data.get("AbstractURL", "") or "",
            "title": data.get("Heading", "") or data.get("AbstractSource", ""),
            "related": related[:10],
            "abstract_source": data.get("AbstractSource", "") or "",
            "abstract_text": data.get("AbstractText", "") or "",
        }
    except subprocess.TimeoutExpired:
        return {"status": "DDG_TIMEOUT", "text": "", "url": "", "title": "", "related": [], "error": "TimeoutExpired"}
    except (ValueError, TypeError, KeyError) as exc:
        return {"status": "DDG_PARSE_ERROR", "text": "", "url": "", "title": "", "related": [], "error": type(exc).__name__}


def score_source(question_terms: list[str], text: str, url: str, title: str) -> dict[str, Any]:
    shared = sorted(set(question_terms) & set(terms(f"{title} {text} {url}")))
    count = len(shared)
    return {"shared_terms": shared, "shared_term_count": count, "coverage": round(count / max(1, len(question_terms)), 6), "source_bonus": host_bonus(url), "url": url, "title": title}


def process(row: dict[str, Any], canonical: dict[str, Any] | None, timeout: float, rate_limit: float) -> dict[str, Any]:
    question = str(row.get("question") or "")
    query, question_terms = query_for(question)
    ddg = ddg_lookup(query, timeout)
    if rate_limit > 0:
        time.sleep(rate_limit)
    canonical = canonical or {}
    ddg_score = score_source(question_terms, ddg.get("text", ""), ddg.get("url", ""), ddg.get("title", ""))
    canonical_url = canonical.get("final_url") or canonical.get("canonical_url") or ""
    canonical_score = score_source(question_terms, canonical.get("text_preview", ""), canonical_url, canonical.get("title", ""))
    ddg_usable = ddg_score["shared_term_count"] > 0 and valid_source(ddg_score["url"])
    if ddg_usable and (ddg_score["shared_term_count"], ddg_score["coverage"], ddg_score["source_bonus"]) >= (canonical_score["shared_term_count"], canonical_score["coverage"], canonical_score["source_bonus"]):
        chosen, chosen_source = ddg_score, "ddg_instant_answer"
    else:
        chosen, chosen_source = canonical_score, "canonical_fetch_existing" if valid_source(canonical_url) else "none"
    count = chosen["shared_term_count"]
    coverage = chosen["coverage"]
    return {
        "question_id": row.get("id") or row.get("question_id"),
        "question": question,
        "domain": row.get("domain", "general"),
        "short_query": query,
        "query_terms": question_terms,
        "ddg_status": ddg.get("status"),
        "ddg_title": ddg.get("title", ""),
        "ddg_url": ddg.get("url", ""),
        "ddg_abstract_source": ddg.get("abstract_source", ""),
        "ddg_abstract_text": ddg.get("abstract_text", ""),
        "canonical_url": canonical_url,
        "canonical_title": canonical.get("title", ""),
        "chosen_source": chosen_source,
        "chosen_url": chosen["url"],
        "chosen_title": chosen["title"],
        "shared_terms": chosen["shared_terms"],
        "shared_term_count": count,
        "coverage": coverage,
        "source_bonus": chosen["source_bonus"],
        "selection_score": round(count * 10 + coverage * 100 + chosen["source_bonus"] + (3 if chosen_source == "ddg_instant_answer" else 0), 6),
        "screening_status": "ELIGIBLE_PRE_REVIEW" if count >= 2 and coverage >= 0.20 and chosen_source != "none" else "REJECT_LOW_ALIGNMENT",
        "selected_for_review": False,
        "review_rank": None,
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    decoder = json.JSONDecoder()
    rows: list[dict[str, Any]] = []
    index = 0
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            break
        value, end = decoder.raw_decode(text, index)
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSON record in {path} at offset {index}")
        rows.append(value)
        index = end
    return rows


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")
    os.replace(temporary, path)


def append_progress(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()


def build_outputs(args: argparse.Namespace, screening: list[dict[str, Any]], review_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in screening if row["screening_status"] == "ELIGIBLE_PRE_REVIEW"]
    eligible.sort(key=lambda row: (row["selection_score"], row["shared_term_count"], row["coverage"], str(row["question_id"])), reverse=True)
    selected = eligible[: args.review_size]
    for rank, row in enumerate(selected, start=1):
        row["selected_for_review"] = True
        row["review_rank"] = rank
    queue: list[dict[str, Any]] = []
    for row in selected:
        base = dict(review_by_id.get(str(row["question_id"]), {}))
        base.update({
            "question_id": row["question_id"], "question": row["question"], "domain": row["domain"],
            "candidate_alignment_shared_term_count": row["shared_term_count"], "candidate_alignment_shared_terms": row["shared_terms"],
            "candidate_alignment_coverage": row["coverage"], "candidate_alignment_selection_score": row["selection_score"],
            "candidate_alignment_short_query": row["short_query"], "candidate_alignment_source": row["chosen_source"],
            "candidate_alignment_source_url": row["chosen_url"], "candidate_alignment_source_title": row["chosen_title"],
            "candidate_ddg_status": row["ddg_status"], "candidate_ddg_abstract_source": row["ddg_abstract_source"],
            "candidate_ddg_abstract_text": row["ddg_abstract_text"], "gold_chunk_ids": base.get("gold_chunk_ids") or [],
            "gold_answer": base.get("gold_answer") or "", "gold_status": "SOURCE_FETCHED_NOT_REVIEWED",
            "review_method": "human_review_after_ddg_short_alignment",
            "reviewer_notes": "Short DDG query plus shared_term_count is only a pre-review screen; reviewer must verify direct support, gold chunk IDs and gold answer independently.",
        })
        queue.append(base)
    args.screening_output.parent.mkdir(parents=True, exist_ok=True)
    args.queue_output.parent.mkdir(parents=True, exist_ok=True)
    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    atomic_jsonl(args.screening_output, screening)
    atomic_jsonl(args.queue_output, queue)
    csv_fields = ["question_id", "question", "domain", "candidate_alignment_shared_term_count", "candidate_alignment_shared_terms", "candidate_alignment_coverage", "candidate_alignment_selection_score", "candidate_alignment_short_query", "candidate_alignment_source", "candidate_alignment_source_url", "candidate_alignment_source_title", "candidate_ddg_status", "candidate_ddg_abstract_source", "candidate_ddg_abstract_text", "gold_chunk_ids", "gold_answer", "gold_status", "review_method", "reviewer_notes"]
    with args.csv_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for row in queue:
            writer.writerow({field: json.dumps(row.get(field), ensure_ascii=False) if isinstance(row.get(field), (list, dict)) else row.get(field, "") for field in csv_fields})
    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "questions_in_input": len(screening),
        "start_offset": args.start_offset, "limit": args.limit, "ddg_api_ok": sum(row["ddg_status"] == "DDG_API_OK" for row in screening),
        "eligible_pre_review": len(eligible), "selected_for_review": len(selected), "review_size_target": args.review_size,
        "selection_cutoff_score": selected[-1]["selection_score"] if selected else None,
        "selection_cutoff_shared_term_count": selected[-1]["shared_term_count"] if selected else None,
        "min_screen_shared_term_count": 2, "min_screen_coverage": 0.20,
        "execution_mode": "sequential_curl_ddg_instant_answer", "ddg_html_note": "DDG HTML endpoint was bot-challenged; DDG Instant Answer API was used for short queries. Rows without usable DDG API result may use existing canonical fetch.",
        "checkpoint_output": str(args.checkpoint_output), "progress_output": str(args.progress_output),
        "output_screening": str(args.screening_output), "output_queue": str(args.queue_output), "output_csv": str(args.csv_output),
    }
    args.summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument("--screening-output", type=Path, required=True)
    parser.add_argument("--queue-output", type=Path, required=True)
    parser.add_argument("--csv-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--checkpoint-output", type=Path)
    parser.add_argument("--progress-output", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--rate-limit", type=float, default=0.20)
    parser.add_argument("--review-size", type=int, default=200)
    parser.add_argument("--limit", type=int, default=0, help="bounded number of input rows; 0 means to end")
    parser.add_argument("--start-offset", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.workers != 1:
        raise SystemExit("fail-closed: use --workers 1 for rate-limited DDG mode")
    if args.start_offset < 0 or args.limit < 0:
        raise SystemExit("start-offset and limit must be non-negative")
    args.checkpoint_output = args.checkpoint_output or args.screening_output.with_name(args.screening_output.name + ".checkpoint.jsonl")
    args.progress_output = args.progress_output or args.screening_output.with_name(args.screening_output.name + ".progress.jsonl")
    questions = load_jsonl(args.questions)
    canonical_by_id = {str(row.get("question_id")): row for row in load_jsonl(args.canonical)}
    review_by_id = {str(row.get("question_id")): row for row in load_jsonl(args.review_queue)}
    end = len(questions) if args.limit == 0 else min(len(questions), args.start_offset + args.limit)
    if args.start_offset > len(questions):
        raise SystemExit("start-offset is beyond input length")
    prior: dict[str, dict[str, Any]] = {}
    if args.resume and args.checkpoint_output.exists():
        prior = {str(row.get("question_id")): row for row in load_jsonl(args.checkpoint_output)}
    screening: list[dict[str, Any]] = []
    for index in range(args.start_offset, end):
        source_row = questions[index]
        question_id = str(source_row.get("id") or source_row.get("question_id"))
        row = prior.get(question_id)
        if row is None:
            row = process(source_row, canonical_by_id.get(question_id), args.timeout, args.rate_limit)
            append_progress(args.progress_output, {"input_index": index, "question_id": row["question_id"], "ddg_status": row["ddg_status"], "shared_term_count": row["shared_term_count"], "coverage": row["coverage"], "completed": index - args.start_offset + 1, "slice_end": end})
        screening.append(row)
        atomic_jsonl(args.checkpoint_output, screening)
    summary = build_outputs(args, screening, review_by_id)
    summary["checkpoint_complete"] = len(screening) == end - args.start_offset
    args.summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
