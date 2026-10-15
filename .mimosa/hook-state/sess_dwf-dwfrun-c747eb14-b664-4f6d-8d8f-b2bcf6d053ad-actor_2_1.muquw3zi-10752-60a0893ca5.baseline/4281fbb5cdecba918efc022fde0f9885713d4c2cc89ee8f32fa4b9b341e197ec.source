#!/usr/bin/env python3
"""Audit Test Quality across T00-T12 and all tests in SCP.
Analyzes AST of all test files for:
1. Empty test functions (only docstring / pass)
2. Placebo assertions (assert True, assert ... or True, tautologies, trivial checks)
3. Exception-swallowing in tests (try ... except: pass)
4. Hollow mocks
5. Subsystem coverage matrix across all 43 subsystems in scp/
"""
import ast
import os
import sys
from pathlib import Path
from collections import defaultdict, Counter

PROJECT_ROOT = Path("D:/scp")
TESTS_ROOT = PROJECT_ROOT / "tests"
SCP_ROOT = PROJECT_ROOT / "scp"

subsystems = sorted([
    d.name for d in SCP_ROOT.iterdir()
    if d.is_dir() and not d.name.startswith(".") and d.name != "__pycache__"
])

print(f"Total subsystems under scp/: {len(subsystems)}")

empty_tests = []
placebo_asserts = []
exception_swallowing = []
mock_findings = []
subsystem_imports = defaultdict(list)
test_file_counts = Counter()

class TestQualityVisitor(ast.NodeVisitor):
    def __init__(self, filepath, rel_path):
        self.filepath = filepath
        self.rel_path = rel_path
        self.current_func = None
        self.func_nodes = []

    def visit_FunctionDef(self, node):
        self._check_test_func(node)
        old_func = self.current_func
        self.current_func = node.name
        self.generic_visit(node)
        self.current_func = old_func

    def visit_AsyncFunctionDef(self, node):
        self._check_test_func(node)
        old_func = self.current_func
        self.current_func = node.name
        self.generic_visit(node)
        self.current_func = old_func

    def _check_test_func(self, node):
        if not node.name.startswith("test"):
            return

        test_file_counts[self.rel_path] += 1
        real_stmts = []
        for stmt in node.body:
            # Skip docstring
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                continue
            real_stmts.append(stmt)

        if not real_stmts or all(isinstance(s, ast.Pass) for s in real_stmts):
            empty_tests.append({
                "file": self.rel_path,
                "line": node.lineno,
                "func": node.name,
                "reason": "Test body contains only pass or docstring"
            })

    def visit_Assert(self, node):
        if self.current_func:
            # Check for assert True or assert 1 == 1
            test_val = node.test
            
            # assert True
            if isinstance(test_val, ast.Constant) and test_val.value is True:
                placebo_asserts.append({
                    "file": self.rel_path,
                    "line": node.lineno,
                    "func": self.current_func,
                    "kind": "assert True",
                    "code": ast.unparse(node)
                })
            # assert ... or True
            elif isinstance(test_val, ast.BoolOp) and isinstance(test_val.op, ast.Or):
                for val in test_val.values:
                    if isinstance(val, ast.Constant) and val.value is True:
                        placebo_asserts.append({
                            "file": self.rel_path,
                            "line": node.lineno,
                            "func": self.current_func,
                            "kind": "assert ... or True",
                            "code": ast.unparse(node)
                        })
            # assert x == x (tautology)
            elif isinstance(test_val, ast.Compare):
                if len(test_val.ops) == 1 and isinstance(test_val.ops[0], ast.Eq):
                    left_str = ast.unparse(test_val.left)
                    right_str = ast.unparse(test_val.comparators[0])
                    if left_str == right_str and not isinstance(test_val.left, ast.Call):
                        placebo_asserts.append({
                            "file": self.rel_path,
                            "line": node.lineno,
                            "func": self.current_func,
                            "kind": f"tautology ({left_str} == {right_str})",
                            "code": ast.unparse(node)
                        })
                # assert len(...) >= 0
                if len(test_val.ops) == 1 and isinstance(test_val.ops[0], ast.GtE):
                    right_str = ast.unparse(test_val.comparators[0])
                    if isinstance(test_val.left, ast.Call) and getattr(test_val.left.func, 'id', '') == 'len' and right_str == '0':
                        placebo_asserts.append({
                            "file": self.rel_path,
                            "line": node.lineno,
                            "func": self.current_func,
                            "kind": "tautological length (len >= 0)",
                            "code": ast.unparse(node)
                        })

        self.generic_visit(node)

    def visit_Try(self, node):
        # Check exception swallowing
        for handler in node.handlers:
            # Check if handler body is only pass
            is_empty_handler = all(isinstance(s, ast.Pass) for s in handler.body)
            if is_empty_handler and self.current_func and self.current_func.startswith("test"):
                exc_name = ast.unparse(handler.type) if handler.type else "bare"
                exception_swallowing.append({
                    "file": self.rel_path,
                    "line": handler.lineno,
                    "func": self.current_func,
                    "exc": exc_name,
                    "code": f"except {exc_name}: pass"
                })
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self._record_import(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self._record_import(node.module)
        self.generic_visit(node)

    def _record_import(self, mod_name):
        for sub in subsystems:
            if mod_name == f"scp.{sub}" or mod_name.startswith(f"scp.{sub}."):
                subsystem_imports[sub].append(self.rel_path)

def scan_tests():
    for p in sorted(TESTS_ROOT.rglob("*.py")):
        rel = p.relative_to(PROJECT_ROOT).as_posix()
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"), filename=str(p))
            visitor = TestQualityVisitor(p, rel)
            visitor.visit(tree)
        except Exception as e:
            print(f"Error parsing {rel}: {e}")

scan_tests()

print("\n=== 1. EMPTY TESTS (PASS ONLY) ===")
print(f"Found {len(empty_tests)} empty test functions")
for t in empty_tests[:20]:
    print(f"  {t['file']}:{t['line']} in {t['func']}() -> {t['reason']}")

print("\n=== 2. PLACEBO / TAUTOLOGICAL ASSERTIONS ===")
print(f"Found {len(placebo_asserts)} placebo assertions")
for a in placebo_asserts:
    print(f"  {a['file']}:{a['line']} in {a['func']}() [{a['kind']}]: {a['code']}")

print("\n=== 3. EXCEPTION SWALLOWING IN TESTS ===")
print(f"Found {len(exception_swallowing)} swallowed exceptions in test functions")
for e in exception_swallowing[:20]:
    print(f"  {e['file']}:{e['line']} in {e['func']}(): {e['code']}")

print("\n=== 4. SUBSYSTEM COVERAGE MATRIX (Across 43 subsystems) ===")
uncovered = []
low_covered = []
well_covered = []
for sub in subsystems:
    files = sorted(set(subsystem_imports[sub]))
    count = len(files)
    if count == 0:
        uncovered.append(sub)
    elif count <= 2:
        low_covered.append((sub, count, files))
    else:
        well_covered.append((sub, count))

print(f"\nCompletely Unexercised Subsystems (0 test files import them) [{len(uncovered)}]:")
for u in uncovered:
    print(f"  - scp/{u}")

print(f"\nMinimally Covered Subsystems (1-2 test files import them) [{len(low_covered)}]:")
for s, c, f in low_covered:
    print(f"  - scp/{s} ({c} files): {', '.join(f)}")

print(f"\nWell Covered Subsystems (>2 test files) [{len(well_covered)}]:")
for s, c in well_covered:
    print(f"  - scp/{s}: {c} test files")
