"""[REPR-INJECTION-FIX + ENV-LEAK-FIX] Regression tests for evidence_replay.

(a) build_characterization_test used to embed the probe-observed repr TEXT
    verbatim into generated pytest source. A hostile candidate controls that
    text via a custom __repr__ (arbitrary quotes/newlines/expression text),
    so the generated test file could break out of the assert and execute
    injected code (e.g. ``assert f(1) == 0 or __import__('os').system(...) or 0``).
    The repr is now pinned as an ESCAPED STRING LITERAL via repr(result_repr)
    with a string-match assert; args_expr must parse as a pure literal list
    or the record is not pinned (fail-closed).

(b) run_test() used to pass the FULL host environment to the B/S/G subprocess
    while the probe legs already used _minimal_probe_env() — host env leaked
    into replay subprocesses. run_test now uses the same minimal env.
"""
import ast as _ast
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

from scp.autofix.evidence_replay import EvidenceReplay, build_characterization_test

_FORBIDDEN_CALL_NAMES = {"open", "eval", "exec", "compile", "__import__", "input", "breakpoint"}


def _record(result_repr, args_expr="1", name="f") -> dict:
    return {
        "callable": name,
        "exercised": True,
        "pinnable": True,
        "result_repr": result_repr,
        "error": None,
        "async": False,
        "args_expr": args_expr,
    }


def _assert_no_injection(generated_source: str, module_stem: str = "cand_mod") -> None:
    tree = _ast.parse(generated_source)
    # `ast` is allowed ONLY for [REPR-HASH-ORDER-FIX]: ast.literal_eval is
    # literal-only and cannot execute. Any other ast.* use is injection.
    allowed_imports = {"asyncio", "os", "sys", "ast", module_stem}
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            # The harness only imports asyncio/os/sys/ast + the module under test;
            # anything else is injection.
            for alias in node.names:
                assert alias.name.split(".")[0] in allowed_imports, (
                    f"injected import: {alias.name}"
                )
        elif isinstance(node, _ast.ImportFrom):
            module = getattr(node, "module", None)
            assert module in allowed_imports, f"injected import-from: {module}"
        if (
            isinstance(node, _ast.Call)
            and isinstance(node.func, _ast.Attribute)
            and isinstance(node.func.value, _ast.Name)
            and node.func.value.id == "ast"
        ):
            assert node.func.attr == "literal_eval", (
                f"injected ast.{node.func.attr} call in generated test"
            )
        if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name):
            assert node.func.id not in _FORBIDDEN_CALL_NAMES, (
                f"injected call to {node.func.id} in generated test"
            )


class TestCharacterizationTestInjectionHardening:
    def test_expression_breakout_cannot_inject_calls(self):
        # Parses as valid Python when embedded verbatim (the worst case):
        # `assert cand_mod.f(1) == 0 or __import__('os').system('PWNED') or 0`
        hostile = "0 or __import__('os').system('PWNED') or 0"
        src = build_characterization_test([_record(hostile)], "cand_mod")
        assert src is not None
        _assert_no_injection(src)
        assert "assert repr(cand_mod.f(1)) == " in src

    def test_quote_and_newline_breakout_cannot_break_the_file(self):
        hostile = "' or open('secret.txt') and ('\nimport subprocess\nsubprocess.run('PWNED')\n#"
        src = build_characterization_test([_record(hostile)], "cand_mod")
        assert src is not None
        # BEFORE the fix this payload both broke syntax AND (payload variants)
        # injected executable statements; now it must parse as pure literals.
        _assert_no_injection(src)

    def test_multi_line_repr_is_pinned_as_single_escaped_literal(self):
        hostile = "line1\nline2\nline3"
        src = build_characterization_test([_record(hostile)], "cand_mod")
        assert src is not None
        body_lines = [ln for ln in src.splitlines() if "assert repr(" in ln]
        assert len(body_lines) == 1, "pinned repr must be one escaped literal line"
        _assert_no_injection(src)

    def test_honest_repr_still_pins_expected_value(self):
        src = build_characterization_test([_record("42")], "cand_mod")
        assert src is not None
        assert "assert repr(cand_mod.f(1)) == '42'" in src
        _assert_no_injection(src)

    def test_hostile_args_expr_record_is_not_pinned(self):
        bad = _record("42", args_expr="0) if __import__('os').system('PWNED') else (0")
        assert build_characterization_test([bad], "cand_mod") is None

    def test_nothing_pinnable_returns_none_fail_closed(self):
        assert build_characterization_test([], "cand_mod") is None


class TestRunTestMinimalEnv:
    def test_run_test_uses_minimal_probe_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SCP_X_REGRESSION_SENTINEL_9QK", "leak-me")
        replay = EvidenceReplay(working_dir=tmp_path)
        captured = {}
        proc = MagicMock(returncode=0, stdout="", stderr="")

        def fake_run(argv, **kwargs):
            captured.update(kwargs)
            return proc

        with patch("subprocess.run", side_effect=fake_run):
            ok, _snippet = replay.run_test(["python", "-c", "pass"])

        assert ok is True
        assert "env" in captured, "run_test must pass an explicit (minimal) env"
        assert "SCP_X_REGRESSION_SENTINEL_9QK" not in captured["env"], (
            "run_test leaked the full host env into the replay subprocess"
        )
        assert "PATH" in captured["env"], "minimal env must keep process basics"

    def test_run_test_real_execution_still_works_with_minimal_env(self, tmp_path):
        replay = EvidenceReplay(working_dir=tmp_path)
        ok, _ = replay.run_test([sys.executable, "-c", "import sys; sys.exit(0)"])
        assert ok is True
        nok, _ = replay.run_test([sys.executable, "-c", "import sys; sys.exit(3)"])
        assert nok is False


# [REPR-HASH-ORDER-FIX] repr of a set/frozenset iterates in PYTHONHASHSEED-
# dependent order. Probe (observed): repr({'alpha','bravo','charlie','delta',
# 'echo'}) differs between PYTHONHASHSEED=0/1/2 processes, so the old
# `assert repr(call) == '<pinned repr>'` characterization test failed
# spuriously in every fresh replay subprocess → spurious rollback.
# Captured under PYTHONHASHSEED=2:
_PINNED_SEED2_SET_REPR = "{'echo', 'delta', 'alpha', 'bravo', 'charlie'}"

_RUN_GEN_TEST = (
    "import importlib.util, sys;"
    "spec = importlib.util.spec_from_file_location('gen_test', sys.argv[1]);"
    "m = importlib.util.module_from_spec(spec);"
    "spec.loader.exec_module(m);"
    "fns = [v for k, v in sorted(vars(m).items())"
    " if k.startswith('test_replay_') and callable(v)];"
    "assert fns, 'no generated test functions found';"
    "[f() for f in fns];"
    "print('GEN-TEST-OK')"
)


class TestSetReprHashOrderStability:
    def test_set_result_pins_order_free_comparison(self):
        src = build_characterization_test(
            [_record(_PINNED_SEED2_SET_REPR, args_expr="")], "cand_mod"
        )
        assert src is not None
        assert "import ast" in src, "set pin needs ast.literal_eval at runtime"
        assert "sorted(map(repr, cand_mod.f()))" in src
        assert "ast.literal_eval(" in src
        # Injection property unchanged: the pinned text stays INSIDE the
        # escaped string literal; nothing forbidden becomes executable.
        _assert_no_injection(src)

    def test_set_repr_with_breakout_attempt_stays_inside_string_literal(self):
        hostile = "{'a\\nb'} or __import__('os').system('PWNED') or {'b'}"
        src = build_characterization_test([_record(hostile, args_expr="")], "cand_mod")
        assert src is not None
        # Does not parse as a set literal → strict string-match fallback.
        assert "sorted(map(repr, cand_mod.f()))" not in src
        assert "assert repr(cand_mod.f()) == " in src
        _assert_no_injection(src)

    def test_generated_set_test_passes_under_two_hash_seeds(self, tmp_path):
        src = build_characterization_test(
            [_record(_PINNED_SEED2_SET_REPR, args_expr="")], "cand_mod"
        )
        assert src is not None
        (tmp_path / "cand_mod.py").write_text(
            "def f():\n"
            "    return {'alpha', 'bravo', 'charlie', 'delta', 'echo'}\n",
            encoding="utf-8",
        )
        test_path = tmp_path / "test_gen_replay.py"
        test_path.write_text(src, encoding="utf-8")
        for seed in ("0", "1"):
            proc = subprocess.run(
                [sys.executable, "-c", _RUN_GEN_TEST, str(test_path)],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONHASHSEED": seed},
                timeout=120,
            )
            assert proc.returncode == 0, (
                f"generated set pin failed under PYTHONHASHSEED={seed}: "
                f"{proc.stdout}\n{proc.stderr}"
            )
            assert "GEN-TEST-OK" in proc.stdout

    def test_non_set_repr_keeps_string_compare_and_no_ast_import(self):
        src = build_characterization_test([_record("42")], "cand_mod")
        assert src is not None
        assert "import ast" not in src
        assert "assert repr(cand_mod.f(1)) == '42'" in src
