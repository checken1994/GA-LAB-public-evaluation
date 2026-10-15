import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier
from scp.autofix.engine import AutoFixEngine
from scp.autofix.llm_fix import process_bug_with_llm

source = Path(str(Path(__file__).resolve().parent.parent / "scp" / "autofix" / "type_flow_verifier.py"))
tmp = Path(tempfile.mkdtemp(prefix="scp-r34-autofix-"))
target = tmp / source.name
shutil.copy2(source, target)
os.environ["SCP_LLM_PROVIDER_MODE"] = "ollama_only"
os.environ["SCP_AUTO_APPROVE_TIER3"] = "1"
os.environ["SCP_DEV_MODE"] = "0"
os.environ["SCP_SKIP_STARTUP_GATE"] = "1"
engine = AutoFixEngine(data_dir=str(tmp / "data"))
bug = BugReport(
    file=str(target),
    line=717,
    bug_type="BareExceptPass",
    description="broad except with pass",
    suggested_fix="",
    tier=BugTier.TIER_1_AUTO_FIX,
)
started = time.perf_counter()
try:
    result = process_bug_with_llm(bug, engine)
    payload = {
        "status": "RETURNED",
        "action": result.get("action") if isinstance(result, dict) else None,
        "fix_source": result.get("fix_source") if isinstance(result, dict) else None,
        "llm_generated": result.get("llm_generated") if isinstance(result, dict) else None,
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "target_changed": target.read_bytes() != source.read_bytes(),
    }
except Exception as exc:
    payload = {
        "status": "EXCEPTION",
        "error_type": type(exc).__name__,
        "error": str(exc)[:240],
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
print(json.dumps(payload, ensure_ascii=True))
