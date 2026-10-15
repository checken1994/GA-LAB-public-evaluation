import ast
import os
import re
import sys

project_root = r"D:\scp"

def parse_req_file(path):
    pkgs = set()
    if not os.path.exists(path):
        return pkgs
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                # strip markers and version specifiers
                p = re.split(r'[=<>~!;\s]', line)[0].strip().lower().replace("-", "_")
                if p:
                    pkgs.add(p)
    return pkgs

prod_reqs = parse_req_file(os.path.join(project_root, "scp", "requirements.txt"))
dev_reqs = parse_req_file(os.path.join(project_root, "scp", "requirements-dev.txt"))
otel_reqs = parse_req_file(os.path.join(project_root, "scp", "requirements-otel.txt"))
all_declared = prod_reqs | dev_reqs | otel_reqs

# Map package distribution names to import names
pkg_import_map = {
    "pyjwt": "jwt",
    "python_dotenv": "dotenv",
    "pywin32": "win32api",
    "pydantic_core": "pydantic_core",
    "pydantic_settings": "pydantic_settings",
    "uvicorn": "uvicorn",
    "fastapi": "fastapi",
    "starlette": "starlette",
    "httpx": "httpx",
    "requests": "requests",
    "cryptography": "cryptography",
    "defusedxml": "defusedxml",
    "psycopg": "psycopg",
    "tenacity": "tenacity",
    "slowapi": "slowapi",
    "prometheus_client": "prometheus_client",
    "pyyaml": "yaml",
    "pillow": "PIL",
    "beautifulsoup4": "bs4",
}
import_to_pkg = {v: k for k, v in pkg_import_map.items()}

# Collect all imports in scp/
scp_imports = set()
stdlib = sys.stdlib_module_names if hasattr(sys, "stdlib_module_names") else set()
local = {"scp", "tools", "tests", "data", "spec"}

for root, _, files in os.walk(os.path.join(project_root, "scp")):
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(root, f)
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fp:
                    tree = ast.parse(fp.read(), filename=p)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for n in node.names:
                            scp_imports.add(n.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.level == 0:
                            scp_imports.add(node.module.split(".")[0])
            except Exception:
                pass

third_party = {m for m in scp_imports if m not in stdlib and m not in local}

# Check which third_party imports are missing in requirements
missing = []
for m in sorted(third_party):
    pkg_name = import_to_pkg.get(m, m.replace("_", "-").lower())
    if pkg_name not in all_declared and m not in all_declared:
        missing.append((m, pkg_name))

print("Total third party imports in scp/:", len(third_party))
print("Missing in prod/dev/otel requirements:", len(missing))
for m, pkg in missing:
    print(f"  - Import '{m}' (expected package '{pkg}')")

import json
with open(r"D:\scp\.agents\explorer_survey_3\dep_analysis.json", "w", encoding="utf-8") as fp:
    json.dump({
        "prod_reqs": sorted(list(prod_reqs)),
        "third_party_imports": sorted(list(third_party)),
        "missing_dependencies": missing
    }, fp, indent=2)
