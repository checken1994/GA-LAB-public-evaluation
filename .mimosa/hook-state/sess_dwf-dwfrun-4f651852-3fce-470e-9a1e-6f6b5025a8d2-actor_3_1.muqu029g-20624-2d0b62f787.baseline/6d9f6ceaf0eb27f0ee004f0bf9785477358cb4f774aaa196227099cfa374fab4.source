"""[S21] Hedged LLM race — first-result-wins, attempt deadline, hedge cap.

Owner directive: "khi LLM trả kết quả chậm khoảng 10s -> chuyển sang LLM khác
hoặc API khác". Contract proven here (hermetic — fake provider in-process,
không gọi mạng thật; T05 conftest fail-closed trên mọi HTTP thật):

  a) Provider A chậm quá attempt deadline → provider B được bắn SONG SONG;
     B thắng; A KHÔNG bị hủy trước khi B về đích (chỉ hủy ở dọn dẹp).
  b) A trả sau deadline nhưng trước B (B đã được bắn) → vẫn nhận A.
  c) Cả hai quá hedge cap → fail-closed (None + label rõ), không treo.
  d) SCP_LLM_HEDGE=off → tuần tự cũ, KHÔNG fire song song.
  e) Env parse lỗi/0/âm/non-finite → default (10s/90s); kill-switch off.
  f) Telemetry: log INFO hedge-fire (provider chậm + provider được bắn) và
     log race-winner; stats hedge_fires/hedge_wins cập nhật.
"""

from __future__ import annotations

import asyncio
import logging
import time

import pytest

from scp.llm_gateway.client import CircuitBreaker, LLMGateway, _hedge_settings


class FakeHedgeProvider:
    """Provider giả in-process: sleep(delay) rồi trả answer hoặc error.

    Ghi event start/answered/cancelled để chứng minh thứ tự thời gian thực
    (A không bị hủy trước khi B thắng, v.v.) — không đụng httpx/network.
    """

    def __init__(
        self,
        name: str,
        delay: float = 0.0,
        answer: str | None = None,
        error: str | None = None,
        events: list[str] | None = None,
    ):
        self.PROVIDER_NAME = name
        self.enabled = True
        self._breaker = CircuitBreaker()
        self._delay = delay
        self._answer = answer
        self._error = error
        self.events = events if events is not None else []

    async def chat(self, question, context="", system_prompt="", prioritize_free=False):
        self.events.append(f"{self.PROVIDER_NAME}:start")
        try:
            if self._delay:
                await asyncio.sleep(self._delay)
            self.events.append(f"{self.PROVIDER_NAME}:answered")
            if self._error is not None:
                return None, self._error
            return self._answer, f"{self.PROVIDER_NAME}:model"
        except asyncio.CancelledError:
            self.events.append(f"{self.PROVIDER_NAME}:cancelled")
            raise


def _make_gateway(monkeypatch, providers, **env):
    """Gateway thật + chain provider giả (instance attribute shadowing)."""
    for name in ("SCP_LLM_HEDGE", "SCP_LLM_ATTEMPT_TIMEOUT_SECONDS", "SCP_LLM_HEDGE_MAX_SECONDS"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    gateway = LLMGateway()
    monkeypatch.setattr(gateway, "_provider_chain", lambda _task: providers, raising=False)
    return gateway


# ---------------------------------------------------------------
# (a) Provider đầu chậm quá deadline → B bắn song song, B thắng,
#     A chỉ bị hủy SAU KHI B đã thắng (dọn dẹp).
# ---------------------------------------------------------------
def test_hedge_slow_first_provider_second_wins(monkeypatch):
    events: list[str] = []
    slow = FakeHedgeProvider("slowA", delay=15.0, answer="A-late", events=events)
    fast = FakeHedgeProvider("fastB", delay=0.05, answer="B-fast", events=events)
    gateway = _make_gateway(
        monkeypatch,
        [slow, fast],
        SCP_LLM_HEDGE="on",
        SCP_LLM_ATTEMPT_TIMEOUT_SECONDS="1",
        SCP_LLM_HEDGE_MAX_SECONDS="5",
    )

    t0 = time.monotonic()
    answer, label = asyncio.run(gateway.chat("q", task="chat"))
    elapsed = time.monotonic() - t0

    assert answer == "B-fast"
    assert label == "fastB:model"
    assert elapsed < 15.0  # không đợi trọn sleep(A)=15s
    assert gateway._stats["hedge_fires"] == 1
    # B được bắn SAU khi A đã chạy (song song, không hủy A trước):
    assert events.index("slowA:start") < events.index("fastB:start")
    # A KHÔNG bị hủy trước khi B thắng — chỉ bị hủy ở bước dọn dẹp:
    assert events.index("fastB:answered") < events.index("slowA:cancelled")


# ---------------------------------------------------------------
# (b) A trả SAU deadline nhưng TRƯỚC B → vẫn nhận A (không hủy oan).
# ---------------------------------------------------------------
def test_hedge_first_provider_wins_after_deadline_before_second(monkeypatch):
    events: list[str] = []
    first = FakeHedgeProvider("firstA", delay=1.0, answer="A-answer", events=events)
    second = FakeHedgeProvider("secondB", delay=3.0, answer="B-answer", events=events)
    gateway = _make_gateway(
        monkeypatch,
        [first, second],
        SCP_LLM_HEDGE="on",
        SCP_LLM_ATTEMPT_TIMEOUT_SECONDS="0.5",
        SCP_LLM_HEDGE_MAX_SECONDS="10",
    )

    answer, label = asyncio.run(gateway.chat("q", task="chat"))

    assert answer == "A-answer"
    assert label == "firstA:model"
    # B đã được bắn do A vượt deadline (hedge đã fire đúng 1 lần)...
    assert "secondB:start" in events
    assert gateway._stats["hedge_fires"] == 1
    # ...nhưng A vẫn thắng vì về trước B; B chỉ bị hủy sau đó.
    assert events.index("firstA:answered") < events.index("secondB:cancelled")
    assert gateway._stats["hedge_wins"] == 1


# ---------------------------------------------------------------
# (c) Cả hai quá hedge cap → fail-closed None + label rõ, không treo.
# ---------------------------------------------------------------
def test_hedge_cap_exceeded_fails_closed(monkeypatch):
    events: list[str] = []
    a = FakeHedgeProvider("capA", delay=10.0, answer="A", events=events)
    b = FakeHedgeProvider("capB", delay=10.0, answer="B", events=events)
    gateway = _make_gateway(
        monkeypatch,
        [a, b],
        SCP_LLM_HEDGE="on",
        SCP_LLM_ATTEMPT_TIMEOUT_SECONDS="0.3",
        SCP_LLM_HEDGE_MAX_SECONDS="1",
    )

    t0 = time.monotonic()
    answer, label = asyncio.run(gateway.chat("q", task="chat"))
    elapsed = time.monotonic() - t0

    assert answer is None
    assert label == "hedge_cap_exceeded"
    assert elapsed < 9.0  # cả hai sleep 10s — không được treo tới đó
    assert gateway._stats["hedge_caps"] == 1
    assert gateway._stats["failures"] == 1
    # Cả hai được bắn rồi bị hủy sạch ở dọn dẹp (không rò rỉ task).
    assert events.count("capA:cancelled") == 1
    assert events.count("capB:cancelled") == 1


# ---------------------------------------------------------------
# (d) SCP_LLM_HEDGE=off → tuần tự cũ, không fire song song.
# ---------------------------------------------------------------
def test_hedge_off_runs_sequential(monkeypatch):
    concurrency = {"current": 0, "max": 0}
    events: list[str] = []

    class TrackingProvider:
        def __init__(self, name, delay, answer=None, error=None):
            self.PROVIDER_NAME = name
            self.enabled = True
            self._breaker = CircuitBreaker()
            self._delay = delay
            self._answer = answer
            self._error = error

        async def chat(self, question, context="", system_prompt="", prioritize_free=False):
            events.append(f"{self.PROVIDER_NAME}:start")
            concurrency["current"] += 1
            concurrency["max"] = max(concurrency["max"], concurrency["current"])
            try:
                await asyncio.sleep(self._delay)
                events.append(f"{self.PROVIDER_NAME}:end")
                if self._error is not None:
                    return None, self._error
                return self._answer, f"{self.PROVIDER_NAME}:model"
            finally:
                concurrency["current"] -= 1

    failing = TrackingProvider("seqA", delay=0.2, error="simulated-failure")
    working = TrackingProvider("seqB", delay=0.2, answer="B-answer")
    gateway = _make_gateway(
        monkeypatch,
        [failing, working],
        SCP_LLM_HEDGE="off",
        SCP_LLM_ATTEMPT_TIMEOUT_SECONDS="0.05",
        SCP_LLM_HEDGE_MAX_SECONDS="10",
    )

    answer, label = asyncio.run(gateway.chat("q", task="chat"))

    assert answer == "B-answer"
    assert label == "seqB:model"
    assert concurrency["max"] == 1  # KHÔNG bao giờ có 2 provider chạy song song
    # B chỉ bắt đầu SAU khi A kết thúc (tuần tự, kể cả khi A lỗi trước deadline ảo).
    assert events == ["seqA:start", "seqA:end", "seqB:start", "seqB:end"]
    assert gateway._stats["hedge_fires"] == 0


# ---------------------------------------------------------------
# (e) Env parse fail-closed: lỗi/0/âm/non-finite → default; kill-switch.
# ---------------------------------------------------------------
@pytest.mark.parametrize("bad", ["abc", "", "   ", "0", "-5", "nan", "inf", "-inf"])
def test_hedge_env_parse_invalid_falls_back_to_defaults(monkeypatch, bad):
    monkeypatch.setenv("SCP_LLM_HEDGE", "on")
    monkeypatch.setenv("SCP_LLM_ATTEMPT_TIMEOUT_SECONDS", bad)
    monkeypatch.setenv("SCP_LLM_HEDGE_MAX_SECONDS", bad)
    enabled, deadline, cap = _hedge_settings()
    assert enabled is True
    assert (deadline, cap) == (10.0, 90.0)


def test_hedge_env_parse_valid_and_unset(monkeypatch):
    monkeypatch.delenv("SCP_LLM_ATTEMPT_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("SCP_LLM_HEDGE_MAX_SECONDS", raising=False)
    monkeypatch.delenv("SCP_LLM_HEDGE", raising=False)
    assert _hedge_settings() == (True, 10.0, 90.0)

    monkeypatch.setenv("SCP_LLM_ATTEMPT_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("SCP_LLM_HEDGE_MAX_SECONDS", "45")
    assert _hedge_settings() == (True, 2.5, 45.0)


def test_hedge_kill_switch_values(monkeypatch):
    for off_value in ("off", "OFF", "0", "false", "no"):
        monkeypatch.setenv("SCP_LLM_HEDGE", off_value)
        assert _hedge_settings()[0] is False, off_value
    for on_value in ("on", "1", "true", "", "anything"):
        monkeypatch.setenv("SCP_LLM_HEDGE", on_value)
        assert _hedge_settings()[0] is True, on_value


def test_hedge_invalid_deadline_env_uses_default_behaviorally(monkeypatch):
    """Deadline env lỗi (0) → default 10s: provider lỗi nhanh vẫn failover
    tuần tự (không fire oan trước 10s), chứng minh default được áp dụng."""
    events: list[str] = []
    failing = FakeHedgeProvider("fastfailA", delay=0.05, error="simulated-failure", events=events)
    working = FakeHedgeProvider("afterfailB", delay=0.05, answer="B-answer", events=events)
    gateway = _make_gateway(
        monkeypatch,
        [failing, working],
        SCP_LLM_HEDGE="on",
        SCP_LLM_ATTEMPT_TIMEOUT_SECONDS="0",  # lỗi → default 10s
        SCP_LLM_HEDGE_MAX_SECONDS="15",
    )

    answer, label = asyncio.run(gateway.chat("q", task="chat"))

    assert (answer, label) == ("B-answer", "afterfailB:model")
    assert gateway._stats["hedge_fires"] == 0  # 0.05s << deadline 10s → không fire
    # Provider lỗi → failover NGAY sang B (không đợi deadline).
    assert events.index("fastfailA:answered") < events.index("afterfailB:start")


# ---------------------------------------------------------------
# (f) Telemetry: log INFO hedge-fire + race winner.
# ---------------------------------------------------------------
def test_hedge_telemetry_logs_fire_and_winner(monkeypatch, caplog):
    events: list[str] = []
    slow = FakeHedgeProvider("slowA", delay=2.0, answer="A-late", events=events)
    quick = FakeHedgeProvider("quickB", delay=0.05, answer="B-fast", events=events)
    gateway = _make_gateway(
        monkeypatch,
        [slow, quick],
        SCP_LLM_HEDGE="on",
        SCP_LLM_ATTEMPT_TIMEOUT_SECONDS="0.3",
        SCP_LLM_HEDGE_MAX_SECONDS="5",
    )

    with caplog.at_level(logging.INFO, logger="scp.llm_gateway"):
        answer, label = asyncio.run(gateway.chat("q", task="chat"))

    assert (answer, label) == ("B-fast", "quickB:model")
    hedge_logs = [r.getMessage() for r in caplog.records if "[S21 HEDGE]" in r.getMessage()]
    # Log fire: nêu provider chậm vượt deadline + provider được bắn thêm.
    assert any("fire" in msg and "slowA" in msg and "quickB" in msg for msg in hedge_logs)
    # Log winner: nêu provider thắng.
    assert any("race won by" in msg and "quickB" in msg for msg in hedge_logs)
    assert gateway._stats["hedge_fires"] == 1
    assert gateway._stats["hedge_wins"] == 1


def test_hedge_no_fire_when_first_provider_fast(monkeypatch):
    """Provider đầu về < deadline → không hedge, không hủy ai (đường lành)."""
    events: list[str] = []
    fast = FakeHedgeProvider("quickA", delay=0.05, answer="A-fast", events=events)
    unused = FakeHedgeProvider("idleB", delay=5.0, answer="B", events=events)
    gateway = _make_gateway(
        monkeypatch,
        [fast, unused],
        SCP_LLM_HEDGE="on",
        SCP_LLM_ATTEMPT_TIMEOUT_SECONDS="1",
        SCP_LLM_HEDGE_MAX_SECONDS="5",
    )

    answer, label = asyncio.run(gateway.chat("q", task="chat"))

    assert (answer, label) == ("A-fast", "quickA:model")
    assert "idleB:start" not in events  # B chưa bao giờ được bắn
    assert gateway._stats["hedge_fires"] == 0
    assert "quickA:cancelled" not in events  # winner không bị hủy oan
