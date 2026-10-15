import json,re,html,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833'/'questions.jsonl';
if not B.exists():B=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833'/'questions.jsonl'
OUT=ROOT/'data'/'rag_corpus'/'canonical-v1-20260817'/'candidates_multi.jsonl';UA='SCP-Canonical-Candidate-Collector/1.0'
def clean(q):
 q=re.sub(r'\(Mã\s*CH-\d+\)','',q,flags=re.I);q=q.replace('\n',' ');q=re.sub(r'\s+',' ',q);q=re.sub(r'\b(mới nhất|năm nay|hiện nay)\b','',q,flags=re.I);return q.strip(' ?')
def one(r):
 q=clean(r['question']);s=requests.Session();out=[]
 try:
  h=s.get('https://www.bing.com/search',params={'q':q,'count':10,'setlang':'vi'},headers={'User-Agent':UA},timeout=20);sp=BeautifulSoup(h.text,'html.parser')
  for li in sp.select('li.b_algo')[:8]:
   a=li.select_one('h2 a');p=li.select_one('.b_caption p')
   if not a or not a.get('href'):continue
   try:
    rr=s.get(a['href'],headers={'User-Agent':UA},timeout=15,allow_redirects=True);url=rr.url
    if 'bing.com/ck/' in url or 'bing.com/search' in url:continue
    ss=BeautifulSoup(rr.text,'html.parser');
    for x in ss(['script','style','nav','footer','header','aside']):x.decompose()
    text=re.sub(r'\s+',' ',ss.get_text(' ',strip=True))[:5000]
   except Exception:continue
   if not url.startswith(('http://','https://')):continue
   out.append({'title':a.get_text(' ',strip=True),'url':url,'snippet':p.get_text(' ',strip=True) if p else '','text':text})
 except Exception:pass
 return {'question_id':r['id'],'question':r['question'],'query':q,'candidates':out[:5],'status':'CANDIDATES_COLLECTED' if out else 'NO_CANDIDATES'}
rows=[json.loads(x) for x in B.read_text(encoding='utf-8').splitlines() if x.strip()];out=[None]*len(rows)
with ThreadPoolExecutor(max_workers=16) as ex:
 fs={ex.submit(one,r):i for i,r in enumerate(rows)};done=0
 for f in as_completed(fs):out[fs[f]]=f.result();done+=1
  
 if done%50==0:print('collected',done,flush=True)
OUT.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf-8');print(json.dumps({'rows':len(out),'with_candidates':sum(bool(x['candidates']) for x in out),'no_candidates':sum(not x['candidates'] for x in out)},ensure_ascii=False))
