import sys
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
p = root / "scp" / "api" / "routes" / "batch_benchmark_routes.py"
bak = p.with_name(p.name + ".bak-domain-field-20260817")
if not bak.exists():
    shutil.copy2(p, bak)
raw = p.read_text(encoding="utf-8-sig")
old = '''        "ground_truth": ground_truth,
        "rag_enabled": bool(contexts),
    }'''
new = '''        "ground_truth": ground_truth,
        "domain": str(item.get("domain", ""))[:64],
        "rag_enabled": bool(contexts),
    }'''
if old not in raw:
    raise RuntimeError("rag payload block not found")
raw = raw.replace(old, new, 1)
p.write_text(raw, encoding="utf-8")
subprocess.run([sys.executable, "-m", "py_compile", str(p)], check=True)
print("patched batch domain field")
print(f"backup={bak}")
