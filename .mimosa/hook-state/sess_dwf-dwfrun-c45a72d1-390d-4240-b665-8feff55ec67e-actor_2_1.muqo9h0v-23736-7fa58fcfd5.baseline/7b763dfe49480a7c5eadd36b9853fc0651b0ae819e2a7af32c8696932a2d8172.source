import json,re
from pathlib import Path
P=Path(str(Path(__file__).resolve().parents[1] / "benchmark" / "questions_1000_real_rag_20260817.jsonl"))
rows=[json.loads(x) for x in P.read_text(encoding='utf-8').splitlines() if x.strip()]
for r in rows:
    raw=str(r.get('ground_truth',''))
    m=re.match(r'\[ground_truth_source=([^\]]+)\]\s*(.*)',raw,re.S)
    if not m: continue
    url,text=m.group(1),m.group(2)
    qterms=set(re.findall(r'[\wÀ-ỹ]{4,}',str(r.get('question','')).lower()))
    sentences=[s.strip() for s in re.split(r'(?<=[.!?])\s+',re.sub(r'\s+',' ',text)) if s.strip()]
    scored=[]
    for i,s in enumerate(sentences):
        terms=set(re.findall(r'[\wÀ-ỹ]{4,}',s.lower()))
        scored.append((len(qterms & terms),-i,s))
    scored.sort(reverse=True)
    chosen=[x[2] for x in scored[:3]]
    r['ground_truth']=f'[ground_truth_source={url}] ' + ' '.join(chosen)[:3000]
    r['review_status']='auto_two_independent_sources_relevance_filtered'
P.with_name(P.stem+'_before_gt_refine.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')
P.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')
print('refined',len(rows))
