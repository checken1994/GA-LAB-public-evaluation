import ast
import os
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# 1. Parse .env.example
with open('.env.example', 'r', encoding='utf-8') as f:
    env_example_text = f.read()

example_keys = set()
for line in env_example_text.splitlines():
    line = line.strip()
    m = re.match(r'^(?:#\s*)?([A-Za-z_][A-Za-z0-9_]*)=', line)
    if m:
        example_keys.add(m.group(1))

print(f"Keys already in .env.example: {len(example_keys)}")

# 2. Extract from scp/ using AST and regex
all_found = defaultdict(list)

# AST extraction
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
                        if re.match(r'^[A-Z0-9_]+$', key):
                            all_found[key].append((path, node.lineno))

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
                        if re.match(r'^[A-Z0-9_]+$', key):
                            all_found[key].append((path, node.lineno))

# Also regex pass for anything missed
regex = re.compile(r"""(?:os\.environ\[|os\.environ\.get\(|os\.getenv\(|os\.environ\.setdefault\()\s*["']([A-Z0-9_]+)["']""")
for root, dirs, files in os.walk('scp'):
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                for lineno, line in enumerate(fp, 1):
                    for m in regex.finditer(line):
                        k = m.group(1)
                        if (path, lineno) not in all_found[k]:
                            all_found[k].append((path, lineno))
        except Exception:
            continue

print(f"Total distinct env vars in scp/: {len(all_found)}")

missing = sorted([k for k in all_found if k not in example_keys])
print(f"Missing from .env.example: {len(missing)}")

# Group missing by subsystem
by_subsystem = defaultdict(dict)
for k in missing:
    occurrences = all_found[k]
    # pick primary subsystem from first occurrence path
    first_path = occurrences[0][0].replace('\\', '/')
    parts = first_path.split('/')
    if len(parts) >= 2:
        if parts[1].endswith('.py'):
            subsystem = 'root (' + parts[1] + ')'
        else:
            subsystem = parts[1]
    else:
        subsystem = 'other'
    by_subsystem[subsystem][k] = occurrences

print("\nMissing env vars grouped by subsystem:")
for sub, keys in sorted(by_subsystem.items()):
    print(f"\n### Subsystem: {sub} ({len(keys)} vars)")
    for k, occs in sorted(keys.items()):
        locs = ', '.join(f"{p}:{l}" for p, l in occs[:3])
        if len(occs) > 3:
            locs += f" (+{len(occs)-3} more)"
        print(f"  - `{k}`: {locs}")
