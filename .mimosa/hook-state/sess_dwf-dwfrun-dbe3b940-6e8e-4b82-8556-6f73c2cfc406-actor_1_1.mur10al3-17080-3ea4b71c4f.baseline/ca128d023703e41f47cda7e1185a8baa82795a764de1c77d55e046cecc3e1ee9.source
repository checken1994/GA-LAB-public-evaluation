import ast
import glob
import json
import os

# Policy A (owner-approved 2026-09-12): the mandatory no-skip gate accepts
# ONLY "declared infra-skips" — a real pytest.skip() call inside a file
# explicitly listed in tests/T00_integrity/declared_infra_skips.json whose
# skip reason matches that entry's declared reason patterns and whose
# declared env-guard token is still present in the file. The allowlist file
# is a reviewed contract: every entry names exactly one file (no wildcards),
# and adding/removing an entry is a deliberate, reviewed change that must
# also update the pin test below.
DECLARED_INFRA_SKIP_ALLOWLIST_FILENAME = "declared_infra_skips.json"
DECLARED_INFRA_SKIP_OUTPUT_TAG = "declared_infra_skips:"

def _real_skip_calls(tree):
    # Real pytest.skip()/pytest.importorskip() Call nodes. A quoted
    # "pytest.skip" token inside a drift-guard deny list is a string constant,
    # NOT a Call node, so it never counts.
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {'skip', 'importorskip'}
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == 'pytest'
    ]

def _static_reason_text(call_node):
    # Statically extractable reason fragments: every string constant inside
    # the first positional argument or the `reason=` keyword (covers plain
    # constants, f-strings and string concatenation). A reason that is not
    # statically extractable yields '' and can never match an allowlist
    # pattern (fail-closed — such a skip must be made literal or declared).
    reason_expr = call_node.args[0] if call_node.args else None
    for keyword in call_node.keywords:
        if keyword.arg == 'reason':
            reason_expr = keyword.value
    if reason_expr is None:
        return ''
    parts = [
        node.value
        for node in ast.walk(reason_expr)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    return ''.join(parts)

def _load_declared_infra_skip_allowlist(allowlist_path):
    # Fail-closed: the no-skip gate refuses to run without a well-formed
    # declared infra-skip contract (missing/malformed contract => violation,
    # never "treat everything as undeclared-debt and move on").
    if not os.path.isfile(allowlist_path):
        raise AssertionError(
            f"Declared infra-skip allowlist is missing: {allowlist_path}. "
            f"The T00 no-skip gate must not run without its explicit contract "
            f"(fail-closed). Create {DECLARED_INFRA_SKIP_ALLOWLIST_FILENAME} deliberately."
        )
    try:
        with open(allowlist_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        raise AssertionError(
            f"Declared infra-skip allowlist is unreadable/malformed: "
            f"{allowlist_path} ({exc})"
        )
    assert isinstance(data, dict), (
        f"Declared infra-skip allowlist root must be a JSON object: {allowlist_path}"
    )
    entries = data.get('entries')
    assert isinstance(entries, list), (
        f"Declared infra-skip allowlist must contain an 'entries' list: {allowlist_path}"
    )
    allowlist = {}
    for entry in entries:
        assert isinstance(entry, dict), (
            f"Declared infra-skip allowlist entry must be a JSON object: {entry!r}"
        )
        for required_key in ('file', 'reason_patterns', 'env_guard_token', 'justification'):
            assert required_key in entry, (
                f"Declared infra-skip allowlist entry is missing required key "
                f"'{required_key}' (a reviewed contract requires it): {entry!r}"
            )
        rel = entry['file']
        assert isinstance(rel, str) and rel and rel.strip() == rel, (
            f"Declared infra-skip 'file' must be a non-empty trimmed string: {entry!r}"
        )
        assert '\\' not in rel, (
            f"Declared infra-skip 'file' must use forward slashes: {rel}"
        )
        assert not os.path.isabs(rel), (
            f"Declared infra-skip 'file' must be repository-relative, not absolute: {rel}"
        )
        assert '..' not in rel.split('/'), (
            f"Declared infra-skip 'file' must not traverse upward: {rel}"
        )
        patterns = entry['reason_patterns']
        assert (
            isinstance(patterns, list)
            and patterns
            and all(isinstance(p, str) and p.strip() for p in patterns)
        ), (
            f"Declared infra-skip 'reason_patterns' must be a non-empty list of "
            f"non-empty strings: {rel}"
        )
        guard = entry['env_guard_token']
        assert isinstance(guard, str) and guard.strip(), (
            f"Declared infra-skip 'env_guard_token' must be a non-empty string: {rel}"
        )
        justification = entry['justification']
        assert isinstance(justification, str) and justification.strip(), (
            f"Declared infra-skip 'justification' must be a non-empty string "
            f"(a reviewed contract requires one): {rel}"
        )
        assert rel not in allowlist, (
            f"Duplicate declared infra-skip allowlist entry for {rel}"
        )
        allowlist[rel] = entry
    return allowlist

def scan_mandatory_test_tree(tests_root, allowlist_path=None):
    # AST-scan every mandatory T* test file for skip usage (policy A).
    #
    # A real pytest.skip()/pytest.importorskip() call is accepted ONLY when
    # (a) the file source is OS-conditional ('platform.system' present —
    # unchanged rule), or (b) the file has an entry in the declared infra-skip
    # allowlist AND every skip reason matches a declared reason pattern AND
    # the file still contains its declared env-guard token. pytestmark
    # whole-file skips and decorator skips are never allowlisted.
    #
    # Prints a `declared_infra_skips: ...` summary (a green result must never
    # be silent) and returns the list of declared records. Raises
    # AssertionError (fail-closed) on any undeclared skip, undeclared reason,
    # missing env guard, stale entry, or missing/malformed allowlist.
    repo_root = os.path.dirname(os.path.abspath(tests_root))
    if allowlist_path is None:
        allowlist_path = os.path.join(
            tests_root, 'T00_integrity', DECLARED_INFRA_SKIP_ALLOWLIST_FILENAME
        )
    allowlist = _load_declared_infra_skip_allowlist(allowlist_path)

    violations = []
    records = []
    declared_seen = set()
    mandatory_dirs = sorted(glob.glob(os.path.join(tests_root, 'T[0-9][0-9]*')))
    for dir_path in mandatory_dirs:
        for filepath in sorted(glob.glob(os.path.join(dir_path, '*.py'))):
            if os.path.abspath(filepath) == os.path.abspath(__file__):
                continue
            rel = os.path.relpath(
                os.path.abspath(filepath), repo_root
            ).replace(os.sep, '/')
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
            skip_calls = _real_skip_calls(tree)

            # Whole-file pytestmark skip is never an exception (unchanged rule).
            for marks in _pytestmark_assignment(tree):
                violations.append(
                    f"Mandatory test {rel} assigns pytestmark = "
                    f"pytest.mark.{marks[0]}(...), which silently skips the "
                    "entire file. Mandatory tests must FAIL if blocked."
                )
            # Decorator-based skip/xfail/skipif must be OS-conditional
            # (unchanged rule, receiver-agnostic attribute match).
            for scoped in ast.walk(tree):
                if not isinstance(scoped, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                for dec in scoped.decorator_list:
                    dec_func = dec.func if isinstance(dec, ast.Call) else dec
                    if (
                        isinstance(dec_func, ast.Attribute)
                        and dec_func.attr in {'skip', 'xfail', 'skipif'}
                        and 'platform.system' not in source
                    ):
                        violations.append(
                            f"Mandatory test {rel} decorates {scoped.name} with "
                            f"pytest.mark.{dec_func.attr}. Mandatory tests must "
                            "FAIL if blocked, unless OS-specific."
                        )

            if not skip_calls:
                continue

            entry = allowlist.get(rel)
            if entry is None:
                if 'platform.system' not in source:
                    violations.append(
                        f"Mandatory test {rel} contains {len(skip_calls)} real "
                        f"pytest.skip() call(s) and is NOT in the declared "
                        f"infra-skip allowlist ({DECLARED_INFRA_SKIP_ALLOWLIST_FILENAME}). "
                        "Mandatory tests must FAIL if blocked, unless "
                        "OS-specific or explicitly declared (policy A)."
                    )
                continue

            # Declared infra-skip path (policy A): validate the contract.
            declared_seen.add(rel)
            guard = entry['env_guard_token']
            if guard not in source:
                violations.append(
                    f"Declared infra-skip {rel} no longer contains its env-guard "
                    f"token '{guard}'. The skip is no longer guarded; update the "
                    "contract deliberately."
                )
            patterns = entry['reason_patterns']
            for call in skip_calls:
                reason_text = _static_reason_text(call)
                if not any(pattern in reason_text for pattern in patterns):
                    violations.append(
                        f"Declared infra-skip {rel} has a pytest.skip() reason "
                        f"not matching any declared pattern {patterns}: "
                        f"{reason_text!r}. Declare the new reason deliberately "
                        "in the allowlist or make the test FAIL."
                    )
            records.append({
                'file': rel,
                'skip_call_count': len(skip_calls),
                'reason_patterns': patterns,
                'env_guard_token': guard,
            })

    # Stale contract entries: allowlisted file deleted or its skips removed.
    # Both mean the contract no longer matches reality and must be reconciled
    # deliberately (fail-closed, never silently ignored).
    for rel in sorted(set(allowlist) - declared_seen):
        abs_path = os.path.join(repo_root, rel.replace('/', os.sep))
        if not os.path.isfile(abs_path):
            violations.append(
                f"Stale declared infra-skip allowlist entry: {rel} does not "
                "exist. Remove or fix the contract entry deliberately."
            )
        else:
            violations.append(
                f"Stale declared infra-skip allowlist entry: {rel} no longer "
                "contains a real pytest.skip() call. Remove the entry "
                "deliberately (the skips were fixed into real failures)."
            )

    if violations:
        raise AssertionError(
            "T00 no-skip gate violations:\n"
            + "\n".join(f"- {violation}" for violation in violations)
        )

    total_calls = sum(record['skip_call_count'] for record in records)
    print(
        f"{DECLARED_INFRA_SKIP_OUTPUT_TAG} {len(records)} file(s), "
        f"{total_calls} pytest.skip call(s) declared via "
        f"{os.path.basename(allowlist_path)}"
    )
    for record in records:
        print(
            f"  - {record['file']}: {record['skip_call_count']} skip call(s), "
            f"patterns={record['reason_patterns']}, "
            f"env_guard={record['env_guard_token']}"
        )
    return records

def _pytestmark_skip_marks(value_node):
    # Names of pytest.mark.{skip,xfail,skipif} referenced inside a pytestmark
    # assignment value (call form or bare attribute form).
    marks = set()
    if value_node is None:
        return marks
    for node in ast.walk(value_node):
        attr_node = node.func if isinstance(node, ast.Call) else node
        if (
            isinstance(attr_node, ast.Attribute)
            and attr_node.attr in {'skip', 'xfail', 'skipif'}
            and isinstance(attr_node.value, ast.Attribute)
            and attr_node.value.attr == 'mark'
            and isinstance(attr_node.value.value, ast.Name)
            and attr_node.value.value.id == 'pytest'
        ):
            marks.add(attr_node.attr)
    return marks

def _pytestmark_assignment(tree):
    # Yields (marks) for module/class-level `pytestmark = pytest.mark.skip(...)`
    # assignments. Whole-file silent skips hide from per-call/per-decorator
    # detectors, so they must be caught at the assignment itself.
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets, value = [node.target], node.value
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == 'pytestmark' for t in targets):
            continue
        marks = _pytestmark_skip_marks(value)
        if marks:
            yield sorted(marks)

def test_meta_audit_no_skip_in_mandatory_tests():
    # Enforce that no mandatory tests are skipped except: (a) OS-conditional
    # skips ('platform.system' in source), or (b) DECLARED infra-skips (policy
    # A, owner-approved): a real pytest.skip() call inside a file explicitly
    # listed in tests/T00_integrity/declared_infra_skips.json whose reason
    # matches the file's declared reason patterns and whose declared env-guard
    # token is still present. Everything else still fails, including
    # module-level `pytestmark = pytest.mark.skip(...)` whole-file skips and
    # skip/xfail/skipif decorators, which are never allowlisted.
    # tests_root is the parent of all T* gate dirs (repo/tests); the allowlist
    # contract lives at tests/T00_integrity/declared_infra_skips.json and its
    # entry paths are repository-relative (tests/T*/...).
    tests_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mandatory_dirs = sorted(glob.glob(os.path.join(tests_root, 'T[0-9][0-9]*')))
    assert len(mandatory_dirs) >= 12, f"expected all 12 gate dirs, found {mandatory_dirs}"
    scan_mandatory_test_tree(tests_root)

# Pin the current reality (policy A contract has review): the declared
# infra-skip contract covers EXACTLY these eight C1/C2/C3/D1/EE-G1 infra-skip
# files with exactly these skip-call counts. A new, changed or removed entry
# must update this pin deliberately together with declared_infra_skips.json.
_KNOWN_DECLARED_INFRA_SKIP_COUNTS = {
    'tests/T03_capability/test_playwright_backend.py': 2,
    'tests/T03_capability/test_egress_enforcement.py': 4,
    'tests/T04_kernel/test_pg_boot_runtime.py': 2,
    'tests/T04_kernel/test_pg_event_bus.py': 2,
    'tests/T04_kernel/test_pg_migration.py': 1,
    'tests/T04_kernel/test_pg_storage_chaos.py': 2,
    'tests/T04_kernel/test_pg_storage_parity.py': 2,
    'tests/T04_kernel/test_sandbox_evaluator_e2e.py': 3,
}

def test_declared_infra_skip_allowlist_pins_known_files():
    tests_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    records = scan_mandatory_test_tree(tests_root)
    assert {record['file'] for record in records} == set(_KNOWN_DECLARED_INFRA_SKIP_COUNTS)
    assert {
        record['file']: record['skip_call_count'] for record in records
    } == _KNOWN_DECLARED_INFRA_SKIP_COUNTS

# ---------------------------------------------------------------------------
# Contract tests for the policy A gate itself. These exercise
# scan_mandatory_test_tree directly against a minimal tmp tree (real files,
# real AST scan, no mocks) so the allowlist behavior is pinned independent of
# the live repository tree.
# ---------------------------------------------------------------------------

def _write_tmp_gate_tree(tmp_path, test_source, entries=None, allowlist_text=None):
    tests_root = tmp_path / 'tests'
    target_dir = tests_root / 'T04_kernel'
    target_dir.mkdir(parents=True)
    (target_dir / 'test_infra_probe.py').write_text(test_source, encoding='utf-8')
    allowlist_path = None
    if entries is not None or allowlist_text is not None:
        allowlist_path = tests_root / 'T00_integrity' / DECLARED_INFRA_SKIP_ALLOWLIST_FILENAME
        allowlist_path.parent.mkdir(parents=True, exist_ok=True)
        text = allowlist_text if allowlist_text is not None else json.dumps({'entries': entries}, indent=2)
        allowlist_path.write_text(text, encoding='utf-8')
    return str(tests_root), (str(allowlist_path) if allowlist_path else None)

_DECLARED_PROBE_SOURCE = (
    "import os\n"
    "import pytest\n\n"
    "def test_probe():\n"
    "    if not os.environ.get('SCP_PG_TEST_DSN'):\n"
    "        pytest.skip(\n"
    "            'SCP_PG_TEST_DSN not set; declared infra-skip (no assertion hidden)'\n"
    "        )\n"
    "    assert os.environ.get('SCP_PG_TEST_DSN') is not None\n"
)

_DECLARED_PROBE_ENTRY = {
    'file': 'tests/T04_kernel/test_infra_probe.py',
    'reason_patterns': ['declared infra-skip'],
    'env_guard_token': 'SCP_PG_TEST_DSN',
    'justification': 'tmp contract-test probe: real PG is an external dependency',
}

def test_gate_accepts_declared_infra_skip_and_records_it(tmp_path, capsys):
    tests_root, allowlist_path = _write_tmp_gate_tree(
        tmp_path, _DECLARED_PROBE_SOURCE, entries=[_DECLARED_PROBE_ENTRY]
    )
    records = scan_mandatory_test_tree(tests_root, allowlist_path)
    assert [record['file'] for record in records] == ['tests/T04_kernel/test_infra_probe.py']
    assert records[0]['skip_call_count'] == 1
    assert records[0]['env_guard_token'] == 'SCP_PG_TEST_DSN'
    output = capsys.readouterr().out
    assert DECLARED_INFRA_SKIP_OUTPUT_TAG in output, "green run must record declared skips"
    assert 'test_infra_probe.py' in output

def test_gate_fails_on_skip_outside_allowlist(tmp_path):
    undeclared_source = (
        "import pytest\n\n"
        "def test_probe():\n"
        "    pytest.skip('some mysterious reason')\n"
    )
    tests_root, allowlist_path = _write_tmp_gate_tree(tmp_path, undeclared_source, entries=[])
    with pytest.raises(AssertionError) as excinfo:
        scan_mandatory_test_tree(tests_root, allowlist_path)
    message = str(excinfo.value)
    assert 'NOT in the declared infra-skip allowlist' in message
    assert 'tests/T04_kernel/test_infra_probe.py' in message

def test_gate_fails_on_undeclared_reason_inside_allowlisted_file(tmp_path):
    undeclared_reason_source = (
        "import pytest\n\n"
        "def test_probe():\n"
        "    pytest.skip('surprise: totally undeclared reason')\n"
    )
    tests_root, allowlist_path = _write_tmp_gate_tree(
        tmp_path, undeclared_reason_source, entries=[_DECLARED_PROBE_ENTRY]
    )
    with pytest.raises(AssertionError) as excinfo:
        scan_mandatory_test_tree(tests_root, allowlist_path)
    message = str(excinfo.value)
    assert 'not matching any declared pattern' in message
    assert 'surprise: totally undeclared reason' in message

def test_gate_fails_when_env_guard_token_removed(tmp_path):
    # The file skips with a declared reason but no longer contains the
    # declared env-guard token: the guard was stripped, so the contract is
    # broken and the gate must fail until it is reconciled deliberately.
    guard_removed_source = (
        "import pytest\n\n"
        "def test_probe():\n"
        "    pytest.skip('declared infra-skip: guard was stripped away')\n"
    )
    tests_root, allowlist_path = _write_tmp_gate_tree(
        tmp_path, guard_removed_source, entries=[_DECLARED_PROBE_ENTRY]
    )
    with pytest.raises(AssertionError) as excinfo:
        scan_mandatory_test_tree(tests_root, allowlist_path)
    message = str(excinfo.value)
    assert 'no longer contains its env-guard token' in message
    assert 'SCP_PG_TEST_DSN' in message

def test_gate_fails_on_stale_allowlist_entry(tmp_path):
    stale_source = (
        "def test_probe():\n"
        "    assert 1 == 1\n"
    )
    tests_root, allowlist_path = _write_tmp_gate_tree(
        tmp_path, stale_source, entries=[_DECLARED_PROBE_ENTRY]
    )
    with pytest.raises(AssertionError) as excinfo:
        scan_mandatory_test_tree(tests_root, allowlist_path)
    message = str(excinfo.value)
    assert 'Stale declared infra-skip allowlist entry' in message
    assert 'tests/T04_kernel/test_infra_probe.py' in message

def test_gate_fails_closed_when_allowlist_missing(tmp_path):
    tests_root, _unused = _write_tmp_gate_tree(tmp_path, _DECLARED_PROBE_SOURCE)
    with pytest.raises(AssertionError) as excinfo:
        scan_mandatory_test_tree(tests_root)
    message = str(excinfo.value)
    assert 'allowlist is missing' in message
    assert 'fail-closed' in message

def test_gate_fails_closed_on_malformed_allowlist(tmp_path):
    tests_root, allowlist_path = _write_tmp_gate_tree(
        tmp_path, _DECLARED_PROBE_SOURCE, allowlist_text='{ this is not json'
    )
    with pytest.raises(AssertionError) as excinfo:
        scan_mandatory_test_tree(tests_root, allowlist_path)
    assert 'unreadable/malformed' in str(excinfo.value)

def test_gate_fails_closed_on_entry_missing_required_keys(tmp_path):
    incomplete_entry = {
        'file': 'tests/T04_kernel/test_infra_probe.py',
        'reason_patterns': ['declared infra-skip'],
        # env_guard_token and justification deliberately missing
    }
    tests_root, allowlist_path = _write_tmp_gate_tree(
        tmp_path, _DECLARED_PROBE_SOURCE, entries=[incomplete_entry]
    )
    with pytest.raises(AssertionError) as excinfo:
        scan_mandatory_test_tree(tests_root, allowlist_path)
    message = str(excinfo.value)
    assert 'missing required key' in message
    assert 'env_guard_token' in message

def test_meta_audit_no_assert_true():
    # Enforce that no tests just assert True
    root_dir = os.path.dirname(os.path.dirname(__file__))
    for filepath in glob.glob(os.path.join(root_dir, 'T*', '*.py')):
        if filepath == __file__: continue
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'assert ' + 'True' + '\n' in content:
                assert False, f"Test {filepath} contains 'assert True', which is a placeholder and violates Evidence rules."

def test_meta_audit_architecture_coverage():
    # Enforce that all 12 T directories exist
    root_dir = os.path.dirname(os.path.dirname(__file__))
    expected_dirs = [f'T{str(i).zfill(2)}' for i in range(12)]
    found_dirs = [d for d in os.listdir(root_dir) if d.startswith('T')]
    for expected in expected_dirs:
        assert any(d.startswith(expected) for d in found_dirs), f"Missing architectural test layer: {expected}"


def test_meta_audit_no_zero_collected_test_files():
    # A test file that collects zero tests is not evidence (historical lesson #8).
    import ast
    root_dir = os.path.dirname(os.path.dirname(__file__))
    for filepath in sorted(glob.glob(os.path.join(root_dir, 'T*', 'test_*.py'))):
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=filepath)
        has_tests = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_')
            for node in ast.walk(tree)
        )
        assert has_tests, f"Test file {filepath} would collect zero tests and proves nothing."


def test_meta_audit_bare_scp_imports_must_resolve_to_real_production_symbols():
    # Bare (not try-guarded) imports of scp.* must point at REAL production
    # modules and symbols. This catches invented-module harnesses such as the
    # fake EpistemicScanner/IndependentVerifier pair manufactured 2026-09-01.
    # try/except-wrapped imports are the intentional BLOCKED-probe pattern and
    # are allowed to reference absent code.
    import ast
    import importlib
    import importlib.util
    root_dir = os.path.dirname(os.path.dirname(__file__))
    for filepath in sorted(glob.glob(os.path.join(root_dir, 'T*', 'test_*.py'))):
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=filepath)
        inside_try = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for child in ast.walk(node):
                    if child is not node:
                        inside_try.add(id(child))
        for node in ast.walk(tree):
            if id(node) in inside_try:
                continue
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith('scp.'):
                        assert importlib.util.find_spec(alias.name) is not None, (
                            f"{filepath}: bare import of nonexistent production module {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module and node.module.startswith('scp.'):
                assert importlib.util.find_spec(node.module) is not None, (
                    f"{filepath}: bare import of nonexistent production module {node.module}"
                )
                module = importlib.import_module(node.module)
                for alias in node.names:
                    if hasattr(module, alias.name):
                        continue
                    # `from pkg import name` is also valid when `name` is a
                    # submodule of pkg, not an attribute of its __init__.
                    try:
                        importlib.import_module(f"{node.module}.{alias.name}")
                    except ImportError as exc:
                        assert False, (
                            f"{filepath}: bare import of nonexistent production symbol "
                            f"{node.module}.{alias.name} ({exc})"
                        )


def test_meta_audit_no_recursive_pytest_and_no_live_repo_git_mutation():
    # Recursive full-pytest self-audit (fork-bomb lesson) and live-checkout git
    # mutation (T11 lesson 2026-09-01) are both forbidden. git commit/reset in
    # a test file is only tolerated when the file demonstrably isolates itself
    # in a temp repo (tmp_path / TemporaryDirectory / --git-dir / -C).
    root_dir = os.path.dirname(os.path.dirname(__file__))
    isolation_markers = ('--git-dir', 'GIT_DIR', 'tmp_path', 'TemporaryDirectory', '"-C"', "'-C'")
    for filepath in sorted(glob.glob(os.path.join(root_dir, 'T*', 'test_*.py'))):
        if filepath == __file__:
            continue  # this file legitimately quotes the forbidden patterns
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if 'pytest.main(' in content:
            assert False, f"Test {filepath} invokes pytest.main() - recursive full-pytest self-audit."
        for pattern in ('"git", "commit"', "'git', 'commit'", '"git", "reset"', "'git', 'reset'"):
            if pattern in content and not any(marker in content for marker in isolation_markers):
                assert False, (
                    f"Test {filepath} runs git commit/reset against the live checkout without an "
                    "isolated temp repo. Mandatory tests must never mutate main-checkout HEAD."
                )

import pytest


def test_meta_audit_t05_no_forbidden_semantic_patterns():
    # Enforce that T05 doesn't use old paid semantics
    forbidden = [
        "paid -> free fallback",
        "paid -> free fallback",
        "[free, paid]",
        "[\"free\", \"paid\"]",
        "paid primary",
        "try paid first"
    ]
    root_dir = os.path.dirname(os.path.dirname(__file__))
    dir_path = os.path.join(root_dir, 'T05_gateway')
    for filepath in glob.glob(os.path.join(dir_path, '*.py')):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().lower()
            for pattern in forbidden:
                if pattern.lower() in content:
                    assert False, f"Test {filepath} contains forbidden semantic pattern: {pattern}"

from unittest.mock import patch

from tools.t00_meta_audit import audit_content, main


def test_t00_fa01_historical_skip_unchanged_passes_as_debt():
    baseline = "import pytest\n@pytest.mark.skip\ndef test_a(): pass"
    candidate = baseline
    new_v, debt = audit_content(candidate, baseline, "tests/test_a.py")
    assert len(new_v) == 0, "Historical skip should not be a new violation"
    assert len(debt) == 1
    assert "FA-01" in debt[0]

def test_t00_fa01_newly_added_skip_fails():
    baseline = "def test_a(): pass"
    candidate = "import pytest\n@pytest.mark.skip\ndef test_a(): pass"
    new_v, debt = audit_content(candidate, baseline, "tests/test_a.py")
    assert len(new_v) == 1, "New skip must be flagged as new violation"
    assert "FA-01" in new_v[0]
    assert len(debt) == 0

def test_t00_fa01_newly_added_xfail_fails():
    baseline = "def test_a(): pass"
    candidate = "import pytest\n@pytest.mark.xfail\ndef test_a(): pass"
    new_v, debt = audit_content(candidate, baseline, "tests/test_a.py")
    assert len(new_v) == 1
    assert "FA-01" in new_v[0]
    
def test_t00_fa01_pytest_skip_call_fails():
    baseline = "def test_a(): pass"
    candidate = "import pytest\ndef test_a(): pytest.skip('reason')"
    new_v, debt = audit_content(candidate, baseline, "tests/test_a.py")
    assert len(new_v) == 1
    assert "FA-01" in new_v[0]

def test_t00_fa04_historical_manufactured_green_passes_as_debt():
    baseline = 'def do():\n    return {"status": "VERIFIED"}'
    candidate = baseline
    new_v, debt = audit_content(candidate, baseline, "scp/engine.py")
    assert len(new_v) == 0
    assert len(debt) == 1
    assert "FA-04" in debt[0]

def test_t00_fa04_new_manufactured_green_fails():
    baseline = 'def do():\n    return {"status": "PENDING"}'
    candidate = 'def do():\n    return {"status": "VERIFIED"}'
    new_v, debt = audit_content(candidate, baseline, "scp/engine.py")
    assert len(new_v) == 1
    assert "FA-04" in new_v[0]
    assert len(debt) == 0

def test_t00_removal_of_historical_violation_passes():
    baseline = "import pytest\n@pytest.mark.skip\ndef test_a(): pass"
    candidate = "def test_a(): pass"
    new_v, debt = audit_content(candidate, baseline, "tests/test_a.py")
    assert len(new_v) == 0, "Removing a violation should pass"
    assert len(debt) == 0, "Debt should be cleared"

def test_t00_set_delta_swap_skip():
    baseline = "import pytest\n@pytest.mark.skip\ndef test_a(): pass\n\ndef test_b(): pass"
    candidate = "import pytest\ndef test_a(): pass\n\n@pytest.mark.skip\ndef test_b(): pass"
    
    new_v, debt = audit_content(candidate, baseline, "tests/test_a.py")
    assert len(new_v) == 1, "The new skip on test_b should be flagged"
    assert "test_b" in new_v[0]
    assert len(debt) == 0, "test_a skip is gone, so 0 debt"

def test_scp_tests_is_protected():
    baseline = "def test_a(): pass"
    candidate = "import pytest\n@pytest.mark.skip\ndef test_a(): pass"
    new_v, debt = audit_content(candidate, baseline, "scp/tests/test_a.py")
    assert len(new_v) == 1, "Must protect scp/tests/ as well"

@patch('tools.t00_meta_audit.POLICY_FILE')
def test_missing_policy_fails_closed(mock_policy_file):
    mock_policy_file.exists.return_value = False
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1


def test_fa01_skipif_importorskip_asyncdef():
    baseline = ""
    candidate = "import pytest\n@pytest.mark.skipif(True, reason='foo')\nasync def test_async_a():\n    pytest.importorskip('os')"
    new_v, debt = audit_content(candidate, baseline, "tests/test_a.py")
    
    assert any("skipif in test_async_a" in v for v in new_v)
    assert any("importorskip() in test_async_a" in v for v in new_v)

from tools.t00_meta_audit import check_real_test_deletion


@patch('tools.t00_meta_audit.get_real_nodeids')
@patch('tools.t00_meta_audit.get_baseline_nodeids')
def test_fa02_normal_test_deletion(mock_base, mock_cand):
    mock_base.return_value = {"tests/a.py::test_1", "tests/a.py::test_2"}
    mock_cand.return_value = {"tests/a.py::test_1"}
    v = check_real_test_deletion("origin/main")
    assert len(v) == 1
    assert "tests/a.py::test_2" in v[0]

@patch('tools.t00_meta_audit.get_real_nodeids')
@patch('tools.t00_meta_audit.get_baseline_nodeids')
def test_fa02_class_method_deletion(mock_base, mock_cand):
    mock_base.return_value = {"tests/a.py::TestA::test_1", "tests/a.py::TestB::test_1"}
    mock_cand.return_value = {"tests/a.py::TestA::test_1"}
    v = check_real_test_deletion("origin/main")
    assert len(v) == 1
    assert "TestB::test_1" in v[0]

@patch('tools.t00_meta_audit.get_real_nodeids')
@patch('tools.t00_meta_audit.get_baseline_nodeids')
def test_fa02_parametrized_reduction(mock_base, mock_cand):
    mock_base.return_value = {"tests/a.py::test_1[case1]", "tests/a.py::test_1[case2]"}
    mock_cand.return_value = {"tests/a.py::test_1[case1]"}
    v = check_real_test_deletion("origin/main")
    assert len(v) == 1
    assert "[case2]" in v[0]

@patch('tools.t00_meta_audit.get_real_nodeids')
@patch('tools.t00_meta_audit.get_baseline_nodeids')
def test_fa02_unchanged_passes(mock_base, mock_cand):
    mock_base.return_value = {"tests/a.py::test_1"}
    mock_cand.return_value = {"tests/a.py::test_1"}
    v = check_real_test_deletion("origin/main")
    assert len(v) == 0

@patch('tools.t00_meta_audit.get_real_nodeids')
@patch('tools.t00_meta_audit.get_baseline_nodeids')
def test_fa02_added_tests_passes(mock_base, mock_cand):
    mock_base.return_value = {"tests/a.py::test_1"}
    mock_cand.return_value = {"tests/a.py::test_1", "tests/a.py::test_2"}
    v = check_real_test_deletion("origin/main")
    assert len(v) == 0

@patch('tools.t00_meta_audit.subprocess.run')
def test_fa02_collection_error_fails_closed(mock_run):
    class FakeRes:
        returncode = 1
        stdout = "error"
        stderr = "error"
    mock_run.return_value = FakeRes()
    with pytest.raises(SystemExit) as e:
        check_real_test_deletion("origin/main")
    assert e.value.code == 1


import tempfile
from pathlib import Path as _Path

from tools.t00_meta_audit import get_fa01_signatures
from tools.verify_scp_target_test_coverage import _node_exists


def test_fa01_module_level_pytestmark_skip_is_new_violation():
    baseline = "import pytest\n"
    candidate = (
        "import pytest\n"
        "pytestmark = pytest.mark.skip(reason='whole file skipped')\n"
        "def test_a():\n    assert 1\n"
    )
    new_v, debt = audit_content(candidate, baseline, "tests/test_a.py")
    assert len(new_v) == 1, new_v
    assert "FA-01" in new_v[0]
    assert "pytestmark skip" in new_v[0]
    assert len(debt) == 0

def test_fa01_historical_module_pytestmark_is_tracked_as_debt():
    baseline = "import pytest\npytestmark = pytest.mark.skipif(False, reason='x')\n"
    new_v, debt = audit_content(baseline, baseline, "tests/test_a.py")
    assert len(new_v) == 0
    assert len(debt) == 1
    assert "pytestmark skipif" in debt[0]

def test_fa01_bare_pytestmark_attribute_assignment_is_flagged():
    baseline = ""
    candidate = "import pytest\npytestmark = pytest.mark.xfail\n"
    new_v, _debt = audit_content(candidate, baseline, "tests/test_a.py")
    assert len(new_v) == 1
    assert "pytestmark xfail" in new_v[0]

def test_fa01_unrelated_pytestmark_mark_is_not_flagged():
    candidate = "import pytest\npytestmark = pytest.mark.slow\n"
    new_v, debt = audit_content(candidate, "", "tests/test_a.py")
    assert len(new_v) == 0
    assert len(debt) == 0

def test_node_exists_requires_executable_asserting_test_node():
    with tempfile.TemporaryDirectory() as tmp:
        path = _Path(tmp) / "sample_tests.py"
        path.write_text(
            "def test_placeholder():\n    pass\n\n"
            "def helper_with_assert():\n    assert 1\n\n"
            "def test_real():\n    assert 1 == 1\n\n"
            "def test_uses_raises():\n    import pytest\n"
            "    with pytest.raises(ValueError):\n        raise ValueError()\n\n"
            "def test_nested_assert_only():\n"
            "    def inner():\n        assert 0\n\n"
            "class TestGroup:\n"
            "    def test_inner(self):\n        assert 1\n\n"
            "class TestHollow:\n"
            "    def test_hollow_member(self):\n        pass\n",
            encoding="utf-8",
        )
        assert _node_exists(path, ["test_real"]) is True
        assert _node_exists(path, ["test_uses_raises"]) is True
        assert _node_exists(path, ["TestGroup", "test_inner"]) is True
        assert _node_exists(path, ["test_placeholder"]) is False, "pass-only test must not validate a coverage claim"
        assert _node_exists(path, ["helper_with_assert"]) is False, "helper without test_ prefix must not validate a coverage claim"
        assert _node_exists(path, ["test_nested_assert_only"]) is False, "assert locked inside a nested def proves nothing"
        assert _node_exists(path, ["TestHollow", "test_hollow_member"]) is False, "class of pass-only tests proves nothing"
        assert _node_exists(path, ["test_missing"]) is False

def test_fa01_signatures_covers_module_pytestmark_directly():
    sigs = get_fa01_signatures(
        "import pytest\npytestmark = pytest.mark.skip(reason='r')\n"
    )
    assert any("pytestmark skip" in key for key in sigs)
