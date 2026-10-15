from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from tools.verify_main_handoff import validate_lineage

SHA, FROZEN, BASE = "a" * 40, "b" * 40, "c" * 40
TREE = "d" * 40
PR = {"number": 31, "merged_at": "2026-09-04T00:00:00Z", "merge_commit_sha": SHA,
      "base": {"ref": "main"}, "head": {"sha": FROZEN, "ref": "integration/experiment-god-split-and-providers"}}


@pytest.mark.parametrize("event,expected", [("push", ""), ("workflow_dispatch", SHA)])
@pytest.mark.parametrize("parents", [[BASE], [BASE, FROZEN]])
def test_main_handoff_requires_exact_immutable_merge_lineage(event, expected, parents):
    evidence = validate_lineage(SHA, expected, SHA, parents, [PR], event,
                                current_tree=TREE, frozen_trees={FROZEN: TREE})
    assert evidence["main_sha"] == SHA
    assert evidence["frozen_sha"] == FROZEN
    assert evidence["pr"] == 31


@pytest.mark.parametrize("change", ["moved_main", "wrong_expected", "missing_expected",
                                   "nonmerge", "wrong_frozen", "unmerged", "wrong_merge",
                                   "wrong_branch", "no_pr", "duplicate_pr", "wrong_event"])
def test_stale_or_unproven_handoff_is_blocked(change):
    expected, remote, parents, event = SHA, SHA, [BASE, FROZEN], "workflow_dispatch"
    pulls = [copy.deepcopy(PR)]
    if change == "moved_main": remote = BASE
    elif change == "wrong_expected": expected = FROZEN
    elif change == "missing_expected": expected = ""
    elif change == "nonmerge": parents = []
    elif change == "wrong_frozen": pulls[0]["head"]["sha"] = BASE
    elif change == "unmerged": pulls[0]["merged_at"] = None
    elif change == "wrong_merge": pulls[0]["merge_commit_sha"] = BASE
    elif change == "wrong_branch": pulls[0]["base"]["ref"] = "other"
    elif change == "no_pr": pulls = []
    elif change == "duplicate_pr": pulls.append(copy.deepcopy(PR))
    elif change == "wrong_event": event = "pull_request"
    with pytest.raises(ValueError):
        validate_lineage(SHA, expected, remote, parents, pulls, event,
                          current_tree=TREE, frozen_trees={FROZEN: TREE})


@pytest.mark.parametrize("parents", [[BASE], [BASE, FROZEN]])
@pytest.mark.parametrize("trees", [{}, {FROZEN: "e" * 40}])
def test_even_a_merged_pr_cannot_handoff_missing_or_different_trees(parents, trees):
    with pytest.raises(ValueError, match="tree"):
        validate_lineage(SHA, SHA, SHA, parents, [PR], "workflow_dispatch",
                          current_tree=TREE, frozen_trees=trees)


def test_bot_merge_dispatch_does_not_bypass_any_fresh_gate():
    workflow = yaml.safe_load(Path(".github/workflows/scp-rc-promotion.yml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    promote = jobs["promote-to-main"]
    command = promote["steps"][-1]["run"]
    assert command.index('test "$MAIN_SHA" = "$MERGE_SHA"') < command.index("--ref main")
    assert '-f handoff_merge_sha="$MERGE_SHA"' in command
    assert '-f merge_method=squash -f sha="$FROZEN_SHA"' in command
    assert "inputs.approve_main_merge == true" in promote["if"]
    handoff = jobs["customer-handoff-verdict"]
    for gate in ("main-lineage-authority", "platform-gates", "security-and-durability", "manifest-provenance"):
        assert gate in handoff["needs"]
        assert f"needs.{gate}.result == 'success'" in handoff["if"]
    assert "inputs.handoff_merge_sha != ''" in handoff["if"]
    assert "github.ref == 'refs/heads/main'" in handoff["if"]
