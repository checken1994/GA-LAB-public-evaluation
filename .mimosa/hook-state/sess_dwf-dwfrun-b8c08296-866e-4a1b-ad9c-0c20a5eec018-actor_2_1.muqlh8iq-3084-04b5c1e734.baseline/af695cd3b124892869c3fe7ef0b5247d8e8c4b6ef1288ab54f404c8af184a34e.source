#!/usr/bin/env python3
"""Verify a committed snapshot manifest against Git, not report self-claims."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8").strip()


def inventory(commit: str) -> list[dict[str, str]]:
    raw = subprocess.check_output(["git", "ls-tree", "-r", "-z", commit], encoding=None)
    rows: list[dict[str, str]] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        meta, path = item.split(b"\t", 1)
        mode, kind, oid = meta.decode("ascii").split(" ", 2)
        path_text = path.decode("utf-8")
        if path_text == "reports/manifests_202608/ROOT_SCP_SNAPSHOT_MANIFEST_20260826.json":
            continue
        rows.append({"mode": mode, "type": kind, "blob": oid, "path": path_text})
    return sorted(rows, key=lambda row: row["path"])


def verification_target(current: str, captured: str, parents: list[str]) -> tuple[str, str]:
    """Choose a verifiable Git tree without trusting a synthetic merge ref."""
    if current == captured or captured in parents:
        return captured, "captured_git_tree"
    return current, "current_tree_excluding_manifest"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest: dict[str, Any] = json.loads(args.manifest.read_text(encoding="utf-8"))
    captured = str(manifest["captured_commit"])
    current = git("rev-parse", "HEAD")
    repo_root = Path(git("rev-parse", "--show-toplevel")).resolve()
    commit_object = git("cat-file", "-p", current)
    parents = [line.split(" ", 1)[1] for line in commit_object.splitlines() if line.startswith("parent ")]
    target_commit, verification_mode = verification_target(current, captured, parents)
    if verification_mode == "captured_git_tree":
        try:
            rows = inventory(target_commit)
            actual_tree = git("rev-parse", f"{target_commit}^{{tree}}")
        except subprocess.CalledProcessError:
            if current == captured:
                raise
            verification_mode = "shallow_current_tree_excluding_manifest"
            current_rows = inventory(current)
            expected_rows = list(manifest["inventory"])
            expected_paths = {str(row["path"]) for row in expected_rows}
            current_paths = {str(row["path"]) for row in current_rows}
            if current_paths - expected_paths:
                raise SystemExit("shallow checkout has unexpected files beyond the captured manifest inventory")
            rows = current_rows
            actual_tree = str(manifest["captured_tree"])
    else:
        rows = inventory(current)
        expected_rows = list(manifest["inventory"])
        expected_paths = {str(row["path"]) for row in expected_rows}
        current_paths = {str(row["path"]) for row in rows}
        if current_paths - expected_paths:
            raise SystemExit("current checkout has unexpected files beyond the captured manifest inventory")
        actual_tree = str(manifest["captured_tree"])
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    actual_sha = hashlib.sha256(canonical).hexdigest()
    if len(rows) != int(manifest["tracked_count"]):
        raise SystemExit(f"tracked count mismatch: {len(rows)} != {manifest['tracked_count']}")
    if actual_sha != manifest["inventory_sha256"]:
        raise SystemExit("tracked inventory hash mismatch")
    if verification_mode == "captured_git_tree" and actual_tree != str(manifest["captured_tree"]):
        raise SystemExit("captured tree SHA mismatch")
    by_path = {row["path"]: row for row in rows}
    for path_name, expected in manifest["required_paths"].items():
        if path_name not in by_path or by_path[path_name]["blob"] != expected["blob"]:
            raise SystemExit(f"required path/blob mismatch: {path_name}")
        try:
            data = subprocess.check_output(["git", "show", f"{target_commit}:{path_name}"], encoding=None)
        except subprocess.CalledProcessError:
            try:
                # In a depth-1 checkout the captured parent blob may be absent,
                # but the current commit blob is available and is byte-stable.
                data = subprocess.check_output(["git", "show", f"{current}:{path_name}"], encoding=None)
            except subprocess.CalledProcessError:
                data = (repo_root / path_name).read_bytes()
        if len(data) != int(expected["bytes"]) or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise SystemExit(f"required path content hash mismatch: {path_name}")
    print(json.dumps({"status": "PASS_WITHIN_SCOPE", "verification_mode": verification_mode, "captured_commit": captured, "current_head": current, "tracked_count": len(rows), "tree": actual_tree}, indent=2))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
