import json,re,hashlib,datetime,concurrent.futures
from pathlib import Path
from bs4 import BeautifulSoup
import requests
from _net_guard import safe_get  # [S6b] boundary-validated egress
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'data'/'rag_canonical_fetch_results_v1_20260817.jsonl';OUT=ROOT/'data'/'rag_corpus'/'canonical-v2-20260817';OUT.mkdir(parents=True,exist_ok=True);CORP=OUT/'corpus_all_fetched.jsonl'
def load_records(p):
 s=p.read_text(encoding='utf-8');dec=json.JSONDecoder();i=0
 while i<len(s):
  while i<len(s) and s[i].isspace():i+=1
  if i>=len(s):break
  try:o,j=dec.raw_decode(s,i);yield o;i=j
  except json.JSONDecodeError:
   k=s.find('{',i+1)
   if k<0:break
   i=k
def one(r):
 u=r.get('final_url') or r.get('canonical_url');base={'question_id':r.get('question_id'),'question':r.get('question'),'source_url':u,'source_title':r.get('title',''),'fetch_status':r.get('fetch_status'),'chunks':[],'gold_status':'NO_GOLD','review_required':True}
 if r.get('fetch_status')!='FETCHED' or not u:return base
 try:
  resp=safe_get(u,timeout=25,headers={'User-Agent':'SCP-Canonical-Corpus/1.0'},allow_redirects=True,allow_internal=False)
  if not resp.ok:return base
  soup=BeautifulSoup(resp.text,'html.parser')
  for z in soup(['script','style','noscript','svg']):z.decompose()
  text=re.sub(r'\s+',' ',soup.get_text(' ',strip=True)).strip()
  if not text:return base
  did='doc-'+hashlib.sha256(resp.url.encode()).hexdigest()[:24];size=1200;chunks=[]
  for i in range(0,len(text),size):
   t=text[i:i+size];chunks.append({'chunk_id':f'{did}-c{i//size:04d}','document_id':did,'text':t,'char_start':i,'char_end':i+len(t),'content_hash':'sha256:'+hashlib.sha256(t.encode()).hexdigest()})
  base.update({'document_id':did,'final_url':resp.url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'chunks':chunks})
 except Exception as e:base['error']=type(e).__name__+': '+str(e)[:200]
 return base
rows=list(load_records(SRC))
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:out=list(ex.map(one,rows))
CORP.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf-8')
print(json.dumps({'rows':len(out),'with_chunks':sum(bool(x['chunks']) for x in out),'chunks':sum(len(x['chunks']) for x in out),'gold_created':0},ensure_ascii=False))
