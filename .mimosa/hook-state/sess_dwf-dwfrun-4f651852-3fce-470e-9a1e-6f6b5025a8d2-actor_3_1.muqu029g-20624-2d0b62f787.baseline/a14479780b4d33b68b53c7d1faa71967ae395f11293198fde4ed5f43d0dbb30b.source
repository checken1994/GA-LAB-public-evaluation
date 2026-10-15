import json
from pathlib import Path
src=Path(r'D:/scp-local-agent/workspace/scp-phase1-test/reports/phase3_candidate_enrichment_pilot20.jsonl')
out=Path(r'D:/scp-local-agent/workspace/scp-phase1-test/reports/phase3_candidate_enrichment_pilot20_sanitized.jsonl')
rows=[]
with src.open(encoding='utf-8-sig') as f:
    for line in f:
        if not line.strip(): continue
        r=json.loads(line)
        p=r.get('provisional') or {}
        ids={c.get('chunk_id') for c in r.get('candidate_contexts',[])}
        cited=[x for x in (p.get('cited_candidate_chunk_ids') or []) if x in ids]
        quotes=[x for x in (p.get('evidence_quotes') or []) if isinstance(x,dict) and x.get('chunk_id') in ids]
        invalid=len(cited)!=len(p.get('cited_candidate_chunk_ids') or []) or len(quotes)!=len(p.get('evidence_quotes') or [])
        if invalid:
            p={'question_id':r.get('question_id'),'provisional_answer':'','cited_candidate_chunk_ids':[],'evidence_quotes':[],'abstain':True,'abstain_reason':'sanitizer: model cited a chunk ID not present in supplied context'}
        r['provisional_sanitized']=p
        r['citation_validation']={'context_chunk_count':len(ids),'model_citation_count':len(r.get('provisional',{}).get('cited_candidate_chunk_ids') or []),'invalid_citation_detected':invalid,'sanitizer_action':'ABSTAIN_AND_CLEAR' if invalid else 'NO_CHANGE'}
        r['candidate_only']=True;r['human_review_required']=True;r['gold_promotion']='FORBIDDEN'
        rows.append(r)
out.write_text('\n'.join(json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in rows)+'\n',encoding='utf-8')
print(json.dumps({'rows':len(rows),'invalid_citation_rows':sum(1 for r in rows if r['citation_validation']['invalid_citation_detected']),'output':str(out)}))
