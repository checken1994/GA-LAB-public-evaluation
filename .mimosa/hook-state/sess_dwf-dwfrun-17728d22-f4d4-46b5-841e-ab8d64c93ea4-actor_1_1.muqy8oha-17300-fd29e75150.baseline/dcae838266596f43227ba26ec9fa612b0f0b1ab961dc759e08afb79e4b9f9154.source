import json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];stamp='20260817_144947';audit=ROOT/'data'/f'rag_input_standardization_audit_{stamp}';audit.mkdir(parents=True,exist_ok=True)
src=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833'/'questions.jsonl';out=ROOT/'data'/'ragas_ares_canonical_1000_20260817.jsonl'
import shutil
shutil.copy2(src,audit/'questions_source.jsonl')
if out.exists():shutil.copy2(out,audit/'canonical_run_source.jsonl')
rows=[json.loads(x) for x in src.read_text(encoding='utf-8').splitlines() if x.strip()]
summary={'rows':len(rows),'ids_unique':len({x.get('id') for x in rows}),'domains':dict(collections.Counter(x.get('domain','') for x in rows)),'has_contexts':sum(bool(x.get('contexts')) for x in rows),'has_ground_truth':sum(bool(x.get('ground_truth')) for x in rows),'has_source_field':sum(any(k in x for k in ['source_url','source','sources']) for x in rows)}
(audit/'source_inventory.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
if out.exists():
 rr=[json.loads(x) for x in out.read_text(encoding='utf-8-sig').splitlines() if x.strip()];s={'rows':len(rr),'pipeline_status':dict(collections.Counter(x.get('pipeline_status') for x in rr)),'review_status':dict(collections.Counter(x.get('review_status') for x in rr)),'gold_chunk_ids':sum(bool(x.get('gold_chunk_ids')) for x in rr),'gold_answer':sum(bool(x.get('gold_answer')) for x in rr),'canonical_url':sum(bool(x.get('review_source_url')) for x in rr)};(audit/'canonical_inventory.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'audit':str(audit),'source':summary},ensure_ascii=False))
