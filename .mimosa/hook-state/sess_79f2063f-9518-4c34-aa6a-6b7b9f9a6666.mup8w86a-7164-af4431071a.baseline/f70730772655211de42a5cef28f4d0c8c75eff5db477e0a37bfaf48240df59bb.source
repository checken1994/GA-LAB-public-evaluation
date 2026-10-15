from pathlib import Path
import re,shutil,subprocess
root=Path(__file__).resolve().parents[1];p=root/'scp'/'api_server.py';bak=p.with_name(p.name+'.bak-extractive-rag-header-20260817')
raw=p.read_text(encoding='utf-8-sig')
start=raw.index('def _extractive_rag_answer(');end=raw.index('async def _ask_rag_verified',start)
new='''def _extractive_rag_answer(question: str, contexts: list[str]) -> str:\n    """Select answer-bearing source sentences without leaking source metadata.\n\n    Context metadata remains in evidence; only the textual excerpt is returned.\n    """\n    import re\n    usable = [str(x).strip() for x in (contexts or []) if str(x).strip()]\n    if not usable:\n        return ""\n    bodies = []\n    for item in usable:\n        text = re.sub(r"\\s+", " ", item).strip()\n        text = re.sub(r"^\\[chunk_id=[^\\]]+\\]\\s*", "", text, flags=re.I)\n        text = re.sub(r"^source_url=https?://\\S+\\s*", "", text, flags=re.I)\n        text = re.sub(r"^https?://\\S+\\s*", "", text, flags=re.I)\n        bodies.append(text.strip())\n    body = " ".join(x for x in bodies if x).strip()\n    if not body:\n        return ""\n    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\\s+", body) if s.strip()]\n    q = set(re.findall(r"[\\wÀ-ỹ]{4,}", question.lower()))\n    ranked = []\n    for i, sentence in enumerate(sentences):\n        terms = set(re.findall(r"[\\wÀ-ỹ]{4,}", sentence.lower()))\n        ranked.append((len(q & terms), -i, sentence))\n    ranked.sort(reverse=True)\n    return " ".join(x[2] for x in ranked[:4])[:3500]\n\n'''
if bak.exists():bak.unlink()
shutil.copy2(p,bak);p.write_text(raw[:start]+new+raw[end:],encoding='utf-8')
subprocess.run([str(root/'scp'/'venv'/'Scripts'/'python.exe'),'-m','py_compile',str(p)],check=True)
print('patched',p,'backup',bak)
