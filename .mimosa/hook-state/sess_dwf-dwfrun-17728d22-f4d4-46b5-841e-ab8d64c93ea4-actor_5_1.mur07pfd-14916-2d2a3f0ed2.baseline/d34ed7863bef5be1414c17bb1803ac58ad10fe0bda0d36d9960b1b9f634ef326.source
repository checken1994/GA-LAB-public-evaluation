from __future__ import annotations

import json
import logging
import math
import re
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TOKEN_RE=re.compile(r'[\wÀ-ỹ]{3,}',re.UNICODE)
_STOP=set('the a an and or of to in on for from is are was were be been being what who when where why how which with that this these those do does did as by at it its their his her our your into about between general terms answer briefly source available explain give say if evidence missing main function difference signal'.split())
_GENERIC={('united','states'),('new','york'),('world','war'),('president','united')}
def _tokens(s:str)->list[str]:
 out=[]
 for x in _TOKEN_RE.findall(str(s).lower()):
  if x in _STOP:continue
  if x.endswith('ly') and len(x)>5:x=x[:-2]
  if x.endswith('s') and len(x)>5:x=x[:-1]
  out.append(x)
 return out
def _records(path:Path):
 s=path.read_text(encoding='utf-8')
 d=json.JSONDecoder()
 i=0
 while i<len(s):
  while i<len(s) and s[i].isspace():i+=1
  if i>=len(s):break
  # [hygiene E702] câu ghép một dòng `try: a; b; c` — giữ nguyên vì tách dòng
  # sẽ phải re-indent toàn bộ thân try (rủi ro > lợi ích với cùng ngữ nghĩa).
  try:o,j=d.raw_decode(s,i);yield o;i=j  # noqa: E702
  except json.JSONDecodeError:
   logger.debug('_records: json.JSONDecodeError ignored', exc_info=True)
   k=s.find('{',i+1)
   if k<0:break
   i=k
class CanonicalRetriever:
 def __init__(self,root:Path|None=None):
  self.root=root or Path(__file__).resolve().parents[2]
  self.paths=[self.root/'data'/'rag_corpus'/'canonical-v2-20260817'/'corpus_all_fetched.jsonl',self.root/'data'/'rag_corpus'/'canonical-v3-20260817'/'verified_seed_corpus.jsonl']
  self._lock=threading.Lock()
  self._loaded=False
  self.available=True
  self.items=[]
  self.df={}
  self.postings={}
 def _load(self):
  if self._loaded:return
  with self._lock:
   if self._loaded:return
   loaded_files=0
   for path in self.paths:
    if not path.exists():
     logger.warning("[R4-F04] Canonical RAG corpus file not found: %s", path)
     continue
    loaded_files+=1
    for doc in _records(path):
     url=doc.get('final_url') or doc.get('source_url') or ''
     title=str(doc.get('source_title') or '')
     if (not str(url).startswith(('http://','https://')) or 'bing.com/' in str(url) or any(bad in str(url).lower() for bad in ('mangatown.com','free-work.com','xhamster.com','pornhub.com'))):continue
     for c in doc.get('chunks') or []:
      text=str(c.get('text') or '').strip()
      terms=set(_tokens(text))
      norm=' '.join(_tokens(text))
      title_terms=set(_tokens(title))
      if text and terms:
       idx=len(self.items)
       self.items.append({'chunk_id':c.get('chunk_id'),'document_id':c.get('document_id'),'source_url':url,'source_title':title,'text':text,'terms':terms,'norm':norm,'title_terms':title_terms})
       for t in terms:self.postings.setdefault(t,set()).add(idx)
   for t,ids in self.postings.items():self.df[t]=len(ids)
   if loaded_files==0 or len(self.items)==0:
    logger.warning("[R4-F04] CanonicalRetriever: No RAG corpus found on disk. Transparent fallback to DomainKnowledge active.")
    self.available=False
   else:
    self.available=True
   self._loaded=True
 def retrieve(self,question:str,k:int=5)->list[dict[str,Any]]:
  self._load()
  if len(self.items)==0:
   try:
    from scp.knowledge.domain_knowledge import DomainKnowledge
    dk=DomainKnowledge()
    hits=dk.search(question,limit=k)
    if hits:
     logger.info("[R4-F04] CanonicalRetriever fallback served %d hits from DomainKnowledge", len(hits))
     # [R4-F04-DICT-FIX] DomainKnowledge.search trả về list[dict] (keys:
     # question/answer/source_url/...), không phải objects — getattr(h,...)
     # luôn trả default rỗng → fallback phục vụ chunk text rỗng với score 1.0
     # nhưng vẫn log "served N hits" (sai sự thật). Đọc bằng dict access.
     return [{
      'chunk_id':f"kb_{h.get('id', i)}",
      'document_id':f"kb_doc_{h.get('id', i)}",
      'source_url':h.get('source_url','') or '',
      'source_title':h.get('question','') or '',
      'text':h.get('answer','') or '',
      'score':1.0,
     } for i,h in enumerate(hits)]
   except Exception as exc:
    logger.debug("[R4-F04] Transparent fallback to DomainKnowledge failed: %s", exc)
   return []
  qt=_tokens(question)
  qset=set(qt)
  q_bigrams=set(zip(qt,qt[1:]))
  if not qset:return []
  candidates=set()
  for t in qset:candidates.update(self.postings.get(t,set()))
  scored=[]
  for idx in candidates:
   item=self.items[idx]
   item_tokens=item['norm'].split()
   overlap=qset&item['terms']
   n=len(overlap)
   coverage=n/max(1,len(qset))
   matched=q_bigrams&set(zip(item_tokens,item_tokens[1:]))
   distinctive={p for p in matched if p not in _GENERIC}
   title_match=qset&item['title_terms']
   if len(qset)==1:
    term=next(iter(qset))
    if term not in item['title_terms'] and not item['norm'].startswith(term):continue
   else:
    if not distinctive and not (coverage==1.0 and len(qset)<=2):continue
    if distinctive and coverage<0.75:continue
   idf=sum(math.log((1+len(self.items))/(1+self.df.get(t,1))) for t in overlap)
   score=idf*coverage+4*len(distinctive)+len(title_match)
   scored.append((score,coverage,n,len(distinctive),item))
  scored.sort(key=lambda x:(x[0],x[1],x[2],x[3]),reverse=True)
  out=[]
  seen=set()
  for score,cov,_n,mb,item in scored:  # [hygiene B007] n không dùng trong thân vòng lặp
   if item['document_id'] in seen:continue
   seen.add(item['document_id'])
   out.append({key:value for key,value in item.items() if key not in ('terms','norm','title_terms')}|{'retrieval_score':round(score,4),'term_coverage':round(cov,4),'matched_bigrams':mb})
   if len(out)>=max(1,min(k,8)):break
  return out
 def contexts(self,question:str,k:int=5):return [f"[chunk_id={x['chunk_id']}] source_url={x['source_url']}\n{x['text']}" for x in self.retrieve(question,k)]


class HybridRetriever(CanonicalRetriever):
 """HybridRetriever compatibility wrapper over CanonicalRetriever."""

 def search(self,query:str,top_k:int=3)->list[dict[str,Any]]:
  """Bridge search() API expected by v105_routes to canonical retrieve()."""
  return self.retrieve(question=query,k=top_k)


_default=None
def get_canonical_retriever():
 global _default
 if _default is None:_default=CanonicalRetriever()
 return _default

__all__ = ["CanonicalRetriever", "HybridRetriever", "get_canonical_retriever", "_tokens"]

