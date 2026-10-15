import ast
import os
import re

project_root = r"D:\scp\scp"

# First, collect all async function names across scp/
async_funcs = {} # func_name -> set of filepaths

for root, _, files in os.walk(project_root):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            rel = os.path.relpath(path, r"D:\scp")
            try:
                with open(path, "r", encoding="utf-8") as fp:
                    content = fp.read()
                tree = ast.parse(content, filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.AsyncFunctionDef):
                        async_funcs.setdefault(node.name, set()).add(rel)
            except Exception:
                pass

print(f"Total async functions indexed: {len(async_funcs)}")

# Now scan for:
# 1. Calls to known async functions not wrapped in await or create_task
# 2. asyncio.create_task calls without error handling
# 3. Off-by-one in pagination/slice
# 4. str vs int comparisons

findings = {
    "fire_and_forget_tasks": [],
    "unawaited_async_calls": [],
    "pagination_off_by_one": [],
    "str_int_comparisons": [],
}

class LogicAuditVisitor(ast.NodeVisitor):
    def __init__(self, filename, lines):
        self.filename = filename
        self.lines = lines
        self.in_async_func = False
        self.current_func = "<module>"

    def visit_AsyncFunctionDef(self, node):
        old_func = self.current_func
        old_async = self.in_async_func
        self.current_func = node.name
        self.in_async_func = True
        self.generic_visit(node)
        self.current_func = old_func
        self.in_async_func = old_async

    def visit_FunctionDef(self, node):
        old_func = self.current_func
        old_async = self.in_async_func
        self.current_func = node.name
        self.in_async_func = False
        self.generic_visit(node)
        self.current_func = old_func
        self.in_async_func = old_async

    def visit_Call(self, node):
        # Check asyncio.create_task
        func_name = ""
        if isinstance(node.func, ast.Attribute) and node.func.attr == "create_task":
            # Check if assigned to variable or callback added
            # If it's an Expr(Call(...)), it is a pure fire-and-forget!
            findings["fire_and_forget_tasks"].append({
                "file": self.filename,
                "line": node.lineno,
                "func": self.current_func,
                "code": self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
            })
        self.generic_visit(node)

    def visit_Expr(self, node):
        # Expression statement: if it is a Call to an async function without await!
        if isinstance(node.value, ast.Call):
            call_node = node.value
            target_name = None
            if isinstance(call_node.func, ast.Name):
                target_name = call_node.func.id
            elif isinstance(call_node.func, ast.Attribute):
                target_name = call_node.func.attr

            if target_name and target_name in async_funcs:
                # If target is known async, and not awaited!
                findings["unawaited_async_calls"].append({
                    "file": self.filename,
                    "line": node.lineno,
                    "func": self.current_func,
                    "callee": target_name,
                    "code": self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
                })
        self.generic_visit(node)

    def visit_Compare(self, node):
        # Check comparison between str and int literals
        left = node.left
        for comp in node.comparators:
            if isinstance(left, ast.Constant) and isinstance(comp, ast.Constant):
                if (isinstance(left.value, str) and isinstance(comp.value, int)) or \
                   (isinstance(left.value, int) and isinstance(comp.value, str)):
                    findings["str_int_comparisons"].append({
                        "file": self.filename,
                        "line": node.lineno,
                        "func": self.current_func,
                        "code": self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
                    })
        self.generic_visit(node)

for root, _, files in os.walk(project_root):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            rel = os.path.relpath(path, r"D:\scp")
            try:
                with open(path, "r", encoding="utf-8") as fp:
                    content = fp.read()
                tree = ast.parse(content, filename=path)
                lines = content.splitlines()
                visitor = LogicAuditVisitor(rel, lines)
                visitor.visit(tree)
            except Exception:
                pass

print(f"Fire-and-forget create_task: {len(findings['fire_and_forget_tasks'])}")
print(f"Potential unawaited async calls: {len(findings['unawaited_async_calls'])}")
print(f"Str vs int comparisons: {len(findings['str_int_comparisons'])}")

import json
with open(r"D:\scp\.agents\explorer_survey_3\r1_logic_results.json", "w", encoding="utf-8") as out:
    json.dump(findings, out, indent=2)
