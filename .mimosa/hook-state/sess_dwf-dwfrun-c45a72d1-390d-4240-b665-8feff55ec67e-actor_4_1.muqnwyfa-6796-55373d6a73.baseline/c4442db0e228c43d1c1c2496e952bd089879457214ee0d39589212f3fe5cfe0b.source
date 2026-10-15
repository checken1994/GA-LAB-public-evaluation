# SCP CIRCUIT: S23 — Hermetic tests cho FreeDiscoveryScheduler.
"""T07/S23 — test FreeDiscoveryScheduler (scp/core/free_discovery_scheduler.py).

Hermetic tuyệt đối: KHÔNG mạng, KHÔNG đụng cache thật của repo — mọi nguồn
refresh được inject qua constructor, entries_count inject, env điều khiển qua
monkeypatch. Không skip/xfail (FA kỷ luật test).

Phủ 6 yêu cầu thiết kế chốt của S23:
  (a) tick gọi đúng refresh cả 2 nguồn + log count
  (b) 1 nguồn raise → nguồn kia vẫn chạy + scheduler không chết
  (c) jitter trong biên ±10%
  (d) kill-switch SCP_DISCOVERY_SCHEDULER=off → không start
  (e) shutdown hủy task sạch (no leak)
  (f) interval parse lỗi → default
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time

import pytest

from scp.core.free_discovery_scheduler import (
    DEFAULT_DISCOVERY_INTERVAL_SECONDS,
    FreeDiscoveryScheduler,
    jittered_interval,
    kill_switch_off,
    parse_interval_seconds,
)

LOGGER_NAME = "scp.core.free_discovery_scheduler"


def _make_scheduler(catalog, llm, **kwargs):
    """Scheduler hermetic: nguồn refresh + entries_count đều inject."""
    kwargs.setdefault("entries_count", lambda: 1785)
    return FreeDiscoveryScheduler(catalog_refresh=catalog, llm_refresh=llm, **kwargs)


async def _spin_until(predicate, max_iterations: int = 2000) -> bool:
    for _ in range(max_iterations):
        if predicate():
            return True
        await asyncio.sleep(0)
    return False


async def _spin_until_wall_clock(predicate, timeout_seconds: float) -> bool:
    """Chờ theo wall-clock (không theo số vòng lặp event-loop).

    Tại sao: số vòng ``sleep(0)`` trong một khoảng wall-clock phụ thuộc tốc độ
    CPU/event-loop của máy. Trên runner ubuntu nhanh (pre-RC run 36102606213),
    2000 iteration kết thúc TRƯỚC timer jitter 9-11ms của tick thứ hai (timer
    Linux bắn đúng giờ, khác với Windows vốn bắn sớm do quantization) → test
    fail dù scheduler chạy đúng thiết kế. Deadline wall-clock là deterministic
    trên mọi máy; semantics assertion giữ nguyên (scheduler phải tick tiếp).
    """
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.005)
    return predicate()


# ---------------------------------------------------------------------------
# (a) Tick gọi đúng refresh cả 2 nguồn + log count
# ---------------------------------------------------------------------------
def test_tick_refreshes_both_sources_and_logs_counts(caplog):
    calls = []

    def catalog_refresh():
        calls.append("catalog")
        return {"ok": True, "served": "network", "count": 1785}

    def llm_refresh():
        calls.append("llm")
        return {"ok": True, "count": 321}

    scheduler = _make_scheduler(catalog_refresh, llm_refresh)
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        summary = asyncio.run(scheduler.tick())

    assert calls == ["catalog", "llm"], "tick phải gọi CẢ HAI nguồn"
    assert summary["catalog"]["ok"] is True
    assert summary["catalog"]["count"] == 1785
    assert summary["llm_models"]["ok"] is True
    assert summary["llm_models"]["count"] == 321
    assert summary["entries_before"] == 1785
    assert scheduler.last_tick_result is summary
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "count=1785" in text, "phải log entries count của catalog"
    assert "models=321" in text, "phải log models count của LLM catalog"


def test_tick_returns_ok_false_when_source_reports_failure_dict():
    def catalog_refresh():
        return {"ok": False, "reason": "RuntimeError", "served": "cache", "count": 0}

    scheduler = _make_scheduler(catalog_refresh, lambda: {"ok": True, "count": 5})
    summary = asyncio.run(scheduler.tick())
    assert summary["catalog"]["ok"] is False
    assert summary["llm_models"]["ok"] is True


# ---------------------------------------------------------------------------
# (b) 1 nguồn raise → nguồn kia vẫn chạy + scheduler không chết
# ---------------------------------------------------------------------------
def test_one_source_raising_does_not_block_the_other(caplog):
    def catalog_refresh():
        raise RuntimeError("catalog network down")

    llm_calls = []

    def llm_refresh():
        llm_calls.append(1)
        return {"ok": True, "count": 42}

    scheduler = _make_scheduler(catalog_refresh, llm_refresh)
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        summary = asyncio.run(scheduler.tick())
    assert len(llm_calls) == 1, "nguồn LLM vẫn phải chạy dù catalog raise"
    assert summary["catalog"]["ok"] is False
    assert summary["catalog"]["error"] == "RuntimeError"
    assert summary["llm_models"]["ok"] is True
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "source free_api_catalog FAILED" in text


def test_run_forever_survives_repeated_source_crashes():
    """Nguồn catalog raise ở MỌI tick → run_forever vẫn sống (không chết)."""
    catalog_calls = []
    llm_calls = []

    def catalog_refresh():
        catalog_calls.append(1)
        raise RuntimeError("boom every tick")

    def llm_refresh():
        llm_calls.append(1)
        return {"ok": True, "count": 7}

    async def scenario():
        scheduler = _make_scheduler(
            catalog_refresh, llm_refresh, interval_seconds=0.01
        )
        task = scheduler.start()
        assert task is not None
        # tick đầu chạy ngay; chờ >= 2 tick LLM thành công rồi mới cancel.
        # Deadline wall-clock 10s ≈ 1000x biên trên của interval jittered
        # (9-11ms) — dư sức cho runner chậm, vẫn fail-closed nếu scheduler
        # thật sự chết (đây là điểm khác biệt so với iteration budget cũ).
        waited = await _spin_until_wall_clock(lambda: len(llm_calls) >= 2, timeout_seconds=10.0)
        assert waited, "scheduler phải tiếp tục tick sau khi nguồn catalog chết"
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        return task

    task = asyncio.run(scenario())
    assert task.cancelled(), (
        "run_forever bị kết thúc bởi exception thay vì cancel → scheduler đã chết"
    )
    assert len(catalog_calls) >= 2 and len(llm_calls) >= 2


# ---------------------------------------------------------------------------
# (c) Jitter trong biên ±10%
# ---------------------------------------------------------------------------
class _FixedRng:
    def __init__(self, value):
        self.value = value

    def uniform(self, lo, hi):
        return self.value


def test_jitter_stays_within_ten_percent_bounds():
    base = 21600.0
    # exact endpoints
    assert jittered_interval(base, 0.10, _FixedRng(base)) == pytest.approx(base)
    assert jittered_interval(base, 0.10, _FixedRng(0.0)) == pytest.approx(base * 0.9)
    assert jittered_interval(base, 0.10, _FixedRng(base * 2)) == pytest.approx(base * 1.1)
    # statistical bounds với rng thật
    values = [jittered_interval(base, 0.10) for _ in range(500)]
    assert min(values) >= base * 0.9
    assert max(values) <= base * 1.1
    assert any(v < base for v in values) and any(v > base for v in values)


def test_run_forever_sleeps_use_jittered_interval():
    durations = []
    catalog_calls = []

    async def fake_sleep(seconds):
        durations.append(seconds)
        await asyncio.sleep(0)

    async def scenario():
        scheduler = _make_scheduler(
            lambda: (catalog_calls.append(1), {"ok": True, "count": 1})[1],
            lambda: {"ok": True, "count": 1},
            interval_seconds=100.0,
            rng=_FixedRng(90.0),  # lower bound của ±10%
            sleep=fake_sleep,
        )
        task = asyncio.create_task(scheduler.run_forever())
        # Tick đầu phải chạy TRƯỚC lần sleep đầu (tick đầu immediate).
        first_ticked = await _spin_until(lambda: len(durations) >= 1)
        assert first_ticked, "run_forever phải tick ngay rồi mới sleep"
        assert len(catalog_calls) >= 1
        second = await _spin_until(lambda: len(durations) >= 2)
        assert second
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert durations[0] == pytest.approx(90.0)
    for duration in durations:
        assert 100.0 * 0.9 <= duration <= 100.0 * 1.1


# ---------------------------------------------------------------------------
# (d) Kill-switch off → không start
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("switch_value", ["off", "0", "false", "OFF", " False "])
def test_kill_switch_off_prevents_start(monkeypatch, caplog, switch_value):
    monkeypatch.setenv("SCP_DISCOVERY_SCHEDULER", switch_value)
    assert kill_switch_off() is True

    async def scenario():
        scheduler = _make_scheduler(
            lambda: {"ok": True, "count": 0}, lambda: {"ok": True, "count": 0}
        )
        return scheduler.start()

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        task = asyncio.run(scenario())
    assert task is None, "kill-switch off → KHÔNG được tạo task"
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "DISABLED" in text


def test_kill_switch_default_is_on(monkeypatch):
    monkeypatch.delenv("SCP_DISCOVERY_SCHEDULER", raising=False)
    assert kill_switch_off() is False
    monkeypatch.setenv("SCP_DISCOVERY_SCHEDULER", "1")
    assert kill_switch_off() is False


# ---------------------------------------------------------------------------
# (e) Shutdown hủy task sạch (no leak)
# ---------------------------------------------------------------------------
def test_stop_cancels_task_cleanly_and_is_idempotent():
    async def scenario():
        scheduler = _make_scheduler(
            lambda: {"ok": True, "count": 1},
            lambda: {"ok": True, "count": 1},
            interval_seconds=3600.0,
        )
        task = scheduler.start()
        assert task is not None and not task.done()
        assert scheduler.running_task is task
        await asyncio.wait_for(scheduler.stop(timeout=5.0), timeout=15)
        assert task.done() and task.cancelled(), "task phải bị hủy sạch"
        assert scheduler.running_task is None
        # stop lần 2 (task đã None) → no-op, không raise
        await scheduler.stop()
        # start lại sau stop → task mới chạy được
        revived = scheduler.start()
        assert revived is not None and revived is not task
        await asyncio.wait_for(scheduler.stop(timeout=5.0), timeout=15)

    asyncio.run(scenario())


def test_stop_when_never_started_is_noop():
    scheduler = _make_scheduler(
        lambda: {"ok": True, "count": 0}, lambda: {"ok": True, "count": 0}
    )
    result = asyncio.run(scheduler.stop())
    # [TQ-05] No-op stop must return None and leave the task slot cleared.
    assert result is None, result
    assert scheduler._task is None

# ---------------------------------------------------------------------------
# (f) Interval parse lỗi → default
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "bad_value",
    ["abc", "", "   ", "nan", "inf", "-inf", "-5", "0", "12abc", "1e999"],
)
def test_interval_parse_error_falls_back_to_default(monkeypatch, bad_value):
    monkeypatch.setenv("SCP_DISCOVERY_INTERVAL_SECONDS", bad_value)
    assert parse_interval_seconds() == DEFAULT_DISCOVERY_INTERVAL_SECONDS
    scheduler = _make_scheduler(
        lambda: {"ok": True, "count": 0}, lambda: {"ok": True, "count": 0}
    )
    assert scheduler.interval_seconds == DEFAULT_DISCOVERY_INTERVAL_SECONDS


def test_interval_valid_value_and_unset(monkeypatch):
    monkeypatch.delenv("SCP_DISCOVERY_INTERVAL_SECONDS", raising=False)
    assert parse_interval_seconds() == DEFAULT_DISCOVERY_INTERVAL_SECONDS
    monkeypatch.setenv("SCP_DISCOVERY_INTERVAL_SECONDS", "60")
    assert parse_interval_seconds() == 60.0
    # explicit constructor arg thắng env (env đang hỏng cũng không ảnh hưởng)
    monkeypatch.setenv("SCP_DISCOVERY_INTERVAL_SECONDS", "garbage")
    scheduler = _make_scheduler(
        lambda: {"ok": True, "count": 0}, lambda: {"ok": True, "count": 0},
        interval_seconds=120,
    )
    assert scheduler.interval_seconds == 120.0


def test_start_logs_interval_and_first_tick_is_immediate(caplog):
    """Bằng chứng boot: start log interval; tick đầu chạy ngay không chờ interval."""
    catalog_calls = []

    async def scenario():
        scheduler = _make_scheduler(
            lambda: (catalog_calls.append(1), {"ok": True, "count": 1785})[1],
            lambda: {"ok": True, "count": 9},
            interval_seconds=3600.0,
        )
        with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
            task = scheduler.start()
        assert task is not None
        started = await _spin_until(lambda: len(catalog_calls) >= 1)
        assert started, "tick đầu phải chạy NGAY khi start (không chờ interval)"
        await asyncio.wait_for(scheduler.stop(timeout=5.0), timeout=15)

    asyncio.run(scenario())
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "FreeDiscoveryScheduler started" in text
    assert "interval=3600s" in text
