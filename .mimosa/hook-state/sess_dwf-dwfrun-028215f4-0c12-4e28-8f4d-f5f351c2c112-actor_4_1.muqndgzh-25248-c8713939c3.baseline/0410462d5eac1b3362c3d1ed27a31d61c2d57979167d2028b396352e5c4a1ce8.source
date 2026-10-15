import sys
from pathlib import Path
import shutil
import re
import subprocess

root = Path(__file__).resolve().parents[1]
p = root / "scp" / "api_server.py"
bak = p.with_name(p.name + ".bak-ask-domain-dispatch-20260817")
if not bak.exists():
    shutil.copy2(p, bak)
raw = p.read_text(encoding="utf-8-sig")
pattern = re.compile(r'''    if hasattr\(judge, ["']judge_with_react_fallback["']\):.*?\n    stage_request\(request, ["']verifier_completed["']''', re.S)
match = pattern.search(raw)
if not match:
    raise RuntimeError("ask dispatch region not found")
new = '''    # Explicit benchmark domain uses sync JudgeCore routing. The async phase
    # pipeline still applies heuristic routing, which can mistake dates/numbers
    # for MathSLM. This branch preserves the caller's trusted domain.
    if req.domain:
        v = await asyncio.to_thread(
            judge.judge,
            question=req.question,
            ai_answer=_ai_answer,
            cycle_count=0,
            source=req.source,
            v98_context=v98_context,
            domain_override=req.domain,
        )
    elif hasattr(judge, "judge_with_react_fallback"):
        v = await judge.judge_with_react_fallback(
            question=req.question,
            ai_answer=_ai_answer,
            cycle_count=0,
            source=req.source,
            v98_context=v98_context,
        )
    else:
        v = await asyncio.to_thread(
            judge.judge,
            question=req.question,
            ai_answer=_ai_answer,
            cycle_count=0,
            source=req.source,
            v98_context=v98_context,
        )
    stage_request(request, "verifier_completed"'''
raw = raw[:match.start()] + new + raw[match.end():]
p.write_text(raw, encoding="utf-8")
subprocess.run([sys.executable, "-m", "py_compile", str(p)], check=True)
print("patched ask explicit-domain dispatch")
print(f"backup={bak}")
