import ast
import os

project_root = r"D:\scp\scp"

dead_branches = []
duplicate_elifs = []
shadowed_vars = []
off_by_one_candidates = []

class DeepLogicVisitor(ast.NodeVisitor):
    def __init__(self, filename, lines):
        self.filename = filename
        self.lines = lines
        self.current_func = "<module>"

    def visit_FunctionDef(self, node):
        old_func = self.current_func
        self.current_func = node.name
        self._check_shadowing(node)
        self.generic_visit(node)
        self.current_func = old_func

    def visit_AsyncFunctionDef(self, node):
        old_func = self.current_func
        self.current_func = node.name
        self._check_shadowing(node)
        self.generic_visit(node)
        self.current_func = old_func

    def _check_shadowing(self, node):
        # Check if function arguments or outer assignments are shadowed in loops or inner blocks
        arg_names = {a.arg for a in node.args.args + node.args.kwonlyargs}
        for n in ast.walk(node):
            if isinstance(n, ast.For):
                target_names = set()
                if isinstance(n.target, ast.Name):
                    target_names.add(n.target.id)
                elif isinstance(n.target, (ast.Tuple, ast.List)):
                    for elt in n.target.elts:
                        if isinstance(elt, ast.Name):
                            target_names.add(elt.id)
                shadowed = target_names.intersection(arg_names)
                if shadowed:
                    shadowed_vars.append({
                        "file": self.filename,
                        "line": n.lineno,
                        "func": self.current_func,
                        "vars": list(shadowed),
                        "code": self.lines[n.lineno - 1].strip() if n.lineno <= len(self.lines) else ""
                    })

    def visit_If(self, node):
        # Check duplicate elif conditions in if-elif-else chain
        conditions = []
        curr = node
        while curr:
            cond_code = ast.unparse(curr.test) if hasattr(ast, "unparse") else ""
            if cond_code in conditions:
                duplicate_elifs.append({
                    "file": self.filename,
                    "line": curr.lineno,
                    "func": self.current_func,
                    "cond": cond_code,
                    "code": self.lines[curr.lineno - 1].strip() if curr.lineno <= len(self.lines) else ""
                })
            else:
                conditions.append(cond_code)
            if len(curr.orelse) == 1 and isinstance(curr.orelse[0], ast.If):
                curr = curr.orelse[0]
            else:
                break
        self.generic_visit(node)

    def visit_Subscript(self, node):
        # Slicing check: e.g. [0:len(x)-1] or [1:len(x)]
        if isinstance(node.slice, ast.Slice):
            sl = node.slice
            if sl.upper and isinstance(sl.upper, ast.BinOp):
                if isinstance(sl.upper.op, ast.Sub) and isinstance(sl.upper.right, ast.Constant) and sl.upper.right.value == 1:
                    # e.g., something[:-1] or [:len - 1]
                    code_line = self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
                    if "page" in code_line.lower() or "limit" in code_line.lower() or "offset" in code_line.lower() or "len" in code_line.lower():
                        off_by_one_candidates.append({
                            "file": self.filename,
                            "line": node.lineno,
                            "func": self.current_func,
                            "code": code_line
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
                visitor = DeepLogicVisitor(rel, lines)
                visitor.visit(tree)
            except Exception:
                pass

print(f"Duplicate elif conditions: {len(duplicate_elifs)}")
for d in duplicate_elifs:
    print(f"  {d['file']}:{d['line']} ({d['func']}) duplicate: {d['cond']}")

print(f"\nShadowed function arguments: {len(shadowed_vars)}")
for s in shadowed_vars:
    print(f"  {s['file']}:{s['line']} ({s['func']}) shadows {s['vars']}: {s['code']}")

print(f"\nOff-by-one pagination/slicing candidates: {len(off_by_one_candidates)}")
for o in off_by_one_candidates[:10]:
    print(f"  {o['file']}:{o['line']} ({o['func']}): {o['code']}")

import json
with open(r"D:\scp\.agents\explorer_survey_3\r1_deep_logic.json", "w", encoding="utf-8") as out:
    json.dump({
        "duplicate_elifs": duplicate_elifs,
        "shadowed_vars": shadowed_vars,
        "off_by_one": off_by_one_candidates
    }, out, indent=2)
