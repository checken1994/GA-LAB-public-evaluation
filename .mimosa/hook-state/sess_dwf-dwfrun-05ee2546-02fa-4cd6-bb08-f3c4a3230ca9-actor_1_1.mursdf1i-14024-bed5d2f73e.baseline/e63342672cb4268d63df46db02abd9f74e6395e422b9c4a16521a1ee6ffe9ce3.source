import os
import re

project_root = r"D:\scp"
ports_to_find = [3000, 3001, 3030, 5432, 6379, 8000, 8080, 8081, 9222]

port_hits = []

target_dirs = ["scp", "dashboard", "mini-services", "tools"]
for d in target_dirs:
    full_d = os.path.join(project_root, d)
    if not os.path.exists(full_d):
        continue
    for root, _, files in os.walk(full_d):
        if "node_modules" in root or ".next" in root or "__pycache__" in root:
            continue
        for f in files:
            if f.endswith((".py", ".ts", ".tsx", ".js", ".json", ".bat", ".sh", ".yaml", ".yml")):
                path = os.path.join(root, f)
                rel = os.path.relpath(path, project_root)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fp:
                        lines = fp.read().splitlines()
                    for i, line in enumerate(lines, 1):
                        if line.strip().startswith("//") or line.strip().startswith("#"):
                            continue
                        for p in ports_to_find:
                            if str(p) in line:
                                # check if preceded or followed by digits
                                if re.search(rf'(?<!\d){p}(?!\d)', line):
                                    port_hits.append({
                                        "file": rel,
                                        "line": i,
                                        "port": p,
                                        "code": line.strip()[:120]
                                    })
                except Exception:
                    pass

print(f"Total port hits found: {len(port_hits)}")
by_port = {}
for h in port_hits:
    by_port.setdefault(h["port"], []).append(h)

for p, hits in sorted(by_port.items()):
    print(f"Port {p}: {len(hits)} occurrences across {len(set(h['file'] for h in hits))} files")
    for sample in hits[:3]:
        print(f"   {sample['file']}:{sample['line']} -> {sample['code']}")

import json
with open(r"D:\scp\.agents\explorer_survey_3\port_hits.json", "w", encoding="utf-8") as fp:
    json.dump(port_hits, fp, indent=2)
