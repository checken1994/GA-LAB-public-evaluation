import os
import ast
import json
from pathlib import Path
from collections import defaultdict

scp_root = Path("D:/scp/scp")
dirs = sorted([d.name for d in scp_root.iterdir() if d.is_dir() and not d.name.startswith(".") and d.name != "__pycache__"])

subsystems = {}
for d in dirs:
    sub_path = scp_root / d
    py_files = list(sub_path.rglob("*.py"))
    total_loc = 0
    god_files = []
    outbound = set()
    
    for f in py_files:
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
            loc = len(lines)
            total_loc += loc
            if loc > 500:
                rel_path = str(f.relative_to(scp_root.parent)).replace("\\", "/")
                god_files.append((rel_path, loc))
                
            tree = ast.parse("\n".join(lines), filename=str(f))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.name
                        if name.startswith("scp."):
                            parts = name.split(".")
                            if len(parts) > 1 and parts[1] != d:
                                outbound.add(parts[1])
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module
                    if mod and mod.startswith("scp."):
                        parts = mod.split(".")
                        if len(parts) > 1 and parts[1] != d:
                            outbound.add(parts[1])
        except Exception as e:
            pass
            
    subsystems[d] = {
        "subsystem": d,
        "path": f"scp/{d}",
        "file_count": len(py_files),
        "loc": total_loc,
        "god_files": sorted(god_files, key=lambda x: x[1], reverse=True),
        "outbound": sorted(list(outbound)),
        "inbound": set()
    }

# Also check root scp/*.py imports to know what standalone files import and who imports what
root_py_files = [f for f in scp_root.iterdir() if f.is_file() and f.suffix == ".py"]
root_data = {}
for f in root_py_files:
    lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
    loc = len(lines)
    tree = ast.parse("\n".join(lines), filename=str(f))
    outbound = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("scp."):
                    parts = alias.name.split(".")
                    if len(parts) > 1:
                        outbound.add(parts[1])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("scp."):
                parts = node.module.split(".")
                if len(parts) > 1:
                    outbound.add(parts[1])
    root_data[f.name] = {"loc": loc, "outbound": sorted(list(outbound))}
    for target in outbound:
        if target in subsystems:
            subsystems[target]["inbound"].add(f"root/{f.name}")

# Compute inbound
for src, data in subsystems.items():
    for target in data["outbound"]:
        if target in subsystems:
            subsystems[target]["inbound"].add(src)

for k, v in subsystems.items():
    v["inbound"] = sorted(list(v["inbound"]))

output_path = Path("D:/scp/.agents/explorer_survey_1/subsystems_data.json")
with open(output_path, "w", encoding="utf-8") as fp:
    json.dump(subsystems, fp, indent=2)

print(f"Successfully wrote data for {len(subsystems)} subsystems to {output_path}")
