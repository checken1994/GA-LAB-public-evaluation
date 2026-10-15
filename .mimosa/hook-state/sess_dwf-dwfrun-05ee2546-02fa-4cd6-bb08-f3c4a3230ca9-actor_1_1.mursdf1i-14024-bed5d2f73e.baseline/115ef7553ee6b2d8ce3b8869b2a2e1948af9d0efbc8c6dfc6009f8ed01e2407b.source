import json,re,math,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];C=ROOT/'data'/'rag_corpus'/'v20260817';B=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833';OUT=ROOT/'data'/'rag_retrieval_eval_20260817.jsonl';SUM=ROOT/'data'/'rag_retrieval_eval_20260817.json'
def tok(s):return set(re.findall(r'[\wÀ-ỹ]{3,}',str(s).lower()))
chunks=[json.loads(x) for x in (C/'chunks.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]; qs=[json.loads(x) for x in (B/'questions.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]; gold={x['question_id']:set(x['gold_chunk_ids']) for x in (C/'gold_retrieval_annotations.jsonl').read_text(encoding='utf-8').splitlines() if x.strip() for x in [json.loads(x)]}
df=collections.Counter();ct=[]
for c in chunks:
 t=tok(c['text']);ct.append(t)
 for w in t:df[w]+=1
N=len(chunks);rows=[]
for q in qs:
 qt=tok(q['question']);scores=[]
 for i,c in enumerate(chunks):
  overlap=qt & ct[i]
  score=sum(math.log((N+1)/(df[w]+1)) for w in overlap)
  scores.append((score,i))
 scores.sort(reverse=True);ranked=[chunks[i]['chunk_id'] for score,i in scores[:10]];g=gold.get(q['id'],set());hit=[x for x in ranked if x in g]
 rr=(1/(ranked.index(hit[0])+1)) if hit else 0
 rec={k:float(bool(set(ranked[:k])&g)) for k in (1,3,5,10)}
 dcg=sum((1/math.log2(i+2)) for i,x in enumerate(ranked) if x in g);ideal=sum((1/math.log2(i+2)) for i in range(min(len(g),10))) or 1
 rows.append({'question_id':q['id'],'retrieved_chunk_ids_at_10':ranked,'gold_chunk_ids':sorted(g),'metrics':{'recall_at_1':rec[1],'recall_at_3':rec[3],'recall_at_5':rec[5],'recall_at_10':rec[10],'mrr':rr,'ndcg_at_10':dcg/ideal},'gold_status':'AUTO_SOURCE_LINK_NOT_HUMAN_VERIFIED'})
OUT.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf-8');summary={'rows':len(rows),'gold_status':'AUTO_SOURCE_LINK_NOT_HUMAN_VERIFIED','recall_at_1':sum(x['metrics']['recall_at_1'] for x in rows)/len(rows),'recall_at_5':sum(x['metrics']['recall_at_5'] for x in rows)/len(rows),'recall_at_10':sum(x['metrics']['recall_at_10'] for x in rows)/len(rows),'mrr':sum(x['metrics']['mrr'] for x in rows)/len(rows),'ndcg_at_10':sum(x['metrics']['ndcg_at_10'] for x in rows)/len(rows),'verdict':'BASELINE_ONLY_NOT_FACTUAL_PROOF'};SUM.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
