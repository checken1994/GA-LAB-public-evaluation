"""
[SCP-DNA-FIX R8 v3 IMP-17] Auto-Rollback on Regression.

TẠI SAO file này tồn tại?
  IMP-1 (post_fix_verify) + IMP-2 (reality_test) chạy NGAY SAU fix apply.
  Nhưng regression có thể xuất hiện MUỘN:
    - Fix modifies shared helper → caller crash sau 30s khi scheduled job chạy.
    - Fix imports a module lazily → ImportError chỉ trigger khi first call.
    - Hypothesis property test (IMP-5) có thể mới fail trên random input sau
      khi fix đã "pass" smoke test.

  IMP-17 thêm "regression watcher": sau khi fix apply + verify OK, đăng ký
  fix với background thread. Thread định kỳ (mỗi 15s) re-run reality_test
  trên các file vừa fix (trong TTL window mặc định 60s). Nếu reality_test
  FAIL → auto-rollback fix đó bằng IMP-6 RollbackTokenRegistry.

  Inspired by:
    - Sentry canary deploys (auto-rollback on error-rate spike)
    - git bisect (identify which commit introduced regression)
    - Sentry Autofix "revert if metrics regress" (post-deploy monitoring)
    - Kubernetes liveness probes (restart pod if probe fails)

Flow:
  watcher = get_regression_watcher()
  token = watcher.register(fix_id, file, rollback_token, ttl=60)
  # ... background thread runs reality_test on file every 15s ...
  # ... if reality_test FAILS within 60s ...
  watcher.rollback(fix_id)   # uses RollbackTokenRegistry.rollback(token)

DNA principles applied:
  #9  (No harm)         — auto-rollback prevents bad fixes from lingering
  #11 (Fail loudly)     — every rollback logged with reason
  #7  (Autofix safe)    — watcher crash → log + continue (don't block engine)
  #26 (Reality cuối cùng)— periodic reality re-test = time dimension of #26

Thread-safety:
  - All public mutations take self._lock (threading.RLock).
  - Background thread is daemon=True (won't block process shutdown).
  - Atomic JSON log writes for audit trail.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.autofix.auto_rollback")


# ============================================================
# Defaults.
# ============================================================

DEFAULT_TTL_SECONDS = 60               # how long after fix to keep watching
DEFAULT_CHECK_INTERVAL_SECONDS = 15    # background thread sleep between sweeps
DEFAULT_MAX_WATCHED = 100              # cap entries (avoid unbounded growth)
DEFAULT_REGRESSION_LOG = "data/regression_watch.jsonl"


# ============================================================
# Dataclasses.
# ============================================================

@dataclass
class WatchedFix:
    """A fix registered with RegressionWatcher.

    Attributes:
        fix_id: Stable identifier (e.g. audit log row id).
        file_path: Patched file path (for reality_test re-run).
        rollback_token: 16-char token from IMP-6 RollbackTokenRegistry.
        registered_at: time.time() when registered.
        ttl: Seconds after which the watcher stops re-testing.
        last_check_at: Last time reality_test ran on this file.
        last_check_ok: Result of last reality_test.
        rollback_count: Number of times rolled back (should be 0 or 1).
        extra: Optional caller metadata (bug_type, tier, etc.).
    """
    fix_id: str
    file_path: str
    rollback_token: str
    registered_at: float = field(default_factory=time.time)
    ttl: int = DEFAULT_TTL_SECONDS
    last_check_at: float = 0.0
    last_check_ok: bool | None = None
    last_check_reason: str = ""
    rollback_count: int = 0
    rolled_back_at: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, now: float | None = None) -> bool:
        """True if TTL elapsed since registration (no more checks needed)."""
        n = now if now is not None else time.time()
        return (n - self.registered_at) > self.ttl


# ============================================================
# RegressionWatcher class.
# ============================================================

class RegressionWatcher:
    """Background-thread watcher that re-runs reality_test on recently-fixed
    files and auto-rolls-back regressions via IMP-6 RollbackTokenRegistry.

    Lifecycle:
        - Singleton via get_regression_watcher().
        - start() launches a daemon thread that wakes every
          DEFAULT_CHECK_INTERVAL_SECONDS.
        - register() adds a fix to the watch list (with TTL).
        - check_regressions() (called by the daemon thread) iterates
          non-expired entries, runs reality_test, on FAIL → rollback.
        - stop() signals the thread to exit (mostly for tests).

    Thread-safety:
        - self._lock (RLock) guards self._watched.
        - Daemon thread is the only writer of last_check_at / last_check_ok.
        - register() can be called from any thread (engine's main thread).

    Fail-open:
        - If reality_test import fails → log + skip check (don't rollback).
        - If rollback itself fails → log loudly (DNA #11), continue.
        - If daemon thread crashes → log + auto-restart on next register().
    """

    def __init__(
        self,
        data_dir: str | Path = "data",
        check_interval: int = DEFAULT_CHECK_INTERVAL_SECONDS,
        max_watched: int = DEFAULT_MAX_WATCHED,
        regression_log: str | Path = DEFAULT_REGRESSION_LOG,
        reality_test_fn: Callable[..., dict[str, Any]] | None = None,
        rollback_fn: Callable[[str], dict[str, Any]] | None = None,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.regression_log = self.data_dir / "regression_watch.jsonl"
        self.check_interval = check_interval
        self.max_watched = max_watched

        # Pluggable reality_test + rollback functions. Default: try to import
        # the canonical implementations (fail-open if unavailable).
        self._reality_test_fn = reality_test_fn
        self._rollback_fn = rollback_fn

        self._watched: dict[str, WatchedFix] = {}
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = False

    # ---------- pluggable dependencies (fail-open imports) ----------

    def _get_reality_test_fn(self) -> Callable[..., dict[str, Any]] | None:
        if self._reality_test_fn is not None:
            return self._reality_test_fn
        try:
            from scp.autofix.runner_phases.reality_test import run_reality_test
            return run_reality_test
        except ImportError as e:
            logger.warning(
                f"[IMP-17] reality_test unavailable — watcher will log only, "
                f"no auto-rollback (fail-open): {e}"
            )
            return None

    def _get_rollback_fn(self) -> Callable[[str], dict[str, Any]] | None:
        if self._rollback_fn is not None:
            return self._rollback_fn
        try:
            from scp.autofix.engine_extensions import get_rollback_registry
            registry = get_rollback_registry(self.data_dir)
            return registry.rollback
        except ImportError as e:
            logger.warning(
                f"[IMP-17] RollbackTokenRegistry unavailable — cannot "
                f"auto-rollback (fail-open): {e}"
            )
            return None

    # ---------- audit log ----------

    def _log_event(self, event: dict[str, Any]) -> None:
        """Append a JSONL event to the regression watch log (best-effort)."""
        try:
            entry = {"timestamp": time.time(), **event}
            with open(self.regression_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.debug(f"[IMP-17] log write failed: {e}")

    # ---------- public API ----------

    def register(
        self,
        fix_id: str,
        file_path: str,
        rollback_token: str,
        ttl: int = DEFAULT_TTL_SECONDS,
        extra: dict[str, Any] | None = None,
    ) -> WatchedFix:
        """Register a freshly-applied fix for regression watching.

        Args:
            fix_id: Stable identifier (caller chooses — e.g. audit log row id).
            file_path: Absolute path to the patched file.
            rollback_token: 16-char token from IMP-6 RollbackTokenRegistry.
            ttl: Seconds to keep watching (default 60).
            extra: Optional metadata (bug_type, tier, etc.) for audit log.

        Returns:
            The WatchedFix record.
        """
        entry = WatchedFix(
            fix_id=fix_id,
            file_path=file_path,
            rollback_token=rollback_token,
            ttl=ttl,
            extra=extra or {},
        )
        with self._lock:
            # Enforce max_watched cap (drop oldest expired entries first,
            # then oldest non-expired if still over cap).
            if len(self._watched) >= self.max_watched:
                self._evict_to_fit()
            self._watched[fix_id] = entry
        self._log_event({
            "action": "register",
            "fix_id": fix_id,
            "file": file_path,
            "ttl": ttl,
        })
        # Lazily start the daemon thread on first register.
        self.start()
        logger.info(
            f"[IMP-17] registered fix {fix_id} for regression watch "
            f"(file={file_path}, ttl={ttl}s)"
        )
        return entry

    def unregister(self, fix_id: str) -> bool:
        """Remove a fix from the watch list (e.g. operator confirmed OK)."""
        with self._lock:
            existed = fix_id in self._watched
            if existed:
                del self._watched[fix_id]
        if existed:
            self._log_event({"action": "unregister", "fix_id": fix_id})
        return existed

    def list_watched(self) -> list[dict[str, Any]]:
        """Snapshot of currently-watched fixes (for monitoring/stats)."""
        with self._lock:
            out = []
            for fix_id, entry in self._watched.items():
                out.append({
                    "fix_id": fix_id,
                    "file": entry.file_path,
                    "registered_at": entry.registered_at,
                    "ttl": entry.ttl,
                    "last_check_at": entry.last_check_at,
                    "last_check_ok": entry.last_check_ok,
                    "rollback_count": entry.rollback_count,
                    "expired": entry.is_expired(),
                })
            return out

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._watched)
            expired = sum(1 for e in self._watched.values() if e.is_expired())
            rolled = sum(1 for e in self._watched.values() if e.rollback_count > 0)
        return {
            "watched_count": total,
            "expired_count": expired,
            "rolled_back_count": rolled,
            "check_interval": self.check_interval,
            "max_watched": self.max_watched,
            "thread_alive": self._thread is not None and self._thread.is_alive(),
        }

    # ---------- core: check_regressions ----------

    def check_regressions(self) -> list[dict[str, Any]]:
        """Re-run reality_test on all non-expired watched files. On FAIL,
        auto-rollback via IMP-6.

        Returns list of rollback result dicts (one per rolled-back fix).

        Called by the daemon thread, but can also be invoked manually (e.g.
        from a test or a scheduled audit).
        """
        results: list[dict[str, Any]] = []
        reality_fn = self._get_reality_test_fn()
        rollback_fn = self._get_rollback_fn()

        # Snapshot under lock (don't hold lock during slow reality_test).
        with self._lock:
            entries = list(self._watched.values())

        now = time.time()
        for entry in entries:
            if entry.is_expired(now):
                continue
            if entry.rollback_count > 0:
                continue  # already rolled back, skip
            if reality_fn is None:
                # No reality_test available — can't check. Skip.
                continue

            try:
                # Re-run reality_test on the patched file. Use a short
                # bug_id for log clarity.
                rt_result = reality_fn(
                    bug_id=f"imp17-watch-{entry.fix_id}",
                    file_path=entry.file_path,
                    exercise_callables=True,
                )
                ok = bool(rt_result.get("ok", False))
                reason = str(rt_result.get("reason", ""))
            except Exception as e:  # noqa: BLE001 — fail-open per DNA #7
                logger.warning(
                    f"[IMP-17] reality_test crashed for {entry.fix_id} "
                    f"(skip check): {e}"
                )
                continue

            with self._lock:
                e2 = self._watched.get(entry.fix_id)
                if e2 is not None:
                    e2.last_check_at = now
                    e2.last_check_ok = ok
                    e2.last_check_reason = reason

            if ok:
                continue

            # Reality test FAILED → auto-rollback.
            self._log_event({
                "action": "regression_detected",
                "fix_id": entry.fix_id,
                "file": entry.file_path,
                "reason": reason,
            })
            logger.warning(
                f"[IMP-17] regression detected for fix {entry.fix_id} "
                f"(file={entry.file_path}) — auto-rolling back. "
                f"Reason: {reason}"
            )

            if rollback_fn is None:
                logger.error(
                    f"[IMP-17] cannot rollback {entry.fix_id} — "
                    f"RollbackTokenRegistry unavailable (DNA #11 fail-loudly)"
                )
                continue

            try:
                rb_result = rollback_fn(entry.rollback_token)
            except Exception as e:  # noqa: BLE001
                rb_result = {"ok": False, "reason": f"rollback crashed: {e}"}
                logger.error(
                    f"[IMP-17] rollback crashed for {entry.fix_id}: {e}\n"
                    f"{traceback.format_exc()}"
                )

            with self._lock:
                e3 = self._watched.get(entry.fix_id)
                if e3 is not None:
                    e3.rollback_count += 1
                    e3.rolled_back_at = time.time()

            self._log_event({
                "action": "rollback",
                "fix_id": entry.fix_id,
                "rollback_token": entry.rollback_token,
                "result_ok": bool(rb_result.get("ok", False)),
                "result_reason": str(rb_result.get("reason", "")),
            })
            results.append({
                "fix_id": entry.fix_id,
                "file": entry.file_path,
                "rollback_token": entry.rollback_token,
                "regression_reason": reason,
                "rollback_result": rb_result,
            })

        # Cleanup expired entries (after sweep, not during).
        self._cleanup_expired()
        return results

    # ---------- background thread ----------

    def start(self) -> None:
        """Start the daemon thread (idempotent — no-op if already running)."""
        with self._lock:
            if self._started and self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="scp-autofix-regression-watcher",
                daemon=True,
            )
            self._thread.start()
            self._started = True
            logger.info(
                f"[IMP-17] regression watcher thread started "
                f"(interval={self.check_interval}s)"
            )

    def stop(self, timeout: float = 2.0) -> None:
        """Signal the daemon thread to exit (mostly for tests)."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        with self._lock:
            self._started = False

    def _run_loop(self) -> None:
        """Daemon thread main loop. Fail-open: any exception logs + continues."""
        while not self._stop_event.is_set():
            try:
                self.check_regressions()
            except Exception as e:  # noqa: BLE001 — must not crash daemon
                logger.error(
                    f"[IMP-17] watcher loop crashed (recovering): {e}\n"
                    f"{traceback.format_exc()}"
                )
            # Wait, but wake early if stop() is called.
            self._stop_event.wait(timeout=self.check_interval)

    # ---------- internal cleanup ----------

    def _evict_to_fit(self) -> None:
        """Caller holds self._lock. Evict oldest expired (or oldest overall)."""
        if len(self._watched) < self.max_watched:
            return
        now = time.time()
        # First pass: drop expired.
        expired_ids = [fid for fid, e in self._watched.items() if e.is_expired(now)]
        for fid in expired_ids:
            del self._watched[fid]
        if len(self._watched) < self.max_watched:
            return
        # Second pass: drop oldest by registered_at.
        sorted_ids = sorted(
            self._watched.keys(),
            key=lambda fid: self._watched[fid].registered_at,
        )
        n_to_drop = len(self._watched) - self.max_watched + 1
        for fid in sorted_ids[:n_to_drop]:
            del self._watched[fid]

    def _cleanup_expired(self) -> None:
        """Remove expired entries from the watch list."""
        now = time.time()
        with self._lock:
            expired_ids = [
                fid for fid, e in self._watched.items()
                if e.is_expired(now) and e.rollback_count == 0
            ]
            for fid in expired_ids:
                del self._watched[fid]
        if expired_ids:
            self._log_event({
                "action": "cleanup_expired",
                "count": len(expired_ids),
                "fix_ids": expired_ids,
            })

    def rollback(self, fix_id: str) -> dict[str, Any]:
        """Manually trigger rollback for a specific fix_id (operator override).

        Returns the rollback_fn result dict, or {"ok": False, "reason": ...}
        if fix_id not in watch list or rollback_fn unavailable.
        """
        with self._lock:
            entry = self._watched.get(fix_id)
        if entry is None:
            return {"ok": False, "reason": f"fix_id {fix_id} not in watch list"}
        rollback_fn = self._get_rollback_fn()
        if rollback_fn is None:
            return {"ok": False, "reason": "RollbackTokenRegistry unavailable"}
        try:
            result = rollback_fn(entry.rollback_token)
        except Exception as e:  # noqa: BLE001
            result = {"ok": False, "reason": f"rollback crashed: {e}"}
        with self._lock:
            e2 = self._watched.get(fix_id)
            if e2 is not None:
                e2.rollback_count += 1
                e2.rolled_back_at = time.time()
        self._log_event({
            "action": "manual_rollback",
            "fix_id": fix_id,
            "result_ok": bool(result.get("ok", False)),
        })
        return result


# ============================================================
# Singleton.
# ============================================================

_singleton_lock = threading.Lock()
_watcher_singleton: RegressionWatcher | None = None


def get_regression_watcher(
    data_dir: str | Path = "data",
    check_interval: int = DEFAULT_CHECK_INTERVAL_SECONDS,
) -> RegressionWatcher:
    """Get the singleton RegressionWatcher instance.

    Env var SCP_REGRESSION_WATCHER_DISABLED=1 → returns a no-op watcher
    (register/unregister do nothing, check_regressions returns []).
    """
    global _watcher_singleton
    with _singleton_lock:
        if _watcher_singleton is None:
            import os
            if os.environ.get("SCP_REGRESSION_WATCHER_DISABLED", "0") == "1":
                _watcher_singleton = _NoOpWatcher()
                logger.info("[IMP-17] watcher DISABLED via env var")
            else:
                _watcher_singleton = RegressionWatcher(
                    data_dir=data_dir, check_interval=check_interval,
                )
        return _watcher_singleton


def reset_regression_watcher() -> None:
    """Reset the singleton (for tests). Stops the daemon thread first."""
    global _watcher_singleton
    with _singleton_lock:
        if _watcher_singleton is not None and isinstance(_watcher_singleton, RegressionWatcher):
            _watcher_singleton.stop()
        _watcher_singleton = None


class _NoOpWatcher(RegressionWatcher):
    """No-op watcher used when SCP_REGRESSION_WATCHER_DISABLED=1.

    All methods short-circuit. No daemon thread is started.
    """

    def register(self, fix_id, file_path, rollback_token, ttl=DEFAULT_TTL_SECONDS, extra=None):  # type: ignore[override]
        return WatchedFix(
            fix_id=fix_id, file_path=file_path,
            rollback_token=rollback_token, ttl=ttl, extra=extra or {},
        )

    def check_regressions(self):  # type: ignore[override]
        return []

    def start(self):  # type: ignore[override]
        pass

    def stop(self, timeout: float = 2.0):  # type: ignore[override]
        pass


__all__ = [
    "RegressionWatcher",
    "WatchedFix",
    "get_regression_watcher",
    "reset_regression_watcher",
    "DEFAULT_TTL_SECONDS",
    "DEFAULT_CHECK_INTERVAL_SECONDS",
]
