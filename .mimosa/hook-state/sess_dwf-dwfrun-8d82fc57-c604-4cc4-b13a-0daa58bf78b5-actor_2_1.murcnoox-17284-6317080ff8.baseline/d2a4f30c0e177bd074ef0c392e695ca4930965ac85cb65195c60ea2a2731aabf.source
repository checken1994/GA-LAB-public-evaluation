import json,base64,urllib.parse,html,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833'/'questions.jsonl';OUT=ROOT/'data'/'rag_normalized_source_candidates_v1_20260817.jsonl'
def resolve(url):
    u=str(url or '')
    p=urllib.parse.urlparse(u)
    qs=urllib.parse.parse_qs(p.query)
    for key in ('u','url','r'):
        if key not in qs: continue
        raw=urllib.parse.unquote(qs[key][0])
        if raw.startswith('a1'):
            try:
                raw=base64.b64decode(raw[2:]+'===').decode('utf-8','ignore')
            except Exception: pass
        if raw.startswith(('http://','https://')): return raw
    return u if u.startswith(('http://','https://')) and 'bing.com/' not in u else ''
def canonical(u):
    p=urllib.parse.urlsplit(u);return urllib.parse.urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/') or '/', '', ''))
rows=[]
for line in SRC.read_text(encoding='utf-8').splitlines():
    if not line.strip(): continue
    x=json.loads(line); contexts=x.get('contexts') or []; cands=[]
    for c in contexts:
        m=re.search(r'source_url=(\S+)',str(c)); raw=html.unescape(m.group(1).rstrip('\\n')) if m else ''
        target=resolve(raw)
        cands.append({'source_url_original':raw,'canonical_url_candidate':canonical(target) if target else '', 'chunk_id_original':re.search(r'chunk_id=([^ ]+)',str(c)).group(1) if re.search(r'chunk_id=([^ ]+)',str(c)) else '', 'text_preview':str(c)[:1000]})
    rows.append({'question_id':x.get('id'),'question':x.get('question'),'candidate_sources':cands,'normalization_status':'CANDIDATE_ONLY','review_required':True})
OUT.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8');print(json.dumps({'rows':len(rows),'source_candidates':sum(len(r['candidate_sources']) for r in rows),'resolved':sum(bool(c['canonical_url_candidate']) for r in rows for c in r['candidate_sources']),'review_required':True},ensure_ascii=False))
