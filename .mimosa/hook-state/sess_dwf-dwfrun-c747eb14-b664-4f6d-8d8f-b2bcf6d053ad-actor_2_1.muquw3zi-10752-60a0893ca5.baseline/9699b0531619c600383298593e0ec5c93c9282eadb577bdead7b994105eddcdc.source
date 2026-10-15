import ast
import os
import re
import sys

project_root = r"D:\scp"
scp_dir = os.path.join(project_root, "scp")

# 1. Environment variables in code
env_vars_used = set()
env_var_locations = {} # var -> list of (file, line)

for root, _, files in os.walk(scp_dir):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            rel = os.path.relpath(path, project_root)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fp:
                    content = fp.read()
                lines = content.splitlines()
                # regex for os.environ, os.getenv
                for m in re.finditer(r'(?:os\.environ\.get|os\.getenv)\s*\(\s*["\']([A-Za-z0-9_]+)["\']', content):
                    var = m.group(1)
                    lineno = content[:m.start()].count('\n') + 1
                    env_vars_used.add(var)
                    env_var_locations.setdefault(var, []).append((rel, lineno))
                for m in re.finditer(r'os\.environ\[\s*["\']([A-Za-z0-9_]+)["\']\s*\]', content):
                    var = m.group(1)
                    lineno = content[:m.start()].count('\n') + 1
                    env_vars_used.add(var)
                    env_var_locations.setdefault(var, []).append((rel, lineno))
                for m in re.finditer(r'os\.environ\.setdefault\s*\(\s*["\']([A-Za-z0-9_]+)["\']', content):
                    var = m.group(1)
                    lineno = content[:m.start()].count('\n') + 1
                    env_vars_used.add(var)
                    env_var_locations.setdefault(var, []).append((rel, lineno))
            except Exception:
                pass

# Read .env.example
env_example_path = os.path.join(project_root, ".env.example")
env_example_vars = set()
if os.path.exists(env_example_path):
    with open(env_example_path, "r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                var = line.split("=")[0].strip()
                env_example_vars.add(var)

undocumented_env_vars = env_vars_used - env_example_vars
unused_example_vars = env_example_vars - env_vars_used

# 2. Hardcoded ports
ports_found = []
for root, _, files in os.walk(scp_dir):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            rel = os.path.relpath(path, project_root)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fp:
                    lines = fp.splitlines()
                for i, line in enumerate(lines, 1):
                    # match port numbers in urls or bind calls: :8000, port=8000, etc.
                    for m in re.finditer(r'(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d{4,5})|port\s*=\s*(\d{4,5})|PORT\s*=\s*(\d{4,5})', line):
                        port = m.group(1) or m.group(2) or m.group(3)
                        ports_found.append({
                            "file": rel,
                            "line": i,
                            "port": port,
                            "code": line.strip()
                        })
            except Exception:
                pass

# 3. Check requirements.txt vs imports
req_file = os.path.join(project_root, "requirements.txt")
declared_pkgs = set()
if os.path.exists(req_file):
    with open(req_file, "r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                pkg = re.split(r'[=<>~!]', line)[0].strip().lower().replace("-", "_")
                declared_pkgs.add(pkg)

# Find top-level imports in scp/
top_level_imports = set()
for root, _, files in os.walk(scp_dir):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fp:
                    tree = ast.parse(fp.read(), filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            top_level_imports.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.level == 0:
                            top_level_imports.add(node.module.split(".")[0])
            except Exception:
                pass

# Standard library modules in Python 3.12
stdlib = sys.stdlib_module_names if hasattr(sys, "stdlib_module_names") else set()
local_modules = {"scp", "tools", "tests"}

third_party_imports = {pkg for pkg in top_level_imports if pkg not in stdlib and pkg not in local_modules}

output = {
    "env_vars_used_count": len(env_vars_used),
    "env_example_vars_count": len(env_example_vars),
    "undocumented_env_vars": sorted(list(undocumented_env_vars)),
    "unused_example_vars": sorted(list(unused_example_vars)),
    "hardcoded_ports_count": len(ports_found),
    "unique_ports": sorted(list({p["port"] for p in ports_found})),
    "third_party_imported": sorted(list(third_party_imports)),
    "declared_requirements": sorted(list(declared_pkgs)),
    "undeclared_dependencies": sorted(list(third_party_imports - declared_pkgs)),
    "unused_requirements": sorted(list(declared_pkgs - third_party_imports))
}

import json
with open(r"D:\scp\.agents\explorer_survey_3\r6_config_results.json", "w", encoding="utf-8") as fp:
    json.dump(output, fp, indent=2)

print(f"Env vars used: {len(env_vars_used)}, In .env.example: {len(env_example_vars)}")
print(f"Undocumented env vars: {len(undocumented_env_vars)}")
print(f"Hardcoded port instances: {len(ports_found)}, Unique ports: {output['unique_ports']}")
print(f"Third party imports: {len(third_party_imports)}, Declared in requirements: {len(declared_pkgs)}")
print(f"Undeclared dependencies: {len(output['undeclared_dependencies'])}")
print("Undeclared dependencies sample:", output['undeclared_dependencies'][:15])
