#!/usr/bin/env python3
"""Read-only localhost bridge between the SCP API and dashboard.

The bearer token remains in SCP's local secret file and is never returned.
"""
from __future__ import annotations

import json
import time
from threading import Lock
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scp.security.url_safety import safe_urlopen  # [S6b] boundary-validated egress
LISTEN_HOST, LISTEN_PORT = "127.0.0.1", 8765
RATE_LIMIT, WINDOW = 60, 60
REQUESTS: dict[str, deque[float]] = defaultdict(deque)

def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists(): return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values

SCP_ENV = load_env(ROOT / ".env")
BRIDGE_ENV = load_env(ROOT / ".scp-dashboard-bridge.env")

def allowed_origins() -> set[str]:
    raw = BRIDGE_ENV.get("SCP_DASHBOARD_ORIGINS", "https://3000-imd47l5cxjk5hxor72yjq-165646b0.sg1.manus.computer,https://cfworkerinsp-en5efvfy.manus.space,http://localhost:3000,http://127.0.0.1:3000")
    return {value.strip().rstrip("/") for value in raw.split(",") if value.strip()}

def token() -> str:
    raw_path = SCP_ENV.get("SCP_AUTH_TOKEN_SECRET_FILE", "")
    if not raw_path: raise RuntimeError("SCP_AUTH_TOKEN_SECRET_FILE is missing")
    path = Path(raw_path)
    if not path.is_absolute(): path = ROOT / path
    value = path.read_text(encoding="utf-8").strip()
    if not value: raise RuntimeError("SCP token file is empty")
    return value

def read_api(path: str, authenticated: bool) -> tuple[int, object]:
    host, port = SCP_ENV.get("SCP_HOST", "127.0.0.1"), SCP_ENV.get("SCP_PORT", "8000")
    headers = {"Accept": "application/json"}
    if authenticated: headers["Authorization"] = f"Bearer {token()}"
    try:
        with safe_urlopen(Request(f"http://{host}:{port}{path}", headers=headers), timeout=5, allow_internal=True) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except HTTPError as error:
        try: return error.code, json.loads(error.read().decode("utf-8"))
        except Exception: return error.code, {"detail": f"HTTP {error.code}"}
    except URLError as error:
        raise RuntimeError(f"Cannot reach SCP API: {error.reason}") from error

def limited(client: str) -> bool:
    now, items = time.monotonic(), REQUESTS[client]
    while items and now - items[0] > WINDOW: items.popleft()
    if len(items) >= RATE_LIMIT: return True
    items.append(now)
    return False

def activity_payload() -> dict:
    code, runtime = read_api("/v100/status", True)
    data = runtime if isinstance(runtime, dict) else {}
    events = []
    try:
        lines = (ROOT / "data" / "pc_controller" / "audit.jsonl").read_text(encoding="utf-8", errors="replace").splitlines()[-12:]
        for index, raw in enumerate(lines):
            try: item = json.loads(raw)
            except json.JSONDecodeError: continue
            occurred = str(item.get("iso") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(item.get("timestamp", time.time())))))
            event = str(item.get("event") or "AUDIT_EVENT")[:64]
            decision = str(item.get("decision") or "")[:120]
            events.append({"id": f"{occurred}|{index}|{event}", "occurredAt": occurred, "event": event, "decision": decision})
    except Exception: pass
    return {"runStatus": str(data.get("run_status") or ("UNAVAILABLE" if code >= 400 else "UNKNOWN")), "ledgerStatus": str(data.get("ledger_status") or ("UNAVAILABLE" if code >= 400 else "UNKNOWN")), "auditEvents": events}
def build_live_payload() -> dict:
    health_code, health = read_api("/health", False)
    status_code, status = read_api("/v98/status", True)
    state = "online" if health_code < 400 and status_code < 400 else "degraded" if health_code < 400 else "offline"
    safe_status = status if status_code < 400 and isinstance(status, dict) else {"available": False, "httpStatus": status_code}
    if state == "online":
        error = None
    elif status_code == 401:
        error = "V98 rejected the configured file credential. The SCP runtime is using a different token or must be restarted with its current auth configuration."
    else:
        error = "SCP returned a non-success status."
    return {
        "activity": activity_payload(),"state": state, "health": health if isinstance(health, dict) else {"value": health}, "status": safe_status, "healthStatus": health_code, "statusStatus": status_code, "checkedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "error": error}

SNAPSHOT_LOCK = Lock()
SNAPSHOT_VALUE: dict | None = None
SNAPSHOT_AT = 0.0

def cached_live_payload() -> dict:
    global SNAPSHOT_VALUE, SNAPSHOT_AT
    with SNAPSHOT_LOCK:
        now = time.monotonic()
        if SNAPSHOT_VALUE is not None and now - SNAPSHOT_AT < 8:
            return SNAPSHOT_VALUE
        SNAPSHOT_VALUE = build_live_payload()
        SNAPSHOT_AT = now
        return SNAPSHOT_VALUE

class Handler(BaseHTTPRequestHandler):
    def log_message(self, _fmt: str, *_args: object) -> None: return
    def json(self, status: int, body: dict, origin: str | None) -> None:
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store"); self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS"); self.send_header("Access-Control-Allow-Headers", "Content-Type"); self.send_header("Vary", "Origin")
        if origin and origin.rstrip("/") in allowed_origins(): self.send_header("Access-Control-Allow-Origin", origin)
        self.end_headers(); self.wfile.write(data)
    def allowed(self, origin: str | None) -> bool: return bool(origin and origin.rstrip("/") in allowed_origins())
    def do_OPTIONS(self) -> None:
        origin = self.headers.get("Origin")
        self.json(204 if self.allowed(origin) else 403, {} if self.allowed(origin) else {"error": "origin_not_allowed"}, origin)
    def do_GET(self) -> None:
        origin = self.headers.get("Origin")
        if not self.allowed(origin): self.json(403, {"error": "origin_not_allowed"}, origin); return
        if self.path != "/live": self.json(404, {"error": "not_found"}, origin); return
        if limited(self.client_address[0]): self.json(429, {"error": "rate_limited"}, origin); return
        try:
            self.json(200, cached_live_payload(), origin)
        except Exception as error:
            self.json(200, {"state": "offline", "health": {}, "status": {}, "checkedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "error": str(error)}, origin)

if __name__ == "__main__":
    print(f"SCP Dashboard Bridge listening on http://{LISTEN_HOST}:{LISTEN_PORT}")
    ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler).serve_forever()




