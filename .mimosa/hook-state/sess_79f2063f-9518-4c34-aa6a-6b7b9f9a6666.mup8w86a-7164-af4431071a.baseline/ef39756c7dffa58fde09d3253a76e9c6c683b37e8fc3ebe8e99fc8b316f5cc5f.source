# SCP CIRCUIT: S23 — Free Discovery Scheduler (blueprint name: free_discovery_scheduler)
"""Background scheduler that periodically refreshes SCP's free discovery data.

TẠI SAO module này tồn tại (S23, owner directive "tự động tìm và cập nhật
hơn 1000 API"):

  `FreeAPICatalog.refresh(force)` đã chạy được (egress mở, ~1,785 entries)
  NHƯNG không có gì TỰ ĐỘNG gọi nó: blueprint module
  ``scp/core/free_discovery_scheduler.py`` chưa từng được xây, search/entries
  không lazy-refresh theo lịch, và catalog chỉ được fetch khi admin gọi route
  ``/v104/free-apis/search`` trên catalog rỗng. Kết quả: dữ liệu "hơn 1000
  API" tồn tại nhưng vòng tự-cập-nật của nó không chạy (PASS ≠ TRUE pattern).

Thiết kế (chốt bởi orchestrator):
  - 1 asyncio task nền, tick ĐẦU chạy NGAY khi boot, các tick sau cách nhau
    ``interval`` (mặc định 6h = 21600s) với jitter ±10% (tránh herd effect
    khi nhiều instance boot cùng lúc).
  - Mỗi tick refresh ĐỘC LẬP 2 nguồn:
      (1) FreeAPICatalog (free APIs, GitHub raw allowlisted host)
      (2) OpenRouter free-model catalog qua ``refresh_free_catalog`` — CHỈ
          GỌI seam có sẵn, KHÔNG sửa scp/llm_gateway/free_catalog.py.
  - Fail độc lập: 1 nguồn chết (raise) KHÔNG chặn nguồn kia, mọi lỗi log
    WARNING, scheduler không bao giờ chết vì tick (loop-level guard).
  - Kill-switch: ``SCP_DISCOVERY_SCHEDULER=off`` (| 0 | false) → không start.
  - Interval: ``SCP_DISCOVERY_INTERVAL_SECONDS`` (default 21600; parse lỗi
    hoặc <= 0 / NaN / Inf → fallback default — fail-safe, không busy-loop).
  - Blocking refresh chạy qua ``asyncio.to_thread``: refresh của catalog là
    urllib blocking (timeout 25s) và refresh_free_catalog là httpx sync
    (timeout 5s) — chạy thẳng trong event loop sẽ đóng băng toàn server.

Refresh-on-404 (phần 3 của thiết kế): AUDIT-FIRST đã tìm và KHÔNG có seam
sạch — caller duy nhất của catalog là route đọc (v104_routes.py status/search,
chỉ lazy-refresh khi catalog rỗng), không có đường nào "caller report
model/API 404" quay lại catalog. Theo đúng phạm vi: KHÔNG chế interface mới,
phần này BỎ (ghi trong reports/expert-panel/S23-discovery-scheduler.md).
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import os
import random
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("scp.core.free_discovery_scheduler")

DEFAULT_DISCOVERY_INTERVAL_SECONDS = 21600.0  # 6h (chốt thiết kế S23)
DEFAULT_JITTER_RATIO = 0.10  # ±10%
_KILL_SWITCH_VALUES = {"0", "false", "off"}


def kill_switch_off() -> bool:
    """True khi SCP_DISCOVERY_SCHEDULER tắt rõ ràng (default: bật)."""
    raw = os.environ.get("SCP_DISCOVERY_SCHEDULER", "on")
    return str(raw).strip().lower() in _KILL_SWITCH_VALUES


def parse_interval_seconds(raw: Any = None) -> float:
    """Parse SCP_DISCOVERY_INTERVAL_SECONDS; mọi giá trị không hợp lệ → default.

    Hợp lệ: số dương hữu hạn. Parse lỗi (ValueError/TypeError), <= 0, NaN,
    Inf đều coi là cấu hình hỏng → trả default (fail-safe: scheduler vẫn chạy
    đúng nhịp 6h thay vì busy-loop hoặc chết).
    """
    if raw is None:
        raw = os.environ.get("SCP_DISCOVERY_INTERVAL_SECONDS")
    if raw is None:
        return DEFAULT_DISCOVERY_INTERVAL_SECONDS
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_DISCOVERY_INTERVAL_SECONDS
    if not math.isfinite(value) or value <= 0:
        return DEFAULT_DISCOVERY_INTERVAL_SECONDS
    return value


def jittered_interval(base: float, ratio: float = DEFAULT_JITTER_RATIO, rng: Any = None) -> float:
    """base * (1 ± ratio), bị chặn trong [base*(1-ratio), base*(1+ratio)]."""
    if ratio < 0:
        ratio = 0.0
    rng = rng if rng is not None else random
    lo = base * (1.0 - ratio)
    hi = base * (1.0 + ratio)
    try:
        value = float(rng.uniform(lo, hi))
    except Exception:  # rng hỏng → không jitter (an toàn hơn là chết)
        logger.debug("jittered_interval ignored", exc_info=True)
        return base
    return min(max(value, lo), hi)


class FreeDiscoveryScheduler:
    """Async background scheduler: tick đầu chạy ngay, sau đó interval ± jitter."""

    def __init__(
        self,
        catalog_refresh: Callable[[], Any] | None = None,
        llm_refresh: Callable[[], Any] | None = None,
        interval_seconds: float | None = None,
        jitter_ratio: float = DEFAULT_JITTER_RATIO,
        rng: Any = None,
        sleep: Callable[[float], Any] = asyncio.sleep,
        entries_count: Callable[[], int] | None = None,
    ):
        self._catalog_refresh = catalog_refresh or self._default_catalog_refresh
        self._llm_refresh = llm_refresh or self._default_llm_refresh
        self._entries_count = entries_count or self._default_entries_count
        self._interval = parse_interval_seconds(interval_seconds)
        self._jitter_ratio = max(0.0, float(jitter_ratio))
        self._rng = rng if rng is not None else random
        self._sleep = sleep
        self._task: asyncio.Task | None = None
        self.last_tick_result: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Default sources (production wiring; tests inject fakes)
    # ------------------------------------------------------------------
    @staticmethod
    def _default_catalog_refresh() -> dict[str, Any]:
        # force=True: scheduler ĐÓ là nhịp cập nhật 6h của catalog; TTL 24h
        # bên trong refresh() chỉ phục vụ đường lazy của caller (nếu không
        # force thì 3/4 tick sẽ là no-op cache_fresh → mất ý nghĩa "tự động
        # cập nhật").
        from scp.data_sources.free_api_catalog import get_catalog

        catalog = get_catalog(data_dir=os.environ.get("SCP_DATA_DIR", "data"))
        return catalog.refresh(force=True)

    @staticmethod
    def _default_entries_count() -> int:
        from scp.data_sources.free_api_catalog import get_catalog

        return len(get_catalog(data_dir=os.environ.get("SCP_DATA_DIR", "data")).entries())

    @staticmethod
    def _default_llm_refresh() -> dict[str, Any]:
        # CHỈ GỌI seam có sẵn trong scp/llm_gateway/free_catalog.py (không sửa
        # file đó). Count đọc từ gateway client (read-only) để log models count.
        from scp.llm_gateway.free_catalog import refresh_free_catalog

        ok = bool(refresh_free_catalog(force=True))
        count: int | None = None
        if ok:
            with contextlib.suppress(Exception):
                from scp.llm_gateway import client as _gw_client

                count = len(getattr(_gw_client, "OPENROUTER_FREE_MODELS", []) or [])
        return {"ok": ok, "count": count}

    # ------------------------------------------------------------------
    # Tick — fail độc lập từng nguồn, không bao giờ raise
    # ------------------------------------------------------------------
    async def _run_source(self, name: str, fn: Callable[[], Any]) -> dict[str, Any]:
        try:
            result = await asyncio.to_thread(fn)
        except Exception as exc:  # noqa: BLE001 — 1 nguồn chết không chặn nguồn kia
            logger.warning("[S23-DISCOVERY] source %s FAILED (%s: %s)", name, type(exc).__name__, str(exc)[:200])
            return {"source": name, "ok": False, "error": type(exc).__name__}
        if isinstance(result, dict):
            ok = bool(result.get("ok", result.get("success", False)))
            count = result.get("count", result.get("models_count"))
            return {"source": name, "ok": ok, "count": count, "detail": str(result.get("served", result.get("reason", "")))[:80]}
        return {"source": name, "ok": bool(result), "count": None}

    async def tick(self) -> dict[str, Any]:
        """Một nhịp refresh cả 2 nguồn (độc lập). Trả summary, không raise."""
        entries_before: int | None = None
        with contextlib.suppress(Exception):
            entries_before = int(self._entries_count())

        catalog_res = await self._run_source("free_api_catalog", self._catalog_refresh)
        llm_res = await self._run_source("llm_free_catalog", self._llm_refresh)

        summary = {
            "tick_at": time.time(),
            "entries_before": entries_before,
            "catalog": catalog_res,
            "llm_models": llm_res,
        }
        self.last_tick_result = summary
        logger.info(
            "[S23-DISCOVERY] tick: free_api_catalog ok=%s count=%s (before=%s, %s) | llm_free_catalog ok=%s models=%s",
            catalog_res.get("ok"),
            catalog_res.get("count"),
            entries_before,
            catalog_res.get("detail") or "-",
            llm_res.get("ok"),
            llm_res.get("count"),
        )
        return summary

    # ------------------------------------------------------------------
    # Loop / lifecycle
    # ------------------------------------------------------------------
    async def run_forever(self) -> None:
        """Tick đầu CHẠY NGAY, sau đó sleep interval ± jitter lặp vô hạn.

        Loop-level guard: bất kỳ exception nào từ tick đều bị nuốt (log
        WARNING) — scheduler không được chết vì một tick hỏng.
        """
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — scheduler không được chết
                logger.warning("[S23-DISCOVERY] tick crashed (non-fatal): %s", exc)
            await self._sleep(jittered_interval(self._interval, self._jitter_ratio, self._rng))

    def start(self) -> asyncio.Task | None:
        """Start background task. Kill-switch off → None (không start)."""
        if kill_switch_off():
            logger.info("[S23-DISCOVERY] scheduler DISABLED by SCP_DISCOVERY_SCHEDULER")
            return None
        if self._task is not None and not self._task.done():
            return self._task
        self._task = asyncio.create_task(self.run_forever(), name="scp-free-discovery-scheduler")
        logger.info(
            "[S23-DISCOVERY] FreeDiscoveryScheduler started (interval=%.0fs ±%.0f%%, first tick immediate)",
            self._interval,
            self._jitter_ratio * 100,
        )
        return self._task

    async def stop(self, timeout: float = 5.0) -> None:
        """Hủy task sạch (no leak): cancel + await, nuốt CancelledError."""
        task, self._task = self._task, None
        if task is None or task.done():
            return
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=timeout)
        except asyncio.CancelledError:
            pass  # hậu quả mong muốn của cancel()
        except asyncio.TimeoutError:
            logger.warning("[S23-DISCOVERY] stop(): task did not finish within %.1fs", timeout)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[S23-DISCOVERY] stop(): unexpected %s", exc)

    @property
    def interval_seconds(self) -> float:
        return self._interval

    @property
    def running_task(self) -> asyncio.Task | None:
        return self._task
