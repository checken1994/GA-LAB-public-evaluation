# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations


def classify_claim(claim: dict, gold_evidence: list[str], scp_evidence: list[dict]) -> str:
    """Classify a claim as SUPPORTED / CONTRADICTED / UNSUPPORTED / UNKNOWN.

    SUPPORTED: claim is entailed by gold_evidence OR scp_evidence
    CONTRADICTED: claim contradicts gold_evidence
    UNSUPPORTED: no evidence supports or contradicts claim
    UNKNOWN: can't determine (no evidence available)
    """
    claim_text = claim.get('text', '').lower()
    claim_value = claim.get('value')
    claim_entity = claim.get('entity', '').lower()
    claim_target = claim.get('target', '').lower()
    if not gold_evidence and (not scp_evidence):
        return 'UNKNOWN'
    for evidence in gold_evidence:
        ev_text = evidence.lower()
        if claim_value is not None:
            ev_nums = [extract_number(evidence)]  # noqa: F821  # [hygiene-keep] extract_number injected by run_benchmark_v2.py rebind/wire
            for ev_num in ev_nums:
                if ev_num is not None:
                    if abs(claim_value - ev_num) / max(abs(ev_num), 0.001) < 0.01:
                        return 'SUPPORTED'
                    elif abs(claim_value - ev_num) / max(abs(ev_num), 0.001) > 0.25:
                        return 'CONTRADICTED'
        if claim_entity and claim_target:
            if claim_entity in ev_text and claim_target in ev_text:
                return 'SUPPORTED'
            if claim_entity in ev_text and claim_target not in ev_text:
                return 'CONTRADICTED'
        if claim_text and len(claim_text) > 5:
            claim_words = set(w for w in claim_text.split() if len(w) > 3)
            ev_words = set(w for w in ev_text.split() if len(w) > 3)
            overlap = claim_words & ev_words
            if len(overlap) >= 2 and len(overlap) / max(len(claim_words), 1) > 0.5:
                return 'SUPPORTED'
    for ev in scp_evidence:
        ev_text = str(ev.get('answer', '') or ev.get('value', '')).lower()
        if not ev_text:
            continue
        if claim_value is not None:
            ev_num = extract_number(ev_text)  # noqa: F821  # [hygiene-keep] extract_number injected by run_benchmark_v2.py rebind/wire
            if ev_num is not None:
                if abs(claim_value - ev_num) / max(abs(ev_num), 0.001) < 0.01:
                    return 'SUPPORTED'
        if claim_entity and claim_target:
            if claim_entity in ev_text and claim_target in ev_text:
                return 'SUPPORTED'
    return 'UNSUPPORTED'
