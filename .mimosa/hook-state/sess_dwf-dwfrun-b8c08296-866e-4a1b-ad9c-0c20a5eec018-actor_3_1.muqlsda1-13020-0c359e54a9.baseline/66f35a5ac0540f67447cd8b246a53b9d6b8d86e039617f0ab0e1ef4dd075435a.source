import ast
import os
import re

scp_dir = r"D:\scp\scp"

# 1. Bare excepts
bare_excepts = []
swallowed_excepts = []
async_defs = set()
calls = []

class AuditVisitor(ast.NodeVisitor):
    def __init__(self, filename, lines):
        self.filename = filename
        self.lines = lines
        self.in_try = False
        self.current_func = None
        self.is_async_func = False

    def visit_AsyncFunctionDef(self, node):
        async_defs.add(node.name)
        old_func = self.current_func
        old_async = self.is_async_func
        self.current_func = node.name
        self.is_async_func = True
        self.generic_visit(node)
        self.current_func = old_func
        self.is_async_func = old_async

    def visit_FunctionDef(self, node):
        old_func = self.current_func
        old_async = self.is_async_func
        self.current_func = node.name
        self.is_async_func = False
        self.generic_visit(node)
        self.current_func = old_func
        self.is_async_func = old_async

    def visit_Try(self, node):
        for h in node.handlers:
            # Check bare except
            if h.type is None:
                bare_excepts.append({
                    "file": self.filename,
                    "line": h.lineno,
                    "func": self.current_func,
                    "code": self.lines[h.lineno - 1].strip() if h.lineno <= len(self.lines) else ""
                })
            # Check swallowed
            # check if body has any logging/print/raise
            has_raise = any(isinstance(s, ast.Raise) for s in h.body)
            has_log = False
            for s in h.body:
                for sub in ast.walk(s):
                    if isinstance(sub, ast.Name) and sub.id.lower() in ("logger", "log", "print", "logging"):
                        has_log = True
                    elif isinstance(sub, ast.Attribute) and sub.attr.lower() in ("warning", "error", "exception", "critical", "info", "debug"):
                        has_log = True

            if not has_raise and not has_log:
                # does it just pass or return?
                body_types = [type(s) for s in h.body]
                if all(t in (ast.Pass, ast.Return, ast.Assign) for t in body_types):
                    swallowed_excepts.append({
                        "file": self.filename,
                        "line": h.lineno,
                        "func": self.current_func,
                        "type": ast.unparse(h.type) if h.type else "bare except",
                        "body": [self.lines[s.lineno - 1].strip() for s in h.body if s.lineno <= len(self.lines)]
                    })
        self.generic_visit(node)

for root, _, files in os.walk(scp_dir):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            rel = os.path.relpath(path, r"D:\scp")
            try:
                with open(path, "r", encoding="utf-8") as fp:
                    content = fp.read()
                tree = ast.parse(content, filename=path)
                lines = content.splitlines()
                visitor = AuditVisitor(rel, lines)
                visitor.visit(tree)
            except Exception as e:
                pass

print(f"Bare excepts found: {len(bare_excepts)}")
for b in bare_excepts:
    print(f"  {b['file']}:{b['line']} in {b['func']} -> {b['code']}")

print(f"\nSwallowed excepts found: {len(swallowed_excepts)}")
for s in swallowed_excepts[:20]:
    print(f"  {s['file']}:{s['line']} in {s['func']} ({s['type']}) -> {s['body']}")

import json
with open(r"D:\scp\.agents\explorer_survey_3\r1_swallowed.json", "w", encoding="utf-8") as out:
    json.dump({"bare": bare_excepts, "swallowed": swallowed_excepts}, out, indent=2)
