import subprocess, json
from pathlib import Path

with open('.agents/explorer_survey_1/orphaned_classified.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

truly_dead = data.get('truly_dead', [])
print(f"Total truly_dead candidates: {len(truly_dead)}")

verified_orphans = []

for item in truly_dead:
    path = item['path']
    stem = Path(path).stem
    
    # Exclude files that are known to be needed or part of other tasks:
    if stem in ['hello_bug', '_trace_impl', 'chaos_recovery']:
        continue
    
    cmd = ['rg', '-n', '--glob', '!*.json', '--glob', '!*.md', '--glob', '!*.log', rf'\b{stem}\b', 'scp', 'tests']
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    # Filter out self-references (the file itself)
    norm_path = path.replace('/', '\\')
    norm_path_fwd = path.replace('\\', '/')
    lines = [line for line in res.stdout.splitlines() if not line.startswith(norm_path) and not line.startswith(norm_path_fwd)]
    
    # Also check if it appears in spec/ or tools/
    cmd_spec = ['rg', '-n', rf'\b{stem}\b', 'spec', 'tools']
    res_spec = subprocess.run(cmd_spec, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    spec_lines = res_spec.stdout.splitlines()
    
    verified_orphans.append({
        'path': path,
        'stem': stem,
        'loc': item['loc'],
        'scp_tests_matches': len(lines),
        'spec_matches': len(spec_lines),
        'match_details': lines[:3] + spec_lines[:3]
    })

print('\n--- SUMMARY ---')
zero_callers = [v for v in verified_orphans if v['scp_tests_matches'] == 0]
print(f"Files with 0 matches in scp/ and tests/: {len(zero_callers)}")
total_loc = sum(v['loc'] for v in zero_callers)
print(f"Total LOC in zero-caller files: {total_loc}")
for i, v in enumerate(zero_callers, 1):
    print(f"{i:>2}. {v['loc']:>4} LOC | {v['path']} (spec/tools matches: {v['spec_matches']})")
    if v['spec_matches'] > 0:
        for d in v['match_details']:
            print(f"    ref: {d}")

# Also print ones with matches to see what matched
some_matches = [v for v in verified_orphans if v['scp_tests_matches'] > 0]
print(f"\nFiles with matches in scp/ or tests/: {len(some_matches)}")
for v in some_matches:
    print(f"MATCH: {v['path']} ({v['scp_tests_matches']} matches)")
    for d in v['match_details']:
        print(f"    ref: {d}")
