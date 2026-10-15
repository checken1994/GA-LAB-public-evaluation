import json,re,math,collections,time,hashlib
from pathlib import Path
import os
import requests
ROOT=Path(os.environ.get("SCP_ROOT", Path(__file__).resolve().parents[1]));CORP=ROOT/'data'/'rag_corpus'/'v20260817'/'chunks.jsonl';BATCH=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833';OUT=ROOT/'data'/'rag_standard_pipeline_20260817.jsonl';K=5
SCP_INTERNAL_URL=os.environ.get("SCP_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")

def tok(s):return re.findall(r'[\wÀ-ỹ]{3,}',str(s).lower())
chunks=[json.loads(x) for x in CORP.read_text(encoding='utf-8').splitlines() if x.strip()]; docs=[]
for c in chunks: docs.append({'c':c,'t':collections.Counter(tok(c['text']))})
df=collections.Counter();
for d in docs:
 for w in d['t']:df[w]+=1
N=len(docs)
def retrieve(q):
 qt=collections.Counter(tok(q));scores=[]
 for d in docs:
  s=0.0
  for w,qtf in qt.items():
   if w in d['t']:
    idf=math.log((N+1)/(df[w]+1))+1;s+=idf*(1+math.log(qtf))
  scores.append((s,d['c']))
 scores.sort(key=lambda x:(x[0],x[1]['chunk_id']),reverse=True);top=scores[:K]
 return [{'chunk_id':c['chunk_id'],'document_id':c['document_id'],'rank':i+1,'score':round(float(s),6),'text':c['text'],'source_url':c['source_url'],'source_title':c['source_title'],'hash':c['hash']} for i,(s,c) in enumerate(top)]
qs=[json.loads(x) for x in (BATCH/'questions.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()];out=[];session=requests.Session()
for n,q in enumerate(qs,1):
 ret=retrieve(q['question']);payload={'question':q['question'],'contexts':[f"[chunk_id={x['chunk_id']}] source_url={x['source_url']}\n{x['text']}" for x in ret],'retrieved_context': '\n\n'.join(x['text'] for x in ret),'ground_truth':'','rag_enabled':True,'domain_override':q.get('domain','general')}
 try:
  rr=session.post(SCP_INTERNAL_URL + '/ask',json=payload,timeout=(10,90));body=rr.json() if rr.headers.get('content-type','').startswith('application/json') else {'raw':rr.text[:1000]};status=rr.status_code
 except Exception as e:body={'error':str(e)};status=0
 out.append({'question_id':q['id'],'question':q['question'],'retrieval':ret,'generation':body,'http_status':status,'gold_reference':q.get('ground_truth',''),'gold_source_url':q.get('ground_truth_source_url',''),'corpus_version':'v20260817','ground_truth_status':'NOT_HUMAN_VERIFIED'})
 if n%50==0:print('processed',n,flush=True)
OUT.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf-8');print(json.dumps({'rows':len(out),'http_200':sum(x['http_status']==200 for x in out),'output':str(OUT)},ensure_ascii=False))
