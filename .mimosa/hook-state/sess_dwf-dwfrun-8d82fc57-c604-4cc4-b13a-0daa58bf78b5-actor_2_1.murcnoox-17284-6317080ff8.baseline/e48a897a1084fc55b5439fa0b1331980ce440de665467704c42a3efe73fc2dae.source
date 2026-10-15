import json,time,requests,datetime
from pathlib import Path
import os
from _net_guard import safe_post  # [S6b] boundary-validated egress
ROOT=Path(os.environ.get('SCP_ROOT', Path(__file__).resolve().parents[1]));SRC=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833'/'questions.jsonl';OUT=ROOT/'reports'/'SCP_FULL_RUNTIME_RAG_1000_2026-08-17.jsonl';OUT.parent.mkdir(parents=True,exist_ok=True)
SCP_INTERNAL_URL=os.environ.get('SCP_INTERNAL_URL','http://127.0.0.1:8000').rstrip('/')
seen=set()
if OUT.exists():
 for line in OUT.read_text(encoding='utf-8').splitlines():
  if line.strip():
   try:seen.add(json.loads(line).get('question_id'))
   except Exception:pass
rows=[json.loads(x) for x in SRC.read_text(encoding='utf-8').splitlines() if x.strip()]
with OUT.open('a',encoding='utf-8') as f:
 for i,x in enumerate(rows,1):
  qid=x.get('id') or x.get('question_id')
  if qid in seen:continue
  body={'question':x.get('question',''),'domain':x.get('domain','general'),'rag_enabled':True,'return_evidence':True,'include_sources':True}
  rec={'question_id':qid,'question':x.get('question',''),'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
  try:
   r=safe_post(SCP_INTERNAL_URL+'/ask',json=body,timeout=240,allow_internal=True);rec['http_status']=r.status_code;data=r.json();rec.update({k:data.get(k) for k in ('verdict','run_status','confidence','governance_decision','final_answer','run_id','trace_id','elapsed_ms','v100_claims')});rec['error']=None
  except Exception as e:rec.update({'http_status':None,'verdict':'REQUEST_ERROR','run_status':'ERROR','error':type(e).__name__+': '+str(e)[:240]})
  f.write(json.dumps(rec,ensure_ascii=False)+'\n');f.flush();seen.add(qid)
  if i%25==0:print(json.dumps({'processed':i,'written':len(seen)},ensure_ascii=False),flush=True)
print(json.dumps({'total_input':len(rows),'written_total':len(seen),'output':str(OUT)},ensure_ascii=False))
