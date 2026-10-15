from pathlib import Path
from datetime import datetime
root=Path.cwd(); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); backup=root/'.private-secrets'/f'llm-fix-secrets-before-{stamp}'; backup.mkdir(parents=True,exist_ok=True)
p=root/'scp/autofix/llm_fix.py'; (backup/p.name).write_bytes(p.read_bytes())
s=p.read_text(encoding='utf-8-sig')
if 'from scp.security.secret_loader import read_secret' not in s:
    marker='import os\n'
    if marker not in s: raise SystemExit('import os marker missing')
    s=s.replace(marker,marker+'from scp.security.secret_loader import read_secret\n',1)
old='''    api_key = os.environ.get("OPENROUTER_API_KEY", "")\n    if not api_key:\n        # Try OPENROUTER_API_KEY_2, _3 (fallback)\n        for i in (2, 3):\n            api_key = os.environ.get(f"OPENROUTER_API_KEY_{i}", "")\n            if api_key:\n                break'''
new='''    api_key = read_secret("OPENROUTER_API_KEY", "OPENROUTER_API_KEY_FILE")\n    if not api_key:\n        # Try file-backed/env fallback keys without logging their values.\n        for i in (2, 3):\n            api_key = read_secret(f"OPENROUTER_API_KEY_{i}", f"OPENROUTER_API_KEY_{i}_FILE")\n            if api_key:\n                break'''
if old not in s: raise SystemExit('api key block marker missing')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8',newline='\n')
test=root/'tests/reality-tests/reality_4-d-030.py'
test.write_text('''#!/usr/bin/env python3\n"""Reality test: Python autofix LLM consumer uses file-backed provider secret loader."""\nfrom pathlib import Path\np=Path(__file__).resolve().parents[2]/"scp/autofix/llm_fix.py"\ns=p.read_text(encoding="utf-8")\nfor marker in ["read_secret", "OPENROUTER_API_KEY_FILE", "OPENROUTER_API_KEY_2_FILE", "OPENROUTER_API_KEY_3_FILE"]:\n    assert marker in s, marker\nprint("PASS [1]: llm_fix uses file-backed provider secret references")\nprint("✓ Reality test 4-d-030 PASSED")\n''',encoding='utf-8',newline='\n')
print(f'backup={backup}')
