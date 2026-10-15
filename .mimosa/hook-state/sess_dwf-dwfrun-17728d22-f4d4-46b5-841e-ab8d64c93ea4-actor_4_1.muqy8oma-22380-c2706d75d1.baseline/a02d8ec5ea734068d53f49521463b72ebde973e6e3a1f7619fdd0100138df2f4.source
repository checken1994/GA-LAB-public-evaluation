# SCP CIRCUIT: M1 Boot & Background — STATUS: CLOSED (closure: docs/evidence-summary/M01-closure.json)
"""
scp/api/background_jobs.py
===========================
Background Job Registry cho SCP lifespan.

DNA #23 — Xây quá trình tự sửa: không để job quan trọng bị "quên" khi thêm mới.
DNA #19 — Missing piece: trước đây mỗi background job là ad-hoc try/except block riêng,
          không có registry → expire_leases, auto_reconcile_orphans không bao giờ được gọi.

Cách dùng:
  from scp.api.background_jobs import registry, BackgroundJob
  import time

  # Đăng ký job (thường ở module init của từng subsystem):
  @registry.register(name="kernel_watchdog", interval_seconds=30, required=True)
  def _kernel_watchdog_tick():
      from scp.api._shared import get_kernel
      k = get_kernel()
      if k:
          k.expire_leases()
          k.auto_reconcile_orphans()

  # Trong lifespan():
  registry.start_all()    # khởi động tất cả jobs
  yield
  registry.stop_all()     # dừng sạch khi shutdown
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger("scp.api.background_jobs")


@dataclass
class BackgroundJob:
    """Mô tả một background job định kỳ."""
    name: str
    fn: Callable[[], None]
    interval_seconds: float
    required: bool = False          # nếu True → lỗi khi start = fail boot
    initial_delay_seconds: float = 10.0
    _stop_event: threading.Event = field(default_factory=threading.Event, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)
    _started: bool = field(default=False, repr=False)
    _error_count: int = field(default=0, repr=False)

    def start(self) -> None:
        if self._started:
            return
        self._stop_event.clear()

        def _loop():
            # Initial delay — để server boot xong trước
            if self._stop_event.wait(self.initial_delay_seconds):
                return
            logger.info("[BackgroundJob] %s: started (interval=%.0fs)", self.name, self.interval_seconds)
            _first_execution_logged = False
            while not self._stop_event.is_set():
                try:
                    self.fn()
                    self._error_count = 0
                    if not _first_execution_logged:
                        # [MACH1-FIX-1] one-line evidence that the job body really
                        # executed (not just that its thread was scheduled).
                        logger.info("[BackgroundJob] %s: first execution completed", self.name)
                        _first_execution_logged = True
                except Exception as exc:
                    self._error_count += 1
                    logger.warning(
                        "[BackgroundJob] %s: error #%d — %s",
                        self.name, self._error_count, exc, exc_info=True
                    )
                    if self._error_count >= 5:
                        logger.error(
                            "[BackgroundJob] %s: %d consecutive errors — suppressing until next cycle",
                            self.name, self._error_count
                        )
                self._stop_event.wait(self.interval_seconds)

        # For required jobs with no initial delay, run once synchronously to fail fast
        if self.required and self.initial_delay_seconds <= 0:
            try:
                self.fn()
                self._error_count = 0
            except Exception as exc:
                logger.error("[BackgroundJob] %s: required job failed synchronously — %s", self.name, exc)
                raise

        self._thread = threading.Thread(
            target=_loop,
            daemon=True,
            name=f"scp-bg-{self.name}",
        )
        self._thread.start()
        self._started = True

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._started = False


class BackgroundJobRegistry:
    """
    Registry trung tâm cho tất cả background jobs của SCP.
    
    Nguyên tắc:
    - Mỗi job đăng ký một lần, start_all() gọi một lần trong lifespan.
    - Job required=True → lỗi start = raise → server không boot.
    - Job required=False → lỗi start = warn + tiếp tục.
    """  # noqa: W291,W293  # [hygiene-keep] whitespace inside string/docstring - keep content verbatim

    def __init__(self) -> None:
        self._jobs: dict[str, BackgroundJob] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        interval_seconds: float,
        required: bool = False,
        initial_delay_seconds: float = 10.0,
    ) -> Callable[[Callable], Callable]:
        """Decorator để đăng ký một background job."""
        def decorator(fn: Callable) -> Callable:
            with self._lock:
                if name in self._jobs:
                    raise ValueError(f"BackgroundJob '{name}' đã được đăng ký.")
                self._jobs[name] = BackgroundJob(
                    name=name,
                    fn=fn,
                    interval_seconds=interval_seconds,
                    required=required,
                    initial_delay_seconds=initial_delay_seconds,
                )
            return fn
        return decorator

    def add(self, job: BackgroundJob) -> None:
        """Thêm job đã tạo sẵn vào registry."""
        with self._lock:
            if job.name in self._jobs:
                raise ValueError(f"BackgroundJob '{job.name}' đã được đăng ký.")
            self._jobs[job.name] = job

    def start_all(self) -> None:
        """Khởi động tất cả jobs. Required jobs fail → raise."""
        failed_required: list[str] = []
        with self._lock:
            jobs = list(self._jobs.values())

        for job in jobs:
            try:
                job.start()
                logger.info("[BackgroundJobRegistry] Started: %s (required=%s)", job.name, job.required)
            except Exception as exc:
                if job.required:
                    failed_required.append(f"{job.name}: {exc}")
                    logger.error("[BackgroundJobRegistry] REQUIRED job failed to start: %s — %s", job.name, exc, exc_info=True)
                else:
                    logger.warning("[BackgroundJobRegistry] Optional job failed to start: %s — %s", job.name, exc)

        if failed_required:
            raise RuntimeError(
                f"[BackgroundJobRegistry] {len(failed_required)} required background job(s) failed to start:\n"
                + "\n".join(f"  - {e}" for e in failed_required)
            )

    def stop_all(self, timeout: float = 5.0) -> None:
        """Dừng sạch tất cả jobs khi shutdown."""
        with self._lock:
            jobs = list(self._jobs.values())
        for job in jobs:
            try:
                job.stop(timeout=timeout)
                logger.debug("[BackgroundJobRegistry] Stopped: %s", job.name)
            except Exception as exc:
                logger.warning("[BackgroundJobRegistry] Error stopping %s: %s", job.name, exc, exc_info=True)

    def status(self) -> dict[str, dict]:
        """Trả về trạng thái của tất cả jobs — dùng trong /health endpoint."""
        with self._lock:
            return {
                name: {
                    "started": job._started,
                    "required": job.required,
                    "interval_seconds": job.interval_seconds,
                    "error_count": job._error_count,
                }
                for name, job in self._jobs.items()
            }


# =============================================================================
# Global registry — import và dùng ở bất kỳ đâu
# =============================================================================
registry = BackgroundJobRegistry()


# =============================================================================
# Đăng ký các jobs BẮT BUỘC của SCP kernel
# =============================================================================

def _get_kernel_or_none():
    """Resolve the live shared TaskKernel, or None if the app has not opened one yet.

    [MACH1-FIX-1] Reality check (DNA #26): ``scp.api._shared`` never defined
    ``get_kernel`` (its PEP 562 delegation list does not include it), so the old
    ``from scp.api._shared import get_kernel`` raised ImportError on every cycle
    and the required watchdogs silently no-op'd (ImportError → pass). Resolution
    order now:
      1. scp.api._shared.get_kernel — future contract, kept first.
      2. scp.api_server._ASK_KERNEL_ADAPTERS — reuse kernels already opened by
         the running app. Reuse only: never triggers adapter initialization
         side effects (integrity check/backup) from a watchdog thread.
    """
    try:
        from scp.api._shared import get_kernel  # type: ignore[attr-defined]
        kernel = get_kernel()
        if kernel is not None:
            return kernel
    except (ImportError, AttributeError) as exc:
        # [MACH1-FIX-8 / D6 fail-loudly] Expected until scp.api._shared exposes
        # get_kernel — debug level keeps the fallback observable without noise.
        logger.debug("[MACH1-FIX-1] scp.api._shared.get_kernel unavailable (%s) — using adapter kernels", exc)
    try:
        from scp import api_server  # runtime import — safe after boot
        for adapter in list(getattr(api_server, "_ASK_KERNEL_ADAPTERS", {}).values()):
            kernel = getattr(adapter, "kernel", None)
            if kernel is not None:
                return kernel
    except Exception as exc:
        # [MACH1-FIX-8 / D6 fail-loudly] A broken fallback means the required
        # watchdogs would silently no-op — this must be visible.
        logger.warning("[MACH1-FIX-1] kernel resolver fallback failed: %s", exc, exc_info=True)
    return None


@registry.register(
    name="kernel_lease_expiry",
    interval_seconds=30,
    required=True,          # thiếu watchdog = owner lockout vĩnh viễn → PHẢI chạy
    initial_delay_seconds=15,
)
def _kernel_lease_expiry_tick() -> None:
    """Hết hạn các lease bị timeout — ngăn owner lockout vĩnh viễn."""
    # [MACH1-FIX-1] resolve the real live kernel instead of the broken
    # _shared.get_kernel import; None = app has not opened a kernel yet.
    kernel = _get_kernel_or_none()
    if kernel is not None:
        expired = kernel.expire_leases()
        if expired:
            logger.info("[Watchdog] expire_leases: %d expired", len(expired))


@registry.register(
    name="kernel_orphan_reconcile",
    interval_seconds=60,
    required=True,          # task orphan không được reconcile = task bị kẹt mãi mãi
    initial_delay_seconds=30,
)
def _kernel_orphan_reconcile_tick() -> None:
    """Reconcile các task orphan (crash, mất kết nối) → RECONCILING state."""
    # [MACH1-FIX-1] same resolver fix as _kernel_lease_expiry_tick.
    kernel = _get_kernel_or_none()
    if kernel is not None:
        orphans = kernel.auto_reconcile_orphans()
        if orphans:
            logger.info("[Watchdog] auto_reconcile_orphans: %d reconciled", len(orphans))


@registry.register(
    name="canary_token_cleanup",
    interval_seconds=86400,  # 24h
    required=False,
    initial_delay_seconds=600,
)
def _canary_cleanup_tick() -> None:
    """Dọn dẹp canary token hết hạn — ngăn memory leak."""
    try:
        from scp.api._shared import get_judge
        judge = get_judge()
        cm = getattr(judge, "canary_monitor", None)
        if cm is not None and hasattr(cm, "cleanup_expired"):
            removed = cm.cleanup_expired()
            if removed:
                logger.info("[Watchdog] canary_cleanup: removed %d expired tokens", removed)
    except Exception as exc:
        # [MACH1-FIX-8 / D6 fail-loudly] The job is optional (required=False), so
        # a failure must not abort boot — but it must be observable, otherwise
        # expired tokens leak and the registry error counter is the only trace.
        logger.warning("[Watchdog] canary_cleanup failed: %s", exc, exc_info=True)
