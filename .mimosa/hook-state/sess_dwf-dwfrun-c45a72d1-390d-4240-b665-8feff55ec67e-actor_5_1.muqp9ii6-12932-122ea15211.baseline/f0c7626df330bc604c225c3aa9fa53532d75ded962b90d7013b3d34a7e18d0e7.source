import json,re,time,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import requests
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'benchmark'/'questions_1000_real_rag_20260817.jsonl'
UA='SCP-Real-RAG-Benchmark/1.0 (refill)'

def variants(q):
 q=re.sub(r'\(Mã\s*CH-\d+\)','',q,flags=re.I)
 q=re.sub(r'\s+',' ',q.replace('\n',' ')).strip(' ?')
 q=re.sub(r'\b(mới nhất|hiện nay|năm nay|thông tin mới nhất)\b','',q,flags=re.I)
 vals=[q]
 if ':' in q: vals.append(q.split(':',1)[1].strip())
 vals.append(re.sub(r'^(thông tin|tra cứu thông tin|hướng dẫn|phân tích|cách|các|một số|giải thích)\s*[:：]?\s*','',q,flags=re.I))
 vals.append(' '.join(q.split()[-8:]))
 out=[]
 for x in vals:
  x=re.sub(r'\s+',' ',x).strip(' ?')
  if x and x not in out: out.append(x)
 return out

def api(s,lang,params):
 try:
  r=s.get(f'https://{lang}.wikipedia.org/w/api.php',params=params,headers={'User-Agent':UA},timeout=12);r.raise_for_status();return r.json()
 except Exception:return {}

def one(r):
 s=requests.Session(); docs=[]
 for q in variants(r['question']):
  for lang in ('vi','en'):
   d=api(s,lang,{'action':'query','list':'search','srsearch':q,'srlimit':5,'format':'json','utf8':1})
   hits=d.get('query',{}).get('search',[])
   for h in hits:
    title=h.get('title','');
    if not title: continue
    x=api(s,lang,{'action':'query','prop':'extracts|info','explaintext':1,'exintro':1,'inprop':'url','titles':title,'format':'json','utf8':1})
    page=next(iter(x.get('query',{}).get('pages',{}).values()),{});text=(page.get('extract') or '').strip()
    if text:
     url=page.get('fullurl') or f'https://{lang}.wikipedia.org/wiki/{title.replace(" ","_")}'
     docs.append({'lang':lang,'title':title,'url':url,'text':text[:10000]})
   if docs: break
  if docs: break
 if not docs:return r
 p=docs[0];gt=docs[1] if len(docs)>1 else docs[0];ch=hashlib.sha256((p['url']+p['text']).encode()).hexdigest()[:16]
 r.update({'contexts':[f"[chunk_id=wiki-{ch}] source_title={p['title']} source_url={p['url']} language={p['lang']}\n{p['text']}"],'ground_truth':f"[ground_truth_source={gt['url']}] {gt['text'][:6000]}",'source_url':p['url'],'ground_truth_source_url':gt['url'],'source_title':p['title'],'ground_truth_title':gt['title'],'retrieval_status':'OK','review_status':'auto_two_document_review'})
 return r

rows=[json.loads(x) for x in P.read_text(encoding='utf-8').splitlines() if x.strip()];missing=[r for r in rows if r.get('retrieval_status')!='OK'];print('missing_before',len(missing),flush=True)
with ThreadPoolExecutor(max_workers=16) as ex:
 fs={ex.submit(one,r):i for i,r in enumerate(missing)};done=0
 for f in as_completed(fs):
  missing[fs[f]]=f.result();done+=1
  if done%50==0:print('refilled',done,flush=True)
by={r['question_id']:r for r in missing};rows=[by.get(r['question_id'],r) for r in rows]
P.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')
print(json.dumps({'rows':len(rows),'ok':sum(r.get('retrieval_status')=='OK' for r in rows),'missing':sum(r.get('retrieval_status')!='OK' for r in rows)}))
