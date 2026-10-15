import os
import re
import ast
import json
from pathlib import Path
from collections import defaultdict

repo_root = Path("D:/scp")
scp_root = repo_root / "scp"

# 1. Orphaned Files Analysis
# Collect all python files in repo
all_repo_py = list(repo_root.rglob("*.py"))
all_repo_py = [p for p in all_repo_py if ".git" not in p.parts and ".pytest_cache" not in p.parts and "__pycache__" not in p.parts and ".agents" not in p.parts]

# For every file in scp, determine its module name(s)
# e.g. D:/scp/scp/core/foo.py -> scp.core.foo, core.foo, foo
# Also check if it is imported as relative import from sibling
scp_py_files = list(scp_root.rglob("*.py"))

# Read all file contents across repo to search for import references
file_contents = {}
for p in all_repo_py:
    try:
        file_contents[p] = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass

orphaned_candidates = []

for p in scp_py_files:
    if p.name == "__init__.py" or p.name == "__main__.py":
        continue
    rel = p.relative_to(scp_root)
    # mod name: scp.a.b.c or a.b.c
    parts = list(rel.parts)
    parts[-1] = p.stem
    mod_full = "scp." + ".".join(parts)
    mod_short = ".".join(parts)
    stem = p.stem
    
    # Check if imported anywhere in any file
    # We look for mod_full, mod_short, or 'from ... import stem' or relative import
    # or import stem
    found = False
    for other_p, content in file_contents.items():
        if other_p == p:
            continue
        if mod_full in content or mod_short in content:
            found = True
            break
        # Also check if imported by stem in same package
        if p.parent == other_p.parent:
            if f"import {stem}" in content or f"from .{stem}" in content or f"from . import {stem}" in content:
                found = True
                break
        # Check string imports like importlib.import_module or pytest / config
        if f'"{stem}"' in content or f"'{stem}'" in content:
            # could be dynamic import
            found = True
            break

    if not found:
        orphaned_candidates.append(str(p.relative_to(repo_root)).replace("\\", "/"))

print(f"Total scp python files: {len(scp_py_files)}")
print(f"Orphaned candidates count: {len(orphaned_candidates)}")
for o in orphaned_candidates[:20]:
    print("  Orphaned candidate:", o)

with open(repo_root / ".agents/explorer_survey_1/orphaned_candidates.json", "w", encoding="utf-8") as f:
    json.dump(orphaned_candidates, f, indent=2)
