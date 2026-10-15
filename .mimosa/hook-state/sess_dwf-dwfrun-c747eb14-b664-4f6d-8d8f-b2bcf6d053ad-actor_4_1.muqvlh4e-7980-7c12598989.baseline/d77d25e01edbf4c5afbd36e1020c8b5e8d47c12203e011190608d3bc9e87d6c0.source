"""[SEC-FIX no-secret-oracle 2026-09-26] AuthConfig phải KHÔNG có bề mặt oracle.

FA-09 provenance: probe (AST sweep + offline guess check) xác nhận TRƯỚC fix:
  - `AuthConfig.config_digest` = sha256 trên chuỗi token|password|sources RAW —
    người thấy digest có thể brute-force token OFFLINE, không cần chạm hệ thống
    (probe: guess-check trả True).
  - `AuthConfig.diagnostics()` trả config_digest nhưng có 0 callers trong toàn
    repo (AST sweep) — bề mặt chết, rủi ro thuần túy.

Contract sau fix: config_digest/diagnostics KHÔNG tồn tại; load_auth_config()
vẫn trả đúng token/password/source (hành vi verify_admin phụ thuộc giữ nguyên).
"""
from __future__ import annotations

from scp.security.auth_config import AuthConfig, load_auth_config


def test_auth_config_has_no_digest_or_diagnostics_surface():
    config = AuthConfig(token="t", password="p", token_source="env", password_source="env")
    assert not hasattr(config, "config_digest"), (
        "config_digest là offline brute-force oracle trên secret raw — không được tồn tại"
    )
    assert not hasattr(config, "diagnostics"), (
        "diagnostics() từng expose config_digest — không được tồn tại"
    )


def test_load_auth_config_behavior_preserved(monkeypatch):
    """Contract pin: cấu hình nguồn env vẫn load đúng (không phá verify_admin)."""
    monkeypatch.setenv("SCP_AUTH_TOKEN_SECRET", "tok-abc")
    monkeypatch.delenv("SCP_AUTH_TOKEN_SECRET_FILE", raising=False)
    monkeypatch.setenv("SCP_AUTH_PASSWORD", "pw-xyz")
    monkeypatch.delenv("SCP_AUTH_PASSWORD_FILE", raising=False)
    config = load_auth_config()
    assert config.token == "tok-abc"
    assert config.password == "pw-xyz"
    assert config.token_source == "env"
    assert config.password_source == "env"
    assert config.configured is True
    # Bề mặt diagnostics phải expose nguồn, KHÔNG expose giá trị/digest của secret.
    assert not hasattr(config, "config_digest")


def test_no_hashlib_oracle_in_auth_config_source():
    """Guard chống hồi quy của oracle: module không được import hashlib và
    không được định nghĩa lại member nào tên config_digest/diagnostics
    (kiểm tra AST — không đếm chữ trong comment/docstring)."""
    import ast
    import inspect

    from scp.security import auth_config

    tree = ast.parse(inspect.getsource(auth_config))
    imported_modules = set()
    defined_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined_names.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            defined_names.add(node.id)
    assert "hashlib" not in imported_modules, (
        "hashlib trong auth_config chỉ từng dùng cho oracle — không được nhập lại"
    )
    assert not ({"config_digest", "diagnostics"} & defined_names)
