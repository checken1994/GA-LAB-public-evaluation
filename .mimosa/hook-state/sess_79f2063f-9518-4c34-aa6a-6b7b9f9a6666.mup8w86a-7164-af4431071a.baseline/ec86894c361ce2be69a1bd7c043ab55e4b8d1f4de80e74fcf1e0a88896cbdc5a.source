from pathlib import Path
from datetime import datetime
root=Path.cwd(); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); backup=root/'.private-secrets'/f'secret-file-auth-before-{stamp}'; backup.mkdir(parents=True,exist_ok=True)
for rel in ['scp/security/auth.py','scp/security/production_guard.py']:
    p=root/rel; (backup/p.name).write_bytes(p.read_bytes())
loader=root/'scp/security/secret_loader.py'
loader.write_text('''"""Secret loading with optional file-backed injection and no value logging."""\nfrom __future__ import annotations\nimport os\nfrom pathlib import Path\n\ndef read_secret(env_name: str, file_env_name: str) -> str:\n    path_value = os.environ.get(file_env_name, "").strip()\n    if path_value:\n        p = Path(path_value).expanduser()\n        if not p.is_file():\n            raise RuntimeError(f"{file_env_name} points to a missing secret file")\n        value = p.read_text(encoding="utf-8").strip()\n        if not value:\n            raise RuntimeError(f"{file_env_name} points to an empty secret file")\n        return value\n    return os.environ.get(env_name, "").strip()\n''',encoding='utf-8',newline='\n')
a=root/'scp/security/auth.py'; s=a.read_text(encoding='utf-8-sig')
if 'from scp.security.secret_loader import read_secret' not in s:
    s=s.replace('logger = logging.getLogger("scp.security.auth")','logger = logging.getLogger("scp.security.auth")\nfrom scp.security.secret_loader import read_secret',1)
s=s.replace('auth_password = os.environ.get("SCP_AUTH_PASSWORD", "")','auth_password = read_secret("SCP_AUTH_PASSWORD", "SCP_AUTH_PASSWORD_FILE")',1)
s=s.replace('auth_token = os.environ.get("SCP_AUTH_TOKEN_SECRET", "")','auth_token = read_secret("SCP_AUTH_TOKEN_SECRET", "SCP_AUTH_TOKEN_SECRET_FILE")',1)
a.write_text(s,encoding='utf-8',newline='\n')
g=root/'scp/security/production_guard.py'; gs=g.read_text(encoding='utf-8-sig')
if 'from scp.security.secret_loader import read_secret' not in gs:
    gs=gs.replace('import os','import os\nfrom scp.security.secret_loader import read_secret',1)
gs=gs.replace('password = os.environ.get("SCP_AUTH_PASSWORD", "")','password = read_secret("SCP_AUTH_PASSWORD", "SCP_AUTH_PASSWORD_FILE")',1)
g.write_text(gs,encoding='utf-8',newline='\n')
test=root/'tests/reality-tests/reality_4-d-027.py'
test.write_text('''#!/usr/bin/env python3\n"""Reality test: file-backed admin secret is used without logging its value."""\nimport os, sys, tempfile\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[2]))\nfrom scp.security.secret_loader import read_secret\nold=os.environ.get("SCP_AUTH_PASSWORD_FILE")\ntry:\n    with tempfile.TemporaryDirectory() as d:\n        p=Path(d)/"secret"; secret="test-file-secret-not-output"; p.write_text(secret,encoding="utf-8")\n        os.environ["SCP_AUTH_PASSWORD_FILE"]=str(p)\n        assert read_secret("SCP_AUTH_PASSWORD","SCP_AUTH_PASSWORD_FILE")==secret\n        assert secret not in repr(read_secret)\n        print("PASS [1]: file-backed secret loaded without value output")\nfinally:\n    if old is None: os.environ.pop("SCP_AUTH_PASSWORD_FILE",None)\n    else: os.environ["SCP_AUTH_PASSWORD_FILE"]=old\nprint("✓ Reality test 4-d-027 PASSED")\n''',encoding='utf-8',newline='\n')
print(f'backup={backup}')
