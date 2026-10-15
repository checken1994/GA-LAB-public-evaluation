import json,math,re,collections,time,requests
from _net_guard import safe_get  # [S6b] boundary-validated egress
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CORP=ROOT/'data'/'rag_corpus'/'v20260817'/'chunks.jsonl';BATCH=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833';RET=ROOT/'data'/'rag_standard_retrieval_20260817.jsonl';
def tok(s):return re.findall(r'[\wÀ-ỹ]{3,}',str(s).lower())
chunks=[json.loads(x) for x in CORP.read_text(encoding='utf-8').splitlines() if x.strip()];d=[]
for c in chunks:d.append((c,collections.Counter(tok(c['text']))))
df=collections.Counter();
for c,t in d:
 for w in t:df[w]+=1
N=len(d)
def retrieve(q):
 qt=collections.Counter(tok(q));sc=[]
 for c,t in d:
  s=sum((math.log((N+1)/(df[w]+1))+1)*(1+math.log(f)) for w,f in qt.items() if w in t);sc.append((s,c))
 sc.sort(key=lambda x:(x[0],x[1]['chunk_id']),reverse=True);return [{'chunk_id':c['chunk_id'],'document_id':c['document_id'],'rank':i+1,'score':round(s,6),'text':c['text'],'source_url':c['source_url'],'source_title':c['source_title'],'hash':c['hash']} for i,(s,c) in enumerate(sc[:5])]
qs=[json.loads(x) for x in (BATCH/'questions.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()];items=[];retr=[]
for q in qs:
 top=retrieve(q['question']);retr.append({'question_id':q['id'],'gold_chunk_ids':[],'retrieved':top,'gold_status':'NOT_HUMAN_VERIFIED'});items.append({'id':q['id'],'question':q['question'],'contexts':[f"[chunk_id={x['chunk_id']}] source_url={x['source_url']}\n{x['text']}" for x in top],'ground_truth':'','domain':q.get('domain','general'),'rag_enabled':True})
RET.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in retr)+'\n',encoding='utf-8');p={'questions':items,'baseUrl':'http://127.0.0.1:8000','maxParallel':4,'timeoutSeconds':90,'maxRetries':1,'startPaused':False};r=requests.post('http://127.0.0.1:8000/v3/hands/benchmark/batch',json=p,timeout=30);print(r.text);job=r.json()['job']['jobId'];print('job',job);(ROOT/'data'/'rag_standard_job_id_20260817.txt').open('w',encoding='utf-8').write(job)  # [S6b] Path.open
for _ in range(180):
 time.sleep(2);s=safe_get('http://127.0.0.1:8000/v3/hands/benchmark/batch/'+job,timeout=20,allow_internal=True).json()['job'];
 if s['state']=='COMPLETED':print(s);break
else:print('poll_timeout')
