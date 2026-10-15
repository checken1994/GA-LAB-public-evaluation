import json,re,hashlib,time,html
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import requests
from _net_guard import safe_get  # [S6b] boundary-validated egress
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'benchmark'/'questions_1000_real_rag_20260817.jsonl';UA='SCP-Real-RAG-Benchmark/1.0 (Bing fallback)'

def qclean(q):
 q=re.sub(r'\(Mã\s*CH-\d+\)','',q,flags=re.I);q=q.replace('\n',' ');q=re.sub(r'\s+',' ',q);q=re.sub(r'\b(mới nhất|hiện nay|năm nay)\b','',q,flags=re.I);q=re.sub(r'^(Thông tin|Tra cứu thông tin|Hướng dẫn|Phân tích|Cách|Các|Một số)\s*[:：]?\s*','',q,flags=re.I);return q.strip(' ?')

def bing(q):
 try:
  r=requests.get('https://www.bing.com/search',params={'q':q,'count':5,'setlang':'vi'},headers={'User-Agent':UA},timeout=15);s=BeautifulSoup(r.text,'html.parser');out=[]
  for li in s.select('li.b_algo'):
   a=li.select_one('h2 a');p=li.select_one('.b_caption p')
   if a and a.get('href'):out.append({'title':a.get_text(' ',strip=True),'url':a['href'],'snippet':p.get_text(' ',strip=True) if p else ''})
  return out
 except Exception:return []

def page_doc(item):
 try:
  r=safe_get(item['url'],headers={'User-Agent':UA},timeout=12,allow_internal=False);s=BeautifulSoup(r.text,'html.parser')
  for x in s(['script','style','nav','footer','header','aside']):x.decompose()
  text=re.sub(r'\s+',' ',s.get_text(' ',strip=True))
  return text[:12000] if len(text)>120 else item['snippet']
 except Exception:return item['snippet']

def one(r):
 hits=bing(qclean(r['question']))
 if not hits:return r
 docs=[]
 for h in hits[:3]:
  text=page_doc(h); 
  if text:docs.append((h,text))
 if not docs:return r
 p=docs[0];g=docs[1] if len(docs)>1 else docs[0]; ch=hashlib.sha256((p[0]['url']+p[1]).encode()).hexdigest()[:16]
 r.update({'contexts':[f"[chunk_id=bing-{ch}] source_title={p[0]['title']} source_url={p[0]['url']}\n{p[1]}"],'ground_truth':f"[ground_truth_source={g[0]['url']}] {g[1][:6000]}",'source_url':p[0]['url'],'ground_truth_source_url':g[0]['url'],'source_title':p[0]['title'],'ground_truth_title':g[0]['title'],'retrieval_status':'OK','review_status':'auto_bing_two_document_review'});return r
rows=[json.loads(x) for x in P.read_text(encoding='utf-8').splitlines() if x.strip()];missing=[r for r in rows if r.get('retrieval_status')!='OK'];print('missing_before',len(missing),flush=True)
with ThreadPoolExecutor(max_workers=12) as ex:
 fs={ex.submit(one,r):i for i,r in enumerate(missing)};done=0
 for f in as_completed(fs):
  missing[fs[f]]=f.result();done+=1
  if done%50==0:print('bing_refilled',done,flush=True)
by={r['question_id']:r for r in missing};rows=[by.get(r['question_id'],r) for r in rows];P.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8');print(json.dumps({'rows':len(rows),'ok':sum(r.get('retrieval_status')=='OK' for r in rows),'missing':sum(r.get('retrieval_status')!='OK' for r in rows)}))
