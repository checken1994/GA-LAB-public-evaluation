from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IEvidenceStore(Protocol):
    objects_dir: Path
    db: Any

    def get(self, evidence_id: str) -> dict[str, Any] | None:
        ...

    def observe(self, **kwargs: Any) -> dict[str, Any]:
        ...
