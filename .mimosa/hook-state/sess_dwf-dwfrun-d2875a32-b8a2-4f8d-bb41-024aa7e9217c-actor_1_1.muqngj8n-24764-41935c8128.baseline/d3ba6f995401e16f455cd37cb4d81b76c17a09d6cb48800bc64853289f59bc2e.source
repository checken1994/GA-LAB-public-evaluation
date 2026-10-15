import ast
import os

project_root = r"D:\scp\scp"
missing_encoding = []

class OpenVisitor(ast.NodeVisitor):
    def __init__(self, filename, lines):
        self.filename = filename
        self.lines = lines

    def visit_Call(self, node):
        # check open(...) or Path.open(...) or Path.read_text(...) or Path.write_text(...)
        is_open = False
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            is_open = True
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "open":
            is_open = True

        if is_open:
            # Check if 'b' is in mode
            is_binary = False
            if len(node.args) >= 2:
                mode_arg = node.args[1]
                if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str) and 'b' in mode_arg.value:
                    is_binary = True
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str) and 'b' in kw.value.value:
                    is_binary = True

            has_encoding = any(kw.arg == "encoding" for kw in node.keywords)
            if not is_binary and not has_encoding:
                missing_encoding.append({
                    "file": self.filename,
                    "line": node.lineno,
                    "code": self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
                })

        # Check read_text / write_text without encoding
        if isinstance(node.func, ast.Attribute) and node.func.attr in ("read_text", "write_text"):
            has_encoding = any(kw.arg == "encoding" for kw in node.keywords)
            if not has_encoding and len(node.args) == 0:
                missing_encoding.append({
                    "file": self.filename,
                    "line": node.lineno,
                    "code": self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
                })

        self.generic_visit(node)

for root, _, files in os.walk(project_root):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            rel = os.path.relpath(path, r"D:\scp")
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fp:
                    content = fp.read()
                tree = ast.parse(content, filename=path)
                lines = content.splitlines()
                visitor = OpenVisitor(rel, lines)
                visitor.visit(tree)
            except Exception:
                pass

print(f"File opens / read_text without explicit encoding: {len(missing_encoding)}")
for m in missing_encoding[:25]:
    print(f"  {m['file']}:{m['line']} -> {m['code']}")

import json
with open(r"D:\scp\.agents\explorer_survey_3\unencoded_opens.json", "w", encoding="utf-8") as out:
    json.dump(missing_encoding, out, indent=2)
