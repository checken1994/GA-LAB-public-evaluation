"""Reality test: BareExceptPass is not semantic-equivalent to except Exception: pass."""
from __future__ import annotations

import ast
import hashlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _handler_at(path: Path, line: int, func_name: str) -> ast.ExceptHandler:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler) and node.lineno == line
    ]
    assert len(matches) == 1, f"expected one except handler at {path}:{line}, got {len(matches)}"
    handler = matches[0]
    # S17 strictness increase: pin the handler IDENTITY, not just a line
    # number. The target must be a plain `except Exception` handler (the
    # narrowing the semantic claim is about) and must live inside the
    # expected function — a coincidental handler at the same line would
    # otherwise pass.
    assert isinstance(handler.type, ast.Name) and handler.type.id == "Exception", (
        f"{path}:{line} no longer narrows to a plain `except Exception` "
        f"(got: {ast.dump(handler.type) if handler.type else 'bare'})"
    )
    enclosing = [
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(h is handler for h in ast.walk(n))
    ]
    assert func_name in enclosing, (
        f"{path}:{line} handler is no longer inside expected function "
        f"{func_name!r} (found in: {enclosing}) — pin drifted again, "
        "re-verify semantics before repinning"
    )
    return handler


def _run_bare(exc_type: type[BaseException]) -> str:
    try:
        raise exc_type()
    except:
        return "caught"


def _run_typed(exc_type: type[BaseException]) -> str:
    try:
        try:
            raise exc_type()
        except Exception:
            return "caught"
    except BaseException:
        return "propagated"


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    # S17 drift update (post-campaign reality): S-B1b fail-loudly commit
    # 265ea20 + B1 logging converted the silent except blocks and shifted
    # lines. Old pins speculative_prefixer.py:559 (_touch) and
    # type_flow_verifier.py:717 (verify_type_flow) moved to 565 and 720
    # respectively — same handlers, same semantics, verified via AST + git
    # history before repinning.
    # Drift update 2 (2026-09-24): commit e40af00 (M1/M2/M3 fixes) added 3
    # lines inside _CallSiteCollector._is_none_check (~line 382), shifting the
    # verify_type_flow handler 720 → 723. Handler content is byte-identical
    # (except Exception as _scp_exc + logger.debug) — identity re-verified via
    # AST (plain Name `Exception`, body Expr non-pass, inside
    # verify_type_flow) + git show e40af00 before repinning. The
    # handler-identity assertions below keep this pin honest (strictness >=
    # original line-only pin).
    # Drift update 3 (2026-09-26): the silent-except visibility sweep added
    # one log line above _touch (shifting its handler) — 565 → 566, identity
    # re-verified via AST before repinning.
    # Drift update 4 (2026-10-01): commit a068dbe2 (fix(audit-r2): scanner
    # coverage cap + sandbox argv-injection gate + ...) added 9 lines inside
    # verify_type_flow, shifting the pinned handler 722 → 731. Handler
    # identity re-verified before repinning: plain Name `Exception`, body is
    # the unchanged `logger.debug(f"[SCP deterministic autofix] silenced
    # exception: {_scp_exc!r}")` Expr, byte-identical to the handler at line
    # 722 in a068dbe2~1 (git show), and still inside verify_type_flow (AST).
    # The assertion strictness is unchanged (identity pin + function
    # containment + non-pass body).
    checks = {
        (root / "scp/autofix/speculative_prefixer.py", 566): "_touch",
        (root / "scp/autofix/type_flow_verifier.py", 731): "verify_type_flow",
    }
    for (path, line), func_name in checks.items():
        handler = _handler_at(path, line, func_name)
        assert handler.type is not None, f"{path}:{line} is a bare except unexpectedly"
        assert handler.body, f"{path}:{line} has an empty typed exception handler"
        assert not (len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass)), f"{path}:{line} still uses typed-except-pass"
        print(f"PASS classification: {path.name}:{line} is typed-exception with explicit handling, not bare-except-pass")

    source = "def f():\n    try:\n        return 1\n    except:\n        pass\n"
    from scp.autofix.speculative_prefixer import SpeculativeCache

    with tempfile.TemporaryDirectory(prefix="r44_4b014_") as tmp:
        cache = SpeculativeCache(cache_file=str(Path(tmp) / "cache.json"))
        stored = cache.prefetch_candidates("historical.py", ["bare_except_pass"], source_override=source)
        file_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        candidate = cache.lookup(file_sha, "bare_except_pass")
        assert stored == 1 and candidate is not None
        assert "except Exception:" in candidate.patched_snippet
        ast.parse(candidate.full_patched_source)
        print("PASS candidate: generated patch parses and narrows handler")

    assert _run_bare(ValueError) == _run_typed(ValueError) == "caught"
    print("PASS semantic matrix: ordinary Exception behavior agrees")

    for exc_type in (KeyboardInterrupt, SystemExit, GeneratorExit):
        bare = _run_bare(exc_type)
        typed = _run_typed(exc_type)
        assert bare == "caught" and typed == "propagated"
        print(f"PASS counterexample: {exc_type.__name__} differs (bare={bare}, typed={typed})")

    print("RESULT: semantic equivalence is disproved outside Exception; promotion must remain gated")


if __name__ == "__main__":
    main()
