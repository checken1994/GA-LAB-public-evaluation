import ast
import os
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

with open('.env.example', 'r', encoding='utf-8') as f:
    env_example_text = f.read()

example_keys = set()
for line in env_example_text.splitlines():
    line = line.strip()
    m = re.match(r'^(?:#\s*)?([A-Za-z_][A-Za-z0-9_]*)=', line)
    if m:
        example_keys.add(m.group(1))

# AST extraction ONLY
ast_vars = defaultdict(list)

for root, dirs, files in os.walk('scp'):
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                content = fp.read()
            tree = ast.parse(content, filename=path)
        except Exception:
            continue

        for node in ast.walk(tree):
            key = None
            default_val = None

            # os.getenv(...) or getenv(...) or os.environ.get(...) or environ.get(...)
            if isinstance(node, ast.Call):
                func = node.func
                is_env = False
                if isinstance(func, ast.Attribute) and func.attr in ('getenv', 'get', 'setdefault'):
                    if isinstance(func.value, ast.Name) and func.value.id in ('os', 'environ'):
                        is_env = True
                    elif isinstance(func.value, ast.Attribute) and func.value.attr == 'environ':
                        is_env = True
                elif isinstance(func, ast.Name) and func.id == 'getenv':
                    is_env = True

                if is_env and node.args:
                    arg0 = node.args[0]
                    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                        key = arg0.value
                        if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                            default_val = node.args[1].value

            elif isinstance(node, ast.Subscript):
                val = node.value
                is_env = False
                if isinstance(val, ast.Name) and val.id == 'environ':
                    is_env = True
                elif isinstance(val, ast.Attribute) and val.attr == 'environ':
                    is_env = True

                if is_env:
                    sl = node.slice
                    if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                        key = sl.value

            if key and re.match(r'^[A-Z0-9_]+$', key):
                ast_vars[key].append({
                    'file': path.replace('\\', '/'),
                    'line': node.lineno,
                    'default': default_val
                })

os_vars = {'SYSTEMROOT', 'TEMP', 'TMP', 'LOCALAPPDATA', 'PROGRAMFILES'}
missing_from_env = sorted([k for k in ast_vars if k not in example_keys and k not in os_vars])

print(f"Total AST-verified distinct env vars in scp/: {len(ast_vars)}")
print(f"Already in .env.example: {len(example_keys)}")
print(f"OS-level variables: {len([k for k in ast_vars if k in os_vars])}")
print(f"Total missing application env vars: {len(missing_from_env)}")

# Print all missing grouped by subsystem
by_sub = defaultdict(list)
for k in missing_from_env:
    first_file = ast_vars[k][0]['file']
    parts = first_file.split('/')
    sub = parts[1] if not parts[1].endswith('.py') else 'root'
    by_sub[sub].append(k)

print("\nBreakdown by Subsystem:")
for sub, vars_list in sorted(by_sub.items()):
    print(f"  - {sub} ({len(vars_list)}):")
    for v in sorted(vars_list):
        defaults = [x['default'] for x in ast_vars[v] if x['default'] is not None]
        def_str = repr(defaults[0]) if defaults else "NONE"
        loc = f"{ast_vars[v][0]['file']}:{ast_vars[v][0]['line']}"
        print(f"      {v:40} default={def_str:20} ({loc})")
