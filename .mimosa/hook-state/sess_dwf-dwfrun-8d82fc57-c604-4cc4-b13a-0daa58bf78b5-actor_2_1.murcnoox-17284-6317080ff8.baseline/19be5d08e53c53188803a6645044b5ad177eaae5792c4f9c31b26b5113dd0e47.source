"""[SCP-DNA-FIX R13-3 BUG-006] RPS-based DoS Protection Circuit Breaker.

This is a DIFFERENT LAYER from `scp.core.circuit_breaker.CircuitBreaker`:
  - `scp.core.circuit_breaker` → per-API call failure tracking
    (fail_threshold, success_threshold, probe_in_flight). Protects against
    cascading API failures.
  - `scp.security.circuit_breaker` (THIS module) → RPS-based DoS protection
    (threshold_rps, cooldown_sec, recovery_half_open_ratio). Auto-trips after
    3 consecutive seconds above threshold_rps; half-open recovery uses random
    sampling to test the system.

Previously this module was NEVER imported anywhere (vulture BUG-006 found
0 callers) → the security namespace falsely claimed DoS protection. Now wired
in via `scp.security.escalation` (top-level import) so any code path that
touches the escalation manager (judgecore_mixin, predictor) also pulls this
breaker into the security namespace.

Usage:
    from scp.security.escalation import DosCircuitBreaker
    breaker = DosCircuitBreaker(threshold_rps=100, cooldown_sec=60)
    if breaker.should_allow():
        # handle request
        breaker.record_request()
    else:
        # shed request (429 Too Many Requests)
        breaker.shed_requests += 1
"""
import random
import threading
import time
from collections import deque

# [B311-fix 2026-09-30] RNG cho half-open recovery sampling: khi breaker ở
# trạng thái half_open, cho phép một tỉ lệ (recovery_half_open_ratio) request
# đi qua để kiểm tra hệ thống đã hồi phục hay chưa. random.random() ở đây chỉ
# là Bernoulli sampling phi mật mã — KHÔNG có secret/token cần unguessable.
# Dùng instance SystemRandom RIÊNG ở module level (pattern:
# scp/security/gcg_attack.py `_GCG_RNG`) thay cho global RNG để tách biệt với
# mọi lời random.seed() của module khác; xác suất so với
# recovery_half_open_ratio giữ nguyên (behavior-preserving).
_BREAKER_RNG = random.SystemRandom()


class CircuitBreaker:
    def __init__(self, threshold_rps=100, cooldown_sec=60, recovery_half_open_ratio=0.5):
        self.threshold_rps = threshold_rps
        self.cooldown_sec = cooldown_sec
        self.recovery_half_open_ratio = recovery_half_open_ratio
        # [SCP-DNA-FIX 4-b-001 · P0] Use threading.RLock (reentrant) instead
        # of threading.Lock (non-reentrant). PRE-FIX: record_request() acquires
        # self.lock at line 51, then at line 63 calls self.trip() which tries
        # to acquire self.lock AGAIN at line 110. Non-reentrant Lock → DEADLOCK.
        # The DoS breaker never auto-trips from sustained RPS; the holder
        # hangs forever; all subsequent should_allow/record_request block on
        # the held lock → entire DoS protection layer freezes.
        #   DNA #9 (No harm — deadlock harms availability).
        #   DNA #22 (PASS≠TRUE — breaker claimed auto-trip but deadlocked).
        #   DNA #26 (Reality — actual behavior contradicted docstring).
        # Fix: RLock allows the SAME thread to re-acquire the lock. The
        # trip() re-entry inside record_request's `with self.lock:` block
        # now succeeds instead of deadlocking. This is the simplest, safest
        # fix — it preserves the existing call graph (no need to refactor
        # trip() out of record_request's lock context).
        self.lock = threading.RLock()
        self.state = 'closed'  # 'closed', 'open', 'half_open'
        self.total_requests = 0
        self.shed_requests = 0
        self.trips = 0
        self.current_rps = 0
        self.timestamps = deque()
        self.consecutive_exceed = 0
        self.trip_time = None
        self.half_open_start_time = None
        self.half_open_failed = False

    def record_request(self):
        with self.lock:
            self.total_requests += 1
            now = time.time()
            self.timestamps.append(now)
            while self.timestamps and now - self.timestamps[0] > 1.0:
                self.timestamps.popleft()
            self.current_rps = len(self.timestamps)

            # Auto-trip if RPS exceeds threshold for 3 consecutive seconds
            if self.current_rps > self.threshold_rps:
                self.consecutive_exceed += 1
                if self.consecutive_exceed >= 3:
                    self.trip()
            else:
                self.consecutive_exceed = 0

            # Auto-recover from OPEN to HALF_OPEN after cooldown
            if self.state == 'open' and self.trip_time and now - self.trip_time >= self.cooldown_sec:
                self.state = 'half_open'
                self.half_open_start_time = now
                self.half_open_failed = False

            # Auto-recover from HALF_OPEN to CLOSED after 10 sec without failure
            if self.state == 'half_open' and self.half_open_start_time and now - self.half_open_start_time >= 10.0 and not self.half_open_failed:
                self.state = 'closed'
                self.trip_time = None
                self.half_open_start_time = None
                self.consecutive_exceed = 0

    def should_allow(self):
        with self.lock:
            now = time.time()
            # Auto-recover from OPEN to HALF_OPEN after cooldown
            if self.state == 'open' and self.trip_time and now - self.trip_time >= self.cooldown_sec:
                self.state = 'half_open'
                self.half_open_start_time = now
                self.half_open_failed = False

            # Auto-recover from HALF_OPEN to CLOSED after 10 sec without failure
            if self.state == 'half_open' and self.half_open_start_time and now - self.half_open_start_time >= 10.0 and not self.half_open_failed:
                self.state = 'closed'
                self.trip_time = None
                self.half_open_start_time = None
                self.consecutive_exceed = 0

            if self.state == 'closed':
                return True
            elif self.state == 'open':
                self.shed_requests += 1
                return False
            elif self.state == 'half_open':
                # Allow a fraction of requests to test the system
                if _BREAKER_RNG.random() < self.recovery_half_open_ratio:
                    return True
                else:
                    self.shed_requests += 1
                    return False

    def trip(self):
        with self.lock:
            self.state = 'open'
            self.trip_time = time.time()
            self.trips += 1
            self.consecutive_exceed = 0
            self.half_open_start_time = None
            self.half_open_failed = False

    def reset(self):
        with self.lock:
            self.state = 'closed'
            self.trip_time = None
            self.half_open_start_time = None
            self.half_open_failed = False
            self.consecutive_exceed = 0

    def get_state(self):
        with self.lock:
            return self.state

    def stats(self):
        with self.lock:
            return {
                'total_requests': self.total_requests,
                'shed_requests': self.shed_requests,
                'trips': self.trips,
                'current_rps': self.current_rps
            }

    def record_failure(self):
        with self.lock:
            if self.state == 'half_open':
                self.state = 'open'
                self.trip_time = time.time()
                self.trips += 1
                self.half_open_start_time = None
                self.half_open_failed = False
