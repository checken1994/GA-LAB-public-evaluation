from pathlib import Path
import shutil,subprocess
root=Path(__file__).resolve().parents[1];api=root/'scp'/'api_server.py';rap=root/'scp'/'rag'/'canonical_retriever.py'
for p,name in [(api,'api-k1'),(rap,'retriever-host-deny')]:
 raw=p.read_text(encoding='utf-8-sig');bak=p.with_name(p.name+'.bak-'+name+'-20260817')
 if name=='api-k1':
  old='get_canonical_retriever().contexts(req.question, k=5)';new='get_canonical_retriever().contexts(req.question, k=1)'
  if old not in raw:raise RuntimeError('api retrieval k marker not found')
  raw=raw.replace(old,new,1)
 else:
  old="if not str(url).startswith(('http://','https://')) or 'bing.com/' in str(url):continue"
  new="if (not str(url).startswith(('http://','https://')) or 'bing.com/' in str(url) or any(bad in str(url).lower() for bad in ('mangatown.com','free-work.com','xhamster.com','pornhub.com'))):continue"
  if old not in raw:raise RuntimeError('retriever URL gate not found')
  raw=raw.replace(old,new,1)
 if bak.exists():bak.unlink()
 shutil.copy2(p,bak);p.write_text(raw,encoding='utf-8')
 subprocess.run([str(root/'scp'/'venv'/'Scripts'/'python.exe'),'-m','py_compile',str(p)],check=True)
 print('patched',p,'backup',bak)
