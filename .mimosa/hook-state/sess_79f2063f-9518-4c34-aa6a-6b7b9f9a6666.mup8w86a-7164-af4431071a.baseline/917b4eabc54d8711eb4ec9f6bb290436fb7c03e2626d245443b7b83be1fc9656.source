"""[LIVE-FLOW-PROOF-KEY 2026-09-26] tools/live_flow_proof.py phải in key thật.

Live sweep: tool từng đọc service_identity['version'] — key này KHÔNG tồn tại
(service_identity: service_name/mode/host/configured_port/pid/commit/
config_hash) nên luôn print rỗng. 'version' nằm TOP-LEVEL trong /health
body. Test pin đúng vị trí key mà tool dựa vào.

[SEC-FIX /health-identity 2026-09-26] 'argv' đã bị LOẠI khỏi service_identity:
/health không auth, từng echo toàn bộ command line — bất kỳ secret nào từng
được truyền qua CLI sẽ lộ. Contract mới: argv KHÔNG được xuất hiện lại.
"""
from __future__ import annotations

import asyncio


def _health_payload() -> dict:
    import os

    os.environ.setdefault("SCP_CAPABILITY_SECRET", "test-capability-secret-for-automated-suites-only-32bytes")
    from scp import api_server

    return asyncio.run(api_server.health())


def test_version_is_top_level_in_health_body():
    payload = _health_payload()
    assert payload.get("version"), "/health body phải có version top-level (không rỗng)"


def test_service_identity_has_no_version_key():
    """Pin nguyên nhân gốc: service_identity KHÔNG có 'version' — tool đọc
    nhầm key này từng in chuỗi rỗng."""
    payload = _health_payload()
    assert "version" not in payload["service_identity"]
    identity = payload["service_identity"]
    expected = {"service_name", "mode", "host", "configured_port", "pid", "commit", "config_hash"}
    assert expected.issubset(set(identity.keys()))


def test_service_identity_never_exposes_argv():
    """[SEC-FIX /health-identity 2026-09-26] service_identity KHÔNG được chứa
    'argv': /health là endpoint không auth — raw command line (có thể chứa
    secret truyền qua CLI) tuyệt đối không được phản hồi về client."""
    payload = _health_payload()
    assert "argv" not in payload["service_identity"]


def test_live_flow_proof_source_reads_top_level_version():
    """Chính tool (không phải bản chép tay) phải đọc health['version'] —
    kiểm tra bằng compile + tham chiếu dòng lệnh print thực tế trong source."""
    import importlib.util
    import py_compile
    from pathlib import Path

    tool_path = Path(__file__).resolve().parents[2] / "tools" / "live_flow_proof.py"
    py_compile.compile(str(tool_path), doraise=True)
    spec = importlib.util.spec_from_file_location("scp_live_flow_proof_under_test", tool_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = __import__("inspect").getsource(module.main)
    assert 'health.get("version"' in source, "tool phải đọc version từ /health body top-level"
    assert 'sid.get("version"' not in source, "không được đọc version từ service_identity (key không tồn tại)"
