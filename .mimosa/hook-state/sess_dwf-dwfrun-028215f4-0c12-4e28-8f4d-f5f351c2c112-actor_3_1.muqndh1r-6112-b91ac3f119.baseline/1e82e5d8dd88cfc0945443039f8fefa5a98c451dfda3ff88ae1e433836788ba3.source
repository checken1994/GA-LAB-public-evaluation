import json

from scp.rag.canonical_retriever import CanonicalRetriever, _tokens


def test_rag_tokenization_and_stemming():
    tokens = _tokens("The quick brown foxes were jumping quickly in the forest")
    assert "the" not in tokens
    assert "were" not in tokens
    assert "foxes" in tokens
    assert "quick" in tokens

def test_rag_retriever_in_memory_index(tmp_path):
    corpus_dir = tmp_path / "data" / "rag_corpus" / "canonical-v2-20260817"
    corpus_dir.mkdir(parents=True)
    corpus_file = corpus_dir / "corpus_all_fetched.jsonl"
    corpus_file.write_text(json.dumps({
        "source_url": "https://en.wikipedia.org/wiki/Helium",
        "source_title": "Helium Element",
        "chunks": [{"chunk_id": "c1", "document_id": "d1", "text": "Helium is a chemical element with atomic number 2."}]
    }) + "\n", encoding="utf-8")

    retriever = CanonicalRetriever(root=tmp_path)
    results = retriever.retrieve("chemical element helium", k=3)
    assert len(results) > 0
    assert results[0]["chunk_id"] == "c1"

def test_rag_retriever_missing_corpus_fallback(tmp_path):
    from scp.rag.canonical_retriever import CanonicalRetriever
    retriever = CanonicalRetriever(root=tmp_path)
    results = retriever.retrieve("NonExistentQueryForTesting12345")
    assert isinstance(results, list)
    assert retriever.available is False


class _FakeDictShapedDomainKnowledge:
    """[R4-F04-DICT-FIX] DomainKnowledge.search trả về list[dict] thật
    (scp/knowledge/domain_knowledge.py search() build dicts với keys
    question/answer/source_url/...). Fake này tái tạo đúng SHAPE đó."""

    def __init__(self, *args, **kwargs):
        pass

    def search(self, question, domain="", limit=5):
        return [{
            "question": "What is helium?",
            "answer": "Helium is a noble gas with atomic number 2.",
            "domain": "chemistry",
            "source": "knowledge_base",
            "source_url": "https://en.wikipedia.org/wiki/Helium",
            "confidence": 0.9,
            "tier": 1,
        }]


def test_rag_fallback_reads_dict_shaped_domain_knowledge_hits(tmp_path, monkeypatch):
    """Pre-fix: fallback dùng getattr(h, 'answer', '') trên DICT → luôn rỗng
    → phục vụ chunk text rỗng score 1.0 nhưng vẫn log 'served N hits'.
    Post-fix: dict access phải trả non-empty text/title/url."""
    import scp.knowledge.domain_knowledge as dk_mod
    from scp.rag.canonical_retriever import CanonicalRetriever

    monkeypatch.setattr(dk_mod, "DomainKnowledge", _FakeDictShapedDomainKnowledge)
    retriever = CanonicalRetriever(root=tmp_path)
    results = retriever.retrieve("helium noble gas", k=3)
    assert results, "fallback phải phục vụ hits cho dict-shaped search results"
    hit = results[0]
    assert hit["text"].strip() != "", "text không được rỗng (getattr trên dict)"
    assert hit["source_title"].strip() != "", "source_title (question) không được rỗng"
    assert hit["source_url"].startswith("https://"), "source_url không được rỗng"
    assert hit["chunk_id"].startswith("kb_")
    assert hit["score"] == 1.0

def test_hybrid_retriever_search(tmp_path):
    from scp.rag.canonical_retriever import HybridRetriever
    retriever = HybridRetriever(root=tmp_path)
    results = retriever.search("NonExistentQueryForTesting12345", top_k=2)
    assert isinstance(results, list)

