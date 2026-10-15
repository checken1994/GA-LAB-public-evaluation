import ast
import os
import re

tests_dir = r"D:\scp\tests"
scp_dir = r"D:\scp\scp"

# 1. Enumerate all test suites
test_suites = {}
for item in os.listdir(tests_dir):
    p = os.path.join(tests_dir, item)
    if os.path.isdir(p) and not item.startswith(".") and item != "__pycache__":
        py_files = [f for f in os.listdir(p) if f.endswith(".py")]
        test_suites[item] = len(py_files)

# 2. Map all 43 subsystems under scp/
subsystems = [d for d in os.listdir(scp_dir) if os.path.isdir(os.path.join(scp_dir, d)) and not d.startswith(".") and d != "__pycache__"]

# Find all imports across all test files
test_imports = set()
all_test_files = []
for root, _, files in os.walk(tests_dir):
    for f in files:
        if f.endswith(".py"):
            all_test_files.append(os.path.join(root, f))
# Also check tests inside scp/tests if any
for root, _, files in os.walk(os.path.join(scp_dir, "tests")):
    for f in files:
        if f.endswith(".py"):
            all_test_files.append(os.path.join(root, f))

trivial_assertions = []
sleep_calls = []
external_state = []
heavy_mocking = {} # file -> patch count
subsystem_references = {sub: 0 for sub in subsystems}

for tf in all_test_files:
    rel_tf = os.path.relpath(tf, r"D:\scp")
    try:
        with open(tf, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        continue

    # Count subsystem references in test content
    for sub in subsystems:
        # check imports like `from scp.sub` or `import scp.sub`
        if f"scp.{sub}" in content or f"from scp import {sub}" in content:
            subsystem_references[sub] += 1

    lines = content.splitlines()
    try:
        tree = ast.parse(content, filename=tf)
    except Exception:
        continue

    mock_count = 0
    for node in ast.walk(tree):
        # Trivial assertions
        if isinstance(node, ast.Assert):
            # assert True
            if isinstance(node.test, ast.Constant) and node.test.value is True:
                trivial_assertions.append({
                    "file": rel_tf,
                    "line": node.lineno,
                    "type": "assert True",
                    "code": lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
                })
            # assert x is not None
            elif isinstance(node.test, ast.Compare):
                if len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.IsNot):
                    right = node.test.comparators[0]
                    if isinstance(right, ast.Constant) and right.value is None:
                        # check if it's the only assertion or trivial
                        trivial_assertions.append({
                            "file": rel_tf,
                            "line": node.lineno,
                            "type": "assert x is not None",
                            "code": lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
                        })

        # Sleep calls
        if isinstance(node, ast.Call):
            is_sleep = False
            if isinstance(node.func, ast.Attribute) and node.func.attr == "sleep":
                is_sleep = True
            elif isinstance(node.func, ast.Name) and node.func.id == "sleep":
                is_sleep = True
            if is_sleep:
                sleep_calls.append({
                    "file": rel_tf,
                    "line": node.lineno,
                    "code": lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
                })

            # Check patch count
            if (isinstance(node.func, ast.Attribute) and node.func.attr in ("patch", "patch.object")) or \
               (isinstance(node.func, ast.Name) and node.func.id in ("patch", "mocker")):
                mock_count += 1

    # Check for external URLs / hardcoded ports
    for i, line in enumerate(lines, 1):
        # External URLs (not localhost, not 127.0.0.1, not example.com, not test)
        match = re.search(r'https?://(?!localhost|127\.0\.0\.1|0\.0\.0\.0|testserver|example\.com)[a-zA-Z0-9.-]+', line)
        if match and not line.strip().startswith("#") and "mock" not in line.lower():
            external_state.append({
                "file": rel_tf,
                "line": i,
                "type": "External URL",
                "match": match.group(0),
                "code": line.strip()
            })

    if mock_count > 0:
        heavy_mocking[rel_tf] = mock_count

output = {
    "test_suites": test_suites,
    "subsystems_total": len(subsystems),
    "subsystem_references": subsystem_references,
    "trivial_assertions": trivial_assertions,
    "sleep_calls": sleep_calls,
    "external_state": external_state,
    "heavy_mocking": sorted(heavy_mocking.items(), key=lambda x: x[1], reverse=True)[:30]
}

import json
with open(r"D:\scp\.agents\explorer_survey_3\r4_test_analysis.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print("Test Suites:", test_suites)
zero_cov = [s for s, count in subsystem_references.items() if count == 0]
print("Subsystems with 0 test imports:", zero_cov)
print(f"Total trivial assertions: {len(trivial_assertions)}")
print(f"Total sleep calls: {len(sleep_calls)}")
print(f"Total external URL refs in tests: {len(external_state)}")
