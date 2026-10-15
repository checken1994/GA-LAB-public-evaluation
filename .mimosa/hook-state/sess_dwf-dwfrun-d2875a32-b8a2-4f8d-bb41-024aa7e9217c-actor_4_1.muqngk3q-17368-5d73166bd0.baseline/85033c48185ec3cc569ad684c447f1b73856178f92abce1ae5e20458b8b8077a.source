# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scp.core.capability_token import (
    InvalidTokenSignatureError,
    compute_token_signature,
    get_capability_secret,
    verify_token_signature,
)

logger = logging.getLogger(__name__)



class CapabilityRevokedError(RuntimeError):
    """Raised when a new action cannot receive a capability token."""


@dataclass(frozen=True)
class CapabilityToken:
    subject: str
    epoch: int
    token_id: str
    issued_at: float
    signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "epoch": self.epoch,
            "token_id": self.token_id,
            "issued_at": self.issued_at,
            "signature": self.signature,
        }


def parse_capability_token(token: Any) -> CapabilityToken | None:
    """Safely parse a capability token from CapabilityToken, dict, or JSON str.

    Returns None fail-closed if token cannot be safely parsed.
    """
    if token is None or token == "":
        return None
    if isinstance(token, CapabilityToken):
        return token
    if isinstance(token, str):
        token_str = token.strip()
        if not token_str:
            return None
        try:
            parsed = json.loads(token_str)
            if isinstance(parsed, dict):
                token = parsed
            else:
                return None
        except Exception:
            logger.warning('parse_capability_token: Exception not handled', exc_info=True)
            return None
    if isinstance(token, dict):
        try:
            subject = str(token.get("subject", "")).strip()
            epoch_val = token.get("epoch")
            if epoch_val is None:
                return None
            epoch = int(epoch_val)
            token_id = str(token.get("token_id") or token.get("tokenId") or "")
            issued_at_val = token.get("issued_at") if token.get("issued_at") is not None else token.get("issuedAt", 0.0)
            issued_at = float(issued_at_val)
            signature = str(token.get("signature") or "")
            return CapabilityToken(
                subject=subject,
                epoch=epoch,
                token_id=token_id,
                issued_at=issued_at,
                signature=signature,
            )
        except (ValueError, TypeError):
            logger.debug('parse_capability_token: ValueError, TypeError ignored', exc_info=True)
            return None
    return None


class CapabilityAuthority:
    """Durable, epoch-based capability revocation for one SCP tool boundary.

    Revocation increments the epoch and persists an atomic JSON state file. Every
    action must obtain and validate a token immediately before dispatch. Old
    tokens remain invalid after both revoke and restore because restore also
    increments the epoch.
    """

    SCHEMA_VERSION = "scp-capability-epoch-v1"

    def __init__(self, state_path: str | Path, secret: bytes | str | None = None) -> None:
        self.state_path = Path(state_path)
        self._lock = threading.RLock()
        if secret is None:
            self.secret = get_capability_secret()
        elif isinstance(secret, str):
            if not secret.strip():
                from scp.core.capability_token import MissingSecretError
                raise MissingSecretError("Explicit capability secret is empty.")
            self.secret = secret.strip().encode("utf-8")
        else:
            if not secret or not secret.strip():
                from scp.core.capability_token import MissingSecretError
                raise MissingSecretError("Explicit capability secret is empty.")
            self.secret = secret
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _default_state() -> dict[str, Any]:
        return {
            "schema_version": CapabilityAuthority.SCHEMA_VERSION,
            "epoch": 0,
            "revoked": False,
            "reason": "initial",
            "actor": "system",
            "updated_at": time.time(),
        }

    def _load(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._default_state()
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if data.get("schema_version") != self.SCHEMA_VERSION:
                raise ValueError("unsupported capability state schema")
            if not isinstance(data.get("epoch"), int) or data["epoch"] < 0:
                raise ValueError("invalid capability epoch")
            if not isinstance(data.get("revoked"), bool):
                raise ValueError("invalid capability revoked flag")
            return data
        except (OSError, ValueError, json.JSONDecodeError):
            # Corrupt control state is fail-closed. A deliberate restore call
            # writes a fresh valid epoch; no action is silently permitted.
            logger.debug('CapabilityAuthority._load: OSError, ValueError, json.JSONDecodeError ignored', exc_info=True)
            state = self._default_state()
            state.update({"epoch": 0, "revoked": True, "reason": "state_corrupt", "actor": "system"})
            return state

    def _persist(self, state: dict[str, Any]) -> None:
        payload = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        fd, temporary = tempfile.mkstemp(prefix="capability-", suffix=".tmp", dir=str(self.state_path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.state_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def status(self) -> dict[str, Any]:
        with self._lock:
            state = self._load()
            return {
                "schema_version": state["schema_version"],
                "epoch": state["epoch"],
                "revoked": state["revoked"],
                "reason": state.get("reason", ""),
                "actor": state.get("actor", ""),
                "updated_at": state.get("updated_at"),
                "state_path": str(self.state_path),
            }

    def issue(self, subject: str, token_id: str | None = None) -> CapabilityToken:
        subject = str(subject).strip()[:128]
        if not subject:
            raise CapabilityRevokedError("capability subject is required")
        with self._lock:
            state = self._load()
            if state["revoked"]:
                raise CapabilityRevokedError(f"capabilities revoked: {state.get('reason', 'operator_revoke')}")
            epoch = state["epoch"]
            if token_id is None:
                token_id = uuid.uuid4().hex
            issued_at = round(time.time(), 6)
            signature = compute_token_signature(
                secret=self.secret,
                subject=subject,
                epoch=epoch,
                token_id=token_id,
                issued_at=issued_at,
            )
            return CapabilityToken(
                subject=subject,
                epoch=epoch,
                token_id=token_id,
                issued_at=issued_at,
                signature=signature,
            )

    def validate(self, token: CapabilityToken | None, required_subject: str | None = None) -> bool:
        if token is None:
            return False
        if not (hasattr(token, "subject") and hasattr(token, "epoch")):
            return False

        # Strict Fail-Closed Signature Verification (GAP-08)
        signature = getattr(token, "signature", "")
        verify_token_signature(
            secret=self.secret,
            subject=str(token.subject),
            epoch=int(token.epoch),
            token_id=str(getattr(token, "token_id", "")),
            issued_at=float(getattr(token, "issued_at", 0.0)),
            signature=signature,
        )

        if required_subject is not None:
            if str(getattr(token, "subject", "")) != str(required_subject):
                return False
        with self._lock:
            state = self._load()
            return not state["revoked"] and getattr(token, "epoch", -1) == state["epoch"]

    def revoke(self, reason: str = "operator_revoke", actor: str = "operator") -> dict[str, Any]:
        with self._lock:
            state = self._load()
            next_state = {
                **state,
                "epoch": int(state["epoch"]) + 1,
                "revoked": True,
                "reason": str(reason).strip()[:256] or "operator_revoke",
                "actor": str(actor).strip()[:128] or "operator",
                "updated_at": time.time(),
            }
            self._persist(next_state)
            return self.status()

    def restore(self, reason: str = "operator_restore", actor: str = "operator") -> dict[str, Any]:
        with self._lock:
            state = self._load()
            next_state = {
                **state,
                "epoch": int(state["epoch"]) + 1,
                "revoked": False,
                "reason": str(reason).strip()[:256] or "operator_restore",
                "actor": str(actor).strip()[:128] or "operator",
                "updated_at": time.time(),
            }
            self._persist(next_state)
            return self.status()


__all__ = [
    "CapabilityAuthority",
    "CapabilityRevokedError",
    "CapabilityToken",
    "InvalidTokenSignatureError",
    "parse_capability_token",
]
