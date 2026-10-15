from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
p = root / "scp" / "runtime" / "judge.py"
bak = p.with_name(p.name + ".bak-domain-async-20260817")
if not bak.exists():
    shutil.copy2(p, bak)
raw = p.read_text(encoding="utf-8-sig")
old = '''    async def judge_async(self, question: str, ai_answer: str = "",
                          cycle_count: int = 0, source: str = "",
                          v98_context: Optional[dict] = None) -> Any:
'''
new = '''    async def judge_async(self, question: str, ai_answer: str = "",
                          cycle_count: int = 0, source: str = "",
                          v98_context: Optional[dict] = None,
                          domain_override: str | None = None) -> Any:
'''
if old not in raw:
    raise RuntimeError("judge_async signature not found")
raw = raw.replace(old, new, 1)
old2 = '''                cycle_count=cycle_count, source=source,
                v98_context=v98_context or {},
            )'''
new2 = '''                cycle_count=cycle_count, source=source,
                v98_context=v98_context or {},
                domain_override=domain_override,
            )'''
if raw.count(old2) < 1:
    raise RuntimeError("judge_async sync fallback call not found")
raw = raw.replace(old2, new2, 1)
old3 = '''    async def judge_with_react_fallback(self, question: str, ai_answer: str = "",
                                         cycle_count: int = 0, source: str = "",
                                         v98_context: Optional[dict] = None) -> Any:
'''
new3 = '''    async def judge_with_react_fallback(self, question: str, ai_answer: str = "",
                                         cycle_count: int = 0, source: str = "",
                                         v98_context: Optional[dict] = None,
                                         domain_override: str | None = None) -> Any:
'''
if old3 not in raw:
    raise RuntimeError("react fallback signature not found")
raw = raw.replace(old3, new3, 1)
old4 = '''                cycle_count=cycle_count, source=source,
                v98_context=v98_context,
            )'''
new4 = '''                cycle_count=cycle_count, source=source,
                v98_context=v98_context,
                domain_override=domain_override,
            )'''
if raw.count(old4) < 1:
    raise RuntimeError("react fallback async call not found")
raw = raw.replace(old4, new4, 1)
p.write_text(raw, encoding="utf-8")
py = root / "scp" / "venv" / "Scripts" / "python.exe"
subprocess.run([str(py), "-m", "py_compile", str(p)], check=True)
print("patched judge async domain propagation")
print(f"backup={bak}")
