import ast
from pathlib import Path
from collections import defaultdict

repo_root = Path("D:/scp")
scp_root = repo_root / "scp"

# Collect all defs in scp/
definitions = [] # (name, type, rel_path, lineno)

for py_file in scp_root.rglob("*.py"):
    if "__pycache__" in py_file.parts or ".pytest_cache" in py_file.parts:
        continue
    rel = str(py_file.relative_to(repo_root)).replace("\\", "/")
    try:
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(py_file))
    except Exception:
        continue
        
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                definitions.append((node.name, "class", rel, node.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                definitions.append((node.name, "def", rel, node.lineno))

# Read all python files across the repo (scp, tests, tools, scripts, desktop)
all_py_files = [p for p in repo_root.rglob("*.py") if "__pycache__" not in p.parts and ".git" not in p.parts and ".agents" not in p.parts]
all_contents = []
for p in all_py_files:
    try:
        all_contents.append((str(p.relative_to(repo_root)).replace("\\", "/"), p.read_text(encoding="utf-8", errors="ignore")))
    except Exception:
        pass

# Check occurrences
unused_symbols = []
for name, kind, def_file, lineno in definitions:
    # count files where name appears
    occurrences = [fpath for fpath, content in all_contents if name in content]
    if len(occurrences) == 1 and occurrences[0] == def_file:
        # Check if used elsewhere in the same file
        content = next(c for f, c in all_contents if f == def_file)
        # count occurrences in the defining file
        count = content.count(name)
        if count == 1: # only the definition line!
            unused_symbols.append((name, kind, def_file, lineno))

print(f"Total public definitions scanned: {len(definitions)}")
print(f"Completely unreferenced public symbols (count=1 in entire repo): {len(unused_symbols)}")
for name, kind, fpath, lineno in unused_symbols[:30]:
    print(f"  {kind} {name} at {fpath}:{lineno}")

import json
with open(repo_root / ".agents/explorer_survey_1/unused_symbols.json", "w", encoding="utf-8") as fp:
    json.dump([{"name": n, "kind": k, "file": f, "lineno": l} for n, k, f, l in unused_symbols], fp, indent=2)
