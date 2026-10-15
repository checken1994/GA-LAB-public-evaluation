#!/usr/bin/env python3
"""
SCP V90 — SMART QUESTION CLASSIFIER
Thay thế keyword matching bằng embedding-based classification.

Các phương pháp có thể dùng:
1. TF-IDF + Cosine Similarity (không cần AI, nhanh)
2. Sentence Embeddings (chính xác hơn)
3. LLM-based (chính xác nhất nhưng chậm)
4. Hybrid (kết hợp)
"""

import hashlib
import logging
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field

# [G3-CONSOLIDATE P1-03] DOMAIN_PROFILES now delegates to canonical domain_registry.DOMAINS.
# Previously this file had its own 44-domain keyword DB (V5.9-V104.36 patches) that
# DISAGREED with domain_registry.DOMAINS (45 domains) and judgeroute_mixin inline rules
# (~470 LOC) — same question routed differently depending on which DB won (Task 2-B
# finding P1-03). The canonical registry now holds the superset (54 domains) with merged
# keywords + patterns + examples + weight. This file delegates purely so the
# SmartClassifier class keeps its public API but reads from the single source of truth.
from scp.data_sources.domain_registry import DOMAINS as _CANONICAL_DOMAINS

logger = logging.getLogger("scp.smart_classifier")

# ============================================================
# DOMAIN DEFINITIONS — delegates to canonical domain_registry.DOMAINS
# ============================================================
# [G3-CONSOLIDATE P1-03] DOMAIN_PROFILES is now a LIVE VIEW of the canonical DOMAINS.
# SmartClassifier._keyword_score / _semantic_score read `keywords`, `patterns`, `examples`,
# `weight` — all four fields are now part of the canonical registry schema (added during
# the merge). Changes to domain_registry.DOMAINS propagate automatically.
DOMAIN_PROFILES = _CANONICAL_DOMAINS


@dataclass
class ClassificationResult:
    """Kết quả phân loại."""
    domain: str
    confidence: float
    alternatives: list[tuple[str, float]] = field(default_factory=list)
    method: str = "hybrid"


class SmartClassifier:
    """SMART QUESTION CLASSIFIER

    Kết hợp nhiều phương pháp để phân loại chính xác:
    1. Keyword matching (nhanh, cho keywords rõ ràng)
    2. Pattern matching (cho cấu trúc đặc biệt)
    3. Semantic similarity (cho câu hỏi phức tạp)

    Usage:
        classifier = SmartClassifier()
        result = classifier.classify("Giá bitcoin hôm nay?")
        print(result.domain, result.confidence)
    """

    def __init__(self, use_embeddings: bool = False):
        self._cache: dict[str, tuple[float, ClassificationResult]] = {}
        self._CACHE_TTL = 3600  # 1 hour
        self._CACHE_MAX = 2000
        self._use_embeddings = use_embeddings

        # Precompute domain signatures
        self._domain_signatures = self._build_signatures()

        logger.info(f"SmartClassifier initialized (embeddings={use_embeddings})")

    def _build_signatures(self) -> dict:
        """Build TF-IDF-like signatures for each domain."""
        signatures = {}
        for domain, profile in DOMAIN_PROFILES.items():
            # Combine keywords and examples
            words = []
            for kw in profile["keywords"]:
                words.extend(kw.lower().split())
            for ex in profile["examples"]:
                words.extend(ex.lower().split())

            # Count word frequencies
            word_freq = Counter(words)

            # TF-IDF-like scoring
            total = sum(word_freq.values()) or 1
            signatures[domain] = {
                word: freq / total
                for word, freq in word_freq.items()
            }

        return signatures

    def _cosine_similarity(self, vec1: dict[str, float], vec2: dict[str, float]) -> float:
        """Tính cosine similarity giữa 2 vectors."""
        common = set(vec1.keys()) & set(vec2.keys())
        if not common:
            return 0.0

        dot_product = sum(vec1[w] * vec2[w] for w in common)
        norm1 = math.sqrt(sum(v**2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v**2 for v in vec2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text thành words."""
        # Remove punctuation and lowercase
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        # Split by whitespace
        words = text.split()
        # Remove very short words
        words = [w for w in words if len(w) >= 2]
        return words

    def _build_query_vector(self, question: str) -> dict[str, float]:
        """Build TF-IDF vector cho question."""
        words = self._tokenize(question)
        word_freq = Counter(words)
        total = len(words) or 1

        return {word: freq / total for word, freq in word_freq.items()}

    def _keyword_score(self, question: str, domain: str) -> float:
        """Tính keyword matching score.

        [V104.36 #70] TẠI SAO: kw.lower() in q_lower is substring — "ai" matches
        "rain", "or" matches "for", "and" matches "hand". Fix: for short keywords
        (<=3 chars), use word-boundary regex; for longer, substring is acceptable.
        """
        profile = DOMAIN_PROFILES.get(domain, {})
        q_lower = question.lower()

        score = 0.0
        matched = 0

        # Keywords — short keywords need word boundary, long can use substring
        for kw in profile.get("keywords", []):
            kw_lower = kw.lower().strip()  # [V104.36 #70] strip leading/trailing space
            if not kw_lower:
                continue
            # [V104.37 #80] TẠI SAO: V104.36 #70 only fixed ≤3 char keywords;
            # 4+ char keywords ("mean" matches "meaning", "force" matches "enforce")
            # had same substring bug. Fix: word-boundary for ALL keywords.
            if re.search(r'\b' + re.escape(kw_lower) + r'\b', q_lower):
                score += 1.0
                matched += 1

        # Patterns
        for pattern in profile.get("patterns", []):
            if re.search(pattern, q_lower, re.IGNORECASE):
                score += 1.5  # Patterns are more specific
                matched += 1

        # Normalize by number of terms
        total_terms = len(profile.get("keywords", [])) + len(profile.get("patterns", []))
        if total_terms > 0:
            return (score / total_terms) * profile.get("weight", 1.0)

        return 0.0

    def _semantic_score(self, question: str, domain: str) -> float:
        """Tính semantic similarity score."""
        query_vec = self._build_query_vector(question)
        domain_sig = self._domain_signatures.get(domain, {})

        return self._cosine_similarity(query_vec, domain_sig)

    def classify(self, question: str) -> ClassificationResult:
        """
        Classify question vào domain phù hợp.

        Returns:
            ClassificationResult với domain, confidence, và alternatives
        """
        if not question:
            return ClassificationResult(domain="math", confidence=0.5, method="fallback")

        # Check cache first
        cache_key = hashlib.sha256(question.encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if cached:
            ts, result = cached
            if time.time() - ts < self._CACHE_TTL:
                return result

        # [FIX #6] TẠI SAO: SmartClassifier fail route "2+2=?" → math because the
        # question has no math keywords (just digits + operators). The keyword/
        # semantic scoring gives 0.097 → fallback to "general" → MathSLM never
        # gets called → FAIL with empty answer + Constitution KILL.
        # Reality > Model: tested `2+2=?` → was "general" 0.097, after this rule
        # → "math" 0.99. MathSLM then returns "2+2 = 4" with confidence 0.99.
        # Pattern: digit(s) + operator + digit(s) → math.
        import re as _re_classify

        # [V5.9-FIX] CVE pattern check BEFORE math — TẠI SAO: math pattern
        # \d+\s*[+\-*/%^]\s*\d+ matches "2021-44228" in CVE IDs → routes CVE
        # questions to math instead of cybersecurity. Fix: check CVE first.
        _CVE_PATTERN = _re_classify.compile(r'\bCVE-\d{4}-\d+\b', _re_classify.IGNORECASE)
        if _CVE_PATTERN.search(question):
            result = ClassificationResult(
                domain="cybersecurity",
                confidence=0.99,
                alternatives=[("general", 0.1)],
                method="deterministic_cve_pattern",
            )
            if len(self._cache) >= self._CACHE_MAX:
                oldest_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])[:500]
                for k in oldest_keys:
                    del self._cache[k]
            self._cache[cache_key] = (time.time(), result)
            return result

        _MATH_PATTERN = _re_classify.compile(r'\d+(?:\.\d+)?\s*[+\-*/%^]\s*\d+(?:\.\d+)?')
        if _MATH_PATTERN.search(question):
            result = ClassificationResult(
                domain="math",
                confidence=0.99,
                alternatives=[("general", 0.1)],
                method="deterministic_math_pattern",
            )
            if len(self._cache) >= self._CACHE_MAX:
                oldest_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])[:500]
                for k in oldest_keys:
                    del self._cache[k]
            self._cache[cache_key] = (time.time(), result)
            return result

        # [REAUDIT-FIX] "Tính 15!" / "tính 2+3" / "calculate 5" → math
        _MATH_VI_PATTERN = _re_classify.compile(r'\b(?:tính|calculate|compute)\s+[\d\w]', _re_classify.IGNORECASE)
        if _MATH_VI_PATTERN.search(question):
            result = ClassificationResult(
                domain="math",
                confidence=0.95,
                alternatives=[("general", 0.1)],
                method="deterministic_math_vi_pattern",
            )
            self._cache[cache_key] = (time.time(), result)
            return result

        # [FIX #18] TẠI SAO: SmartClassifier fails to route "capital of France"
        # to geography — keyword scoring gives geography=0.128 but general=0.174
        # (because "what is the" matches general keywords). GeneralSLM has no
        # geography data → empty answer → UNKNOWN/FAIL.
        # Reality > Model: tested "capital of France" → was "general" 0.174,
        # GeographySLM never called. After fix: "geography" 0.99, GeographySLM
        # returns "thủ đô France = Paris" with conf=0.7.
        # Pattern: "capital of X" / "currency of X" / "population of X" → geography
        _GEO_PATTERN = _re_classify.compile(
            r'\b(?:capital|currency|population|area|language)s?\s+of\s+\w+'
            r'|\b(?:thủ\s+đô|thủ\s+do)\b',
            _re_classify.IGNORECASE
        )
        if _GEO_PATTERN.search(question):
            result = ClassificationResult(
                domain="geography",
                confidence=0.99,
                alternatives=[("general", 0.1)],
                method="deterministic_geo_pattern",
            )
            if len(self._cache) >= self._CACHE_MAX:
                oldest_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])[:500]
                for k in oldest_keys:
                    del self._cache[k]
            self._cache[cache_key] = (time.time(), result)
            return result

        # [ROOT-FIX 43-A / Fix 2] TẠI SAO: "Is earth flat?" was routing to "general"
        # (reality keyword score ~0.05, general "is" keyword score ~0.10 → general wins).
        # RealitySLM already has 'earth is flat' / 'trái đất phẳng' in CONSTANTS table
        # and would return the correct answer (False, oblate spheroid). Fix: detect
        # fact-check / boolean-truth / conspiracy questions deterministically → route
        # to reality domain. Reality > Model: tested "Is earth flat?" → was "general"
        # 0.10, after fix → "reality" 0.99. RealitySLM returns "earth is flat = False"
        # with conf=0.95.
        _REALITY_FACT_PATTERN = _re_classify.compile(
            r'\b(?:earth|trái\s+đất)\s+(?:is\s+)?flat\b'
            r'|\bflat\s+(?:earth|trái\s+đất)\b'
            r'|\btrái\s+đất\s+phẳng\b'
            r'|\b(?:is|có)\s+(?:earth|trái\s+đất)\s+(?:flat|phẳng)\b'
            r'|\bfact[\s-]?check\b'
            r'|\btrue\s+or\s+false\b'
            r'|\bđúng\s+hay\s+sa?i\b'
            r'|\bconspiracy\b',
            _re_classify.IGNORECASE
        )
        if _REALITY_FACT_PATTERN.search(question):
            result = ClassificationResult(
                domain="reality",
                confidence=0.99,
                alternatives=[("general", 0.1)],
                method="deterministic_reality_fact_pattern",
            )
            if len(self._cache) >= self._CACHE_MAX:
                oldest_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])[:500]
                for k in oldest_keys:
                    del self._cache[k]
            self._cache[cache_key] = (time.time(), result)
            return result

        # Calculate scores for all domains
        scores: dict[str, float] = {}
        for domain in DOMAIN_PROFILES:
            keyword_sc = self._keyword_score(question, domain)
            semantic_sc = self._semantic_score(question, domain)

            # Combine scores (weighted average)
            combined = (keyword_sc * 0.7) + (semantic_sc * 0.3)
            scores[domain] = combined

        # Sort by score
        sorted_domains = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Get best domain
        best_domain, best_score = sorted_domains[0]

        # [FIX 2026-07-09] Minimum-confidence gate. Root cause found via live-data
        # audit: classify() had NO floor — it always returned whichever domain
        # scored highest even when that score was pure noise (e.g. 0.05-0.09 out
        # of a max of 1.0), because random 1-2 word substring overlaps against a
        # domain's small keyword list can edge out a tiny nonzero score. This was
        # confirmed routing real trivia questions like "Pamina and Papageno are
        # characters in what Mozart opera?" -> "logic" and "...SpongeBack..." ->
        # "uxui" with scores under 0.13 — nowhere near a genuine match. Below this
        # floor, fall back to "general" (safe multi-purpose SLM) instead of a
        # confidently-wrong specific domain that has zero chance of answering.
        _MIN_CONFIDENT_SCORE = 0.15
        if best_score < _MIN_CONFIDENT_SCORE:
            best_domain = "general"
            method_used = "fallback_low_confidence"
        else:
            method_used = "hybrid"

        # Calculate confidence (normalize to 0-1)
        max_possible = 1.0
        confidence = min(best_score / max_possible, 1.0) if best_score > 0 else 0.3

        # Get top 3 alternatives
        alternatives = sorted_domains[1:4]

        result = ClassificationResult(
            domain=best_domain,
            confidence=confidence,
            alternatives=alternatives,
            method=method_used
        )

        # Cache result
        if len(self._cache) >= self._CACHE_MAX:
            # Remove oldest entries
            oldest_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])[:500]
            for k in oldest_keys:
                del self._cache[k]

        self._cache[cache_key] = (time.time(), result)

        return result

    def classify_multi(self, question: str, max_domains: int = 3) -> list[str]:
        """Classify và trả về nhiều domains (cho multi-SLM).

        Returns:
            List of domains (e.g., ["finance", "conversion"])
        """
        result = self.classify(question)

        domains = [result.domain]

        # Add alternatives if confidence is low
        if result.confidence < 0.5:
            for alt_domain, alt_score in result.alternatives:
                if alt_score > 0.1 and len(domains) < max_domains:
                    domains.append(alt_domain)

        return domains

    def learn_from_feedback(self, question: str, correct_domain: str):
        """Học từ feedback để cải thiện classification.

        TODO: Implement learning mechanism
        """
        # This could update domain profiles based on corrections
        pass

    def get_stats(self) -> dict:
        """Get classifier statistics."""
        return {
            "cache_size": len(self._cache),
            "domains": len(DOMAIN_PROFILES),
            "cache_hit_rate": "N/A (not tracked yet)"
        }


# ============================================================
# STANDALONE TEST
# ============================================================
if __name__ == "__main__":
    print("=" * 70)
    print("🔍 SMART CLASSIFIER TEST")
    print("=" * 70)

    classifier = SmartClassifier()

    test_questions = [
        "Giá bitcoin hôm nay là bao nhiêu USD?",
        "Tính sqrt(144) + 25",
        "Thủ đô của Việt Nam là gì?",
        "Tốc độ ánh sáng là bao nhiêu?",
        "Triệu chứng của covid 2024?",
        "Ai phát minh ra điện thoại?",
        "Sao Hỏa có bao nhiêu vệ tinh?",
        "Công thức phân tử của nước là gì?",
        "Standard deviation của [1,2,3,4,5]?",
        "Thời tiết Hà Nội hôm nay như nào?",
    ]

    print("\n📊 CLASSIFICATION RESULTS:")
    print("-" * 70)

    for q in test_questions:
        result = classifier.classify(q)
        print(f"\n❓ {q}")
        print(f"   → Domain: {result.domain} (confidence: {result.confidence:.2f})")
        if result.alternatives:
            alts = ", ".join([f"{d} ({s:.2f})" for d, s in result.alternatives[:2]])
            print(f"   → Alternatives: {alts}")

    print("\n" + "=" * 70)
    print(f"✅ Tested {len(test_questions)} questions")
    print("=" * 70)
