from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
p = root / "scp" / "runtime" / "judge_parts" / "judgecore_mixin.py"
bak = p.with_name(p.name + ".bak-domain-signature-20260817")
if not bak.exists():
    shutil.copy2(p, bak)
raw = p.read_text(encoding="utf-8-sig")
old_sig = '''    def judge(self, question: str, ai_answer: str = "", cycle_count: int = 0,
              source: str = "", v98_context: Optional[dict[str, Any]] = None) -> JudgeVerdict:
'''
new_sig = '''    def judge(self, question: str, ai_answer: str = "", cycle_count: int = 0,
              source: str = "", v98_context: Optional[dict[str, Any]] = None,
              domain_override: str | None = None) -> JudgeVerdict:
'''
if old_sig not in raw:
    raise RuntimeError("JudgeCoreMixin judge signature not found")
raw = raw.replace(old_sig, new_sig, 1)
old_call = '        domains = self._route_question(question, domain_override=kwargs.get("domain_override"))\n'
new_call = '        domains = self._route_question(question, domain_override=domain_override)\n'
if old_call not in raw:
    raise RuntimeError("domain routing call not found")
raw = raw.replace(old_call, new_call, 1)
p.write_text(raw, encoding="utf-8")
py = root / "scp" / "venv" / "Scripts" / "python.exe"
subprocess.run([str(py), "-m", "py_compile", str(p)], check=True)
print("patched JudgeCoreMixin domain signature")
print(f"backup={bak}")
