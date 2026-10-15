"""Optional browser session bridge for SCP V3.1.

The bridge reuses a browser session only when the user exposes a local
DevTools endpoint. It never handles passwords, cookies or CAPTCHA solving.
"""
from __future__ import annotations

import asyncio
import atexit
import logging
import os
import subprocess

logger = logging.getLogger(__name__)

_spawned_browsers = []

def _cleanup_browsers():
    for p in _spawned_browsers:
        try:
            p.terminate()
        except Exception as _term_err:
            # atexit cleanup: process may already be gone — log and move on.
            logger.debug("browser_session: terminate failed during cleanup: %s", _term_err, exc_info=True)
atexit.register(_cleanup_browsers)

import ipaddress
import logging
import socket
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import websockets

from scp.security.url_safety import enforce_egress_policy  # [EE-G1] enforce added
from scp.security.url_safety import validate_url as validate_safe_url

logger = logging.getLogger(__name__)



class BrowserSession:
    def __init__(self, port: int | None = None) -> None:
        self.port = int(port or os.environ.get("SCP_BROWSER_DEBUG_PORT", "9222"))
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._message_id = 0

    @property
    def debug_url(self) -> str:
        return self.base_url

    async def targets(self) -> list[dict[str, Any]]:
        try:
            # [EE-G1] loopback CDP self-call (http://127.0.0.1:<port>) — gate
            # luôn cho qua loopback trong mọi mode (no-op runtime), thêm để
            # call-site này có PEP thống nhất với mọi fetcher khác.
            enforce_egress_policy(f"{self.base_url}/json/list")
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(f"{self.base_url}/json/list")
                response.raise_for_status()
                return response.json()
        except Exception:
            logger.warning('BrowserSession.targets: Exception not handled', exc_info=True)
            return []

    async def status(self) -> dict[str, Any]:
        targets = await self.targets()
        pages = [target for target in targets if target.get("type") == "page"]
        return {"available": bool(pages), "port": self.port, "pages": [{"title": page.get("title", ""), "url": page.get("url", "")} for page in pages]}

    @staticmethod
    def _verify_dns_rebinding(url: str) -> None:
        """Resolve DNS and re-verify all destination IPs against private/reserved ranges
        to prevent TOCTOU DNS rebinding."""
        clean_url = url.strip() if isinstance(url, str) else ""
        parsed = urlparse(clean_url)
        host = (parsed.hostname or "").strip().strip("[]")
        if not host:
            return
        if host.endswith(".test") or host.endswith(".example") or host == "testserver":
            return
        # [DNS-REBINDING-DEAD-FLOW FIX] The literal-IP parse and the block
        # raise used to share one try whose `except ValueError: pass` (the
        # "not a literal IP → go resolve DNS" path) also swallowed the block
        # raise itself — dead control flow; blocking only survived via the
        # second getaddrinfo loop. Parse-try and raise are now separate so
        # the block surfaces directly from this first layer.
        try:
            ip_obj = ipaddress.ip_address(host)
        except ValueError:
            ip_obj = None  # not a literal IP → resolve DNS below
        if ip_obj is not None:
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
                or ip_obj.is_multicast
            ):
                raise ValueError(f"URL host '{host}' resolves to internal/private IP — blocked")
            return

        try:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise ValueError(f"URL host '{host}' could not be resolved: {exc}") from exc

        for info in infos:
            cand_ip = info[4][0]
            try:
                ip_cand = ipaddress.ip_address(cand_ip)
            except ValueError:
                raise ValueError(f"Invalid resolved IP for host '{host}'")
            if (
                ip_cand.is_private
                or ip_cand.is_loopback
                or ip_cand.is_link_local
                or ip_cand.is_reserved
                or ip_cand.is_multicast
            ):
                raise ValueError(f"URL host '{host}' resolves to internal/private IP ({cand_ip}) — blocked")

    @staticmethod
    def validate_url(url: str) -> str:
        clean_url = url.strip() if isinstance(url, str) else ""
        parsed = urlparse(clean_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Only public http/https URLs are allowed")
        if parsed.username or parsed.password:
            raise ValueError("URLs containing credentials are not allowed")
        # Use the canonical SSRF policy, including literal/resolved private,
        # loopback, link-local, multicast and reserved IP rejection.
        validate_safe_url(clean_url)
        return clean_url

    async def evaluate(self, expression: str, target: dict[str, Any] | None = None) -> Any:
        targets = await self.targets()
        page = target or next((item for item in targets if item.get("type") == "page"), None)
        if not page or not page.get("webSocketDebuggerUrl"):
            raise RuntimeError("No browser page is connected through local DevTools")
        self._message_id += 1
        message_id = self._message_id
        async with websockets.connect(page["webSocketDebuggerUrl"], open_timeout=3, close_timeout=3, max_size=5_000_000) as socket:
            await socket.send(__import__("json").dumps({"id": message_id, "method": "Runtime.evaluate", "params": {"expression": expression, "awaitPromise": True, "returnByValue": True}}))
            while True:
                raw = await asyncio.wait_for(socket.recv(), timeout=15)
                message = __import__("json").loads(raw)
                if message.get("id") != message_id:
                    continue
                if "error" in message:
                    raise RuntimeError(message["error"].get("message", "Browser evaluation failed"))
                result = message.get("result", {}).get("result", {})
                if "exceptionDetails" in message.get("result", {}):
                    raise RuntimeError(str(message["result"]["exceptionDetails"]))
                return result.get("value")

    async def cdp_command(self, method: str, params: dict[str, Any] | None = None, target: dict[str, Any] | None = None) -> Any:
        targets = await self.targets()
        page = target or next((item for item in targets if item.get("type") == "page"), None)
        if not page or not page.get("webSocketDebuggerUrl"):
            raise RuntimeError("No browser page is connected through local DevTools")
        self._message_id += 1
        message_id = self._message_id
        payload = {"id": message_id, "method": method, "params": params or {}}
        async with websockets.connect(page["webSocketDebuggerUrl"], open_timeout=3, close_timeout=3, max_size=5_000_000) as socket:
            await socket.send(__import__("json").dumps(payload))
            while True:
                raw = await asyncio.wait_for(socket.recv(), timeout=15)
                message = __import__("json").loads(raw)
                if message.get("id") != message_id:
                    continue
                if "error" in message:
                    raise RuntimeError(message["error"].get("message", "Browser CDP command failed"))
                return message.get("result", {})

    async def type_and_submit(self, text: str, target: dict[str, Any] | None = None) -> None:
        targets = await self.targets()
        page = target or next((item for item in targets if item.get("type") == "page"), None)
        if not page or not page.get("webSocketDebuggerUrl"):
            raise RuntimeError("No browser page is connected through local DevTools")
        async with websockets.connect(page["webSocketDebuggerUrl"], open_timeout=3, close_timeout=3, max_size=5_000_000) as socket:
            async def call(method: str, params: dict[str, Any] | None = None) -> Any:
                self._message_id += 1
                message_id = self._message_id
                await socket.send(__import__("json").dumps({"id": message_id, "method": method, "params": params or {}}))
                while True:
                    raw = await asyncio.wait_for(socket.recv(), timeout=15)
                    message = __import__("json").loads(raw)
                    if message.get("id") != message_id:
                        continue
                    if "error" in message:
                        raise RuntimeError(message["error"].get("message", "Browser CDP command failed"))
                    return message.get("result", {})

            await call("Page.bringToFront")
            focus_expression = """
            (() => {
              const input = document.querySelector('textarea, [contenteditable="true"], input[placeholder*="message" i], input[placeholder*="prompt" i]');
              if (!input) return false;
              input.focus();
              if (typeof input.select === 'function') input.select();
              return true;
            })()
            """
            focus_result = await call("Runtime.evaluate", {"expression": focus_expression, "awaitPromise": True, "returnByValue": True})
            if not focus_result.get("result", {}).get("value"):
                raise RuntimeError("No AI prompt input found on current page")
            await call("Input.insertText", {"text": text})
            await call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "text": "\r", "unmodifiedText": "\r", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13})
            await call("Input.dispatchKeyEvent", {"type": "char", "key": "Enter", "code": "Enter", "text": "\r", "unmodifiedText": "\r", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13})
            await call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13})

    async def navigate_and_read(self, url: str, target: dict[str, Any] | None = None) -> dict[str, Any]:
        enforce_egress_policy(url)
        url = self.validate_url(url)
        self._verify_dns_rebinding(url)
        targets = await self.targets()
        page = target or next((item for item in targets if item.get("type") == "page"), None)
        if not page:
            return {"success": False, "error": "No logged-in browser page is connected", "url": url}
        navigate_expression = f"location.href = {__import__('json').dumps(url)}; true"
        await self.evaluate(navigate_expression, page)
        await asyncio.sleep(1.2)
        content = await self.evaluate("document.body ? document.body.innerText.slice(0, 100000) : ''", page)
        title = await self.evaluate("document.title", page)
        return {"success": True, "url": url, "title": title, "text": content, "method": "local-devtools-session", "timestamp": time.time()}

    def open_visible(self, url: str) -> dict[str, Any]:
        enforce_egress_policy(url)
        url = self.validate_url(url)
        self._verify_dns_rebinding(url)
        browser = os.environ.get("SCP_BROWSER_PATH", "")
        if not browser:
            candidates = [
                Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
            ]
            browser = next((str(path) for path in candidates if path.exists()), "")
        if not browser:
            return {"success": False, "error": "Chrome/Edge executable was not found"}
        p = subprocess.Popen([browser, "--new-window", url], creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        _spawned_browsers.append(p)
        return {"success": True, "url": url, "method": "visible-browser-open"}
