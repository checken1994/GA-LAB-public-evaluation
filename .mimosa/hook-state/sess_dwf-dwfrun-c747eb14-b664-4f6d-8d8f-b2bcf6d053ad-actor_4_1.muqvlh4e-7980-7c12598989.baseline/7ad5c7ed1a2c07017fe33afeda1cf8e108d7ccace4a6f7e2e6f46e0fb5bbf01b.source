import json,re,time,hashlib,html,urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833'/'questions.jsonl';OUT=ROOT/'data'/'rag_corpus'/'canonical-v1-20260817';OUT.mkdir(parents=True,exist_ok=True);UA='SCP-Canonical-RAG-Rebuilder/1.0'

def clean(q):
 q=re.sub(r'\(Mã\s*CH-\d+\)','',q,flags=re.I);q=q.replace('\n',' ');q=re.sub(r'\s+',' ',q);q=re.sub(r'\b(mới nhất|năm nay|hiện nay)\b','',q,flags=re.I);q=re.sub(r'^(Thông tin|Tra cứu thông tin|Hướng dẫn|Phân tích|Cách|Các|Một số)\s*[:：]?\s*','',q,flags=re.I);return q.strip(' ?')
def terms(s):return set(re.findall(r'[\wÀ-ỹ]{4,}',str(s).lower()))
def wiki(s,q):
 for lang in ('vi','en'):
  for qq in [q,' '.join(list(terms(q))[:8])]:
   try:
    d=s.get(f'https://{lang}.wikipedia.org/w/api.php',params={'action':'query','list':'search','srsearch':qq,'srlimit':8,'format':'json','utf8':1},headers={'User-Agent':UA},timeout=12).json()
    for hit in d.get('query',{}).get('search',[]):
     title=hit.get('title','');
     if not title:continue
     p=s.get(f'https://{lang}.wikipedia.org/w/api.php',params={'action':'query','prop':'extracts|info','explaintext':1,'inprop':'url','titles':title,'format':'json','utf8':1},headers={'User-Agent':UA},timeout=12).json();page=next(iter(p.get('query',{}).get('pages',{}).values()),{});text=(page.get('extract') or '').strip();url=page.get('fullurl','')
     rel=len(terms(q)&terms(title+' '+text[:4000]))/max(1,len(terms(q)))
     if text and url and rel>=0.08:return {'title':title,'url':url,'text':text[:9000],'relevance':round(rel,4),'provider':'wikipedia'}
   except Exception:pass
 return None
def bing(s,q):
 try:
  h=s.get('https://www.bing.com/search',params={'q':q,'count':8,'setlang':'vi'},headers={'User-Agent':UA},timeout=15);soup=BeautifulSoup(h.text,'html.parser')
  cand=[]
  for li in soup.select('li.b_algo'):
   a=li.select_one('h2 a');p=li.select_one('.b_caption p')
   if not a or not a.get('href'):continue
   url=a['href'];title=a.get_text(' ',strip=True);snip=p.get_text(' ',strip=True) if p else ''
   try:
    rr=s.get(url,headers={'User-Agent':UA},timeout=12,allow_redirects=True);final=rr.url
    if 'bing.com/ck/' in final or 'bing.com/search' in final:continue
    ss=BeautifulSoup(rr.text,'html.parser');
    for x in ss(['script','style','nav','footer','header','aside']):x.decompose()
    text=re.sub(r'\s+',' ',ss.get_text(' ',strip=True))[:9000]
   except Exception:final=url;text=snip
   rel=len(terms(q)&terms(title+' '+text[:5000]))/max(1,len(terms(q)))
   cand.append({'title':title,'url':final,'text':text,'relevance':round(rel,4),'provider':'bing_canonical'})
  cand.sort(key=lambda x:(x['relevance'],len(x['text'])),reverse=True)
  return cand[0] if cand and cand[0]['relevance']>=0.10 else None
 except Exception:return None
def one(row):
 q=clean(row['question']);s=requests.Session();doc=wiki(s,q) or bing(s,q);base={'question_id':row['id'],'question':row['question'],'query_clean':q,'source_date':'2026-08-17','corpus_version':'canonical-v1-20260817'}
 if not doc:
  base.update({'status':'NO_CANONICAL_SOURCE','answerable':False,'document_id':'','chunk_id':'','source_url':'','source_title':'','text':'','hash':'','relevance':0,'provider':''});return base
 did='doc-'+hashlib.sha256(doc['url'].encode()).hexdigest()[:16];cid=did+'-chunk-001';h='sha256:'+hashlib.sha256(doc['text'].encode()).hexdigest();base.update({'status':'CANDIDATE_CANONICAL','answerable':True,'document_id':did,'chunk_id':cid,'source_url':doc['url'],'source_title':doc['title'],'text':doc['text'],'hash':h,'relevance':doc['relevance'],'provider':doc['provider']});return base
rows=[json.loads(x) for x in B.read_text(encoding='utf-8').splitlines() if x.strip()];out=[None]*len(rows)
with ThreadPoolExecutor(max_workers=12) as ex:
 fs={ex.submit(one,r):i for i,r in enumerate(rows)};done=0
 for f in as_completed(fs):out[fs[f]]=f.result();done+=1
 if done%50==0:print('rebuilt',done,flush=True)
(OUT/'candidates.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf-8');print(json.dumps({'rows':len(out),'candidate':sum(x['status']=='CANDIDATE_CANONICAL' for x in out),'no_source':sum(x['status']!='CANDIDATE_CANONICAL' for x in out),'wikipedia':sum(x.get('provider')=='wikipedia' for x in out),'bing_canonical':sum(x.get('provider')=='bing_canonical' for x in out),'low_relevance':sum(x.get('relevance',0)<0.10 for x in out)},ensure_ascii=False))
