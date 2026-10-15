# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations

import json
import logging
import time

import requests

logger = logging.getLogger(__name__)


def evaluate_questions_v2(url: str, token: str, categories: list[str], inject_corrupted: bool=True, random_questions: list[dict] | None=None) -> list[dict]:
    """Evaluate questions with proper methodology.

    Args:
        url: SCP server URL
        token: auth token
        categories: question categories (used if random_questions is None)
        inject_corrupted: whether to inject corrupted_answer for self-correction test
        random_questions:  if provided, use these generated questions
                          instead of loading from JSONL files
    """
    results = []
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    if random_questions is not None:
        by_cat: dict[str, list] = {}
        for q in random_questions:
            cat = q.get('category', 'unknown')
            by_cat.setdefault(cat, []).append(q)
        categories = sorted(by_cat.keys())
        all_questions_map = by_cat
    else:
        all_questions_map = None
    for cat in categories:
        if all_questions_map is not None:
            questions = all_questions_map.get(cat, [])
        else:
            q_file = BENCHMARK_DIR / QUESTION_CATEGORIES_V2.get(cat, f'questions_v2/{cat}_sample.jsonl')  # noqa: F821  # [hygiene-keep] BENCHMARK_DIR injected by run_benchmark_v2.py rebind/wire
            if not q_file.exists():
                print(f'  ⚠️  {q_file} not found, skipping {cat}')
                continue
            questions = []
            with open(q_file, encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        questions.append(json.loads(line))
        print(f'\n  [{cat}] {len(questions)} questions...')
        correct_count = 0
        for q in questions:
            q_id = q.get('id', '?')
            question = q.get('question', '')
            expected = q.get('expected_answer', '')
            answer_type = q.get('answer_type', 'string')
            answerable = q.get('answerable', True)
            gold_evidence = q.get('gold_evidence', [])
            corrupted = q.get('corrupted_answer', '')
            ai_answer = corrupted if inject_corrupted and corrupted and answerable else ''
            try:
                t0 = time.time()
                resp = requests.post(f'{url}/ask', json={'question': question, 'ai_answer': ai_answer, 'source': 'benchmark_v2'}, headers=headers, timeout=120)
                latency_ms = (time.time() - t0) * 1000
                if resp.status_code != 200:
                    results.append({'id': q_id, 'category': cat, 'question': question, 'expected_answer': expected, 'answer_type': answer_type, 'answerable': answerable, 'gold_evidence': gold_evidence, 'corrupted_answer': corrupted, 'ai_answer_injected': ai_answer, 'correct': False, 'error': f'HTTP {resp.status_code}', 'latency_ms': round(latency_ms, 2)})
                    continue
                data = resp.json()
                scp_answer = data.get('final_answer', '')
                verdict = data.get('verdict', '')
                is_correct, match_method = check_factual_correctness(scp_answer, expected, answer_type)  # noqa: F821  # [hygiene-keep] check_factual_correctness injected by run_benchmark_v2.py rebind/wire
                if answerable and verdict != 'UNKNOWN':
                    if is_correct:
                        correct_count += 1
                claims = extract_claims_from_answer(scp_answer, question)  # noqa: F821  # [hygiene-keep] extract_claims_from_answer injected by run_benchmark_v2.py rebind/wire
                scp_evidence = data.get('slm_trace') or []
                claim_analysis = compute_claim_hallucination(claims, gold_evidence, scp_evidence)  # noqa: F821  # [hygiene-keep] compute_claim_hallucination injected by run_benchmark_v2.py rebind/wire
                evidence_metrics = compute_evidence_metrics(scp_evidence, gold_evidence)  # noqa: F821  # [hygiene-keep] compute_evidence_metrics injected by run_benchmark_v2.py rebind/wire
                results.append({'id': q_id, 'category': cat, 'question': question, 'expected_answer': expected, 'answer_type': answer_type, 'answerable': answerable, 'gold_evidence': gold_evidence, 'corrupted_answer': corrupted, 'ai_answer_injected': ai_answer, 'correct': is_correct, 'match_method': match_method, 'verdict': verdict, 'confidence': data.get('confidence', 0), 'scp_answer': scp_answer[:500], 'latency_ms': round(latency_ms, 2), 'claim_analysis': claim_analysis, 'evidence_metrics': evidence_metrics, 'response': data})
            except requests.exceptions.Timeout:
                logger.debug('evaluate_questions_v2: requests.exceptions.Timeout ignored', exc_info=True)
                results.append({'id': q_id, 'category': cat, 'question': question, 'expected_answer': expected, 'answer_type': answer_type, 'answerable': answerable, 'gold_evidence': gold_evidence, 'corrupted_answer': corrupted, 'ai_answer_injected': ai_answer, 'correct': False, 'error': 'timeout', 'latency_ms': 120000})
            except Exception as e:
                logger.warning('evaluate_questions_v2: Exception not handled: %s', e, exc_info=True)
                results.append({'id': q_id, 'category': cat, 'question': question, 'expected_answer': expected, 'answer_type': answer_type, 'answerable': answerable, 'gold_evidence': gold_evidence, 'corrupted_answer': corrupted, 'ai_answer_injected': ai_answer, 'correct': False, 'error': str(e)})
        denom = sum(1 for r in results if r.get('category') == cat and r.get('answerable'))
        acc = correct_count / denom if denom > 0 else 0
        print(f'  → [{cat}] Accuracy: {correct_count}/{denom} = {acc:.1%}' + (' (N/A — no answerable questions)' if denom == 0 else ''))
    return results
