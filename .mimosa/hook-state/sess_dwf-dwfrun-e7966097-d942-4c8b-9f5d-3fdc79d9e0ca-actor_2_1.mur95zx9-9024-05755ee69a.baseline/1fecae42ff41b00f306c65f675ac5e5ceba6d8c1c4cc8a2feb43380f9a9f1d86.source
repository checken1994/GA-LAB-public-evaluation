"""
SCP Behavior Monitor — EmoBank-inspired behavioral signal tracking.

TẠI SAO module này tồn tại?
  VIGIL-style EmoBank tracks behavioral signals (frustration, anxiety, relief,
  curiosity) from observed events. SCP applies the same idea to its OWN JSONL
  logs so the WHY Gate can "feel" how the pipeline is doing — not just reason
  about it.

  Sources (auto-ingested on init, relative to data_dir):
    - data/error_store.jsonl
    - data/notifications.jsonl
    - data/deep_audit_results.jsonl

  Events → BehaviorSignal via DETERMINISTIC heuristics (NO LLM — pure Python).
  Signals decay exponentially (half-life) and coalesce when repeated. The WHY
  Gate consumes get_rbt() (Roses/Buds/Thorns) to enrich falsification reasoning
  — non-blocking (DNA #7 fail-open).

Heuristics (deterministic):
  - frustration (valence=-1): retry_count >= 3 | fail_count >= 3
                              | (status == "failed" AND attempts > 2)
        intensity = min(1.0, count / 5.0)   # count = retry_count|fail_count|attempts
  - anxiety    (valence=-1): latency_ms > 2000 | timeout | circuit_breaker_open
        intensity = min(1.0, latency_ms / 10000.0)   # 0.5 fallback when no latency
  - relief     (valence=+1): status == "success" AND previous event status == "failed"
        intensity = 0.6
  - curiosity  (valence=+1): new_pattern | hypothesis | why_question
        intensity = 0.4
  - neutral → None (not stored)

Decay:       decayed = original * 0.5 ^ (age_hours / half_life_hours)
Noise floor: skip if decayed < noise_floor AND valence didn't flip vs prev kept
Coalesce:    same emotion+cause within coalesce_window_seconds
             → merge: keep latest ts, intensity = max(a, b) + 0.1
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("scp.meta.behavior_monitor")


@dataclass
class BehaviorSignal:
    """A single behavioral signal derived from one SCP event.

    Attributes:
        emotion:    one of "frustration" | "anxiety" | "relief" | "curiosity" | "neutral"
        valence:    -1 (negative), 0 (neutral), +1 (positive)
        intensity:  original intensity at capture time, in [0.0, 1.0]
        cause:      human-readable cause chain (e.g. "autofix.retry:count=3")
        timestamp:  time.time() at capture
        source:     which log file / event source produced this signal
    """

    emotion: str
    valence: int
    intensity: float
    cause: str
    timestamp: float
    source: str

    def decayed_intensity(self, now: float, half_life_hours: float) -> float:
        """Exponentially-decayed intensity at time `now`.

        decayed = original * 0.5 ^ (age_hours / half_life_hours)
        """
        age_hours = max(0.0, (now - self.timestamp) / 3600.0)
        return self.intensity * (0.5 ** (age_hours / max(0.001, half_life_hours)))

    def to_dict(self) -> dict:
        return {
            "emotion": self.emotion,
            "valence": self.valence,
            "intensity": self.intensity,
            "cause": self.cause,
            "timestamp": self.timestamp,
            "source": self.source,
        }


class BehaviorMonitor:
    """EmoBank-style behavioral signal monitor.

    Reads SCP JSONL logs, converts events to BehaviorSignal via deterministic
    heuristics (NO LLM), applies exponential decay + coalescing, and exposes
    Roses/Buds/Thorns diagnosis for the WHY Gate.
    """

    # Standard SCP log files auto-ingested on init (filename, source-label).
    STANDARD_LOGS: list[tuple[str, str]] = [
        ("error_store.jsonl", "error_store"),
        ("notifications.jsonl", "notifications"),
        ("deep_audit_results.jsonl", "deep_audit_results"),
    ]

    def __init__(
        self,
        data_dir: str = "data",
        half_life_hours: float = 12.0,
        noise_floor: float = 0.25,
        coalesce_window_seconds: float = 300.0,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.half_life_hours = float(half_life_hours)
        self.noise_floor = float(noise_floor)
        self.coalesce_window_seconds = float(coalesce_window_seconds)
        self._signals: list[BehaviorSignal] = []
        # Last seen event status — used by the relief heuristic
        # (relief fires when status flips failed → success).
        self._prev_status: str | None = None
        # Auto-ingest standard SCP logs (fail-open per DNA #7).
        try:
            self._auto_ingest()
        except Exception as e:  # noqa: BLE001 — fail-open, never block caller
            logger.debug(f"BehaviorMonitor auto-ingest failed (fail-open): {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def ingest_event(self, event: dict, source: str) -> BehaviorSignal | None:
        """Convert one event dict → BehaviorSignal via deterministic heuristics.

        Returns None for neutral events (no heuristic match). The previous
        event status is tracked regardless so the relief heuristic can fire on
        the next success event.
        """
        if not isinstance(event, dict):
            return None
        signal = self._classify(event, source)
        # Track previous status even on neutral — relief needs the failed → success flip.
        status = event.get("status")
        if isinstance(status, str):
            self._prev_status = status
        if signal is None:
            return None
        self._coalesce_or_store(signal)
        return signal

    def ingest_log_file(self, path: str, source: str) -> list[BehaviorSignal]:
        """Read JSONL file at `path`, ingest each line. Returns stored signals.

        Missing file → []. Malformed lines → skipped (fail-open).
        """
        p = Path(path)
        if not p.is_file():
            return []
        stored: list[BehaviorSignal] = []
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except (json.JSONDecodeError, ValueError) as exc:
                        # Corrupt event line must be visible, not silently dropped.
                        logger.warning("behavior_monitor: corrupt event line skipped: %s", exc, exc_info=True)
                        continue
                    sig = self.ingest_event(event, source)
                    if sig is not None:
                        stored.append(sig)
        except Exception as e:  # noqa: BLE001 — fail-open
            logger.debug(f"BehaviorMonitor ingest_log_file({path}) failed: {e}")
        return stored

    def get_signals(self, since: float = 0.0) -> list[BehaviorSignal]:
        """Return signals with timestamp >= `since`, after exponential decay
        and noise-floor filtering. Valence flips are preserved even below floor.

        Signals are returned in ascending timestamp order. A signal whose
        decayed intensity falls below `noise_floor` is skipped UNLESS its
        valence differs from the immediately preceding signal's valence
        (a "flip" — kept as a transition marker). The preceding signal's
        valence is tracked whether or not that signal was itself kept, so a
        flip is still detectable when the prior signal was below the floor.
        """
        now = time.time()
        candidates = sorted(
            (s for s in self._signals if s.timestamp >= since),
            key=lambda s: s.timestamp,
        )
        kept: list[BehaviorSignal] = []
        # prev_valence tracks the immediately preceding signal's valence
        # (whether or not it was kept) so that a flip is detectable even when
        # the prior signal was itself below the noise floor and skipped.
        prev_valence: int | None = None
        for s in candidates:
            decayed = s.decayed_intensity(now, self.half_life_hours)
            flipped = prev_valence is not None and s.valence != prev_valence
            below_floor = decayed < self.noise_floor
            # Track valence progression regardless of keep/skip decision.
            prev_valence = s.valence
            if below_floor and not flipped:
                continue
            kept.append(s)
        return kept

    def get_rbt(self) -> dict:
        """Return Roses/Buds/Thorns diagnosis (after decay).

        Categories are mutually exclusive (checked in order):
          - roses:  valence=+1 AND decayed_intensity >= 0.5
          - buds:   emotion="curiosity" OR (valence=+1 AND 0.25 <= decayed < 0.5)
          - thorns: valence=-1 AND decayed_intensity >= 0.4

        Returns a dict with keys "roses", "buds", "thorns" (lists of
        BehaviorSignal) and "counts" (a dict of int counts for convenience).
        """
        now = time.time()
        roses: list[BehaviorSignal] = []
        buds: list[BehaviorSignal] = []
        thorns: list[BehaviorSignal] = []
        for s in self._signals:
            d = s.decayed_intensity(now, self.half_life_hours)
            if s.valence == +1 and d >= 0.5:
                roses.append(s)
            elif s.emotion == "curiosity" or (s.valence == +1 and 0.25 <= d < 0.5):
                buds.append(s)
            elif s.valence == -1 and d >= 0.4:
                thorns.append(s)
        return {
            "roses": roses,
            "buds": buds,
            "thorns": thorns,
            "counts": {"roses": len(roses), "buds": len(buds), "thorns": len(thorns)},
        }

    def get_aggregate_emotion(self) -> dict:
        """Return {emotion: total_decayed_intensity} for all stored signals."""
        now = time.time()
        agg: dict[str, float] = {}
        for s in self._signals:
            d = s.decayed_intensity(now, self.half_life_hours)
            agg[s.emotion] = agg.get(s.emotion, 0.0) + d
        return agg

    # ------------------------------------------------------------------
    # Heuristics (deterministic, no LLM)
    # ------------------------------------------------------------------
    def _classify(self, event: dict, source: str) -> BehaviorSignal | None:
        """Apply deterministic heuristics in priority order. Returns None if neutral."""
        status = event.get("status")
        now = time.time()

        # relief: success after a prior failed status.
        if status == "success" and self._prev_status == "failed":
            return BehaviorSignal(
                emotion="relief",
                valence=+1,
                intensity=0.6,
                cause="status_flip:failed->success",
                timestamp=now,
                source=source,
            )

        # frustration: retries / fails / failed-with-attempts.
        if self._matches_frustration(event):
            count = self._frustration_count(event)
            intensity = min(1.0, count / 5.0) if count > 0 else 0.6
            return BehaviorSignal(
                emotion="frustration",
                valence=-1,
                intensity=intensity,
                cause=f"retry_or_fail:count={count}",
                timestamp=now,
                source=source,
            )

        # anxiety: latency / timeout / circuit breaker.
        if self._matches_anxiety(event):
            latency = _safe_float(event.get("latency_ms"), 0.0)
            if latency > 0:
                intensity = min(1.0, latency / 10000.0)
                cause = f"latency_ms={latency}"
            elif event.get("timeout"):
                intensity = 0.5
                cause = "timeout"
            else:
                intensity = 0.5
                cause = "circuit_breaker_open"
            return BehaviorSignal(
                emotion="anxiety",
                valence=-1,
                intensity=intensity,
                cause=cause,
                timestamp=now,
                source=source,
            )

        # curiosity: new pattern / hypothesis / why question.
        if event.get("new_pattern") or event.get("hypothesis") or event.get("why_question"):
            return BehaviorSignal(
                emotion="curiosity",
                valence=+1,
                intensity=0.4,
                cause=_curiosity_cause(event),
                timestamp=now,
                source=source,
            )

        return None  # neutral

    @staticmethod
    def _matches_frustration(event: dict) -> bool:
        rc = _safe_float(event.get("retry_count"), 0.0)
        fc = _safe_float(event.get("fail_count"), 0.0)
        att = _safe_float(event.get("attempts"), 0.0)
        if rc >= 3:
            return True
        if fc >= 3:
            return True
        if event.get("status") == "failed" and att > 2:
            return True
        return False

    @staticmethod
    def _matches_anxiety(event: dict) -> bool:
        lat = _safe_float(event.get("latency_ms"), 0.0)
        if lat > 2000:
            return True
        if event.get("timeout"):
            return True
        if event.get("circuit_breaker_open"):
            return True
        return False

    @staticmethod
    def _frustration_count(event: dict) -> float:
        """First available count among retry_count / fail_count / attempts."""
        for key in ("retry_count", "fail_count", "attempts"):
            v = _safe_float(event.get(key), 0.0)
            if v > 0:
                return v
        return 0.0

    # ------------------------------------------------------------------
    # Coalescing
    # ------------------------------------------------------------------
    def _coalesce_or_store(self, signal: BehaviorSignal) -> None:
        """If a stored signal has same emotion+cause within coalesce_window,
        merge into it (keep latest ts, intensity = max(a, b) + 0.1). Else append.
        """
        for existing in self._signals:
            if existing.emotion != signal.emotion or existing.cause != signal.cause:
                continue
            if abs(existing.timestamp - signal.timestamp) > self.coalesce_window_seconds:
                continue
            # Merge into existing signal in-place.
            existing.intensity = max(existing.intensity, signal.intensity) + 0.1
            existing.timestamp = signal.timestamp  # keep latest
            return
        self._signals.append(signal)

    # ------------------------------------------------------------------
    # Auto-ingest
    # ------------------------------------------------------------------
    def _auto_ingest(self) -> None:
        """Ingest the 3 standard SCP log files if they exist under data_dir."""
        for fname, source in self.STANDARD_LOGS:
            path = self.data_dir / fname
            if path.is_file():
                self.ingest_log_file(str(path), source)


# ------------------------------------------------------------------
# Module-level helpers (pure functions, deterministic)
# ------------------------------------------------------------------
def _safe_float(v, default: float = 0.0) -> float:
    """Coerce arbitrary JSON value to float; NaN → default; errors → default."""
    try:
        f = float(v)
    except (TypeError, ValueError) as exc:
        # silent-by-design: coerce probe; caller default is the documented fallback.
        logger.debug("behavior_monitor: float coercion failed, using default: %s", exc, exc_info=True)
        return default
    if f != f:  # NaN guard
        return default
    return f


def _curiosity_cause(event: dict) -> str:
    """Build a human-readable cause string for a curiosity signal."""
    if event.get("new_pattern"):
        return f"new_pattern:{str(event['new_pattern'])[:60]}"
    if event.get("hypothesis"):
        return f"hypothesis:{str(event['hypothesis'])[:60]}"
    return f"why_question:{str(event.get('why_question', ''))[:60]}"


# ============================================================
# Smoke test
# ============================================================
if __name__ == "__main__":
    import tempfile

    print("=== SCP Behavior Monitor smoke test ===")
    with tempfile.TemporaryDirectory() as tmp:
        # 5 synthetic JSONL events in time order:
        #   1. neutral  — failed status but no frustration trigger (enables relief)
        #   2. relief   — success after failed (intensity 0.6)
        #   3. frustration — retry_count=4 (intensity 0.8)
        #   4. anxiety  — latency_ms=5000 (intensity 0.5)
        #   5. curiosity — new_pattern (intensity 0.4)
        events = [
            {"event": "heartbeat", "status": "failed", "attempts": 1},   # neutral
            {"event": "recovery", "status": "success"},                   # relief
            {"event": "autofix", "status": "retrying", "retry_count": 4}, # frustration
            {"event": "llm_call", "latency_ms": 5000, "timeout": True},   # anxiety
            {"event": "scanner", "new_pattern": "weird_stack_trace"},     # curiosity
        ]
        log_path = Path(tmp) / "synthetic.jsonl"
        with log_path.open("w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")

        # Fresh monitor — auto-ingest finds no standard logs under tmp (clean slate).
        bm = BehaviorMonitor(data_dir=tmp)
        stored = bm.ingest_log_file(str(log_path), "smoke_test")

        print(f"\nIngest returned {len(stored)} signals (expected 4 — neutral not stored)")
        signals = bm.get_signals()
        print(f"get_signals() returned {len(signals)} (expected 4)")
        for s in signals:
            print(
                f"  [{s.emotion:11s}] valence={s.valence:+d}  "
                f"intensity={s.intensity:.3f}  cause={s.cause}  src={s.source}"
            )

        rbt = bm.get_rbt()
        print("\nRBT diagnosis:")
        print(f"  roses ({len(rbt['roses'])}): {[s.emotion for s in rbt['roses']]}")
        print(f"  buds  ({len(rbt['buds'])}): {[s.emotion for s in rbt['buds']]}")
        print(f"  thorns({len(rbt['thorns'])}): {[s.emotion for s in rbt['thorns']]}")

        agg = bm.get_aggregate_emotion()
        print("\nAggregate emotion (total decayed intensity):")
        for emo, total in sorted(agg.items()):
            print(f"  {emo:11s}: {total:.3f}")

        # Assertions (matches task verification).
        assert len(signals) == 4, f"Expected 4 signals stored, got {len(signals)}"
        emotions = {s.emotion for s in signals}
        assert emotions == {"relief", "frustration", "anxiety", "curiosity"}, emotions
        assert len(rbt["thorns"]) >= 2, f"Expected >=2 thorns (frustration+anxiety), got {len(rbt['thorns'])}"
        assert len(rbt["roses"]) >= 1, f"Expected >=1 rose (relief), got {len(rbt['roses'])}"
        assert len(rbt["buds"]) >= 1, f"Expected >=1 bud (curiosity), got {len(rbt['buds'])}"
        print("\n[OK] All smoke-test assertions passed.")
