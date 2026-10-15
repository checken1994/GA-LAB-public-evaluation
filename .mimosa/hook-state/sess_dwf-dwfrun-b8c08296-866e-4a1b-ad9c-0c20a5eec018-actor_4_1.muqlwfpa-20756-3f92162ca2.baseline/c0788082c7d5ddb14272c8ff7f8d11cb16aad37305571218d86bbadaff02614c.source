import json,re,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'data'/'rag_corpus'/'canonical-v1-20260817'/'corpus_1000.jsonl';OUT=ROOT/'data'/'rag_input_gold_validation_v1_20260817.jsonl';SUM=ROOT/'data'/'rag_input_gold_validation_v1_20260817.json'
def url_ok(u):return bool(re.match(r'^https?://',str(u))) and 'bing.com/ck/' not in str(u) and 'bing.com/search' not in str(u)
def hash_ok(text,h):return bool(h) and h=='sha256:'+hashlib.sha256(str(text).encode()).hexdigest()
rows=[]
for line in SRC.read_text(encoding='utf-8').splitlines():
 if not line.strip():continue
 x=json.loads(line);reasons=[];docs=x.get('documents') or [];ids=[d.get('chunk_id') for d in docs if d.get('chunk_id')];
 if not x.get('question_id') or not str(x.get('question','')).strip():reasons.append('QUESTION_EMPTY')
 if not docs:reasons.append('NO_DOCUMENT')
 for d in docs:
  if not url_ok(d.get('source_url')):reasons.append('NON_CANONICAL_URL')
  if not d.get('text','').strip():reasons.append('CHUNK_EMPTY')
  if not hash_ok(d.get('text',''),d.get('hash','')):reasons.append('HASH_INVALID')
 if x.get('answerable') and not x.get('gold_chunk_ids'):reasons.append('GOLD_CHUNK_IDS_EMPTY')
 if x.get('answerable') and not x.get('gold_answer','').strip():reasons.append('GOLD_ANSWER_EMPTY')
 if x.get('review_status') in ('HUMAN_VERIFIED','INDEPENDENT_LLM_REVIEWED') and (not x.get('review_source_url') or not x.get('gold_chunk_ids')):reasons.append('REVIEW_PROVENANCE_INCOMPLETE')
 status='FACTUAL_READY' if x.get('answerable') and not reasons and x.get('review_status') in ('HUMAN_VERIFIED','INDEPENDENT_LLM_REVIEWED') else ('VALID_SOURCE_ABSTAIN' if x.get('review_status') in ('NO_CANONICAL_SOURCE','CANDIDATE_NOT_FETCH_VERIFIED') else ('SOURCE_FETCHED_NOT_GOLD' if not reasons else 'INVALID'))
 rows.append({'question_id':x.get('question_id'),'status':status,'review_status':x.get('review_status'),'gold_chunk_ids':x.get('gold_chunk_ids',[]),'source_count':len(docs),'reasons':sorted(set(reasons))})
OUT.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8');from collections import Counter
s={'schema_version':'rag-input-gold-v1','rows':len(rows),'status':dict(Counter(r['status'] for r in rows)),'gold_chunk_id_coverage':sum(bool(r['gold_chunk_ids']) for r in rows),'factual_ready':sum(r['status']=='FACTUAL_READY' for r in rows),'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'release_verdict':'BLOCKED_UNLESS_ALL_FACTUAL_READY'};SUM.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(s,ensure_ascii=False))
