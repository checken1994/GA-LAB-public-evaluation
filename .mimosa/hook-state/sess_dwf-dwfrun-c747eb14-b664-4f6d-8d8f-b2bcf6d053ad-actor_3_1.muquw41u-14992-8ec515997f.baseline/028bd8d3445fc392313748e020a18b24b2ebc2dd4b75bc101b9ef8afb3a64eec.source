"""
[Capability 7] RAG (Retrieval Augmented Generation).

TÁI SAO: KB search hiện dùng TF-IDF (keyword). RAG dùng embedding → semantic search.
"thủ đô Việt Nam" tìm được "Hà Nội là capital của Vietnam" (không cần exact keyword).

Pipeline: question → embed → vector search KB → augment prompt → LLM → verify
"""
from __future__ import annotations

import logging

logger = logging.getLogger("scp.capabilities.rag")

class RAGEngine:
    """Retrieval Augmented Generation with SCP verification."""

    def __init__(self):
        from scp.capabilities.vector_db import VectorStore
        self.vector_store = VectorStore()

    def retrieve(self, question: str, limit: int = 5) -> list[dict]:
        """Retrieve relevant KB entries via vector similarity."""
        return self.vector_store.search(question, limit=limit)

    def augment(self, question: str, retrieved: list[dict]) -> str:
        """Augment question with retrieved context."""
        if not retrieved:
            return question
        context = "\n".join([f"- {r['text'][:200]}" for r in retrieved[:3]])
        return f"Context:\n{context}\n\nQuestion: {question}"

    def answer(self, question: str) -> dict:
        """Full RAG pipeline: retrieve → augment → LLM → verify."""
        # 1. Retrieve
        retrieved = self.retrieve(question)
        # 2. Augment
        augmented = self.augment(question, retrieved)
        # 3. LLM (via gateway)
        from scp.llm_gateway import chat_sync
        answer, provider = chat_sync(augmented)
        # 4. Return (verification done by judge.py)
        return {
            "question": question,
            "answer": answer or "",
            "retrieved": retrieved,
            "provider": provider,
        }
