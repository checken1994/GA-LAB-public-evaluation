import os

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

from pathlib import Path

from scp.brain.error_store import ErrorStore, _is_spam_question


def test_brain_isolated_flow(tmp_path: Path):
    """FA-13: Cover brain flow with genuine behavioral execution.

    Verifies spam question filtering, ErrorStore lifecycle, record persistence,
    and automatic spam rejection on write.
    """
    # 1. Spam question detection: emoji/symbols vs meaningful natural language
    is_spam, reason = _is_spam_question("🇻🇳" * 10)
    assert is_spam is True
    assert reason == "no_content"

    is_valid, _ = _is_spam_question("thủ đô của nước Pháp là gì?")
    assert is_valid is False

    # 2. ErrorStore instantiation with isolated temporary storage
    store_file = tmp_path / "errors.jsonl"
    store = ErrorStore(path=str(store_file))
    assert len(store._records) == 0

    # 3. Add legitimate pipeline error record
    rec = store.add(
        question="What is 2+2?",
        answer="5",
        verdict="FAIL",
        domain="math",
        error_type="calc_error",
        details={"expected": "4"},
    )
    assert rec["question"] == "What is 2+2?"
    assert rec["domain"] == "math"
    assert rec["verdict"] == "FAIL"
    assert len(store._records) == 1

    # 4. Attempting to add spam should be filtered out
    spam_rec = store.add(question="🇻🇳" * 10, answer="spam", verdict="FAIL")
    assert "rejected" in spam_rec
    assert len(store._records) == 1  # Not inserted into error store
