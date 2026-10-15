import json
import os
from pathlib import Path

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

from scp.rag.canonical_retriever import CanonicalRetriever, HybridRetriever, _tokens


def test_rag_isolated_flow(tmp_path: Path):
    """FA-13: Cover RAG flow with genuine behavioral execution.

    Verifies stopword stripping in _tokens, CanonicalRetriever fallback when corpus
    is absent, and HybridRetriever indexing and BM25/term matching across corpus chunks.
    """
    # 1. Behavioral: Tokenizer cleans stop words, normalizes suffixes
    tokens = _tokens("The quick brown fox jumps over the lazy dog")
    assert "the" not in tokens
    assert "quick" in tokens
    assert "brown" in tokens

    # 2. Behavioral: CanonicalRetriever graceful empty retrieval when no corpus exists
    empty_retriever = CanonicalRetriever(root=tmp_path / "empty_root")
    assert empty_retriever.retrieve("nonexistent search query") == []

    # 3. Behavioral: HybridRetriever indexes and searches corpus chunks
    corpus_dir = tmp_path / "data" / "rag_corpus" / "canonical-v2-20260817"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    doc_1 = {
        "final_url": "https://docs.python.org/3/tutorial/",
        "source_title": "Python Language Tutorial",
        "chunks": [
            {
                "chunk_id": "py-chunk-1",
                "document_id": "doc-py",
                "text": "Python language emphasizes code readability and software development.",
            }
        ],
    }
    (corpus_dir / "corpus_all_fetched.jsonl").write_text(json.dumps(doc_1) + "\n", encoding="utf-8")

    hybrid = HybridRetriever(root=tmp_path)
    results = hybrid.search(query="python language development", top_k=2)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "py-chunk-1"
    assert results[0]["document_id"] == "doc-py"
    assert "term_coverage" in results[0]
    assert results[0]["term_coverage"] > 0.0
