import os
import platform
import tempfile

import pytest

from scp.security.capability_epoch import CapabilityAuthority, CapabilityToken
from scp.security.os_sandbox import ProcessIsolationEnvironment, isolation_capability


def test_sandbox_executes_command_inside_job_object():
    if platform.system() != "Windows":
        pytest.skip("Job Object sandbox is Windows-specific")
    assert isolation_capability()["job_object"] is True, "pywin32 must be present"
    with tempfile.TemporaryDirectory() as tmp:
        authority = CapabilityAuthority(state_path=os.path.join(tmp, "caps.sqlite3"))
        token = authority.issue("sandbox-verify")
        pie = ProcessIsolationEnvironment(authority)
        result = pie.execute_bounded(token, ["cmd", "/c", "echo", "alive-in-job-object"])
        assert result.returncode == 0
        assert "alive-in-job-object" in result.stdout

def test_sandbox_rejects_invalid_capability():
    if platform.system() != "Windows":
        pytest.skip("Job Object sandbox is Windows-specific")
    with tempfile.TemporaryDirectory() as tmp:
        authority = CapabilityAuthority(state_path=os.path.join(tmp, "caps.sqlite3"))
        pie = ProcessIsolationEnvironment(authority)
        forged = CapabilityToken(subject="intruder", epoch=999, token_id="fake", issued_at=0.0)
        with pytest.raises(PermissionError):
            pie.execute_bounded(forged, ["cmd", "/c", "echo", "should-not-run"])


# ===========================================================================
# [SEC-FIX dead-branch 2026-09-26] The second Linux rlimit block in
# execute_bounded was unreachable (the first Linux branch always returns or
# raises). Probe evidence: sys.settrace over forced platform "Linux" and
# "Darwin" executed NONE of the dead block's lines and `preexec` was always
# None. The block was deleted; these tests pin the contract.
# ===========================================================================

def _make_pie(tmp):
    from scp.security.os_sandbox import ProcessIsolationEnvironment as PIE

    authority = CapabilityAuthority(state_path=os.path.join(tmp, "caps_dead_branch.json"))
    token = authority.issue("dead-branch-probe")
    return PIE(authority), token


def test_execute_bounded_linux_without_bwrap_fails_closed(tmp_path, monkeypatch):
    """Contract pin: Linux không có bwrap → RuntimeError (DNA #27 fail-closed).
    Phải giữ nguyên sau khi xóa dead branch — KHÔNG được hạ cấp thành rlimit."""

    from scp.security import os_sandbox as OS

    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(OS.shutil, "which", lambda name: None)
    pie, token = _make_pie(tmp_path)
    with pytest.raises(RuntimeError, match="bwrap is missing"):
        pie.execute_bounded(token, ["echo", "nope"], cwd=None)
    # Nếu code hạ cấp thành rlimit-fallback rồi subprocess.run, lệnh echo thật
    # sẽ chạy và trả về bình thường → pytest.raises phía trên sẽ FAIL.


def test_no_dead_second_linux_branch():
    """[SEC-FIX dead-branch] execute_bounded chỉ được chứa MỘT check
    `_plat.system() == "Linux"`. Trước fix có 2 (bản thứ 2 chết) → test này
    đỏ trên code cũ, xanh trên code mới."""
    import ast
    import inspect
    import textwrap

    from scp.security.os_sandbox import ProcessIsolationEnvironment

    source = textwrap.dedent(inspect.getsource(ProcessIsolationEnvironment.execute_bounded))
    tree = ast.parse(source)
    linux_checks = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Call)
        and isinstance(node.left.func, ast.Attribute)
        and node.left.func.attr == "system"
    ]
    assert len(linux_checks) == 1, (
        f"execute_bounded phải chỉ có 1 Linux check (thấy {len(linux_checks)}) — "
        "nhánh Linux thứ hai là dead code hoặc regression đã quay lại"
    )


def test_darwin_fallback_runs_subprocess_with_no_rlimit(tmp_path, monkeypatch):
    """Contract pin: non-Windows non-Linux chạy subprocess thường, preexec_fn=None
    (rlimit fallback đã bị xóa cùng dead branch — không còn đường nào set preexec)."""
    from subprocess import CompletedProcess

    from scp.security import os_sandbox as OS

    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    captured = {}

    def _fake_run(cmd, **kwargs):
        captured.update(kwargs)
        return CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(OS.subprocess, "run", _fake_run)
    pie, token = _make_pie(tmp_path)
    result = pie.execute_bounded(token, ["echo", "hi"], cwd=None)
    assert result.returncode == 0
    assert captured.get("preexec_fn") is None
