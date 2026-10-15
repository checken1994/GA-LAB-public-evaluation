"""
SCP V102 — UserNotificationSystem
==================================
Báo cáo user real-time khi có sự kiện quan trọng.

Channels:
  1. Dashboard (real-time WebSocket push)
  2. Webhook (Slack/Discord/Telegram/configurable)
  3. Email (SMTP)
  4. File log (user_reports.jsonl — always)

User configures which channels via config.yaml.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scp.security.url_safety import enforce_egress_policy  # [EE-G1]

# [ROOT-FIX Task 38-A / Issue 3] DNA #5 UNKNOWN > wrong answer: SEVERITY_ORDER
# was missing "high", "medium", "low" — these fell back to 0 (treated as
# "info") via SEVERITY_ORDER.get(severity, 0). Concrete impact: a "high"
# severity event from governance was compared against min_severity="warning"
# (which has order=1) and SKIPPED because 0 < 1. Now import from
# scp.meta.severity (single source of truth, Issue 1 fix) and include ALL
# severity levels. Backward-compatible fallback if severity.py unavailable.
try:
    from scp.meta.severity import Severity

    _SEVERITY_ORDER_RESOLVED = {
        Severity.INFO: 0,
        Severity.LOW: 1,
        Severity.MEDIUM: 2,
        Severity.WARNING: 3,
        Severity.HIGH: 4,
        Severity.CRITICAL: 5,
    }
except ImportError:  # pragma: no cover — fallback if severity.py unreachable
    # silent-by-design: documented fallback — built-in severity map replaces the optional severity module
    _SEVERITY_ORDER_RESOLVED = {
        "info": 0, "low": 1, "medium": 2,
        "warning": 3, "high": 4, "critical": 5,
    }

logger = logging.getLogger("scp.runtime.notifications")


@dataclass
class NotificationConfig:
    """User notification configuration."""
    # Webhook (Slack/Discord/Telegram)
    webhook_url: str = ""
    webhook_enabled: bool = False

    # Email
    email_enabled: bool = False
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_from: str = ""
    email_to: str = ""

    # Dashboard (always enabled if API server running)
    dashboard_enabled: bool = True

    # Severity threshold — only notify for >= this level
    min_severity: str = "warning"  # info|warning|critical

    # Rate limit — max notifications per hour
    max_per_hour: int = 50


class UserNotificationSystem:
    """Send real-time notifications to user via multiple channels.

    Naming convention: <Purpose>System (world standard).
    """

    # [ROOT-FIX Task 38-A / Issue 3] Was: {"info": 0, "warning": 1, "critical": 2}
    # Bug: "high"/"medium"/"low" fell back to 0 (treated as "info") →
    # high-severity events SKIPPED when min_severity="warning".
    # Fix: full ordered ladder 0..5, sourced from scp.meta.severity (Issue 1).
    # Severity is `str, Enum` so dict lookup with plain string "high" works
    # via hash-of-string (Severity.HIGH == "high" and hash matches).
    SEVERITY_ORDER = _SEVERITY_ORDER_RESOLVED

    def __init__(self, config: NotificationConfig = None, data_dir: str = "data"):
        self.config = config or NotificationConfig()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._notifications_file = self.data_dir / "notifications.jsonl"
        # [SCP-DNA-FIX R9-7 / SA-R9-2 / SA-R9-3] Two bugs:
        # (1) Thread-safety: notify() (called from judge.judge() worker
        #     threads) appends to _recent while _attack_mode_monitor
        #     (daemon thread) and admin endpoints (event loop thread)
        #     iterate it — R8-1's fix replaced a dead SQLite query with
        #     direct list iteration WITHOUT a lock → RuntimeError: list
        #     changed size during iteration swallowed by `except: logger.debug`
        #     → attack-mode monitor silently dies (the exact failure R8-1
        #     was supposed to fix). Mirror R8-6's lock pattern.
        # (2) Unbounded growth: notify() appended without trim → ~6.3 GB RAM
        #     after 1 year at 1 notif/sec. Switch to deque(maxlen=1000)
        #     (auto-evict oldest — O(1), no lock needed for trim).
        self._recent: deque[dict[str, Any]] = deque(maxlen=1000)
        self._recent_lock = threading.Lock()
        self._hourly_count = 0
        self._hour_start = time.time()
        self._stats = {
            "total_sent": 0,
            "total_dashboard": 0,
            "total_webhook": 0,
            "total_email": 0,
            "total_rate_limited": 0,
        }

    def notify(
        self,
        event_type: str = "governance_event",
        severity: str = "warning",
        title: str = "",
        message: str = "",
        details: dict[str, Any] | None = None,
        actions_taken: list[str] | None = None,
    ) -> dict[str, Any]:
        """Send notification to all configured channels.

        Args:
            event_type: attack_blocked|bypass_detected|false_positive|slow_query|daily_summary|governance_event|governance_kill|bypass_detected|canary_triggered
            severity: info|warning|critical
            title: Short title
            message: Detailed message
            details: Additional data
            actions_taken: What SCP did automatically

        Returns:
            Dict with delivery status per channel

         TẠI SAO: `event_type` and `severity` had no defaults, but all
        3 call sites in judge.py (KILL, bypass, canary) omit `event_type` and rely
        on kwargs for the rest → TypeError: missing 1 required positional argument
        → swallowed by `except Exception as e: pass` → Bug CV was cosmetically "fixed"
        (calls exist) but functionally DEAD. Giving defaults makes the existing
        calls work immediately; judge.py call sites will additionally be updated
        to pass explicit event_type values for proper routing/analytics.
        """
        # [P1-7] Backward-compat: older callers used positional (severity, title, message).
        # If the first positional arg looks like a severity level, treat it as such.
        if event_type in ("info", "warning", "critical") and severity not in ("info", "warning", "critical"):
            # caller did notify("warning", "title", "message") — shift args
            event_type, severity, title, message = "governance_event", event_type, severity, title or message, ""
        # Check severity threshold
        if self.SEVERITY_ORDER.get(severity, 0) < self.SEVERITY_ORDER.get(self.config.min_severity, 0):
            return {"skipped": True, "reason": "below_severity_threshold"}

        # Rate limit
        now = time.time()
        if now - self._hour_start > 3600:
            self._hour_start = now
            self._hourly_count = 0
        if self._hourly_count >= self.config.max_per_hour:
            self._stats["total_rate_limited"] += 1
            return {"skipped": True, "reason": "rate_limited"}
        self._hourly_count += 1

        notification = {
            "id": f"notif_{int(now*1000)}",
            "timestamp": now,
            "event_type": event_type,
            "severity": severity,
            "title": title,
            "message": message,
            "details": details or {},
            "actions_taken": actions_taken or [],
        }

        delivery = {"notification_id": notification["id"]}

        # 1. Always save to file
        self._save_to_file(notification)
        delivery["file"] = True

        # 2. Dashboard (real-time)
        if self.config.dashboard_enabled:
            # [SCP-DNA-FIX R9-7] Guard mutation with _recent_lock — concurrent
            # readers (_attack_mode_monitor daemon thread, admin endpoints)
            # may iterate/snapshot while we append. deque.append is atomic
            # in CPython, but the snapshot+iterate sequence in callers is NOT.
            with self._recent_lock:
                self._recent.append(notification)
            self._stats["total_dashboard"] += 1
            delivery["dashboard"] = True

        # 3. Webhook (Slack/Discord/Telegram)
        if self.config.webhook_enabled and self.config.webhook_url:
            success = self._send_webhook(notification)
            delivery["webhook"] = success
            if success:
                self._stats["total_webhook"] += 1

        # 4. Email
        if self.config.email_enabled:
            success = self._send_email(notification)
            delivery["email"] = success
            if success:
                self._stats["total_email"] += 1

        self._stats["total_sent"] += 1
        return delivery

    def _save_to_file(self, notification: dict[str, Any]):
        """Save to JSONL file."""
        try:
            with open(self._notifications_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(notification, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug(f"[Notifications] File save error: {e}", exc_info=True)

    def _send_webhook(self, notification: dict[str, Any]) -> bool:
        """Send to webhook (Slack/Discord/Telegram)."""
        try:
            import httpx
            # Format for Slack/Discord
            severity_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
            payload = {
                "text": f"{severity_emoji.get(notification['severity'], '📌')} {notification['title']}\n{notification['message']}",
                "username": "SCP V102",
            }
            # For Telegram
            if "telegram" in self.config.webhook_url:
                payload = {
                    "chat_id": "",
                    "text": f"{severity_emoji.get(notification['severity'], '📌')} *{notification['title']}*\n{notification['message']}",
                    "parse_mode": "Markdown",
                }

            import asyncio
            async def _send():
                # [EE-G1] webhook là external WRITE — đọc SCP_EGRESS_MODE
                # trước mọi I/O; denial → raise → except ngoài → False.
                enforce_egress_policy(self.config.webhook_url)
                async with httpx.AsyncClient(timeout=5) as client:
                    r = await client.post(self.config.webhook_url, json=payload)
                    return r.status_code in (200, 204)
            return asyncio.run(_send())
        except Exception as e:
            logger.debug(f"[Notifications] Webhook error: {e}", exc_info=True)
            return False

    def _send_email(self, notification: dict[str, Any]) -> bool:
        """Send email notification."""
        try:
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(
                f"{notification['title']}\n\n{notification['message']}\n\n"
                f"Event: {notification['event_type']}\n"
                f"Severity: {notification['severity']}\n"
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(notification['timestamp']))}\n"
                f"Actions: {', '.join(notification.get('actions_taken', []))}"
            )
            msg["Subject"] = f"[SCP V102] {notification['title']}"
            msg["From"] = self.config.email_from
            msg["To"] = self.config.email_to

            with smtplib.SMTP(self.config.email_smtp_host, self.config.email_smtp_port) as server:
                server.starttls()
                server.login(self.config.email_username, self.config.email_password)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.debug(f"[Notifications] Email error: {e}", exc_info=True)
            return False

    def get_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent notifications for dashboard."""
        # [SCP-DNA-FIX R9-7] Snapshot under lock — notify() (worker thread)
        # mutates concurrently. deque does NOT support slicing directly,
        # so convert to list under lock, then slice the snapshot.
        with self._recent_lock:
            snapshot = list(self._recent)
        return snapshot[-limit:] if limit < len(snapshot) else snapshot

    def count_recent_by_type(self, event_type: str, cutoff_ts: float) -> int:
        """[SCP-DNA-FIX R9-7] Thread-safe count of recent notifications matching
        a given event_type with timestamp > cutoff_ts.

        TẠI SAO: api_server.py:_attack_mode_monitor (daemon thread) needs to
        count governance_kill events in the last 10 min. R8-1's fix inlined
        `sum(1 for _n in _notif._recent ...)` WITHOUT a lock — iterating a
        deque that notify() (worker thread) is appending to raises
        RuntimeError: list/deque changed size during iteration (CPython
        deque iterator caches size). The daemon's outer `except Exception:
        logger.debug(...)` swallows it → attack mode NEVER auto-enables.
        Exposing a thread-safe count method centralizes the locking.
        Fail-open: returns 0 on any internal error (attack mode stays in
        its current state — never falsely enables).
        """
        try:
            with self._recent_lock:
                return sum(
                    1 for _n in self._recent
                    if _n.get("timestamp", 0) > cutoff_ts
                    and _n.get("event_type") == event_type
                )
        except Exception as e:
            logger.debug(f"[Notifications] count_recent_by_type error: {e}", exc_info=True)
            return 0

    def stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "hourly_count": self._hourly_count,
            "max_per_hour": self.config.max_per_hour,
            "webhook_enabled": self.config.webhook_enabled,
            "email_enabled": self.config.email_enabled,
            "dashboard_enabled": self.config.dashboard_enabled,
        }


__all__ = ["NotificationConfig", "UserNotificationSystem"]
