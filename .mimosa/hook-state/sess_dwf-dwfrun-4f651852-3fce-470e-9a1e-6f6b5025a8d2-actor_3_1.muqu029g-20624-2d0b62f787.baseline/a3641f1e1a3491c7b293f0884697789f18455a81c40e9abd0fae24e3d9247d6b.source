from pathlib import Path
from datetime import datetime
root=Path.cwd(); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); b=root/'.private-secrets'/f'reality-runner-before-cygpath-{stamp}'; b.mkdir(parents=True,exist_ok=True)
p=root/'tests'/'run-reality-tests.sh'
s=p.read_text(encoding='utf-8-sig'); (b/p.name).write_bytes(p.read_bytes())
marker='''run_python() {
  local target="$1"
  shift
  if command -v cygpath >/dev/null 2>&1; then
    target="$(cygpath -w "$target")"
  fi
  "$PYTHON_BIN" "$target" "$@"
}
'''
if 'run_python() {' not in s:
    s=s.replace('PYTHON_BIN="${SCP_PYTHON_BIN:-python3}"\n', 'PYTHON_BIN="${SCP_PYTHON_BIN:-python3}"\n'+marker)
s=s.replace('"$PYTHON_BIN" "$script"', 'run_python "$script"')
p.write_text(s,encoding='utf-8',newline='\n')
print(f'patched {p}; backup={b}')
