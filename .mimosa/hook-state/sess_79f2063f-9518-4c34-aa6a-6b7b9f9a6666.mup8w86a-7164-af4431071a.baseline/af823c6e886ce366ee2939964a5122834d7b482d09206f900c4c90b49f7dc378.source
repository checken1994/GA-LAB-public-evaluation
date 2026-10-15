"""
SCP V98 — CanaryTokenMonitor
Copyright (c) 2026 Minh. MIT License.

Port từ WHY H2 — generate + monitor canary token để phát hiện data exfiltration.

Naming convention: <Purpose>Monitor (world standard).
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.security.canary_monitor")


@dataclass
class CanaryToken:
    """1 canary token đã generate."""
    token: str
    attacker_ip: str
    created_at: float
    expires_at: float
    triggered: bool = False
    triggered_at: float | None = None
    triggered_by: str | None = None  # github | darknet | internal_log

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "attacker_ip": self.attacker_ip,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "triggered": self.triggered,
            "triggered_at": self.triggered_at,
            "triggered_by": self.triggered_by,
        }


@dataclass
class CanaryStatus:
    """Status của canary cho 1 IP."""
    has_canary: bool = False
    canary_token: str = ""
    triggered: bool = False
    exfil_confirmed: bool = False
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_canary": self.has_canary,
            "canary_token": self.canary_token,
            "triggered": self.triggered,
            "exfil_confirmed": self.exfil_confirmed,
            "evidence": self.evidence,
        }


class CanaryTokenMonitor:
    """Generate + monitor canary tokens to detect data exfiltration.

    Naming convention: <Purpose>Monitor (world standard).

    Token lifecycle:
      1. Generate: khi attacker bị Phase 2+ counter
      2. Inject: vào response (invisible to human, visible to AI)
      3. Register: lưu vào internal DB
      4. Monitor: scan GitHub/darknet/internal logs for token reuse
      5. Expire: sau 7 ngày tự expire

    Sources to monitor:
      - Internal access logs (real-time)
      - Public GitHub search (every 6h)
      - Darknet paste scan (every 12h)
    """

    TOKEN_TTL_DAYS = 7
    SCAN_INTERVAL_GITHUB_H = 6
    SCAN_INTERVAL_DARKNET_H = 12

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tokens: dict[str, CanaryToken] = {}  # token → CanaryToken
        self.tokens_file = self.data_dir / "canary_tokens.jsonl"
        self.triggers_file = self.data_dir / "canary_triggers.jsonl"
        # [EXEC-3] TẠI SAO: self.tokens dict had NO thread lock — generate /
        # check_trigger / cleanup_expired / stats can run concurrently from
        # multiple workers. Iterating a dict while another thread mutates it
        # raises RuntimeError: dictionary changed size during iteration.
        self._lock = threading.Lock()
        self._stats = {
            "total_generated": 0,
            "total_triggered": 0,
            "total_expired": 0,
        }
        self._load_tokens()

    def _load_tokens(self):
        """Load existing tokens from file."""
        if not self.tokens_file.is_file():
            return
        try:
            for line in self.tokens_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    data = json.loads(line)
                    token = CanaryToken(
                        token=data["token"],
                        attacker_ip=data["attacker_ip"],
                        created_at=data["created_at"],
                        expires_at=data["expires_at"],
                        triggered=data.get("triggered", False),
                        triggered_at=data.get("triggered_at"),
                        triggered_by=data.get("triggered_by"),
                    )
                    self.tokens[token.token] = token
            logger.info(f"[CanaryTokenMonitor] Loaded {len(self.tokens)} tokens")
        except Exception as e:
            logger.warning(f"[CanaryTokenMonitor] Load error: {e}", exc_info=True)

    def generate(self, attacker_ip: str) -> CanaryToken:
        """Generate new canary token for attacker IP."""
        now = time.time()
        expires = now + (self.TOKEN_TTL_DAYS * 86400)
        token_str = f"CANARY_{hashlib.sha256(f'{attacker_ip}{now}'.encode()).hexdigest()[:16]}"

        token = CanaryToken(
            token=token_str,
            attacker_ip=attacker_ip,
            created_at=now,
            expires_at=expires,
        )
        # [EXEC-3] Lock tokens dict + _stats (mutated from multiple workers).
        with self._lock:
            self.tokens[token_str] = token
            self._stats["total_generated"] += 1
        self._persist_token(token)

        logger.info(f"[CanaryTokenMonitor] Generated {token_str} for {attacker_ip}")
        return token

    def _persist_token(self, token: CanaryToken):
        """Persist token to file."""
        try:
            with open(self.tokens_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(token.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug(f"[CanaryTokenMonitor] Persist error: {e}", exc_info=True)

    def check_trigger(self, text: str, source: str = "internal_log") -> CanaryToken | None:
        """Check if text contains any canary token.

        Args:
            text: Text to check (log entry, GitHub code, darknet paste)
            source: Where this text came from

        Returns:
            CanaryToken if triggered, None otherwise
        """
        # [EXEC-3] Snapshot tokens under lock (iterating a dict while another
        # thread mutates raises RuntimeError). Mutations (set triggered + _stats)
        # also under lock to keep audit consistent.
        with self._lock:
            for token_str, token in list(self.tokens.items()):
                if token_str in text:
                    if not token.triggered:
                        token.triggered = True
                        token.triggered_at = time.time()
                        token.triggered_by = source
                        self._stats["total_triggered"] += 1
                        logger.critical(
                            f"🚨 CANARY TRIGGERED: {token_str} from {source} "
                            f"(attacker_ip={token.attacker_ip})"
                        )
                        triggered_token = token
                        break
                    else:
                        return token
            else:
                return None
        # File I/O outside the lock (slow, audit-only).
        self._persist_trigger(triggered_token)
        return triggered_token

    def _persist_trigger(self, token: CanaryToken):
        """Persist trigger event."""
        try:
            with open(self.triggers_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(token.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug(f"[CanaryTokenMonitor] Trigger persist error: {e}", exc_info=True)

    def get_attacker_status(self, attacker_ip: str) -> CanaryStatus:
        """Get canary status for 1 IP."""
        with self._lock:
            ip_tokens = [t for t in self.tokens.values() if t.attacker_ip == attacker_ip]
            if not ip_tokens:
                return CanaryStatus(has_canary=False)

            triggered = [t for t in ip_tokens if t.triggered]
            return CanaryStatus(
                has_canary=True,
                canary_token=ip_tokens[-1].token,  # most recent
                triggered=bool(triggered),
                exfil_confirmed=bool(triggered),
                evidence=[t.to_dict() for t in triggered],
            )

    def get_all_triggers(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get all triggered tokens."""
        with self._lock:
            triggered = [t.to_dict() for t in self.tokens.values() if t.triggered]
        return sorted(triggered, key=lambda x: x.get("triggered_at", 0), reverse=True)[:limit]

    def cleanup_expired(self) -> int:
        """Remove expired tokens. Returns: number removed.

        [SCP-DNA-FIX R7-9] Prune both memory (self.tokens) AND disk (triggers_file).
        TẠI SAO: R6-9 wired this as daily periodic thread, but method only pruned
        self.tokens dict — triggers_file (disk) accumulated expired tokens forever.
        Each attacker IP gets a new canary token; expired ones never removed from
        file → disk leak. Now rewrites triggers_file atomically (.tmp + rename)
        excluding expired token IDs. Thread-safe (holds self._lock during both
        memory + disk prune). Reality evidence: du -sh triggers.jsonl grows 1KB/day.
        """
        now = time.time()
        with self._lock:
            expired = [t for t in self.tokens.values() if t.expires_at < now]
            expired_ids = {t.token for t in expired}
            for t in expired:
                del self.tokens[t.token]
            self._stats["total_expired"] += len(expired)

            #  Prune disk: rewrite triggers_file without expired tokens.
            # Atomic: write to .tmp then rename (crash-safe on POSIX).
            if expired_ids and self.triggers_file.exists():
                try:
                    import json as _json
                    remaining_lines = []
                    for line in self.triggers_file.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = _json.loads(line)
                            if entry.get("token") not in expired_ids:
                                remaining_lines.append(line)
                        except Exception:
                            # Keep unparseable lines (don't lose data).
                            logger.warning('CanaryTokenMonitor.cleanup_expired: Exception not handled', exc_info=True)
                            remaining_lines.append(line)
                    tmp = self.triggers_file.with_suffix(".tmp")
                    tmp.write_text("\n".join(remaining_lines) + ("\n" if remaining_lines else ""), encoding="utf-8")
                    tmp.replace(self.triggers_file)  # atomic rename
                except Exception as e:
                    logger.warning(f" Disk prune failed: {e}", exc_info=True)

        if expired:
            logger.info(f"[CanaryTokenMonitor] Cleaned up {len(expired)} expired tokens (memory + disk)")
        return len(expired)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                **self._stats,
                "active_tokens": len(self.tokens),
                "triggered_tokens": sum(1 for t in self.tokens.values() if t.triggered),
            }


__all__ = ["CanaryToken", "CanaryStatus", "CanaryTokenMonitor"]
