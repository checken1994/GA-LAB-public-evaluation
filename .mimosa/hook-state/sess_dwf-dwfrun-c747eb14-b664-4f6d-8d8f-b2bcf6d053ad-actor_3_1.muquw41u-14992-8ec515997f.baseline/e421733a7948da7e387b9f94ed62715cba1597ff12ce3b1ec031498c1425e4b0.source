"""
[Capability 2] Vector DB / Embedding — semantic search thay thế TF-IDF.

TÁI SAO: domain_store hiện dùng keyword matching (≥2 tokens) → sai nhiều.
Embedding search hiểu semantic: "thủ đô" ≈ "capital city" ≈ "thành phố chính".

Uses: sentence-transformers (local, free) + SQLite vector storage.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3

logger = logging.getLogger("scp.capabilities.vector_db")

class VectorStore:
    """Lightweight vector store using SQLite + sentence-transformers."""

    def __init__(self, db_path: str = "data/vectors.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._model = None
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS vectors (
            id TEXT PRIMARY KEY,
            text TEXT, embedding BLOB, metadata TEXT, timestamp TEXT
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_text ON vectors(text)")
        conn.commit()
        conn.close()

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                logger.warning("sentence-transformers not installed — vector DB disabled")
                return None
        return self._model

    def add(self, text: str, metadata: dict | None = None):
        model = self._get_model()
        if not model: return False
        emb = model.encode(text).tolist()
        vid = hashlib.sha256(text.encode()).hexdigest()[:16]
        # [Fix 4-a-011] Use the actual vector store file's mtime — not the cwd's
        # mtime (`os.path.getmtime('.')`). The cwd mtime reflects ANY file
        # creation/deletion in the working directory (e.g. log rotation, cache
        # writes), so the timestamp had nothing to do with the vector record
        # and was effectively a random wall-clock-ish value.
        store_mtime = os.path.getmtime(self.db_path)
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT OR REPLACE INTO vectors VALUES (?,?,?,?,?)",
                     (vid, text, json.dumps(emb), json.dumps(metadata or {}), str(store_mtime)))
        conn.commit()
        conn.close()
        return True

    def search(self, query: str, limit: int = 5) -> list[dict]:
        model = self._get_model()
        if not model: return []
        query_emb = model.encode(query)
        # [Fix 4-a-011 — known limitation, DNA #23 honest limit]
        # Loads all vectors (capped at 1000) into memory + computes cosine
        # similarity in pure Python. Acceptable for small stores (≤1000 rows)
        # but O(N×D) per query becomes a bottleneck at scale. Phase 8+ should
        # migrate to faiss (HNSW/IVF) or sqlite-vec for O(log N) ANN search.
        # Tracked as known limitation — NOT a regression vs prior behaviour
        # (the old code had the same LIMIT 1000 + in-memory cosine loop).
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT id, text, embedding, metadata FROM vectors LIMIT 1000").fetchall()
        results = []
        for _rid, text, emb_str, meta_str in rows:
            emb = json.loads(emb_str)
            # Cosine similarity
            import math
            dot = sum(a*b for a,b in zip(query_emb, emb))
            norm_q = math.sqrt(sum(a*a for a in query_emb))
            norm_e = math.sqrt(sum(b*b for b in emb))
            sim = dot / (norm_q * norm_e + 1e-8)
            results.append({"text": text, "score": sim, "metadata": json.loads(meta_str)})
        results.sort(key=lambda x: -x["score"])
        conn.close()
        return results[:limit]
