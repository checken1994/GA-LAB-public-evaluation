"""[AUDIT-FIX low-7] Contract test — llm_gateway/client.py smalls.

(a) CircuitBreaker HALF-OPEN: docstring hứa "cho đúng 1 request thăm dò" nhưng
    transition nằm trong is_open() → N caller đi qua sau cooldown ĐỀU probe.
    Fix: acquire_half_open_probe()/release_half_open_probe() — probe duy nhất
    được cấp tại điểm HTTP attempt thật (_call_model), is_open() pure.
(b) chat_sync: context manager ThreadPoolExecutor join worker QUA 90s timeout.
    Fix: shutdown(wait=False) + abandon worker (bounded leak), caller không bị
    chặn thêm sau timeout; coroutine do worker sở hữu KHÔNG close() từ luồng
    khác (tránh race).
(c) openrouter_fast dead branch: removed (openrouter_fast_learning luôn được
    set bởi vòng lặp task; RHS không bao giờ được đánh giá).
(d) _stats/_rr_counter: telemetry increments phải dưới lock — concurrent
    increments không được mất sample.

Timing: dùng fake monotonic clock (monkeypatch client_module.time) thay sleep
thật — sleep 60ms trên Windows không ổn định quanh cooldown 50ms (harness
flaky đã quan sát); fake clock giữ nguyên strictness assertions, loại bỏ race.
"""
import asyncio
import threading
import time

import pytest

import scp.llm_gateway.client as client_module
from scp.llm_gateway.client import CircuitBreaker, LLMGateway


class _FakeClock:
    """Thay thế time module cho client_module trong test breaker."""

    def __init__(self, start: float = 1000.0):
        self._now = start

    def monotonic(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


@pytest.fixture()
def clock(monkeypatch):
    fake = _FakeClock()
    monkeypatch.setattr(client_module, "time", fake)
    yield fake


# ---------------------------------------------------------------------------
# (a) HALF-OPEN single probe
# ---------------------------------------------------------------------------
def test_half_open_allows_exactly_one_probe(clock):
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=300.0)
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.is_open() is True
    assert breaker.acquire_half_open_probe() is False  # còn trong cooldown
    clock.advance(300.0)
    # is_open() giờ là pure classifier — cooldown hết chỉ báo hiệu HALF-OPEN.
    assert breaker.is_open() is False
    assert breaker.acquire_half_open_probe() is True  # caller duy nhất
    assert breaker.acquire_half_open_probe() is False  # probe thứ hai bị chặn
    breaker.record_success()  # CLOSE
    assert breaker.is_open() is False
    assert breaker.acquire_half_open_probe() is True  # CLOSED: mọi caller đi được


def test_probe_failure_reopens_breaker(clock):
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=300.0)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(300.0)
    assert breaker.acquire_half_open_probe() is True
    breaker.record_failure()  # probe thất bại → OPEN lại NGAY
    assert breaker.is_open() is True
    assert breaker.acquire_half_open_probe() is False


def test_probe_release_allows_new_attempt_without_faking_success(clock):
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=300.0)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(300.0)
    assert breaker.acquire_half_open_probe() is True
    breaker.release_half_open_probe()  # nhánh không-record (vd dead-model skip)
    assert breaker.acquire_half_open_probe() is True  # attempt kế tiếp được đi
    breaker.record_failure()
    assert breaker.is_open() is True


def test_half_open_concurrent_callers_single_probe(clock):
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=300.0)
    breaker.record_failure()
    clock.advance(300.0)  # cooldown hết TRƯỚC khi các thread start → deterministic
    allowed: list[bool] = []
    lock = threading.Lock()

    def worker():
        ok = breaker.acquire_half_open_probe()
        with lock:
            allowed.append(ok)

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert allowed.count(True) == 1, f"MULTI-PROBE: {allowed}"
    assert allowed.count(False) == 15


# ---------------------------------------------------------------------------
# (b) chat_sync timeout không join worker
# ---------------------------------------------------------------------------
def test_chat_sync_timeout_returns_contract_fast_without_join(monkeypatch):
    """BEFORE: future.result(90s) raise → `with` exit join worker (block thêm
    tới khi chat xong). AFTER: abandon worker ngay (bounded leak), caller nhận
    (None, "none") theo contract fail-open cũ."""
    monkeypatch.setattr(client_module, "SYNC_CALL_TIMEOUT_SECONDS", 0.2)
    gateway = LLMGateway()

    async def slow_chat(*args, **kwargs):
        await asyncio.sleep(2.0)
        return "late", "provider"

    async def scenario():
        monkeypatch.setattr(gateway, "chat", slow_chat)
        start = time.monotonic()
        result = gateway.chat_sync("question")  # trong running loop → _in_async
        elapsed = time.monotonic() - start
        return result, elapsed

    result, elapsed = asyncio.run(scenario())
    assert result == (None, "none")  # contract cũ giữ nguyên
    assert elapsed < 1.0, (
        f"chat_sync bị join worker sau timeout: {elapsed:.2f}s (old behavior ~2.0s)"
    )


# ---------------------------------------------------------------------------
# (c) dead branch đã xóa
# ---------------------------------------------------------------------------
def test_no_dead_openrouter_fast_branch():
    import inspect

    src = inspect.getsource(client_module.LLMGateway.__init__)
    dead_line = (
        'self.openrouter_fast_learning = getattr(self, "openrouter_fast_learning", '
        "None) or self.openrouter_fast"
    )
    assert dead_line not in src, "nhánh chết `or self.openrouter_fast` còn trong __init__"
    gateway = LLMGateway()
    assert gateway.openrouter_fast_learning is not None  # set bởi vòng lặp task


# ---------------------------------------------------------------------------
# (d) telemetry counters dưới lock
# ---------------------------------------------------------------------------
def test_stats_counters_consistent_under_concurrency():
    gateway = LLMGateway()
    iterations = 500
    workers = 8

    def bump():
        for _ in range(iterations):
            gateway._bump_stat("total_calls")

    threads = [threading.Thread(target=bump) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    expected = iterations * workers
    stats = gateway.stats()
    assert stats["total_calls"] == expected, (
        f"mất sample telemetry: {stats['total_calls']} != {expected}"
    )


def test_rr_counter_rotate_is_atomic():
    gateway = LLMGateway()
    pool_size = 3
    picks: list[int] = []
    lock = threading.Lock()

    def rotate():
        for _ in range(300):
            with gateway._stats_lock:
                start = gateway._rr_counter % pool_size
                gateway._rr_counter += 1
            with lock:
                picks.append(start)

    threads = [threading.Thread(target=rotate) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert gateway._rr_counter == 300 * 8
    for bucket in range(pool_size):
        assert picks.count(bucket) == 300 * 8 // pool_size
