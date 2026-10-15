"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

"""
SCP V14 — Reality Engine & Classifier
"""
import logging
import math
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)
import re
from collections import defaultdict

# [G3-CONSOLIDATE RE-05] Canonical Wikipedia client — replaces inline
# urllib.request calls in WikipediaDataSource below. Same public API
# (WikipediaDataSource().fetch(query) -> {"title","extract"} | None),
# but HTTP layer now goes through scp.core.wikipedia_client for
# consistent timeout (10s), 1 req/sec rate limit, LRU cache, and
# proper User-Agent header. Verified external callers (all use
# WikipediaDataSource().fetch): adversary_verifier.py:152,177;
# runtime/slms_parts/{generalslm,entertainmentslm,universalslm}.py;
# runtime/slm_impls/{misc_slm,lifestyle_slm}.py.
from scp.core.wikipedia_client import (
    fetch_summary as _wiki_fetch_summary,
)
from scp.core.wikipedia_client import (
    search as _wiki_search,
)

# [AUDIT-20260909 SSRF-S1] safe_urlopen thay raw urllib.request.urlopen.
from scp.security.url_safety import safe_urlopen

VERDICT_PASS = "PASS"  # noqa: S105,S106  # nosec B105 — verdict constant, not a password
VERDICT_FAIL = "FAIL"
VERDICT_UNKNOWN = "UNKNOWN"

class TfidfVectorizer:
    def __init__(self):
        self.vocabulary = {}
        self.idf = {}
        self.doc_count = 0

    def fit(self, documents):
        self.vocabulary = {}
        df = defaultdict(int)
        self.doc_count = len(documents)
        for doc in documents:
            for tok in set(doc.lower().split()):
                df[tok] += 1
        for i, (tok, freq) in enumerate(df.items()):
            self.vocabulary[tok] = i
            self.idf[tok] = math.log((1 + self.doc_count) / (1 + freq)) + 1
        return self

    def transform(self, text):
        tokens = text.lower().split()
        vec = defaultdict(float)
        tf = defaultdict(int)
        for tok in tokens: tf[tok] += 1
        for tok, count in tf.items():
            if tok in self.vocabulary:
                vec[self.vocabulary[tok]] = (1 + math.log(count)) * self.idf.get(tok, 1.0)
        norm = math.sqrt(sum(v*v for v in vec.values())) or 1.0
        return {k: v/norm for k, v in vec.items()}

class MultiClassPerceptron:
    def __init__(self, n_features, classes, lr=0.15):
        self.classes = classes
        self.weights = {c: defaultdict(float) for c in classes}
        self.bias = {c: 0.0 for c in classes}
        self.lr = lr

    def _score(self, c, x):
        return sum(self.weights[c].get(k, 0.0) * v for k, v in x.items()) + self.bias[c]

    def predict(self, x):
        scores = {c: self._score(c, x) for c in self.classes}
        mx = max(scores.values())
        best = [c for c, s in scores.items() if s == mx]
        return best[0], mx / (sum(abs(v) for v in scores.values()) or 1.0)

    def partial_fit(self, x, true_cls):
        pred, _ = self.predict(x)
        if pred != true_cls:
            for k, v in x.items():
                self.weights[true_cls][k] += self.lr * v
                self.weights[pred][k] -= self.lr * v
            self.bias[true_cls] += self.lr
            self.bias[pred] -= self.lr

class RealityClassifier:
    FRAMES = ["math", "logic", "reality", "chemistry", "biology", "geography", "conversion", "statistics"]
    TRAINING_DATA = [
        ("tính collatz", "math"), ("số nguyên tố", "math"), ("2 + 3 = 5", "math"),
        ("tốc độ ánh sáng", "reality"), ("khối lượng trái đất", "reality"),
        ("khối lượng phân tử", "chemistry"), ("h2o", "chemistry"),
        ("nhiễm sắc thể", "biology"), ("dna", "biology"),
        ("thủ đô", "geography"), ("everest", "geography"),
        ("chuyển đổi", "conversion"), ("usd sang vnd", "conversion"),
        ("trung bình", "statistics"), ("phương sai", "statistics"),
    ]

    def __init__(self, confidence_threshold=0.30):
        self.confidence_threshold = confidence_threshold
        self.vectorizer = TfidfVectorizer()
        self.vectorizer.fit([q for q, _ in self.TRAINING_DATA])
        self.classifier = MultiClassPerceptron(len(self.vectorizer.vocabulary), self.FRAMES, 0.15)
        for _ in range(200):
            for q, f in self.TRAINING_DATA:
                self.classifier.partial_fit(self.vectorizer.transform(q), f)

    def classify(self, text):
        rule = self._rule_based_classify(text)
        if rule: return rule, 1.0
        x = self.vectorizer.transform(text)
        if not x: return "unknown", 0.0
        cls, conf = self.classifier.predict(x)
        return (cls, conf) if conf >= self.confidence_threshold else ("unknown", conf)

    def _rule_based_classify(self, text):
        if not text: return None
        t = text.lower().strip()
        if 'tính' in t and any(op in t for op in ['+', '-', '*', '/']): return "math"
        if re.search(r'\d+\s*[+\-*/]\s*\d+\s*=', t): return "math"
        if any(kw in t for kw in ['khối lượng phân tử', 'phân tử lượng', 'h2o']): return "chemistry"
        if 'chuyển đổi' in t and re.search(r'[a-z]{3}\s+sang\s+[a-z]{3}', t): return "conversion"
        if any(kw in t for kw in ['nhiệt độ', 'thời tiết']): return "weather" if 'cơ thể' not in t else "biology"
        if any(kw in t for kw in ['tốc độ ánh sáng', 'hằng số', 'nhiệt độ sôi']): return "reality"
        if any(kw in t for kw in ['thủ đô', 'everest']): return "geography"
        return None

class WikipediaDataSource:
    """Wikipedia REST API verifier — cải thiện trích entity từ câu hỏi.

    [G3-CONSOLIDATE RE-05] HTTP layer now delegates to scp.core.wikipedia_client.
    Same public API: WikipediaDataSource().fetch(query) -> {"title","extract"} | None.
    The _fetch_wiki(url) helper is kept as a thin wrapper for backward compat
    (it's only called internally by fetch() and verify(); no external callers
    found via grep as of G3-full-B). It now delegates URL parsing to the
    canonical client when the URL is a known Wikipedia endpoint, otherwise
    falls back to the original urllib.request path (kept for safety in case
    a non-Wikipedia URL is passed).
    """
    name = "wikipedia"

    def _fetch_wiki(self, url):
        """[G3-CONSOLIDATE RE-05] Thin compatibility wrapper.

        Original: made raw urllib.request call with timeout=15s.
        Now: detects Wikipedia REST/API URLs and delegates to the canonical
        client (which has 10s timeout, 1 req/sec rate limit, LRU cache).
        Falls back to urllib.request for any non-Wikipedia URL (defensive —
        shouldn't happen in practice since this class only fetches Wikipedia).
        """
        try:
            # Detect Wikipedia REST summary URL and delegate.
            if "en.wikipedia.org/api/rest_v1/page/summary/" in url:
                # Extract the title (last path segment, URL-decoded).
                title = url.rsplit("/", 1)[-1]
                if title:
                    title = urllib.parse.unquote(title).replace("_", " ")
                    result = _wiki_fetch_summary(title, lang="en")
                    if result:
                        return {"title": result.get("title", ""),
                                "extract": result.get("extract", ""),
                                "type": "standard"}  # not "not_found"
                    return None
            # Detect Wikipedia action=query (search) URL and delegate.
            if "en.wikipedia.org/w/api.php" in url and "action=query" in url:
                from urllib.parse import parse_qs, urlparse
                qs = parse_qs(urlparse(url).query)
                srsearch = qs.get("srsearch", [None])[0]
                if srsearch:
                    results = _wiki_search(srsearch, lang="en", limit=1)
                    if results:
                        return {"query": {"search": [{"title": results[0]["title"]}]}
                                , "_wiki_search_meta": True}
                    return None
            # Fallback: safe_urlopen path for non-Wikipedia URLs.
            # [AUDIT-20260909 SSRF-S1] safe_urlopen thay urllib.request.urlopen
            # — validate scheme + chặn private/loopback IP.
            import json
            req = urllib.request.Request(url, headers={  # noqa: S310
                'User-Agent': 'SCP-V73-Bot/1.0 (https://scp-vietnam.example.com; Vietnamese educational research project)',
                'Accept': 'application/json'
            })
            with safe_urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as exc:
            # silent-by-design: external fetch is best-effort; None means "unverifiable here".
            logger.debug("reality_engine: external fetch failed: %s", exc, exc_info=True)
            return None

    def fetch(self, query):
        """[G3-CONSOLIDATE RE-05] Now delegates to scp.core.wikipedia_client.

        Same return shape: {"title": str, "extract": str} or None.
        """
        # [G3-CONSOLIDATE RE-05] Now delegates to scp.core.wikipedia_client
        try:
            clean = query.strip().replace(' ', '_')
            result = _wiki_fetch_summary(clean, lang="en")
            if result and result.get("extract"):
                return {"title": result.get("title", ""), "extract": result["extract"]}
        except Exception as e:
            logger.debug(f"[V104.37] core/reality_engine.py: e={e}", exc_info=True)
        return None

    def _extract_entity(self, question: str) -> str:
        """
         Trích entity (chủ thể) từ câu hỏi — hỗ trợ VN + EN.
        Trả về chuỗi dùng để search Wikipedia.
        """
        clean_q = re.sub(r'[?¿!]', '', question).strip()

        # Patterns theo dạng câu hỏi (priority cao → thấp)
        patterns = [
            # Vietnamese — famous person
            (r'^ai\s+là\s+(.+?)\s*(?:và|,|$)', 'person'),
            (r'(.+?)\slà\s+ai\s*$', 'person'),
            (r'tác\s+giả\s+của\s+(.+?)\s*(?:là|$)', 'person'),
            (r'tác\s+giả\s+(.+?)\s*(?:là|$)', 'person'),
            (r'(?:vua|tổng\s+thống|chủ\s+tịch|tướng|hoàng\s+đế)\s+(.+?)\s*(?:là|$)', 'person'),

            # Vietnamese — capital
            (r'thủ\s+đô\s*(?:của\s+)?(.+?)\s*(?:là|$)', 'capital'),
            (r'(.+?)\s+có\s+thủ\s+đô\s*(?:là|$)', 'capital'),

            # Vietnamese — geography
            (r'diện\s+tích\s*(?:của\s+)?(.+?)\s*(?:là|$)', 'area'),
            (r'dân\s+số\s*(?:của\s+)?(.+?)\s*(?:là|$)', 'population'),
            (r'(.+?)\snằm\s+ở\s+đâu\s*$', 'location'),
            (r'tọa\s+độ\s*(?:của\s+)?(.+?)\s*(?:là|$)', 'location'),

            # Vietnamese — history event
            (r'sự\s+kiện\s+(.+?)\s*(?:xảy|xuất|diễn|$)', 'event'),
            (r'(.+?)\sxảy\s+ra\s+vào\s+năm\s+nào\s*$', 'event'),
            (r'năm\s+(\d{3,4}).*?(xảy\s+ra|diễn\s+ra)', 'year'),

            # English — common patterns
            (r'who\s+is\s+(.+?)\??$', 'person'),
            (r'who\s+was\s+(.+?)\??$', 'person'),
            (r'what\s+is\s+the\s+capital\s+of\s+(.+?)\??$', 'capital'),
            (r'what\s+is\s+(.+?)\??$', 'thing'),
            (r'where\s+is\s+(.+?)\s+located\??$', 'location'),
            (r'when\s+did\s+(.+?)\s+(?:happen|occur|take\s+place)\??$', 'event'),
        ]

        for pattern, _kind in patterns:
            m = re.search(pattern, clean_q, re.IGNORECASE)
            if m:
                entity = m.group(1).strip().rstrip('?').rstrip('.').strip()
                # Bỏ stop words ở cuối
                entity = re.sub(r'\s+(?:gì|nào|bao nhiêu|ở đâu|khi nào)\s*$', '', entity, flags=re.IGNORECASE).strip()
                if entity and len(entity) > 1:
                    return entity

        # Fallback: bỏ prefix "Tính/Calculate/What is" và trả về phần còn lại (capped 5 words)
        prefix_stripped = re.sub(
            r'^(?:tính|calculate|compute|what\s+is|whats|who\s+is|who\s+was|where\s+is|when\s+did)\s+',
            '', clean_q, flags=re.IGNORECASE
        ).strip().rstrip('?').rstrip('.').strip()
        words = prefix_stripped.split()[:5]
        if words:
            return ' '.join(words)
        return clean_q

    def verify(self, question, ai_answer):
        """
         Verify AI answer bằng Wikipedia.
        Cải thiện: trích entity tốt hơn, hỗ trợ câu hỏi VN + EN.
        """
        if not ai_answer or not ai_answer.strip():
            return (VERDICT_UNKNOWN, "AI answer rỗng", None)

        # Trích entity từ question
        search_query = self._extract_entity(question)

        # Thử fetch Wikipedia page summary
        wiki_data = self.fetch(search_query)

        # Fallback: nếu không tìm thấy, thử tìm qua Wikipedia Search API
        if not wiki_data or not wiki_data.get("extract"):
            try:
                search_url = (
                    f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch="
                    f"{urllib.parse.quote(search_query)}&format=json&srlimit=1"
                )
                search_resp = self._fetch_wiki(search_url)
                if search_resp and search_resp.get("query", {}).get("search"):
                    title = search_resp["query"]["search"][0]["title"]
                    wiki_data = self.fetch(title)
            except Exception as e:
                logger.debug(f"[V104.37] core/reality_engine.py: e={e}", exc_info=True)

        if not wiki_data or not wiki_data.get("extract"):
            return (VERDICT_UNKNOWN, f"Wikipedia không có dữ liệu cho '{search_query}'", None)

        wiki_extract = wiki_data["extract"].lower()
        ai_lower = ai_answer.lower().strip()
        ai_numbers = re.findall(r'\d+\.?\d*', ai_answer)
        # Tokens dài >3 ký tự để tránh stop words
        ai_words = [w for w in re.findall(r'\b[a-zA-Zà-ỹ]+\b', ai_lower) if len(w) > 3]

        matched_nums = sum(1 for n in ai_numbers if re.search(r"\b" + re.escape(n) + r"\b", wiki_extract))  # [V104.37 #81] TẠI SAO: substring "12" matched "2012"
        matched_words = sum(1 for w in ai_words if re.search(r"\b" + re.escape(w) + r"\b", wiki_extract))  # [V104.37 #81]
        matched = matched_nums + matched_words
        total = len(ai_numbers) + len(ai_words)

        if total == 0:
            return (VERDICT_UNKNOWN, "Không extract được fact từ AI answer", wiki_data["extract"][:200])

        ratio = matched / total
        if ratio >= 0.5:
            return (VERDICT_PASS, f"Wikipedia match {ratio*100:.0f}% (title={wiki_data.get('title','?')[:50]})", wiki_data["extract"][:200])
        if ratio >= 0.25:
            return (VERDICT_UNKNOWN, f"Wikipedia partial match {ratio*100:.0f}%", wiki_data["extract"][:200])
        return (VERDICT_FAIL, f"Wikipedia mismatch {ratio*100:.0f}% (title={wiki_data.get('title','?')[:50]})", wiki_data["extract"][:200])

#  DELETED: RealityEngine class — dead code (V14 era, all checkers empty)
# Replaced by: DirectAPIVerifier (V27) + 11 SLMs (V27-V29) + multi-source (V29.1)
# Kept WikipediaDataSource above (still used by adversary_verifier)
