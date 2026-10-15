from pathlib import Path
import re
root = Path.cwd()
test_dir = root / "tests" / "reality-tests"
pat = re.compile(r"(str\(Path\(__file__\)\.resolve\(\)\.parents\[2\]\))(\s*)(['\"])([^'\"]*)\3")
changed = 0
replacements = 0
for p in sorted(test_dir.rglob("*.py")):
    s = p.read_text(encoding="utf-8-sig")
    def repl(m: re.Match[str]) -> str:
        return f"{m.group(1)} + {m.group(3)}{m.group(4)}{m.group(3)}"
    ntext, n = pat.subn(repl, s)
    if n:
        p.write_text(ntext, encoding="utf-8", newline="\n")
        changed += 1
        replacements += n
print(f"changed_files={changed}")
print(f"replacements={replacements}")
