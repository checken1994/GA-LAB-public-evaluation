"""
Retrieval — async search/check_against_history/get_error_lessons/stats + smoke test data.

Functions (async unless noted):
  - search_similar(index, query, top_k, domain, limit): O(log k) similarity search.
  - check_against_history(index, question, llm_answer): match against past errors.
  - get_error_lessons(index, domain, limit): top-severity lessons (sync).
  - stats(index): aggregate store stats (sync).
  - rebuild_index_async(index): rebuild inverted index + TF-IDF from scratch.

Smoke-test helpers (sync):
  - gen_test_errors(n): generate n varied test error records.
  - smoke_test(): exercise every public method of ErrorStoreIndex.

Extracted from `brain/error_store_index.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict

from scp.brain.index_parts.clustering import (
    ERRORSTORE_MAX_SIZE,
    make_error,
)
from scp.brain.index_parts.similarity import (
    DEFAULT_TOP_K,
    search_sync,
)

logger = logging.getLogger(__name__)


async def search_similar(
    index,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    domain: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Find similar past errors — O(log k) via inverted index.

    1. Tokenize query.
    2. Get candidate docs from inverted index (docs sharing keywords).
    3. Compute cosine similarity with TF-IDF vectors.
    4. Return top_k most similar.

    This is the KEY operation: when V4 processes a new question, it
    checks "have I made a similar mistake before?"

    [V104.50 #P1-10] `limit` is accepted as a DEPRECATED alias for
    `top_k` to remain compatible with callers that pass `limit=`
    (e.g. scp/runtime/judge.py:1430,1434). If both are given, `limit`
    wins (caller explicitness). `top_k` remains the canonical param.
    """
    if limit is not None:
        top_k = limit
    t0 = time.perf_counter()
    try:
        async with index._lock:
            results = search_sync(index, query, top_k, domain)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("search_similar failed: %s", exc, exc_info=True)
        results = []
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    index._search_latencies.append(elapsed_ms)
    # Cap latency history to avoid unbounded growth.
    if len(index._search_latencies) > 1000:
        index._search_latencies = index._search_latencies[-500:]
    return results


async def check_against_history(
    index, question: str, llm_answer: str
) -> dict:
    """Check if this Q&A matches any known past error.

    Returns
    -------
    dict
        {
            has_similar_error: bool,
            similar_errors: [{error, similarity, lesson}],
            recommendation: str,  # "caution: similar to past error #1234"
        }
    """
    try:
        query = f"{question} {llm_answer}"
        similar = await search_similar(index, query, top_k=DEFAULT_TOP_K)
        has_similar = len(similar) > 0
        if has_similar:
            top = similar[0]
            recommendation = (
                f"CAUTION: similar to past error #{top['error_id']} "
                f"(similarity={top['similarity']:.2f}). "
                f"Lesson: {top.get('lesson', 'review required')}"
            )
        else:
            recommendation = (
                "No similar past error found within current scope — "
                "V4 still cannot guarantee safety."
            )
        return {
            "has_similar_error": has_similar,
            "similar_errors": similar,
            "recommendation": recommendation,
        }
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("check_against_history failed: %s", exc, exc_info=True)
        return {
            "has_similar_error": False,
            "similar_errors": [],
            "recommendation": "history check failed — proceed with caution",
        }


_SEVERITY_RANK: dict[str, int] = {
    "CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1,
}


def get_error_lessons(
    index, domain: str | None = None, limit: int = 10
) -> list[dict]:
    """Get the most important error lessons (highest severity, most recent).

    These are V4's 'scars' — reminders of past mistakes.
    """
    try:
        pool = index.errors
        if domain is not None:
            pool = [e for e in pool if e.get("domain") == domain]
        ranked = sorted(
            pool,
            key=lambda e: (
                -_SEVERITY_RANK.get(
                    str(e.get("severity", "")).upper(), 0
                ),
                e.get("timestamp", ""),
            ),
            reverse=False,
        )
        # We sorted by (-severity, timestamp) ascending, so highest
        # severity comes first; among equal severity, the most recent
        # timestamp (lexicographically largest) should come first, so
        # we reverse the timestamp comparison. Easiest: reverse list
        # then sort stably by severity only.
        ranked.sort(
            key=lambda e: -_SEVERITY_RANK.get(
                str(e.get("severity", "")).upper(), 0
            ),
        )
        return [
            {
                "error_id": e.get("error_id", idx),
                "domain": e.get("domain", ""),
                "severity": e.get("severity", ""),
                "lesson": e.get("lesson", ""),
                "timestamp": e.get("timestamp", ""),
            }
            for idx, e in enumerate(ranked[:limit])
        ]
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("get_error_lessons failed: %s", exc, exc_info=True)
        return []


def stats(index) -> dict:
    """Return aggregate stats about the ErrorStore."""
    try:
        by_domain: dict[str, int] = defaultdict(int)
        by_error_type: dict[str, int] = defaultdict(int)
        for e in index.errors:
            by_domain[e.get("domain", "unknown")] += 1
            by_error_type[e.get("error_type", "unknown")] += 1

        avg_ms = 0.0
        if index._search_latencies:
            avg_ms = sum(index._search_latencies) / len(index._search_latencies)

        coverage_pct = 100.0
        if ERRORSTORE_MAX_SIZE > 0:
            coverage_pct = round(
                100.0 * len(index.errors) / ERRORSTORE_MAX_SIZE, 2
            )

        return {
            "total_errors": len(index.errors),
            "by_domain": dict(by_domain),
            "by_error_type": dict(by_error_type),
            "index_size": len(index.document_freq),
            "avg_search_time_ms": round(avg_ms, 4),
            "max_search_time_ms": round(
                max(index._search_latencies) if index._search_latencies else 0.0,
                4,
            ),
            "coverage": f"{coverage_pct}% of {ERRORSTORE_MAX_SIZE} capacity",
        }
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("stats failed: %s", exc, exc_info=True)
        return {
            "total_errors": 0,
            "by_domain": {},
            "by_error_type": {},
            "index_size": 0,
            "avg_search_time_ms": 0.0,
            "coverage": "stats failed",
        }


async def rebuild_index_async(index) -> dict:
    """Rebuild the inverted index + TF-IDF from scratch.

    Call after bulk updates, trims, or external file edits to
    compact stale postings and refresh IDF values.
    """
    from scp.brain.index_parts.clustering import build_index
    async with index._lock:
        try:
            t0 = time.perf_counter()
            build_index(index)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "rebuilt": True,
                "total_errors": len(index.errors),
                "index_size": len(index.document_freq),
                "build_time_ms": round(elapsed_ms, 4),
            }
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("rebuild_index failed: %s", exc, exc_info=True)
            return {"rebuilt": False, "error": str(exc)}


# ============================================================
# SMOKE TEST DATA (used by _smoke_test() below)
# ============================================================

_TEST_DOMAINS: list[str] = [
    "finance", "medical", "legal", "tech", "general",
    "cybersecurity", "ecommerce", "education", "news", "science",
]

_TEST_ERROR_TYPES: list[str] = [
    "hallucination", "contradiction", "outdated_fact", "numeric_error",
    "citation_error", "entity_confusion", "temporal_error",
    "scope_violation", "safety_breach", "pattern_match",
]

_TEST_SEVERITIES: list[str] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Per-domain entity pools (diverse vocabulary -> effective inverted index).
_DOMAIN_ENTITIES: dict[str, list[str]] = {
    "finance": [
        "FPT", "Vingroup", "Vinamilk", "Masan", "HoaPhat", "Techcombank",
        "Vietcombank", "BIDV", "Vietjet", "Sabeco", "VPBank", "MBBank",
        "ACB", "TPBank", "HDBank", "PNJ", "MobileWorld", "PhuNhuan",
        "BambooCapital", "GELEX",
    ],
    "medical": [
        "paracetamol", "ibuprofen", "amoxicillin", "metformin", "atorvastatin",
        "omeprazole", "loratadine", "aspirin", "warfarin", "insulin",
        "prednisone", "diazepam", "morphine", "heparin", "furosemide",
        "enalapril", "amlodipine", "rosuvastatin", "cetirizine", "naproxen",
    ],
    "legal": [
        "boiluatdansu", "luatdatochinh", "luatlaodong", "luathinhsu",
        "luatthuongmai", "luatdautu", "luatbando", "luatmoitruong",
        "luatkiemtoan", "luatphasan", "nghidinh", "thongtu", "nghiquyet",
        "chiuthutuong", "quyetdinh", "congvan", "hiepdinh", "dieuluat",
        "dieu", "khoan",
    ],
    "cybersecurity": [
        "CVE2023", "CVE2024", "CVE2025", "CVE2026", "log4shell",
        "shellshock", "heartbleed", "meltdown", "spectre", "eternalblue",
        "wannacry", "petya", "solwar", "spring4shell", "proxylogon",
        "log4j", "apache", "nginx", "openssl", "tomcat",
    ],
    "ecommerce": [
        "shopee", "lazada", "tiki", "sendo", "adayroi", "fptshop",
        "nguyenkim", "dienmayxanh", "cellphones", "thegioididong",
        "phukien", "dien thoai", "laptop", "may tinh", "tablet",
        "phu kien", "mayanh", "dongho", "tainghe", "loa",
    ],
    "news": [
        "baochinhphu", "vnexpress", "tuoitre", "thanhnien", "dantri",
        "vietnamnet", "zingnews", "nhandan", "baomoi", "cafef",
        "kenh14", "vov", "vtv", "tintuc", "anninh",
        "doisongphapluat", "laodong", "phapluat", "congly", "baochauau",
    ],
    "science": [
        "newton", "einstein", "bohr", "planck", "schrodinger",
        "maxwell", "faraday", "tesla", "curie", "hawking",
        "speedoflight", "gravity", "quantum", "relativity", "entropy",
        "thermodynamics", "electromagnetism", "evolution", "genetics", "crispr",
    ],
    "tech": [
        "python", "javascript", "golang", "rust", "java",
        "react", "vue", "angular", "svelte", "nextjs",
        "docker", "kubernetes", "terraform", "ansible", "jenkins",
        "postgresql", "mongodb", "redis", "elasticsearch", "kafka",
    ],
}

# Context/topic words mixed into each error for vocabulary diversity.
_CONTEXT_WORDS: list[str] = [
    "analysis", "report", "dashboard", "summary", "overview", "brief",
    "review", "assessment", "evaluation", "benchmark", "metric", "kpi",
    "quarterly", "annual", "monthly", "weekly", "daily", "realtime",
    "batch", "stream", "pipeline", "workflow", "process", "procedure",
    "policy", "standard", "guideline", "framework", "blueprint", "schema",
    "archive", "backup", "snapshot", "checkpoint", "milestone", "deliverable",
    "incident", "anomaly", "alert", "warning", "critical", "urgent",
    "confirmed", "verified", "validated", "rejected", "approved", "pending",
    "draft", "final", "revised", "updated", "deprecated", "legacy",
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta",
    "eta", "theta", "iota", "kappa", "lambda", "mu",
    "nu", "xi", "omicron", "pi", "rho", "sigma",
    "tau", "upsilon", "phi", "chi", "psi", "omega",
]


def gen_test_errors(n: int = 100) -> list[dict]:
    """Generate n varied test error records across all domains.

    Uses diverse per-domain entity names + random context words so the
    inverted index has thousands of unique keywords (realistic scenario).
    This ensures search_similar achieves O(log k) with small candidate
    sets rather than degrading to O(n).
    """
    import random
    # [B311 documented exception] Seeded PRNG is REQUIRED here: the smoke
    # test contract demands reproducible candidate sampling (SystemRandom
    # cannot be seeded). No secret/token ever derives from this sampling.
    rng = random.Random(42)  # nosec B311 — seeded PRNG REQUIRED: reproducible smoke-test contract; no secret derives from this sampling
    errors: list[dict] = []

    domains = list(_DOMAIN_ENTITIES.keys())

    # Per-domain question templates (entity-agnostic; entity filled in).
    templates_by_domain: dict[str, list[str]] = {
        "finance": [
            "{entity} revenue {val} tỷ reported but real was {real} tỷ",
            "{entity} quarterly profit margin {val}% vs actual {real}%",
            "{entity} stock price {val}k VND contradicted by exchange {real}k",
        ],
        "medical": [
            "{entity} dosage {val}mg vs safe range {real}mg for adult",
            "{entity} contraindication in pregnancy category {val}",
            "{entity} side effect frequency {val}% vs clinical trial {real}%",
        ],
        "legal": [
            "{entity} citation article {val} does not exist in code",
            "{entity} penalty clause {val} vs statutory {real}",
            "{entity} procedure deadline {val} days vs legal {real} days",
        ],
        "cybersecurity": [
            "{entity} vulnerability CVSS score {val} vs actual {real}",
            "{entity} exploit affected systems {val} vs confirmed {real}",
            "{entity} patch severity {val} vs NVD rating {real}",
        ],
        "ecommerce": [
            "{entity} product price {val}k VND vs listing {real}k",
            "{entity} discount {val}% vs advertised {real}%",
            "{entity} stock count {val} vs warehouse {real} units",
        ],
        "news": [
            "{entity} report date {val} vs event occurrence {real}",
            "{entity} casualty count {val} vs confirmed {real}",
            "{entity} location {val} vs actual coordinates {real}",
        ],
        "science": [
            "{entity} constant value {val} vs accepted {real}",
            "{entity} measurement {val} vs peer review {real}",
            "{entity} prediction {val} vs experimental {real}",
        ],
        "tech": [
            "{entity} version {val} vs latest release {real}",
            "{entity} benchmark {val} ops vs reference {real} ops",
            "{entity} latency {val}ms vs sla {real}ms",
        ],
    }

    # Map domain to error types for realistic pairing.
    error_type_by_domain: dict[str, list[str]] = {
        "finance": ["numeric_error", "contradiction", "hallucination"],
        "medical": ["safety_breach", "numeric_error", "contradiction"],
        "legal": ["citation_error", "hallucination", "scope_violation"],
        "cybersecurity": ["hallucination", "entity_confusion", "pattern_match"],
        "ecommerce": ["contradiction", "numeric_error", "entity_confusion"],
        "news": ["temporal_error", "numeric_error", "citation_error"],
        "science": ["numeric_error", "citation_error", "hallucination"],
        "tech": ["entity_confusion", "hallucination", "outdated_fact"],
    }

    for i in range(n):
        domain = domains[i % len(domains)]
        entity = rng.choice(_DOMAIN_ENTITIES[domain])
        tmpl = rng.choice(templates_by_domain[domain])
        question = tmpl.format(
            entity=entity,
            val=rng.randint(10, 999),
            real=rng.randint(10, 999),
        )
        # Append 2-3 random context words for vocabulary diversity.
        ctx = rng.sample(_CONTEXT_WORDS, rng.randint(2, 3))
        question = f"{question} {' '.join(ctx)}"
        etype = rng.choice(error_type_by_domain[domain])
        errors.append(make_error(
            error_id=i,
            question=question,
            llm_answer=f"LLM claimed: {question}",
            error_type=etype,
            domain=domain,
            severity=rng.choice(_TEST_SEVERITIES),
            lesson=(
                f"Lesson #{i}: verify {etype} for {entity} in {domain} "
                f"before answering. Tags: {' '.join(ctx)}."
            ),
        ))
    return errors
