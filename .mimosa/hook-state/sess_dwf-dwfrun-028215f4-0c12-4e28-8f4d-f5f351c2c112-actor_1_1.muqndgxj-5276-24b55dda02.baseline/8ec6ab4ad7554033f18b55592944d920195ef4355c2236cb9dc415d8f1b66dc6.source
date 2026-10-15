"""[SEC-FIX bounded-stores 2026-09-26] Regression tests — in-memory stores
keyed by attacker-controllable input phải bounded.

FA-09 provenance: probe xác nhận TRƯỚC fix — 10k key attacker-controlled làm
4 store tăng trưởng không giới hạn:
  - AsnDetector._cache             (threat_detector.py)  -> 10000 entries
  - MemoryPoisoningGuard._session_history (memory_guard.py) -> 10000 sessions
  - AttackPredictor._history       (predictor.py)        -> 10000 entries
  - AdminAlerter._ip_attack_counts (counter_response.py) -> 10000 IPs

Pattern tham chiếu của repo: ChatMemoryStore (MAX_RECORDS) + deque maxlen +
BehavioralDetector._max_ips. Tests monkeypatch bound xuống giá trị nhỏ với
`raising=False` — trên code cũ (không có bound) store vẫn vượt cap → test đỏ.
"""
from __future__ import annotations

import asyncio
import logging

import pytest

logging.disable(logging.CRITICAL)


@pytest.fixture(autouse=True)
def deterministic_why_gate(monkeypatch):
    """Pin the WHY gate to its deterministic (non-LLM) falsification layer.

    Same pin as tests/T07_learning/test_autofix_shadow_rollback.py and
    tests/T09_golden_task/test_golden_b_epistemic_loop.py: the repo .env
    carries SCP_WHY_LLM_ENABLED=1 and leaks into os.environ for the rest of
    the pytest process once any module imports the runner/api_server, so
    AttackPredictor.predict_cyber_attack (called 120x in a pure unit test
    here) makes the WHY gate consult a real LLM per call. Observed live
    2026-10-02: full-suite run hung >10 minutes inside
    test_attack_predictor_history_is_bounded at
    llm_gateway.client.chat_sync (py-spy stack), because every hedge attempt
    waits out its network timeout. The subjects of these tests are the
    bounded-memory regression contracts, NOT the WHY-LLM behavior — the
    history-bound assertions below are unchanged. monkeypatch restores the
    caller's environment afterwards.
    """
    monkeypatch.setenv("SCP_WHY_LLM_ENABLED", "0")


def test_asn_detector_cache_is_bounded(monkeypatch):
    import socket

    from scp.security.threat_detector import AsnDetector

    detector = AsnDetector(mmdb_dir=".")
    monkeypatch.setattr(detector, "_cache_max", 50, raising=False)

    def _no_dns(ip):
        raise OSError("probe: no DNS")

    monkeypatch.setattr(socket, "gethostbyaddr", _no_dns)
    for i in range(120):
        asyncio.run(detector.lookup(f"192.0.2.{i // 256}.{i % 256}"))

    assert len(detector._cache) <= 50, (
        f"AsnDetector._cache vượt cap ({len(detector._cache)}) — store không bounded"
    )
    # Entry MỚI NHẤT phải còn trong cache (evict oldest-inserted).
    assert "192.0.2.0.119" in detector._cache


def test_memory_poisoning_guard_session_map_is_bounded(monkeypatch):
    from scp.security.memory_guard import MemoryPoisoningGuard

    guard = MemoryPoisoningGuard()
    monkeypatch.setattr(guard, "max_sessions", 50, raising=False)
    for i in range(120):
        guard.check(session_id=f"attacker-session-{i}", new_input="hello world")
    assert len(guard._session_history) <= 50, (
        f"_session_history vượt cap ({len(guard._session_history)}) — số session không bounded"
    )
    # Session mới nhất phải được track.
    assert "attacker-session-119" in guard._session_history


def test_memory_guard_per_session_history_still_trimmed():
    """Contract pin: trim theo max_history trong 1 session giữ nguyên semantics."""
    from scp.security.memory_guard import MemoryPoisoningGuard

    guard = MemoryPoisoningGuard(max_history=5)
    for i in range(20):
        guard.check(session_id="one-session", new_input=f"turn {i}")
    assert len(guard._session_history["one-session"]) == 5


def test_attack_predictor_history_is_bounded(monkeypatch):
    from scp.security.predictor import AttackPredictor

    predictor = AttackPredictor()
    monkeypatch.setattr(predictor, "_max_history", 50, raising=False)
    for _ in range(120):
        predictor.predict_cyber_attack({"request_rate_anomaly": 0.9})
    assert len(predictor._history) <= 50, (
        f"AttackPredictor._history vượt cap ({len(predictor._history)})"
    )
    # get_history() semantics: trả về tail (mới nhất) như cũ.
    history = predictor.get_history(limit=10)
    assert len(history) == 10


def test_admin_alerter_ip_map_is_bounded(monkeypatch):
    from scp.security.counter_response import AdminAlerter

    alerter = AdminAlerter()
    monkeypatch.setattr(alerter, "_max_tracked_ips", 50, raising=False)
    for i in range(120):
        alerter.alert(
            "attack_detected",
            "low",
            {"attacker_ip": f"10.{i // 256}.{i % 256}.1"},
        )
    assert len(alerter._ip_attack_counts) <= 50, (
        f"_ip_attack_counts vượt cap ({len(alerter._ip_attack_counts)})"
    )
    # IP mới nhất phải còn (evict oldest-inserted).
    assert "10.0.119.1" in alerter._ip_attack_counts


def test_admin_alerter_repeated_attack_detection_unchanged():
    """Contract pin: hành vi repeated_attacks (==3 trong 1h) không đổi sau khi bound."""
    from scp.security.counter_response import AdminAlerter

    alerter = AdminAlerter()
    ip = "10.9.9.9"
    for _ in range(3):
        alerter.alert("attack_detected", "low", {"attacker_ip": ip})
    events = [a for a in alerter._alert_history if a["event_type"] == "repeated_attacks"]
    assert len(events) == 1
    assert events[0]["details"]["attacker_ip"] == ip
    assert events[0]["details"]["count"] == 3
