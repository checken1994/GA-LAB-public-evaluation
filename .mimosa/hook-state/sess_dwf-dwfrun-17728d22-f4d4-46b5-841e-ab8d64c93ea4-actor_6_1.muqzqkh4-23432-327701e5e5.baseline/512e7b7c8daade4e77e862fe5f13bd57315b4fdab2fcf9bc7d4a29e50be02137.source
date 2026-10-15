import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scp.rag.canonical_retriever import CanonicalRetriever
r=CanonicalRetriever()
print({'path':str(r.path),'items_before':len(r.items)})
xs=r.retrieve('Who was the first president of the United States?',k=8)
print(json.dumps(xs,ensure_ascii=False,indent=2)[:12000])
