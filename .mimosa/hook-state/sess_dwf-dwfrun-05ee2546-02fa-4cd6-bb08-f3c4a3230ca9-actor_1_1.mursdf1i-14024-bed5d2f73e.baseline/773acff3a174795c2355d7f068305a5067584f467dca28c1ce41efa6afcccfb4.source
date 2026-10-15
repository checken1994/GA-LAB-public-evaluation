import subprocess, sys, json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Candidate list of top 35 safe orphans to delete:
candidates = [
    "scp/runtime/experts/chem_reality_astro.py",
    "scp/runtime/experts/misc.py",
    "scp/security/h8_redteam_bridge.py",
    "scp/runtime/engine_parts/scpv14_process_mixin.py",
    "scp/meta/calibration_engine.py",
    "scp/meta/adversary_verifier.py",
    "scp/brain/error_store_index.py",
    "scp/benchmark/run_benchmark_enhanced.py",
    "scp/meta/question_tracker.py",
    "scp/ai_patterns.py",
    "scp/runtime/experts/numeric_data.py",
    "scp/meta/verdict_predictor.py",
    "scp/meta/self_questioning.py",
    "scp/runtime/experts/math_biology.py",
    "scp/runtime/healing_v14.py",
    "scp/security/threat_intel.py",
    "scp/knowledge/scheduled_crawler.py",
    "scp/meta/cognitive_engine.py",
    "scp/core/real_question_fetcher.py",
    "scp/knowledge/cwe_exploit_store.py",
    "scp/benchmark/run_baseline.py",
    "scp/core/auto_backup.py",
    "scp/meta/logical_auditor.py",
    "scp/security/auto_payload_generator.py",
    "scp/security/memory_guard.py",
    "scp/security/rogue_ai_detector.py",
    "scp/core/react_agent.py",
    "scp/core/github_backup.py",
    "scp/meta/multi_llm_check.py",
    "scp/benchmark/compare_results.py",
    "scp/security/attack_classifier.py",
    "scp/runtime/parallel_pipeline.py",
    "scp/core/evidence_filter.py",
    "scp/core/healing_engine.py",
    "scp/runtime/experts/management.py",
    "scp/core/environment_snapshot.py",
    "scp/runtime/timing_and_restart.py",
    "scp/security/quorum_why.py",
    "scp/observability/otel_exporter.py",
    "scp/core/dependency_resolver.py",
]

report = []

for rel_path in candidates:
    p = Path(rel_path)
    if not p.exists():
        print(f"MISSING: {rel_path}")
        continue
    loc = len(p.read_text(encoding='utf-8', errors='ignore').splitlines())
    stem = p.stem
    
    # Run rg for import or usage
    cmd = ['rg', '-n', '--glob', '!*.log', '--glob', '!*.json', '--glob', '!*.md', rf'\b{stem}\b', 'scp', 'tests']
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    norm_p = rel_path.replace('/', '\\')
    norm_fwd = rel_path.replace('\\', '/')
    lines = [l for l in res.stdout.splitlines() if not l.startswith(norm_p) and not l.startswith(norm_fwd)]
    
    # Filter out comments and type: ignore
    code_lines = []
    for l in lines:
        code_part = l.split(':', 2)[-1].strip() if l.count(':') >= 2 else l.strip()
        if not code_part.startswith('#') and 'type: ignore' not in code_part and 'type:ignore' not in code_part:
            code_lines.append(l)
            
    report.append({
        'path': rel_path,
        'loc': loc,
        'stem': stem,
        'all_matches': len(lines),
        'code_matches': len(code_lines),
        'code_details': code_lines
    })

print(f"Analyzed {len(report)} candidates.")
total_loc = sum(r['loc'] for r in report)
print(f"Total LOC: {total_loc}")

zero_code = [r for r in report if r['code_matches'] == 0]
print(f"Files with exactly 0 code usages in scp and tests: {len(zero_code)}")

with open('D:/scp/.agents/explorer_p1_2_gen2/top35_orphans_verified.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2)

print("\n--- Summary of Verified 30+ Orphans ---")
for i, r in enumerate(report, 1):
    status = "CLEAN (0 code refs)" if r['code_matches'] == 0 else f"{r['code_matches']} code refs: {r['code_details'][0]}"
    print(f"{i:2d}. {r['loc']:4d} LOC | {r['path']} -> {status}")
