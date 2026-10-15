"""Knowledge interfaces and protocols."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ILearningDB(Protocol):
    def execute_insert(self, table: str, data: dict[str, Any]) -> int:
        ...
    def execute_query(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        ...
