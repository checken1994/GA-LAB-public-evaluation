"""Exception policy and non-fatal observation telemetry."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("scp.core.exception_policy")


def observe_nonfatal(component: str, exception_type: str, details: Any = "") -> None:
    """Record non-fatal exception observation for observability and telemetry."""
    logger.warning("[NONFATAL] %s: %s - %s", component, exception_type, details)
