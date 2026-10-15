import json,re,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833';OUT=ROOT/'data'/'rag_corpus'/'v20260817';OUT.mkdir(parents=True,exist_ok=True)
qs=[json.loads(x) for x in (B/'questions.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
chunks=[];docs={};gold=[]
for q in qs:
 for i,raw in enumerate(q.get('contexts') or []):
  raw=str(raw);m=re.search(r'chunk_id=([^\]\s]+)',raw);cid=m.group(1) if m else f"{q['id']}-chunk-{i+1}"
  mu=re.search(r'source_url=(https?://[^\s]+)',raw);url=mu.group(1) if mu else ''
  mt=re.search(r'source_title=(.*?)\s+source_url=',raw);title=mt.group(1).strip() if mt else q['id']
  text=raw.split('\n',1)[1] if '\n' in raw else raw
  did='doc-'+hashlib.sha256(url.encode()).hexdigest()[:16] if url else 'doc-'+cid
  h='sha256:'+hashlib.sha256(text.encode()).hexdigest()
  chunks.append({'chunk_id':cid,'document_id':did,'text':text,'source_url':url,'source_title':title,'source_date':'2026-08-17','hash':h,'origin_question_id':q['id']})
  docs[did]={'document_id':did,'source_url':url,'source_title':title,'source_date':'2026-08-17'}
  if i==0:gold.append({'question_id':q['id'],'gold_chunk_ids':[cid],'gold_status':'AUTO_SOURCE_LINK_NOT_HUMAN_VERIFIED','gold_source_url':q.get('source_url','')})
  break
(OUT/'chunks.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in chunks)+'\n',encoding='utf-8')
(OUT/'documents.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in docs.values())+'\n',encoding='utf-8')
(OUT/'gold_retrieval_annotations.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in gold)+'\n',encoding='utf-8')
manifest={'corpus_version':'v20260817','created_at':'2026-08-17','documents':len(docs),'chunks':len(chunks),'gold_annotations':len(gold),'gold_annotation_status':'NOT_HUMAN_VERIFIED','hash_algorithm':'sha256','files':{}}
for p in (OUT/'chunks.jsonl',OUT/'documents.jsonl',OUT/'gold_retrieval_annotations.jsonl'):
 manifest['files'][p.name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(manifest,ensure_ascii=False))
