from __future__ import annotations

from enum import Enum
from typing import Any, Protocol, runtime_checkable


class PrivacyDecision(str, Enum):
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    DENY_STORAGE = "DENY_STORAGE"

@runtime_checkable
class IPrivacyWriteGate(Protocol):
    def evaluate_write(self, target: str, payload: Any, metadata: dict[str, Any]) -> Any:
        ...
