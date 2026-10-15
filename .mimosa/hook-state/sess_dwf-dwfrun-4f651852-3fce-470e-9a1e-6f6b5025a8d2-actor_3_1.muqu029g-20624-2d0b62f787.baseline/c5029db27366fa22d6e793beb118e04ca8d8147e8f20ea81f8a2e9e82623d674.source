"""[AUDIT-FIX low-2 + low-3] Reality smoke — mini-services/llm-bridge auth +
recursion-guard header (bun runtime thật, KHÔNG phải static check).

Root cause:
  * low-2: /api/cache/stats và /api/cache/clear KHÔNG có auth trong khi
    /api/chat yêu cầu Bearer (probe: POST /api/cache/clear unauth → 200
    {"cleared":true}).
  * low-3: X-LLM-Bridge-Internal được CHECK ở handleChat nhưng không bao giờ
    được SET (0 setter) — guard chết; comment claiming block self-call là sai.
Fix:
  * isAuthorized() single-source; cache endpoints cùng gate 401.
  * callProviderDirect() SET header trên mọi outbound request → một self-call
    thật bị 503-block ở hop đầu.

Chạy: python -m pytest tests/T02_contract/test_llm_bridge_cache_auth.py -q
Yêu cầu: bun trên PATH (runtime thật). Không cần key thật — OpenRouter trỏ
tới dead port, Groq trỏ tới capture server nội bộ (đã allowlist egress).
"""
import json
import os
import secrets
import socket
import subprocess
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from scp.security.url_safety import safe_urlopen

ROOT = Path(__file__).resolve().parents[2]
BRIDGE_DIR = ROOT / "mini-services" / "llm-bridge"
# Runtime-generated canary: exercises the real Bearer gate without embedding
# any credential-shaped literal (GitHub push protection / secret scanning).
SECRET = "smoke-" + secrets.token_hex(16)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _reachable(url: str) -> bool:
    """Raw reachability probe — KHÔNG parse JSON (/health trả HTML)."""
    try:
        with safe_urlopen(urllib.request.Request(url), timeout=5, allow_internal=True) as resp:
            return resp.status == 200
    except Exception:
        return False


def _request(method: str, url: str, token: str | None = None, extra_headers: dict | None = None,
             payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, method=method, data=data)
    if token is not None:
        req.add_header("Authorization", f"Bearer {token}")
    for k, v in (extra_headers or {}).items():
        req.add_header(k, v)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        # Loopback-only test transport through the repo SSRF choke point
        # ([AUDIT-FIX] scanner-flagged raw urlopen on a dynamic URL).
        with safe_urlopen(req, timeout=10, allow_internal=True) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode() or "{}"
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"raw": body}


class _CaptureHandler(BaseHTTPRequestHandler):
    """Ghi lại headers nhận được; trả 503 như guard của chính bridge."""

    seen_headers: dict = {}

    def do_POST(self):
        _CaptureHandler.seen_headers = dict(self.headers)
        body = json.dumps({"error": "self-call blocked (recursion guard)"}).encode()
        self.send_response(503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # im lặng
        pass


@pytest.fixture(scope="module")
def capture_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CaptureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()


@pytest.fixture(scope="module")
def bridge(capture_server):
    bun = "bun"
    port = _free_port()
    env = dict(os.environ)
    env.update({
        "SCP_LLM_BRIDGE_PORT": str(port),
        "ZAI_BRIDGE_HOST": "127.0.0.1",
        "SHARED_SECRET": SECRET,
        # Dummy provider keys are runtime-generated canaries (never literals).
        "OPENROUTER_API_KEY": "dummy-" + secrets.token_hex(8),
        # OpenRouter trỏ dead port → fail nhanh, buộc rơi xuống fallback groq.
        "OPENROUTER_BASE_URL": "http://127.0.0.1:1",
        # Groq fallback trỏ tới capture server (loopback phải allowlist egress).
        "GROQ_BASE_URL": f"http://127.0.0.1:{capture_server.server_address[1]}",
        "GROQ_API_KEY": "dummy-" + secrets.token_hex(8),
        "LLM_EGRESS_ALLOWED_HOSTS": "127.0.0.1",
    })
    proc = subprocess.Popen(
        [bun, "index.ts"], cwd=str(BRIDGE_DIR), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = __import__("time").time() + 30
    ready = False
    while __import__("time").time() < deadline:
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"bridge exited early:\n{out}")
        if _reachable(f"{base}/health"):
            ready = True
            break
        __import__("time").sleep(0.3)
    if not ready:
        proc.kill()
        raise RuntimeError("bridge không lắng nghe trong 30s")
    yield base
    proc.kill()
    proc.wait(timeout=10)


# ---------------------------------------------------------------------------
# [AUDIT-FIX low-2] /api/cache/* phải 401 khi không có Bearer
# ---------------------------------------------------------------------------
def test_cache_stats_unauth_is_401(bridge):
    status, _ = _request("GET", f"{bridge}/api/cache/stats")
    assert status == 401, f"unauth /api/cache/stats → {status} (fail-open!)"


def test_cache_clear_unauth_is_401(bridge):
    status, _ = _request("POST", f"{bridge}/api/cache/clear")
    assert status == 401, f"unauth /api/cache/clear → {status} (fail-open!)"


def test_chat_unauth_is_401_unchanged(bridge):
    status, _ = _request("POST", f"{bridge}/api/chat", payload={"messages": []})
    assert status == 401  # hành vi cũ của /api/chat phải giữ nguyên


def test_cache_endpoints_work_with_valid_bearer(bridge):
    status, body = _request("GET", f"{bridge}/api/cache/stats", token=SECRET)
    assert status == 200
    assert "cache_size" in body and "keys_available" in body
    status, body = _request("POST", f"{bridge}/api/cache/clear", token=SECRET)
    assert status == 200
    assert body.get("cleared") is True


def test_wrong_bearer_is_401(bridge):
    status, _ = _request("GET", f"{bridge}/api/cache/stats", token="wrong-secret")
    assert status == 401


# ---------------------------------------------------------------------------
# [AUDIT-FIX low-3] header tự nhận diện phải được SET và guard 503 thật
# ---------------------------------------------------------------------------
def test_chat_with_internal_header_is_503_blocked(bridge):
    """Self-call shape: request mang X-LLM-Bridge-Internal: 1 → guard 503."""
    status, body = _request(
        "POST", f"{bridge}/api/chat", token=SECRET,
        extra_headers={"X-LLM-Bridge-Internal": "1"},
        payload={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert status == 503, f"self-call shape phải bị 503-block, nhận {status}"
    assert "self-call blocked" in body.get("error", "")


def test_outbound_provider_request_carries_internal_header(bridge):
    """callProviderDirect phải SET X-LLM-Bridge-Internal trên outbound request:
    authed /api/chat → OpenRouter dead → groq fallback → capture server thấy
    header và trả 503 (mô phỏng đúng guard của bridge khi self-call)."""
    _CaptureHandler.seen_headers = {}
    status, _ = _request(
        "POST", f"{bridge}/api/chat", token=SECRET,
        payload={"messages": [{"role": "user", "content": "hi"}], "stream": False},
    )
    seen = _CaptureHandler.seen_headers
    assert seen, "outbound request không tới capture server"
    assert seen.get("X-LLM-Bridge-Internal") == "1", (
        f"callProviderDirect KHÔNG set header tự nhận diện: {seen}"
    )
    assert status == 502  # mọi provider fail (capture trả 503) → 502 cho client
