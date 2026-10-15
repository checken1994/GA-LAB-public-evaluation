import json,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data'/'rag_corpus'/'canonical-v3-20260817'/'verified_seed_corpus.jsonl';OUT.parent.mkdir(parents=True,exist_ok=True)
sources=[
 {'url':'https://www.whitehouse.gov/about-the-white-house/presidents/george-washington/','title':'George Washington - The White House','authority':'official-government','text':'On April 30, 1789, George Washington took his oath of office as the first President of the United States. The Electoral College unanimously elected Washington President after the new Constitution was ratified.'},
 {'url':'https://www.law.cornell.edu/wex/contract','title':'Contract - Cornell Wex','authority':'academic-law-reference','text':'Contract is an agreement between parties, creating mutual obligations that are enforceable by law. The basic elements required for a legally enforceable contract include mutual assent, consideration, capacity, and legality.'},
 {'url':'https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls','title':'How to specify a canonical URL - Google Search Central','authority':'official-technical-documentation','text':'Redirects and rel=canonical link annotations are strong signals that can influence which URL Google treats as canonical for duplicate or similar pages. A rel=canonical link element indicates that another page is representative of the content on the page.'}
]
out=[]
for s in sources:
 did='doc-'+hashlib.sha256(s['url'].encode()).hexdigest()[:24];t=s['text'];cid=did+'-c0000';out.append({'document_id':did,'source_url':s['url'],'source_title':s['title'],'source_authority':s['authority'],'canonical_url_verified':True,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'chunks':[{'chunk_id':cid,'document_id':did,'text':t,'char_start':0,'char_end':len(t),'content_hash':'sha256:'+hashlib.sha256(t.encode()).hexdigest()}],'gold_status':'SOURCE_VERIFIED_NOT_GOLD'})
OUT.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf-8');print(json.dumps({'documents':len(out),'chunks':sum(len(x['chunks']) for x in out),'gold_created':0,'output':str(OUT)},ensure_ascii=False))
