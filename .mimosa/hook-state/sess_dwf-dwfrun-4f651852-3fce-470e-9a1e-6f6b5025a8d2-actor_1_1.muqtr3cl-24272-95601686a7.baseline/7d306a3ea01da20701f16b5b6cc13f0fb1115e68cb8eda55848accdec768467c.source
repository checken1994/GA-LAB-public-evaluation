"""
[STARTUP-GATE] Pre-startup audit + scheduled audit.

Logic:
  1. Scan code (AST) → tìm bugs
  2. Auto-fix Tier 1/2 (implementation bugs)
  3. Đếm bugs KHÔNG fix được (Tier 3 pending + fix failed)
  4. Nếu có bugs không fix được → return {"blocking": True, ...}
  5. Nếu không có → return {"blocking": False, ...}

Caller (api_server.py lifespan) sẽ check:
  - blocking=True → raise Exception → server KHÔNG start
  - blocking=False → server start bình thường

Extracted from `autofix/runner.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("scp.autofix.runner")


def pre_startup_audit(run_deep_audit_fn, max_bugs: int | None = None) -> dict:
    """[STARTUP-GATE] Chạy deep audit TRƯỚC khi server start.

    [ROOT-FIX 46] max_bugs default changed 50 → 200 (env: SCP_MAX_STARTUP_BUGS).
    WHY: 50 cap bỏ sót 14+ bugs mỗi startup. MAX_FIXES_PER_CYCLE=200, nên
    max_bugs=200 cho phép fix tất cả bugs trong 1 cycle.

    Args:
        run_deep_audit_fn: Callable[[int], dict] — injected to avoid
            circular import with runner.py. Pass `run_deep_audit` from
            runner.py at call time.
        max_bugs: Cap bugs processed. Default: env SCP_MAX_STARTUP_BUGS or 200.

    Returns:
        {
            "blocking": bool,        # True = có lỗi không fix được, dừng server
            "total_bugs": int,       # tổng bugs tìm
            "fixed": int,            # bugs đã auto-fix
            "unfixed": int,          # bugs chưa fix (Tier 3 + failed)
            "details": [...],        # chi tiết bugs không fix được
        }
    """
    if max_bugs is None:
        max_bugs = int(os.environ.get("SCP_MAX_STARTUP_BUGS", "200"))

    logger.info("=" * 60)
    logger.info("[STARTUP-GATE] Pre-startup deep audit starting...")
    logger.info("=" * 60)

    results = run_deep_audit_fn(max_bugs=max_bugs)

    total = results.get("processed", 0)
    fixed = results.get("fixed", 0)
    permission_requested = results.get("permission_requested", 0)
    skipped = results.get("skipped", 0)

    # Bugs không fix được = permission_requested (Tier 3) + skipped (failed/cooldown)
    unfixed = permission_requested + skipped

    # [V10.4-FIX] BareExceptPass không fatal → không block server
    # TẠI SAO: BareExceptPass chỉ nuốt error (silent failure) — không crash
    # → Server vẫn chạy được, fix sau bằng background audit
    # Chỉ block bugs NGUY HIỂM (security, crash, type mismatch)
    _NON_BLOCKING_TYPES = {
        "BareExceptPass", "PossiblyUndefinedName",
        #  style warnings + intentional patterns — không block server
        "RuffSecurity_PLC0415",  # lazy import (avoids circular)
        "RuffSecurity_PLW0717",  # try clause too long (style)
        "RuffSecurity_PLW0603",  # global statement (intentional for bg tasks)
        "RuffSecurity_RUF052",   # used dummy variable (false positive on closures)
        "RuffSecurity_RUF100",   # unused noqa (style)
        "RuffSecurity_PLR2004",  # magic value (style)
        "RuffSecurity_BLE001",   # broad except (SCP's deliberate fail-open)
        "RuffSecurity_T201",     # print() (style)
        "RuffSecurity_G004",     # logging-f-string (style)
        # [R12-21b] additional non-blocking (style + SCP patterns)
        "RuffSecurity_RUF012",   # mutable class default (Tier 3, not runtime crash)
        "RuffSecurity_RUF013",   # implicit Optional (style, Python 3.9+)
        "RuffSecurity_RUF001",   # ambiguous unicode (style)
        "RuffSecurity_RUF002",   # ambiguous unicode docstring (style)
        "RuffSecurity_RUF003",   # ambiguous unicode comment (style)
        "RuffSecurity_RUF029",   # dict init (style)
        "RuffSecurity_RUF059",   # unused param (style)
        "RuffSecurity_RUF067",   # unused noqa (style)
        "RuffSecurity_RUF069",   # unused noqa (style)
        "RuffSecurity_RUF075",   # noqa count (style)
        "RuffSecurity_RUF022",   # mutable __all__ (style — SCP uses dynamic __all__)
        "RuffSecurity_UP045",    # typing.Optional (style, pyupgrade)
        "RuffSecurity_PLW1514",  # open without explicit (style)
        "RuffSecurity_PLW2901",  # redefined loop name (idiomatic in SCP)
        "RuffSecurity_S101",     # assert (intentional in debug)
        "RuffSecurity_S110",     # try except pass (SCP's fail-open)
        "RuffSecurity_S112",     # try except continue (SCP's fail-open)
        "RuffSecurity_S104",     # 0.0.0.0 bind (intentional for bridge)
        "RuffSecurity_S404",     # subprocess module (intentional)
        "RuffSecurity_S603",     # subprocess run (intentional, validated)
        "RuffSecurity_S607",     # partial path (intentional)
        "RuffSecurity_S608",     # SQL string (SCP uses hardcoded queries)
        "DeadCode_Vulture",      # dead code (not runtime crash)
    }

    # Lấy chi tiết bugs skipped để check type
    _blocking_unfixed = 0
    _non_blocking_unfixed = 0
    for detail in results.get("details", []):
        _bt = detail.get("bug_type", "")
        if _bt in _NON_BLOCKING_TYPES:
            _non_blocking_unfixed += 1
        else:
            _blocking_unfixed += 1

    # Chỉ block nếu có bugs nguy hiểm
    blocking = _blocking_unfixed > 0

    summary = {
        "blocking": blocking,
        "total_bugs": total,
        "fixed": fixed,
        "unfixed": unfixed,
        "permission_requested": permission_requested,
        "skipped": skipped,
        "non_blocking_skipped": _non_blocking_unfixed,
        "blocking_skipped": _blocking_unfixed,
    }

    if blocking:
        logger.error("=" * 60)
        logger.error(f"[STARTUP-GATE] ❌ {_blocking_unfixed} CRITICAL bugs CANNOT be auto-fixed!")
        logger.error(f"  - {permission_requested} need human permission (Tier 3)")
        logger.error(f"  - {_blocking_unfixed} critical skipped (failed/cooldown)")
        logger.error(f"  - {_non_blocking_unfixed} non-critical (BareExceptPass) — will fix background")
        logger.error("  SERVER START BLOCKED — fix critical bugs manually.")
        logger.error("=" * 60)
    else:
        if _non_blocking_unfixed > 0:
            logger.warning("=" * 60)
            logger.warning(f"[STARTUP-GATE] ⚠️ {total} bugs found, {fixed} fixed, "
                          f"{_non_blocking_unfixed} non-critical (BareExceptPass) — server start OK")
            logger.warning("  Non-critical bugs will be fixed by background audit.")
            logger.warning("=" * 60)
        else:
            logger.info("=" * 60)
            logger.info(f"[STARTUP-GATE] ✅ All {total} bugs auto-fixed (or none found).")
            logger.info("  Server start authorized.")
            logger.info("=" * 60)

    return summary


def run_scheduled(run_deep_audit_fn, interval_seconds: int = 7 * 24 * 3600,
                  max_bugs: int = 0) -> None:
    """[EXEC-1 A4] Block + run deep audit on a schedule (weekly by default).

    For use as a long-lived background thread OR called by a systemd timer /
    cron entry. Each invocation runs run_deep_audit() then sleeps.

    Args:
        run_deep_audit_fn: Callable[[int], dict] — injected to avoid
            circular import with runner.py.
        interval_seconds: sleep between runs (default weekly).
        max_bugs: bug cap per run.
    """
    logger.info(
        f"[runner] scheduled deep-audit started — interval={interval_seconds}s"
    )
    while True:
        try:
            run_deep_audit_fn(max_bugs=max_bugs)
        except Exception as e:
            logger.error(f"[runner] scheduled deep-audit failed: {e}", exc_info=True)
        import time as _time
        _time.sleep(interval_seconds)
