"""Outbound-only bridge: polls public relay and calls local SCP on loopback."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scp.security.url_safety import safe_urlopen

PUBLIC = os.environ["SCP_PUBLIC_URL"].rstrip("/") + "/api/trpc"
AGENT = os.environ["SCP_AGENT_ID"]
TOKEN = os.environ["SCP_RELAY_TOKEN"]
LOCAL = os.environ.get("SCP_LOCAL_URL", "http://127.0.0.1:3000").rstrip("/")
ASK_PATH = os.environ.get("SCP_LOCAL_ASK_PATH", "/api/scp/ask")
AUTH_TOKEN_FILE = os.environ.get("SCP_LOCAL_AUTH_TOKEN_FILE", "").strip()
POLL_SECONDS = max(2, int(os.environ.get("SCP_BRIDGE_POLL_SECONDS", "5")))
LOCAL_TIMEOUT_SECONDS = max(10, min(110, int(os.environ.get("SCP_BRIDGE_LOCAL_TIMEOUT_SECONDS", "110"))))
LOG_PATH = Path(os.environ.get("SCP_BRIDGE_LOG", "scp-public-bridge.log"))


def log(event: str, **detail: Any) -> None:
    """Store only bounded operational facts; never token, address or answer."""
    row = {"ts_utc": datetime.now(timezone.utc).isoformat(), "event": event, **detail}
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass


def rpc(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        PUBLIC + "/scp.agent." + path,
        data=json.dumps({"json": payload}).encode("utf-8"),
        headers={"content-type": "application/json"},
    )
    # [SEC-S6] SSRF guard: outbound relay call goes through safe_urlopen
    # (scheme allowlist + private-IP block) instead of raw urlopen.
    with safe_urlopen(request, timeout=30) as response:
        value = json.loads(response.read())
    return value if isinstance(value, dict) else {}


def trpc_result(response: dict[str, Any]) -> Any:
    return response.get("result", {}).get("data", {}).get("json")


def service_status() -> dict[str, str]:
    targets = {
        "dashboard": "http://127.0.0.1:3000/",
        "scheduler": "http://127.0.0.1:3030/healthz",
        "backend": "http://127.0.0.1:8000/health",
        "ollama": "http://127.0.0.1:11434/api/tags",
    }
    result: dict[str, str] = {}
    for name, url in targets.items():
        try:
            # [SEC-S6] Loopback health probes are intentional internal targets.
            with safe_urlopen(url, timeout=3, allow_internal=True) as response:
                result[name] = "healthy" if response.status < 500 else "unreachable"
        except (urllib.error.URLError, TimeoutError, ValueError):
            result[name] = "unreachable"
    return result


def call_local(job: dict[str, Any]) -> dict[str, Any]:
    if job.get("action") != "ask":
        raise RuntimeError("action_not_allowed")
    payload = job.get("requestPayload")
    if not isinstance(payload, dict) or not isinstance(payload.get("question"), str):
        raise RuntimeError("invalid_ask_payload")
    headers = {"content-type": "application/json"}
    if AUTH_TOKEN_FILE:
        token = Path(AUTH_TOKEN_FILE).read_text(encoding="utf-8").strip()
        if not token:
            raise RuntimeError("local_auth_token_empty")
        headers["authorization"] = "Bearer " + token
    request = urllib.request.Request(
        LOCAL + ASK_PATH,
        data=json.dumps({"question": payload["question"], "domain": "general", "session_id": "public-" + str(job["id"]), "conversation_history": []}).encode("utf-8"),
        headers=headers,
    )
    # [SEC-S6] LOCAL targets the loopback ask endpoint by design.
    with safe_urlopen(request, timeout=LOCAL_TIMEOUT_SECONDS, allow_internal=True) as response:
        value = json.loads(response.read())
    if not isinstance(value, dict):
        raise RuntimeError("invalid_local_response")
    return value


def run() -> None:
    last_error: str | None = None
    log("BRIDGE_STARTED", agent_id=AGENT)
    while True:
        try:
            services = service_status()
            all_healthy = all(value == "healthy" for value in services.values())
            # Heartbeat reports health; the only remotely executable action is Ask.
            # Do not advertise actions that the local allowlist rejects.
            rpc("heartbeat", {"agentId": AGENT, "token": TOKEN, "status": "online" if all_healthy and last_error is None else "degraded", "capabilities": ["ask"], "serviceStatus": services, "lastError": last_error})
            job = trpc_result(rpc("claim", {"agentId": AGENT, "token": TOKEN}))
            if isinstance(job, dict) and job.get("id"):
                log("JOB_CLAIMED", job_id=str(job["id"]), action=str(job.get("action")))
                try:
                    result = call_local(job)
                    rpc("complete", {"agentId": AGENT, "token": TOKEN, "jobId": job["id"], "result": result, "failed": False})
                    log("JOB_COMPLETED", job_id=str(job["id"]), result_keys=sorted(result.keys())[:8])
                    last_error = None
                except Exception as exc:
                    rpc("complete", {"agentId": AGENT, "token": TOKEN, "jobId": job["id"], "result": {"error": "local execution failed", "error_class": type(exc).__name__}, "failed": True})
                    log("JOB_FAILED", job_id=str(job["id"]), error_class=type(exc).__name__)
                    last_error = "local execution failed"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, KeyError) as exc:
            last_error = "bridge transport error"
            log("BRIDGE_DEGRADED", error_class=type(exc).__name__)
        except Exception as exc:
            last_error = "bridge internal error"
            log("BRIDGE_DEGRADED", error_class=type(exc).__name__)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run()
