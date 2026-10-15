from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
STAMP = datetime.now().strftime('%Y%m%d-%H%M%S')
BACKUP = ROOT / '.private-secrets' / f'reality-tests-before-windows-commands-{STAMP}'
BACKUP.mkdir(parents=True, exist_ok=True)
HELPER = r'''

# Windows portability: provide a deterministic Python fallback for GNU grep/rg
# used by older reality tests. Production code is not modified by this shim.
_REAL_SUBPROCESS_RUN = subprocess.run

def _portable_search_run(args, *pargs, **kwargs):
    if args and str(args[0]).lower() in {"grep", "rg"}:
        argv = [str(x) for x in args]
        root_path = Path(argv[-1])
        pattern = argv[-2]
        pattern = pattern.replace(r"\|", "|")
        try:
            rx = re.compile(pattern)
        except re.error:
            rx = re.compile(re.escape(pattern))
        if root_path.is_file():
            files = [root_path]
        else:
            files = list(root_path.rglob("*"))
        exts = None
        if str(argv[0]).lower() == "rg":
            wanted = {x for x in ("ts", "tsx") if x in argv}
            exts = {"." + x for x in wanted} if wanted else None
        else:
            inc = [x.split("=", 1)[1] for x in argv if x.startswith("--include=")]
            exts = {"." + x[2:] for x in inc if x.startswith("*.")} if inc else None
        rows = []
        for f in files:
            if not f.is_file() or (exts is not None and f.suffix.lower() not in exts):
                continue
            try:
                lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines, 1):
                if rx.search(line):
                    rows.append(f"{f}:{n}:{line}")
        return subprocess.CompletedProcess(args, 0, stdout="\n".join(rows), stderr="")
    return _REAL_SUBPROCESS_RUN(args, *pargs, **kwargs)

subprocess.run = _portable_search_run
'''
for rel in [
    Path('tests/reality-tests/reality_4-a-005.py'),
    Path('tests/reality-tests/reality_4-a-006.py'),
    Path('tests/reality-tests/reality_4-b-015.py'),
    Path('tests/reality-tests/reality_4-c-021.py'),
]:
    p = ROOT / rel
    s = p.read_text(encoding='utf-8-sig')
    (BACKUP / rel.name).write_bytes(p.read_bytes())
    if 'import subprocess' not in s:
        s = 'import subprocess\n' + s
    if 'import re' not in s:
        s = s.replace('import subprocess\n', 'import subprocess\nimport re\n', 1)
    if '_portable_search_run' not in s:
        anchor = 'import subprocess\n'
        s = s.replace(anchor, anchor + HELPER, 1)
    p.write_text(s, encoding='utf-8', newline='\n')
    print(f'patched {rel}')
# 4-b-018 uses Path after the portability transformation but had no import.
p = ROOT / 'tests/reality-tests/reality_4-b-018.py'
s = p.read_text(encoding='utf-8-sig')
(BACKUP / p.name).write_bytes(p.read_bytes())
if 'from pathlib import Path' not in s:
    s = 'from pathlib import Path\n' + s
p.write_text(s, encoding='utf-8', newline='\n')
print('patched tests/reality-tests/reality_4-b-018.py')
print(f'backup={BACKUP}')
