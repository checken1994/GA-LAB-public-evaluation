"""Evidence Replay & Verification (BSG-VA: Buggy / State / Gold Validation).

Replays candidate fixes against Buggy (B), Candidate State (S), and Gold (G)
code baselines to verify that tests discriminate genuine fixes from regression
or manufactured pass conditions.

DNA Principles Enforced:
  #22 (PASS ≠ TRUE) — test PASS does not mean bug FIXED; replay against gold
  #26 (Reality > Model) — run real tests in subprocess, zero simulation
  #04 (No Manufactured Green) — fail-closed verification, no hardcoded success
  #09 (No Harm) — restore original files after replay
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.autofix.evidence_replay")

_MAX_TEST_TIME_S = 30
_OUTPUT_SNIPPET_LEN = 200
# NOTE: '~' is deliberately NOT blacklisted. Windows exposes temp directories
# through 8.3 short path components (e.g. C:\Users\RUNNER~1\AppData\Local\Temp
# on GitHub-hosted Windows runners), and post_fix_verify builds replay
# file_paths from tempfile.TemporaryDirectory() — a legitimate '~' there made
# every replay B-leg fail with "[REJECTED: unsafe characters in file_path]"
# (pre-RC run 36102606213). No shell ever expands '~' here: file_path is only
# used as a Path target and test commands run as argv lists / shlex tokens.
_SHELL_METACHAR_BLACKLIST = frozenset(";|&$`><\n\r\"'!*?[]{()}")


class EvidenceRole(str, Enum):
    GOLD_ALIGNED = "gold_aligned"
    REGRESSION_ONLY = "regression_only"
    MISLEADING = "misleading"
    CANDIDATE_SPECIFIC = "candidate_specific"
    DIAGNOSTIC_NEGATIVE = "diagnostic_negative"
    VERIFIER = "verifier"


_DISCRIMINATING_ROLES: frozenset[EvidenceRole] = frozenset({
    EvidenceRole.GOLD_ALIGNED,
    EvidenceRole.CANDIDATE_SPECIFIC,
    EvidenceRole.DIAGNOSTIC_NEGATIVE,
    EvidenceRole.VERIFIER,
})


@dataclass
class ReplayResult:
    role: EvidenceRole
    b_result: tuple[bool, str] = (False, "")
    s_result: tuple[bool, str] = (False, "")
    g_result: tuple[bool, str] = (False, "")
    test_command: str = ""
    discriminating: bool = field(init=False)

    def __post_init__(self) -> None:
        self.discriminating = self.role in _DISCRIMINATING_ROLES

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "b_pass": self.b_result[0],
            "s_pass": self.s_result[0],
            "g_pass": self.g_result[0],
            "b_snippet": self.b_result[1],
            "s_snippet": self.s_result[1],
            "g_snippet": self.g_result[1],
            "test_command": self.test_command,
            "discriminating": self.discriminating,
        }

    def __str__(self) -> str:
        return (
            f"ReplayResult(role={self.role.value}, "
            f"b={'PASS' if self.b_result[0] else 'FAIL'}, "
            f"s={'PASS' if self.s_result[0] else 'FAIL'}, "
            f"g={'PASS' if self.g_result[0] else 'FAIL'}, "
            f"discriminating={self.discriminating})"
        )


def compute_bug_signature(bug_type: str, description: str = "") -> str:
    raw = f"{bug_type}:{description}".encode()
    return hashlib.sha256(raw).hexdigest()


class GoldDataset:
    def __init__(self, dataset_path: str = "data/gold_dataset.jsonl", data_dir: str | None = None) -> None:
        self.dataset_path = Path(data_dir or dataset_path)
        self._cache: dict[str, dict[str, Any]] | None = None

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._cache is not None:
            return self._cache
        cache: dict[str, dict[str, Any]] = {}
        if self.dataset_path.exists():
            try:
                with self.dataset_path.open("r", encoding="utf-8") as f:
                    for line_no, raw in enumerate(f, start=1):
                        line = raw.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            sig = entry.get("bug_signature")
                            if sig:
                                cache[sig] = entry
                        except json.JSONDecodeError as exc:
                            logger.warning("[BSG-VA] malformed line %d: %s", line_no, exc)
            except OSError as exc:
                logger.warning("[BSG-VA] gold_dataset load failed: %s", exc)
        self._cache = cache
        return cache

    def get_gold_fix(self, bug_signature: str) -> str | None:
        entry = self._load().get(bug_signature)
        return entry.get("gold_source") if entry else None

    def get_entry(self, bug_signature: str) -> dict[str, Any] | None:
        if os.environ.get("SCP_SEED_GOLD_EVIDENCE") == "1":
            # [FA-04 repair] The seed entry is the "gold-seeding policy for
            # first-time bug signatures". It deliberately carries NO test, so
            # the replay harness must synthesize a real, discriminating
            # characterization test at replay time (see prepare_seed_replay).
            # The command uses sys.executable -m pytest so the replay does not
            # depend on a pytest launcher being on PATH. `seeded` marks the
            # entry as synthesized so run_full_post_fix_verify only builds a
            # generated test for seed entries, never for dataset entries.
            return {
                "test_command": [sys.executable, "-m", "pytest", "-q"],
                "buggy_source": "",
                "gold_source": "",
                "seeded": True,
            }
        return self._load().get(bug_signature)

    def add_entry(
        self,
        bug_signature: str,
        buggy_source: str,
        gold_source: str,
        test_command: str,
        bug_type: str = "",
        description: str = "",
    ) -> None:
        entry = {
            "bug_signature": bug_signature,
            "bug_type": bug_type,
            "description": description,
            "buggy_source": buggy_source,
            "gold_source": gold_source,
            "test_command": test_command,
        }
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
        with self.dataset_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if self._cache is not None:
            self._cache[bug_signature] = entry

    def list_entries(self) -> list[dict[str, Any]]:
        return list(self._load().values())


class EvidenceReplay:
    def __init__(self, working_dir: str | Path | None = None, dataset: GoldDataset | None = None) -> None:
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.dataset = dataset or GoldDataset()

    def run_test(self, test_command: str | list[str], cwd: Path | None = None) -> tuple[bool, str]:
        run_cwd = cwd or self.working_dir
        if isinstance(test_command, (list, tuple)):
            argv = [str(a) for a in test_command]
        elif sys.platform.startswith("win"):
            argv = shlex.split(test_command, posix=False)
            argv = [
                token[1:-1]
                if len(token) >= 2 and token[0] == token[-1] and token[0] in {"'", '"'}
                else token
                for token in argv
            ]
        else:
            argv = shlex.split(test_command)

        if not argv:
            return False, "[empty test_command]"

        win_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        try:
            # [ENV-LEAK-FIX] Run the B/S/G replay legs with the SAME minimal
            # environment as probe_module_behavior(). The test command may
            # come from a hostile gold-dataset entry / hostile candidate
            # context — inheriting the FULL host env leaked PYTHON*/*SCP*/
            # PYTEST_* variables and host secrets into the subprocess and let
            # host state influence replay outcomes (probe legs were already
            # sandboxed to _minimal_probe_env(); run_test was the gap).
            result = subprocess.run(
                argv,
                cwd=str(run_cwd),
                capture_output=True,
                text=True,
                timeout=_MAX_TEST_TIME_S,
                creationflags=win_flags,
                env=_minimal_probe_env(),
            )
            output = (result.stdout or "") + (result.stderr or "")
            snippet = output[-_OUTPUT_SNIPPET_LEN:] if output else ""
            return (result.returncode == 0, snippet)
        except subprocess.TimeoutExpired:
            return False, f"[TIMEOUT after {_MAX_TEST_TIME_S}s]"
        except Exception as exc:
            logger.debug(f"EvidenceReplay.run_test: exception ignored: {exc}", exc_info=True)
            return False, f"[EXECUTION ERROR: {exc}]"

    def _classify(self, b_pass: bool, s_pass: bool, g_pass: bool) -> EvidenceRole:
        if not s_pass:
            return EvidenceRole.DIAGNOSTIC_NEGATIVE
        if not b_pass and s_pass and g_pass:
            return EvidenceRole.GOLD_ALIGNED
        if not b_pass and s_pass and not g_pass:
            return EvidenceRole.CANDIDATE_SPECIFIC
        if b_pass and s_pass and not g_pass:
            return EvidenceRole.MISLEADING
        return EvidenceRole.REGRESSION_ONLY

    def classify_evidence(
        self,
        test_command: str | list[str],
        buggy_source: str,
        candidate_source: str,
        gold_source: str,
        file_path: str,
    ) -> ReplayResult:
        if any(c in file_path for c in _SHELL_METACHAR_BLACKLIST):
            return ReplayResult(
                role=EvidenceRole.DIAGNOSTIC_NEGATIVE,
                b_result=(False, "[REJECTED: unsafe characters in file_path]"),
                test_command=str(test_command),
            )
        target = Path(file_path)
        cwd = self.working_dir
        backup_existed = target.exists()
        backup_content = target.read_text(encoding="utf-8", errors="replace") if backup_existed else None

        try:
            self._write_source(target, buggy_source)
            b_result = self.run_test(test_command, cwd=cwd)

            self._write_source(target, candidate_source)
            s_result = self.run_test(test_command, cwd=cwd)

            self._write_source(target, gold_source)
            g_result = self.run_test(test_command, cwd=cwd)

            role = self._classify(b_result[0], s_result[0], g_result[0])
            return ReplayResult(
                role=role,
                b_result=b_result,
                s_result=s_result,
                g_result=g_result,
                test_command=str(test_command),
            )
        finally:
            self._restore(target, backup_existed, backup_content)

    def verify(
        self,
        test_command: str | list[str] | None = None,
        file_path: str | Path | None = None,
        candidate_source: str | None = None,
        bug_type: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Verify candidate fix with real execution test (Fail-Closed, FA-04 compliant)."""
        if not test_command and not candidate_source:
            return {
                "ok": False,
                "status": "UNVERIFIED",
                "reason": "Missing required test_command or candidate_source for verification",
            }

        if test_command:
            passed, output = self.run_test(test_command)
            status_label = "VERIFIED" if passed else "FAILED"
            return {
                "ok": passed,
                "status": status_label,
                "output": output,
                "discriminating": passed,
            }

        return {
            "ok": False,
            "status": "UNVERIFIED",
            "reason": "Incomplete verification parameters",
        }

    @staticmethod
    def _invalidate_bytecode_cache(target: Path) -> None:
        candidates = [target.with_suffix(".pyc")]
        cache_dir = target.parent / "__pycache__"
        if cache_dir.exists():
            candidates.extend(cache_dir.glob(f"{target.stem}.*.pyc"))
        for cached in candidates:
            try:
                cached.unlink(missing_ok=True)
            except OSError as exc:
                logger.debug("Failed unlinking bytecode %s: %s", cached, exc)

    @staticmethod
    def _write_source(target: Path, source: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
        EvidenceReplay._invalidate_bytecode_cache(target)

    @staticmethod
    def _restore(target: Path, backup_existed: bool, backup_content: str | None) -> None:
        try:
            if backup_existed and backup_content is not None:
                target.write_text(backup_content, encoding="utf-8")
                EvidenceReplay._invalidate_bytecode_cache(target)
            elif not backup_existed and target.exists():
                target.unlink(missing_ok=True)
                EvidenceReplay._invalidate_bytecode_cache(target)
        except OSError as exc:
            logger.warning("Failed restoring backup for %s: %s", target, exc)


# ============================================================================
# [FA-04 repair + FA-13 containment] Seed-mode characterization replay.
#
# TẠI SAO: Seed gold entries (SCP_SEED_GOLD_EVIDENCE=1) exist because a
# first-time bug signature has no gold dataset entry yet — i.e. NO test and
# NO gold source. When classify_evidence replaced the FA-04 stub with real
# subprocess execution, the seeded `test_command="pytest"` began running in
# the replay workspace, which contains only the module under test and no
# test file: pytest collects 0 tests, exits non-zero, and EVERY seeded fix
# was classified DIAGNOSTIC_NEGATIVE and rolled back.
#
# The honest repair is NOT to skip the phase (that would be manufactured
# green, FA-04). It is to build a real test from real behavior:
#   1. probe_module_behavior — load the candidate (and, when available, the
#      pre-fix buggy source) in an ISOLATED SUBPROCESS with deterministic
#      smoke inputs (same arg-construction contract as
#      runner_phases.reality_test) and record the observed return values /
#      errors. The untrusted source is NEVER exec'd inside the AutoFix host
#      process (FA-13): the subprocess runs the STATIC runner harness
#      replay_probe_runner.py from a cwd-isolated throwaway dir with a
#      minimal environment and a bounded timeout.
#   2. build_characterization_test — generate a pytest file that pins the
#      candidate's observed behavior. It lives only inside the replay temp
#      workspace and is executed as a real subprocess test against the
#      Buggy (B), candidate (S) and Gold (G) states.
#   3. prepare_seed_replay — fail-closed gate: if the candidate exposes no
#      exercisable/stable observable behavior, or behaves IDENTICALLY to the
#      buggy state, the replay cannot discriminate and must be UNVERIFIED
#      (escalate, never promote). If the candidate RAISES where the buggy
#      code was clean, the fix introduced a regression → rollback.
# A crash and a test failure are both non-zero exits → fail-closed by
# construction (they can never be promoted as discrimination).
# ============================================================================

_MAX_PINNED_REPR_LEN = 300
_PROBE_TIMEOUT_S = 30
_PROBE_RUNNER_MODULE = "replay_probe_runner.py"
_PROBE_RUNNER_STAGED_NAME = "_scp_replay_probe_runner.py"
_MINIMAL_ENV_KEEP = (
    # Windows process basics
    "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "PATHEXT", "TEMP", "TMP",
    "APPDATA", "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)",
    "ALLUSERSPROFILE", "COMMONPROGRAMFILES", "COMMONPROGRAMFILES(X86)",
    "USERPROFILE", "USERNAME", "HOMEDRIVE", "HOMEPATH",
    # Generic
    "PATH", "LANG", "LC_ALL", "TZ",
    # POSIX basics
    "HOME", "TMPDIR",
)


def _minimal_probe_env() -> dict[str, str]:
    """Minimal environment for the probe subprocess.

    Deliberately EXCLUDES PYTHONPATH/PYTHONHOME/other PYTHON* vars, PYTEST_*
    and every SCP_* variable: the probe must not inherit the host
    test-process state and the untrusted module must not see host
    configuration or secrets.
    """
    return {k: os.environ[k] for k in _MINIMAL_ENV_KEEP if k in os.environ}


def _repr_is_stable(repr_text: str | None) -> bool:
    """Heuristic: repr must not embed object identity or be unwieldy."""
    if repr_text is None:
        return False
    if len(repr_text) > _MAX_PINNED_REPR_LEN:
        return False
    return " at 0x" not in repr_text


def _repr_is_order_free_literal(repr_text: str | None) -> bool:
    """True when ``repr_text`` parses (literal-only, NEVER executes) into a
    set/frozenset — i.e. a repr whose element order is PYTHONHASHSEED-
    dependent across processes. The HOST does the parse at generation time;
    the generated test repeats it at runtime purely to recover the pinned
    VALUE from the escaped string literal (see REPR-HASH-ORDER-FIX in
    ``build_characterization_test``). Non-literals (a hostile ``__repr__``
    payload) fail the parse and keep the strict string-match pin.
    """
    if not repr_text or not repr_text.strip():
        return False
    try:
        value = ast.literal_eval(repr_text)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return False
    return isinstance(value, (set, frozenset))


_ARGS_EXPR_ALLOWED_NODES = (
    ast.Constant, ast.Tuple, ast.List, ast.Dict, ast.Set,
    ast.UnaryOp, ast.USub, ast.UAdd, ast.Load, ast.Name, ast.keyword,
)


def _is_safe_args_expr(args_expr: str) -> bool:
    """True when ``args_expr`` parses as a PURE LITERAL argument list.

    [REPR-INJECTION-FIX] ``args_expr`` is embedded verbatim into the generated
    assert line. It is produced by the static probe runner's deterministic
    smoke-arg builder, but a hostile module controls ``repr()`` of its own
    parameter DEFAULTS, so the text must be treated as untrusted: it must
    parse as ``_scp_replay_f(<args_expr>)`` where every node is a literal —
    no calls (``__import__`` escape), no attribute access, no names other
    than the synthetic function name. Anything else ⇒ the record is not
    pinnable (fail-closed: fewer pins, never a corrupted test file).
    """
    if not args_expr or not args_expr.strip():
        return True  # empty arg list → `_scp_replay_f()` — nothing to inject
    try:
        tree = ast.parse(f"_scp_replay_f({args_expr})", mode="eval")
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Expression):
            continue
        if isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and node.func.id == "_scp_replay_f"):
                return False
            continue
        if not isinstance(node, _ARGS_EXPR_ALLOWED_NODES):
            return False
        if isinstance(node, ast.Name) and node.id != "_scp_replay_f":
            return False
    return True


def probe_module_behavior(
    source: str,
    module_stem: str,
    isolate_cwd: Path | None = None,
) -> dict[str, Any]:
    """Load `source` in an ISOLATED SUBPROCESS and record observable behavior.

    Containment (FA-13): the source is UNVERIFIED candidate/buggy code — it is
    never exec'd inside the AutoFix host process. The parent stages the source
    plus the STATIC runner harness (replay_probe_runner.py, copied verbatim,
    no dynamic code generation) into the cwd-isolated work dir and runs
    [sys.executable, "-X", "utf8", runner, module, names_json] with a minimal
    environment and a bounded timeout. The runner imports the module from its
    file path via importlib.util.spec_from_file_location, exercises the given
    public top-level names with the same deterministic smoke-arg contract as
    runner_phases.reality_test, buffers the module's stdout, and answers with
    exactly one JSON document.

    Fail-closed: syntax error, module import/exec crash, runner crash,
    non-zero exit, unparsable stdout, malformed payload, or timeout all return
    ok=False with no records — never a silent pass.
    """
    import ast as _ast
    import tempfile as _tmpfile

    result: dict[str, Any] = {"ok": False, "reason": "", "records": [], "exercised": 0, "pinnable": 0}
    try:
        tree = _ast.parse(source)
    except SyntaxError as exc:
        result["reason"] = f"SyntaxError: {exc}"
        return result

    public_names = [
        node.name
        for node in tree.body
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    if not public_names:
        result["reason"] = "no public top-level callables discovered"
        return result

    shipped_runner = Path(__file__).resolve().parent / _PROBE_RUNNER_MODULE
    if not shipped_runner.exists():
        result["reason"] = f"probe runner harness missing: {shipped_runner}"
        return result

    owned_tmp = None
    try:
        if isolate_cwd is None:
            owned_tmp = _tmpfile.TemporaryDirectory(prefix="bsgva_probe_")
            work_dir = Path(owned_tmp.name)
        else:
            work_dir = Path(isolate_cwd)
            work_dir.mkdir(parents=True, exist_ok=True)

        module_path = work_dir / f"{module_stem}.py"
        module_path.write_text(source, encoding="utf-8")
        EvidenceReplay._invalidate_bytecode_cache(module_path)
        runner_path = work_dir / _PROBE_RUNNER_STAGED_NAME
        shutil.copyfile(shipped_runner, runner_path)

        win_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-X", "utf8",
                    str(runner_path),
                    str(module_path),
                    json.dumps(public_names),
                ],
                cwd=str(work_dir),
                stdin=subprocess.DEVNULL,  # input()-style targets fail fast, not hang
                capture_output=True,
                text=True,
                errors="replace",
                timeout=_PROBE_TIMEOUT_S,
                env=_minimal_probe_env(),
                creationflags=win_flags,
            )
        except subprocess.TimeoutExpired:
            result["reason"] = f"[TIMEOUT after {_PROBE_TIMEOUT_S}s]"
            return result
        except Exception as exc:  # noqa: BLE001 — spawn failure is a failed probe
            result["reason"] = f"[EXECUTION ERROR: {exc}]"
            return result

        if proc.returncode != 0:
            result["reason"] = (
                f"probe runner exited with code {proc.returncode}: "
                f"{(proc.stderr or '')[-200:]}"
            )
            return result
        try:
            payload = json.loads((proc.stdout or "").strip())
        except json.JSONDecodeError as exc:
            result["reason"] = f"probe runner produced unparsable stdout: {exc}"
            return result
        if not isinstance(payload, dict):
            result["reason"] = "probe runner payload is not a JSON object"
            return result
        if payload.get("ok") is not True:
            # Module import/exec crash (or harness failure) reported by the
            # runner — exactly the exec-failure path: no records, fail-closed.
            result["reason"] = str(payload.get("reason") or "probe runner reported failure")
            return result
        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            result["reason"] = "probe runner payload has no records list"
            return result

        records: list[dict[str, Any]] = []
        for raw in raw_records:
            if not isinstance(raw, dict) or not isinstance(raw.get("callable"), str):
                result["reason"] = "probe runner returned a malformed record"
                return result
            rec: dict[str, Any] = {
                "callable": raw["callable"],
                "exercised": bool(raw.get("exercised")),
                # Recomputed here — the parent owns the stability rule.
                "pinnable": False,
                "result_repr": raw.get("result_repr") if isinstance(raw.get("result_repr"), str) else None,
                "error": raw.get("error") if isinstance(raw.get("error"), str) else None,
                "async": bool(raw.get("async")),
                "args_expr": raw.get("args_expr") if isinstance(raw.get("args_expr"), str) else "",
            }
            rec["pinnable"] = bool(rec["exercised"]) and _repr_is_stable(rec["result_repr"])
            records.append(rec)

        result["ok"] = True
        result["records"] = records
        result["exercised"] = sum(1 for r in records if r["exercised"])
        result["pinnable"] = sum(1 for r in records if r["pinnable"])
        return result
    finally:
        if owned_tmp is not None:
            owned_tmp.cleanup()


def build_characterization_test(records: list[dict[str, Any]], module_stem: str) -> str | None:
    """Generate a pytest file pinning the observed candidate behavior.

    Only exercised callables with a stable result repr are pinned. Returns
    None when nothing can be pinned (caller must fail closed).

    [REPR-INJECTION-FIX] The pinned value is the repr TEXT returned by the
    probe subprocess — a hostile candidate controls it via a custom
    ``__repr__`` (arbitrary quotes/newlines/code text). Embedding it verbatim
    as ``assert call == {result_repr}`` let the repr break out of the assert
    and inject arbitrary statements/expressions into the generated test
    source. The repr is now pinned as an ESCAPED STRING LITERAL via
    ``repr(result_repr)`` (repr() of a str is always a safe single-line
    literal) and compared with a string-match assert:
    ``assert repr(call) == '<pinned repr text>'``. Same discrimination
    power (the probe OBSERVED ``result_repr == repr(value)``), zero injection
    surface. Records whose args_expr fails the literal-safety parse are
    dropped as unpinnable (fail-closed), never embedded raw.

    [REPR-HASH-ORDER-FIX] A plain ``repr(...) == '<pinned>'`` string-match is
    only valid for DETERMINISTIC reprs. The repr of a set/frozenset iterates
    in PYTHONHASHSEED-dependent order, so a set-returning candidate pinned in
    the probe subprocess failed spuriously in every fresh replay process
    (spurious DIAGNOSTIC_NEGATIVE rollback). When the pinned repr TEXT parses
    (``ast.literal_eval`` in the HOST — literal-only, never executes) into a
    set/frozenset, the generated assert compares the ORDER-FREE canonical
    form ``sorted(map(repr, <actual>))`` against the pinned VALUE recovered
    at test runtime via ``ast.literal_eval('<pinned repr text>')``. The
    hostile text still never leaves the escaped string literal, and
    ``ast.literal_eval`` cannot execute it — the injection property is
    unchanged. All other reprs keep the strict string-match assert.
    """
    pinnable = [
        r for r in records
        if r.get("pinnable") and r.get("exercised")
        and _is_safe_args_expr(r.get("args_expr") or "")
    ]
    if not pinnable:
        return None

    needs_literal_eval = any(
        _repr_is_order_free_literal(r.get("result_repr")) for r in pinnable
    )
    lines: list[str] = [
        '"""[R12-9 BSG-VA] Auto-generated seed-mode characterization replay test.',
        "",
        "Generated by scp.autofix.evidence_replay.prepare_seed_replay for a",
        "first-time bug signature (gold-seeding policy). Pins the OBSERVED",
        "behavior of the candidate (fixed) module so the BSG replay can",
        "discriminate the buggy state from the fixed state with a real pytest",
        "subprocess run (DNA #26). Throwaway artifact: exists only inside the",
        "replay temp workspace.",
        '"""',
    ]
    if needs_literal_eval:
        lines.append("import ast")
    lines.extend([
        "import asyncio",
        "import os",
        "import sys",
        "",
        "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))",
        "",
        f"import {module_stem}",
        "",
        "",
    ])
    for record in pinnable:
        name = record["callable"]
        call = f"{module_stem}.{name}({record['args_expr']})"
        # repr() of a str is ALWAYS a valid single-line Python string literal
        # (quotes, backslashes and newlines are escaped) — injection-proof.
        pinned_repr_literal = repr(record["result_repr"])
        if _repr_is_order_free_literal(record["result_repr"]):
            # set/frozenset: repr element order is hash-seed dependent across
            # processes — compare the order-free canonical form of the VALUE.
            actual = f"asyncio.run({call})" if record.get("async") else call
            body = (
                f"assert sorted(map(repr, {actual})) == "
                f"sorted(map(repr, ast.literal_eval({pinned_repr_literal})))"
            )
        elif record.get("async"):
            body = f"assert repr(asyncio.run({call})) == {pinned_repr_literal}"
        else:
            body = f"assert repr({call}) == {pinned_repr_literal}"
        lines.extend([
            f"def test_replay_{name}() -> None:",
            f'    """Pin observed candidate behavior of {module_stem}.{name}."""',
            f"    {body}",
            "",
            "",
        ])
    return "\n".join(lines)


def _behavior_differs(buggy_records: list[dict[str, Any]], candidate_records: list[dict[str, Any]]) -> bool:
    """True when the candidate's observable behavior differs from the buggy state.

    Comparable differences: a stable pinned result that changed, or a callable
    the candidate exercises cleanly while the buggy code raised. Missing
    callables also count as a difference (the promotion path treats a deleted
    public function as MISLEADING evidence and escalates).
    """
    buggy_by_name = {r["callable"]: r for r in buggy_records}
    cand_by_name = {r["callable"]: r for r in candidate_records}
    for name in set(buggy_by_name) | set(cand_by_name):
        bug_rec = buggy_by_name.get(name)
        cand_rec = cand_by_name.get(name)
        if bug_rec is None or cand_rec is None:
            return True  # callable added or removed by the fix
        if cand_rec["exercised"] and not bug_rec["exercised"]:
            return True
        if (
            cand_rec["exercised"]
            and bug_rec["exercised"]
            and cand_rec["pinnable"]
            and _repr_is_stable(bug_rec["result_repr"])
            and cand_rec["result_repr"] != bug_rec["result_repr"]
        ):
            return True
    return False


def prepare_seed_replay(
    buggy_source: str,
    candidate_source: str,
    module_stem: str,
    isolate_cwd: Path | None = None,
) -> dict[str, Any]:
    """Build a genuinely discriminating replay for a seeded gold entry.

    Returns a plan dict:
      ok=True  → `test_source` holds a generated pytest file to stage in the
                 replay workspace before classify_evidence.
      ok=False, rollback=True → the candidate regressed (crashes where the
                 buggy code was clean) → DIAGNOSTIC_NEGATIVE, roll back.
      ok=False, rollback=False → no discriminating evidence can be built
                 (no exercisable/stable behavior, or behavior identical to
                 the buggy state) → UNVERIFIED, escalate, never promote.
    """
    candidate_probe = probe_module_behavior(candidate_source, module_stem, isolate_cwd=isolate_cwd)
    if not candidate_probe["ok"] or candidate_probe["exercised"] == 0:
        return {
            "ok": False,
            "rollback": False,
            "reason": (
                "seed replay: candidate module has no exercisable callable "
                f"({candidate_probe.get('reason') or '0 callables exercised'})"
            ),
        }
    if candidate_probe["pinnable"] == 0:
        return {
            "ok": False,
            "rollback": False,
            "reason": "seed replay: no stable observable behavior to pin (fail-closed)",
        }

    if buggy_source:
        buggy_probe = probe_module_behavior(buggy_source, module_stem, isolate_cwd=isolate_cwd)
        if buggy_probe["ok"]:
            regressions = [
                bug_rec["callable"]
                for bug_rec in buggy_probe["records"]
                if bug_rec["exercised"]
                and not next(
                    (c for c in candidate_probe["records"] if c["callable"] == bug_rec["callable"]),
                    {"exercised": False},
                )["exercised"]
            ]
            if regressions:
                return {
                    "ok": False,
                    "rollback": True,
                    "reason": (
                        "seed replay: candidate raises where the buggy code was "
                        f"clean (regression): {', '.join(regressions)}"
                    ),
                }
            if not _behavior_differs(buggy_probe["records"], candidate_probe["records"]):
                return {
                    "ok": False,
                    "rollback": False,
                    "reason": (
                        "seed replay: candidate behavior is identical to the buggy "
                        "state — replay cannot discriminate (fail-closed)"
                    ),
                }
        # else: the buggy state is broken (import/exec crash) — that alone
        # discriminates it from a working candidate; the B-leg of the replay
        # will fail on the generated test through the same crash.

    test_source = build_characterization_test(candidate_probe["records"], module_stem)
    if test_source is None:
        return {
            "ok": False,
            "rollback": False,
            "reason": "seed replay: could not generate a characterization test (fail-closed)",
        }
    return {
        "ok": True,
        "rollback": False,
        "reason": "seed replay: characterization test generated from observed behavior",
        "test_source": test_source,
        "pinned": candidate_probe["pinnable"],
    }


__all__ = [
    "EvidenceRole",
    "ReplayResult",
    "GoldDataset",
    "EvidenceReplay",
    "compute_bug_signature",
    "probe_module_behavior",
    "build_characterization_test",
    "prepare_seed_replay",
]
