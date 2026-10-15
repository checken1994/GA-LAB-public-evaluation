import ast
from pathlib import Path

repo = Path("D:/scp")

pairs = [
    ("core", "autofix"),
    ("autofix", "core"),
    ("core", "hands"),
    ("hands", "core"),
    ("epistemic", "governance"),
    ("governance", "epistemic"),
    ("security", "api_server_parts"),
    ("api_server_parts", "security"),
    ("llm_gateway", "security"),
    ("security", "llm_gateway"),
    ("meta", "knowledge"),
    ("knowledge", "meta"),
    ("meta", "security"),
    ("security", "meta"),
]

for src_sub, tgt_sub in pairs:
    src_dir = repo / "scp" / src_sub
    print(f"\n--- Imports from [{src_sub}] -> [{tgt_sub}] ---")
    for py_file in src_dir.rglob("*.py"):
        try:
            lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            for line_idx, line in enumerate(lines, 1):
                if f"scp.{tgt_sub}" in line:
                    rel_p = str(py_file.relative_to(repo)).replace("\\", "/")
                    print(f"  {rel_p}:{line_idx} -> {line.strip()}")
        except Exception:
            pass
