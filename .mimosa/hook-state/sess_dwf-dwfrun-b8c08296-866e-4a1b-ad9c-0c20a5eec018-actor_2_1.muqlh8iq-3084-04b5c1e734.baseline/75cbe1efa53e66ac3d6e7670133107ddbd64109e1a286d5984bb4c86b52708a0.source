import os
import sys
import ast
import json
from pathlib import Path
from collections import defaultdict

repo_root = Path("D:/scp")
scp_root = repo_root / "scp"

# Gather all python files in repo
def get_py_files(folder):
    return [p for p in folder.rglob("*.py") if ".git" not in p.parts and ".pytest_cache" not in p.parts and "__pycache__" not in p.parts and ".agents" not in p.parts]

all_repo_py = get_py_files(repo_root)
scp_py_files = get_py_files(scp_root)

# Map from module string to Path
# e.g. "scp.core.trace_store" -> Path
# Also handle init files: "scp.core" -> scp/core/__init__.py
mod_to_path = {}
path_to_mod = {}

for p in scp_py_files:
    rel = p.relative_to(repo_root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts.pop()
    else:
        parts[-1] = p.stem
    mod_name = ".".join(parts)
    mod_to_path[mod_name] = p
    path_to_mod[p] = mod_name

# Now parse all imports across all repo python files
# Track which modules in mod_to_path are imported
imported_modules = defaultdict(set) # mod -> set of importing files
subsystem_edges = defaultdict(lambda: defaultdict(int)) # src_sub -> tgt_sub -> count

for py_file in all_repo_py:
    try:
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(py_file))
    except Exception:
        continue
        
    src_sub = None
    if py_file.is_relative_to(scp_root):
        rel_parts = py_file.relative_to(scp_root).parts
        if len(rel_parts) > 1:
            src_sub = rel_parts[0]
        else:
            src_sub = f"root_{py_file.stem}"

    # Determine base module of py_file if within scp
    current_mod_parts = []
    if py_file.is_relative_to(repo_root):
        rel_p = py_file.relative_to(repo_root)
        current_mod_parts = list(rel_p.parts)
        if current_mod_parts[-1] == "__init__.py":
            current_mod_parts.pop()
        else:
            current_mod_parts[-1] = py_file.stem

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name
                # check if target or target prefix is in mod_to_path
                parts = target.split(".")
                for i in range(len(parts), 0, -1):
                    prefix = ".".join(parts[:i])
                    if prefix in mod_to_path:
                        imported_modules[prefix].add(str(py_file.relative_to(repo_root)).replace("\\", "/"))
                        if src_sub and prefix.startswith("scp."):
                            tgt_parts = prefix.split(".")
                            if len(tgt_parts) > 1 and tgt_parts[1] != src_sub:
                                subsystem_edges[src_sub][tgt_parts[1]] += 1
                        break
        elif isinstance(node, ast.ImportFrom):
            target_mod = None
            if node.level == 0:
                target_mod = node.module
            else:
                # relative import
                # level 1 = current package, level 2 = parent package
                if current_mod_parts:
                    base_parts = current_mod_parts[:-1] if py_file.name != "__init__.py" else current_mod_parts
                    up = node.level - 1
                    if up <= len(base_parts):
                        rel_base = base_parts[:len(base_parts)-up] if up > 0 else base_parts
                        if node.module:
                            target_mod = ".".join(rel_base) + "." + node.module
                        else:
                            target_mod = ".".join(rel_base)
            
            if target_mod:
                # Check target_mod itself
                parts = target_mod.split(".")
                for i in range(len(parts), 0, -1):
                    prefix = ".".join(parts[:i])
                    if prefix in mod_to_path:
                        imported_modules[prefix].add(str(py_file.relative_to(repo_root)).replace("\\", "/"))
                        if src_sub and prefix.startswith("scp."):
                            tgt_parts = prefix.split(".")
                            if len(tgt_parts) > 1 and tgt_parts[1] != src_sub:
                                subsystem_edges[src_sub][tgt_parts[1]] += 1
                        break
                # Also check imported names: from scp.core import trace_store
                for alias in node.names:
                    full_name = f"{target_mod}.{alias.name}"
                    if full_name in mod_to_path:
                        imported_modules[full_name].add(str(py_file.relative_to(repo_root)).replace("\\", "/"))
                        if src_sub and full_name.startswith("scp."):
                            tgt_parts = full_name.split(".")
                            if len(tgt_parts) > 1 and tgt_parts[1] != src_sub:
                                subsystem_edges[src_sub][tgt_parts[1]] += 1

# Also check dynamic imports or string mentions:
for py_file in all_repo_py:
    try:
        content = py_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for mod_name in list(mod_to_path.keys()):
        short = mod_name.split(".")[-1]
        if f'"{mod_name}"' in content or f"'{mod_name}'" in content or f'"{short}"' in content or f"'{short}'" in content:
            imported_modules[mod_name].add(str(py_file.relative_to(repo_root)).replace("\\", "/"))

# Find truly orphaned modules in scp/
orphaned = []
for mod, path in mod_to_path.items():
    if path.name in ("__init__.py", "__main__.py"):
        continue
    # If imported by no other file (or only by itself)
    importers = [f for f in imported_modules[mod] if f != str(path.relative_to(repo_root)).replace("\\", "/")]
    if not importers:
        # Also check if imported by tests or anything
        orphaned.append((str(path.relative_to(repo_root)).replace("\\", "/"), mod))

print(f"Verified Orphaned modules count: {len(orphaned)}")
for path_str, mod in sorted(orphaned):
    print(f"  {path_str} ({mod})")

# Write results
with open(repo_root / ".agents/explorer_survey_1/verified_orphaned.json", "w", encoding="utf-8") as fp:
    json.dump([{"path": p, "module": m} for p, m in sorted(orphaned)], fp, indent=2)

# Analyze Cycles between subsystems
subsystems_list = [d.name for d in scp_root.iterdir() if d.is_dir() and not d.name.startswith(".") and d.name != "__pycache__"]
# Cycle detection using DFS
cycles = []
visited = {} # node -> 0: unvisited, 1: visiting, 2: visited
path = []

adj = defaultdict(list)
for s, targets in subsystem_edges.items():
    if s in subsystems_list:
        for t in targets:
            if t in subsystems_list:
                adj[s].append(t)

def dfs(u):
    visited[u] = 1
    path.append(u)
    for v in adj[u]:
        if visited.get(v, 0) == 1:
            # Cycle found
            idx = path.index(v)
            cycle = path[idx:] + [v]
            cycles.append(cycle)
        elif visited.get(v, 0) == 0:
            dfs(v)
    path.pop()
    visited[u] = 2

for sub in subsystems_list:
    visited[sub] = 0

for sub in subsystems_list:
    if visited[sub] == 0:
        dfs(sub)

print(f"\nSubsystem Circular Dependency Chains: {len(cycles)}")
for c in cycles:
    print("  Cycle:", " -> ".join(c))

with open(repo_root / ".agents/explorer_survey_1/subsystem_cycles.json", "w", encoding="utf-8") as fp:
    json.dump(cycles, fp, indent=2)

# Save edges
with open(repo_root / ".agents/explorer_survey_1/subsystem_edges.json", "w", encoding="utf-8") as fp:
    json.dump({k: dict(v) for k, v in subsystem_edges.items()}, fp, indent=2)
