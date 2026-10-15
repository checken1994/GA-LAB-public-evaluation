"""[SEC-FIX auth-eviction 2026-09-26] Regression tests for the auth rate limiter.

FA-09 provenance: probe (temp dir) confirmed BEFORE fix:
  - 5 failed 401s from "unknown"-client requests blocked the whole "unknown"
    bucket (shared-bucket, fail-closed — documented limitation).
  - Eviction popped `next(iter(_auth_failures))` (pure insertion order): an
    ACTIVE attacker bucket carrying the most recent failures was evicted
    first (its position in the dict is fixed since creation), RESETING the
    attacker's throttle budget, while stale one-failure buckets lingered.

Fixed contract:
  - eviction targets the bucket whose most recent failure is the OLDEST
  - an active attacker's failure history is never wiped by eviction
  - shared "unknown" bucket remains fail-closed (documented; XFF is
    deliberately NOT trusted — spoofable)
"""
import time

import pytest

from scp.security import auth as A


@pytest.fixture(autouse=True)
def _clean_buckets():
    with A._auth_failures_lock:
        A._auth_failures.clear()
    yield
    with A._auth_failures_lock:
        A._auth_failures.clear()


def test_eviction_targets_least_recently_active_bucket():
    """Overflow phải evict bucket cũ nhất theo THỜI GIAN failure gần nhất,
    không theo thứ tự insert. Attacker đang hoạt động không được reset budget."""
    A._record_auth_failure("ATTACKER")  # inserted first (t0)
    for i in range(4000):
        A._record_auth_failure(f"B{i}")
    A._record_auth_failure("ATTACKER")  # most recent failure, STILL first position
    for i in range(4000, 5000):
        A._record_auth_failure(f"B{i}")  # overflow -> one eviction

    assert len(A._auth_failures) <= A._MAX_AUTH_FAILURE_IPS
    # Fixed behavior: active bucket with the newest failures is preserved…
    assert "ATTACKER" in A._auth_failures
    assert len(A._auth_failures["ATTACKER"]) == 2
    # …and the least-recently-active stale bucket is the one evicted.
    assert "B0" not in A._auth_failures

    # No budget reset: 3 more failures must trip the limiter (2+3 >= 5).
    for _ in range(3):
        A._record_auth_failure("ATTACKER")
    assert A._check_rate_limit("ATTACKER") is False


def test_eviction_guarded_by_lock_helper():
    """Helper phải no-op khi chưa vượt cap (không evict oan bucket nào)."""
    A._record_auth_failure("solo")
    with A._auth_failures_lock:
        A._evict_oldest_failure_bucket_locked()
    assert "solo" in A._auth_failures


def test_unknown_client_shared_bucket_is_fail_closed():
    """Pin documented limitation: mọi request không có client.host dùng chung
    bucket 'unknown' — 5 failure của AI đó chặn cả client khác (fail-closed).
    XFF cố tình KHÔNG được tin (spoofable) — nếu ai thêm XFF, test này + docstring
    phải được xem lại."""
    for _ in range(A._RATE_LIMIT_MAX_FAILURES):
        A._record_auth_failure("unknown")
    assert A._check_rate_limit("unknown") is False
    # IP riêng (client có host) KHÔNG bị ảnh hưởng bởi bucket 'unknown'.
    assert A._check_rate_limit("192.0.2.7") is True


def test_expired_failures_do_not_block_and_are_purged():
    """Sliding window: failure quá 60s phải hết hiệu lực và bị dọn khỏi bucket."""
    with A._auth_failures_lock:
        A._auth_failures["old-ip"] = [time.time() - 61.0] * A._RATE_LIMIT_MAX_FAILURES
    assert A._check_rate_limit("old-ip") is True
    with A._auth_failures_lock:
        assert "old-ip" not in A._auth_failures
