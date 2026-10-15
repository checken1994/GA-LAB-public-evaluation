#!/usr/bin/env python3
"""
Empirical Challenge Harness: Concurrency & Protocol Stress
Author: Challenger 2 (Protocol & Concurrency Stress Challenger)
Target: TaskKernelBridge, HandsExecutor, API Routes, Capability PEP
Governing Rules: INV-AUTH-01, INV-AUTH-02, INV-AUTH-03, FA-01 through FA-10
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["SCP_OTEL_ENABLED"] = "0"
os.environ["SCP_API_PROFILE"] = "full"
os.environ["SCP_PRODUCTION_MODE"] = "0"
os.environ["SCP_SKIP_STARTUP_GATE"] = "1"
import scp.observability.telemetry as scp_tel
scp_tel.setup_telemetry = lambda app: None

from scp.hands.hands_executor import HandsExecutor
from scp.hands.task_kernel_bridge import TaskKernelHandsBridge
from scp.pc_control.pc_controller import PCController
from scp.security.capability_epoch import CapabilityAuthority, CapabilityToken
from scp.task_kernel import TaskKernel


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def safe_cleanup(dir_path: Path):
    try:
        shutil.rmtree(str(dir_path), ignore_errors=True)
    except Exception:
        pass


def create_test_env(base_dir: Path):
    workspace = base_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    cap_state = base_dir / "capability_state.json"
    cap_auth = CapabilityAuthority(cap_state)
    executor = HandsExecutor(
        controller=PCController(working_dir=workspace),
        capability_authority=cap_auth,
        data_dir=base_dir / "hands_data",
    )
    db_path = base_dir / "kernel.sqlite3"
    bridge = TaskKernelHandsBridge(executor, db_path=db_path)
    return bridge, workspace, cap_auth, executor, db_path


async def challenge_1_concurrency_valid_tokens() -> dict[str, Any]:
    """
    Challenge 1: Concurrency with Valid Tokens
    Multiple concurrent bridge executions with valid capability tokens.
    """
    log("=== CHALLENGE 1: Concurrency with Valid Tokens ===")
    tmp_dir = Path(tempfile.mkdtemp(prefix="ch2_valid_"))
    try:
        bridge, workspace, cap_auth, executor, db_path = create_test_env(tmp_dir)

        num_tasks = 15
        tasks_data = []
        for i in range(num_tasks):
            file_path = workspace / f"valid_file_{i}.txt"
            content = f"valid_content_for_task_{i}_{uuid.uuid4().hex}"
            token = cap_auth.issue("hands:pc.write_file")
            req_key = f"valid-req-{i}-{uuid.uuid4().hex}"
            tasks_data.append({
                "index": i,
                "file_path": file_path,
                "content": content,
                "token": token,
                "req_key": req_key,
            })

        log(f"Launching {num_tasks} concurrent bridge executions with valid tokens...")
        start_time = time.perf_counter()

        async def exec_task(item):
            return await bridge.execute(
                action="pc.write_file",
                params={"path": str(item["file_path"]), "content": item["content"]},
                capability_level=3,
                approved=True,
                request_key=item["req_key"],
                capability_token=item["token"],
            )

        results = await asyncio.gather(*(exec_task(item) for item in tasks_data), return_exceptions=True)
        elapsed = time.perf_counter() - start_time
        log(f"Completed {num_tasks} concurrent executions in {elapsed:.3f}s")

        kernel = TaskKernel(str(db_path))

        for item, res in zip(tasks_data, results):
            assert not isinstance(res, Exception), f"Task {item['index']} raised exception: {res}"
            assert res.get("success") is True, f"Task {item['index']} execution failed: {res}"
            assert (res.get("verification") or {}).get("passed") is True, f"Task {item['index']} verification failed"

            # Check reality (filesystem)
            assert item["file_path"].exists(), f"File {item['file_path']} was not created on disk!"
            assert item["file_path"].read_text() == item["content"], f"Content mismatch in {item['file_path']}"

            # Check kernel task state
            task_id = res["kernel"]["taskId"]
            task_row = kernel.get_task(task_id)
            assert task_row["state"] == "COMPLETED", f"Task {task_id} state is {task_row['state']}, expected COMPLETED"

            # Check checkpoint epoch matches token epoch
            checkpoints = kernel.conn.execute(
                "SELECT capability_epoch, state FROM checkpoints WHERE task_id=?", (task_id,)
            ).fetchall()
            assert len(checkpoints) >= 1, f"Task {task_id} has no checkpoints!"
            for cp_epoch, cp_state in checkpoints:
                assert cp_epoch == item["token"].epoch, f"Checkpoint epoch {cp_epoch} != token epoch {item['token'].epoch}"
                assert cp_state == "WAITING_TOOL", f"Checkpoint state {cp_state} != WAITING_TOOL"

        kernel.close()
        bridge.kernel.close()
        log(f"[PASS] Challenge 1: All {num_tasks} concurrent tasks completed, files verified, epochs matched.")
        return {"status": "PASS", "tasks": num_tasks, "elapsed": elapsed}
    finally:
        safe_cleanup(tmp_dir)


async def challenge_2_concurrency_denial_missing_tokens() -> dict[str, Any]:
    """
    Challenge 2: Concurrency Denial (Missing Tokens)
    Multiple concurrent bridge executions WITHOUT capability tokens.
    """
    log("=== CHALLENGE 2: Concurrency Denial (Missing Tokens) ===")
    tmp_dir = Path(tempfile.mkdtemp(prefix="ch2_denial_"))
    try:
        bridge, workspace, cap_auth, executor, db_path = create_test_env(tmp_dir)

        num_tasks = 15
        tasks_data = []
        for i in range(num_tasks):
            file_path = workspace / f"denied_file_{i}.txt"
            content = f"denied_content_for_task_{i}_{uuid.uuid4().hex}"
            req_key = f"denial-req-{i}-{uuid.uuid4().hex}"
            tasks_data.append({
                "index": i,
                "file_path": file_path,
                "content": content,
                "req_key": req_key,
            })

        log(f"Launching {num_tasks} concurrent bridge executions WITHOUT tokens...")
        start_time = time.perf_counter()

        async def exec_denied(item):
            return await bridge.execute(
                action="pc.write_file",
                params={"path": str(item["file_path"]), "content": item["content"]},
                capability_level=3,
                approved=True,
                request_key=item["req_key"],
                capability_token=None,  # Missing token!
            )

        results = await asyncio.gather(*(exec_denied(item) for item in tasks_data), return_exceptions=True)
        elapsed = time.perf_counter() - start_time
        log(f"Completed {num_tasks} concurrent denial executions in {elapsed:.3f}s")

        kernel = TaskKernel(str(db_path))

        findings = []
        for item, res in zip(tasks_data, results):
            assert not isinstance(res, Exception), f"Task {item['index']} raised unexpected exception: {res}"
            assert res.get("success") is False, f"Task {item['index']} unexpectedly succeeded!"
            assert not item["file_path"].exists(), f"FATAL: File {item['file_path']} was written to disk despite denial!"

            error_msg = str(res.get("error", ""))
            requires_recovery = res.get("requiresRecovery")

            # Check if CapabilityRequiredError was properly returned
            if "CapabilityRequiredError" not in error_msg:
                findings.append({
                    "task_index": item["index"],
                    "error": error_msg,
                    "requiresRecovery": requires_recovery,
                    "task_id": (res.get("kernel") or {}).get("taskId"),
                })

        kernel.close()
        bridge.kernel.close()

        if findings:
            sample = findings[0]
            log(f"[BUG DETECTED] Challenge 2 FAILED: {len(findings)}/{num_tasks} denial responses corrupted!")
            log(f"Sample corrupt response: error='{sample['error']}', requiresRecovery={sample['requiresRecovery']}")
            return {
                "status": "FAIL",
                "reason": "Bridge internal crash on release() swallowed CapabilityRequiredError into OptimisticLockError with requiresRecovery=True",
                "sample": sample,
                "corrupt_count": len(findings),
            }
        else:
            log(f"[PASS] Challenge 2: All {num_tasks} concurrent denial tasks failed closed cleanly.")
            return {"status": "PASS", "tasks": num_tasks}
    finally:
        safe_cleanup(tmp_dir)


async def challenge_3_concurrency_scope_mismatch() -> dict[str, Any]:
    """
    Challenge 3: Concurrency Scope Mismatch Denial
    Multiple concurrent bridge executions with WRONG token subjects.
    """
    log("=== CHALLENGE 3: Concurrency Scope Mismatch Denial ===")
    tmp_dir = Path(tempfile.mkdtemp(prefix="ch2_scope_"))
    try:
        bridge, workspace, cap_auth, executor, db_path = create_test_env(tmp_dir)

        num_tasks = 10
        tasks_data = []
        for i in range(num_tasks):
            file_path = workspace / f"scope_mismatch_file_{i}.txt"
            content = f"scope_mismatch_content_{i}"
            token = cap_auth.issue("hands:pc.status")  # Read-only token
            req_key = f"scope-req-{i}-{uuid.uuid4().hex}"
            tasks_data.append({
                "index": i,
                "file_path": file_path,
                "content": content,
                "token": token,
                "req_key": req_key,
            })

        log(f"Launching {num_tasks} concurrent bridge executions with scope-mismatched tokens...")

        async def exec_scope(item):
            return await bridge.execute(
                action="pc.write_file",
                params={"path": str(item["file_path"]), "content": item["content"]},
                capability_level=3,
                approved=True,
                request_key=item["req_key"],
                capability_token=item["token"],
            )

        results = await asyncio.gather(*(exec_scope(item) for item in tasks_data), return_exceptions=True)
        kernel = TaskKernel(str(db_path))

        findings = []
        for item, res in zip(tasks_data, results):
            assert not isinstance(res, Exception), f"Task {item['index']} raised exception: {res}"
            assert res.get("success") is False, f"Task {item['index']} succeeded unexpectedly!"
            assert not item["file_path"].exists(), f"File {item['file_path']} was written to disk!"

            error_msg = str(res.get("error", ""))
            requires_recovery = res.get("requiresRecovery")

            if "CapabilityScopeMismatchError" not in error_msg:
                findings.append({
                    "task_index": item["index"],
                    "error": error_msg,
                    "requiresRecovery": requires_recovery,
                })

        kernel.close()
        bridge.kernel.close()

        if findings:
            sample = findings[0]
            log(f"[BUG DETECTED] Challenge 3 FAILED: {len(findings)}/{num_tasks} scope mismatch responses corrupted!")
            log(f"Sample corrupt response: error='{sample['error']}', requiresRecovery={sample['requiresRecovery']}")
            return {
                "status": "FAIL",
                "reason": "Bridge internal crash on release() swallowed CapabilityScopeMismatchError into OptimisticLockError with requiresRecovery=True",
                "sample": sample,
                "corrupt_count": len(findings),
            }
        else:
            log(f"[PASS] Challenge 3: All {num_tasks} scope-mismatched executions failed closed cleanly.")
            return {"status": "PASS", "tasks": num_tasks}
    finally:
        safe_cleanup(tmp_dir)


async def challenge_4_idempotency_replay() -> dict[str, Any]:
    """
    Challenge 4: Idempotency Replay Stress
    Verify:
    1. Sequential replay with valid token returns replayed=True, does not duplicate side effect.
    2. Concurrent race on same idempotency key: exactly one creates and executes, others resolve cleanly.
    3. Replay with modified content does not mutate disk file.
    """
    log("=== CHALLENGE 4: Idempotency Replay Stress ===")
    tmp_dir = Path(tempfile.mkdtemp(prefix="ch2_replay_"))
    try:
        bridge, workspace, cap_auth, executor, db_path = create_test_env(tmp_dir)
        kernel = TaskKernel(str(db_path))

        # Part 1: Sequential replay
        target_file = workspace / "idempotent_file.txt"
        initial_content = "original_content_verified"
        req_key = f"idem-key-{uuid.uuid4().hex}"
        token = cap_auth.issue("hands:pc.write_file")

        log("Step 1: Initial execution...")
        first_res = await bridge.execute(
            action="pc.write_file",
            params={"path": str(target_file), "content": initial_content},
            capability_level=3,
            approved=True,
            request_key=req_key,
            capability_token=token,
        )
        assert first_res.get("success") is True, f"First execution failed: {first_res}"
        task_id = first_res["kernel"]["taskId"]
        assert target_file.read_text() == initial_content

        events_before = len(kernel.get_events(task_id))

        log("Step 2: Sequential replay with mutated parameter attempt...")
        replay_res = await bridge.execute(
            action="pc.write_file",
            params={"path": str(target_file), "content": "MALICIOUS_OVERWRITE_ATTEMPT"},
            capability_level=3,
            approved=True,
            request_key=req_key,
            capability_token=token,
        )
        assert replay_res.get("replayed") is True, f"Expected replayed=True, got {replay_res}"
        assert replay_res.get("success") is False
        assert replay_res.get("safeToRetry") is False
        assert replay_res["kernel"]["taskId"] == task_id

        # Reality invariant: file content must NOT be overwritten!
        assert target_file.read_text() == initial_content, "File was overwritten by replay!"
        # Journal invariant: no new events appended
        assert len(kernel.get_events(task_id)) == events_before, "New events were appended on replay!"

        # Part 2: Concurrent race on identical request_key
        log("Step 3: Concurrent race on identical request_key (10 parallel requests)...")
        race_file = workspace / "race_file.txt"
        race_key = f"race-key-{uuid.uuid4().hex}"
        race_content = "race_content_winner"
        race_token = cap_auth.issue("hands:pc.write_file")

        async def fire_race(idx):
            return await bridge.execute(
                action="pc.write_file",
                params={"path": str(race_file), "content": f"{race_content}_{idx}"},
                capability_level=3,
                approved=True,
                request_key=race_key,
                capability_token=race_token,
            )

        race_results = await asyncio.gather(*(fire_race(i) for i in range(10)), return_exceptions=True)

        successes = [r for r in race_results if not isinstance(r, Exception) and r.get("success") is True]
        replays_or_denials = [
            r for r in race_results
            if not isinstance(r, Exception) and (r.get("replayed") is True or "Stable Hands request exists" in str(r.get("error", "")))
        ]

        log(f"Race outcome: {len(successes)} succeeded, {len(replays_or_denials)} replayed/fenced")
        assert len(successes) == 1, f"Expected exactly 1 successful execution in race, got {len(successes)}"
        assert race_file.exists(), "Race file was not written!"
        assert len(replays_or_denials) == 9, f"Expected 9 replayed/fenced requests, got {len(replays_or_denials)}"

        kernel.close()
        bridge.kernel.close()
        log("[PASS] Challenge 4: Idempotency replay and concurrent race invariants verified.")
        return {"status": "PASS"}
    finally:
        safe_cleanup(tmp_dir)


async def challenge_5_fastapi_route_concurrency() -> dict[str, Any]:
    """
    Challenge 5: FastAPI Route Concurrency & Stress
    """
    log("=== CHALLENGE 5: FastAPI Route Concurrency ===")
    from starlette.testclient import TestClient
    from scp.api_server import app
    import scp.api.routes.hands_routes as hands_routes

    pc_token = "stress-test-pc-token-123"
    os.environ["SCP_PC_CONTROLLER_TOKEN"] = pc_token
    headers = {
        "X-SCP-PC-Token": pc_token,
    }

    if not any(getattr(r, "path", "") == "/v3/hands/execute" for r in app.routes):
        app.include_router(hands_routes.router)

    tmp_dir = Path(tempfile.mkdtemp(prefix="ch2_api_"))
    try:
        workspace = tmp_dir / "workspace"
        workspace.mkdir()
        cap_state = tmp_dir / "cap_state.json"
        cap_auth = CapabilityAuthority(cap_state)

        executor = HandsExecutor(
            controller=PCController(working_dir=workspace),
            capability_authority=cap_auth,
            data_dir=tmp_dir / "hands_data",
        )
        hands_routes._hands = executor
        hands_routes._hands_bridge = TaskKernelHandsBridge(executor, db_path=tmp_dir / "kernel.sqlite3")

        client = TestClient(app)

        # 5A: Valid concurrent API requests
        log("Step 1: Testing concurrent valid requests to /v3/hands/execute...")
        num_api_tasks = 8
        api_items = []
        for i in range(num_api_tasks):
            f_path = str(workspace / f"api_file_{i}.txt")
            f_content = f"api_content_{i}"
            token = cap_auth.issue("hands:pc.write_file")
            token_dict = token.to_dict()
            req_key = f"api-req-{i}-{uuid.uuid4().hex}"
            api_items.append({
                "path": f_path,
                "content": f_content,
                "token_dict": token_dict,
                "req_key": req_key,
            })

        def call_api(item):
            return client.post(
                "/v3/hands/execute",
                headers={**headers, "X-SCP-Idempotency-Key": item["req_key"]},
                json={
                    "action": "pc.write_file",
                    "params": {"path": item["path"], "content": item["content"]},
                    "capabilityLevel": 3,
                    "approved": True,
                    "capabilityToken": item["token_dict"],
                },
            )

        loop = asyncio.get_event_loop()
        api_results = await asyncio.gather(*(loop.run_in_executor(None, call_api, item) for item in api_items))

        for item, resp in zip(api_items, api_results):
            assert resp.status_code == 200, f"API returned status {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data.get("success") is True, f"API execute failed: {data}"
            assert Path(item["path"]).exists(), f"File {item['path']} was not created!"
            assert Path(item["path"]).read_text() == item["content"]

        log("Step 2: Testing concurrent missing token requests to /v3/hands/execute...")
        denial_items = []
        for i in range(num_api_tasks):
            f_path = str(workspace / f"api_denied_{i}.txt")
            f_content = f"api_denied_content_{i}"
            req_key = f"api-denied-req-{i}-{uuid.uuid4().hex}"
            denial_items.append({
                "path": f_path,
                "content": f_content,
                "req_key": req_key,
            })

        def call_api_denied(item):
            return client.post(
                "/v3/hands/execute",
                headers={**headers, "X-SCP-Idempotency-Key": item["req_key"]},
                json={
                    "action": "pc.write_file",
                    "params": {"path": item["path"], "content": item["content"]},
                    "capabilityLevel": 3,
                    "approved": True,
                },
            )

        denial_results = await asyncio.gather(*(loop.run_in_executor(None, call_api_denied, item) for item in denial_items))

        findings = []
        for item, resp in zip(denial_items, denial_results):
            assert resp.status_code == 200, f"API status: {resp.status_code}"
            data = resp.json()
            assert data.get("success") is False, f"Expected fail-closed, got: {data}"
            assert not Path(item["path"]).exists(), f"File {item['path']} exists despite denial!"

            if "CapabilityRequiredError" not in str(data.get("error", "")):
                findings.append(data)

        # 5C: Replay through API route
        log("Step 3: Testing replay through /v3/hands/execute...")
        replay_item = api_items[0]
        replay_resp = client.post(
            "/v3/hands/execute",
            headers={**headers, "X-SCP-Idempotency-Key": replay_item["req_key"]},
            json={
                "action": "pc.write_file",
                "params": {"path": replay_item["path"], "content": "REPLAY_MUTATION"},
                "capabilityLevel": 3,
                "approved": True,
                "capabilityToken": replay_item["token_dict"],
            },
        )
        assert replay_resp.status_code == 200
        replay_data = replay_resp.json()
        assert replay_data.get("replayed") is True, f"Expected replayed=True, got: {replay_data}"
        assert replay_data.get("success") is False

        hands_routes._hands_bridge.kernel.close()

        if findings:
            sample = findings[0]
            log(f"[BUG DETECTED] Challenge 5: Route denial returned corrupted response: error='{sample.get('error')}', requiresRecovery={sample.get('requiresRecovery')}")
            return {
                "status": "FAIL",
                "reason": "Route denial cascades into OptimisticLockError with requiresRecovery=True",
                "sample": sample,
            }
        else:
            log("[PASS] Challenge 5: FastAPI route concurrency, denial, and replay verified.")
            return {"status": "PASS"}
    finally:
        safe_cleanup(tmp_dir)


async def main():
    print_banner = lambda t: print("\n" + "=" * 78 + f"\n  {t}\n" + "=" * 78, flush=True)
    print_banner("CHALLENGER 2: PROTOCOL & CONCURRENCY EMPIRICAL SUITE")

    t0 = time.perf_counter()
    summary = {}
    summary["challenge_1"] = await challenge_1_concurrency_valid_tokens()
    summary["challenge_2"] = await challenge_2_concurrency_denial_missing_tokens()
    summary["challenge_3"] = await challenge_3_concurrency_scope_mismatch()
    summary["challenge_4"] = await challenge_4_idempotency_replay()
    summary["challenge_5"] = await challenge_5_fastapi_route_concurrency()

    elapsed = time.perf_counter() - t0
    print_banner(f"EMPIRICAL CHALLENGE SUMMARY (Elapsed: {elapsed:.2f}s)")
    for name, res in summary.items():
        print(f"  {name}: {res['status']}")
        if res['status'] == 'FAIL':
            print(f"    Reason: {res['reason']}")
            if 'sample' in res:
                print(f"    Sample: {json.dumps(res['sample'], default=str)}")

    # Overall verdict
    has_fails = any(r["status"] == "FAIL" for r in summary.values())
    print("\n" + "-" * 78)
    if has_fails:
        print("OVERALL VERDICT: REJECT")
        print("Reason: Critical failure in Policy Denial path in TaskKernelHandsBridge (lines 450-455).")
        print("Calling self.kernel.release() after transition('FAILED') triggers OptimisticLockError,")
        print("corrupting the PEP denial response and incorrectly setting requiresRecovery=True.")
        sys.exit(2)
    else:
        print("OVERALL VERDICT: APPROVE")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
