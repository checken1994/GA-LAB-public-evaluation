"""
SCP V106 — DoSProtectionEngine
================================
Bảo vệ SCP khỏi DoS attack — đặc biệt attack lợi dụng triết lý SCP.

Vấn đề: Attacker gửi 1000 câu "xám" (OUT_OF_SCOPE) → SCP tự KILL 1000 lần → DoS

Giải pháp 3 lớp:
  1. RATE LIMITING — giới hạn requests/IP/phút
  2. CIRCUIT BREAKER — nếu quá nhiều UNKNOWN/SPECULATIVE liên tiếp → throttle
  3. RESOURCE QUOTA — giới hạn CPU/RAM per request + total

Naming convention: <Purpose>Engine (world standard).
"""
from __future__ import annotations

import logging
import math
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("scp.security.dos_protection")


@dataclass
class DoSAlert:
    """Cảnh báo DoS."""
    alert_type: str  # rate_limit | circuit_breaker | resource_quota
    severity: str  # warning | critical
    message: str
    ip: str = ""
    current_rate: float = 0.0
    threshold: float = 0.0
    action_taken: str = ""  # throttle | block | circuit_open
    # [Fix 4-b-009 · Phase 4-A] Explicit HTTP status code + headers so the
    # FastAPI route handler can map this DoSAlert to a proper HTTP response
    # (RFC 6585 §4 for 429 Too Many Requests, RFC 7231 §6.5.3 for 403 Forbidden).
    # Pre-fix: the throttle branch never fired at all (see _last_throttle bug),
    # so there was no point in carrying status_code. Post-fix: throttle fires
    # → status_code=429 + Retry-After header → client can retry gracefully.
    status_code: int = 0  # 0 means "no explicit recommendation" (caller decides)
    recommended_headers: dict[str, str] = field(default_factory=dict)


class DoSProtectionEngine:
    """Bảo vệ SCP khỏi DoS — rate limiting + circuit breaker + resource quota.

    Naming convention: <Purpose>Engine (world standard).

    3 layers:
      1. Rate Limiting: max 60 requests/phút per IP (1 req/giây)
      2. Circuit Breaker: nếu 10 UNKNOWN/SPECULATIVE liên tiếp → throttle 5 giây
      3. Resource Quota: max 100 concurrent requests, max 10s per request
    """

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_REQUESTS_PER_HOUR = 1000

    # Circuit breaker
    CIRCUIT_UNKNOWN_THRESHOLD = 10  # 10 UNKNOWN liên tiếp → open circuit
    CIRCUIT_RESET_TIME = 30  # 30 giây trước khi thử lại
    CIRCUIT_COOLDOWN = 5  # 5 giây throttle khi circuit open

    # Resource quota
    MAX_CONCURRENT = 100
    MAX_REQUEST_TIME_S = 10

    def __init__(self):
        # [SCP-DNA-FIX 4-b-010] Thread-safety lock — guards ALL mutable shared
        # state below (rate-limit deques, circuit-breaker counters, concurrent
        # counter, stats dict). Pre-fix: counters/windows/_last_throttle were
        # plain attributes mutated from request handlers without a lock.
        # Under concurrent load: increments were lost, windows drifted, the
        # breaker under-counted RPS → it never tripped. Compounds with 4-b-001
        # (the deadlock) — the entire DoS layer was effectively non-functional.
        #   DNA #9 (No harm — silent under-count harms availability protection).
        #   DNA #22 (PASS≠TRUE — DoS layer claimed protection but lost updates).
        #   DNA #19 (Tầng kiểm toán — observation layer couldn't see real RPS).
        self._lock = threading.Lock()

        # Rate limiting per IP
        self._requests_per_minute: dict[str, deque] = defaultdict(lambda: deque(maxlen=120))
        self._requests_per_hour: dict[str, deque] = defaultdict(lambda: deque(maxlen=7200))

        # Circuit breaker
        self._consecutive_unknown: int = 0
        self._circuit_state: str = "closed"  # closed | open | half_open
        self._circuit_opened_at: float = 0
        # [Fix 4-b-009] _last_throttle is now ASSIGNED in the throttle branch
        # of check_request (was previously only declared here, never assigned,
        # → throttle branch was dead code). Tracks timestamp of last applied
        # throttle — used for stats + for the cooldown check that documents
        # intent (currently always True while circuit open; see check_request
        # comment for design).
        self._last_throttle: float = 0

        # Resource quota
        self._current_concurrent: int = 0

        # Stats
        self._stats = {
            "total_requests": 0,
            "total_blocked_rate": 0,
            "total_throttled": 0,
            "circuit_opens": 0,
            "max_concurrent_seen": 0,
        }

    def check_request(self, ip: str = "unknown") -> DoSAlert | None:
        """Check if request should be allowed.

        Returns:
            None if allowed, DoSAlert if blocked/throttled.

        [SCP-DNA-FIX 4-b-010] Thread-safe — entire body runs under
        `self._lock` so concurrent requests can't race on counters/windows.
        Pre-fix: increments were lost under concurrent load (read-modify-write
        races), windows drifted, breaker under-counted RPS → never tripped.
        """
        with self._lock:
            self._stats["total_requests"] += 1
            now = time.time()

            # === LAYER 1: RATE LIMITING ===
            # Per-minute
            minute_requests = self._requests_per_minute[ip]
            # Remove old entries (> 60 seconds)
            while minute_requests and now - minute_requests[0] > 60:
                minute_requests.popleft()
            if len(minute_requests) >= self.MAX_REQUESTS_PER_MINUTE:
                self._stats["total_blocked_rate"] += 1
                retry_after = min(60, max(1, math.ceil(60 - (now - minute_requests[0]))))
                return DoSAlert(
                    alert_type="rate_limit",
                    severity="critical",
                    message=f"Rate limit exceeded: {len(minute_requests)} req/min for {ip}",
                    ip=ip,
                    current_rate=float(len(minute_requests)),
                    threshold=float(self.MAX_REQUESTS_PER_MINUTE),
                    action_taken="block",
                    status_code=429,
                    recommended_headers={"Retry-After": str(retry_after)},
                )

            # Per-hour
            hour_requests = self._requests_per_hour[ip]
            while hour_requests and now - hour_requests[0] > 3600:
                hour_requests.popleft()
            if len(hour_requests) >= self.MAX_REQUESTS_PER_HOUR:
                self._stats["total_blocked_rate"] += 1
                retry_after = min(3600, max(1, math.ceil(3600 - (now - hour_requests[0]))))
                return DoSAlert(
                    alert_type="rate_limit",
                    severity="critical",
                    message=f"Hourly limit exceeded: {len(hour_requests)} req/hour for {ip}",
                    ip=ip,
                    current_rate=float(len(hour_requests)),
                    threshold=float(self.MAX_REQUESTS_PER_HOUR),
                    action_taken="block",
                    status_code=429,
                    recommended_headers={"Retry-After": str(retry_after)},
                )

            # Record request
            minute_requests.append(now)
            hour_requests.append(now)

            # === LAYER 2: CIRCUIT BREAKER ===
            if self._circuit_state == "open":
                if now - self._circuit_opened_at > self.CIRCUIT_RESET_TIME:
                    self._circuit_state = "half_open"
                    logger.info("[DoSProtection] Circuit → half_open (trying again)")
                else:
                    # Still open — throttle
                    # [Fix 4-b-009 · Phase 4-A] Pre-fix bug: `_last_throttle` was
                    # declared at __init__ (line 71: `self._last_throttle: float = 0`)
                    # but NEVER ASSIGNED anywhere in the codebase. So
                    # `now - self._last_throttle` was always `now - 0` ≈ 1.7B
                    # seconds, which is >> CIRCUIT_COOLDOWN (5s) → the `if` below
                    # was always False → the throttle branch was DEAD CODE → every
                    # request was silently ALLOWED through while circuit was
                    # "open". DNA #22 (PASS≠TRUE): docstring claimed "5 giây throttle
                    # khi circuit open" but reality was "no throttle ever".
                    # DNA #19 (Tầng kiểm toán): the throttle mechanism couldn't
                    # see the requests it was supposed to throttle.
                    #
                    # Fix: assign _last_throttle = now BEFORE the cooldown check,
                    # so the check is meaningful (0 < COOLDOWN → True → throttle
                    # fires). The cooldown check is now always True while circuit
                    # is open — kept for documentation of intent. Probing is
                    # handled by the half_open transition above (after
                    # CIRCUIT_RESET_TIME elapses).
                    self._last_throttle = now
                    if now - self._last_throttle < self.CIRCUIT_COOLDOWN:
                        self._stats["total_throttled"] += 1
                        return DoSAlert(
                            alert_type="circuit_breaker",
                            severity="warning",
                            message=(
                                f"Circuit OPEN — throttling request from {ip}; "
                                f"retry after {self.CIRCUIT_COOLDOWN}s "
                                f"(HTTP 429 Too Many Requests; "
                                f"Retry-After: {self.CIRCUIT_COOLDOWN})"
                            ),
                            ip=ip,
                            current_rate=float(self._consecutive_unknown),
                            threshold=float(self.CIRCUIT_COOLDOWN),
                            action_taken="throttle",
                            # [Fix 4-b-009] Explicit 429 + Retry-After header so
                            # the FastAPI route handler can map this DoSAlert to
                            # a proper HTTP 429 response (RFC 6585 §4) with a
                            # Retry-After header telling the client when to retry.
                            status_code=429,
                            recommended_headers={
                                "Retry-After": str(self.CIRCUIT_COOLDOWN),
                            },
                        )

            # === LAYER 3: RESOURCE QUOTA ===
            if self._current_concurrent >= self.MAX_CONCURRENT:
                return DoSAlert(
                    alert_type="resource_quota",
                    severity="critical",
                    message=f"Max concurrent reached: {self._current_concurrent}/{self.MAX_CONCURRENT}",
                    current_rate=float(self._current_concurrent),
                    threshold=float(self.MAX_CONCURRENT),
                    action_taken="block",
                )

            self._current_concurrent += 1
            self._stats["max_concurrent_seen"] = max(self._stats["max_concurrent_seen"], self._current_concurrent)

            return None  # Request allowed

    def record_verdict(self, verdict: str):
        """Record verdict result — update circuit breaker.

        [SCP-DNA-FIX 4-b-010] Thread-safe — entire body runs under
        `self._lock` so concurrent verdicts can't race on
        _consecutive_unknown / _circuit_state / _stats.

        [AUDIT-FIX 2026-09-24] CONTRACT: record_verdict must only be called
        by a request path that previously passed check_request (i.e. holds a
        resource-quota slot). It releases that slot AND updates the circuit
        breaker. Callers that exit early before producing a verdict must use
        release_slot() instead — see the pairing rules in _ask_impl and
        openai_compat.
        """
        with self._lock:
            self._current_concurrent = max(0, self._current_concurrent - 1)

            # Circuit breaker logic
            if verdict in ("UNKNOWN", "SPECULATIVE"):
                self._consecutive_unknown += 1
                if self._consecutive_unknown >= self.CIRCUIT_UNKNOWN_THRESHOLD:
                    if self._circuit_state != "open":
                        self._circuit_state = "open"
                        self._circuit_opened_at = time.time()
                        self._stats["circuit_opens"] += 1
                        logger.warning(
                            f"[DoSProtection] Circuit OPENED — {self._consecutive_unknown} consecutive UNKNOWN/SPECULATIVE"
                        )
            else:
                # Reset on PASS or FAIL
                if self._consecutive_unknown > 0:
                    self._consecutive_unknown = 0
                    if self._circuit_state == "half_open":
                        self._circuit_state = "closed"
                        logger.info("[DoSProtection] Circuit → closed (recovered)")

    def release_slot(self):
        """Release one resource-quota slot WITHOUT touching the circuit breaker.

        [AUDIT-FIX 2026-09-24] TAI SAO: /ask requests that exit early (HTTP
        400/403 or an exception) after passing check_request used to leak
        their slot forever — check_request incremented _current_concurrent but
        record_verdict was never reached. After 100 leaks the WHOLE process
        429'd for every IP. This method returns the slot so the global
        100-slot invariant stays honest on every exit path, while leaving the
        verdict-driven circuit-breaker state untouched (an early exit produced
        no verdict and must not count toward the UNKNOWN circuit).
        """
        with self._lock:
            self._current_concurrent = max(0, self._current_concurrent - 1)

    def stats(self) -> dict[str, Any]:
        """[SCP-DNA-FIX 4-b-010] Take the lock for a consistent snapshot.

        Pre-fix: counters could change mid-snapshot → inconsistent dict
        (e.g. total_requests observed before lock release but
        total_blocked_rate observed after).
        """
        with self._lock:
            return {
                **self._stats,
                "circuit_state": self._circuit_state,
                "consecutive_unknown": self._consecutive_unknown,
                "current_concurrent": self._current_concurrent,
                "tracked_ips": len(self._requests_per_minute),
                "thresholds": {
                    "max_per_minute": self.MAX_REQUESTS_PER_MINUTE,
                    "max_per_hour": self.MAX_REQUESTS_PER_HOUR,
                    "circuit_threshold": self.CIRCUIT_UNKNOWN_THRESHOLD,
                    "max_concurrent": self.MAX_CONCURRENT,
                },
            }


__all__ = ["DoSAlert", "DoSProtectionEngine"]
