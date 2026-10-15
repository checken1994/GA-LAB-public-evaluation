from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
TEST_DIR = ROOT / ".private-secrets" / "release-audit" / "r43-failclosed-test"
if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)
TEST_DIR.mkdir(parents=True)
DB = TEST_DIR / "v13.db"

sys.path.insert(0, str(ROOT))
from scp.core.fast_learning_engine import FastLearningEngine
import scp.meta.why_gate as why_gate_module
import scp.knowledge.source_reputation as reputation_module
import scp.core.db_manager as db_manager_module

engine = FastLearningEngine(scp_db_path=str(DB), data_dir=str(TEST_DIR))

class AllowWhy:
    allowed = True

original_why = why_gate_module.get_why_gate
original_rep = reputation_module.ReputationStore
original_db_exec = db_manager_module.db_exec


def good_why():
    class Gate:
        def gate(self, **kwargs):
            return AllowWhy()
    return Gate()

why_gate_module.get_why_gate = good_why

results = {}

# 1) Watchlist failure must block.
def broken_reputation(*args, **kwargs):
    raise RuntimeError("synthetic-watchlist-infra-failure")
reputation_module.ReputationStore = broken_reputation
results["watchlist_error_blocks"] = engine._store_kb("watchlist-test", "verified_answer", "value", "test-source", 0.8) is False
reputation_module.ReputationStore = original_rep

# 2) Verification failure must block.
def broken_verify(*args, **kwargs):
    raise RuntimeError("synthetic-verify-infra-failure")
engine._verify_learned_fact = broken_verify
results["verify_error_blocks"] = engine._store_kb("verify-test", "verified_answer", "value", "test-source", 0.8) is False

# Restore verification and test DB write failure.
def valid_verify(*args, **kwargs):
    return True, "test-ok", 0.0
engine._verify_learned_fact = valid_verify

def broken_db_exec(*args, **kwargs):
    raise RuntimeError("synthetic-db-write-failure")
db_manager_module.db_exec = broken_db_exec
results["db_write_error_blocks"] = engine._store_kb("db-test", "verified_answer", "value", "test-source", 0.8) is False
db_manager_module.db_exec = original_db_exec

# 3) WHY failure must block.
def broken_why():
    raise RuntimeError("synthetic-why-infra-failure")
why_gate_module.get_why_gate = broken_why
results["why_error_blocks"] = engine._store_kb("why-test", "verified_answer", "value", "test-source", 0.8) is False
why_gate_module.get_why_gate = original_why

# 4) A verified result with store=False must report stored=0.
async def fake_ask(question):
    return "a valid answer"
async def fake_wiki(question, answer):
    return {"verified": True, "confidence": 0.9}
engine._ask_ollama_parallel = fake_ask
engine._check_wikipedia_parallel = fake_wiki
engine._store_kb = lambda **kwargs: False
cycle = asyncio.run(engine.fast_learning_cycle(count=1))
results["stored_metric_reflects_false"] = cycle.get("verified") == 1 and cycle.get("stored") == 0

ok = all(results.values())
report = {
    "status": "PASS" if ok else "FAIL",
    "checks": results,
    "cycle_metrics": {key: cycle.get(key) for key in ("asked", "verified", "stored")},
    "test_dir": str(TEST_DIR),
}
(TEST_DIR / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
raise SystemExit(0 if ok else 1)
