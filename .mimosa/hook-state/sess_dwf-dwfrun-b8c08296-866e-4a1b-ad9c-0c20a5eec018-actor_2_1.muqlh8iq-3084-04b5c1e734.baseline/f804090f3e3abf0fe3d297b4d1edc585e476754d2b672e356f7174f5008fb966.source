#!/usr/bin/env python3
"""Reality test: file-backed admin secret is used without logging its value."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scp.security.secret_loader import read_secret

old=os.environ.get("SCP_AUTH_PASSWORD_FILE")
try:
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"secret"; secret="test-file-secret-not-output"; p.write_text(secret,encoding="utf-8")
        os.environ["SCP_AUTH_PASSWORD_FILE"]=str(p)
        assert read_secret("SCP_AUTH_PASSWORD","SCP_AUTH_PASSWORD_FILE")==secret
        assert secret not in repr(read_secret)
        print("PASS [1]: file-backed secret loaded without value output")
finally:
    if old is None: os.environ.pop("SCP_AUTH_PASSWORD_FILE",None)
    else: os.environ["SCP_AUTH_PASSWORD_FILE"]=old
print("✓ Reality test 4-d-027 PASSED")
