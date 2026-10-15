from __future__ import annotations

from scp.llm_gateway.client import CircuitBreaker


def test_default_threshold_and_initial_state() -> None:
    breaker = CircuitBreaker(cooldown_seconds=30)

    assert breaker.failure_threshold == 3
    assert breaker._consecutive_failures == 0
    assert breaker.is_open() is False
    breaker.record_failure()
    assert breaker.is_open() is False
    breaker.record_failure()
    assert breaker.is_open() is False
    breaker.record_failure()
    assert breaker.is_open() is True


def test_threshold_one_is_valid_and_opens_on_first_failure() -> None:
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=30)
    breaker.record_failure()
    assert breaker.is_open() is True
