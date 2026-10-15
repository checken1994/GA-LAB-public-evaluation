import ast
import os
import sys

TARGET_FILES = [
    r"D:\scp\scp\capabilities\tools.py",
    r"D:\scp\scp\core\autonomous_ledger.py",
    r"D:\scp\scp\policy\egress.py",
    r"D:\scp\scp\web_control\playwright_backend.py",
    r"D:\scp\tests\T01_boot\test_live_cluster_e2e.py",
    r"D:\scp\tests\T01_boot\test_startup_launcher_contract.py",
    r"D:\scp\tests\T03_capability\test_autonomous_tool_contracts.py",
    r"D:\scp\tests\T03_capability\test_egress_policy_unified.py",
    r"D:\scp\tests\T04_kernel\test_autonomous_audit_ledger_provenance.py",
    r"D:\scp\tests\test_concurrency_stress_v2.py",
    r"D:\scp\tests\test_epistemic_functional.py",
    r"D:\scp\tests\test_observability_functional.py",
    r"D:\scp\tests\test_self_model_behavioral.py",
    r"D:\scp\tests\test_task_kernel_stress.py",
    r"D:\scp\tools\adversarial_goal3_probe.py",
    r"D:\scp\tools\e2e_live_cluster_verifier.py",
]

class IntegrityVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.findings = []

    def visit_Assert(self, node):
        # Check assert True / assert False / assert constant
        if isinstance(node.test, ast.Constant):
            self.findings.append((node.lineno, f"Constant assert: assert {node.test.value}"))
        elif isinstance(node.test, ast.Compare):
            if isinstance(node.test.left, ast.Constant):
                all_const = all(isinstance(c, ast.Constant) for c in node.test.comparators)
                if all_const:
                    self.findings.append((node.lineno, f"Trivial constant comparison assert"))
        self.generic_visit(node)

    def visit_Call(self, node):
        # Check pytest.skip()
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

    def visit_FunctionDef(self, node):
        # Check decorators for skip / xfail
        for deco in node.decorator_list:
            deco_str = ast.dump(deco)
            if "skip" in deco_str or "xfail" in deco_str:
                self.findings.append((node.lineno, f"Skip/xfail decorator: {deco_str}"))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

def scan():
    total_findings = 0
    print("=== STARTING AST INTEGRITY SCAN ON COMMIT 0bed14c FILES ===")
    for fpath in TARGET_FILES:
        if not os.path.exists(fpath):
            print(f"[ERROR] File not found: {fpath}")
            total_findings += 1
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read(), filename=fpath)
            except Exception as e:
                print(f"[PARSE ERROR] {fpath}: {e}")
                total_findings += 1
                continue
        visitor = IntegrityVisitor(fpath)
        visitor.visit(tree)
        if visitor.findings:
            print(f"[FINDINGS in {os.path.basename(fpath)}]:")
            for line, msg in visitor.findings:
                print(f"  Line {line}: {msg}")
                total_findings += 1
        else:
            print(f"[CLEAN] {os.path.basename(fpath)}")

    print(f"\n=== AST SCAN COMPLETE: Total Suspicious Patterns = {total_findings} ===")
    return total_findings

if __name__ == "__main__":
    sys.exit(scan())
