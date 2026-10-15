import json
from pathlib import Path
from collections import defaultdict

repo = Path("D:/scp")
with open(repo / ".agents/explorer_survey_1/subsystem_cycles.json", encoding="utf-8") as f:
    cycles = json.load(f)

with open(repo / ".agents/explorer_survey_1/subsystem_edges.json", encoding="utf-8") as f:
    edges = json.load(f)

print(f"Total cycles detected: {len(cycles)}")
for i, c in enumerate(cycles, 1):
    chain_str = " -> ".join(c)
    print(f"\nCycle {i:2d}: {chain_str}")
    for j in range(len(c) - 1):
        s1, s2 = c[j], c[j+1]
        weight = edges.get(s1, {}).get(s2, 0)
        print(f"   [{s1}] -> [{s2}] ({weight} import refs)")
