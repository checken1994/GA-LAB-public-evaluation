import sys, subprocess, json, re
from pathlib import Path

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('D:/scp/.agents/explorer_survey_1/orphaned_classified.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

truly_dead = data.get('truly_dead', [])

protected = {
    'hello_bug.py',
    '_trace_impl.py',
    'chaos_recovery.py',
    'test_security.py',
    'test_none_safety.py',
    'test_free_catalog.py',
    'golden_task.py',
    'continual.py', # sole file in scp/learning/
}

results = []

for item in truly_dead:
    path = item['path']
    p = Path(path)
    stem = p.stem
    filename = p.name
    
    is_protected = filename in protected or 'audit_engine' in path or 'scp/tests/' in path
    
    # Check imports via rg
    # Pattern 1: import of module
    cmd = ['rg', '-n', '--glob', '!*.log', '--glob', '!*.json', '--glob', '!*.md', rf'\b{stem}\b', 'scp', 'tests', 'tools', 'spec']
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    norm_path = path.replace('/', '\\')
    norm_path_fwd = path.replace('\\', '/')
    all_lines = [l for l in res.stdout.splitlines() if not l.startswith(norm_path) and not l.startswith(norm_path_fwd)]
    
    # Separate actual code imports from comments/type-ignores
    code_import_lines = []
    comment_or_misc_lines = []
    
    for l in all_lines:
        # Check if line is comment or type: ignore[misc]
        stripped = l.split(':', 2)[-1].strip() if l.count(':') >= 2 else l.strip()
        if stripped.startswith('#') or 'type: ignore' in stripped or 'type:ignore' in stripped:
            comment_or_misc_lines.append(l)
        elif bool(re.search(rf'(?:import\s+.*\b{stem}\b|from\s+.*\b{stem}\b\s+import|from\s+\S*{stem}\s+import)', stripped)):
            code_import_lines.append(l)
        else:
            # Check other code occurrences
            code_import_lines.append(l)
            
    results.append({
        'path': path,
        'filename': filename,
        'stem': stem,
        'loc': item['loc'],
        'protected': is_protected,
        'all_matches': len(all_lines),
        'code_imports': code_import_lines,
        'comment_matches': comment_or_misc_lines
    })

# Safe to remove: not protected, 0 code imports!
safe_orphans = [r for r in results if not r['protected'] and len(r['code_imports']) == 0]
print(f'Total Candidates: {len(results)}')
print(f'Safe to delete orphans (0 code imports/references): {len(safe_orphans)}')
total_loc = sum(r['loc'] for r in safe_orphans)
print(f'Total LOC of safe orphans: {total_loc}')

# Sort by LOC descending
safe_orphans.sort(key=lambda x: x['loc'], reverse=True)
for i, r in enumerate(safe_orphans, 1):
    comment_info = f" ({len(r['comment_matches'])} comment refs)" if r['comment_matches'] else ""
    print(f"{i:2d}. {r['loc']:4d} LOC | {r['path']}{comment_info}")

print('\n--- Not safe or needs attention ---')
not_safe = [r for r in results if r['protected'] or len(r['code_imports']) > 0]
for r in not_safe:
    reason = "PROTECTED" if r['protected'] else f"{len(r['code_imports'])} CODE MATCHES"
    print(f" - {r['path']} ({reason})")
    for m in r['code_imports'][:3]:
        print(f"     CODE: {m}")

# Save verified results
with open('D:/scp/.agents/explorer_p1_2_gen2/verified_orphans.json', 'w', encoding='utf-8') as f:
    json.dump({
        'safe_orphans': safe_orphans,
        'not_safe': not_safe
    }, f, indent=2)
