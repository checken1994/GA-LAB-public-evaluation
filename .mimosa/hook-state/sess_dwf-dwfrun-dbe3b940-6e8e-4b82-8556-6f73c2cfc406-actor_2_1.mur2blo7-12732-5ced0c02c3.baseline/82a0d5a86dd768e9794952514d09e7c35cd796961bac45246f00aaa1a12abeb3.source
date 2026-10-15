"""[ZONE-FIX 2026-09-26] Regression — HandsExecutor bounds + rollback path
validation.

Item A (pc.search_workspace): the workspace walk must be LAZY — the whole tree
must not be materialized (list(rglob)) before the scanned/match bounds stop
the loop.

Item B (pc.read_file): the hands path must clamp maxBytes to the same 1MB
bound the API route enforces (pc_controller_routes.py Field le=1_000_000).

Item C (rollback): a checkpoint ledger entry whose backupPath escapes the
managed backup directory must be REFUSED fail-closed (crafted/poisoned ledger
would otherwise copy an arbitrary system file into the workspace); a
legitimate backup (inside controller.backup_dir) must still restore.
"""
from __future__ import annotations

import asyncio
import json
import sys

from scp.hands.hands_executor import HandsExecutor
from scp.pc_control.pc_controller import PCController
from scp.security.capability_epoch import CapabilityAuthority


def _setup_executor(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    cap_auth = CapabilityAuthority(tmp_path / "capability_state.json")
    executor = HandsExecutor(
        controller=PCController(working_dir=workspace),
        capability_authority=cap_auth,
        data_dir=tmp_path / "hands_data",
    )
    return executor, workspace, cap_auth


def test_search_workspace_walk_is_lazy_not_materialized(tmp_path):
    executor, workspace, cap_auth = _setup_executor(tmp_path)
    for d in range(40):
        dir_path = workspace / f"dir_{d:02d}"
        dir_path.mkdir()
        for f in range(100):
            (dir_path / f"file_{f:03d}.txt").write_text("needle\n", encoding="utf-8")

    # Python 3.12 pathlib.rglob raises os.scandir per directory visited: an
    # EAGER list(root.rglob("*")) walks the whole tree (>= 41 scandir calls)
    # BEFORE the matches>=50 bound stops the loop; a lazy walk stops after
    # the first directory (100 candidates >= 50 matches).
    scandir_events: list[str] = []
    root_prefix = str(workspace)

    def _hook(event, args):
        if event in ("os.scandir", "os.listdir"):
            path = str(args[0]) if args else ""
            if path.startswith(root_prefix):
                scandir_events.append(path)

    token = cap_auth.issue("hands:pc.search_workspace")
    sys.addaudithook(_hook)
    try:
        result = asyncio.run(
            executor.execute(
                action="pc.search_workspace",
                params={"query": "needle", "path": str(workspace)},
                capability_level=0,
                approved=False,
                capability_token=token,
            )
        )
    finally:
        pass  # audit hooks cannot be removed; this one only records

    assert result.get("success") is True
    assert result.get("evidence", {}).get("matchCount") == 50
    assert len(scandir_events) < 20, (
        f"workspace walk materialized the whole tree before the bounds "
        f"({len(scandir_events)} scandir calls >= full-tree threshold)"
    )


def test_read_file_max_bytes_is_capped_on_hands_path(tmp_path):
    executor, workspace, cap_auth = _setup_executor(tmp_path)
    big = workspace / "big.txt"
    big.write_text("A" * 2_000_000, encoding="utf-8")

    token = cap_auth.issue("hands:pc.read_file")
    result = asyncio.run(
        executor.execute(
            action="pc.read_file",
            params={"path": str(big), "maxBytes": 5_000_000},
            capability_level=0,
            approved=False,
            capability_token=token,
        )
    )
    assert result.get("success") is True
    assert len(result.get("content", "")) <= 1_000_000, (
        "hands pc.read_file bypassed the route's 1MB maxBytes bound"
    )
    assert result.get("truncated") is True


def test_rollback_refuses_backup_path_outside_managed_backup_dir(tmp_path):
    executor, workspace, cap_auth = _setup_executor(tmp_path)

    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "stolen_secret.env"
    secret.write_text("API_KEY=TOPSECRET", encoding="utf-8")

    target = workspace / "innocent.txt"
    write_token = cap_auth.issue("hands:pc.write_file")
    confirmation_id = executor.controller.human_store.record_confirmation(
        action="pc.write_file", target=str(target.resolve()), ttl_seconds=60,
    )
    write_res = asyncio.run(
        executor.execute(
            action="pc.write_file",
            params={"path": str(target), "content": "initial_content", "confirmation_id": confirmation_id},
            capability_level=3,
            approved=True,
            capability_token=write_token,
        )
    )
    assert write_res.get("success") is True
    checkpoint_id = write_res["checkpointId"]

    # Poison the ledger: point backupPath at the outside secret file.
    lines = executor.checkpoint_path.read_text(encoding="utf-8").splitlines()
    poisoned = []
    for line in lines:
        record = json.loads(line)
        if record.get("checkpointId") == checkpoint_id:
            record["backupPath"] = str(secret)
            record["existed"] = True
        poisoned.append(json.dumps(record))
    executor.checkpoint_path.write_text("\n".join(poisoned) + "\n", encoding="utf-8")

    rollback_token = cap_auth.issue("hands:rollback")
    rb = asyncio.run(
        executor.rollback(
            checkpoint_id=checkpoint_id,
            capability_level=3,
            approved=True,
            capability_token=rollback_token,
        )
    )
    assert rb.get("success") is False, f"traversal backupPath accepted: {rb}"
    assert "backup directory" in rb.get("error", "")
    assert not target.exists() or target.read_text(encoding="utf-8") != "API_KEY=TOPSECRET", (
        "arbitrary outside file was copied into the workspace"
    )


def test_rollback_still_restores_legitimate_backup(tmp_path):
    executor, workspace, cap_auth = _setup_executor(tmp_path)

    target = workspace / "doc.txt"
    target.write_text("BEFORE", encoding="utf-8")
    write_token = cap_auth.issue("hands:pc.write_file")
    confirmation_id = executor.controller.human_store.record_confirmation(
        action="pc.write_file", target=str(target.resolve()), ttl_seconds=60,
    )
    write_res = asyncio.run(
        executor.execute(
            action="pc.write_file",
            params={"path": str(target), "content": "AFTER", "confirmation_id": confirmation_id},
            capability_level=3,
            approved=True,
            capability_token=write_token,
        )
    )
    assert write_res.get("success") is True
    checkpoint_id = write_res["checkpointId"]
    assert target.read_text(encoding="utf-8") == "AFTER"

    rollback_token = cap_auth.issue("hands:rollback")
    rb = asyncio.run(
        executor.rollback(
            checkpoint_id=checkpoint_id,
            capability_level=3,
            approved=True,
            capability_token=rollback_token,
        )
    )
    assert rb.get("success") is True, f"legitimate restore broken by the path check: {rb}"
    assert rb.get("action") == "restore_backup"
    assert target.read_text(encoding="utf-8") == "BEFORE"
