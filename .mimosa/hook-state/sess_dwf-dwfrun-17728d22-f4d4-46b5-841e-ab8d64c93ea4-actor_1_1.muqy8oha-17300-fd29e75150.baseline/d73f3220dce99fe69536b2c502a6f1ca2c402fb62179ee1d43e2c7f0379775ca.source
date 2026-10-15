from pathlib import Path
from datetime import datetime
root=Path.cwd(); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); backup=root/'.private-secrets'/f'egress-policy-before-{stamp}'; backup.mkdir(parents=True,exist_ok=True)
source=root/'scp/core/url_fetcher.py'; (backup/source.name).write_bytes(source.read_bytes())
s=source.read_text(encoding='utf-8-sig')
if 'import os\n' not in s:
    s=s.replace('import logging\n','import logging\nimport os\n',1)
marker='    hostname = parsed.hostname\n'
insert='''    hostname = parsed.hostname\n    # Explicit test/staging egress policy. Production defaults to allow here,\n    # while a hardened environment can set SCP_EGRESS_MODE=deny/offline.\n    egress_mode = os.environ.get("SCP_EGRESS_MODE", "allow").strip().lower()\n    if egress_mode in {"deny", "offline", "disabled"} and hostname not in {"localhost", "127.0.0.1", "::1"}:\n        raise ValueError("external egress disabled by SCP_EGRESS_MODE")\n'''
if marker not in s: raise SystemExit('hostname marker missing')
if 'external egress disabled by SCP_EGRESS_MODE' not in s: s=s.replace(marker,insert,1)
source.write_text(s,encoding='utf-8',newline='\n')
# Add an executable reality test for the deny policy.
test=root/'tests/reality-tests/reality_4-d-025.py'
if not test.exists():
    test.write_text('''#!/usr/bin/env python3\n"""Reality test: explicit egress deny blocks external URLs before DNS/network."""\nimport os\nfrom scp.core.url_fetcher import _safe_fetch_url\nold=os.environ.get("SCP_EGRESS_MODE")\nos.environ["SCP_EGRESS_MODE"]="deny"\ntry:\n    try:\n        _safe_fetch_url("https://example.com", timeout=1)\n    except ValueError as exc:\n        assert "external egress disabled" in str(exc), str(exc)\n        print("PASS [1]: external egress denied before network")\n    else:\n        raise AssertionError("external URL was not denied")\nfinally:\n    if old is None: os.environ.pop("SCP_EGRESS_MODE", None)\n    else: os.environ["SCP_EGRESS_MODE"]=old\nprint("✓ Reality test 4-d-025 PASSED")\n''',encoding='utf-8',newline='\n')
else:
    (backup/test.name).write_bytes(test.read_bytes())
print(f'backup={backup}')
print('patched egress policy and reality test')
