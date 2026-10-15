"""Census of silent `except` blocks in scp/core/ and scp/meta/ (S-B1a).

Classification:
  OK            - body contains logging call or raise/re-raise or explicit error return
  INTENTIONAL   - body has `# silent-by-design` comment with reason (or pass with such comment on handler line)
  SILENT        - everything else (candidate for fail-loudly fix)

Usage: python scripts/diagnostics/census_silent_except.py [--json OUT]
"""
import ast
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCOPES = [REPO / "scp" / "core", REPO / "scp" / "meta"]

LOG_ATTRS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "log"}
LOG_NAMES = {"logger", "log", "logging", "console", "_log", "audit_log", "tlog", "self._log"}


def is_logging_call(node: ast.Call) -> bool:
    f = node.func
    # logger.warning(...) / log.debug(...) / logging.error(...) / self.logger.info(...)
    if isinstance(f, ast.Attribute) and f.attr in LOG_ATTRS:
        base = f.value
        if isinstance(base, ast.Name) and base.id in LOG_NAMES:
            return True
        if isinstance(base, ast.Attribute) and base.attr in LOG_NAMES | {"logger", "log"}:
            return True
    return False


def collect_calls(node):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            yield sub


def body_has_logging(body):
    for stmt in body:
        for call in collect_calls(stmt):
            if is_logging_call(call):
                return True
        # print(..., "ERROR", ...) style is not logging per contract, skip
    return False


def body_has_raise(body):
    for stmt in body:
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Raise):
                return True
    return False


EXC_TEXT_MARKERS = ("type(exc).__name__", "str(exc)", "repr(exc)", "{e}", "exc)")


def body_has_explicit_error_return(body):
    """Return-_error-tu-minh: return value visibly encodes the error
    (dict with 'error' key, tuple/status string referencing the exception,
    or an f-string containing the exception)."""
    for stmt in body:
        if not isinstance(stmt, ast.Return):
            continue
        val = stmt.value
        if val is None:
            continue
        try:
            text = ast.unparse(val)
        except Exception:
            continue
        if "'error'" in text or '"error"' in text:
            return True
        exc_names = "|".join(sorted(_exc_names(body)))
        if re.search(rf"\b({exc_names})\b", text):
            # any reference to exception variable in the returned value
            return True
        if "UNKNOWN" in text or "FAILED" in text or "ERROR" in text:
            return True
    return False


def _exc_names(body):
    names = set()
    # find the handler's exception binding by scanning for common names used in returns
    for n in ("e", "exc", "err"):
        names.add(n)
    return names


def body_appends_to_error_accumulator(body):
    """errors.append(...) / errs / failures / result['errors'] — explicit
    aggregated error propagation returned to the caller."""
    for stmt in body:
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "append":
                base = sub.func.value
                if isinstance(base, ast.Name) and base.id.lower() in {"errors", "errs", "failures"}:
                    return True
                if isinstance(base, ast.Subscript) and "error" in ast.unparse(base.slice):
                    return True
            if isinstance(sub, ast.Assign):
                try:
                    t = ast.unparse(sub)
                except Exception:
                    continue
                if "'error'" in t or '"error"' in t or "ok': False" in t or "ok\": False" in t:
                    return True
    return False


def has_silent_by_design(handler):
    # comment on the `except` line itself
    if handler.lineno in COMMENTS and "silent-by-design" in COMMENTS[handler.lineno]:
        return COMMENTS[handler.lineno].strip()
    for stmt in handler.body:
        seg = COMMENTS.get(stmt.lineno, "") + COMMENTS.get(stmt.lineno - 1, "")
        if "silent-by-design" in seg:
            return seg.strip()
        # inline trailing comment on first body stmt
        seg2 = COMMENTS.get(stmt.lineno, "")
        if "silent-by-design" in seg2:
            return seg2.strip()
    return None


def comments_of(src: str):
    import tokenize
    import io
    out = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                line = tok.start[0]
                out[line] = (out.get(line, "") + " " + tok.string).strip()
    except Exception:
        pass
    return out


def exception_type_str(handler):
    t = handler.type
    if t is None:
        return "bare-except"
    try:
        return ast.unparse(t)
    except Exception:
        return "<complex>"


def summarize_body(handler, max_len=80):
    parts = []
    for stmt in handler.body:
        try:
            parts.append(ast.unparse(stmt))
        except Exception:
            parts.append(type(stmt).__name__)
    s = " ; ".join(parts)
    return s[:max_len] + ("..." if len(s) > max_len else "")


COMMENTS = {}


def census_file(path: Path):
    global COMMENTS
    src = path.read_text(encoding="utf-8", errors="replace")
    COMMENTS = comments_of(src)
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"file": str(path), "line": e.lineno, "exc": "SYNTAX-ERROR", "cls": "SILENT", "body": str(e)}]
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                body = handler.body
                is_pass = all(isinstance(s, ast.Pass) for s in body) and len(body) == 1
                has_log = body_has_logging(body)
                has_raise = body_has_raise(body)
                has_err_ret = body_has_explicit_error_return(body)
                has_err_acc = body_appends_to_error_accumulator(body)
                reason = has_silent_by_design(handler)
                if has_log or has_raise or has_err_ret or has_err_acc:
                    cls = "OK"
                elif reason:
                    cls = "INTENTIONAL"
                elif is_pass:
                    cls = "SILENT"
                else:
                    # body does something but no logging/raise: e.g. continue/break/return None/fallback set
                    # per contract this is SILENT unless it returns explicit error; classify as SILENT-NOLOG
                    cls = "SILENT"
                rows.append({
                    "file": str(path.relative_to(REPO)).replace("\\", "/"),
                    "line": handler.lineno,
                    "exc": exception_type_str(handler),
                    "cls": cls,
                    "is_pass": is_pass,
                    "body": summarize_body(handler),
                })
    return rows


def main():
    out_rows = []
    for scope in SCOPES:
        for path in sorted(scope.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            out_rows.extend(census_file(path))
    counts = {"SILENT": 0, "OK": 0, "INTENTIONAL": 0}
    for r in out_rows:
        counts[r["cls"]] += 1
    print(f"TOTAL except handlers: {len(out_rows)}")
    print(f"OK(has log/raise): {counts['OK']}")
    print(f"INTENTIONAL(silent-by-design): {counts['INTENTIONAL']}")
    print(f"SILENT(need fix): {counts['SILENT']}")
    print()
    silent = [r for r in out_rows if r["cls"] == "SILENT"]
    if "--json" in sys.argv:
        outp = sys.argv[sys.argv.index("--json") + 1]
        Path(outp).write_text(json.dumps(out_rows, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {outp}")
    else:
        for r in silent:
            print(f"{r['file']}:{r['line']} [{r['exc']}]{' PASS' if r['is_pass'] else ''} :: {r['body']}")


if __name__ == "__main__":
    main()
