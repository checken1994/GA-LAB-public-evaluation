"""
scripts/check_imports_vs_requirements.py
========================================
Quét tất cả file .py trong scp/ và các file khởi động.
Trích xuất top-level imports và đối chiếu với requirements.txt.

DNA #2 — Vòng lặp khép kín: mọi import mới phải được phản ánh vào manifest.
Fail CI nếu có thư viện external được import nhưng thiếu trong requirements.txt.
"""
import ast
import re
import sys
from pathlib import Path

# Thư viện chuẩn Python (không cần trong requirements.txt)
STDLIB = sys.stdlib_module_names

def get_imports_from_file(file_path: Path) -> set[str]:
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(name.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                imports.add(node.module.split('.')[0])
    return imports

def get_requirements(req_path: Path) -> set[str]:
    if not req_path.exists():
        return set()
    reqs = set()
    # Các package name có thể khác import name, ánh xạ phổ biến:
    pkg_to_import = {
        "python-dotenv": "dotenv",
        "python-multipart": "multipart",
        "python-jose": "jose",
        "prometheus-client": "prometheus_client",
        "opentelemetry-api": "opentelemetry",
        "opentelemetry-sdk": "opentelemetry",
        "opentelemetry-instrumentation-fastapi": "opentelemetry",
        "pyjwt": "jwt",
        "pywin32": "win32api",
        "pywin32 ": "win32con",
        "pywin32  ": "win32job",
        "pywin32   ": "win32process",
        "pillow": "pil",
        "openai-whisper": "whisper",
        "pyyaml": "yaml",
    }
    
    for line in req_path.read_text(encoding="utf-8").splitlines():
        line = line.split('#')[0].strip()
        if not line:
            continue
        pkg_name = re.split(r'[=><\[]', line)[0].strip().lower()
        
        # Match reverse direction for pywin32 which has multiple imports
        if pkg_name == "pywin32":
            reqs.update([
                "win32api", "win32con", "win32job", "win32process",
                "pywintypes", "win32event", "win32file", "win32pipe",
            ])
            continue
        if pkg_name == "pillow":
            reqs.add("pil")
            continue
            
        if pkg_name in pkg_to_import:
            reqs.add(pkg_to_import[pkg_name])
        else:
            reqs.add(pkg_name.replace('-', '_'))
    return reqs

def main():
    root = Path(__file__).parent.parent
    scp_dir = root / "scp"
    req_file = scp_dir / "requirements.txt"

    if not scp_dir.exists() or not req_file.exists():
        print(f"Error: {scp_dir} or {req_file} not found.")
        sys.exit(1)

    reqs = set()
    for req_file in scp_dir.glob("requirements*.txt"):
        reqs.update(get_requirements(req_file))
    for req_file in (scp_dir / "scp").glob("requirements*.txt"):
        reqs.update(get_requirements(req_file))
    # Các module local hoặc stdlib không có trên PyPI
    local_modules = {
        "scp", "tests", "benchmark", "scripts", "task_kernel", "trace_ledger", "conftest",
        "question_generator", # from benchmark
    }
    
    all_imports = set()
    for py_file in scp_dir.rglob("*.py"):
        if "venv" in py_file.parts or ".venv" in py_file.parts or "node_modules" in py_file.parts:
            continue
        # Bỏ qua cả thư mục rác cũ nếu có
        if "archived_workspaces" in py_file.parts:
            continue
        all_imports.update(get_imports_from_file(py_file))

    reqs_lower = {r.lower() for r in reqs}
    missing = []
    for imp in sorted(all_imports):
        # Bỏ qua stdlib, local modules, và private names
        if imp in STDLIB or imp in local_modules or imp.startswith("_"):
            continue
        if imp.lower() not in reqs_lower:
            missing.append(imp)

    if missing:
        print("="*60)
        print("[FAIL] Missing dependencies in requirements.txt:")
        for m in missing:
            print(f"  - {m}")
        print("="*60)
        print("Please add these libraries to scp/requirements.txt.")
        sys.exit(1)
    
    print("[PASS] All external imports match requirements.txt")
    sys.exit(0)

if __name__ == "__main__":
    main()
