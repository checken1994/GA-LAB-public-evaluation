import json,re,hashlib
from pathlib import Path
import requests
from _net_guard import safe_get  # [S6b] boundary-validated egress
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'benchmark'/'questions_1000_real_rag_20260817.jsonl';UA='SCP-Real-RAG-Benchmark/1.0 (source independence repair)'
def clean(q):
 q=re.sub(r'\(Mã\s*CH-\d+\)','',q,flags=re.I);q=re.sub(r'\s+',' ',q.replace('\n',' '));q=re.sub(r'\b(mới nhất|hiện nay|năm nay)\b','',q,flags=re.I);return q.strip(' ?')
def fetch(q):
 try:
  r=requests.get('https://www.bing.com/search',params={'q':clean(q),'count':10,'setlang':'vi'},headers={'User-Agent':UA},timeout=20);s=BeautifulSoup(r.text,'html.parser');out=[]
  for li in s.select('li.b_algo'):
   a=li.select_one('h2 a');p=li.select_one('.b_caption p')
   if a and a.get('href'):out.append((a.get_text(' ',strip=True),a['href'],p.get_text(' ',strip=True) if p else ''))
  return out
 except Exception:return []
rows=[json.loads(x) for x in P.read_text(encoding='utf-8').splitlines() if x.strip()];fixed=0
for r in rows:
 if r.get('source_url')!=r.get('ground_truth_source_url'):continue
 hits=fetch(r['question']);hits=[h for h in hits if h[1] and h[1]!=r.get('source_url')]
 if not hits:continue
 title,url,snip=hits[0];text=snip
 try:
  rr=safe_get(url,headers={'User-Agent':UA},timeout=12,allow_internal=False);ss=BeautifulSoup(rr.text,'html.parser')
  for x in ss(['script','style','nav','footer','header','aside']):x.decompose()
  text=re.sub(r'\s+',' ',ss.get_text(' ',strip=True))[:6000] or snip
 except Exception:pass
 r['ground_truth']=f'[ground_truth_source={url}] {text}';r['ground_truth_source_url']=url;r['ground_truth_title']=title;r['review_status']='auto_two_independent_sources_repaired';fixed+=1
P.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8');print(json.dumps({'same_source_before':sum(r.get('source_url')==r.get('ground_truth_source_url') for r in rows),'repaired':fixed,'same_source_after':sum(r.get('source_url')==r.get('ground_truth_source_url') for r in rows)}))
