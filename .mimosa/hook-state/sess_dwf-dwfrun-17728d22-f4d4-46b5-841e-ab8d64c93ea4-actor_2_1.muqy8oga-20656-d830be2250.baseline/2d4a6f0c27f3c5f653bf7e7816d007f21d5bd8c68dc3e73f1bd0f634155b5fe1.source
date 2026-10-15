import json,requests,time
from pathlib import Path
import os
from _net_guard import safe_post  # [S6b] boundary-validated egress
ROOT=Path(os.environ.get("SCP_ROOT", Path(__file__).resolve().parents[1]));C=ROOT/'data'/'rag_corpus'/'canonical-v1-20260817'/'corpus_1000.jsonl';OUT=ROOT/'data'/'ragas_ares_canonical_1000_20260817.jsonl';rows=[]
SCP_INTERNAL_URL=os.environ.get("SCP_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
for line in C.read_text(encoding='utf-8').splitlines():
 if not line.strip():continue
 c=json.loads(line);base={'question_id':c['question_id'],'question':c['question'],'corpus_version':c['corpus_version'],'gold_chunk_ids':c['gold_chunk_ids'],'gold_answer':c['gold_answer'],'review_status':c['review_status'],'review_source_url':c['review_source_url'],'retrieval_metrics':{'retrieval_recall_at_1':'UNAVAILABLE_NO_INDEX_RUN','retrieval_precision_at_1':'UNAVAILABLE_NO_HUMAN_GOLD','mrr':'UNAVAILABLE_NO_INDEX_RUN','ndcg_at_10':'UNAVAILABLE_NO_INDEX_RUN'},'citation_provenance':'UNAVAILABLE_NOT_RUN'}
 if not c['answerable']:
  base.update({'pipeline_status':'ABSTAIN','abstain_reason':c['review_status'],'generation':None,'metrics':{'context_relevance':'BLOCKED','context_precision':'BLOCKED','answer_correctness':'BLOCKED','faithfulness':'BLOCKED','answer_relevance':'BLOCKED'}})
 else:
  d=c['documents'][0];ctx=f"[chunk_id={d['chunk_id']}] source_url={d['source_url']}\n{d['text'][:5000]}";payload={'question':c['question'],'contexts':[ctx],'retrieved_context':d['text'][:5000],'ground_truth':'','rag_enabled':True,'domain_override':'general'}
  try:
   r=safe_post(SCP_INTERNAL_URL + '/ask',json=payload,timeout=(10,90),allow_internal=True);base.update({'pipeline_status':'SUCCESS' if r.status_code==200 else 'GENERATION_FAILED','generation':r.json() if r.headers.get('content-type','').startswith('application/json') else {'raw':r.text[:500]},'retrieved':[{'chunk_id':d['chunk_id'],'rank':1,'score':'RECORDED_BY_CORPUS_SELECTION','source_url':d['source_url']}],'citation_provenance':'STRUCTURAL_CANONICAL_URL'})
  except Exception as e:base.update({'pipeline_status':'GENERATION_FAILED','generation':{'error':str(e)}})
 rows.append(base)
OUT.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf-8');from collections import Counter;print(json.dumps({'rows':len(rows),'status':Counter(x['pipeline_status'] for x in rows),'review_status':Counter(x['review_status'] for x in rows)},ensure_ascii=False))
