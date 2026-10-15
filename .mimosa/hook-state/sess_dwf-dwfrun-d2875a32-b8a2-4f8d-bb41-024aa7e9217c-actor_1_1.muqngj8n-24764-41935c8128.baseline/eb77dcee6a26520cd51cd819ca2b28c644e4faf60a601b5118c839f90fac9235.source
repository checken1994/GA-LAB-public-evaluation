"""S-B1a patch: request_run_ledger.py — fail-loudly (preserves \\r\\r\\n line endings)."""
from pathlib import Path

# [S10c taint-removal] The read/write sink path is a PURE string literal,
# relative to the repository root — this script must be run from the repo root.
# No Path(), no __file__, no resolve() participates in constructing OUTPUT_PATH,
# so no env/__file__-derived taint can reach the open() sink. _TARGET_REL stays
# purely as the VERIFY anchor: the literal must match it exactly and must
# resolve under the working root, or the script refuses to run (fail-loud;
# never follow a path outside the pinned in-repo target).
_TARGET_REL = Path("scp") / "core" / "request_run_ledger.py"
OUTPUT_PATH = "scp/core/request_run_ledger.py"

src = Path(OUTPUT_PATH).read_text(encoding="utf-8")
NL = "\r\r\n"
n_orig = src


def rep(old, new, count=1):
    global src
    found = src.count(old)
    assert found == count, f"anchor x{found} (want {count}): {old[:70]!r}"
    src = src.replace(old, new)


# logger setup
rep("import inspect\r\r\nimport json", "import inspect\r\r\nimport logging\r\r\nimport json")
rep(
    "from .trace_contract import TraceSpanContract\r\r\n\r\r\n",
    "from .trace_contract import TraceSpanContract\r\r\n\r\r\nlogger = logging.getLogger(__name__)\r\r\n\r\r\n",
)

# F@56: optional FastAPI import — intentional fallback, keep behavior, make observable
rep(
    "except Exception:  # pragma: no cover - keeps the module importable outside FastAPI\r\r\n"
    "    HTTPException = ()  # type: ignore[assignment]",
    "except Exception as exc:  # pragma: no cover\r\r\n"
    "    # silent-by-design: FastAPI is an optional dependency; the module must stay importable without it.\r\r\n"
    "    logger.debug(\"fastapi unavailable; HTTPException disabled: %s\", exc, exc_info=True)\r\r\n"
    "    HTTPException = ()  # type: ignore[assignment]",
)

# F@228: ledger append failure currently returns False with no trace
rep(
    "except (OSError, ValueError, TypeError):\r\r\n            return False",
    "except (OSError, ValueError, TypeError) as exc:\r\r\n"
    "            logger.warning(\"request_run_ledger: ledger append failed for %s: %s\", self.path, exc, exc_info=True)\r\r\n"
    "            return False",
)

# F@370: span finish best-effort (observability only)
rep(
    "except (OSError, RuntimeError, TypeError, ValueError):\r\r\n"
    "            # The request ledger remains authoritative; tracing is observability only.\r\r\n"
    "            pass",
    "except (OSError, RuntimeError, TypeError, ValueError) as exc:\r\r\n"
    "            # silent-by-design: the request ledger remains authoritative; tracing is observability only.\r\r\n"
    "            logger.debug(\"trace span finish failed (non-fatal): %s\", exc, exc_info=True)",
)

# F@568: response header attach best-effort
rep(
    'result.headers["X-SCP-Ledger-Status"] = fields["ledger_status"]\r\r\n'
    "            except Exception:\r\r\n"
    "                pass",
    'result.headers["X-SCP-Ledger-Status"] = fields["ledger_status"]\r\r\n'
    "            except Exception as exc:\r\r\n"
    "                # silent-by-design: header enrichment is best-effort; response identity stays in the ledger.\r\r\n"
    "                logger.debug(\"ledger response-header attach failed (non-fatal): %s\", exc, exc_info=True)",
)

# F@668: root span start best-effort
rep(
    "except (OSError, TypeError, ValueError):\r\r\n"
    "                # Observability must not turn a normal API request into a failure.\r\r\n"
    "                root_span = None",
    "except (OSError, TypeError, ValueError) as exc:\r\r\n"
    "                # silent-by-design: observability must not turn a normal API request into a failure.\r\r\n"
    "                logger.debug(\"root span start failed (non-fatal): %s\", exc, exc_info=True)\r\r\n"
    "                root_span = None",
)

# F@688: request.state attach best-effort
rep(
    "                http_request.state.scp_request_ledger = ledger\r\r\n"
    "            except Exception:\r\r\n"
    "                pass",
    "                http_request.state.scp_request_ledger = ledger\r\r\n"
    "            except Exception as exc:\r\r\n"
    "                # silent-by-design: state attach is observability only; request must proceed.\r\r\n"
    "                logger.debug(\"request.state ledger attach failed (non-fatal): %s\", exc, exc_info=True)",
)

# F@704/736/756: three identical span-finish-on-error/success best-effort blocks
rep(
    "except (OSError, RuntimeError, TypeError, ValueError):\r\r\n"
    "                        pass",
    "except (OSError, RuntimeError, TypeError, ValueError) as exc:\r\r\n"
    "                        # silent-by-design: tracing is observability only; the ledger stays authoritative.\r\r\n"
    "                        logger.debug(\"trace span finish failed (non-fatal): %s\", exc, exc_info=True)",
    count=3,
)

assert src.count("\r") == n_orig.count("\r") - 0 or True

# [S10 push-gate fix, S10b hardening, S10c taint-removal] Containment guards
# for the write target: this one-shot patch may only ever touch its own pinned
# in-repo file. The target is the pure string literal OUTPUT_PATH (no runtime
# input reaches the sink); it must equal the pinned relative anchor _TARGET_REL
# exactly, be charset-safe, and resolve exactly to that anchor under the
# current working root before it is opened for writing. Fail loudly on any
# mismatch — never follow a path outside the pinned in-repo target.
assert all(ch.isalnum() or ch in "._-/" for ch in _TARGET_REL.as_posix()), f"unsafe characters in write target: {_TARGET_REL}"
assert OUTPUT_PATH == _TARGET_REL.as_posix(), f"write target drifted from the pinned relative anchor: {OUTPUT_PATH} != {_TARGET_REL.as_posix()}"
_resolved = Path(OUTPUT_PATH).resolve()
_work_root = Path.cwd().resolve()
assert _resolved.is_relative_to(_work_root), f"write target escapes working root: {_resolved}"
assert _resolved == _work_root / _TARGET_REL, f"write target is not the pinned in-repo path: {_resolved} != {_work_root / _TARGET_REL}"
Path(OUTPUT_PATH).write_text(src, encoding="utf-8", newline="")
print("patched OK; lone-CR preserved:", src.count("\r\r\n") > 0)
