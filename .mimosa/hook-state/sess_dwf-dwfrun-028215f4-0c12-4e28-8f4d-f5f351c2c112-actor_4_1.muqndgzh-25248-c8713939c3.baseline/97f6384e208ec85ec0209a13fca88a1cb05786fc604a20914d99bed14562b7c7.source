import json,datetime,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'data'/'rag_corpus'/'canonical-v1-20260817'/'corpus_1000.jsonl';OUT=ROOT/'data'/'rag_gold_review_queue_v1_20260817.jsonl'
def is_canonical(u):return str(u).startswith(('http://','https://')) and 'bing.com/' not in str(u)
rows=[]
for line in SRC.read_text(encoding='utf-8').splitlines():
 if not line.strip():continue
 x=json.loads(line);docs=x.get('documents') or [];cand=[]
 for d in docs:
  text=d.get('text','');url=d.get('source_url','')
  if text.strip() and is_canonical(url):cand.append({'chunk_id':d.get('chunk_id'),'document_id':d.get('document_id'),'source_url':url,'source_title':d.get('source_title'),'text':text,'content_hash':d.get('hash')})
 rows.append({'question_id':x.get('question_id'),'question':x.get('question'),'domain':x.get('domain','general'),'candidate_chunks':cand,'gold_chunk_ids':[],'gold_answer':'','gold_status':'NO_GOLD' if not cand else 'SOURCE_FETCHED_NOT_REVIEWED','review_method':'none','review_source_urls':[],'reviewed_at':None,'reviewer_notes':'Human or independent judge must select only directly supporting chunks; no keyword-only acceptance.'})
OUT.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8');print(json.dumps({'rows':len(rows),'with_candidates':sum(bool(r['candidate_chunks']) for r in rows),'without_candidates':sum(not r['candidate_chunks'] for r in rows),'output':str(OUT)},ensure_ascii=False))
