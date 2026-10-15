# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='SCP Benchmark v2 — proper anti-hallucination evaluator')
    parser.add_argument('--url', default=DEFAULT_URL)  # noqa: F821  # [hygiene-keep] DEFAULT_URL injected by run_benchmark_v2.py rebind/wire
    parser.add_argument('--token', default=DEFAULT_TOKEN)  # noqa: F821  # [hygiene-keep] DEFAULT_TOKEN injected by run_benchmark_v2.py rebind/wire
    parser.add_argument('--questions', nargs='*', default=list(QUESTION_CATEGORIES_V2.keys()))  # noqa: F821  # [hygiene-keep] QUESTION_CATEGORIES_V2 injected by run_benchmark_v2.py rebind/wire
    parser.add_argument('--attacks', nargs='*', default=list(ATTACK_CATEGORIES_V2.keys()))  # noqa: F821  # [hygiene-keep] ATTACK_CATEGORIES_V2 injected by run_benchmark_v2.py rebind/wire
    parser.add_argument('--no-corruption', action='store_true', help='Skip self-correction test')
    parser.add_argument('--output', default='results_v2/scp_results.json')
    parser.add_argument('--random', action='store_true', help='Generate random questions (not static dataset) — each run tests different questions')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducibility (default: None = truly random)')
    parser.add_argument('--num-math', type=int, default=10, help='Number of random math questions')
    parser.add_argument('--num-geography', type=int, default=10, help='Number of random geography questions')
    parser.add_argument('--num-ambiguous', type=int, default=5, help='Number of random ambiguous questions')
    parser.add_argument('--num-attacks', type=int, default=5, help='Number of random attacks')
    parser.add_argument('--save-questions', default=None, help='Save generated questions to JSONL (for reproducibility audit)')
    parser.add_argument('--auto-start', action='store_true', help='Auto-start SCP server if not running (launches start-scp.bat/sh)')
    args = parser.parse_args()
    print('\n' + '=' * 70)
    print('  SCP Benchmark v2 — Proper Anti-Hallucination Evaluator')
    print('=' * 70)
    print(f'  URL: {args.url}')
    if args.random:
        print(f"  Mode: RANDOM (seed={(args.seed if args.seed is not None else 'None (truly random)')})")
        print(f'  Questions: {args.num_math} math + {args.num_geography} geography + {args.num_ambiguous} ambiguous')
        print(f'  Attacks: {args.num_attacks}')
    else:
        print('  Mode: STATIC (from JSONL files)')
        print(f'  Questions: {args.questions}')
        print(f'  Attacks: {args.attacks}')
    print(f"  Self-correction: {('OFF' if args.no_corruption else 'ON (inject corrupted_answer)')}")
    random_questions = None
    random_attacks = None
    if args.random:
        random_questions, random_attacks = generate_random_questions(num_math=args.num_math, num_geography=args.num_geography, num_ambiguous=args.num_ambiguous, num_attacks=args.num_attacks, seed=args.seed)  # noqa: F821  # [hygiene-keep] generate_random_questions injected by run_benchmark_v2.py rebind/wire
        print(f'\n  📝 Generated {len(random_questions)} questions + {len(random_attacks)} attacks')
        for q in random_questions[:3]:
            ans = q.get('expected_answer', '(unanswerable)')
            print(f"     [{q['category']}] {q['question']} → {ans}")
        print(f'     ... and {len(random_questions) - 3} more')
        if args.save_questions:
            save_questions_to_jsonl(random_questions, random_attacks, args.save_questions)  # noqa: F821  # [hygiene-keep] save_questions_to_jsonl injected by run_benchmark_v2.py rebind/wire
            print(f'  💾 Questions saved to: {args.save_questions} (+ _attacks.jsonl)')

    def _check_server_health(url: str, timeout: int=5) -> bool:
        """Return True if /health returns 200."""
        try:
            r = requests.get(f'{url}/health', timeout=timeout)
            return r.ok
        except Exception:
            logger.warning('main._check_server_health: Exception not handled', exc_info=True)
            return False

    def _auto_start_scp():
        """Auto-start SCP server (Windows + Linux/Mac)."""
        import platform
        import subprocess
        project_root = BENCHMARK_DIR.parent.parent  # noqa: F821  # [hygiene-keep] BENCHMARK_DIR injected by run_benchmark_v2.py rebind/wire
        start_bat = project_root / 'start-scp.bat'
        start_sh = project_root / 'start-scp.sh'
        print(f'\n  🚀 Auto-starting SCP (from {project_root})...')
        if platform.system() == 'Windows':
            if not start_bat.exists():
                print(f'     ❌ {start_bat} not found')
                return False
            try:
                subprocess.Popen(['cmd', '/c', 'start', 'SCP-Server', str(start_bat)], cwd=str(project_root), creationflags=subprocess.DETACHED_PROCESS if hasattr(subprocess, 'DETACHED_PROCESS') else 0)
            except Exception as _e:
                logger.warning('main._auto_start_scp: Exception not handled: %s', _e, exc_info=True)
                print(f'     ⚠️  Failed to launch start-scp.bat: {_e}')
                print(f'     Manual: cd {project_root} && .\\start-scp.bat')
                return False
        else:
            if not start_sh.exists():
                print(f'     ❌ {start_sh} not found')
                return False
            try:
                subprocess.Popen(['bash', str(start_sh), 'daemon'], cwd=str(project_root))
            except Exception as _e:
                logger.warning('main._auto_start_scp: Exception not handled: %s', _e, exc_info=True)
                print(f'     ⚠️  Failed to launch start-scp.sh: {_e}')
                print(f'     Manual: cd {project_root} && ./start-scp.sh daemon')
                return False
        print('     ✅ SCP launcher started — waiting for server to bind (up to 90s)...')
        return True
    server_ok = _check_server_health(args.url)
    if not server_ok:
        if args.auto_start:
            print(f'\n  ⚠️  SCP not running at {args.url}')
            if _auto_start_scp():
                import time as _time
                for _i in range(30):
                    _time.sleep(3)
                    server_ok = _check_server_health(args.url, timeout=3)
                    if server_ok:
                        print(f'     ✅ SCP is up! (after {(_i + 1) * 3}s)')
                        break
                    print(f'     ... waiting ({(_i + 1) * 3}s)')
        if not server_ok:
            print(f'\n❌ Cannot connect to SCP at {args.url}')
            print('   Either:')
            print('     1. Start SCP manually:  start-scp.bat (Windows) or ./start-scp.sh (Linux/Mac)')
            print('     2. Use --auto-start flag:  python run_benchmark_v2.py --random --auto-start ...')
            sys.exit(1)
    print(f'\n  Server: ✅ (connected to {args.url})')
    q_results = evaluate_questions_v2(args.url, args.token, args.questions, inject_corrupted=not args.no_corruption, random_questions=random_questions)  # noqa: F821  # [hygiene-keep] evaluate_questions_v2 injected by run_benchmark_v2.py rebind/wire
    a_results = evaluate_attacks_v2(args.url, args.token, args.attacks, random_attacks=random_attacks)  # noqa: F821  # [hygiene-keep] evaluate_attacks_v2 injected by run_benchmark_v2.py rebind/wire
    metrics = compute_all_metrics_v2(q_results, a_results)  # noqa: F821  # [hygiene-keep] compute_all_metrics_v2 injected by run_benchmark_v2.py rebind/wire
    print(f"\n{'=' * 70}")
    print('  7 PROPER ANTI-HALLUCINATION METRICS (v2)')
    print(f"{'=' * 70}")
    m = metrics['A_factual_accuracy']
    print(f"\n  A. Factual Accuracy:        {m['value']:.1%} ({m['correct']}/{m['total_answerable_answered']})")
    print(f"     Method: {m['method']}")
    m = metrics['B_claim_hallucination']
    hr = m['hallucination_rate']
    print(f'\n  B. Claim Hallucination:     {hr:.1%}' if hr is not None else '\n  B. Claim Hallucination:     N/A (no verifiable claims)')
    print(f"     Total claims: {m['total_claims']} (SUPPORTED={m['supported']}, CONTRADICTED={m['contradicted']}, UNSUPPORTED={m['unsupported']}, UNKNOWN={m['unknown']})")
    print(f"     Method: {m['method']}")
    m = metrics['D_evidence_recall']
    er = m['value']
    print(f'\n  D. Evidence Recall:         {er:.1%}' if er is not None else '\n  D. Evidence Recall:         N/A (no gold_evidence)')
    print(f"     Questions with gold_evidence: {m['questions_with_gold_evidence']}")
    print(f"     Method: {m['method']}")
    m = metrics['E_abstention']
    print('\n  E. Abstention:')
    print(f"     Correct answer:          {m['correct_answer']}")
    print(f"     Correct abstention:      {m['correct_abstention']}")
    print(f"     False abstention:        {m['false_abstention']} (should have answered)")
    print(f"     False answer:            {m['false_answer']} (should have abstained)")
    aa = m['abstention_accuracy']
    print(f'     Abstention accuracy:     {aa:.1%}' if aa is not None else '     Abstention accuracy:     N/A')
    print(f"     Selective accuracy:      {m['selective_accuracy']:.1%}")
    m = metrics['F_self_correction']
    print('\n  F. Self-Correction:')
    print(f"     Corrections attempted:   {m['corrections_attempted']}")
    print(f"     Corrections success:     {m['corrections_success']}")
    print(f"     False corrections:       {m['false_corrections']}")
    sr = m['correction_success_rate']
    print(f'     Success rate:            {sr:.1%}' if sr is not None else '     Success rate:            N/A (no corrupted_answer)')
    m = metrics['G_security']
    print('\n  G. Security:')
    print(f"     BLOCKED:                 {m['blocked']}")
    print(f"     BYPASSED:                {m['bypassed']}")
    print(f"     ERROR:                   {m['errors']}")
    print(f"     TIMEOUT:                 {m['timeouts']}")
    ar = m['attack_resistance']
    print(f'     Attack resistance:       {ar:.1%}' if ar is not None else '     Attack resistance:       N/A')
    print(f"     NOTE: {m['note']}")
    m = metrics['latency']
    print(f"\n  Latency (mean/p50/p95):     {m['mean_ms']}ms / {m['p50_ms']}ms / {m['p95_ms']}ms")
    print(f"{'=' * 70}")
    _output_path = Path(args.output)
    _output_path.parent.mkdir(parents=True, exist_ok=True)
    output = {'version': 'v2', 'timestamp': time.time(), 'iso_timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'url': args.url, 'mode': 'random' if args.random else 'static', 'seed': args.seed if args.random else None, 'question_counts': {'math': args.num_math if args.random else None, 'geography': args.num_geography if args.random else None, 'ambiguous': args.num_ambiguous if args.random else None, 'attacks': args.num_attacks if args.random else None} if args.random else None, 'metrics': metrics, 'question_results': q_results, 'attack_results': a_results}
    with _output_path.open('w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f'\n📄 Results saved to: {args.output}')
