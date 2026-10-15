"""[G3-STUB → G5-FIX] SCPV14 — minimal stub (real logic was dead, returning UNKNOWN).

Previous version: 53 LOC stub returning final_verdict='UNKNOWN'.
Imported by 5 modules (experience, judge, engine, meta, prediction) as SCPV13 alias.

This stub preserves the import chain while signaling that V14 logic is deprecated.
Real verdict logic lives in scp/runtime/judge.py::RealityJudge.

[G5-FIX] Previously returned a plain dict — but judgecore_mixin.py accesses
v13_result.final_verdict, .final_reason, .real_value, .source, .verdict_detail
as attributes. Returning a dict caused AttributeError on every judge() call
that reached V13 reality check. Fix: return a SimpleNamespace with the same
attribute surface so callers using either dict[...] or .attr both work.
"""
from types import SimpleNamespace
from typing import Any


class SCPV14:
    """Deprecated V14 engine stub — use RealityJudge instead."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.v13 = None  # backward compat (self.v13.v13 pattern in judgecore)

    def process(self, question: str = "", ai_answer: str = "", **kwargs: Any) -> SimpleNamespace:
        """Return UNKNOWN — real logic in RealityJudge.judge().

        Returns a SimpleNamespace (not a dict) so callers using attribute access
        (v13_result.final_verdict) and callers using dict access (v13['final_verdict'])
        both work consistently.
        """
        return SimpleNamespace(
            final_verdict="UNKNOWN",
            final_reason="SCPV14 stub deprecated — real logic in RealityJudge",
            real_value=None,
            source="SCPV14_STUB_DEPRECATED",
            verdict_detail={"note": "V14 stub — no real verification performed"},
        )
