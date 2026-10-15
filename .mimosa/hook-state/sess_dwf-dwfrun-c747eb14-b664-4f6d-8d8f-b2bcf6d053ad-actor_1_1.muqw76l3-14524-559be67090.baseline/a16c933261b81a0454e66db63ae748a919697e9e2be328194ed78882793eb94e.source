#!/usr/bin/env python3
"""Reality test for explicit fail-closed production safety guard."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scp.security.production_guard import enforce_production_safety

keys=["SCP_PRODUCTION_MODE","SCP_AUTH_PASSWORD","SCP_DEV_MODE","SCP_SKIP_STARTUP_GATE","SCP_AUTO_APPROVE_TIER3","SCP_EVOLUTION_AUTO","SCP_ENABLE_CLOSED_LOOP","SCP_TIER3_ALLOW_RELAXATION","SCP_TIER3_ALLOW_BAREEXCEPTPASS"]
old={k:os.environ.get(k) for k in keys}
try:
    os.environ["SCP_PRODUCTION_MODE"]="1"
    os.environ["SCP_AUTH_PASSWORD"]="short"
    os.environ["SCP_DEV_MODE"]="1"
    try:
        enforce_production_safety()
    except RuntimeError as exc:
        text=str(exc)
        assert "SCP_DEV_MODE" in text and "short" not in text
        print("PASS [1]: unsafe production config refused without secret leakage")
    else:
        raise AssertionError("unsafe production config was accepted")
    os.environ["SCP_DEV_MODE"]="0"
    os.environ["SCP_AUTH_PASSWORD"]="a-strong-test-password"
    os.environ["SCP_EGRESS_MODE"]="deny"
    enforce_production_safety()
    print("PASS [2]: safe explicit production config accepted")
finally:
    for k,v in old.items():
        if v is None: os.environ.pop(k,None)
        else: os.environ[k]=v
print("✓ Reality test 4-d-026 PASSED")
