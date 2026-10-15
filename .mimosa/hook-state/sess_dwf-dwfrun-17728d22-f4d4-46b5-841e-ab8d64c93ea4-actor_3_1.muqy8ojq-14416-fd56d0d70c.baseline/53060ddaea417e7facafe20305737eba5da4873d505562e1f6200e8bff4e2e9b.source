from scp.sandbox_evaluator.evaluator import evaluate


def test_sandbox_evaluator_rejects_missing_tests():
    result = evaluate({"files": {"mod.py": "x = 1"}})
    assert result.verdict == "FAIL"
    assert "no_tests" in result.reason

def test_sandbox_evaluator_executes_passing_pytest():
    patch_target = {
        "files": {"calc.py": "def add(a, b): return a + b\n"},
        "test_files": {"test_calc.py": "from calc import add\ndef test_add(): assert add(2, 3) == 5\n"},
        "timeout_seconds": 10,
    }
    result = evaluate(patch_target)
    assert result.verdict == "PASS"
    assert result.returncode == 0
    assert result.duration_seconds > 0

def test_sandbox_evaluator_catches_failing_assertion():
    patch_target = {
        "files": {"calc.py": "def add(a, b): return a - b\n"},
        "test_files": {"test_calc.py": "from calc import add\ndef test_add(): assert add(2, 3) == 5\n"},
        "timeout_seconds": 10,
    }
    result = evaluate(patch_target)
    assert result.verdict == "FAIL"
    assert result.reason == "test_failed"
