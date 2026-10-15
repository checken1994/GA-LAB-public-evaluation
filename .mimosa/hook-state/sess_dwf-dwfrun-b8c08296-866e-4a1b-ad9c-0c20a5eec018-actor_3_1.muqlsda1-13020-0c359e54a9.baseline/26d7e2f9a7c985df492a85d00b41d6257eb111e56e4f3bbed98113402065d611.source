import sys,json,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scp.rag.canonical_retriever import CanonicalRetriever
root=str(Path(__file__).resolve().parents[1]);src=root+r'\data\benchmark_batches\cc047e32d62448678a773738abe08833\questions.jsonl';r=CanonicalRetriever();out=[]
for line in open(src,encoding='utf-8'):
 if not line.strip():continue
 x=json.loads(line);hits=r.retrieve(x.get('question',''),k=5);out.append({'question_id':x.get('id'),'question':x.get('question'),'hit_count':len(hits),'hits':hits})
Path(root+r'\data\retrieval_coverage_v5_20260817.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf-8')
print(json.dumps({'rows':len(out),'with_hits':sum(x['hit_count']>0 for x in out),'no_hits':sum(x['hit_count']==0 for x in out),'hit_count_distribution':dict(collections.Counter(x['hit_count'] for x in out))},ensure_ascii=False))
