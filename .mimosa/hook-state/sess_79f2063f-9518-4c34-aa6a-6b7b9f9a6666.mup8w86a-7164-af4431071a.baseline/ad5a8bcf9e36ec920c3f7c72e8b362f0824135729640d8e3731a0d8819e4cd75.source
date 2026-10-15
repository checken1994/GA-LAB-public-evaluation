from pathlib import Path
import shutil,subprocess,re
root=Path(__file__).resolve().parents[1];p=root/'scp'/'api_server.py';bak=p.with_name(p.name+'.bak-auto-canonical-retrieval-20260817')
raw=p.read_text(encoding='utf-8-sig')
if 'from scp.rag.canonical_retriever import get_canonical_retriever' not in raw:
 marker='from scp.web_control.internet_search import InternetSearch\n'
 ins='''from scp.web_control.internet_search import InternetSearch\ntry:\n    from scp.rag.canonical_retriever import get_canonical_retriever\nexcept Exception as _retriever_import_error:\n    get_canonical_retriever = None\n    logger.warning(f"[RAG] canonical retriever unavailable: {_retriever_import_error}")\n'''
 if marker not in raw: raise RuntimeError('import marker not found')
 raw=raw.replace(marker,ins,1)
old='''    if req.rag_enabled and (req.contexts or req.retrieved_context):\n        return await _ask_rag_verified(req, request)\n'''
new='''    if req.rag_enabled:\n        # Auto-retrieve only from the versioned canonical corpus. If no verified\n        # candidate is found, keep the request on the normal abstention path.\n        if not req.contexts and not req.retrieved_context and get_canonical_retriever is not None:\n            try:\n                req.contexts = get_canonical_retriever().contexts(req.question, k=5)\n            except Exception as _retrieval_error:\n                logger.warning(f"[RAG] canonical retrieval failed: {_retrieval_error}")\n                req.contexts = []\n        if req.contexts or req.retrieved_context:\n            return await _ask_rag_verified(req, request)\n'''
if old not in raw: raise RuntimeError('rag dispatch block not found')
raw=raw.replace(old,new,1)
if bak.exists():bak.unlink()
shutil.copy2(p,bak);p.write_text(raw,encoding='utf-8')
subprocess.run([str(root/'scp'/'venv'/'Scripts'/'python.exe'),'-m','py_compile',str(p)],check=True)
print('patched',p,'backup',bak)
