import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'data'/'benchmark_batches'/'cc047e32d62448678a773738abe08833'/'questions.jsonl';C=ROOT/'data'/'rag_corpus'/'canonical-v1-20260817';OUT=C/'corpus_1000.jsonl';
rows=[json.loads(x) for x in B.read_text(encoding='utf-8').splitlines() if x.strip()];cand={}
cp=C/'candidates.jsonl'
if cp.exists():
 for x in cp.read_text(encoding='utf-8').splitlines():
  if x.strip():z=json.loads(x);cand[z['question_id']]=z
verified={
 'CH-0001':{'url':'https://congan.hungyen.gov.vn/deepfake-gia-nhuat-lam-sao-de-tranh-bay-luao-c218065.html','title':'Deepfake giả như thật, làm sao để tránh bẫy lừa đảo','text':'Deepfake có thể làm giả âm thanh, hình ảnh và video. Dấu hiệu nhận biết gồm chất lượng hình ảnh thấp, rung mờ, thời lượng ngắn; cử chỉ mắt không tự nhiên; màu da và ánh sáng bất thường; chuyển động giật; khuôn mặt thiếu cân đối; khẩu hình không tự nhiên. Cần xác minh bằng cách gọi điện thoại trực tiếp qua SIM, không chỉ gọi qua Zalo hoặc Facebook trước khi chuyển tiền.','gold_answer':'Có thể nghi ngờ deepfake khi video rung/mờ, ngắn, mắt và khẩu hình không tự nhiên, màu da/ánh sáng bất thường, chuyển động giật hoặc khuôn mặt thiếu cân đối. Cần xác minh bằng cuộc gọi trực tiếp qua SIM và không chuyển tiền chỉ dựa vào video call mạng xã hội.'},
 'CH-0002':{'url':'https://thitruongtaichinhtiente.vn/dieu-hanh-chinh-sach-tien-te-theo-lai-suat-mo-hinh-xac-dinh-lai-suat-dieu-hanh-tai-viet-nam-44182.html','title':'Điều hành chính sách tiền tệ theo lãi suất mô hình xác định lãi suất điều hành tại Việt Nam','text':'Lãi suất điều hành là lãi suất ngắn hạn chủ đạo do cơ quan quản lý tiền tệ đặt ra để tác động đến các biến số như giá tiêu dùng, tỷ giá và tín dụng. Ngân hàng Nhà nước sử dụng lãi suất điều hành và các công cụ chính sách tiền tệ để tác động đến các lãi suất khác trên thị trường.','gold_answer':'Ngân hàng Nhà nước điều hành chính sách tiền tệ bằng các công cụ, trong đó lãi suất điều hành là lãi suất ngắn hạn chủ đạo dùng để tác động đến lạm phát, tỷ giá, tín dụng và các lãi suất khác trên thị trường.'}}
out=[]
for q in rows:
 z={'question_id':q['id'],'question':q['question'],'corpus_version':'canonical-v1-20260817','source_date':'2026-08-17','gold_chunk_ids':[],'gold_answer':'','answerable':False,'review_status':'NO_CANONICAL_SOURCE','review_source_url':'','reviewed_at':'','documents':[]}
 if q['id'] in verified:
  v=verified[q['id']];did='doc-'+hashlib.sha256(v['url'].encode()).hexdigest()[:16];cid=did+'-chunk-001';z.update({'gold_chunk_ids':[cid],'gold_answer':v['gold_answer'],'answerable':True,'review_status':'INDEPENDENT_SOURCE_FETCHED_NOT_HUMAN_REVIEWED','review_source_url':v['url'],'documents':[{'document_id':did,'chunk_id':cid,'source_url':v['url'],'source_title':v['title'],'source_date':'2026-08-17','text':v['text'],'hash':'sha256:'+hashlib.sha256(v['text'].encode()).hexdigest()}]})
 elif q['id'] in cand and cand[q['id']].get('status')=='CANDIDATE_CANONICAL':
  c=cand[q['id']];z.update({'review_status':'CANDIDATE_NOT_FETCH_VERIFIED','documents':[{'document_id':c.get('document_id',''),'chunk_id':c.get('chunk_id',''),'source_url':c.get('source_url',''),'source_title':c.get('source_title',''),'source_date':c.get('source_date',''),'text':c.get('text',''),'hash':c.get('hash','')} ]})
 out.append(z)
OUT.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf-8');print(json.dumps({'rows':len(out),'independent_fetched':sum(x['review_status']=='INDEPENDENT_SOURCE_FETCHED_NOT_HUMAN_REVIEWED' for x in out),'candidate_unverified':sum(x['review_status']=='CANDIDATE_NOT_FETCH_VERIFIED' for x in out),'no_source':sum(x['review_status']=='NO_CANONICAL_SOURCE' for x in out)},ensure_ascii=False))
