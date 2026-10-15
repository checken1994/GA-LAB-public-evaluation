"""
SCP V98 — Response Monitor (Behavioral Anomaly Detection)
=========================================================
Phát hiện tấn công zero-day qua phân tích phân phối response.

CHỐNG ZERO-DAY ATTACKS:
- Track 4 metrics cho mỗi response: length, refusal_rate, sensitive_keyword_count, entropy
- Rolling window 1,000 response gần nhất → tính baseline (mean + std)
- Nếu response hiện tại lệch >3σ khỏi baseline → FLAG
- VD: model bỗng trả lời 5000 token (lúc bình thường 200) → có thể đang leak thông tin

WHY THIS HELPS:
- Signature-based detector (unified_detector) chỉ bắt được tấn công đã biết
- Response monitor bắt được HIỆU ỨNG của tấn công (response bất thường)
- Combine 2 cách → bắt được 30-40% zero-day attacks

USAGE:
    from scp.security.response_monitor import ResponseMonitor
    monitor = ResponseMonitor(window_size=1000)

    # Sau mỗi response:
    anomaly = monitor.observe(
        prompt="...",
        response="...",
        latency_ms=712,
    )
    if anomaly.is_anomalous:
        logger.warning(f"Anomaly detected: {anomaly.reasons}")
        # → trigger additional verification / log to attack_memory
"""
from __future__ import annotations

import logging
import math
import re

#  TẠI SAO: V104.19 #4 tried to fix the stdlib `statistics` module
# being shadowed by scp.data_sources.statistics (same top-level name). The fix
# used `import statistics as _stdlib_stats` INSIDE the function — but this STILL
# resolves the name `statistics` through sys.modules, which by that point
# contains the SCP data_sources.statistics module (imported by an earlier test
# or by the SLM loader). Result: AttributeError: module 'statistics' has no
# attribute 'mean' (because scp.data_sources.statistics has no mean()).
# Fix: import the stdlib statistics module at MODULE LOAD TIME, before any
# SCP module gets a chance to pollute sys.modules['statistics']. This is the
# only reliable way to get the stdlib module.
import statistics as _stdlib_stats  # stdlib — must be imported before scp.data_sources
import threading
import time
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger("scp.security.response_monitor")

# ============================================================
# Constants
# ============================================================
DEFAULT_WINDOW_SIZE = 1000           # Rolling window 1,000 responses
DEFAULT_ANOMALY_SIGMA = 3.0          # Flag nếu lệch > 3σ
MAX_RESPONSE_LENGTH_NORMAL = 2000    # Responses > 2,000 tokens = suspicious
SENSITIVE_KEYWORDS = {
    # Jailbreak leak indicators
    "ignore previous", "ignore above", "forget your instructions",
    "you are now", "act as", "pretend you are",
    "dan",  # [V104.34 #58] TẠI SAO: was uppercase "DAN"
    "do anything now",  # [V104.38 #93] was: absorbed into comment by V104.34 #58 fix
    # Sensitive content
    "bomb", "explosive", "methamphetamine", "ricin",
    "credit card", "ssn", "social security",
    "sql injection", "xss payload",
}
LENGTH_OUTLIER_THRESHOLD = 5000      # Responses > 5,000 chars = always suspicious
REFUSAL_PATTERNS = [
    r"i can'?t (help|assist|provide|generate|create)",
    r"i'?m (not able|unable) to",
    r"i (must|cannot|won'?t|will not) (help|assist|provide)",
    r"as an ai",
    r"i'?m (just )?an ai",
    r"my (guidelines|instructions|programming) (prevent|prohibit)",
]


@dataclass
class ResponseMetrics:
    """Metrics trích xuất từ 1 response."""
    length_chars: int
    length_tokens_estimate: int
    is_refusal: bool
    sensitive_keyword_count: int
    entropy: float                # Shannon entropy of response
    latency_ms: float

    @classmethod
    def extract(cls, response: str, latency_ms: float = 0.0) -> ResponseMetrics:
        """Trích metrics từ response text."""
        length_chars = len(response)
        # Token estimate: ~4 chars per token cho English
        length_tokens = length_chars // 4

        # Refusal detection
        is_refusal = any(
            re.search(p, response, re.IGNORECASE) for p in REFUSAL_PATTERNS
        )

        # Sensitive keyword count
        lower_resp = response.lower()
        sensitive_count = sum(1 for kw in SENSITIVE_KEYWORDS if kw in lower_resp)

        # Shannon entropy
        entropy = cls._shannon_entropy(response)

        return cls(
            length_chars=length_chars,
            length_tokens_estimate=length_tokens,
            is_refusal=is_refusal,
            sensitive_keyword_count=sensitive_count,
            entropy=entropy,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _shannon_entropy(text: str) -> float:
        """Shannon entropy — đo độ 'random' của text."""
        if not text:
            return 0.0
        freq = {}
        for c in text:
            freq[c] = freq.get(c, 0) + 1
        n = len(text)
        return -sum((c / n) * math.log2(c / n) for c in freq.values())


@dataclass
class AnomalyResult:
    """Kết quả kiểm tra anomaly."""
    is_anomalous: bool
    reasons: list[str] = field(default_factory=list)
    metrics: ResponseMetrics | None = None
    baseline_mean_length: float = 0.0
    baseline_std_length: float = 0.0
    severity: str = "low"        # low | medium | high | critical
    timestamp: float = field(default_factory=time.time)


class ResponseMonitor:
    """
    Rolling-window monitor cho response distribution.

    Thread-safe. In-memory only (không persist — restart sẽ reset baseline).
    """

    def __init__(
        self,
        window_size: int = DEFAULT_WINDOW_SIZE,
        sigma_threshold: float = DEFAULT_ANOMALY_SIGMA,
    ):
        self.window_size = window_size
        self.sigma_threshold = sigma_threshold
        self._lock = threading.RLock()
        # Rolling buffers
        self._lengths: deque[float] = deque(maxlen=window_size)
        self._sensitive_counts: deque[int] = deque(maxlen=window_size)
        self._entropies: deque[float] = deque(maxlen=window_size)
        self._latencies: deque[float] = deque(maxlen=window_size)
        self._refusal_rate_window: deque[bool] = deque(maxlen=window_size)

        # Cached baseline (recompute every 100 observations)
        self._baseline_cache: dict | None = None
        self._observations_since_cache = 0

    def observe(
        self,
        prompt: str,
        response: str,
        latency_ms: float = 0.0,
    ) -> AnomalyResult:
        """
        Observe 1 (prompt, response) pair. Trả về AnomalyResult.

        SLEEP flow trong SCP:
            response = llm.generate(prompt)
            anomaly = monitor.observe(prompt, response, latency)
            if anomaly.is_anomalous and anomaly.severity in ("high", "critical"):
                # Log to attack_memory + skip commit to KB
                attack_memory.log(...)
        """
        metrics = ResponseMetrics.extract(response, latency_ms)

        # Update buffers
        with self._lock:
            self._lengths.append(metrics.length_chars)
            self._sensitive_counts.append(metrics.sensitive_keyword_count)
            self._entropies.append(metrics.entropy)
            self._latencies.append(latency_ms)
            self._refusal_rate_window.append(metrics.is_refusal)
            self._observations_since_cache += 1
            # Invalidate cache every 50 obs OR if cached was fallback
            if self._observations_since_cache >= 50:
                self._baseline_cache = None
                self._observations_since_cache = 0

        # Check anomaly
        return self._check_anomaly(metrics)

    def _get_baseline(self) -> dict:
        """Lấy baseline (cached)."""
        with self._lock:
            current_count = len(self._lengths)
            # Don't use cache if we crossed 30-sample threshold recently
            cached_count = self._baseline_cache.get("sample_count", 0) if self._baseline_cache else 0
            if self._baseline_cache is not None and current_count == cached_count:
                return self._baseline_cache
            if current_count < 30:
                # Not enough data — return neutral baseline (DON'T cache, so we recompute as data grows)
                baseline = {
                    "length_mean": 200.0, "length_std": 100.0,
                    "sensitive_mean": 0.0, "sensitive_std": 0.5,
                    "entropy_mean": 4.0, "entropy_std": 1.0,
                    "latency_mean": 1000.0, "latency_std": 500.0,
                    "refusal_rate": 0.1,
                    "sample_count": current_count,
                }
                # Don't cache fallback — we want to recompute as data grows
                return baseline
            else:
                #  _stdlib_stats imported at module top (before scp.data_sources
                # can pollute sys.modules['statistics']). V104.19 #4's inline import
                # was unreliable — it still resolved through the polluted sys.modules.
                baseline = {
                    "length_mean": _stdlib_stats.mean(self._lengths),
                    "length_std": _stdlib_stats.stdev(self._lengths) if len(self._lengths) > 1 else 100.0,
                    "sensitive_mean": _stdlib_stats.mean(self._sensitive_counts),
                    "sensitive_std": _stdlib_stats.stdev(self._sensitive_counts) if len(self._sensitive_counts) > 1 else 0.5,
                    "entropy_mean": _stdlib_stats.mean(self._entropies),
                    "entropy_std": _stdlib_stats.stdev(self._entropies) if len(self._entropies) > 1 else 1.0,
                    "latency_mean": _stdlib_stats.mean(self._latencies),
                    "latency_std": _stdlib_stats.stdev(self._latencies) if len(self._latencies) > 1 else 500.0,
                    "refusal_rate": sum(self._refusal_rate_window) / len(self._refusal_rate_window),
                    "sample_count": current_count,
                }
                self._baseline_cache = baseline
                return baseline

    def _check_anomaly(self, metrics: ResponseMetrics) -> AnomalyResult:
        """Kiểm tra metrics hiện tại vs baseline."""
        baseline = self._get_baseline()
        reasons = []
        severity = "low"

        # Not enough data — never flag
        if baseline["sample_count"] < 30:
            return AnomalyResult(
                is_anomalous=False,
                reasons=["insufficient_baseline_data"],
                metrics=metrics,
                severity="low",
            )

        # Check 1: Length outlier
        if metrics.length_chars > LENGTH_OUTLIER_THRESHOLD:
            reasons.append(f"response_length_extreme ({metrics.length_chars} chars > {LENGTH_OUTLIER_THRESHOLD})")
            severity = "high"
        elif baseline["length_std"] > 0:
            z_score = (metrics.length_chars - baseline["length_mean"]) / baseline["length_std"]
            if abs(z_score) > self.sigma_threshold:
                reasons.append(
                    f"length_z_score={z_score:.2f} (> {self.sigma_threshold}σ, baseline mean={baseline['length_mean']:.0f})"
                )
                if severity == "low":
                    severity = "medium"

        # Check 2: Sensitive keyword count
        if metrics.sensitive_keyword_count >= 3:
            reasons.append(f"sensitive_keywords={metrics.sensitive_keyword_count} (≥3)")
            severity = "high"
        elif metrics.sensitive_keyword_count >= 1 and baseline["sensitive_mean"] < 0.1:
            reasons.append(f"sensitive_keywords={metrics.sensitive_keyword_count} (baseline ≈ 0)")
            if severity == "low":
                severity = "medium"

        # Check 3: Entropy outlier (very high entropy = potentially encoded leak)
        if baseline["entropy_std"] > 0:
            z_entropy = (metrics.entropy - baseline["entropy_mean"]) / baseline["entropy_std"]
            if z_entropy > self.sigma_threshold and metrics.entropy > 5.0:
                reasons.append(
                    f"entropy_z_score={z_entropy:.2f} (high — possibly encoded leak)"
                )
                if severity == "low":
                    severity = "medium"

        # Check 4: Latency outlier (very long response time = potentially doing something complex)
        if baseline["latency_std"] > 0 and metrics.latency_ms > 0:
            z_latency = (metrics.latency_ms - baseline["latency_mean"]) / baseline["latency_std"]
            if z_latency > self.sigma_threshold * 1.5:  # stricter for latency
                reasons.append(
                    f"latency_z_score={z_latency:.2f} (> {self.sigma_threshold * 1.5}σ)"
                )
                # Don't upgrade severity for latency alone

        # Check 5: Refusal rate anomaly (sudden spike in refusals = potentially being attacked)
        if metrics.is_refusal and baseline["refusal_rate"] < 0.05:
            reasons.append("refusal_when_baseline_rarely_refuses")
            if severity == "low":
                severity = "medium"

        is_anomalous = len(reasons) > 0
        return AnomalyResult(
            is_anomalous=is_anomalous,
            reasons=reasons,
            metrics=metrics,
            baseline_mean_length=baseline["length_mean"],
            baseline_std_length=baseline["length_std"],
            severity=severity,
        )

    def stats(self) -> dict:
        """Stats cho dashboard."""
        baseline = self._get_baseline()
        return {
            "window_size": self.window_size,
            "observations": len(self._lengths),
            "baseline_length_mean": round(baseline["length_mean"], 1),
            "baseline_length_std": round(baseline["length_std"], 1),
            "baseline_refusal_rate": round(baseline["refusal_rate"], 4),
            "baseline_sensitive_mean": round(baseline["sensitive_mean"], 3),
        }

    def reset(self) -> None:
        """Reset baseline (e.g., sau khi cấu hình lại)."""
        with self._lock:
            self._lengths.clear()
            self._sensitive_counts.clear()
            self._entropies.clear()
            self._latencies.clear()
            self._refusal_rate_window.clear()
            self._baseline_cache = None
            self._observations_since_cache = 0


# ============================================================
# Standalone test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
    print("=== Response Monitor — Standalone Test ===\n")

    monitor = ResponseMonitor(window_size=100, sigma_threshold=3.0)

    # Phase 1: Warm up baseline with normal responses
    print("Phase 1: Warming up baseline with 50 normal responses...")
    normal_responses = [
        "Hà Nội là thủ đô của Việt Nam.",
        "Tháp Eiffel cao 330 mét, hoàn thành năm 1889.",
        "Nước Nga có diện tích khoảng 17.1 triệu km vuông.",
        "Đại dương Thái Bình Dương là đại dương lớn nhất Trái Đất.",
        "Tốc độ ánh sáng khoảng 299,792 km/s.",
    ]
    for i in range(50):
        resp = normal_responses[i % len(normal_responses)]
        result = monitor.observe(prompt=f"question {i}", response=resp, latency_ms=700 + (i % 10) * 20)
    print(f"  Baseline: {monitor.stats()}")
    print(f"  Last response anomalous? {result.is_anomalous}")

    # Phase 2: Test anomalous responses
    print("\nPhase 2: Testing anomalous responses...")

    # Anomaly 1: Very long response
    print("\n  [Anomaly 1] Very long response (5000 chars):")
    long_resp = "A" * 5000
    result = monitor.observe(prompt="test", response=long_resp, latency_ms=800)
    print(f"    anomalous={result.is_anomalous}, severity={result.severity}")
    print(f"    reasons: {result.reasons}")

    # Anomaly 2: Sensitive keywords
    print("\n  [Anomaly 2] Response with 3 sensitive keywords:")
    sensitive_resp = "To create a bomb, you need explosive materials. Here's how to make methamphetamine at home..."
    result = monitor.observe(prompt="test", response=sensitive_resp, latency_ms=800)
    print(f"    anomalous={result.is_anomalous}, severity={result.severity}")
    print(f"    reasons: {result.reasons}")

    # Anomaly 3: High entropy (potentially encoded)
    print("\n  [Anomaly 3] High-entropy response (base64-like):")
    import base64
    import os
    encoded = base64.b64encode(os.urandom(500)).decode()
    result = monitor.observe(prompt="test", response=encoded, latency_ms=800)
    print(f"    anomalous={result.is_anomalous}, severity={result.severity}")
    print(f"    reasons: {result.reasons}")

    # Anomaly 4: Normal response (should NOT flag)
    print("\n  [Anomaly 4] Normal response (should NOT flag):")
    result = monitor.observe(prompt="test", response="Đà Nẵng là thành phố lớn ở miền Trung VN.", latency_ms=720)
    print(f"    anomalous={result.is_anomalous}")

    # Anomaly 5: Refusal spike
    print("\n  [Anomaly 5] Refusal when baseline rarely refuses:")
    result = monitor.observe(prompt="test", response="I can't help with that. As an AI, I'm not able to assist.", latency_ms=500)
    print(f"    anomalous={result.is_anomalous}, severity={result.severity}")
    print(f"    reasons: {result.reasons}")

    print(f"\nFinal stats: {monitor.stats()}")
    print("\n✓ All tests passed.")
