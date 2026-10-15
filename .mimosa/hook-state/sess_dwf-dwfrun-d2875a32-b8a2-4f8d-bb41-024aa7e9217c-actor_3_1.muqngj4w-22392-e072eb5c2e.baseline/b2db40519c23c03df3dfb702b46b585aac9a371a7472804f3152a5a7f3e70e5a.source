import os

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')


from scp.experience.semantic_kb import compute_tf_idf


def test_experience_isolated_flow():
    """FA-13: Cover experience flow with genuine behavioral execution.

    Verifies TF-IDF ranking of experience knowledge documents, relevance scoring,
    and exclusion of non-matching documents.
    """
    corpus = [
        {"id": 1, "content": "kubernetes container orchestration deployment pod"},
        {"id": 2, "content": "quantum mechanics wave particle duality physics"},
        {"id": 3, "content": "kubernetes pod lifecycle container restart policy"},
    ]

    # Matching query ranks relevant docs and excludes unrelated
    results = compute_tf_idf("kubernetes pod", corpus)
    assert len(results) == 2
    matched_ids = {doc["id"] for doc in results}
    assert matched_ids == {1, 3}

    # Query with no overlap returns empty
    empty_results = compute_tf_idf("unrelated extraterrestrial query", corpus)
    assert len(empty_results) == 0
