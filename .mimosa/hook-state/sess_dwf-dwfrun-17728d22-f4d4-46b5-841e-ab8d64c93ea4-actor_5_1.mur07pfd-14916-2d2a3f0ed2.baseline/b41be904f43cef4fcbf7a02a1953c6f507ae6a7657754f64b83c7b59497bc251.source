"""[IDENTITY-PORT-PRECEDENCE 2026-09-26] service_identity phải khớp socket.

Live sweep: khi SCP_ENV_FILE set, ``load_selected_env()`` ở module import của
scp/api_server.py re-apply SCP_PORT=8000 của env file SAU khi
``__main__.main()`` đã resolve argv port 8091 và ghi vào os.environ → /health
quảng cáo configured_port 8000 trong khi uvicorn bind 8091 (identity tự mâu
thẫn với socket thật).

Fix: _scp_service_identity() dùng đúng precedence của socket —
argv PORT > SCP_PORT env > 8000 (giống __main__.main()).

Unit-level: gọi thẳng _scp_service_identity() (composition thật của identity)
— không boot server thật.
"""
from __future__ import annotations

import sys

from scp import api_server


def test_configured_port_equals_argv_port_when_env_file_port_differs(monkeypatch):
    """Env file port (SCP_PORT=8000 sau override) KHÔNG được thắng argv port
    8091 — identity phải báo port mà socket thật bind (argv)."""
    monkeypatch.setenv("SCP_PORT", "8000")
    monkeypatch.setattr(sys, "argv", ["/usr/bin/python", "-m", "scp", "8091"])

    identity = api_server._scp_service_identity()

    assert identity["configured_port"] == 8091


def test_env_port_used_when_no_argv_port(monkeypatch):
    """Boot chỉ qua env (python -m scp, không argv port) → env port giữ nguyên
    hành vi (main() cũng dùng env làm fallback)."""
    monkeypatch.setenv("SCP_PORT", "9123")
    monkeypatch.setattr(sys, "argv", ["/usr/bin/python", "-m", "scp"])

    identity = api_server._scp_service_identity()

    assert identity["configured_port"] == 9123


def test_default_port_8000_when_no_signal(monkeypatch):
    monkeypatch.delenv("SCP_PORT", raising=False)
    monkeypatch.setattr(sys, "argv", ["/usr/bin/python", "-m", "scp"])

    identity = api_server._scp_service_identity()

    assert identity["configured_port"] == 8000


def test_malformed_env_port_falls_back_to_argv_and_warns(monkeypatch, caplog):
    """MACH1-FIX-8 giữ nguyên: SCP_PORT hỏng → fallback + WARNING (khi argv
    không quyết định trước)."""
    monkeypatch.setattr(sys, "argv", ["/usr/bin/python", "-m", "scp"])
    monkeypatch.setenv("SCP_PORT", "not-a-port")

    with caplog.at_level("WARNING", logger="scp.api"):
        identity = api_server._scp_service_identity()

    assert identity["configured_port"] == 8000
    assert any("MACH1-FIX-8" in r.message for r in caplog.records)


def test_identity_argv_port_still_reported_when_env_port_is_same(monkeypatch):
    """Non-regression: boot `python -m scp 8000` với env SCP_PORT=8000 → vẫn
    8000 (reality_4-e-002 contract: configured_port == argv PORT)."""
    monkeypatch.setenv("SCP_PORT", "8000")
    monkeypatch.setattr(sys, "argv", ["/usr/bin/python", "-m", "scp", "8000"])

    identity = api_server._scp_service_identity()

    assert identity["configured_port"] == 8000
