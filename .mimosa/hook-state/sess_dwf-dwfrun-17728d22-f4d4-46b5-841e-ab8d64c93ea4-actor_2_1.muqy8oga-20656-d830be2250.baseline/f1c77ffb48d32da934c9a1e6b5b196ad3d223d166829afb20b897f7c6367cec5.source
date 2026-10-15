"""
DirectAPIVerifier — extracted from engine.py (Task 19-A).
Verify facts bằng cách gọi API trực tiếp, bypass V13 Regex Engine.

[G3-CONSOLIDATE P1-06] Verifier consolidation status:
- This verifier: LIVE-UNIQUE
- Canonical verifier: scp/core/multi_source_verifier.py::AsyncMultiSourceVerifier
- Unique role: DIRECT-API CLAIM VERIFICATION — given (question, answer, domain),
  fetches the GROUND-TRUTH value from a domain-specific REST API and checks if
  the answer matches. Domains: geography (REST Countries), chemistry (PubChem),
  finance (CoinGecko), general (Wikipedia REST summary). Returns
  verdict ∈ {PASS, FAIL, UNKNOWN}. Distinct from canonical
  AsyncMultiSourceVerifier which verifies a claim against REGISTERED
  IDataSource objects in parallel via asyncio.gather(); DirectAPIVerifier
  routes by domain and only fires as a FALLBACK when V13 Regex Engine returns
  UNKNOWN (judgecore_mixin.py:1380).
- Wired to /ask: YES — engine.py:76 imports DirectAPIVerifier; engine.py:132
  assigns `self.v13.direct_verifier = DirectAPIVerifier()`; judgecore_mixin.py
  calls `self.v13.direct_verifier.verify()` at Step 7 (V13 UNKNOWN fallback).
- Known partial overlaps (intentional, NOT delegated):
  * `_verify_chemistry` calls PubChem — same endpoint family as canonical
    `multi_source_verifier._fetch_pubchem`. DIFFERENT intent: canonical
    returns molecular WEIGHT (for SLM consensus); DirectAPIVerifier returns
    molecular FORMULA (for claim verification against an answer string).
  * `_verify_finance` calls CoinGecko — same as
    `crypto_verifier._fetch_coingecko`. DIFFERENT intent: crypto_verifier
    returns a consensus price across 6 exchanges; DirectAPIVerifier returns
    a single price + ±10% tolerance check against the user's answer.
  * `_verify_general` calls Wikipedia REST summary — same endpoint as
    `multi_source_verifier.fetch_wikipedia_summary`. DIFFERENT intent:
    canonical returns the extract for SLM context; DirectAPIVerifier computes
    TOKEN OVERLAP between the extract and the user's answer to decide
    PASS/FAIL.
"""
import logging
import re

from scp.security.url_safety import enforce_egress_policy  # [V-EE-2]

logger = logging.getLogger("scp.v14")


class DirectAPIVerifier:
    """Direct API verification — calls external REST APIs to verify claims.

    [Task 19-B / Mục 14] Real implementation replacing the placeholder stub.
    Routes by domain:
      - geography → REST Countries API (https://restcountries.com/v3.1)
      - chemistry → PubChem REST API (https://pubchem.ncbi.nlm.nih.gov/rest/pug)
      - finance   → CoinGecko API (https://api.coingecko.com/api/v3)
      - general   → Wikipedia REST API (https://en.wikipedia.org/api/rest_v1)

    All calls are wrapped in try/except — on any failure (network, parse,
    timeout) returns verdict="UNKNOWN" so the judge falls back to other
    evidence. NEVER raises.
    """

    # [PERF] shared session for connection pooling across calls
    _session = None

    def _session_get(self, url: str, *, params: dict | None = None,
                     timeout: float = 5.0, headers: dict | None = None):
        """Lightweight wrapper around requests.get with shared session + UA.

        [V-EE-2] enforce_egress_policy chạy TRƯỚC MỌI fetch — raw
        requests.Session này giờ đọc SCP_EGRESS_MODE (deny/allowlist) giống
        các fetcher chuẩn. EgressDeniedError là ValueError subclass → mọi
        caller (`_verify_*` bọc try/except Exception) trả verdict UNKNOWN
        graceful như contract; không đổi behavior nào khác.
        """
        # [V-EE-2] PEP ngay trước driver: gate egress trước cả việc tạo
        # session / import requests — fail-closed không I/O.
        enforce_egress_policy(url)
        try:
            import requests  # local import — keeps optional dep
        except ImportError as e:
            raise RuntimeError(f"requests not installed: {e}") from e
        if DirectAPIVerifier._session is None:
            DirectAPIVerifier._session = requests.Session()
            DirectAPIVerifier._session.headers.update({
                "User-Agent": "SCP-Vietnam-DirectAPIVerifier/1.0 (+scp-vietnam@example.com)",
                "Accept": "application/json",
            })
        resp = DirectAPIVerifier._session.get(url, params=params, timeout=timeout,
                                             headers=headers)
        resp.raise_for_status()
        return resp

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def verify(self, question: str, answer: str, domain: str) -> dict:
        """Verify answer using direct API calls based on domain.

        Returns dict with keys: verdict, reason, real_value, source.
        verdict ∈ {"PASS", "FAIL", "UNKNOWN"}.
        """
        try:
            q_norm = (question or "").strip().lower()
            a_norm = (answer or "").strip()
            if not q_norm or not a_norm:
                return {"verdict": "UNKNOWN",
                        "reason": "empty question or answer",
                        "real_value": None, "source": "none"}

            if domain == "geography":
                return self._verify_geography(q_norm, a_norm)
            if domain == "chemistry":
                return self._verify_chemistry(q_norm, a_norm)
            if domain == "finance":
                return self._verify_finance(q_norm, a_norm)
            return self._verify_general(q_norm, a_norm)
        except Exception as e:
            logger.debug("Direct API verify dispatch failed: %s", e, exc_info=True)
            return {"verdict": "UNKNOWN",
                    "reason": f"API verify failed: {e}",
                    "real_value": None, "source": "error"}

    # ------------------------------------------------------------------
    # Helpers — text normalization for comparison
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_text(s: str) -> str:
        """Lowercase, strip accents, collapse whitespace, drop punctuation."""
        import unicodedata
        if not s:
            return ""
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        s = s.lower().strip()
        # Remove common punctuation but keep alphanumerics + spaces
        s = re.sub(r"[^a-z0-9\s]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @classmethod
    def _answer_contains(cls, real_value: str, answer: str) -> bool:
        """True if real_value (or any token) appears in answer."""
        if not real_value:
            return False
        r = cls._normalize_text(real_value)
        a = cls._normalize_text(answer)
        if not r or not a:
            return False
        if r in a or a in r:
            return True
        # Multi-word real_value: check all tokens present in answer
        r_tokens = [t for t in r.split() if len(t) >= 3]
        if r_tokens and all(t in a for t in r_tokens):
            return True
        return False

    # ------------------------------------------------------------------
    # Domain: geography — REST Countries API
    # ------------------------------------------------------------------
    def _verify_geography(self, q: str, a: str) -> dict:
        """Verify capital / region of a country via REST Countries API."""
        # Try to extract country name from question
        country = None
        # Pattern: "capital of <country>", "thủ đô của <country>"
        m = re.search(r"(?:capital of|thủ đô của|thủ đô)\s+([a-zA-Zà-ỹ\s]+?)(?:\?|$|\.)", q)
        if m:
            country = m.group(1).strip()
        else:
            # Pattern: "<country> capital?"
            m = re.search(r"([a-zA-Zà-ỹ\s]+?)\s+(?:capital|thủ đô)", q)
            if m:
                country = m.group(1).strip()
        if not country:
            return {"verdict": "UNKNOWN", "reason": "could not extract country",
                    "real_value": None, "source": "restcountries"}
        # Clean up country name
        country = country.strip("?.!,;:'\"")
        # If question asks about capital
        asks_capital = ("capital" in q) or ("thủ đô" in q)
        asks_region = ("region" in q) or ("continent" in q) or ("châu lục" in q) or ("khu vực" in q)
        try:
            # REST Countries — search by name (case-insensitive)
            resp = self._session_get(
                f"https://restcountries.com/v3.1/name/{country}",
                params={"fullText": "false"},
                timeout=5.0,
            )
            data = resp.json()
            if not data:
                return {"verdict": "UNKNOWN", "reason": f"country not found: {country}",
                        "real_value": None, "source": "restcountries"}
            first = data[0]
            if asks_capital:
                capitals = first.get("capital") or []
                if not capitals:
                    return {"verdict": "UNKNOWN", "reason": "no capital data",
                            "real_value": None, "source": "restcountries"}
                real_capital = capitals[0]
                ok = self._answer_contains(real_capital, a)
                return {
                    "verdict": "PASS" if ok else "FAIL",
                    "reason": f"capital of {country} is {real_capital}",
                    "real_value": real_capital,
                    "source": "restcountries.com",
                }
            if asks_region:
                region = first.get("region") or ""
                subregion = first.get("subregion") or ""
                real_value = region or subregion
                if not real_value:
                    return {"verdict": "UNKNOWN", "reason": "no region data",
                            "real_value": None, "source": "restcountries"}
                ok = self._answer_contains(real_value, a)
                return {
                    "verdict": "PASS" if ok else "FAIL",
                    "reason": f"{country} is in {real_value}",
                    "real_value": real_value,
                    "source": "restcountries.com",
                }
            # Default: just return country exists
            official = first.get("name", {}).get("official", country)
            return {"verdict": "UNKNOWN",
                    "reason": f"country found: {official}",
                    "real_value": official, "source": "restcountries.com"}
        except Exception as e:
            logger.debug("restcountries verify failed: %s", e, exc_info=True)
            return {"verdict": "UNKNOWN",
                    "reason": f"restcountries call failed: {e}",
                    "real_value": None, "source": "error"}

    # ------------------------------------------------------------------
    # Domain: chemistry — PubChem
    # ------------------------------------------------------------------
    def _verify_chemistry(self, q: str, a: str) -> dict:
        """Verify molecular formula via PubChem PUG REST API."""
        # Extract compound name — remove "formula of", "công thức của", trailing ?
        name = q
        for pat in (r"^(?:formula of|công thức của|công thức|chemical formula of|formula for)\s+",
                    r"\s+(?:formula|công thức).*$"):
            name = re.sub(pat, "", name).strip()
        name = re.sub(r"[?.!,;:'\"]", "", name).strip()
        if not name:
            return {"verdict": "UNKNOWN", "reason": "no compound name",
                    "real_value": None, "source": "pubchem"}
        # Common aliases
        aliases = {
            "nước": "water", "muối": "salt", "muối ăn": "sodium chloride",
            "khí oxy": "oxygen", "khí hidro": "hydrogen",
        }
        name = aliases.get(name, name)
        try:
            # PubChem PUG REST — get molecular formula
            resp = self._session_get(
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/MolecularFormula,Title/JSON",
                timeout=5.0,
            )
            data = resp.json()
            props = (data.get("PropertyTable") or {}).get("Properties") or []
            if not props:
                return {"verdict": "UNKNOWN", "reason": f"compound not found: {name}",
                        "real_value": None, "source": "pubchem"}
            first = props[0]
            formula = first.get("MolecularFormula") or ""
            title = first.get("Title") or name
            if not formula:
                return {"verdict": "UNKNOWN", "reason": "no formula data",
                        "real_value": None, "source": "pubchem"}
            # Extract formula-like token from answer (letters + digits + parens)
            m = re.search(r"\b([A-Z][A-Za-z0-9\(\)]{0,40})\b", a)
            ans_formula = m.group(1) if m else a.strip()
            ok = (ans_formula.upper() == formula.upper()) or (formula.lower() in a.lower())
            return {
                "verdict": "PASS" if ok else "FAIL",
                "reason": f"{title} formula = {formula}",
                "real_value": formula,
                "source": "pubchem.ncbi.nlm.nih.gov",
            }
        except Exception as e:
            logger.debug("pubchem verify failed: %s", e, exc_info=True)
            return {"verdict": "UNKNOWN",
                    "reason": f"pubchem call failed: {e}",
                    "real_value": None, "source": "error"}

    # ------------------------------------------------------------------
    # Domain: finance — CoinGecko
    # ------------------------------------------------------------------
    def _verify_finance(self, q: str, a: str) -> dict:
        """Verify cryptocurrency price via CoinGecko API."""
        # Extract coin name
        coin = None
        m = re.search(r"(?:price of|giá của|giá|price)\s+([a-zA-Z\s]+?)(?:\?|$|today|now)", q)
        if m:
            coin = m.group(1).strip()
        else:
            # "bitcoin price?"
            m = re.search(r"^([a-zA-Z\s]+?)\s+(?:price|giá)", q)
            if m:
                coin = m.group(1).strip()
        if not coin:
            return {"verdict": "UNKNOWN", "reason": "could not extract coin",
                    "real_value": None, "source": "coingecko"}
        # Normalize common names → CoinGecko IDs
        coin_map = {
            "bitcoin": "bitcoin", "btc": "bitcoin",
            "ethereum": "ethereum", "eth": "ethereum",
            "solana": "solana", "sol": "solana",
            "cardano": "cardano", "ada": "cardano",
            "dogecoin": "dogecoin", "doge": "dogecoin",
            "ripple": "ripple", "xrp": "ripple",
            "litecoin": "litecoin", "ltc": "litecoin",
        }
        coin_id = coin_map.get(coin.lower(), coin.lower().split()[0])
        try:
            resp = self._session_get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd"},
                timeout=5.0,
            )
            data = resp.json()
            if coin_id not in data:
                return {"verdict": "UNKNOWN",
                        "reason": f"coin not found: {coin_id}",
                        "real_value": None, "source": "coingecko"}
            usd_price = data[coin_id].get("usd")
            if usd_price is None:
                return {"verdict": "UNKNOWN", "reason": "no price data",
                        "real_value": None, "source": "coingecko"}
            # Answer comparison: extract first number from answer
            m = re.search(r"[\d,]+\.?\d*", a.replace(",", ""))
            if not m:
                return {"verdict": "UNKNOWN",
                        "reason": f"{coin_id}=${usd_price} (no number in answer)",
                        "real_value": str(usd_price),
                        "source": "coingecko.com"}
            try:
                ans_price = float(m.group(0).replace(",", ""))
            except ValueError:
                return {"verdict": "UNKNOWN",
                        "reason": "could not parse answer price",
                        "real_value": str(usd_price),
                        "source": "coingecko.com"}
            # Allow ±10% tolerance for crypto (volatile)
            tolerance = max(0.10, abs(usd_price) * 0.10)
            ok = abs(ans_price - usd_price) <= tolerance
            return {
                "verdict": "PASS" if ok else "FAIL",
                "reason": f"{coin_id} current price = ${usd_price}",
                "real_value": str(usd_price),
                "source": "coingecko.com",
            }
        except Exception as e:
            logger.debug("coingecko verify failed: %s", e, exc_info=True)
            return {"verdict": "UNKNOWN",
                    "reason": f"coingecko call failed: {e}",
                    "real_value": None, "source": "error"}

    # ------------------------------------------------------------------
    # Domain: general — Wikipedia REST API
    # ------------------------------------------------------------------
    def _verify_general(self, q: str, a: str) -> dict:
        """Verify via Wikipedia REST summary API.

        Strategy: extract a likely topic (noun phrase) from the question,
        fetch Wikipedia summary, and check if answer tokens appear in it.
        """
        # Extract topic — strip question words, take remaining
        stop = {"what", "is", "the", "a", "an", "of", "who", "when",
                "where", "why", "how", "are", "was", "were", "do",
                "does", "did", "can", "could", "should", "would",
                "cái", "gì", "là", "của", "ai", "khi", "đâu",
                "tại", "sao", "như", "thế", "nào", "những", "các",
                "một", "và", "hoặc", "cho", "về"}
        # Remove punctuation
        q_clean = re.sub(r"[?.!,;:'\"]", " ", q).strip()
        words = [w for w in q_clean.split() if w.lower() not in stop and len(w) >= 2]
        topic = " ".join(words[:3]) if words else q_clean.split()[0] if q_clean else ""
        if not topic:
            return {"verdict": "UNKNOWN", "reason": "no topic extracted",
                    "real_value": None, "source": "wikipedia"}
        # For Vietnamese questions, also try Vietnamese Wikipedia
        wiki_lang = "vi" if any(ord(c) > 127 for c in q) else "en"
        try:
            # REST summary endpoint — uses page title (spaces → underscores, URL-encoded)
            from urllib.parse import quote
            topic_path = quote(topic.replace(" ", "_"))
            resp = self._session_get(
                f"https://{wiki_lang}.wikipedia.org/api/rest_v1/page/summary/{topic_path}",
                timeout=5.0,
                headers={"Accept": "application/json"},
            )
            data = resp.json()
            extract = data.get("extract") or ""
            title = data.get("title") or topic
            if not extract:
                return {"verdict": "UNKNOWN", "reason": "no wikipedia extract",
                        "real_value": title, "source": "wikipedia.org"}
            # Check if answer tokens appear in extract (normalize both)
            extract_norm = self._normalize_text(extract)
            answer_norm = self._normalize_text(a)
            if not answer_norm:
                return {"verdict": "UNKNOWN", "reason": "empty answer",
                        "real_value": title, "source": "wikipedia.org"}
            # Token-overlap check
            ans_tokens = [t for t in answer_norm.split() if len(t) >= 3]
            if not ans_tokens:
                return {"verdict": "UNKNOWN", "reason": "answer too short",
                        "real_value": title, "source": "wikipedia.org"}
            overlap = sum(1 for t in ans_tokens if t in extract_norm)
            coverage = overlap / len(ans_tokens)
            # PASS if ≥50% of answer tokens appear in Wikipedia extract
            ok = coverage >= 0.5 or answer_norm in extract_norm
            return {
                "verdict": "PASS" if ok else "FAIL",
                "reason": f"wikipedia coverage={coverage:.0%} for topic '{title}'",
                "real_value": title,
                "source": f"{wiki_lang}.wikipedia.org",
            }
        except Exception as e:
            logger.debug("wikipedia verify failed: %s", e, exc_info=True)
            return {"verdict": "UNKNOWN",
                    "reason": f"wikipedia call failed: {e}",
                    "real_value": None, "source": "error"}
