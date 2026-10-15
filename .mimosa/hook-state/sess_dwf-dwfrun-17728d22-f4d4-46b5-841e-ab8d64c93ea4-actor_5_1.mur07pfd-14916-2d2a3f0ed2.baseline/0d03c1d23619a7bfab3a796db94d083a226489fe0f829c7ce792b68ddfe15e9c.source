import json,re,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833'/'questions.jsonl';OUT=ROOT/'data'/'rag_corpus_quality_gate_20260817.jsonl';
def tok(s):return set(re.findall(r'[\wÀ-ỹ]{4,}',str(s).lower()))
def qclean(q):
 q=re.sub(r'\(Mã\s*CH-\d+\)','',q,flags=re.I);q=re.sub(r'\b(mới nhất|năm nay|hiện nay)\b','',q,flags=re.I);return q
rows=[]
for line in P.read_text(encoding='utf-8').splitlines():
 if not line.strip():continue
 r=json.loads(line);ctxs=r.get('contexts') or [];text=' '.join(map(str,ctxs));terms=tok(qclean(r['question']));ct=tok(text);overlap=len(terms&ct)/max(1,len(terms));urls=re.findall(r'https?://[^\s\]]+',text);bing=any('bing.com/ck/' in u for u in urls);canonical=bool(urls) and not bing;title=re.search(r'source_title=(.*?)\s+source_url=',text);title_overlap=len(terms&tok(title.group(1) if title else ''))/max(1,len(terms));status='PASS_STRUCTURAL' if canonical and overlap>=0.08 and title_overlap>=0.03 else 'REJECT_CORPUS_ITEM'
 rows.append({'question_id':r['id'],'context_term_overlap':round(overlap,4),'title_term_overlap':round(title_overlap,4),'canonical_url':canonical,'bing_redirect':bing,'status':status,'reasons':[] if status=='PASS_STRUCTURAL' else ['low_question_context_overlap' if overlap<0.08 else '', 'low_question_title_overlap' if title_overlap<0.03 else '', 'noncanonical_bing_redirect' if bing else '']})
OUT.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf-8');print(json.dumps({'rows':len(rows),'pass':sum(x['status']=='PASS_STRUCTURAL' for x in rows),'reject':sum(x['status']=='REJECT_CORPUS_ITEM' for x in rows),'bing_redirect':sum(x['bing_redirect'] for x in rows)},ensure_ascii=False))
