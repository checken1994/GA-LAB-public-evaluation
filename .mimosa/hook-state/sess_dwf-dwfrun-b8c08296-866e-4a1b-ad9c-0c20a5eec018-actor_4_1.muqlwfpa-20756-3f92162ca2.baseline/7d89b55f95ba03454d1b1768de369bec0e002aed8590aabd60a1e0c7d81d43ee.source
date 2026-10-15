from pathlib import Path
from datetime import datetime
import re
root=Path.cwd(); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); backup=root/'.private-secrets'/f'final-reality-fix-{stamp}'; backup.mkdir(parents=True,exist_ok=True)
files=[root/'tests/reality-tests/reality_4-b-018.py', root/'scp/knowledge/trust_hierarchy.py']
for p in files:
    (backup/(p.name+'.before')).write_bytes(p.read_bytes())
# Ensure import is before any Path use.
p=files[0]; s=p.read_text(encoding='utf-8-sig')
if 'from pathlib import Path' not in s:
    s=s.replace('import time\n','import time\nfrom pathlib import Path\n',1)
else:
    lines=s.splitlines(True); idx=next((i for i,l in enumerate(lines) if l.startswith('from pathlib import Path')),None)
    use=next((i for i,l in enumerate(lines) if 'Path(__file__)' in l),None)
    if idx is not None and use is not None and idx>use:
        line=lines.pop(idx); lines.insert(use,line); s=''.join(lines)
p.write_text(s,encoding='utf-8',newline='\n')
# Remove stale literal wording that B015 correctly flags as an invalid historical reference.
p=files[1]; s=p.read_text(encoding='utf-8-sig')
s,n=re.subn(r'(?ms)^\s*# \[Fix 4-b-015\] slm_self was tier 5.*?^\s*# SLM self-reports are the least trustworthy source per design\.\s*\n', '    # [Fix 4-b-015] The self-answer entry previously used an unsupported\n    # numeric enum value. It now uses level 4 (LEARNED), the lowest legitimate\n    # level, because self-reports are the least trustworthy source by design.\n', s, count=1)
if n!=1: raise SystemExit('B015 comment marker not found')
p.write_text(s,encoding='utf-8',newline='\n')
print(f'backup={backup}')
print('patched B018 Path import and B015 comment')
