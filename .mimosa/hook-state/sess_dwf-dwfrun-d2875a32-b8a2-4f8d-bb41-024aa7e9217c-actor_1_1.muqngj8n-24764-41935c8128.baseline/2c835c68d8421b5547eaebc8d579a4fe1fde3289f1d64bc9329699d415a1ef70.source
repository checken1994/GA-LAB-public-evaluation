from pathlib import Path
from datetime import datetime
root=Path.cwd(); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); b=root/'.private-secrets'/f'reality-runner-before-utf8-{stamp}'; b.mkdir(parents=True,exist_ok=True)
for rel in (Path('tests/run-reality-tests.sh'), Path('tests/reality-check.sh')):
    p=root/rel
    if not p.exists(): continue
    s=p.read_text(encoding='utf-8-sig'); (b/p.name).write_bytes(p.read_bytes())
    marker='export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"\n'
    if marker not in s:
        s=s.replace('PYTHON_BIN="${SCP_PYTHON_BIN:-python3}"\n', 'PYTHON_BIN="${SCP_PYTHON_BIN:-python3}"\n'+marker)
    p.write_text(s,encoding='utf-8',newline='\n')
    print(f'patched {rel}')
print(f'backup={b}')
