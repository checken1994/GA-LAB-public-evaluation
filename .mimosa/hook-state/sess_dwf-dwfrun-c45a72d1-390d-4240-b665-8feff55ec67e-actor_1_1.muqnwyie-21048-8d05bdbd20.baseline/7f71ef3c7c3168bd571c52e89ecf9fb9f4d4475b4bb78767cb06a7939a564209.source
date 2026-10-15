"""Index parts package — extracted from `brain/error_store_index.py` in Task 10-B.

Sub-modules:
  - similarity: TF-IDF cosine similarity + O(log k) search_sync core.
  - clustering: Vietnamese-safe tokenization + inverted-index builder.
  - retrieval:  async search/check_against_history/get_error_lessons/stats
                 + smoke-test data generators.

All public symbols re-exported here — backward compatible with error_store_index.py.
"""
from scp.brain.index_parts.clustering import (
    _STOPWORDS,
    _TOKEN_RE,
    ERRORSTORE_MAX_SIZE,
    build_index,
    error_text,
    load,
    make_error,
    persist_append,
    rebuild_index,
    tokenize,
    trim,
)
from scp.brain.index_parts.retrieval import (
    _CONTEXT_WORDS,
    _DOMAIN_ENTITIES,
    _SEVERITY_RANK,
    _TEST_DOMAINS,
    _TEST_ERROR_TYPES,
    _TEST_SEVERITIES,
    check_against_history,
    gen_test_errors,
    get_error_lessons,
    rebuild_index_async,
    search_similar,
    stats,
)
from scp.brain.index_parts.similarity import (
    DEFAULT_TOP_K,
    MAX_DF_RATIO,
    MAX_FULL_CANDIDATES,
    MAX_POSTINGS_PER_KEYWORD,
    SIMILARITY_FLOOR,
    compute_tfidf,
    cosine_similarity,
    search_sync,
)

__all__ = [
    # similarity
    "DEFAULT_TOP_K",
    "SIMILARITY_FLOOR",
    "MAX_FULL_CANDIDATES",
    "MAX_DF_RATIO",
    "MAX_POSTINGS_PER_KEYWORD",
    "cosine_similarity",
    "compute_tfidf",
    "search_sync",
    # clustering
    "ERRORSTORE_MAX_SIZE",
    "_TOKEN_RE",
    "_STOPWORDS",
    "tokenize",
    "error_text",
    "make_error",
    "build_index",
    "rebuild_index",
    "trim",
    "load",
    "persist_append",
    # retrieval
    "search_similar",
    "check_against_history",
    "get_error_lessons",
    "stats",
    "rebuild_index_async",
    "gen_test_errors",
    "_SEVERITY_RANK",
    "_TEST_DOMAINS",
    "_TEST_ERROR_TYPES",
    "_TEST_SEVERITIES",
    "_DOMAIN_ENTITIES",
    "_CONTEXT_WORDS",
]
