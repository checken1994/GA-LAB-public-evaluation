import json,re,html,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'data'/'rag_canonical_fetch_results_v1_20260817.jsonl';OUT=ROOT/'data'/'rag_relevance_review_queue_v1_20260817.jsonl'
def load_records(p):
    s=p.read_text(encoding='utf-8');dec=json.JSONDecoder();i=0
    while i<len(s):
        while i<len(s) and s[i].isspace():i+=1
        if i>=len(s):break
        try: obj,j=dec.raw_decode(s,i);yield obj;i=j
        except json.JSONDecodeError:
            k=s.find('{',i+1)
            if k<0:break
            i=k
def toks(s):
 s=unicodedata.normalize('NFKC',str(s).lower());return set(re.findall(r'[\wÀ-ỹ]{3,}',s,flags=re.UNICODE))
def clean(s):
 s=re.sub(r'<script.*?</script>|<style.*?</style>',' ',s,flags=re.I|re.S);s=re.sub(r'<[^>]+>',' ',s);return html.unescape(re.sub(r'\s+',' ',s))
rows=[]
for x in load_records(SRC):
 q=toks(x.get('question'));txt=toks(clean(x.get('text_preview','')));over=sorted(q&txt);score=len(over)/max(1,len(q));status='REVIEW_REQUIRED' if x.get('fetch_status')=='FETCHED' and score>=0.15 else 'REJECT_CANDIDATE'
 rows.append({'question_id':x.get('question_id'),'question':x.get('question'),'canonical_url':x.get('final_url') or x.get('canonical_url'),'source_title':x.get('title'),'fetch_status':x.get('fetch_status'),'lexical_overlap_score':round(score,4),'matched_terms':over[:30],'relevance_status':status,'gold_status':'NO_GOLD','review_required':True})
OUT.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8');from collections import Counter
print(json.dumps({'rows':len(rows),'status':dict(Counter(r['relevance_status'] for r in rows)),'gold_created':0},ensure_ascii=False))
