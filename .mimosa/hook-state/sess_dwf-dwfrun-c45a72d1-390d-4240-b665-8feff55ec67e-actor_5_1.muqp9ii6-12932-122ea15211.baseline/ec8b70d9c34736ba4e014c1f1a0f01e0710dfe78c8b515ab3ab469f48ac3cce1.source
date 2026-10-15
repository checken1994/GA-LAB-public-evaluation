import ast
import hashlib
from pathlib import Path
from collections import defaultdict

repo = Path("D:/scp/scp")

# Find duplicate function definitions across different files
func_hashes = defaultdict(list)
func_names = defaultdict(list)

for py_file in repo.rglob("*.py"):
    if ".git" in py_file.parts or "__pycache__" in py_file.parts:
        continue
    rel = str(py_file.relative_to(repo.parent)).replace("\\", "/")
    try:
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(py_file))
    except Exception:
        continue

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Filter out trivial functions (< 5 statements)
            if len(node.body) < 4:
                continue
            # Extract unparsed code or normalized AST dump
            try:
                code_str = ast.unparse(node.body)
                h = hashlib.sha256(code_str.encode("utf-8")).hexdigest()
                func_hashes[h].append((rel, node.name, node.lineno, len(node.body)))
            except Exception:
                pass
            func_names[node.name].append((rel, node.lineno))

duplicates = [v for k, v in func_hashes.items() if len(v) > 1]
# filter duplicates in different files
inter_file_dups = []
for dup in duplicates:
    files = set(x[0] for x in dup)
    if len(files) > 1:
        inter_file_dups.append(dup)

print(f"Total exact function body duplicates across different files: {len(inter_file_dups)}")
for i, dup in enumerate(sorted(inter_file_dups, key=lambda x: x[0][3], reverse=True)[:15], 1):
    print(f"\nDuplicate Group {i} (body size: {dup[0][3]} stmts):")
    for fpath, name, lineno, _ in dup:
        print(f"  {fpath}:{lineno} in {name}()")
