from pathlib import Path
import shutil,subprocess
root=Path(__file__).resolve().parents[1];p=root/'scp'/'api_server.py';bak=p.with_name(p.name+'.bak-rag-top-context-only-20260817');raw=p.read_text(encoding='utf-8-sig')
old='    body = " ".join(x for x in bodies if x).strip()\n'
new='    # Use the highest-ranked retrieved chunk for generation. Other chunks remain\n    # in evidence for context-precision evaluation but must not contaminate answer text.\n    body = next((x for x in bodies if x), "")\n'
if old not in raw:raise RuntimeError('extractive body assembly not found')
if bak.exists():bak.unlink()
shutil.copy2(p,bak);p.write_text(raw.replace(old,new,1),encoding='utf-8')
subprocess.run([str(root/'scp'/'venv'/'Scripts'/'python.exe'),'-m','py_compile',str(p)],check=True)
print('patched top-context-only',p,'backup',bak)
