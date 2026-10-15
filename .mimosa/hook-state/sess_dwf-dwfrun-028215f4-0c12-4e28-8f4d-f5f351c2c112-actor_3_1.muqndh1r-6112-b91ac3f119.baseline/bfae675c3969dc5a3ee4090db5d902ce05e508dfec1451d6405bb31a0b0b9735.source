import sys,json,re,datetime,concurrent.futures,requests
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));from scp.rag.canonical_retriever import CanonicalRetriever
from _net_guard import safe_post  # [S6b] boundary-validated egress
QUESTION_FILES=[ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833'/'questions.jsonl'];OUT=ROOT/'data'/'rag_local_answer_drafts_v1_20260817.jsonl';ENDPOINT='http://127.0.0.1:11434/api/chat'
def terms(s):return set(re.findall(r'[\wÀ-ỹ]{4,}',str(s).lower()))
def loadq():
 rows=[];seen=set()
 for src in QUESTION_FILES:
  for line in src.read_text(encoding='utf-8').splitlines():
   if not line.strip():continue
   x=json.loads(line);qid=x.get('id') or x.get('question_id')
   if qid in seen:continue
   seen.add(qid);rows.append(x)
 return rows
r=CanonicalRetriever()
def one(x):
 q=x.get('question','');hits=r.retrieve(q,k=1);base={'question_id':x.get('id') or x.get('question_id'),'question':q,'domain':x.get('domain','general'),'gold_chunk_ids':[],'gold_answer':'','gold_status':'ABSTAIN','source_url':'','retrieval_score':None,'review_method':'local_llama_draft_plus_programmatic_gate','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'error':None}
 if not hits:return base
 h=hits[0];base['gold_chunk_ids']=[h['chunk_id']];base['source_url']=h['source_url'];base['retrieval_score']=h.get('retrieval_score');context=f"[chunk_id={h['chunk_id']}] source_url={h['source_url']}\n{h['text'][:4000]}"
 prompt={'model':'llama3.2:latest','stream':False,'format':'json','options':{'temperature':0},'messages':[{'role':'system','content':'Answer only from the supplied source. If unsupported, return JSON {"answer":"","supported":false}. Otherwise return JSON {"answer":"short answer","supported":true}. Do not add outside facts.'},{'role':'user','content':f'Question: {q}\nSource:\n{context}'}]}
 try:
  z=safe_post(ENDPOINT,json=prompt,timeout=180,allow_internal=True);z.raise_for_status();raw=z.json().get('message',{}).get('content','');obj=json.loads(raw) if isinstance(raw,str) else raw;ans=str(obj.get('answer','')).strip();sup=bool(obj.get('supported'))
  et=terms(ans);ct=terms(h['text']);ratio=len(et&ct)/max(1,len(et))
  if sup and ans and ratio>=0.35:
   base['gold_answer']=ans;base['gold_status']='LOCAL_SOURCE_GROUNDED_DRAFT';base['support_ratio']=round(ratio,4)
  else:base['gold_status']='ABSTAIN';base['support_ratio']=round(ratio,4)
 except Exception as e:
  base['error']=type(e).__name__+': '+str(e)[:240];base['gold_status']='ABSTAIN'
 return base
rows=loadq();
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:out=list(ex.map(one,rows))
OUT.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf-8');from collections import Counter
print(json.dumps({'rows':len(out),'local_drafts':sum(x['gold_status']=='LOCAL_SOURCE_GROUNDED_DRAFT' for x in out),'abstain':sum(x['gold_status']=='ABSTAIN' for x in out),'errors':sum(bool(x['error']) for x in out),'status_counts':dict(Counter(x['gold_status'] for x in out))},ensure_ascii=False))
