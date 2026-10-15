"""Fix silent `except` blocks flagged by census_silent_except.py (S-B1c).

Behavior-preserving fail-loudly pass: inserts a logging call as the FIRST
statement of each SILENT handler found in the census JSON.  Level policy:
  warning - bare except or except Exception/BaseException (may hide real bugs)
  debug   - narrow expected exception types (designed fallback paths)

Also injects a module-level ``logger = logging.getLogger(__name__)`` when the
file has no reusable logger.  Preserves each file's CRLF/LF endings.

Usage:
  python scripts/diagnostics/fix_silent_except_sb1c.py \
      --census reports/expert-panel/S-B1c-census-baseline.json \
      --scope scp/security [--dry-run]
"""
import argparse
import ast
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANDIDATE_LOGGER_NAMES = ("logger", "log", "_logger", "tlog", "audit_log", "_log")
BROAD_EXC = {"Exception", "BaseException", "bare-except"}


def split_top_level_colon(text):
    """Split at the first ':' outside brackets/strings -> (head, tail)."""
    depth = 0
    in_str = None
    esc = False
    for i, c in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == in_str:
                in_str = None
        elif c in "\"'":
            in_str = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ":" and depth == 0:
            return text[:i], text[i + 1:]
    return None, None


def find_top_level_keyword(text, kw):
    """Index of first top-level (outside brackets/strings) whole-word `kw`."""
    depth = 0
    in_str = None
    esc = False
    pat = re.compile(r"\b%s\b" % kw)
    for i, c in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == in_str:
                in_str = None
        elif c in "\"'":
            in_str = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0:
            m = pat.match(text, i)
            if m:
                return i
    return -1


def enclosing_name(tree, lineno):
    chain = []

    def rec(node, names):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if ch.lineno <= lineno <= (ch.end_lineno or ch.lineno):
                    new = names + [ch.name]
                    if len(new) > len(chain):
                        chain[:] = new
                    rec(ch, new)
            else:
                rec(ch, names)

    rec(tree, [])
    return ".".join(chain) if chain else "<module>"


def short_exc(exc_desc):
    s = exc_desc.strip()
    if s == "bare-except":
        return "exception"
    return s.replace("(", "").replace(")", "").strip()


def compose_log(level, func, exc_desc, exc_name):
    msg = "%s: %s %s" % (func, short_exc(exc_desc), "not handled" if level == "warning" else "ignored")
    if exc_name:
        return "logger.%s('%s: %%s', %s)" % (level, msg, exc_name)
    return "logger.%s('%s', exc_info=True)" % (level, msg)


def logger_info(tree, src):
    """Return (logger_name_or_None, inject_at_1based_or_None, need_import)."""
    assigns = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    try:
                        assigns[t.id] = ast.unparse(node.value)
                    except Exception:
                        assigns[t.id] = ""
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            try:
                assigns[node.target.id] = ast.unparse(node.value) if node.value else ""
            except Exception:
                pass
        elif isinstance(node, ast.ImportFrom) and node.module == "loguru":
            if any(a.name == "logger" for a in node.names):
                return "logger", None, False
    for nm in CANDIDATE_LOGGER_NAMES:
        if nm in assigns and ("getLogger" in assigns[nm] or "get_logger" in assigns[nm]):
            return nm, None, False
    name = "logger" if "logger" not in assigns else "_sb1c_logger"
    last_import_end = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last_import_end = max(last_import_end, node.end_lineno or 0)
    if not last_import_end:
        if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
            last_import_end = tree.body[0].end_lineno or 0
    need_import = re.search(r"^import logging\b", src, re.M) is None
    return name, last_import_end, need_import


def fix_file(rel_path, targets, dry_run):
    path = REPO / rel_path
    data = path.read_bytes().decode("utf-8")
    raw = data.split("\n")  # elements may carry trailing '\r'
    tree = ast.parse(data)

    handlers = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for h in node.handlers:
                handlers.setdefault(h.lineno, h)

    log_name, inject_at, need_import = logger_info(tree, data)

    # 1) module logger injection FIRST (top of file) so handler line numbers
    #    only need a single uniform shift afterwards.
    shift = 0
    if inject_at is not None:
        style = ""
        if inject_at < len(raw) and raw[inject_at].endswith("\r"):
            style = "\r"
        inj = [""]
        if need_import:
            inj.append("import logging")
        inj.append("%s = logging.getLogger(__name__)" % log_name)
        inj.append("")
        raw[inject_at:inject_at] = [seg + style for seg in inj]
        shift = len(inj)

    def pos(orig_line):
        return orig_line - 1 + (shift if inject_at is not None and orig_line > inject_at else 0)

    # 2) handler edits, descending line order so earlier positions stay valid.
    changed = 0
    for t in sorted(targets, key=lambda r: -r["line"]):
        h = handlers.get(t["line"])
        if h is None:
            print("  !! handler not found %s:%s" % (rel_path, t["line"]))
            continue
        level = "warning" if t["exc"] in BROAD_EXC else "debug"
        func = enclosing_name(tree, h.lineno)
        code = compose_log(level, func, t["exc"], h.name)

        idx = pos(h.lineno)
        line = raw[idx]
        eol = "\r" if line.endswith("\r") else ""
        core = line.rstrip("\r")
        hindent = re.match(r"^[\t ]*", core).group(0)
        body0 = h.body[0]
        one_liner = body0.lineno == h.lineno
        pass_only = len(h.body) == 1 and isinstance(body0, ast.Pass)

        if one_liner:
            stripped = core.lstrip()
            kwx = find_top_level_keyword(stripped, "except")
            head = None
            if kwx >= 0:
                head, tail = split_top_level_colon(stripped[kwx:])
            if kwx < 0 or head is None:
                print("  !! cannot split one-liner %s:%s" % (rel_path, t["line"]))
                continue
            prefix = stripped[:kwx].rstrip()
            bindent = hindent + "    "
            out = [hindent + prefix] if prefix else []
            out.append(hindent + head.rstrip() + ":")
            rest = tail.strip()
            if pass_only:
                m = re.match(r"^pass\b(.*)$", rest)
                rest_comment = m.group(1).strip() if m else ""
                out.append(bindent + code + (("  " + rest_comment) if rest_comment else ""))
            else:
                out.append(bindent + code)
                if rest:
                    out.append(bindent + rest)
            raw[idx:idx + 1] = [seg + eol for seg in out]
            changed += 1
        elif pass_only:
            pidx = pos(body0.lineno)
            pline = raw[pidx]
            peol = "\r" if pline.endswith("\r") else ""
            pcore = pline.rstrip("\r")
            m = re.match(r"^(\s*)pass\b(.*)$", pcore)
            if not m:
                print("  !! pass not matched %s:%s" % (rel_path, t["line"]))
                continue
            trailing = m.group(2).strip()
            newcore = m.group(1) + code + (("  " + trailing) if trailing else "")
            raw[pidx] = newcore + peol
            changed += 1
        else:
            bidx = pos(body0.lineno)
            bline = raw[bidx]
            beol = "\r" if bline.endswith("\r") else ""
            bindent = re.match(r"^[\t ]*", bline.rstrip("\r")).group(0)
            raw.insert(bidx, bindent + code + beol)
            changed += 1

    if not dry_run and (changed or inject_at is not None):
        path.write_bytes("\n".join(raw).encode("utf-8"))
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", required=True)
    ap.add_argument("--scope", required=True, help="comma list, e.g. scp/security or ROOT")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = json.loads(Path(args.census).read_text(encoding="utf-8"))
    scopes = [s.strip() for s in args.scope.split(",")]
    targets = {}
    for r in rows:
        if r["cls"] != "SILENT":
            continue
        f = r["file"]
        if f.startswith("scp/tests") or "/tests/" in f:
            continue
        hit = False
        for s in scopes:
            if s == "ROOT":
                hit = hit or (f.startswith("scp/") and f.count("/") == 1 and f.endswith(".py"))
            else:
                hit = hit or f.startswith(s + "/")
        if hit:
            targets.setdefault(f, []).append(r)

    total = 0
    files_changed = []
    for f in sorted(targets):
        n = fix_file(f, targets[f], args.dry_run)
        if n:
            files_changed.append(f)
        total += n
        print("%3d fix(es)  %s" % (n, f))
    print("TOTAL edits: %d across %d files" % (total, len(files_changed)))
    if files_changed:
        print("FILES:")
        for f in files_changed:
            print("  " + f)


if __name__ == "__main__":
    main()
