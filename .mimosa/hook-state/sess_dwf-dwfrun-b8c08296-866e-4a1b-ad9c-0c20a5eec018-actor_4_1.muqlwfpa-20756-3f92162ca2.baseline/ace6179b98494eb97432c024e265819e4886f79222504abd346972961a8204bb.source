from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IGoalParser(Protocol):
    def parse(self, goal: str, **kwargs: Any) -> dict[str, Any]:
        ...

@runtime_checkable
class IHandsPlanner(Protocol):
    def create_plan(self, goal_data: dict[str, Any]) -> list[dict[str, Any]]:
        ...

@runtime_checkable
class IHandsExecutor(Protocol):
    async def execute_step(self, step: dict[str, Any]) -> dict[str, Any]:
        ...
