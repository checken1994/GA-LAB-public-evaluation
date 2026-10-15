from pathlib import Path
from datetime import datetime
root=Path.cwd(); p=root/'tests/reality-tests/reality_4-d-025.py'; stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); b=root/'.private-secrets'/f'reality-4-d-025-before-path-{stamp}.py'; b.write_bytes(p.read_bytes())
s=p.read_text(encoding='utf-8-sig')
if 'sys.path.insert' not in s:
    marker='import os\n'
    if marker not in s: raise SystemExit('import os marker missing')
    s=s.replace(marker, 'import os\nimport sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[2]))\n', 1)
p.write_text(s,encoding='utf-8',newline='\n')
print(f'backup={b}')
