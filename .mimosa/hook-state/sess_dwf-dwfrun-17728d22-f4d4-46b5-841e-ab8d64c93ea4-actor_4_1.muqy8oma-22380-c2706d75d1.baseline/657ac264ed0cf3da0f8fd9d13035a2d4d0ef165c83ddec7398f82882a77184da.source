import ast
import os
import sys

project_root = r"D:\scp\scp"

results = {
    "swallowed_exceptions": [],
    "mutable_defaults": [],
    "literal_is_comparisons": [],
    "dead_branches": [],
    "suspicious_none_comparisons": [],
    "unawaited_async_calls": [],
}

def check_file(filepath):
    rel_path = os.path.relpath(filepath, r"D:\scp")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
        return

    try:
        tree = ast.parse(code, filename=filepath)
    except Exception as e:
        return

    lines = code.splitlines()

    class R1Visitor(ast.NodeVisitor):
        def __init__(self):
            self.async_function_names = set()
            super().__init__()

        def visit_FunctionDef(self, node):
            self._check_defaults(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            self.async_function_names.add(node.name)
            self._check_defaults(node)
            self.generic_visit(node)

        def _check_defaults(self, node):
            for default in node.args.defaults + node.args.kw_defaults:
                if default is None:
                    continue
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    results["mutable_defaults"].append({
                        "file": rel_path,
                        "line": default.lineno,
                        "func": node.name,
                        "snippet": lines[default.lineno - 1] if default.lineno <= len(lines) else ""
                    })

        def visit_Try(self, node):
            for handler in node.handlers:
                # Check if handler body only has pass or return None/empty
                is_swallowed = False
                has_logging = False
                for stmt in handler.body:
                    # check for logger/logging/print
                    for sub in ast.walk(stmt):
                        if isinstance(sub, ast.Name) and any(x in sub.id.lower() for x in ["log", "logger", "print"]):
                            has_logging = True
                        elif isinstance(sub, ast.Attribute) and any(x in sub.attr.lower() for x in ["log", "logger", "error", "warning", "info", "exception", "debug"]):
                            has_logging = True

                if not has_logging:
                    # if body is just pass
                    if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                        is_swallowed = True
                    # or if body is return None / return / return empty
                    elif len(handler.body) == 1 and isinstance(handler.body[0], ast.Return):
                        val = handler.body[0].value
                        if val is None or (isinstance(val, ast.Constant) and val.value in (None, "", False, 0, [], {})):
                            is_swallowed = True
                    # or if all statements are pass or return default
                    elif all(isinstance(s, (ast.Pass, ast.Return)) for s in handler.body):
                        is_swallowed = True

                if is_swallowed:
                    exc_type = "bare"
                    if handler.type:
                        exc_type = ast.unparse(handler.type)
                    results["swallowed_exceptions"].append({
                        "file": rel_path,
                        "line": handler.lineno,
                        "type": exc_type,
                        "snippet": lines[handler.lineno - 1] if handler.lineno <= len(lines) else ""
                    })

            self.generic_visit(node)

        def visit_Compare(self, node):
            for op, right in zip(node.ops, node.comparators):
                # Is or IsNot with literal (str, int, float, list, dict)
                if isinstance(op, (ast.Is, ast.IsNot)):
                    if isinstance(right, ast.Constant) and right.value is not None:
                        results["literal_is_comparisons"].append({
                            "file": rel_path,
                            "line": node.lineno,
                            "snippet": lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                        })
                    elif isinstance(node.left, ast.Constant) and node.left.value is not None:
                        results["literal_is_comparisons"].append({
                            "file": rel_path,
                            "line": node.lineno,
                            "snippet": lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                        })
            self.generic_visit(node)

        def visit_If(self, node):
            # Check for constant condition
            if isinstance(node.test, ast.Constant):
                results["dead_branches"].append({
                    "file": rel_path,
                    "line": node.lineno,
                    "detail": f"Constant condition: {node.test.value}",
                    "snippet": lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                })
            self.generic_visit(node)

    visitor = R1Visitor()
    visitor.visit(tree)

for root, dirs, files in os.walk(project_root):
    for f in files:
        if f.endswith(".py"):
            check_file(os.path.join(root, f))

print(f"Swallowed exceptions: {len(results['swallowed_exceptions'])}")
print(f"Mutable defaults: {len(results['mutable_defaults'])}")
print(f"Literal is comparisons: {len(results['literal_is_comparisons'])}")
print(f"Dead branches (constant if): {len(results['dead_branches'])}")

import json
with open(r"D:\scp\.agents\explorer_survey_3\r1_ast_results.json", "w", encoding="utf-8") as out:
    json.dump(results, out, indent=2)
print("Saved to r1_ast_results.json")
