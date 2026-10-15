import ast
import os
import sys

class FullIntegrityVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.findings = []

    def visit_Assert(self, node):
        if isinstance(node.test, ast.Constant):
            self.findings.append((node.lineno, f"Constant assert: assert {node.test.value}"))
        elif isinstance(node.test, ast.Compare):
            if isinstance(node.test.left, ast.Constant):
                all_const = all(isinstance(c, ast.Constant) for c in node.test.comparators)
                if all_const:
                    self.findings.append((node.lineno, f"Trivial constant comparison assert"))
        self.generic_visit(node)

    def visit_Call(self, node):
        func_name = ""
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            func_name = node.func.id
        if func_name == "skip" and isinstance(node.func, ast.Attribute):
            val = getattr(node.func.value, 'id', '')
            if val == "pytest":
                self.findings.append((node.lineno, "pytest.skip() call"))
        self.generic_visit(node)

def scan_dir(root_dir):
    print(f"=== SCANNING DIRECTORY: {root_dir} ===")
    total = 0
    for root, dirs, files in os.walk(root_dir):
        for f in files:
            if f.endswith(".py") and ("test" in f or "tools" in root):
                fpath = os.path.join(root, f)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                    try:
                        tree = ast.parse(fp.read(), filename=fpath)
                    except Exception as e:
                        continue
                v = FullIntegrityVisitor(fpath)
                v.visit(tree)
                if v.findings:
                    # Filter out pre-existing known skips in legacy test files if any
                    rel = os.path.relpath(fpath, root_dir)
                    print(f"[{rel}]:")
                    for line, msg in v.findings:
                        print(f"  Line {line}: {msg}")
                        total += 1
    print(f"=== COMPLETED. Found {total} occurrences in {root_dir} ===")
    return total

if __name__ == "__main__":
    scan_dir(r"D:\scp\tests")
