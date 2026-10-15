from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IEvolutionEngine(Protocol):
    def evolve_cycle(self, max_bugs: int = 20) -> dict[str, Any]:
        ...

def get_relative_repo_path(filepath: Path | str, repo_root: Path | None = None) -> str:
    """Canonical repository relative path calculator for all subsystems."""
    p = Path(filepath).resolve()
    root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")
