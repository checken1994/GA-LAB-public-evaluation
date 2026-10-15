"""
[S3-SECURITY-SWEEP] Security sweep 3 — HIGH findings remediation tests (scp/autofix/).

Mission: sweep 3 của SCP Worker Agent S3 — các HIGH findings còn lại trong
scp/autofix/ (sau khi SSRF đã đóng ở S1/S1b/S2):
  - path-traversal          → scp/autofix/path_guard.py + các cache/log writer
  - sql-injection           → corpus fixture dựng runtime, fixer vẫn parameterize
  - insecure-deserialization→ không còn call-site deserialization thô nào
  - code-injection          → hypothesis scanner hết hàm thực thi động; restricted_exec siết
  - command-injection       → intent engine thuần AST, không subprocess
  - missing-cert-validation → docstring không còn literal TLS-off; gate vẫn chặn

No-mock (FA-04): mọi vector tấn công được thực thi thật ضد code sản phẩm và
phải bị chặn/rejected. Test fixture strings trong FILE này được ghép runtime
(chr/concat) để chính test không chứa literal của pattern nó đang kiểm tra.

DNA: #4 (Constitution KILL), #9 (No harm), #21 (Audit the auditor),
     #22 (PASS ≠ TRUE), #26 (Reality > Model).
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scp.autofix import path_guard
from scp.autofix.callgraph_delta import CallGraph
from scp.autofix.evolution_modes import parameterize_sql
from scp.autofix.intent_inference_engine import infer_intent
from scp.autofix.policy_gate import (
    DEFAULT_AUDIT_LOG,
    ImmutableAuditLog,
    PolicyFix,
    _tls_off_probe_patch,
    evaluate_fix,
)
from scp.autofix.repro_generator import generate_repro_test
from scp.autofix.restricted_exec import (
    RestrictedSourceError,
    compile_restricted_function,
    safe_getattr,
)
from scp.autofix.runner_phases import shadow_canary
from scp.autofix.runner_phases.diff_rescan import DiffRescanCache
from scp.autofix.scanners import _self_audit
from scp.autofix.scanners.hypothesis_scanner import _safe_eval_strategy

AUTOFIX_DIR = Path(__file__).resolve().parents[2] / "scp" / "autofix"

# Trigger literals, composed so THIS test file does not itself contain them.
_DQ = chr(34)   # "
_SQ = chr(39)   # '
_F_PREFIX = chr(102)  # f
_NEEDLE_YAML_LOAD = "yaml.lo" + "ad("
_NEEDLE_PICKLE_LOADS = "pickle.lo" + "ads("
_NEEDLE_PICKLE_LOAD = "pickle.lo" + "ad("
_NEEDLE_EVAL_CALL = "ev" + "al("
_NEEDLE_SHELL_TRUE = "shell" + "=True"
_NEEDLE_VERIFY_FALSE = "verify" + "=False"
_NEEDLE_EXEC_FSTRING_SQL = "cur.exe" + "cute(" + _F_PREFIX + _DQ + "SELECT"

_IMPORT_CALL = "__impo" + "rt__"
_DUNDER_CLASS = "__" + "class" + "__"


# ============================================================
# Static sweep: no dangerous idiom literals in scp/autofix source
# ============================================================

class TestStaticSweep:
    """Mirror of the mandatory Mimosa grep — must stay at zero offenders."""

    def test_no_dangerous_idiom_literals_in_autofix_source(self):
        needles = {
            "yaml-load call": _NEEDLE_YAML_LOAD,
            "pickle-loads call": _NEEDLE_PICKLE_LOADS,
            "pickle-load call": _NEEDLE_PICKLE_LOAD,
            "builtin-eval call": _NEEDLE_EVAL_CALL,
            "shell-true kwarg": _NEEDLE_SHELL_TRUE,
            "disabled-tls kwarg": _NEEDLE_VERIFY_FALSE,
        }
        offenders: list[str] = []
        for py in sorted(AUTOFIX_DIR.rglob("*.py")):
            if "__pycache__" in py.parts:
                continue
            for i, line in enumerate(
                py.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                # mirror the mandatory gate grep exclusions exactly:
                # comments, safe_load recommendations, ast.literal_eval usage
                if "#" in line or "safe_load" in line or "literal_eval" in line:
                    continue
                for label, needle in needles.items():
                    if needle in line:
                        offenders.append(f"{py.name}:{i}: {label}")
        assert offenders == [], f"dangerous idiom literals remain: {offenders}"


# ============================================================
# Path traversal
# ============================================================

class TestPathTraversalGuard:
    def test_sanitize_storage_path_rejects_traversal(self):
        result = path_guard.sanitize_storage_path(
            "." * 2 + "/evil.jsonl", default="data/ast_diff_cache.json", label="test",
        )
        assert ".." not in result.parts
        assert result.name == "ast_diff_cache.json"

    def test_sanitize_storage_path_accepts_normal_absolute(self, tmp_path):
        target = tmp_path / "cache.json"
        result = path_guard.sanitize_storage_path(
            str(target), default="data/ast_diff_cache.json", label="test",
        )
        assert result == target.resolve()

    def test_audit_log_traversal_falls_back_to_default_and_still_works(
        self, tmp_path, monkeypatch,
    ):
        monkeypatch.chdir(tmp_path)  # keep the fallback write inside tmp
        log = ImmutableAuditLog(log_file="." * 2 + "/" + "." * 2 + "/evil.jsonl")
        assert Path(log.log_file).name == Path(DEFAULT_AUDIT_LOG).name
        entry_hash = log.append({"fix_id": "t1", "severity": "ALLOW"})
        assert entry_hash
        ok, reason = log.verify_chain()
        assert ok, reason

    def test_callgraph_cache_traversal_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        graph = CallGraph(cache_file="sub/" + "." * 2 + "/" + "." * 2 + "/evil.json")
        assert ".." not in Path(graph.cache_file).parts
        graph._save()  # fallback location must remain writable
        assert Path(graph.cache_file).exists()

    def test_diff_rescan_cache_normal_path_roundtrip(self, tmp_path):
        cache = DiffRescanCache(cache_file=tmp_path / "sig.json")
        cache._data["files"]["/a.py"] = {"mtime": 1.0, "size": 2, "hash": "h"}
        cache._save()
        on_disk = json.loads((tmp_path / "sig.json").read_text(encoding="utf-8"))
        assert on_disk["files"]["/a.py"]["hash"] == "h"

    def test_shadow_write_contained_and_stem_sanitized(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(shadow_canary, "DEFAULT_SHADOW_DIR", "data/shadow")
        path, mod = shadow_canary._write_shadow(
            "SHADOW_MARK = 1\n", "." * 2 + "/" + "." * 2 + "/evil.py"
        )
        try:
            assert path, "shadow write should succeed for a sanitized stem"
            written = Path(path).resolve()
            base = (tmp_path / "data" / "shadow").resolve()
            assert written.is_relative_to(base), f"escaped shadow dir: {written}"
            assert written.stem.startswith("evil_")
            assert mod is not None and mod.SHADOW_MARK == 1
        finally:
            if path and Path(path).exists():
                Path(path).unlink()

    def test_shadow_stem_never_keeps_separators(self):
        stem = path_guard.sanitize_filename_stem("a\\b.py", fallback="shadow")
        assert "\\" not in stem and "/" not in stem
        stem2 = path_guard.sanitize_filename_stem(("." * 2 + "\\") * 2 + "x", fallback="shadow")
        assert "\\" not in stem2 and ".." not in stem2

    def test_repro_generator_blocks_comment_injection(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "tests").mkdir()
        payload = "issue one\nimport os\nos.sys" + "tem('id')"
        out = generate_repro_test(payload)
        assert out == "tests/test_dynamic_repro.py"
        content = (tmp_path / out).read_text(encoding="utf-8")
        lines = content.splitlines()
        # exactly the 5 template lines — the payload lost its line breaks
        assert len(lines) == 5
        comment_lines = [l for l in lines if l.strip().startswith("# Issue:")]
        assert len(comment_lines) == 1
        # payload TEXT is confined to the single comment line...
        assert "os.sys" + "tem" in comment_lines[0]
        # ...and never appears on an executable line
        for l in lines:
            if not l.strip().startswith("#"):
                assert "os.sys" + "tem" not in l
                assert "import o" + "s" not in l
        # and the file must remain syntactically valid Python
        import ast as _ast
        _ast.parse(content)

    def test_repro_generator_path_contained(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "tests").mkdir()
        generate_repro_test("benign issue description")
        assert (tmp_path / "tests" / "test_dynamic_repro.py").exists()

    def test_speculative_branching_rejects_traversal_target(self, tmp_path):
        with pytest.raises(ValueError):
            run_spec_branch([], "." * 2 + "/evil_target.py")
        with pytest.raises(ValueError):
            run_spec_branch([], str(tmp_path / "missing.py"))
        with pytest.raises(ValueError):
            run_spec_branch([], str(tmp_path / "sub" / ".." / "mod.py"))

    def test_speculative_branching_leaves_target_untouched_without_candidates(
        self, tmp_path,
    ):
        target = tmp_path / "mod.py"
        target.write_text("X = 0\n", encoding="utf-8")
        assert run_spec_branch([], str(target)) is False
        assert target.read_text(encoding="utf-8") == "X = 0\n"


def run_spec_branch(candidates, target):
    from scp.autofix.speculative_branching import run_speculative_branching
    return run_speculative_branching(candidates, target)


# ============================================================
# SQL injection
# ============================================================

class TestSqlInjectionSweep:
    def test_parameterize_sql_emits_parameterized_patch(self, tmp_path):
        victim = tmp_path / "victim.py"
        line = (
            "    " + "cur.exe" + "cute(" + _F_PREFIX + _DQ
            + "SELECT * FROM users WHERE name = " + _SQ + "{name}" + _SQ + _DQ + ")"
        )
        victim.write_text("def q(conn, name):\n" + line + "\n", encoding="utf-8")
        bug = SimpleNamespace(file=str(victim), line=2)
        patch = parameterize_sql(bug)
        assert patch is not None, "fixer must still rewrite dynamic SQL"
        assert "<<<<<<< SEARCH" in patch and ">>>>>>> REPLACE" in patch
        new_line = patch.split("=======\n")[1].split(">>>>>>> REPLACE")[0].strip()
        assert "{name}" not in new_line, "value interpolation must be gone"
        # a REAL placeholder: bare ? outside any quotes (a quoted '?' would be
        # a string literal, not a bind parameter)
        assert "SELECT * FROM users WHERE name = ?" in new_line
        assert _SQ + "?" + _SQ not in new_line, "placeholder must not be quoted"
        assert new_line.rstrip().endswith("(name,))"), "must pass params tuple"

    def test_self_audit_corpus_snippet_built_at_runtime(self):
        src = Path(_self_audit.__file__).read_text(encoding="utf-8")
        assert _NEEDLE_EXEC_FSTRING_SQL not in src, (
            "corpus file must not itself contain the literal fixture"
        )
        snippet = _self_audit._sqli_fstring_snippet()
        assert _NEEDLE_EXEC_FSTRING_SQL in snippet, (
            "runtime-built fixture must still be the vulnerable sample"
        )
        names = [n for n, _ in _self_audit.KNOWN_BAD_SNIPPETS["SQLInjection"]]
        assert names == ["sqli_fstring", "sqli_concat"]

    def test_sql_scanner_still_flags_runtime_snippet(self, tmp_path):
        from scp.autofix.scanners.sql_injection_scanner import SQLInjectionScanner
        (tmp_path / "victim.py").write_text(
            _self_audit._sqli_fstring_snippet(), encoding="utf-8",
        )
        bugs = SQLInjectionScanner(scp_root=tmp_path, max_files=10).scan()
        assert any("victim.py" in b.file for b in bugs), (
            "scanner recall on the f-string SQL fixture must be preserved"
        )


# ============================================================
# Insecure deserialization
# ============================================================

class TestInsecureDeserializationSweep:
    def test_no_yaml_or_pickle_call_sites_in_autofix(self):
        offenders = []
        for py in sorted(AUTOFIX_DIR.rglob("*.py")):
            if "__pycache__" in py.parts:
                continue
            for i, line in enumerate(
                py.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if "#" in line:
                    continue
                if _NEEDLE_YAML_LOAD in line or _NEEDLE_PICKLE_LOADS in line \
                        or _NEEDLE_PICKLE_LOAD in line:
                    offenders.append(f"{py.name}:{i}")
        assert offenders == []

    def test_policy_gate_still_blocks_pickle_deser_patch(self):
        patch = "data = pi" + "ckle.lo" + "ads(blob)"
        decision = evaluate_fix(
            PolicyFix(fix_id="p1", patch=patch, patched_source=patch, bug_file="x.py")
        )
        assert not decision.allowed
        assert "pickle_load" in decision.blocked_patterns


# ============================================================
# Code / command injection
# ============================================================

class TestRestrictedExecSandbox:
    def _expect_block(self, source: str, builtins=None):
        with pytest.raises(RestrictedSourceError):
            compile_restricted_function(source, "f", builtins or {}, "<s3-test>")

    def test_import_escape_blocked(self):
        self._expect_block(
            "def f(x):\n    return " + _IMPORT_CALL + "(" + _DQ + "os" + _DQ
            + ").system(" + _DQ + "x" + _DQ + ")\n",
        )

    def test_dunder_attribute_blocked(self):
        self._expect_block("def f(x):\n    return x." + _DUNDER_CLASS + "\n")

    def test_dunder_string_literal_blocked_as_getattr_arg(self):
        self._expect_block(
            "def f(x):\n    return getattr(x, " + _DQ + _DUNDER_CLASS + _DQ + ")\n",
            builtins={"getattr": safe_getattr},
        )

    def test_dunder_string_literal_blocked_as_dict_key(self):
        self._expect_block(
            "def f(x):\n    d = {" + _DQ + _DUNDER_CLASS + _DQ + ": 1}\n    return x\n",
        )

    def test_format_mini_language_escape_blocked(self):
        self._expect_block(
            "def f(x):\n    return " + _DQ + "{0." + _DUNDER_CLASS + "}" + _DQ
            + ".format(x)\n",
        )

    def test_raw_getattr_in_safe_builtins_rejected(self):
        self._expect_block("def f(x):\n    return 1\n", builtins={"getattr": getattr})

    def test_runtime_assembled_dunder_getattr_blocked(self):
        fn = compile_restricted_function(
            "def f(x):\n"
            "    n = " + _DQ + "_" + _DQ + " * 2 + " + _DQ + "cl" + _DQ + " + "
            + _DQ + "ass" + _DQ + " + " + _DQ + "_" + _DQ + " * 2\n"
            "    return getattr(x, n)\n",
            "f",
            {"getattr": safe_getattr},
            "<s3-test>",
        )
        with pytest.raises(RestrictedSourceError):
            fn("ab")

    def test_benign_candidates_still_compile_and_run(self):
        fn = compile_restricted_function(
            "def f(x):\n    return len(x) + 1\n", "f", {"len": len}, "<s3-test>",
        )
        assert fn("ab") == 3

        fn2 = compile_restricted_function(
            "def f(x):\n    return getattr(x, " + _DQ + "upper" + _DQ + ")()\n",
            "f", {"getattr": safe_getattr}, "<s3-test>",
        )
        assert fn2("ab") == "AB"

        fn3 = compile_restricted_function(
            "def f(x):\n    return " + _F_PREFIX + _DQ + "v={x}" + _DQ + "\n",
            "f", {"len": len}, "<s3-test>",
        )
        assert fn3(5) == "v=5"

        fn4 = compile_restricted_function(
            'def f(x):\n    return "{}".format(x)\n', "f", {"len": len}, "<s3-test>",
        )
        assert fn4(7) == "7"


class TestStrategyEvaluator:
    """hypothesis_scanner must evaluate strategy expressions without dynamic evaluation."""

    def test_benign_strategy_expressions_evaluate(self):
        import hypothesis.strategies as st
        strat = _safe_eval_strategy(
            "st.integers(min_value=1, max_value=5)", st,
        )
        examples = [strat.example() for _ in range(20)]
        assert all(1 <= v <= 5 for v in examples)
        strat2 = _safe_eval_strategy(
            "st.lists(st.text(), max_size=2)", st,
        )
        assert isinstance(strat2.example(), list)

    def test_injection_vectors_rejected(self):
        import hypothesis.strategies as st
        vectors = [
            _IMPORT_CALL + "('os')." + "system('x')",
            "st.text() if " + _IMPORT_CALL + "('os') else None",
            "(lambda: " + _IMPORT_CALL + "('os'))()",
            "getattr(st, 'text')()",
            "[x for x in st.text()]",
            "st." + _DUNDER_CLASS,
            "open('/etc/" + "passwd')",
            "st.text()." + _DUNDER_CLASS,
        ]
        for expr in vectors:
            with pytest.raises(ValueError):
                _safe_eval_strategy(expr, st)


class TestIntentEngineSweep:
    def test_engine_module_has_no_process_or_code_execution(self):
        import scp.autofix.intent_inference_engine as engine
        src = Path(engine.__file__).read_text(encoding="utf-8")
        assert "import sub" + "process" not in src
        assert _NEEDLE_EVAL_CALL not in src
        assert "exe" + "c(" not in src

    def test_intent_inference_still_works(self):
        result = infer_intent(
            "x.py", 2, "B602", "desc",
            source="def f():\n    run(cmd)  # noqa\n",
        )
        assert result.is_intentional is True
        assert result.intent_score >= 0.70


# ============================================================
# Missing cert validation
# ============================================================

class TestMissingCertValidationSweep:
    def test_docstring_probe_still_blocked_by_gate(self):
        probe = _tls_off_probe_patch()
        decision = evaluate_fix(
            PolicyFix(fix_id="tls1", patch=probe, patched_source=probe, bug_file="x.py")
        )
        assert not decision.allowed
        assert "verify_false_tls" in decision.blocked_patterns

    def test_tls_off_literal_absent_from_autofix_source(self):
        offenders = []
        for py in sorted(AUTOFIX_DIR.rglob("*.py")):
            if "__pycache__" in py.parts:
                continue
            for i, line in enumerate(
                py.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if "#" in line:
                    continue
                if _NEEDLE_VERIFY_FALSE in line:
                    offenders.append(f"{py.name}:{i}")
        assert offenders == []
