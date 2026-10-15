import json
from pathlib import Path

repo = Path("D:/scp")
with open(repo / ".agents/explorer_survey_1/verified_orphaned.json", encoding="utf-8") as f:
    orphans = json.load(f)

# Also check if any test in tests/ imports or mentions the stem or module name
tests_py = list((repo / "tests").rglob("*.py"))
test_contents = {t: t.read_text(encoding="utf-8", errors="ignore") for t in tests_py}

results = []
for item in orphans:
    p = repo / item["path"]
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    loc = len(lines)
    stem = p.stem
    mod = item["module"]
    
    # Check if mentioned in tests
    test_mentions = []
    for t_path, content in test_contents.items():
        if mod in content or f"from scp.{mod[4:]}" in content or f"import {stem}" in content:
            test_mentions.append(str(t_path.relative_to(repo)).replace("\\", "/"))
            
    # Check first 5 non-empty lines for docstring/purpose
    doc = ""
    for l in lines[:10]:
        if l.strip().startswith('"""') or l.strip().startswith("'''") or l.strip().startswith("#"):
            doc += l.strip() + " "
            
    results.append({
        "path": item["path"],
        "module": mod,
        "loc": loc,
        "test_mentions": test_mentions,
        "has_tests": len(test_mentions) > 0,
        "header": doc[:120]
    })

results.sort(key=lambda x: x["loc"], reverse=True)

print(f"Total orphaned files analyzed: {len(results)}")
print("\n--- Orphaned with ZERO tests (completely dead): ---")
truly_dead = [r for r in results if not r["has_tests"]]
print(f"Count: {len(truly_dead)}")
for r in truly_dead:
    safe_header = r['header'].encode('ascii', 'replace').decode('ascii')
    print(f"  {r['path']:50} | {r['loc']:4} LOC | {safe_header}")

print("\n--- Orphaned in runtime code but covered by tests: ---")
tested_orphans = [r for r in results if r["has_tests"]]
print(f"Count: {len(tested_orphans)}")
for r in tested_orphans:
    print(f"  {r['path']:50} | {r['loc']:4} LOC | Tests: {len(r['test_mentions'])}")

with open(repo / ".agents/explorer_survey_1/orphaned_classified.json", "w", encoding="utf-8") as f:
    json.dump({"truly_dead": truly_dead, "tested_orphans": tested_orphans}, f, indent=2)
