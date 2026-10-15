"""
Similarity search — TF-IDF + cosine similarity + inverted-index retrieval.

Pure-Python stdlib implementation for O(log k) similarity search against
up to 50K ErrorStore records.

Functions:
  - cosine_similarity(vec_a, vec_b): cosine of two sparse TF-IDF vectors.
  - compute_tfidf(tokens, document_freq, total_docs): build sparse TF-IDF vector.
  - search_sync(index, query, top_k, domain, limit): synchronous core of
    async search_similar — two-stage retrieval (inverted index → cosine).

Constants:
  - DEFAULT_TOP_K, SIMILARITY_FLOOR, MAX_FULL_CANDIDATES,
    MAX_DF_RATIO, MAX_POSTINGS_PER_KEYWORD

Extracted from `brain/error_store_index.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

import logging
import math
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

# Similarity-search tuning constants
DEFAULT_TOP_K: int = 5                      # default results per search
SIMILARITY_FLOOR: float = 0.05              # below this -> not "similar"
MAX_FULL_CANDIDATES: int = 500              # above this, pre-rank by keyword overlap
MAX_DF_RATIO: float = 0.20                  # skip keywords in >20% of docs (overly common)
MAX_POSTINGS_PER_KEYWORD: int = 1_500       # cap posting iteration per keyword (avoids O(n) blowup)


def cosine_similarity(
    vec_a: dict[str, float], vec_b: dict[str, float]
) -> float:
    """Cosine similarity between two sparse TF-IDF vectors (dicts).

    Only iterates over the smaller vector's keys for efficiency.
    Returns 0.0 if either vector is empty (safe default).
    """
    if not vec_a or not vec_b:
        return 0.0
    # Iterate over the smaller dict to minimize work.
    if len(vec_a) > len(vec_b):
        vec_a, vec_b = vec_b, vec_a
    dot = 0.0
    for key, val in vec_a.items():
        other = vec_b.get(key)
        if other is not None:
            dot += val * other
    if dot == 0.0:
        return 0.0
    # Magnitudes are precomputed and stored under key "" — but to keep
    # the public dict clean we compute them on the fly. For 50K records
    # this is still fast because vectors are sparse.
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def compute_tfidf(
    tokens: list[str],
    document_freq: dict[str, int],
    total_docs: int | None = None,
    max_df_ratio: float = MAX_DF_RATIO,
) -> dict[str, float]:
    """Compute the TF-IDF sparse vector for a token list.

    TF  = count(term) / total_terms_in_doc
    IDF = log(1 + N / (1 + df(term)))   (smoothed)

    Keywords appearing in more than max_df_ratio of all documents are
    excluded — they are not discriminative and only bloat the vectors.
    """
    if not tokens:
        return {}
    n = total_docs if total_docs is not None else 1
    max_df = n * max_df_ratio
    tf = Counter(tokens)
    total = len(tokens)
    vec: dict[str, float] = {}
    for term, count in tf.items():
        df = document_freq.get(term, 0)
        if df > max_df:
            continue  # overly common — not discriminative
        idf = math.log(1.0 + n / (1.0 + df))
        vec[term] = (count / total) * idf
    return vec


def search_sync(
    index,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    domain: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Synchronous core of search_similar (called under lock).

    Two-stage retrieval for O(log k) performance on large stores:
      1. Inverted index -> candidate set (docs sharing >=1 keyword).
      2. If candidate set exceeds MAX_FULL_CANDIDATES, pre-rank by
         keyword-overlap count and keep only the top candidates.
      3. Full TF-IDF cosine similarity (using precomputed magnitudes)
         over the (possibly trimmed) candidate set.

    [V104.50 #P1-10] `limit` accepted as deprecated alias for `top_k`
    (judge.py calls `_search_sync(question, limit=3)` directly when the
    event loop is running). If both are given, `limit` wins.
    """
    if limit is not None:
        top_k = limit
    if not index.errors:
        return []
    # Local import to avoid circular dependency at module load time.
    from scp.brain.index_parts.clustering import tokenize
    query_tokens = tokenize(query)
    if not query_tokens:
        return []
    query_terms = set(query_tokens)

    # --- Stage 1: gather candidate doc ids from inverted index ---
    # Track keyword overlap per candidate for stage 2 pre-ranking.
    # Skip overly common keywords (df > MAX_DF_RATIO * N) — they are
    # not discriminative and would balloon the candidate set to ~all
    # documents, defeating the O(log k) purpose of the inverted index.
    # Also cap postings processed per keyword (MAX_POSTINGS_PER_KEYWORD)
    # so that a single common keyword cannot dominate search latency.
    n_docs = len(index.errors)
    max_df = n_docs * MAX_DF_RATIO
    overlap_counts: dict[int, int] = defaultdict(int)
    for tok in query_terms:
        df_tok = index.document_freq.get(tok, 0)
        if df_tok == 0 or df_tok > max_df:
            continue  # not in index, or overly common — skip
        postings = index.inverted_index.get(tok)
        if not postings:
            continue
        # Cap posting iteration to bound worst-case latency.
        if len(postings) > MAX_POSTINGS_PER_KEYWORD:
            postings = postings[:MAX_POSTINGS_PER_KEYWORD]
        for pid in postings:
            overlap_counts[pid] += 1

    if not overlap_counts:
        return []

    # --- Stage 2: if too many candidates, pre-rank by overlap ---
    candidate_ids: list[int]
    if len(overlap_counts) > MAX_FULL_CANDIDATES:
        # Keep docs sharing the most keywords with the query.
        # Ties broken by doc id (smaller = older = more established).
        ranked = sorted(
            overlap_counts.items(),
            key=lambda kv: (-kv[1], kv[0]),
        )
        candidate_ids = [
            pid for pid, _ in ranked[:MAX_FULL_CANDIDATES]
        ]
    else:
        candidate_ids = list(overlap_counts.keys())

    # --- Stage 3: full TF-IDF cosine similarity ---
    # Compute query vector + magnitude once.
    query_vec = compute_tfidf(query_tokens, index.document_freq, total_docs=n_docs)
    query_mag = math.sqrt(sum(v * v for v in query_vec.values()))
    if query_mag == 0.0:
        return []

    # Pre-bind locals for the hot loop (avoids self.* attribute lookups).
    tfidf_vectors = index.tfidf_vectors
    magnitudes = index._magnitudes
    errors_list = index.errors
    n_vecs = len(tfidf_vectors)
    n_mags = len(magnitudes)
    qvec_get = query_vec.get
    qvec_items = query_vec.items()
    qvec_len = len(query_vec)
    floor = SIMILARITY_FLOOR

    scored: list[tuple[float, int]] = []
    scored_append = scored.append
    for idx in candidate_ids:
        if idx >= n_vecs:
            continue
        if domain is not None:
            if errors_list[idx].get("domain", "") != domain:
                continue
        doc_vec = tfidf_vectors[idx]
        if not doc_vec:
            continue
        # Use precomputed magnitude (falls back to inline if missing).
        doc_mag = magnitudes[idx] if idx < n_mags else 0.0
        if doc_mag == 0.0:
            doc_mag = math.sqrt(sum(v * v for v in doc_vec.values()))
            if doc_mag == 0.0:
                continue
        # Inline dot product — iterate over the smaller vector.
        if qvec_len <= len(doc_vec):
            dot = 0.0
            doc_get = doc_vec.get
            for key, val in qvec_items:
                other = doc_get(key)
                if other is not None:
                    dot += val * other
        else:
            dot = 0.0
            for key, val in doc_vec.items():
                other = qvec_get(key)
                if other is not None:
                    dot += val * other
        if dot == 0.0:
            continue
        sim = dot / (query_mag * doc_mag)
        if sim >= floor:
            scored_append((sim, idx))

    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    top = scored[:top_k]
    # [V104.50 #P1-10] Return shape: keep the historical keys
    # (error, similarity, lesson, error_id) AND add `question` +
    # `verdict` so consumers that do `s.get("question")` /
    # `s.get("verdict")` (e.g. scp/runtime/judge.py:1437,1441) get a
    # non-empty value instead of "". Both new keys source from the
    # underlying error record and fall back to "" when absent.
    return [
        {
            "error": index.errors[idx],
            "similarity": round(sim, 4),
            "lesson": index.errors[idx].get("lesson", ""),
            "error_id": index.errors[idx].get("error_id", idx),
            "question": index.errors[idx].get("question", ""),
            "verdict": index.errors[idx].get("verdict", ""),
        }
        for sim, idx in top
    ]
