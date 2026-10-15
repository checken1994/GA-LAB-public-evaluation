"""[F-RUN-01 audit-r2 2026-10-01] Kill switch MUST block /ask — causal tests.

Causal chain of the bug (audit A9, OBSERVED live): POST /v3/pc/kill wrote the
PCController flag file `data/pc_controller/KILL_SWITCH`, but the ask path
never consulted it — a /ask issued after the kill still created a kernel task
and ran it to COMPLETED.

Fix under test (3 layers, each pinned here):
  1. /ask admission gate (scp/api_server.py::_pc_kill_switch_engaged) —
     fail-closed refusal BEFORE judge/kernel work, with an explicit reason
     (falsification_status=KILL_SWITCH_ENGAGED, governance KILL, REJECTED).
  2. Kernel bridge (pc_controller_routes::_engage_kernel_global_kill /
     _release_kernel_global_kill) — engaging the flag ALSO flips
     taskkernel.set_global_kill on every live ask-kernel adapter, fencing
     in-flight leases (epoch bump) and blocking claim()/claim_next().
  3. Path authority (pc_control.pc_controller.default_kill_switch_path) —
     controller and ask gate share ONE derivation (drift guard).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault(
    "SCP_CAPABILITY_SECRET",
    "test-capability-secret-for-automated-suites-only-32bytes",
)

from scp.security.capability_epoch import CapabilityAuthority
from scp.security.jwt_guard import create_access_token


def _flag_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "pc_controller" / "KILL_SWITCH"


@pytest.fixture(autouse=True)
def _isolate_ask_kernel_adapter_registry(monkeypatch):
    """[FA-01 HARNESS isolation, two-sided] ``api_server._ASK_KERNEL_ADAPTERS``
    is a module-global registry that lives for the whole process: a REAL /ask
    elsewhere in the suite (e.g. T02 test_ask_world_state_hook_cs2) registers
    an adapter via ``_get_ask_kernel_adapter`` (api_server.py) and has no
    teardown, so by the time this file runs the shared dict is already
    polluted. The exact-equality assertions of the Layer 2 route tests are
    only meaningful on a registry containing exactly the adapters THIS test
    installed. The fixture swaps the module attribute for a FRESH empty dict
    (mutations during the test land in the new dict; monkeypatch restores the
    original attribute afterwards), so isolation works both ways: this test
    sees no earlier leaks and leaks nothing forward. Assertion strictness is
    untouched — only state isolation is added (no test skipped, no assertion
    loosened)."""
    from scp import api_server

    monkeypatch.setattr(api_server, "_ASK_KERNEL_ADAPTERS", {})


@pytest.fixture()
def pc_working_dir(tmp_path, monkeypatch):
    """Isolated kill-switch authority dir + isolated JWT secret."""
    monkeypatch.setenv("SCP_PC_WORKING_DIR", str(tmp_path))
    monkeypatch.setenv("SCP_JWT_SECRET", "f-run-01-test-jwt-secret-not-for-production")
    monkeypatch.delenv("SCP_PC_CONTROLLER_TOKEN", raising=False)
    return tmp_path


def _engage_flag(tmp_path: Path, reason: str = "audit-r2 test") -> Path:
    flag = _flag_path(tmp_path)
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text(reason, encoding="utf-8")
    return flag


def _ask_client() -> TestClient:
    from scp import api_server

    return TestClient(api_server.app)  # no lifespan — judge NOT ready (503 control)


def _ask_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}


class _FakeKernel:
    def __init__(self):
        self.calls: list[tuple[bool, str]] = []
        self.next_epoch = 3

    def set_global_kill(self, active: bool, actor: str = "operator") -> int:
        self.calls.append((bool(active), actor))
        if active:
            self.next_epoch += 1
        return self.next_epoch


class _FakeAdapter:
    def __init__(self):
        self.kernel = _FakeKernel()


# ---------------------------------------------------------------------------
# Layer 1 — /ask admission gate
# ---------------------------------------------------------------------------


def test_ask_blocked_when_kill_switch_engaged(pc_working_dir):
    """A9 closure: kill engaged → /ask bị CHẶN fail-closed với lý do rõ ràng.

    Trước fix: /ask sau kill vẫn tạo kernel task và chạy tới COMPLETED.
    """
    from scp import api_server

    flag = _engage_flag(pc_working_dir)
    assert flag.exists()

    # Spy: gate phải chặn TRƯỚC khi bất kỳ kernel work nào bắt đầu.
    def _must_not_be_called():
        raise AssertionError("kill switch engaged nhưng /ask vẫn đi vào kernel path")

    monkey_spy = pytest.MonkeyPatch()
    monkey_spy.setattr(api_server, "_get_ask_kernel_adapter", _must_not_be_called)
    try:
        client = _ask_client()
        response = client.post("/ask", json={"question": "should be blocked"}, headers=_ask_headers())
    finally:
        monkey_spy.undo()

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "FAIL"
    assert body["falsification_status"] == "KILL_SWITCH_ENGAGED"
    assert body["governance_decision"] == "KILL"
    # ledger.attach ghi đè ledger_status = trạng thái GHI ledger ("OK");
    # disposition fail-closed nằm ở run_status=REJECTED (contract
    # RequestRunLedger.attach/classify_result — REJECTED ∈ TERMINAL_STATUSES).
    assert body["run_status"] == "REJECTED"
    assert body["ledger_status"] in {"OK", "DB_WRITE_FAILED"}
    assert "Kill switch engaged" in body["final_answer"]


def test_ask_not_blocked_when_kill_switch_absent(pc_working_dir):
    """Control: flag vắng mặt → gate KHÔNG chặn (request đi tiếp tới judge gate 503)."""
    assert not _flag_path(pc_working_dir).exists()
    client = _ask_client()
    response = client.post("/ask", json={"question": "control"}, headers=_ask_headers())
    assert response.status_code == 503  # judge_initializing — KHÔNG phải kill-switch block
    body = response.json()
    assert body.get("detail") == "judge_initializing"


def test_ask_gate_fails_closed_when_flag_unreadable(pc_working_dir, monkeypatch):
    """Kill-switch state UNKNOWN (flag không đọc được) → refuse (fail-closed)."""
    from scp import api_server

    class _BoomPath:
        def exists(self):
            raise OSError("simulated flag probe failure")

    monkeypatch.setattr(api_server, "default_kill_switch_path", lambda: _BoomPath())
    client = _ask_client()
    response = client.post("/ask", json={"question": "unknown state"}, headers=_ask_headers())
    body = response.json()
    assert body["verdict"] == "FAIL"
    assert body["falsification_status"] == "KILL_SWITCH_ENGAGED"
    assert body["governance_decision"] == "KILL"


# ---------------------------------------------------------------------------
# Layer 2 — kernel bridge trong /v3/pc/kill và /v3/pc/kill/clear
# ---------------------------------------------------------------------------


def _route_client() -> TestClient:
    """Real pc_controller router without depending on the API profile."""
    from scp.api.routes.pc_controller_routes import router as pc_router

    app = FastAPI()
    app.include_router(pc_router)
    return TestClient(app)


def _inject_fake_adapter(monkeypatch) -> tuple[str, _FakeAdapter]:
    from scp import api_server

    adapter = _FakeAdapter()
    key = ("f-run-01-fake.sqlite", "f-run-01-fake.jsonl")
    monkeypatch.setitem(api_server._ASK_KERNEL_ADAPTERS, key, adapter)
    return str(key), adapter


def test_pc_kill_route_engages_kernel_global_kill(pc_working_dir, monkeypatch):
    """POST /v3/pc/kill phải ĐỒNG THỜI engage kernel global kill (set_global_kill True)."""
    from scp.api.routes import pc_controller_routes
    from scp.pc_control.pc_controller import PCController

    key, adapter = _inject_fake_adapter(monkeypatch)
    monkeypatch.setenv("SCP_PC_CONTROLLER_TOKEN", "f-run-01-pc-token")
    # Hermetic: module-level `_controller` bind path theo lần import ĐẦU tiên
    # của process — gán controller trong tmp của test này để flag file đi vào
    # đúng authority dir (chống pollution chéo test).
    monkeypatch.setattr(
        pc_controller_routes, "_controller", PCController(working_dir=pc_working_dir)
    )

    client = _route_client()
    response = client.post(
        "/v3/pc/kill",
        json={"reason": "audit-r2 kernel bridge test"},
        headers={"x-scp-pc-token": "f-run-01-pc-token"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["killSwitch"] is True
    assert body["kernel_global_kill"]["engaged"] == [{"adapter": key, "epoch": adapter.kernel.next_epoch}]
    assert adapter.kernel.calls == [(True, "pc_kill_switch")]


def test_pc_kill_route_survives_kernel_bridge_failure(pc_working_dir, monkeypatch):
    """Kernel kill fail (DB locked...) KHÔNG được hạ kill-switch flag file."""
    from scp.api.routes import pc_controller_routes
    from scp.pc_control.pc_controller import PCController

    key, adapter = _inject_fake_adapter(monkeypatch)
    monkeypatch.setattr(
        pc_controller_routes, "_controller", PCController(working_dir=pc_working_dir)
    )

    def _boom(active, actor="operator"):
        raise RuntimeError("simulated kernel lock")

    adapter.kernel.set_global_kill = _boom
    monkeypatch.setenv("SCP_PC_CONTROLLER_TOKEN", "f-run-01-pc-token")

    client = _route_client()
    response = client.post(
        "/v3/pc/kill",
        json={"reason": "bridge failure tolerance"},
        headers={"x-scp-pc-token": "f-run-01-pc-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["killSwitch"] is True  # flag file vẫn engage
    assert {"adapter": key, "error": "RuntimeError"} in body["kernel_global_kill"]["errors"]
    assert body["kernel_global_kill"]["engaged"] == []
    assert _flag_path(pc_working_dir).exists()


def test_kernel_bridge_real_taskkernel_blocks_begin(tmp_path, monkeypatch):
    """REAL kernel enforcement: bridge engage → adapter.begin() dies fail-closed.

    Không LLM, không mock kernel: AskKernelAdapter thật trên SQLite tmp —
    sau _engage_kernel_global_kill, control row global_kill=1 (đọc trực tiếp
    SQLite — FA-12 runtime data) và adapter.begin() (create→claim) phải raise
    KillSwitchActive tại kernel.claim (taskkernel._assert_not_killed).
    """
    import sqlite3

    from scp import api_server
    from scp.ask_kernel_adapter import AskKernelAdapter
    from scp.api.routes.pc_controller_routes import (
        _engage_kernel_global_kill,
        _release_kernel_global_kill,
    )
    from scp.task_kernel_parts.definitions import KillSwitchActive

    db_path = tmp_path / "kernel-bridge.sqlite"
    trace_path = tmp_path / "kernel-bridge.jsonl"
    adapter = AskKernelAdapter(str(db_path), str(trace_path))
    key = (str(db_path), str(trace_path))
    monkeypatch.setitem(api_server._ASK_KERNEL_ADAPTERS, key, adapter)

    result = _engage_kernel_global_kill()
    assert {"adapter": str(key), "epoch": 1} in result["engaged"], result

    # Runtime data (FA-12): đọc control row trực tiếp từ SQLite.
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT global_kill, global_kill_epoch FROM control WHERE id=1").fetchone()
    assert row == (1, 1), f"kernel control row phải global_kill=1 epoch=1, thấy {row}"

    with pytest.raises(KillSwitchActive):
        adapter.begin(
            "question under kernel kill",
            [],
            "",
            session_id="bridge-real-kernel-test",
        )

    release = _release_kernel_global_kill()
    assert {"adapter": str(key)} in release["released"], release
    # Sau release, admission hoạt động trở lại (task được tạo + claim OK).
    handle = adapter.begin(
        "question after kernel release",
        [],
        "",
        session_id="bridge-real-kernel-test",
    )
    assert handle["task_id"], "sau release kernel phải nhận ask trở lại"


def test_pc_clear_route_releases_kernel_global_kill(pc_working_dir, monkeypatch):
    """/kill/clear thành công phải release kernel global kill (đối xứng với engage)."""
    from scp.api.routes import pc_controller_routes
    from scp.pc_control.pc_controller import PCController

    key, adapter = _inject_fake_adapter(monkeypatch)
    monkeypatch.setenv("SCP_PC_CONTROLLER_TOKEN", "f-run-01-pc-token")

    authority = CapabilityAuthority(pc_working_dir / "capability_state.json")
    controller = PCController(working_dir=pc_working_dir, capability_authority=authority)
    controller.engage_kill_switch("setup: engaged before clear")
    assert controller.kill_switch_engaged()

    monkeypatch.setattr(pc_controller_routes, "_controller", controller)
    token = authority.issue("pc.clear_kill_switch")
    import json as _json

    token_header = (
        token.to_dict() if hasattr(token, "to_dict") else token
    )
    token_str = token_header if isinstance(token_header, str) else _json.dumps(token_header)

    client = _route_client()
    response = client.post(
        "/v3/pc/kill/clear",
        json={"approved": True},
        headers={
            "x-scp-pc-token": "f-run-01-pc-token",
            "x-scp-capability-token": token_str,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["killSwitch"] is False
    assert body["kernel_global_kill"]["released"] == [{"adapter": key}]
    assert (False, "pc_kill_switch_clear") in adapter.kernel.calls


# ---------------------------------------------------------------------------
# Layer 3 — path authority (drift guard)
# ---------------------------------------------------------------------------


def test_default_kill_switch_path_matches_default_controller(pc_working_dir):
    """PCController mặc định (no working_dir) và ask gate phải dùng CÙNG file."""
    from scp.pc_control.pc_controller import PCController, default_kill_switch_path

    controller = PCController()
    assert Path(controller.kill_switch_path) == default_kill_switch_path()


def test_explicit_working_dir_controller_keeps_own_flag(tmp_path, monkeypatch):
    """Controller truyền working_dir tường minh giữ flag riêng — không bị env override."""
    from scp.pc_control.pc_controller import PCController, default_kill_switch_path

    monkeypatch.setenv("SCP_PC_WORKING_DIR", str(tmp_path / "env-dir"))
    explicit_dir = tmp_path / "explicit-dir"
    controller = PCController(working_dir=explicit_dir)
    assert controller.kill_switch_path == explicit_dir / "data" / "pc_controller" / "KILL_SWITCH"
    # Gate vẫn đọc theo env authority (mặc định của deployment).
    assert default_kill_switch_path() == (tmp_path / "env-dir") / "data" / "pc_controller" / "KILL_SWITCH"
