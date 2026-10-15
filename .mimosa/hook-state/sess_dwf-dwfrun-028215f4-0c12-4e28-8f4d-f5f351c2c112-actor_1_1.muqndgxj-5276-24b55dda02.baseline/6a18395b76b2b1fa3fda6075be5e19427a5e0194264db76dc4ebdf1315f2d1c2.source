import json,re,html,hashlib,datetime,concurrent.futures,sys,urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scp.security.url_safety import safe_urlopen
SRC=ROOT/'data'/'rag_relevance_review_queue_v1_20260817.jsonl';OUT=ROOT/'data'/'rag_corpus'/'canonical-v2-20260817';OUT.mkdir(parents=True,exist_ok=True);CORP=OUT/'corpus_review_candidates.jsonl'
def one(r):
 u=r.get('canonical_url','');base={'question_id':r.get('question_id'),'question':r.get('question'),'source_url':u,'source_title':r.get('source_title',''),'fetch_status':r.get('fetch_status'),'chunks':[],'gold_status':'NO_GOLD','review_required':True}
 if r.get('relevance_status')!='REVIEW_REQUIRED' or not u:return base
 try:
  # [SEC-S6] SSRF guard: corpus URLs are fetched through safe_urlopen.
  req=urllib.request.Request(u,headers={'User-Agent':'SCP-Canonical-Corpus/1.0'})
  with safe_urlopen(req,timeout=25) as resp:
   final_url=str(resp.url);ok=int(resp.status)<400;page=resp.read().decode('utf-8','replace') if ok else ''
  base['final_url']=final_url
  if not ok:return base
  soup=BeautifulSoup(page,'html.parser')
  for z in soup(['script','style','noscript','svg']):z.decompose()
  text=re.sub(r'\s+',' ',soup.get_text(' ',strip=True)).strip()
  if not text:return base
  did='doc-'+hashlib.sha256(resp.url.encode()).hexdigest()[:24];size=1200;chunks=[]
  for i in range(0,len(text),size):
   t=text[i:i+size];chunks.append({'chunk_id':f'{did}-c{i//size:04d}','document_id':did,'text':t,'char_start':i,'char_end':i+len(t),'content_hash':'sha256:'+hashlib.sha256(t.encode()).hexdigest()})
  base.update({'document_id':did,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'chunks':chunks})
 except Exception as e:base['error']=type(e).__name__+': '+str(e)[:200]
 return base
rows=[json.loads(x) for x in SRC.read_text(encoding='utf-8').splitlines() if x.strip()]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:out=list(ex.map(one,rows))
CORP.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf-8');print(json.dumps({'rows':len(out),'with_chunks':sum(bool(x['chunks']) for x in out),'chunks':sum(len(x['chunks']) for x in out),'gold_created':0},ensure_ascii=False))
