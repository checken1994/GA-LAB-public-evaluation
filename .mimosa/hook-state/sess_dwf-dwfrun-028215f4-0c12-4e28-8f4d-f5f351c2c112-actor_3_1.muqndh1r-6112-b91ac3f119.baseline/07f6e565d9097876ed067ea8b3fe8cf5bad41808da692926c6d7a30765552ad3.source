"""
Clustering / Indexing — Vietnamese-safe tokenization + inverted-index builder.

Pure-Python stdlib implementation:
  - tokenize(text): Vietnamese-safe, lowercase, stopword-filtered.
  - build_index(index): build inverted index + TF-IDF vectors for all errors.
  - rebuild_index(index): rebuild from scratch (after trim).
  - trim(index): FIFO-trim oldest errors, rebuild index after.
  - make_error(...): build canonical error record dict.

Constants:
  - ERRORSTORE_MAX_SIZE, _TOKEN_RE, _STOPWORDS

Extracted from `brain/error_store_index.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

import json
import logging
import math
import re
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ErrorStore capacity ceiling (auto-trim when exceeded)
ERRORSTORE_MAX_SIZE: int = 50_000

# Vietnamese-safe tokenization
# Match runs of Unicode letters (preserves Vietnamese diacritics, excludes
# digits and underscores). re.UNICODE is default in Python 3 for str patterns.
_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# A small bilingual stopword list. Keeping it small avoids over-filtering
# domain terms (e.g. "không" can be meaningful in "không an toàn").
_STOPWORDS: frozenset = frozenset({
    # English
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "of", "in", "on",
    "at", "to", "for", "with", "by", "from", "as", "and", "or", "but",
    "not", "no", "if", "then", "this", "that", "these", "those", "it",
    "its", "i", "you", "he", "she", "we", "they", "what", "which", "who",
    "reported", "real", "actual", "vs", # Vietnamese (common function words only)
    "của", "và", "là", "có", "trong", "một", "các", "những", "được",
    "cho", "với", "không", "này", "về", "từ", "đến", "để", "theo",
    "khi", "như", "cũng", "đã", "sẽ", "đang", "mà", "ở", "nên",
    # Common lesson boilerplate (appears in every error record)
    "verify", "before", "answering", "lesson", "tags", "context",
})


def tokenize(text: str) -> list[str]:
    """Tokenize text: lowercase, split on non-letters, filter stopwords.

    Vietnamese-safe: diacritics are preserved because _TOKEN_RE matches
    Unicode letter runs. "FPT doanh thu 62 tỷ" -> ["fpt", "doanh", "thu", "tỷ"].
    """
    if not text:
        return []
    tokens: list[str] = []
    for m in _TOKEN_RE.finditer(str(text).lower()):
        tok = m.group(0)
        if len(tok) < 2:           # drop single-char tokens (noise)
            continue
        if tok in _STOPWORDS:
            continue
        tokens.append(tok)
    return tokens


def error_text(error: dict) -> str:
    """Concatenate the searchable text of an error record."""
    parts = [
        str(error.get("question", "")),
        str(error.get("llm_answer", "")),
        str(error.get("error_type", "")),
        str(error.get("domain", "")),
        str(error.get("lesson", "")),
    ]
    return " ".join(p for p in parts if p)


def make_error(
    error_id: int,
    question: str,
    llm_answer: str,
    error_type: str,
    domain: str,
    severity: str,
    lesson: str,
    timestamp: str | None = None,
) -> dict:
    """Build a canonical error record dict."""
    return {
        "error_id": error_id,
        "question": question,
        "llm_answer": llm_answer,
        "error_type": error_type,
        "domain": domain,
        "severity": severity,
        "lesson": lesson,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
    }


def build_index(index) -> None:
    """Build inverted index + TF-IDF vectors for all loaded errors.

    - Tokenize each error: question + error_type + domain + lesson
    - Build inverted index: keyword -> [error_ids]
    - Compute TF-IDF for each error
    - O(n) build, then O(log k) lookup where k = matching docs

    Mutates `index` in place: inverted_index, document_freq, tfidf_vectors,
    _magnitudes.
    """
    from scp.brain.index_parts.similarity import compute_tfidf

    index.inverted_index = defaultdict(list)
    index.document_freq = defaultdict(int)
    index.tfidf_vectors = []
    index._magnitudes = []

    n = len(index.errors)
    if n == 0:
        return

    # Pass 1: tokenize, populate inverted index + document frequency.
    per_doc_tokens: list[list[str]] = []
    for idx, error in enumerate(index.errors):
        tokens = tokenize(error_text(error))
        per_doc_tokens.append(tokens)
        seen = set(tokens)
        for tok in seen:
            index.document_freq[tok] += 1
            index.inverted_index[tok].append(idx)

    # Pass 2: compute TF-IDF for each document.
    for tokens in per_doc_tokens:
        vec = compute_tfidf(tokens, index.document_freq, total_docs=n)
        index.tfidf_vectors.append(vec)
        mag = math.sqrt(sum(v * v for v in vec.values()))
        index._magnitudes.append(mag)

    logger.info(
        "ErrorStoreIndex built: %d errors, %d unique keywords",
        n, len(index.document_freq),
    )


def rebuild_index(index) -> None:
    """Rebuild inverted index + TF-IDF vectors + magnitudes from scratch.

    [V104.50 #P1-10] Thin wrapper around build_index() — extracted as
    a named method so callers (notably _trim) express intent clearly
    and so the rebuild path has a single place to hook diagnostics.
    Safe to call repeatedly; O(n) cost.
    """
    try:
        build_index(index)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("_rebuild_index failed: %s", exc, exc_info=True)
        # Mark dirty so callers know the index may be inconsistent.
        index._index_dirty = True


def trim(index) -> None:
    """FIFO-trim the oldest errors when over ERRORSTORE_MAX_SIZE.

    [V104.50 #P1-10] CRITICAL: pop(0) on `index.errors` shifts every
    subsequent element down by one index, but the inverted_index held
    the OLD positions (e.g. inverted_index[tok] = [5, 10, 20] would
    point at docs 4, 9, 19 after a single pop). Without a rebuild,
    search_similar returned WRONG documents after every trim.
    Fix: after popping, rebuild the entire inverted index + TF-IDF
    vectors + magnitudes from scratch via rebuild_index().

    Must be called under index._lock (the asyncio.Lock from add()).
    """
    trimmed = 0
    while len(index.errors) > ERRORSTORE_MAX_SIZE:
        index.errors.pop(0)
        index.tfidf_vectors.pop(0)
        index._magnitudes.pop(0)
        trimmed += 1
    if trimmed > 0:
        rebuild_index(index)
        index._index_dirty = False  # rebuilt — no longer stale


def load(index) -> None:
    """Load errors from JSONL. Each line is one JSON object.

    [V104.50 #P1-10] After loading, seed `_next_id` from the maximum
    `error_id` present on disk so a process restart does NOT reset the
    counter to 0 (which would re-issue ids already on disk and create
    duplicate-id records). This makes the V104.34 #44 monotonic-counter
    fix actually durable across restarts without needing a separate
    counter file.
    """
    if not index.store_path.exists():
        logger.info("ErrorStore file not found at %s — starting empty.", index.store_path)
        return
    max_loaded_id: int = 0
    with index.store_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if isinstance(record, dict):
                    index.errors.append(record)
                    # Track the highest error_id seen so _next_id can be
                    # seeded above it (handles int ids; non-int ids ignored).
                    _eid = record.get("error_id")
                    if isinstance(_eid, int) and _eid > max_loaded_id:
                        max_loaded_id = _eid
            except json.JSONDecodeError as exc:
                logger.debug("Skipping malformed JSONL line: %s", exc)
                continue
    index._next_id = max_loaded_id
    logger.info(
        "ErrorStore loaded %d records from %s (next_id seeded to %d)",
        len(index.errors), index.store_path, index._next_id,
    )


def persist_append(index, error: dict) -> None:
    """Append a single error to the JSONL file (best-effort)."""
    try:
        index.store_path.parent.mkdir(parents=True, exist_ok=True)
        with index.store_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(error, ensure_ascii=False) + "\n")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("ErrorStore append failed (in-memory only): %s", exc, exc_info=True)
