"""Human-review guide for fixes that cannot be applied safely."""
from __future__ import annotations

import os
from pathlib import Path


def ensure_review_guide(pending_dir: str | Path) -> Path:
    """Write a truthful, atomic review guide for the currently queued items."""
    directory = Path(pending_dir)
    directory.mkdir(parents=True, exist_ok=True)
    items = sorted(
        path.name
        for path in directory.glob("*.py")
        if path.is_file()
    )

    lines = [
        "# Pending fix human review",
        "",
        "These files were not applied automatically because the proposed change could not be represented as a safe patch.",
        "",
        "For each queued item:",
        "1. Review the referenced source file and the proposed change together.",
        "2. Choose an explicit decision: approve, reject, or defer.",
        "3. If approved, apply the change manually to the source; do not execute the queued review file.",
        "4. Run the relevant tests and reality checks after the manual change.",
        "5. Remove the queued item only after the decision and resulting evidence are recorded.",
        "",
        "## Currently queued items",
    ]
    if items:
        lines.extend(f"- `{name}`" for name in items)
    else:
        lines.append("- None")
    lines.append("")

    target = directory / "README.md"
    temp = directory / ".README.md.tmp"
    # Durability must be cross-platform. On Windows, fsync() on a read-only
    # descriptor can fail with EBADF; flush and fsync the writable descriptor
    # before the atomic replace instead.
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, target)
    return target
