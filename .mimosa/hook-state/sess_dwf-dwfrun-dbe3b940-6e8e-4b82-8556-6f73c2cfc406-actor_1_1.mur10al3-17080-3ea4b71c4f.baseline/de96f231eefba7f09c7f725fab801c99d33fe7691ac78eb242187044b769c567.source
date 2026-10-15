"""SCP entry point — run with: python3 -m scp [port]

Defaults to port 8000. Reads SCP_PORT env var if no arg is passed.
Reads SCP_HOST env var (default 127.0.0.1 — bind to loopback only; the
Caddy gateway on :81 reverse-proxies public traffic via ?XTransformPort=8000).

Examples:
    python3 -m scp                 # 127.0.0.1:8000 (default)
    python3 -m scp 8080            # 127.0.0.1:8080
    SCP_PORT=9000 python3 -m scp   # 127.0.0.1:9000

NOTE: `app` is the FastAPI instance defined at module level in
`scp/api_server.py` (line ~438). uvicorn imports it via the string
"scp.api_server:app" so it doesn't import this __main__ module (which would
trigger uvicorn.run() recursively).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


# [SCP-DNA-FIX R14-ENV] ROOT CAUSE FIX: load .env BEFORE anything else.
#
# 5-Whys analysis:
#   Symptom: User set SCP_AUTH_PASSWORD + SCP_SKIP_STARTUP_GATE in .env but
#   gate doesn't run / auth doesn't work.
#   Why 1: .env is never loaded when `python3 -m scp` starts
#   Why 2: load_dotenv() only exists in scp/autofix/runner.py
#   Why 3: runner.py is imported LAZILY (inside lifespan() function, line 92)
#   Why 4: By the time lifespan() runs, api_server.py module-level code has
#   already read env vars (CORS, FORCE_HTTPS, etc.) with EMPTY values
#   Why 5 (ROOT): .env loading is FRAGMENTED — it happens too late (inside
#         lifespan) instead of at process start. Env reads at module-level
#         and early lifespan (SCP_SKIP_STARTUP_GATE at line 87) happen
#         BEFORE runner.py imports and loads .env.
#
# ROOT FIX: load .env at the VERY START of __main__.py, before uvicorn
# imports api_server. This ensures ALL env reads (module-level, lifespan,
# verify_admin) see the real values from .env.
#
# Why this is ROOT not CASCADE:
# - Cascade fix would add load_dotenv() to api_server.py module-level too,
#   but that still runs AFTER __main__.py reads SCP_PORT/SCP_HOST.
# - This fix loads .env ONCE at process entry → all downstream code sees
#   correct env, regardless of import order.
# - Eliminates the bug CLASS (late .env loading) at origin.
def _load_env_at_startup() -> None:
    """Load the selected env file before importing the API.
    SCP_ENV_FILE is the explicit configuration boundary for isolated runs.
    If absent, retain the historical repo-root .env fallback.
    If present but missing, fail closed by loading no env file.
    """
    _override = os.environ.get("SCP_ENV_FILE")
    if _override:
        _env_path = Path(_override).expanduser()
        if not _env_path.is_absolute():
            _env_path = Path.cwd() / _env_path
    else:
        _env_path = Path(__file__).resolve().parent.parent / ".env"
    if not _env_path.exists() or not _env_path.is_file():
        return
    if _override:
        # Explicit env-file is an isolated boundary: always apply its keys.
        for _line in _env_path.read_text(encoding="utf-8-sig").splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _, _val = _line.partition("=")
            _key = _key.strip()
            _val = _val.strip().strip(chr(34)).strip(chr(39))
            if _key:
                os.environ[_key] = _val
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path, override=False)
    except ImportError:
        # [F-05 audit-r2 2026-10-01] This except body used to call
        # `logger.debug(...)` — but `logger` is only bound AFTER this function
        # runs (module line ~95), so a missing python-dotenv raised NameError
        # here instead of reaching the manual parser fallback below (audit
        # probe probe2_main_logger_nameerror, OBSERVED NameError). At this
        # point in module init no logging handler exists yet: stderr is the
        # only safe, already-initialized channel. The fallback parser below
        # still runs — fail-open to the fallback, fail-loud on stderr.
        print(
            "[scp.__main__] python-dotenv unavailable - using built-in env parser fallback",
            file=sys.stderr,
        )
        for _line in _env_path.read_text(encoding="utf-8-sig").splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _, _val = _line.partition("=")
            _key = _key.strip()
            _val = _val.strip().strip(chr(34)).strip(chr(39))
            if _key and _key not in os.environ:
                os.environ[_key] = _val
_load_env_at_startup()
import logging

from scp.security.production_guard import enforce_production_safety

logger = logging.getLogger(__name__)

enforce_production_safety()
def main() -> None:
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print("usage: python -m scp [PORT]")
        print("Starts the SCP API on loopback; PORT defaults to SCP_PORT or 8000.")
        return
    port = (
        int(sys.argv[1])
        if len(sys.argv) > 1
        else int(os.environ.get("SCP_PORT", "8000"))
    )
    os.environ["SCP_PORT"] = str(port)
    host = os.environ.get("SCP_HOST", "127.0.0.1")

    import asyncio

    import uvicorn
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Import via string so uvicorn's reloader (when reload=True) doesn't
    # double-import this module. We keep reload=False — the SCP codebase
    # spins up background threads at startup that don't survive a reload.
    uvicorn.run(
        "scp.api_server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
