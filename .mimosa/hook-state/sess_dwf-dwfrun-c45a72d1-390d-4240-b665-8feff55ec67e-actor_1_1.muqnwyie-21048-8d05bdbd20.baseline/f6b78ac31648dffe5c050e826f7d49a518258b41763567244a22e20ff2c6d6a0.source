from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IJudge(Protocol):
    @property
    def attack_memory(self) -> Any:
        ...
    def judge(self, question: str, ai_answer: str, **kwargs: Any) -> Any:
        ...

_ACTIVE_JUDGE: Any | None = None

def set_judge_provider(judge: Any) -> None:
    global _ACTIVE_JUDGE
    _ACTIVE_JUDGE = judge

def get_judge_provider() -> Any | None:
    return _ACTIVE_JUDGE
