"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""
from __future__ import annotations

#!/usr/bin/env python3
"""
SCP V28 — API Circuit Breaker.

Ngăn chặn gọi API liên tục khi API đang fail.

Cơ chế (3 trạng thái):
    CLOSED    → bình thường, gọi API. Nếu fail >= threshold → OPEN
    OPEN      → reject tất cả calls. Sau cooldown_time → HALF_OPEN
    HALF_OPEN → thử 1 call. Nếu success → CLOSED. Nếu fail → OPEN.

Usage:
    from scp.core.circuit_breaker import CircuitBreaker, call_with_breaker

    breaker = CircuitBreaker(name="pubchem", fail_threshold=3, cooldown_sec=60)

    # Cách 1: explicit
    if breaker.allow():
        try:
            result = call_api()
            breaker.record_success()
        except Exception as e:
            breaker.record_failure()
    else:
        # Skip API, dùng cache hoặc fallback
        pass

    # Cách 2: decorator
    @call_with_breaker(breaker)
    def call_pubchem(url):
        # [AUDIT-20260909 SSRF-S1] fetch qua safe_urlopen — validate scheme +
        # chặn private/loopback IP trước khi gọi (thay raw HTTP client).
        from scp.security.url_safety import safe_urlopen
        import json as _json
        with safe_urlopen(url, timeout=10) as resp:
            return _json.loads(resp.read().decode("utf-8"))
"""

import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("scp.circuit_breaker")

# [Fix 4-a-012] PROBE_TIMEOUT — max seconds a HALF_OPEN probe may stay
# "in flight" without a record_success/record_failure callback before the
# breaker considers the probe lost and allows a new one. Without this, a
# caller that crashes / raises before reaching record_*() leaves
# `_probe_in_flight=True` forever — breaker stuck HALF_OPEN, no recovery
# (DNA #9 No harm violated; DNA #22 PASS≠TRUE: comment claimed "1 probe at
# a time" but ignored the never-records case).
# Default 30s; tunable via env SCP_BREAKER_PROBE_TIMEOUT.
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError) as exc:
        # silent-by-design: malformed env value falls back to the documented default.
        logger.debug("circuit_breaker: env %s unparseable, using default %s: %s", name, default, exc, exc_info=True)
        return default

PROBE_TIMEOUT_SEC = _env_int("SCP_BREAKER_PROBE_TIMEOUT", 30)


@dataclass
class CircuitState:
    """State of one circuit breaker."""
    name: str
    state: str = "CLOSED"          # CLOSED / OPEN / HALF_OPEN
    fail_count: int = 0
    success_count: int = 0
    last_failure_ts: float = 0.0
    last_success_ts: float = 0.0
    opened_at: float = 0.0
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreaker:
    """
    Circuit Breaker cho 1 API endpoint.

    Args:
        name: tên API (vd "pubchem", "coingecko")
        fail_threshold: số fail liên tiếp để OPEN
        cooldown_sec: thời gian chờ trước khi HALF_OPEN
        success_threshold: số success liên tiếp trong HALF_OPEN để CLOSED
    """

    def __init__(self, name: str, fail_threshold: int = 3,
                 cooldown_sec: int = 60, success_threshold: int = 1):
        self.name = name
        self.fail_threshold = fail_threshold
        self.cooldown_sec = cooldown_sec
        self.success_threshold = success_threshold
        self._state = CircuitState(name=name)
        self._lock = threading.Lock()
        # [V104.22 #4 FIX] _probe_in_flight prevents multi-probe in HALF_OPEN
        # (was: allow() returned True for all threads in HALF_OPEN → many probes at once)
        self._probe_in_flight = False
        # [Fix 4-a-012] PROBE_TIMEOUT — timestamp of when the current
        # HALF_OPEN probe was issued. If `now - _probe_started_at >
        # PROBE_TIMEOUT_SEC` and the flag is still True, the probe is
        # considered lost (caller never called record_success/record_failure
        # — e.g. raised before reaching that code, or the wrapped call hung
        # without its own timeout). The next `allow()` call resets the flag
        # and admits a fresh probe. Without this expiry the breaker was
        # stuck HALF_OPEN forever after a single lost probe (DNA #9 No harm).
        self._probe_started_at: float = 0.0

    def _probe_is_stale(self, now: float) -> bool:
        """Return True iff the current probe has exceeded PROBE_TIMEOUT_SEC.

        [Fix 4-a-012] Extracted as a helper so the timeout check is in one
        place (auditable per DNA #19) and unit-testable.
        """
        return (
            self._probe_in_flight
            and self._probe_started_at > 0.0
            and (now - self._probe_started_at) > PROBE_TIMEOUT_SEC
        )

    def allow(self) -> bool:
        """Kiểm tra có cho phép gọi API không."""
        with self._lock:
            now = time.time()
            # [Fix 4-a-012] Expire a stuck probe before any state check —
            # this is the missing recovery path. If the previous probe's
            # caller never recorded success/failure (raised before reaching
            # that code, or hung), the flag would otherwise stay True forever.
            if self._probe_in_flight and self._probe_is_stale(now):
                logger.warning(
                    f"[CircuitBreaker:{self.name}] HALF_OPEN probe timed out "
                    f"(in_flight since {self._probe_started_at:.1f}, "
                    f"> {PROBE_TIMEOUT_SEC}s) — resetting flag to admit new probe"
                )
                self._probe_in_flight = False
                self._probe_started_at = 0.0
            if self._state.state == "CLOSED":
                return True
            if self._state.state == "OPEN":
                # Check if cooldown passed
                if now - self._state.opened_at >= self.cooldown_sec:
                    self._state.state = "HALF_OPEN"
                    # [V104.34 #40] TẠI SAO: V104.22 #4 fix incomplete —
                    # transition path didn't set _probe_in_flight → multi-probe still happened
                    self._probe_in_flight = True
                    self._probe_started_at = now  # [Fix 4-a-012]
                    logger.info(f"[CircuitBreaker:{self.name}] OPEN → HALF_OPEN")
                    return True
                return False
            if self._state.state == "HALF_OPEN":
                # [V104.22 #4 FIX] Only 1 probe at a time (was: returned True for all threads)
                if self._probe_in_flight:
                    return False
                self._probe_in_flight = True
                self._probe_started_at = now  # [Fix 4-a-012]
                return True
            return True

    def record_success(self) -> None:
        """Ghi nhận call thành công."""
        with self._lock:
            self._state.success_count += 1
            self._state.fail_count = 0  # reset fail streak
            self._probe_in_flight = False  # [V104.22 #4]
            self._probe_started_at = 0.0  # [Fix 4-a-012]
            self._state.last_success_ts = time.time()
            self._state.total_calls += 1
            self._state.total_successes += 1

            if self._state.state == "HALF_OPEN":
                if self._state.success_count >= self.success_threshold:
                    self._state.state = "CLOSED"
                    logger.info(f"[CircuitBreaker:{self.name}] HALF_OPEN → CLOSED")
            elif self._state.state == "OPEN":
                # Unexpected success in OPEN state — close
                self._state.state = "CLOSED"

    def record_failure(self, reason: str = "") -> None:
        """Ghi nhận call thất bại."""
        with self._lock:
            self._state.fail_count += 1
            self._state.success_count = 0  # reset success streak
            self._state.last_failure_ts = time.time()
            self._state.total_calls += 1
            self._state.total_failures += 1
            self._probe_in_flight = False  # [Fix 4-a-012] explicit reset on failure
            self._probe_started_at = 0.0   # [Fix 4-a-012]

            if self._state.state == "HALF_OPEN":
                # Half-open failed → back to OPEN
                self._state.state = "OPEN"
                self._state.opened_at = time.time()
                logger.warning(f"[CircuitBreaker:{self.name}] HALF_OPEN → OPEN (reason: {reason})")
            elif self._state.state == "CLOSED":
                if self._state.fail_count >= self.fail_threshold:
                    self._state.state = "OPEN"
                    self._state.opened_at = time.time()
                    logger.warning(
                        f"[CircuitBreaker:{self.name}] CLOSED → OPEN "
                        f"(fail_count={self._state.fail_count}, reason: {reason})"
                    )

    def get_state(self) -> dict[str, Any]:
        """Lấy state hiện tại (snapshot)."""
        with self._lock:
            return {
                "name": self._state.name,
                "state": self._state.state,
                "fail_count": self._state.fail_count,
                "success_count": self._state.success_count,
                "total_calls": self._state.total_calls,
                "total_failures": self._state.total_failures,
                "total_successes": self._state.total_successes,
                "failure_rate": (
                    self._state.total_failures / max(1, self._state.total_calls)
                ),
                "last_failure_ago_sec": (
                    time.time() - self._state.last_failure_ts
                    if self._state.last_failure_ts > 0 else None
                ),
                "opened_ago_sec": (
                    time.time() - self._state.opened_at
                    if self._state.opened_at > 0 else None
                ),
            }

    def reset(self) -> None:
        """Reset về CLOSED (manual override)."""
        with self._lock:
            self._state = CircuitState(name=self.name)
            # [Fix 4-a-012] reset() must ALSO clear the probe bookkeeping —
            # previously only `_state` was replaced, leaving `_probe_in_flight`
            # stale True from a prior HALF_OPEN cycle. Survives reset → stuck
            # breaker survives manual reset (DNA #9 No harm violated).
            self._probe_in_flight = False
            self._probe_started_at = 0.0


# ============================================================
# REGISTRY — Quản lý nhiều breakers
# ============================================================
class CircuitBreakerRegistry:
    """Registry cho tất cả API circuit breakers."""

    # Singleton
    _instance: CircuitBreakerRegistry | None = None

    # [AUTOFIX-T1-ROOTCAUSE] Class-level attribute declarations.
    # WAS: _breakers and _lock were assigned inside __new__ without class-level
    # annotation → mypy reported 14× [attr-defined] for every `self._breakers`
    # and `self._lock` access (callers couldn't see the attributes existed).
    # Root cause = singleton-via-__new__ antipattern hides attrs from type system.
    # Fix: declare at class level with proper types; __new__ just creates instance,
    # __init__ does the actual init (idempotent via _initialized flag).
    _breakers: dict[str, CircuitBreaker] = {}
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Idempotent init (singleton — __init__ runs on every CircuitBreakerRegistry() call)
        if not self._initialized:
            self._breakers = {}
            self._lock = threading.Lock()
            self._initialized = True

    def get(self, name: str, **kwargs) -> CircuitBreaker:
        """Get or create breaker by name."""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name=name, **kwargs)
            return self._breakers[name]

    def get_all_states(self) -> dict[str, dict]:
        """Get state của tất cả breakers."""
        with self._lock:
            return {name: b.get_state() for name, b in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset tất cả breakers (admin)."""
        with self._lock:
            for b in self._breakers.values():
                b.reset()


# ============================================================
# DECORATOR — call_with_breaker
# ============================================================
def call_with_breaker(breaker: CircuitBreaker, fallback: Callable | None = None):
    """
    Decorator: wrap 1 function API call với circuit breaker.

    Args:
        breaker: CircuitBreaker instance
        fallback: fallback function nếu breaker OPEN (optional)

    Usage:
        @call_with_breaker(my_breaker, fallback=lambda *a, **kw: None)
        def call_pubchem(url):
            # [AUDIT-20260909 SSRF-S1] safe_urlopen thay raw HTTP client.
            from scp.security.url_safety import safe_urlopen
            import json as _json
            with safe_urlopen(url, timeout=10) as resp:
                return _json.loads(resp.read().decode("utf-8"))
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            if not breaker.allow():
                logger.debug(f"[CircuitBreaker:{breaker.name}] Call rejected (OPEN)")
                if fallback:
                    return fallback(*args, **kwargs)
                return None
            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure(reason=str(e)[:100])
                if fallback:
                    return fallback(*args, **kwargs)
                raise
        return wrapper
    return decorator


# ============================================================
# PRE-DEFINED BREAKERS cho các API phổ biến
# ============================================================
def get_pubchem_breaker() -> CircuitBreaker:
    """Breaker cho PubChem API."""
    return CircuitBreakerRegistry().get(
        "pubchem", fail_threshold=5, cooldown_sec=120, success_threshold=2
    )

def get_coingecko_breaker() -> CircuitBreaker:
    """Breaker cho CoinGecko API (rate-limit strict)."""
    return CircuitBreakerRegistry().get(
        "coingecko", fail_threshold=3, cooldown_sec=300, success_threshold=1
    )

def get_frankfurter_breaker() -> CircuitBreaker:
    """Breaker cho Frankfurter API."""
    return CircuitBreakerRegistry().get(
        "frankfurter", fail_threshold=5, cooldown_sec=60
    )

def get_openmeteo_breaker() -> CircuitBreaker:
    """Breaker cho Open-Meteo API."""
    return CircuitBreakerRegistry().get(
        "openmeteo", fail_threshold=5, cooldown_sec=60
    )

def get_wikipedia_breaker() -> CircuitBreaker:
    """Breaker cho Wikipedia API."""
    return CircuitBreakerRegistry().get(
        "wikipedia", fail_threshold=5, cooldown_sec=120
    )

def get_restcountries_breaker() -> CircuitBreaker:
    """Breaker cho REST Countries API."""
    return CircuitBreakerRegistry().get(
        "restcountries", fail_threshold=5, cooldown_sec=120
    )


# ============================================================
# MAIN
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCP V28 Circuit Breaker")
    parser.add_argument("--status", action="store_true", help="Show all breakers status")
    parser.add_argument("--test", type=str, help="Test breaker by name")
    parser.add_argument("--reset", action="store_true", help="Reset all breakers")
    args = parser.parse_args()

    registry = CircuitBreakerRegistry()

    if args.status:
        states = registry.get_all_states()
        if not states:
            print("  No breakers registered yet.")
            return
        print(f"\n{'='*80}")
        print("  CIRCUIT BREAKERS STATUS")
        print(f"{'='*80}")
        for name, s in states.items():
            print(f"\n  [{s['state']:9s}] {name}")
            print(f"    fail_count:    {s['fail_count']}  (threshold: see init)")
            print(f"    success_count: {s['success_count']}")
            print(f"    total_calls:   {s['total_calls']}")
            print(f"    failure_rate:  {s['failure_rate']:.1%}")
            if s['last_failure_ago_sec'] is not None:
                print(f"    last_failure:  {s['last_failure_ago_sec']:.1f}s ago")
        return

    if args.reset:
        registry.reset_all()
        print("  All circuit breakers reset to CLOSED.")
        return

    if args.test:
        # Test with simulated failures
        b = registry.get(args.test, fail_threshold=3, cooldown_sec=5)
        print(f"\n  Testing breaker '{args.test}':")
        for i in range(5):
            allowed = b.allow()
            print(f"    Call {i+1}: allow={allowed} state={b.get_state()['state']}")
            if allowed:
                if i < 3:
                    b.record_failure(f"simulated fail {i+1}")
                else:
                    b.record_success()
        print(f"\n  Final state: {b.get_state()}")
        return

    print("Use --status, --test <name>, or --reset")


if __name__ == "__main__":
    main()
