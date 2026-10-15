import json,re,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BATCH=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833'
Q=BATCH/'questions.jsonl';R=BATCH/'results.jsonl';OUT=ROOT/'data'/'rag_standard_eval_20260817.jsonl';REPORT=ROOT/'data'/'rag_standard_eval_20260817.json'

def chunk_ids(values):
    text='\n'.join(str(x) for x in (values or []));return re.findall(r'chunk_id=([^\]\s]+)',text)
def urls(values):
    text='\n'.join(str(x) for x in (values or []));return re.findall(r'https?://[^\s\]\)]+',text)
qs={x['id']:x for x in (json.loads(line) for line in Q.read_text(encoding='utf-8').splitlines() if line.strip())}
rows=[]
for line in R.read_text(encoding='utf-8').splitlines():
    if not line.strip():continue
    r=json.loads(line); q=qs.get(r.get('id'),{}); resp=r.get('response') or {}; retrieved=r.get('retrieved_contexts') or q.get('contexts') or []
    ids=chunk_ids(retrieved); src=urls(retrieved); ans=str(resp.get('final_answer') or resp.get('answer') or '').strip()
    ev=resp.get('v100_claims') or {}; evidence=ev.get('evidence') or {}
    gold_url=str(q.get('ground_truth_source_url') or '')
    # No score/rank was recorded by the current custom path; never invent them.
    retrieval_recall='UNAVAILABLE_NO_GOLD_CHUNK_ID'
    context_precision='UNAVAILABLE_NO_HUMAN_RELEVANCE_LABEL'
    answer_correctness='UNAVAILABLE_GOLD_NOT_VERIFIED'
    faithfulness='UNAVAILABLE_NO_CLAIM_LEVEL_NLI'
    answer_relevance='UNAVAILABLE_NO_INDEPENDENT_JUDGE'
    citation='PASS_STRUCTURAL' if ids and src else 'FAIL_NO_PROVENANCE'
    factual='BLOCKED' if 'UNAVAILABLE' in ' '.join([retrieval_recall,context_precision,answer_correctness,faithfulness,answer_relevance]) else 'PASS'
    rows.append({'question_id':r.get('id'),'run_id':r.get('run_id'),'answer_nonempty':bool(ans),'retrieved_chunk_ids':ids,'retrieved_source_urls':src,'gold_source_url':gold_url,'metrics':{'retrieval_recall_at_k':retrieval_recall,'context_precision':context_precision,'answer_correctness':answer_correctness,'faithfulness':faithfulness,'answer_relevance':answer_relevance,'citation_provenance':citation},'runtime_verdict':resp.get('verdict'),'strict_factual_verdict':factual,'blocking_reasons':['gold_answer_not_verified','gold_chunk_ids_missing','retrieval_rank_score_missing','claim_level_faithfulness_not_run']})
OUT.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf-8')
summary={'eval_version':'scp-rag-standard-v1','date':'2026-08-17','source_batch':str(BATCH),'rows':len(rows),'runtime_pass':sum(x.get('runtime_verdict')=='PASS' for x in rows),'strict_factual_pass':sum(x['strict_factual_verdict']=='PASS' for x in rows),'strict_factual_blocked':sum(x['strict_factual_verdict']=='BLOCKED' for x in rows),'answer_nonempty':sum(x['answer_nonempty'] for x in rows),'citation_structural_pass':sum(x['metrics']['citation_provenance']=='PASS_STRUCTURAL' for x in rows),'metric_contract':{'retrieval_recall_at_k':'required','context_precision':'required','answer_correctness':'required','faithfulness':'required','answer_relevance':'required','citation_provenance':'required'},'final_verdict':'BLOCKED_NOT_FACTUAL_PROVEN','reasons':['The current batch path is a custom context-injection path, not a separately measured retriever.','The corpus has source URLs but no gold chunk annotation, rank, score, or independently verified concise gold answer for each row.','Keyword overlap is intentionally excluded from this verdict.']}
REPORT.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
