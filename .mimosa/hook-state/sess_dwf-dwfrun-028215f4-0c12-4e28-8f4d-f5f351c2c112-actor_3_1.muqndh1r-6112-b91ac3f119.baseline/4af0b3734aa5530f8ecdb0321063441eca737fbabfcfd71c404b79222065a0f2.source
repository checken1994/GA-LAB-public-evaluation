#!/usr/bin/env python3
"""Require immutable merged-PR lineage before a fresh main handoff verdict."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


def validate_lineage(sha: str, expected: str, remote: str, parents: list[str],
                     pulls: list[dict], event: str, *, current_tree: str = "",
                     frozen_trees: dict[str, str] | None = None) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or remote != sha:
        raise ValueError("checkout SHA must equal live main SHA")
    if event not in {"push", "workflow_dispatch"}:
        raise ValueError("unsupported main handoff event")
    if event == "workflow_dispatch" and expected != sha:
        raise ValueError("dispatch must name the exact main merge SHA")
    if len(parents) not in {1, 2}:
        raise ValueError("customer handoff requires normal or linear PR merge lineage")
    matches = [pr for pr in pulls if pr.get("merged_at")
               and pr.get("merge_commit_sha") == sha
               and pr.get("base", {}).get("ref") == "main"
               and re.fullmatch(r"[0-9a-f]{40}", pr.get("head", {}).get("sha", ""))
               and (len(parents) == 1 or pr["head"]["sha"] == parents[1])
               and pr.get("head", {}).get("ref") == "integration/experiment-god-split-and-providers"]
    if len(matches) != 1:
        raise ValueError("exactly one merged integration PR must match main and frozen SHA")
    frozen = matches[0]["head"]["sha"]
    if (not re.fullmatch(r"[0-9a-f]{40}", current_tree)
            or (frozen_trees or {}).get(frozen) != current_tree):
        raise ValueError("main Git tree must exactly equal the immutable frozen PR head tree")
    return {"status": "PASS_WITHIN_SCOPE", "main_sha": sha, "frozen_sha": frozen,
            "tree": current_tree, "lineage_type": "linear_pr_merge" if len(parents) == 1 else "merge_commit",
            "pr": matches[0]["number"], "event": event}


def main() -> int:
    def read(*command: str) -> str:
        return subprocess.check_output(list(command), text=True, encoding="utf-8").strip()

    sha = os.environ["GITHUB_SHA"]
    if read("git", "rev-parse", "HEAD") != sha:
        raise ValueError("working checkout does not match GITHUB_SHA")
    repo = os.environ["GITHUB_REPOSITORY"]
    remote = read("gh", "api", f"repos/{repo}/git/ref/heads/main", "--jq", ".object.sha")
    parents = [line.split()[1] for line in read("git", "cat-file", "-p", "HEAD").splitlines()
               if line.startswith("parent ")]
    pages = json.loads(read("gh", "api", f"repos/{repo}/commits/{sha}/pulls", "--paginate", "--slurp"))
    pulls = [pr for page in pages for pr in page]
    frozen_trees = {}
    for pr in pulls:
        frozen = pr.get("head", {}).get("sha", "")
        if pr.get("merged_at") and pr.get("merge_commit_sha") == sha and re.fullmatch(r"[0-9a-f]{40}", frozen):
            read("git", "fetch", "--no-tags", "--depth=1", "origin", frozen)
            frozen_trees[frozen] = read("git", "rev-parse", f"{frozen}^{{tree}}")
    evidence = validate_lineage(sha, os.environ.get("HANDOFF_MERGE_SHA", ""), remote,
                                parents, pulls, os.environ["GITHUB_EVENT_NAME"],
                                current_tree=read("git", "rev-parse", "HEAD^{tree}"),
                                frozen_trees=frozen_trees)
    output = Path("reports/release/main-lineage.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
