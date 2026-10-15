from pathlib import Path
from datetime import datetime
root=Path.cwd(); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); backup=root/'.private-secrets'/f'reality-runner-before-portable-{stamp}'; backup.mkdir(parents=True,exist_ok=True)
for rel in (Path('tests/run-reality-tests.sh'), Path('tests/reality-check.sh')):
    p=root/rel
    if not p.exists(): continue
    s=p.read_text(encoding='utf-8-sig')
    (backup/rel.name).write_bytes(p.read_bytes())
    marker='PYTHON_BIN="${SCP_PYTHON_BIN:-python3}"'
    if marker not in s:
        lines=s.splitlines(keepends=True)
        idx=1 if lines and lines[0].startswith('#!') else 0
        lines.insert(idx, marker+'\n')
        s=''.join(lines)
    s=s.replace('python3 "$script"', '"$PYTHON_BIN" "$script"')
    s=s.replace('python3 -c ', '"$PYTHON_BIN" -c ')
    p.write_text(s,encoding='utf-8',newline='\n')
    print(f'patched {rel}')
print(f'backup={backup}')
