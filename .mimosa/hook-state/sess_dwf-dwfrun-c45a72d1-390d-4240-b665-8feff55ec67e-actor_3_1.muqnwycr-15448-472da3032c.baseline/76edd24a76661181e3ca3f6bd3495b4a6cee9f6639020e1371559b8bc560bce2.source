# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations

import re


def compute_evidence_metrics(scp_evidence: list[dict], gold_evidence: list[str]) -> dict:
    """Compute evidence grounding + recall.

    Evidence Recall = retrieved_relevant_evidence / gold_evidence
    (NOT coverage — uses gold_evidence as denominator)
    """
    if not gold_evidence:
        return {'gold_evidence_count': 0, 'retrieved_relevant': 0, 'evidence_recall': None, 'note': 'no gold_evidence in dataset — recall N/A'}
    retrieved_relevant = 0
    for gold_ev in gold_evidence:
        gold_words = set(w.lower() for w in re.findall('\\w+', gold_ev) if len(w) > 3)
        if not gold_words:
            continue
        for ev in scp_evidence:
            ev_text = str(ev.get('answer', '') or ev.get('source', '') or '').lower()
            ev_words = set(w for w in re.findall('\\w+', ev_text) if len(w) > 3)
            overlap = gold_words & ev_words
            if len(overlap) / len(gold_words) > 0.5:
                retrieved_relevant += 1
                break
    recall = retrieved_relevant / len(gold_evidence)
    return {'gold_evidence_count': len(gold_evidence), 'retrieved_relevant': retrieved_relevant, 'evidence_recall': round(recall, 4)}
