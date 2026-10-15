"""Privacy/data-governance write gate (26-P0.12b).

The gate runs BEFORE durable evidence persistence. Secret/PII detections are
redacted in-memory; raw matched values are never returned in logs/reasons.
Unknown classification is conservatively composed as SENSITIVE.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from scp.contracts.data_class import DataClass, max_severity, parse_data_class
from scp.interfaces.governance import PrivacyDecision


@dataclass(frozen=True)
class Redaction:
    kind: str
    fingerprint: str


@dataclass(frozen=True)
class PrivacyWriteResult:
    decision: PrivacyDecision
    content: bytes | None
    data_class: DataClass
    retention_policy_id: str
    redactions: tuple[Redaction, ...]
    reason: str


_SECRET_PATTERNS = (
    ("PRIVATE_KEY", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I)),
    ("API_KEY", re.compile(rb"\b(?:sk|sk-or-v1)-[A-Za-z0-9_\-]{12,}\b")),
    ("JWT", re.compile(rb"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b")),
    (
        "SECRET_ASSIGNMENT",
        re.compile(
            rb"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)\s*[:=]\s*['\"]?([^\s'\";,]{8,})"
        ),
    ),
)
_PII_PATTERNS = (
    ("EMAIL", re.compile(rb"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("IPV4", re.compile(rb"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("PHONE", re.compile(rb"(?<!\d)\+?\d[\d .()\-]{7,}\d(?!\d)")),
)


def _fingerprint(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()[:16]


class PrivacyWriteGate:
    def __init__(self, policy_path: str | Path) -> None:
        self.policy_path = Path(policy_path)
        doc = yaml.safe_load(self.policy_path.read_text(encoding="utf-8")) or {}
        if doc.get("schema_version") != 1:
            raise ValueError("unsupported data policy schema")
        raw = doc.get("policies") or {}
        self._policies = {DataClass(name): dict(value) for name, value in raw.items()}
        missing = set(DataClass) - set(self._policies)
        if missing:
            raise ValueError(f"missing data policies: {[item.value for item in sorted(missing, key=lambda x: x.value)]}")

    def policy_for(self, data_class: DataClass | str) -> dict:
        return dict(self._policies[parse_data_class(data_class)])

    def provider_allowed(self, data_class: DataClass | str) -> bool:
        return bool(self.policy_for(data_class).get("external_provider_allowed", False))

    def evaluate(
        self,
        *,
        content: bytes,
        requested_class: DataClass | str | None,
        input_classes: tuple[object, ...] | list[object] = (),
        sanitized: bool = False,
    ) -> PrivacyWriteResult:
        if not isinstance(content, (bytes, bytearray)) or not content:
            raise ValueError("privacy write gate requires non-empty bytes")
        # None is intentionally included: max_severity treats missing/unknown as
        # a SENSITIVE floor.
        composed = max_severity(requested_class, *input_classes)
        redacted = bytes(content)
        redactions: list[Redaction] = []
        detected_secret = False
        detected_pii = False

        def apply(kind: str, pattern: re.Pattern[bytes], replacement: bytes) -> None:
            nonlocal redacted
            found = list(pattern.finditer(redacted))
            for match in found:
                raw = match.group(0)
                redactions.append(Redaction(kind=kind, fingerprint=_fingerprint(raw)))
            redacted = pattern.sub(replacement, redacted)

        for kind, pattern in _SECRET_PATTERNS:
            if pattern.search(redacted):
                detected_secret = True
                apply(kind, pattern, f"<{kind}_REDACTED>".encode("ascii"))
        for kind, pattern in _PII_PATTERNS:
            if pattern.search(redacted):
                detected_pii = True
                apply(kind, pattern, f"<{kind}_REDACTED>".encode("ascii"))

        if detected_secret:
            composed = max_severity(composed, DataClass.SECRET)
        elif detected_pii:
            composed = max_severity(composed, DataClass.SENSITIVE)

        policy = self.policy_for(composed)
        policy_id = f"p0-{composed.value.lower()}"
        changed = redacted != bytes(content)

        if bool(policy.get("raw_storage_allowed", False)) and not changed:
            return PrivacyWriteResult(
                PrivacyDecision.ALLOW,
                bytes(content),
                composed,
                policy_id,
                (),
                "content allowed by data policy",
            )

        if changed and bool(policy.get("redacted_storage_allowed", False)):
            return PrivacyWriteResult(
                PrivacyDecision.REDACT,
                redacted,
                composed,
                policy_id,
                tuple(redactions),
                "sensitive values redacted before persistence",
            )

        # An explicit sanitization step may store already-sanitized SENSITIVE
        # material while retaining the original data class. Declassification is
        # a separate governance act; `sanitized=True` never lowers data_class.
        if sanitized and bool(policy.get("redacted_storage_allowed", False)):
            return PrivacyWriteResult(
                PrivacyDecision.ALLOW,
                bytes(content),
                composed,
                policy_id,
                tuple(redactions),
                "caller supplied sanitized content; classification retained",
            )

        return PrivacyWriteResult(
            PrivacyDecision.DENY_STORAGE,
            None,
            composed,
            policy_id,
            tuple(redactions),
            "raw storage forbidden by data policy",
        )
