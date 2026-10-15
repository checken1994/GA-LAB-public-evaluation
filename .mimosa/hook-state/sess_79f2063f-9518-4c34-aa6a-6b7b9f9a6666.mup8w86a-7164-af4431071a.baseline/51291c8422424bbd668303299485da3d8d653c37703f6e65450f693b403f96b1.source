from pathlib import Path
import shutil,subprocess
root=Path(__file__).resolve().parents[1];p=root/'scp'/'rag'/'canonical_retriever.py';bak=p.with_name(p.name+'.bak-coverage-threshold-20260817');raw=p.read_text(encoding='utf-8-sig')
old='if distinctive and coverage<0.6:continue';new='if distinctive and coverage<0.75:continue'
if old not in raw:raise RuntimeError('coverage threshold marker not found')
if bak.exists():bak.unlink()
shutil.copy2(p,bak);p.write_text(raw.replace(old,new,1),encoding='utf-8');subprocess.run([str(root/'scp'/'venv'/'Scripts'/'python.exe'),'-m','py_compile',str(p)],check=True);print('patched',p,'backup',bak)
