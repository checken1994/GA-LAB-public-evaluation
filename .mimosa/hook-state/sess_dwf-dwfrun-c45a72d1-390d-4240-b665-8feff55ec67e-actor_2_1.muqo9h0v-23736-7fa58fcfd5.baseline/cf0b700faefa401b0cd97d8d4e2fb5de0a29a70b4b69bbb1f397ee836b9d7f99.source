"""Autonomous Evidence Retrieval & Domain Knowledge Store (Milestone 2 - R2).

Provides:
- DomainKnowledge: Unified knowledge store integrating DomainKnowledgeStore and SQLite (knowledge.sqlite3).
- AutonomousEvidenceRetriever: Automatic two-tier evidence retrieval (KB -> Public Web Search) with Quarantine.
- FactSeparator: Separation of verified facts, LLM reasoning, and confidence badge payload.
"""
from __future__ import annotations

import inspect
import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scp.core.top_systems_learning import inspect_untrusted
from scp.knowledge.claim_extractor import Claim, ClaimExtractor
from scp.knowledge.domain_store import DomainKnowledgeStore
from scp.web_control.internet_search import InternetSearch

logger = logging.getLogger("scp.knowledge.autonomous")


@dataclass
class VerifiedFact:
    """A verified factual claim backed by authoritative evidence."""
    claim: str
    source: str  # "knowledge_base" | "web_search"
    url: str | None
    confidence: float
    evidence_snippet: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "source": self.source,
            "url": self.url,
            "confidence": round(float(self.confidence), 4),
            "evidence_snippet": self.evidence_snippet,
        }


@dataclass
class ConfidenceBadge:
    """Confidence & Transparency Badge metadata."""
    badge: str  # "FACT_VERIFIED" | "CONVERSATIONAL" | "UNVERIFIED_CONJECTURE"
    score: float
    sources_consulted: list[str]
    transparency_notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "badge": self.badge,
            "score": round(float(self.score), 2),
            "sources_consulted": list(self.sources_consulted),
            "transparency_notes": self.transparency_notes,
        }


# Comprehensive stop words definition for fact validation (Vietnamese + English)
_VI_STOPWORDS = {
    "là", "của", "và", "các", "có", "trong", "cho", "với", "được", "về",
    "đến", "khi", "những", "thì", "đó", "này", "một", "như", "theo", "tại",
    "người", "đã", "sẽ", "đang", "từ", "ra", "vào", "lại", "qua", "đây",
    "gì", "nào", "sao", "ai", "đâu", "ở", "làm", "rất", "nhiều", "cũng",
    "thủ", "đô", "nhưng", "bởi", "vì", "để", "nếu", "hay", "hoặc"
}
_EN_STOPWORDS = {
    "the", "is", "at", "which", "on", "and", "a", "an", "in", "to", "for",
    "of", "with", "as", "by", "that", "this", "it", "from", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "what", "who", "when", "where", "why", "how", "but", "not", "or"
}
ALL_FACT_STOPWORDS = _VI_STOPWORDS | _EN_STOPWORDS


def _extract_content_tokens(text: str) -> set[str]:
    """Extract content tokens (excluding stopwords and short noise)."""
    words = re.findall(r"[\wÀ-ỹ]+", text.lower())
    return {w for w in words if len(w) >= 2 and w not in ALL_FACT_STOPWORDS}


def _extract_capitalized_entities(text: str) -> set[str]:
    """Extract capitalized entity tokens from text (excluding stopwords)."""
    return {w.lower() for w in re.findall(r"\b[A-ZÀ-Ỹ][a-zà-ỹ]*\b", text)} - ALL_FACT_STOPWORDS



class DomainKnowledge:
    """Unified access to DomainKnowledgeStore and SQLite knowledge base (knowledge.sqlite3)."""

    def __init__(
        self,
        data_dir: str = "data/knowledge",
        sqlite_path: str = "data/knowledge.sqlite3",
    ) -> None:
        self.data_dir = Path(data_dir)
        self.sqlite_path = Path(sqlite_path)
        self.store_impl = DomainKnowledgeStore(data_dir=str(self.data_dir))
        self._init_sqlite()

    def _init_sqlite(self) -> None:
        """Initialize SQLite table for knowledge records if sqlite_path is configured."""
        try:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_records (
                        id TEXT PRIMARY KEY,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        domain TEXT NOT NULL,
                        source TEXT NOT NULL,
                        source_url TEXT,
                        confidence REAL DEFAULT 0.5,
                        collected_at REAL,
                        expires_at REAL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_kr_domain ON knowledge_records(domain);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_kr_question ON knowledge_records(question);")
        except Exception as exc:
            logger.warning("[DomainKnowledge] SQLite init failed (%s): %s", type(exc).__name__, exc, exc_info=True)

    def store(
        self,
        question: str,
        answer: str,
        domain: str = "general",
        source: str = "knowledge_base",
        source_url: str = "",
        confidence: float = 0.95,
        collected_by: str = "on_demand",
    ) -> Any:
        """Store knowledge in both DomainKnowledgeStore and SQLite."""
        # 1. JSONL store
        record = self.store_impl.store(
            question=question,
            answer=answer,
            domain=domain,
            source=source,
            source_url=source_url,
            confidence=confidence,
            collected_by=collected_by,
        )

        # 2. SQLite store
        try:
            rec_id = getattr(record, "id", None) or f"kr_{int(time.time()*1000)}"
            now = time.time()
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO knowledge_records
                    (id, question, answer, domain, source, source_url, confidence, collected_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (rec_id, question, answer, domain, source, source_url, confidence, now, 0),
                )
        except Exception as exc:
            logger.debug("[DomainKnowledge] SQLite store error: %s", exc, exc_info=True)

        return record

    def search(self, question: str, domain: str = "", limit: int = 5) -> list[dict[str, Any]]:
        """Search both in-memory/JSONL cache and SQLite store for matching records."""
        results: list[dict[str, Any]] = []
        seen_answers: set[str] = set()

        # 1. Search DomainKnowledgeStore
        try:
            records = self.store_impl.search(question, domain=domain, limit=limit)
            for r in records:
                ans = str(getattr(r, "answer", "")).strip()
                if ans and ans not in seen_answers:
                    seen_answers.add(ans)
                    results.append({
                        "question": getattr(r, "question", ""),
                        "answer": ans,
                        "domain": getattr(r, "domain", domain or "general"),
                        "source": getattr(r, "source", "knowledge_base"),
                        "source_url": getattr(r, "source_url", "") or getattr(r, "url", ""),
                        "confidence": float(getattr(r, "confidence", 0.9)),
                        "tier": int(getattr(r, "source_tier", 1)),
                    })
        except Exception as exc:
            logger.warning("[DomainKnowledge] Store search failed: %s", exc, exc_info=True)

        # 2. Fallback query SQLite if needed
        if len(results) < limit and self.sqlite_path.exists():
            try:
                with sqlite3.connect(self.sqlite_path) as conn:
                    conn.row_factory = sqlite3.Row
                    q_tokens = [w for w in question.lower().split() if len(w) > 2]
                    for token in q_tokens[:3]:
                        rows = conn.execute(
                            "SELECT * FROM knowledge_records WHERE lower(question) LIKE ? OR lower(answer) LIKE ? LIMIT ?",
                            (f"%{token}%", f"%{token}%", limit),
                        ).fetchall()
                        for row in rows:
                            ans = str(row["answer"]).strip()
                            if ans and ans not in seen_answers:
                                seen_answers.add(ans)
                                results.append({
                                    "question": row["question"],
                                    "answer": ans,
                                    "domain": row["domain"],
                                    "source": row["source"],
                                    "source_url": row["source_url"] or "",
                                    "confidence": float(row["confidence"]),
                                    "tier": 1,
                                })
            except Exception as exc:
                logger.debug("[DomainKnowledge] SQLite query error: %s", exc, exc_info=True)

        return results[:limit]


class AutonomousEvidenceRetriever:
    """Autonomous Evidence Retriever with Knowledge Base lookup and Safe Public Web Search."""

    def __init__(
        self,
        kb: DomainKnowledge | DomainKnowledgeStore | None = None,
        searcher: InternetSearch | None = None,
    ) -> None:
        if kb is None:
            self.kb = DomainKnowledge()
        elif isinstance(kb, DomainKnowledgeStore):
            self.kb = kb
        else:
            self.kb = kb
        self.searcher = searcher or InternetSearch()

    async def retrieve(
        self,
        question: str,
        current_confidence: float = 0.5,
        domain: str = "general",
        allow_web: bool = True,
    ) -> dict[str, Any]:
        """Perform autonomous evidence retrieval.
        
        Triggers when current_confidence < 0.7 or when context is insufficient.
        (a) Queries internal Knowledge Base.
        (b) If KB is insufficient, queries safe public web search.
        (c) Applies Data Quarantine via inspect_untrusted to all web snippets.
        """  # noqa: W291,W293  # [hygiene-keep] whitespace inside string/docstring - keep content verbatim
        output: dict[str, Any] = {
            "retrieval_triggered": False,
            "kb_hits": [],
            "web_search_hits": [],
            "quarantined_hits": [],
            "sources_consulted": [],
            "clean_evidence_snippets": [],
            "confidence": current_confidence,
        }

        should_retrieve = current_confidence < 0.7
        if not should_retrieve:
            # Check if query is explicitly asking a factual question
            q_lower = question.lower()
            factual_keywords = (
                "là gì", "ở đâu", "ai là", "thủ đô", "bao nhiêu", "năm nào",
                "mấy", "khi nào", "what is", "where is", "who is", "when did",
                "how many", "capital of", "speed of", "diện tích", "dân số",
            )
            if any(kw in q_lower for kw in factual_keywords):
                should_retrieve = True

        if not should_retrieve:
            return output

        output["retrieval_triggered"] = True

        # (a) Query internal Knowledge Base
        kb_matches: list[dict[str, Any]] = []
        try:
            if hasattr(self.kb, "search"):
                res = self.kb.search(question, domain=domain, limit=5)
                # Normalize results
                for item in res:
                    if hasattr(item, "answer"):
                        kb_matches.append({
                            "question": getattr(item, "question", ""),
                            "answer": getattr(item, "answer", ""),
                            "domain": getattr(item, "domain", domain),
                            "source": getattr(item, "source", "knowledge_base"),
                            "source_url": getattr(item, "source_url", ""),
                            "confidence": float(getattr(item, "confidence", 0.9)),
                        })
                    elif isinstance(item, dict):
                        kb_matches.append(item)
        except Exception as exc:
            logger.warning("[AutonomousRetriever] KB query error: %s", exc, exc_info=True)

        if kb_matches:
            output["kb_hits"] = kb_matches
            output["sources_consulted"].append("knowledge_base")
            for m in kb_matches:
                output["clean_evidence_snippets"].append(m["answer"])
            output["confidence"] = max(current_confidence, 0.90)

        # (b) If KB does not have sufficient evidence, trigger Safe Public Web Search
        if not kb_matches and allow_web:
            try:
                search_call = self.searcher.search(question, max_results=5)
                if inspect.isawaitable(search_call):
                    web_res = await search_call
                else:
                    web_res = search_call

                raw_items: list[dict[str, Any]] = []
                if isinstance(web_res, dict):
                    raw_items = web_res.get("results", []) or []
                elif isinstance(web_res, list):
                    raw_items = web_res

                if raw_items:
                    output["sources_consulted"].append("web_search")

                for item in raw_items:
                    snippet = str(item.get("snippet", "") or item.get("title", "")).strip()
                    url = str(item.get("url", "")).strip()
                    if not snippet:
                        continue

                    # (c) Data Quarantine: inspect_untrusted
                    quarantined, reason = inspect_untrusted(snippet)
                    if quarantined:
                        logger.warning(
                            "[AutonomousRetriever] Quarantine BLOCKED untrusted web snippet: %s",
                            reason,
                        )
                        output["quarantined_hits"].append({
                            "source": "web_search",
                            "url": url,
                            "evidence_snippet": snippet,
                            "quarantined": True,
                            "quarantine_reason": reason,
                            "quarantine_verdict": "BLOCKED",
                        })
                    else:
                        evidence_item = {
                            "source": "web_search",
                            "url": url,
                            "evidence_snippet": snippet,
                            "quarantined": False,
                            "quarantine_verdict": "SAFE",
                        }
                        output["web_search_hits"].append(evidence_item)
                        output["clean_evidence_snippets"].append(snippet)

                if output["web_search_hits"]:
                    output["confidence"] = max(current_confidence, 0.85)

            except Exception as exc:
                logger.warning("[AutonomousRetriever] Web search fallback error: %s", exc, exc_info=True)

        return output


class FactSeparator:
    """Separates verified factual claims from LLM reasoning and assigns confidence badge."""

    def __init__(self, claim_extractor: ClaimExtractor | None = None) -> None:
        self.claim_extractor = claim_extractor or ClaimExtractor()

    def separate(
        self,
        question: str,
        answer: str,
        lane: str = "LANE_CHATBOT",
        confidence: float = 0.85,
        retrieval_result: dict[str, Any] | None = None,
        contexts: list[str] | None = None,
    ) -> dict[str, Any]:
        """Produce structured payload separating verified_facts, llm_reasoning, and confidence_badge."""
        retrieval_result = retrieval_result or {}
        contexts = contexts or []
        clean_snippets: list[str] = list(retrieval_result.get("clean_evidence_snippets", []))
        clean_snippets.extend([str(c) for c in contexts if str(c).strip()])

        # If conversational chit-chat with no external factual grounding needed
        is_conversational_lane = (lane == "LANE_CHATBOT" or lane == "CHATBOT")
        if is_conversational_lane and not clean_snippets:
            return {
                "verified_facts": [],
                "llm_reasoning": answer,
                "confidence_badge": ConfidenceBadge(
                    badge="CONVERSATIONAL",
                    score=max(confidence, 0.85) if confidence >= 0.0 else 0.85,
                    sources_consulted=[],
                    transparency_notes="Conversational chit-chat or reasoning without external factual dependencies.",
                ).to_dict(),
            }

        # Extract claims from the answer
        extracted_claims = self.claim_extractor.extract(answer, question)
        verified_facts: list[dict[str, Any]] = []
        seen_claims: set[str] = set()

        # Match extracted claims against KB hits
        kb_hits = retrieval_result.get("kb_hits", [])
        for claim in extracted_claims:
            claim_text = claim.text.strip()
            if not claim_text or claim_text in seen_claims:
                continue

            matched = False
            # Check KB
            for kb_hit in kb_hits:
                kb_ans = kb_hit.get("answer", "")
                if self._is_match(claim, kb_ans):
                    verified_facts.append(VerifiedFact(
                        claim=claim_text,
                        source="knowledge_base",
                        url=kb_hit.get("source_url") or None,
                        confidence=min(1.0, max(float(kb_hit.get("confidence", 0.95)), 0.90)),
                        evidence_snippet=kb_ans,
                    ).to_dict())
                    seen_claims.add(claim_text)
                    matched = True
                    break

            if matched:
                continue

            # Check clean web search hits
            for web_hit in retrieval_result.get("web_search_hits", []):
                snippet = web_hit.get("evidence_snippet", "")
                if self._is_match(claim, snippet):
                    verified_facts.append(VerifiedFact(
                        claim=claim_text,
                        source="web_search",
                        url=web_hit.get("url") or None,
                        confidence=0.88,
                        evidence_snippet=snippet,
                    ).to_dict())
                    seen_claims.add(claim_text)
                    matched = True
                    break

            if matched:
                continue

            # Check direct contexts
            for ctx in contexts:
                if self._is_match(claim, ctx):
                    verified_facts.append(VerifiedFact(
                        claim=claim_text,
                        source="knowledge_base",
                        url=None,
                        confidence=0.92,
                        evidence_snippet=ctx,
                    ).to_dict())
                    seen_claims.add(claim_text)
                    break

        # Fallback for factual answers if regex claim extractor didn't isolate structured claims
        if not verified_facts and clean_snippets:
            # Check if answer sentences align with clean snippets
            sentences = [s.strip() for s in re.split(r"[.!?\n]+", answer) if len(s.strip()) > 8]
            for sentence in sentences:
                s_content = _extract_content_tokens(sentence)
                if len(s_content) < 3:
                    continue
                s_entities = _extract_capitalized_entities(sentence)
                for snippet in clean_snippets:
                    snip_content = _extract_content_tokens(snippet)
                    snip_lower = snippet.lower()

                    # Semantic entity constraint: any entity declared in sentence must appear in snippet
                    if s_entities and any(ent not in snip_lower for ent in s_entities):
                        continue

                    overlap = s_content & snip_content
                    # [R4-F01] Require minimum 3 content tokens AND >= 60% content overlap
                    if len(overlap) >= 3 and (len(overlap) / len(s_content) >= 0.60):
                        src = "web_search" if any(h.get("evidence_snippet") == snippet for h in retrieval_result.get("web_search_hits", [])) else "knowledge_base"
                        url_val = None
                        if src == "web_search":
                            for h in retrieval_result.get("web_search_hits", []):
                                if h.get("evidence_snippet") == snippet:
                                    url_val = h.get("url")
                                    break
                        elif src == "knowledge_base":
                            for h in kb_hits:
                                if h.get("answer") == snippet:
                                    url_val = h.get("source_url") or None
                                    break
                        verified_facts.append(VerifiedFact(
                            claim=sentence,
                            source=src,
                            url=url_val,
                            confidence=0.92 if src == "knowledge_base" else 0.85,
                            evidence_snippet=snippet,
                        ).to_dict())
                        break

        # Sources consulted
        sources_consulted = list(set([f["source"] for f in verified_facts]))
        if not sources_consulted:
            sources_consulted = list(retrieval_result.get("sources_consulted", []))

        # Compute overall confidence score considering verified facts
        fact_confidence = max([f["confidence"] for f in verified_facts], default=0.0)
        effective_confidence = max(confidence, fact_confidence) if verified_facts else confidence

        # Assign confidence badge
        if verified_facts and effective_confidence >= 0.70:
            badge_name = "FACT_VERIFIED"
            score = max(effective_confidence, 0.80)
            notes = "All claims backed by authoritative sources."
        elif is_conversational_lane:
            badge_name = "CONVERSATIONAL"
            score = max(confidence, 0.85)
            notes = "Conversational chit-chat or reasoning without external factual dependencies."
        else:
            badge_name = "UNVERIFIED_CONJECTURE"
            score = min(effective_confidence, 0.65) if effective_confidence >= 0.70 else max(0.1, effective_confidence)
            notes = "Claims could not be verified against authoritative sources; answer contains unverified conjecture."

        # Separate LLM reasoning from verified facts
        if verified_facts:
            llm_reasoning = f"Mô hình tổng hợp và kiểm chứng {len(verified_facts)} mệnh đề dựa trên các nguồn tri thức đã xác thực."
        elif is_conversational_lane:
            llm_reasoning = answer
        else:
            llm_reasoning = f"Suy đoán mô hình chưa đủ chứng cứ đối chiếu (độ tin cậy: {score:.0%})."

        return {
            "verified_facts": verified_facts,
            "llm_reasoning": llm_reasoning,
            "confidence_badge": ConfidenceBadge(
                badge=badge_name,
                score=score,
                sources_consulted=sources_consulted,
                transparency_notes=notes,
            ).to_dict(),
        }

    @staticmethod
    def _is_match(claim: Claim, text: str) -> bool:
        """Check if claim matches evidence text with strict entity and token constraints."""
        text_lower = text.lower()
        claim_lower = claim.text.lower()

        # Entity constraints: if entity or target are declared, they MUST be present in evidence
        if claim.entity and claim.entity.lower() not in text_lower:
            return False
        if claim.target and claim.target.lower() not in text_lower:
            return False

        # If both entity and target are present in evidence, check for match
        if claim.entity and claim.target:
            if claim.entity.lower() in text_lower and claim.target.lower() in text_lower:
                return True

        if claim_lower in text_lower:
            return True

        # Numeric check with word boundary (prevent single-digit '0' or '1' substring match)
        if claim.value is not None:
            val_str = str(claim.value)
            if re.search(rf"\b{re.escape(val_str)}\b", text_lower):
                return True
            int_str = str(int(claim.value))
            if re.search(rf"\b{re.escape(int_str)}\b", text_lower):
                return True

        # Content token overlap check (excluding stopwords)
        c_content = _extract_content_tokens(claim.text)
        t_content = _extract_content_tokens(text)
        if c_content and t_content:
            overlap = c_content & t_content
            # Require minimum 3 content tokens AND >= 60% overlap ratio
            if len(overlap) >= 3 and (len(overlap) / len(c_content)) >= 0.60:
                c_ents = _extract_capitalized_entities(claim.text)
                if c_ents and any(e not in text_lower for e in c_ents):
                    return False
                return True
        return False

