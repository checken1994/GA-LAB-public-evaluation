from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
files = [
    ROOT / "scp" / "runtime" / "judge_parts" / "judgeroute_mixin.py",
    ROOT / "scp" / "runtime" / "judge_parts" / "judgecore_mixin.py",
    ROOT / "scp" / "api_server.py",
]
for p in files:
    bak = p.with_name(p.name + ".bak-domain-override-20260817")
    if not bak.exists():
        shutil.copy2(p, bak)

route = files[0]
raw = route.read_text(encoding="utf-8-sig")
old = '    def _route_question(self, question: str) -> list[str]:\n'
new = '''    def _route_question(self, question: str, domain_override: str | None = None) -> list[str]:\n'''
if old not in raw:
    raise RuntimeError("route signature not found")
raw = raw.replace(old, new, 1)
old2 = '''        if not question:\n            return ["math"]\n        #  Check cache first\n'''
new2 = '''        # Explicit domain supplied by a trusted benchmark/request caller wins over\n        # heuristic numbers/date tokens. Only route to domains with a registered SLM.\n        if domain_override:\n            normalized = str(domain_override).strip().lower()\n            allowed = {\n                "math", "biology", "finance", "geography", "history", "chemistry",\n                "weather", "physics", "education", "psychology", "environment",\n                "energy", "transport", "blockchain", "cybersecurity", "genai",\n                "social", "aerospace", "tourism", "foodtech", "geology",\n                "oceanography", "cartography", "architecture", "uxui",\n                "digitalmarketing", "ecommerce", "audiovideo", "crafts",\n                "diplomacy", "heritage", "military", "spacemedicine",\n                "legal", "general",\n            }\n            if normalized in allowed:\n                return [normalized]\n        if not question:\n            return ["math"]\n        #  Check cache first\n'''
if old2 not in raw:
    raise RuntimeError("route preamble not found")
raw = raw.replace(old2, new2, 1)
route.write_text(raw, encoding="utf-8")

core = files[1]
raw = core.read_text(encoding="utf-8-sig")
old = '        domains = self._route_question(question)\n'
new = '        domains = self._route_question(question, domain_override=kwargs.get("domain_override"))\n'
if old not in raw:
    raise RuntimeError("core route call not found")
raw = raw.replace(old, new, 1)
core.write_text(raw, encoding="utf-8")

api = files[2]
raw = api.read_text(encoding="utf-8-sig")
old = '''            question=req.question,\n            ai_answer=_ai_answer,\n            cycle_count=0,\n            source=req.source,\n            v98_context=v98_context,\n'''
new = '''            question=req.question,\n            ai_answer=_ai_answer,\n            cycle_count=0,\n            source=req.source,\n            v98_context=v98_context,\n            domain_override=req.domain,\n'''
if old not in raw:
    raise RuntimeError("api judge call block not found")
raw = raw.replace(old, new, 1)
api.write_text(raw, encoding="utf-8")

py = ROOT / "scp" / "venv" / "Scripts" / "python.exe"
for p in files:
    subprocess.run([str(py), "-m", "py_compile", str(p)], check=True)
print("patched explicit domain override")
for p in files:
    print(p)
