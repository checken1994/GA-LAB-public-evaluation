# SCP CIRCUIT: M12 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M12-closure.json)
"""SCP WHY Engine public boundary.

The implementation is split into focused modules while this file preserves the
stable import surface used by runtime callers. Wiring is explicit here so an
extracted module never depends on an accidental parent-module global.
"""
from __future__ import annotations

import importlib
import logging
import os
import threading
from dataclasses import dataclass

logger = logging.getLogger("scp.why_engine")


@dataclass
class VerificationPlan:
    """Verification work produced by :class:`WhyEngine`."""

    question: str
    target: str
    target_type: str
    evidence_type: str
    proof_criteria: str
    falsification_criteria: str
    verification_strategy: str
    sources_to_query: list[str]
    expected_answer_type: str
    confidence_threshold: float
    reasoning: str
    # [M12-FIX PF-3] DB row id when the plan was claimed from
    # why_verification_plans (execute_pending_plans). None for freshly built
    # plans that have not been persisted. execute_plan uses it for an exact
    # id-based status UPDATE (the previous UPDATE ... ORDER BY id DESC LIMIT 1
    # raised OperationalError on standard SQLite builds -> status silently
    # stayed 'pending' forever, fail-silently).
    plan_id: int | None = None


_METAWHY_MONITOR_SINGLETON = None
_METAWHY_MONITOR_LOCK = threading.Lock()


def _get_metawhy_monitor():
    """Lazy singleton for the passive MetaWhy monitor."""

    global _METAWHY_MONITOR_SINGLETON
    if _METAWHY_MONITOR_SINGLETON is None:
        with _METAWHY_MONITOR_LOCK:
            if _METAWHY_MONITOR_SINGLETON is None:
                try:
                    from scp.meta.metawhy_monitor import MetaWhyMonitor

                    data_dir = os.environ.get("SCP_DATA_DIR", "data")
                    _METAWHY_MONITOR_SINGLETON = MetaWhyMonitor(data_dir=data_dir)
                    logger.info("MetaWhyMonitor initialized")
                except Exception as exc:
                    logger.warning(
                        "MetaWhyMonitor init failed: %s — monitoring disabled",
                        type(exc).__name__,
                    exc_info=True)
                    _METAWHY_MONITOR_SINGLETON = False
    return _METAWHY_MONITOR_SINGLETON if _METAWHY_MONITOR_SINGLETON is not False else None


# Explicit dependency wiring for extracted implementation modules. The parts
# intentionally do not import this public boundary back at import time, which
# avoids circular initialization and makes every legacy dependency visible.
_init_module = importlib.import_module("scp.meta.why_engine_parts.init_why_db")
_init_module.logger = logger
init_why_db = _init_module.init_why_db

_impl = importlib.import_module("scp.meta.why_engine_parts.whyengine")
_impl.logger = logger
_impl.init_why_db = init_why_db
_impl.VerificationPlan = VerificationPlan
_impl._get_metawhy_monitor = _get_metawhy_monitor
WhyEngine = _impl.WhyEngine

# The split is an implementation detail. Preserve the pre-split public module
# identity for introspection and pickle/import compatibility.
init_why_db.__module__ = __name__
WhyEngine.__module__ = __name__


def main():
    """CLI delegate."""

    from scp.meta.why_engine_cli import main as _cli_main

    return _cli_main()


__all__ = ["VerificationPlan", "WhyEngine", "init_why_db"]


if __name__ == "__main__":
    main()
