from pathlib import Path
import shutil,subprocess
root=Path(__file__).resolve().parents[1];p=root/'scp'/'api_server.py';bak=p.with_name(p.name+'.bak-rag-fail-closed-20260817');raw=p.read_text(encoding='utf-8-sig')
old='''        if req.contexts or req.retrieved_context:\n            return await _ask_rag_verified(req, request)\n'''
new='''        # RAG requests never fall through to an ungrounded model answer.\n        return await _ask_rag_verified(req, request)\n'''
if old not in raw:raise RuntimeError('auto retrieval dispatch block not found')
if bak.exists():bak.unlink()
shutil.copy2(p,bak);p.write_text(raw.replace(old,new,1),encoding='utf-8')
subprocess.run([str(root/'scp'/'venv'/'Scripts'/'python.exe'),'-m','py_compile',str(p)],check=True)
print('patched',p,'backup',bak)
