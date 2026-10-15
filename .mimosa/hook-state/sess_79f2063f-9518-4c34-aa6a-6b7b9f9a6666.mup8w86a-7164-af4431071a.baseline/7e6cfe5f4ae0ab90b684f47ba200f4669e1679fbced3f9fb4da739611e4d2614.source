"""
SCP V98 — AttackClassifierEngine
Copyright (c) 2026 Minh. MIT License.

Port từ WHY H6 — tổng hợp tín hiệu từ ThreatDetector → verdict AI/HUMAN + attack type.

Naming convention: <Purpose>Engine (world standard, e.g. ClassificationEngine)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from scp.security.threat_detector import ThreatSignal

logger = logging.getLogger("scp.security.attack_classifier")


@dataclass
class Classification:
    """Kết quả classify từ ThreatSignal."""
    actor: str = "human"  # human | bot_legacy | ai_agent_2026 | anonymizing_proxy | unknown
    attack_type: str = "none"  # none | scanner | injection | jailbreak | exfil | suspicious
    severity: str = "none"  # none | low | medium | high | critical
    confidence: float = 0.0
    strong_signals: list[str] = field(default_factory=list)
    weak_signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor": self.actor,
            "attack_type": self.attack_type,
            "severity": self.severity,
            "confidence": round(self.confidence, 3),
            "strong_signals": self.strong_signals,
            "weak_signals": self.weak_signals,
        }


# Strong signals (high confidence AI agent)
STRONG_SIGNALS = {
    "injection": "injection",
    "ua:python-requests": "bot",
    "ua:curl": "bot",
    "ua:scrapy": "scraper",
    "ua:selenium": "automated",
    "ua:puppeteer": "automated",
    "asn:tor": "anonymizing",
    "asn:datacenter": "datacenter",
    "bot_timing": "automated",
    "rapid_fire": "automated",
}

# Weak signals
WEAK_SIGNALS = {
    "missing_headers": "suspicious",
    "low_header_count": "suspicious",
    "scanner": "suspicious",
    "asn:vpn": "anonymizing",
    "ua_mismatch": "suspicious",
}


class AttackClassifierEngine:
    """Classify threat signal → actor + attack_type + severity.

    Naming convention: <Purpose>Engine (world standard).
    """

    def classify(
        self,
        threat_signal: ThreatSignal,
        h2_signatures: list[str] | None = None,
    ) -> Classification:
        """Fusion logic: strong signals > weak signals.

        Rules:
          - H2 attack content → actor = ai_agent
          - 2+ strong signals → ai_agent_2026
          - 1 strong + 1 weak → bot_legacy
          - Weak only → monitor
          - No signals → human
        """
        signals = threat_signal.signals or []
        strong = []
        weak = []

        for sig in signals:
            # [V104.34 #55] TẠI SAO: old split(":")[0] gave prefix "ua"/"asn" →
            # matched "injection" but missed "ua:python-requests" (full sig).
            # Fix: try full sig first, then prefix as fallback.
            sig_key = sig  # full signal (e.g., "ua:python-requests")
            if sig_key in STRONG_SIGNALS:
                strong.append(sig)
            elif sig_key in WEAK_SIGNALS:
                weak.append(sig)
            else:
                # Fallback: try prefix (e.g., "injection:ignore_previous" → "injection")
                prefix = sig.split(":")[0]
                if prefix in STRONG_SIGNALS:
                    strong.append(sig)
                elif prefix in WEAK_SIGNALS:
                    weak.append(sig)

        # H2 attack content override
        if h2_signatures:
            strong.extend([f"h2:{s}" for s in h2_signatures])

        # Determine actor
        if len(strong) >= 2:
            actor = "ai_agent_2026"
        elif len(strong) >= 1:
            if any("tor" in s for s in strong):
                actor = "anonymizing_proxy"
            elif any("injection" in s for s in strong):
                actor = "ai_agent_2026"
            else:
                actor = "bot_legacy"
        elif len(weak) >= 1:
            actor = "unknown"
        else:
            actor = "human"

        # Determine attack_type
        if any("injection" in s for s in strong):
            attack_type = "injection"
        elif any("scanner" in s for s in strong + weak):
            attack_type = "scanner"
        elif any("rapid_fire" in s for s in strong):
            attack_type = "dos"
        elif any("tor" in s for s in strong):
            attack_type = "anonymizing"
        elif weak:
            attack_type = "suspicious"
        else:
            attack_type = "none"

        # Determine severity
        if "injection" in attack_type:
            severity = "critical"
        elif actor == "ai_agent_2026" and attack_type in ("scanner", "dos"):
            severity = "high"
        elif actor == "ai_agent_2026":
            severity = "high"
        elif actor == "anonymizing_proxy":
            severity = "high"
        elif actor == "bot_legacy":
            severity = "medium"
        elif actor == "unknown":
            severity = "low"
        else:
            severity = "none"

        # Confidence: based on signal count + strength
        conf = threat_signal.confidence
        if len(strong) >= 2:
            conf = max(conf, 0.9)
        elif len(strong) >= 1:
            conf = max(conf, 0.7)

        return Classification(
            actor=actor,
            attack_type=attack_type,
            severity=severity,
            confidence=conf,
            strong_signals=strong,
            weak_signals=weak,
        )


__all__ = ["Classification", "AttackClassifierEngine"]
