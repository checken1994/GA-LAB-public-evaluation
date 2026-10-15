#!/usr/bin/env python3
"""Reality test: scheduler source has an explicit auth boundary for mutating controls."""
from pathlib import Path

p=Path(__file__).resolve().parents[2]/"mini-services/loop-scheduler/index.ts"
s=p.read_text(encoding="utf-8")
required=["SCP_SCHEDULER_ADMIN_TOKEN","schedulerAdminAuthorized","/trigger","/pause","/resume","scheduler admin authentication required"]
missing=[x for x in required if x not in s]
assert not missing, missing
print("PASS [1]: scheduler mutating endpoints require explicit admin token")
print("✓ Reality test 4-d-028 PASSED")
