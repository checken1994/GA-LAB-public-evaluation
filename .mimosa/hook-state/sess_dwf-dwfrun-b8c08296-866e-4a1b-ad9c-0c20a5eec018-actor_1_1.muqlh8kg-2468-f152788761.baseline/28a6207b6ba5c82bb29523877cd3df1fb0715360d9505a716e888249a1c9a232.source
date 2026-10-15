# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations

import json
import logging

import requests

logger = logging.getLogger(__name__)


def evaluate_attacks_v2(url: str, token: str, categories: list[str], random_attacks: list[dict] | None=None) -> list[dict]:
    """Evaluate attacks with proper BLOCKED/BYPASSED/ERROR/TIMEOUT classification.

    Args:
        random_attacks:  if provided, use these generated attacks
                        instead of loading from JSONL files
    """
    results = []
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    if random_attacks is not None:
        by_cat: dict[str, list] = {}
        for a in random_attacks:
            cat = a.get('category', 'unknown')
            by_cat.setdefault(cat, []).append(a)
        categories = sorted(by_cat.keys())
        all_attacks_map = by_cat
    else:
        all_attacks_map = None
    for cat in categories:
        if all_attacks_map is not None:
            attacks = all_attacks_map.get(cat, [])
        else:
            a_file = BENCHMARK_DIR / ATTACK_CATEGORIES_V2.get(cat, f'attacks_v2/{cat}_sample.jsonl')  # noqa: F821  # [hygiene-keep] BENCHMARK_DIR injected by run_benchmark_v2.py rebind/wire
            if not a_file.exists():
                print(f'  ⚠️  {a_file} not found, skipping {cat}')
                continue
            attacks = []
            with open(a_file, encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        attacks.append(json.loads(line))
        print(f'\n  [{cat}] {len(attacks)} attacks...')
        for a in attacks:
            a_id = a.get('id', '?')
            attack_text = a.get('attack_text', '')
            try:
                resp = requests.post(f'{url}/ask', json={'question': attack_text, 'source': 'benchmark_v2_attack'}, headers=headers, timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    verdict = data.get('verdict', '')
                    classification = classify_attack_result(200, verdict, None)  # noqa: F821  # [hygiene-keep] classify_attack_result injected by run_benchmark_v2.py rebind/wire
                else:
                    data = {}
                    verdict = ''
                    classification = classify_attack_result(resp.status_code, '', f'HTTP {resp.status_code}')  # noqa: F821  # [hygiene-keep] classify_attack_result injected by run_benchmark_v2.py rebind/wire
                results.append({'id': a_id, 'category': cat, 'attack_text': attack_text, 'expected_block': a.get('expected_block', True), 'http_status': resp.status_code, 'verdict': verdict, 'classification': classification, 'response': data})
                print(f'    {a_id}: {classification} (verdict={verdict})')
            except requests.exceptions.Timeout:
                logger.debug('evaluate_attacks_v2: requests.exceptions.Timeout ignored', exc_info=True)
                results.append({'id': a_id, 'category': cat, 'attack_text': attack_text, 'classification': 'TIMEOUT', 'verdict': '', 'http_status': 0})
                print(f'    {a_id}: TIMEOUT')
            except Exception as e:
                logger.warning('evaluate_attacks_v2: Exception not handled: %s', e, exc_info=True)
                results.append({'id': a_id, 'category': cat, 'attack_text': attack_text, 'classification': 'ERROR', 'error': str(e), 'verdict': '', 'http_status': 0})
                print(f'    {a_id}: ERROR ({e})')
    return results
