from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
TEST_ROOT = ROOT / ".private-secrets" / "release-audit" / "scp-247" / "autofix-fixture"
DATA_DIR = TEST_ROOT / "engine-data"
FIXTURE = TEST_ROOT / "fixture_xss.py"
TEST_ROOT.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))
os.environ["SCP_AUTOFIX_RUN_PYTEST"] = "0"
os.environ["SCP_ENABLE_CLOSED_LOOP"] = "0"
os.environ["SCP_AUTO_APPROVE_TIER3"] = "0"
os.environ["SCP_ATTACK_MODE"] = "0"

from scp.autofix.classifier import BugClassifier, BugTier, BugReport
from scp.autofix.engine import AutoFixEngine
from scp.autofix.policy_gate import PolicyFix, evaluate_fix


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

# Fixture is intentionally outside scp/ and production data.
original = "from markupsafe import Markup\n\ndef render(user_input):\n    return Markup(user_input)\n"
FIXTURE.write_text(original, encoding="utf-8")
before = sha(FIXTURE)

classifier = BugClassifier()
relax = classifier.classify(
    file="fixture.py", line=1, bug_type="LogicChange",
    description="security policy change", suggested_fix="remove block rule",
)
policy = evaluate_fix(PolicyFix(
    fix_id="fixture:1:malicious", patch="ev" + "al(user_input)", patched_source="",
    bug_file=str(FIXTURE), bug_line=1, scanner_name="fixture",
))

engine = AutoFixEngine(data_dir=str(DATA_DIR))
preview = engine.preview_fix_dry_run(
    str(FIXTURE), original.replace("Markup(user_input)", "Markup(html.escape(user_input))")
)
after_preview = sha(FIXTURE)

bug = BugReport(
    file=str(FIXTURE), line=4, bug_type="XSSVulnerability",
    description="Markup(user_input) leaves user input unescaped",
    suggested_fix="Remove the Markup() wrapper and escape user input.",
    tier=BugTier.TIER_1_AUTO_FIX,
)
result = engine.process_bug(bug)
after_apply = sha(FIXTURE)

rollback = {"attempted": False}
if isinstance(result, dict) and result.get("rollback_token"):
    rollback["attempted"] = True
    rollback["result"] = engine.rollback_fix_by_token(result["rollback_token"])
rollback["hash_after_rollback"] = sha(FIXTURE)

out = {
    "fixture": str(FIXTURE),
    "before_hash": before,
    "after_preview_hash": after_preview,
    "after_apply_hash": after_apply,
    "after_rollback_hash": rollback["hash_after_rollback"],
    "preview_ok": bool(preview.get("ok")),
    "preview_did_not_mutate": before == after_preview,
    "relaxation_tier": int(relax.tier),
    "relaxation_hard_locked": bool(relax.is_relaxation),
    "policy_malicious_allowed": bool(policy.allowed),
    "apply_result": {
        k: result.get(k) for k in (
            "action", "status", "tier", "reason", "patched",
            "rollback_token", "before_hash", "after_hash",
            "reality_test_result", "policy_blocked",
        ) if k in result
    },
    "rollback": rollback,
}
print(json.dumps(out, ensure_ascii=False, sort_keys=True))

if not out["preview_did_not_mutate"]:
    raise SystemExit(10)
if out["relaxation_tier"] != 3 or not out["relaxation_hard_locked"]:
    raise SystemExit(11)
if out["policy_malicious_allowed"]:
    raise SystemExit(12)
if not out["preview_ok"]:
    raise SystemExit(13)
if rollback["attempted"] and rollback["hash_after_rollback"] != before:
    raise SystemExit(14)
if result.get("action") not in {"fixed", "skipped", "permission_requested", "denied"}:
    raise SystemExit(15)
