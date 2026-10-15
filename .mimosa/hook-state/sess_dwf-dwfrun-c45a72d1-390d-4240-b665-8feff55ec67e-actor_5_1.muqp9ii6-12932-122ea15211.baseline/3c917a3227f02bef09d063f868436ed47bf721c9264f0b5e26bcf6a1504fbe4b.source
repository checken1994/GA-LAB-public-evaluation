#!/usr/bin/env python3
"""Check assert x is not None where x is never further inspected in the test function."""
import ast
from pathlib import Path

TESTS_ROOT = Path("D:/scp/tests")

suspicious = []

for p in sorted(TESTS_ROOT.rglob("*.py")):
    try:
        tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"), filename=str(p))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                # Count total asserts
                asserts = [s for s in ast.walk(node) if isinstance(s, ast.Assert)]
                if len(asserts) == 1:
                    a = asserts[0]
                    # Check if it's assert x is not None
                    if isinstance(a.test, ast.Compare):
                        if len(a.test.ops) == 1 and isinstance(a.test.ops[0], ast.IsNot):
                            comparator = a.test.comparators[0]
                            if isinstance(comparator, ast.Constant) and comparator.value is None:
                                target_var = ast.unparse(a.test.left)
                                suspicious.append({
                                    "file": p.relative_to(TESTS_ROOT.parent).as_posix(),
                                    "line": a.lineno,
                                    "func": node.name,
                                    "var": target_var,
                                    "code": ast.unparse(a)
                                })
    except Exception:
        pass

print(f"Found {len(suspicious)} tests where the ONLY assertion is 'assert x is not None':")
for s in suspicious:
    print(f"  {s['file']}:{s['line']} in {s['func']}(): {s['code']}")
