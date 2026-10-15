import sys
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
p = root / "scp" / "api_server.py"
bak = p.with_name(p.name + ".bak-ask-domain-dispatch-20260817")
if not bak.exists():
    shutil.copy2(p, bak)
raw = p.read_text(encoding="utf-8-sig")
old = '''    # [OPT-8/9] Use async judge with ReActAgent fallback.
    # Was: asyncio.to_thread(judge.judge, ...) — blocked event loop thread.
    # Now: judge_with_react_fallback() — async LLM call + ReActAgent when
    # SmartClassifier confidence < 0.5. Falls back to sync judge() on error.
    if hasattr(judge, "judge_with_react_fallback"):
        v = await judge.judge_with_react_fallback(
            question=req.question,
            ai_answer=_ai_answer,
            cycle_count=0,
            source=req.source,
            v98_context=v98_context,
            domain_override=req.domain,
        )
    else:
        # Fallback for older judge instances without async method
        v = await asyncio.to_thread(
            judge.judge,
            question=req.question,
            ai_answer=_ai_answer,
            cycle_count=0,
            source=req.source,
            v98_context=v98_context,
        )
'''
new = '''    # Explicit benchmark domain must use the sync JudgeCore route because the
    # async phase pipeline still performs heuristic routing. This prevents dates
    # and numeric tokens from sending history/biology/finance questions to MathSLM.
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
        # Fallback for older judge instances without async method
        v = await asyncio.to_thread(
            judge.judge,
            question=req.question,
            ai_answer=_ai_answer,
            cycle_count=0,
            source=req.source,
            v98_context=v98_context,
        )
'''
if old not in raw:
    raise RuntimeError("ask dispatch block not found")
raw = raw.replace(old, new, 1)
p.write_text(raw, encoding="utf-8")
subprocess.run([sys.executable, "-m", "py_compile", str(p)], check=True)
print("patched ask explicit-domain dispatch")
print(f"backup={bak}")
