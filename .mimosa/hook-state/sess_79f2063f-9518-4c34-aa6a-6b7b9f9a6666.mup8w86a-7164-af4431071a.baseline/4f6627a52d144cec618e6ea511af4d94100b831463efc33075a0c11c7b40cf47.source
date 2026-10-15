import json,re,hashlib,datetime,concurrent.futures,requests
from pathlib import Path
from _net_guard import safe_post  # [S6b] boundary-validated egress
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'data'/'rag_corpus'/'canonical-v2-20260817'/'corpus_all_fetched.jsonl';OUT=ROOT/'data'/'rag_gold_independent_review_v1_20260817.jsonl';BASE='https://11435-i6tz6ri8dbkvtipolhdxd-b4a6d624.sg1.manus.computer/api/v1';HEAD={'Authorization':'Bearer bridge-test-token','Content-Type':'application/json'}
def load_records(p):
 s=p.read_text(encoding='utf-8');d=json.JSONDecoder();i=0
 while i<len(s):
  while i<len(s) and s[i].isspace():i+=1
  if i>=len(s):break
  try:o,j=d.raw_decode(s,i);yield o;i=j
  except json.JSONDecodeError:
   k=s.find('{',i+1)
   if k<0:break
   i=k
def toks(s):return set(re.findall(r'[\wÀ-ỹ]{3,}',str(s).lower()))
def call(model,messages,schema):
 body={'model':model,'messages':messages,'max_tokens':1800,'response_format':{'type':'json_schema','json_schema':{'name':'review','strict':True,'schema':schema}}}
 r=safe_post(BASE+'/chat/completions',headers=HEAD,json=body,timeout=120,allow_internal=True);r.raise_for_status();content=r.json()['choices'][0]['message'].get('content') or '{}';return json.loads(content)
gen_schema={'type':'object','properties':{'gold_answer':{'type':'string'},'claim_count':{'type':'integer'}},'required':['gold_answer','claim_count'],'additionalProperties':False}
judge_schema={'type':'object','properties':{'decision':{'type':'string','enum':['SUPPORTED','UNSUPPORTED','INSUFFICIENT']},'supporting_chunk_ids':{'type':'array','items':{'type':'string'}},'claim_notes':{'type':'string'}},'required':['decision','supporting_chunk_ids','claim_notes'],'additionalProperties':False}
def one(x):
 q=x.get('question','');chunks=x.get('chunks') or []
 qt=toks(q);rank=[]
 for c in chunks:
  ov=len(qt&toks(c.get('text','')));rank.append((ov,c))
 rank.sort(key=lambda z:z[0],reverse=True);chosen=[c for ov,c in rank[:5] if ov>0]
 base={'question_id':x.get('question_id'),'question':q,'source_url':x.get('final_url') or x.get('source_url'),'document_id':x.get('document_id'),'candidate_chunk_ids':[c.get('chunk_id') for c in chosen],'gold_chunk_ids':[],'gold_answer':'','gold_status':'NO_GOLD','review_method':'none','review_source_urls':[],'reviewed_at':None,'judge_decision':'INSUFFICIENT','claim_notes':'','error':None}
 if not chosen:return base
 context='\n\n'.join(f"[{c['chunk_id']}] {c['text'][:1800]}" for c in chosen)
 try:
  g=call('gpt-5-mini',[{'role':'system','content':'Write a concise answer using only the supplied source chunks. Do not add unsupported facts. Output JSON only.'},{'role':'user','content':f'Question: {q}\nSource chunks:\n{context}'}],gen_schema)
  base['gold_answer']=g.get('gold_answer','').strip()
  j=call('claude-sonnet-4-6',[{'role':'system','content':'Independently judge whether every claim in the proposed answer is supported by the supplied chunks. Do not use outside knowledge. Output JSON only.'},{'role':'user','content':f'Question: {q}\nProposed answer: {base["gold_answer"]}\nSource chunks:\n{context}'}],judge_schema)
  base['judge_decision']=j.get('decision','INSUFFICIENT');base['supporting_chunk_ids']=j.get('supporting_chunk_ids',[]);base['claim_notes']=j.get('claim_notes','');base['review_method']='independent_llm_two_model';base['review_source_urls']=[base['source_url']] if base['source_url'] else [];base['reviewed_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
  if base['judge_decision']=='SUPPORTED' and base['gold_answer'] and set(base['supporting_chunk_ids']).issubset(set(base['candidate_chunk_ids'])):base['gold_chunk_ids']=base['supporting_chunk_ids'];base['gold_status']='INDEPENDENT_LLM_REVIEWED'
  else:base['gold_status']='ABSTAIN'
 except Exception as e:base['error']=type(e).__name__+': '+str(e)[:300];base['gold_status']='ABSTAIN'
 return base
rows=list(load_records(SRC));
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:out=list(ex.map(one,rows))
OUT.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf-8');from collections import Counter
print(json.dumps({'rows':len(out),'gold_reviewed':sum(x['gold_status']=='INDEPENDENT_LLM_REVIEWED' for x in out),'abstain':sum(x['gold_status']=='ABSTAIN' for x in out),'no_candidate':sum(not x['candidate_chunk_ids'] for x in out),'errors':sum(bool(x['error']) for x in out),'decisions':dict(Counter(x['judge_decision'] for x in out))},ensure_ascii=False))
