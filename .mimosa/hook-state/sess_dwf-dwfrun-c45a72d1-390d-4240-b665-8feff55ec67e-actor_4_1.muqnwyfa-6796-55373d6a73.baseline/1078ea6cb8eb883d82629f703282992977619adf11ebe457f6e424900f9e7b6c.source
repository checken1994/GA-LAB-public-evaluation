"""[LOG-NOISE-FIX 2026-09-26] _is_private_ip: hostname KHÔNG phải warning.

Boot warning nhiễu: "Silent except: 'raw.githubusercontent.com' does not
appear to be an IPv4 or IPv6 address" — đây là luồng BÌNH THƯỜNG (hostname
không phải IP literal → rơi xuống DNS resolution), từng bị log WARNING. Fix:
DEBUG với message đúng; phân loại an toàn không đổi.

Không dùng network thật: socket.getaddrinfo được monkeypatch.
"""
from __future__ import annotations

import logging
import socket

from scp.security import url_safety


def test_plain_hostname_logs_no_warning(monkeypatch, caplog):
    def _no_dns(host, port=None, **kwargs):
        raise socket.gaierror("test-isolated: DNS disabled")

    monkeypatch.setattr(url_safety.socket, "getaddrinfo", _no_dns)

    with caplog.at_level(logging.WARNING, logger="scp.security.url_safety"):
        result = url_safety._is_private_ip("raw.githubusercontent.com")

    # Unresolvable → fail-closed như cũ (True = coi như unsafe).
    assert result is True
    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert warnings == [], f"hostname parse là expected path — không được WARNING: {warnings}"


def test_plain_hostname_path_is_visible_at_debug(monkeypatch, caplog):
    """Nhánh hostname vẫn phải quan sát được ở DEBUG (không phải im lặn hẳn)."""
    def _no_dns(host, port=None, **kwargs):
        raise socket.gaierror("test-isolated: DNS disabled")

    monkeypatch.setattr(url_safety.socket, "getaddrinfo", _no_dns)

    with caplog.at_level(logging.DEBUG, logger="scp.security.url_safety"):
        url_safety._is_private_ip("raw.githubusercontent.com")

    debugs = [r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG]
    assert any("not an IP literal" in m for m in debugs)
    assert not any("Silent except" in m for m in debugs)


def test_ip_literal_classification_unchanged(monkeypatch, caplog):
    """Non-regression: IP literal vẫn phân loại đúng, không log warning."""
    with caplog.at_level(logging.WARNING, logger="scp.security.url_safety"):
        assert url_safety._is_private_ip("127.0.0.1") is True
        assert url_safety._is_private_ip("169.254.169.254") is True
        assert url_safety._is_private_ip("8.8.8.8") is False

    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert warnings == []
