#!/usr/bin/env python3
"""Create a reproducible manifest for a specific Git commit tree."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_PATHS = (
    ".github/workflows/scp-release-gate.yml",
    "scp/api_server.py",
    "scp/task_kernel.py",
    "scp/ask_kernel_adapter.py",
    "scp/autofix/restricted_exec.py",
    "scp/runtime/safe_math.py",
    "scp/history/migration.py",
    "scp/core/knowledge_io.py",
    # Release-critical authority + evidence artifacts pinned at freeze time.
    # The 2026-08-25/26 runtime report paths were removed by the evidence
    # cleanup (M4); the current equivalents are the AUDIT_READY audit runs and
    # the machine-readable authority spec files below.
    "reports/audit/audit-20260925-031649.json",
    "reports/audit/audit-20260925-140947.json",
    "spec/complete_scp_reference.yaml",
    "spec/protected_invariants.yaml",
    "spec/scp_future_target_manifest.yaml",
    "tools/summarize_bandit_report.py",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8").strip()


def blob_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], encoding=None)


def tree_inventory(commit: str) -> list[dict[str, str]]:
    raw = subprocess.check_output(["git", "ls-tree", "-r", "-z", commit], encoding=None)
    entries: list[dict[str, str]] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        meta, path = item.split(b"\t", 1)
        mode, kind, oid = meta.decode("ascii").split(" ", 2)
        path_text = path.decode("utf-8")
        # The manifest is committed after capture and must not hash itself.
        if path_text == "reports/manifests_202608/ROOT_SCP_SNAPSHOT_MANIFEST_20260826.json":
            continue
        entries.append({"mode": mode, "type": kind, "blob": oid, "path": path_text})
    entries.sort(key=lambda row: row["path"])
    return entries


def create_manifest(commit: str) -> dict[str, Any]:
    commit = git("rev-parse", commit)
    tree = git("rev-parse", f"{commit}^{{tree}}")
    inventory = tree_inventory(commit)
    canonical = json.dumps(inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    required: dict[str, Any] = {}
    by_path = {row["path"]: row for row in inventory}
    for path in REQUIRED_PATHS:
        if path not in by_path:
            raise FileNotFoundError(f"required tracked path missing at {commit}: {path}")
        data = blob_bytes(commit, path)
        required[path] = {
            "blob": by_path[path]["blob"],
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    parent = git("rev-parse", f"{commit}^") if git("rev-list", "--parents", "-n", "1", commit).count(" ") else None
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "captured_commit": commit,
        "captured_parent": parent,
        "captured_tree": tree,
        "tracked_count": len(inventory),
        "inventory_sha256": hashlib.sha256(canonical).hexdigest(),
        "scope": "recursive tracked Git tree at captured_commit; ignored/untracked files are outside this manifest",
        "required_paths": required,
        "inventory": inventory,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(create_manifest(args.commit), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
