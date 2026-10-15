"""Launcher contract tests — updated for API-only era (no Ollama, port 8000)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = (ROOT / "start-scp.bat").read_text(encoding="utf-8")


def test_manual_launcher_preflights_dashboard_dependency_and_build():
    assert 'dashboard\\node_modules\\next\\dist\\bin\\next' in LAUNCHER
    assert 'bun install --frozen-lockfile' in LAUNCHER
    assert 'start "SCP-Dashboard" cmd /k "cd /d %~dp0dashboard && set SCP_INTERNAL_URL=http://127.0.0.1:8000' in LAUNCHER
    assert '&& bun run start"' in LAUNCHER
    assert 'bun run build' in LAUNCHER


def test_launcher_is_api_only_no_ollama():
    """[MẢNH 12 — Map vs Territory] Launcher phải khớp code: không Ollama, không 11434, port 8000."""
    assert '11434' not in LAUNCHER, "FAIL: launcher vẫn tham chiếu Ollama port 11434"
    assert 'SCP-LLM-Bridge' in LAUNCHER, "FAIL: launcher thieu LLM-Bridge (R6-02)"
    assert 'SCP_LLM_BRIDGE_PORT=8081' in LAUNCHER, "FAIL: launcher phai cau hinh port 8081 cho LLM-Bridge"
    assert '8002' not in LAUNCHER, "FAIL: launcher vẫn dùng port cũ 8002"
    assert 'set SCP_INTERNAL_URL=http://127.0.0.1:8000' in LAUNCHER
    assert 'set LOOP_SCHEDULER_URL=http://127.0.0.1:3030' in LAUNCHER


def test_stop_launcher_never_kills_external_ollama_port():
    stop = (ROOT / "stop-scp.bat").read_text(encoding="utf-8")
    assert 'findstr ":11434 "' not in stop
    kill_lines = [line.lower() for line in stop.splitlines() if 'taskkill' in line.lower()]
    assert all('11434' not in line for line in kill_lines)
    assert 'taskkill' in stop.lower()
