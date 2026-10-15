import json,re,math,collections,time,os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import requests
from _net_guard import safe_post  # [S6b] boundary-validated egress
ROOT=Path(os.environ.get("SCP_ROOT", Path(__file__).resolve().parents[1]));CORP=ROOT/'data'/'rag_corpus'/'v20260817'/'chunks.jsonl';BATCH=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833';OUT=ROOT/'data'/'rag_standard_pipeline_20260817.jsonl';TMP=ROOT/'data'/'rag_standard_pipeline_20260817.partial.jsonl';K=5;WORKERS=4
SCP_INTERNAL_URL=os.environ.get("SCP_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")

def tok(s):return re.findall(r'[\wÀ-ỹ]{3,}',str(s).lower())
chunks=[json.loads(x) for x in CORP.read_text(encoding='utf-8').splitlines() if x.strip()];docs=[]
for c in chunks:docs.append({'c':c,'t':collections.Counter(tok(c['text']))})
df=collections.Counter()
for d in docs:
 for w in d['t']:df[w]+=1
N=len(docs)
def retrieve(q):
 qt=collections.Counter(tok(q));scores=[]
 for d in docs:
  s=0.0
  for w,qtf in qt.items():
   if w in d['t']:s+=(math.log((N+1)/(df[w]+1))+1)*(1+math.log(qtf))
  scores.append((s,d['c']))
 scores.sort(key=lambda x:(x[0],x[1]['chunk_id']),reverse=True);return [{'chunk_id':c['chunk_id'],'document_id':c['document_id'],'rank':i+1,'score':round(float(s),6),'text':c['text'],'source_url':c['source_url'],'source_title':c['source_title'],'hash':c['hash']} for i,(s,c) in enumerate(scores[:K])]
def one(q):
 ret=retrieve(q['question']);payload={'question':q['question'],'contexts':[f"[chunk_id={x['chunk_id']}] source_url={x['source_url']}\n{x['text']}" for x in ret],'retrieved_context':'\n\n'.join(x['text'] for x in ret),'ground_truth':'','rag_enabled':True,'domain_override':q.get('domain','general')};last='';
 for attempt in range(2):
  try:
   rr=safe_post(SCP_INTERNAL_URL + '/ask',json=payload,timeout=(10,90),allow_internal=True);
   try:body=rr.json()
   except Exception:body={'raw':rr.text[:1000]}
   return {'question_id':q['id'],'question':q['question'],'retrieval':ret,'generation':body,'http_status':rr.status_code,'gold_reference':q.get('ground_truth',''),'gold_source_url':q.get('ground_truth_source_url',''),'corpus_version':'v20260817','ground_truth_status':'NOT_HUMAN_VERIFIED','attempts':attempt+1}
  except Exception as e:last=str(e);time.sleep(1)
 return {'question_id':q['id'],'question':q['question'],'retrieval':ret,'generation':{'error':last},'http_status':0,'gold_reference':q.get('ground_truth',''),'gold_source_url':q.get('ground_truth_source_url',''),'corpus_version':'v20260817','ground_truth_status':'NOT_HUMAN_VERIFIED','attempts':2}
qs=[json.loads(x) for x in (BATCH/'questions.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()];done={}
if TMP.exists():
 for x in TMP.read_text(encoding='utf-8').splitlines():
  if x.strip():
   z=json.loads(x);done[z['question_id']]=z
pending=[q for q in qs if q['id'] not in done];print('resume_done',len(done),'pending',len(pending),flush=True)
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
 fs={ex.submit(one,q):q['id'] for q in pending};count=0
 for f in as_completed(fs):
  z=f.result();done[z['question_id']]=z;count+=1
  if count%20==0:
   TMP.write_text('\n'.join(json.dumps(done[q['id']],ensure_ascii=False) for q in qs if q['id'] in done)+'\n',encoding='utf-8');print('checkpoint',len(done),flush=True)
TMP.write_text('\n'.join(json.dumps(done[q['id']],ensure_ascii=False) for q in qs if q['id'] in done)+'\n',encoding='utf-8');OUT.write_text(TMP.read_text(encoding='utf-8'),encoding='utf-8');print(json.dumps({'rows':len(done),'http_200':sum(z['http_status']==200 for z in done.values()),'errors':sum(z['http_status']!=200 for z in done.values()),'output':str(OUT)},ensure_ascii=False))
