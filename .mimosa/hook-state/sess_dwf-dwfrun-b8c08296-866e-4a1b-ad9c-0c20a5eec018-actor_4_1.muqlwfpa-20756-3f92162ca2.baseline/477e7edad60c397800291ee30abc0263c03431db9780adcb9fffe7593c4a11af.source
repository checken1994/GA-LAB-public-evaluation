from pathlib import Path

"""Reality test for Fix 4-a-017: healing_engine LIKE pattern escape.

Before fix: User error text was interpolated into a SQL LIKE pattern without
escaping `%` and `_`. A search for '50%' matched every row containing '50'
followed by anything; 'a_b' matched 'aXb', 'aYb', etc.

After fix: `%` and `_` are escaped to `\\%` and `\\_` (with backslash itself
escaped first to `\\\\`), and the LIKE clause uses `ESCAPE '\\'` so the
backslash is treated as the escape char inside the pattern.

DNA principles exercised:
  #2  (vòng lặp khép kín — reality test of the fix, not just the fix)
  #9  (no harm — unescaped LIKE = wrong healing suggestion)
  #22 (PASS ≠ TRUE — old code "worked" but matched too broadly)
  #26 (reality test — execute + cross-check)
"""
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

FILE = str(Path(__file__).resolve().parents[2]) + '/scp/core/healing_engine.py'


def test_reality_4_a_017_ast():
    """Verify AST source has escape replacements and ESCAPE clause."""
    assert os.path.isfile(FILE), f"FAIL: file missing: {FILE}"
    with open(FILE, encoding="utf-8") as f:
        src = f.read()

    assert "def get_similar_errors" in src
    assert "ESCAPE" in src


def test_healing_engine_like_escape_behavioral():
    """Behavioral test: SQL query with wildcards % and _ only matches literal characters."""
    from scp.core.db_manager import db_exec
    from scp.core.healing_engine import ErrorHistory

    # Ensure schema exists
    db_exec("""
        CREATE TABLE IF NOT EXISTS error_history (
            timestamp TEXT, question TEXT, ai_answer TEXT, frame TEXT,
            v13_verdict TEXT, final_verdict TEXT, verdict_detail TEXT,
            error_type TEXT, source TEXT, real_value TEXT, ai_value TEXT,
            reason TEXT, sha256 TEXT
        )
    """)

    # Clean test rows from previous runs
    db_exec("DELETE FROM error_history WHERE question LIKE 'TEST_ERR_%'")

    eh = ErrorHistory()

    # Seed test rows
    eh.record("TEST_ERR_50% CPU threshold exceeded", "ans", "f", "v", "f", "d", "e", "s", "1", "2", "r")
    eh.record("TEST_ERR_500 Internal Server Error", "ans", "f", "v", "f", "d", "e", "s", "1", "2", "r")
    eh.record("TEST_ERR_a_b identifier missing", "ans", "f", "v", "f", "d", "e", "s", "1", "2", "r")
    eh.record("TEST_ERR_aXb identifier missing", "ans", "f", "v", "f", "d", "e", "s", "1", "2", "r")

    # 1. Search for literal '%'
    res_percent = eh.get_similar_errors("TEST_ERR_50%")
    matched_questions_percent = [r["question"] for r in res_percent]
    assert "TEST_ERR_50% CPU threshold exceeded" in matched_questions_percent, (
        f"Expected literal '50%' to match, got: {matched_questions_percent}"
    )
    assert "TEST_ERR_500 Internal Server Error" not in matched_questions_percent, (
        "FAIL: unescaped '%' matched '500' incorrectly"
    )

    # 2. Search for literal '_'
    res_underscore = eh.get_similar_errors("TEST_ERR_a_b")
    matched_questions_underscore = [r["question"] for r in res_underscore]
    assert "TEST_ERR_a_b identifier missing" in matched_questions_underscore, (
        f"Expected literal 'a_b' to match, got: {matched_questions_underscore}"
    )
    assert "TEST_ERR_aXb identifier missing" not in matched_questions_underscore, (
        "FAIL: unescaped '_' matched 'aXb' wildcard incorrectly"
    )

    # Teardown test rows
    db_exec("DELETE FROM error_history WHERE question LIKE 'TEST_ERR_%'")


if __name__ == "__main__":
    test_reality_4_a_017_ast()
    test_healing_engine_like_escape_behavioral()
    print("PASS: reality_4-a-017 behavioral test succeeded")
