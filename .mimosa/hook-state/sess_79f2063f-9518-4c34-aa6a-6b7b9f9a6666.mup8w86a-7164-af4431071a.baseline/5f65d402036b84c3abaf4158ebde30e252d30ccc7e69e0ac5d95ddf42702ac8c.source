"""Cryptographic Ledger Provenance for Agent OS Autonomous Steps with HMAC-SHA256 support."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scp.core.trace_contract import redact_attributes
from scp.trace_ledger import TraceLedger

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ProvenanceBlock:
    block_index: int
    prev_block_hash: str | None
    task_id: str
    step_id: str
    tool_name: str
    input_sha256: str
    capability_token_id: str
    capability_token_hash: str
    output_sha256: str
    status: str  # SUCCESS, FAILED, BLOCKED, UNKNOWN
    duration_ms: float
    timestamp: float
    block_hash: str = ""

    def canonical_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("block_hash", None)
        return d

    def compute_hmac(self, key: bytes | str) -> str:
        """Compute HMAC-SHA256 digest of the block canonical serialization."""
        serialized = json.dumps(self.canonical_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        k = key.encode("utf-8") if isinstance(key, str) else key
        return "hmac-sha256:" + hmac.new(k, serialized.encode("utf-8"), hashlib.sha256).hexdigest()

    def compute_hash(self, key: bytes | str | None = None) -> str:
        """Compute block digest. Uses HMAC-SHA256 if key is provided; bare SHA-256 otherwise."""
        if key is not None:
            return self.compute_hmac(key)
        serialized = json.dumps(self.canonical_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class AutonomousAuditLedger:
    """Ledger recording two-phase tool provenance blocks into the append-only TraceLedger with HMAC-SHA256."""

    def __init__(
        self,
        trace_ledger: TraceLedger | None = None,
        ledger_path: str | Path | None = None,
        hmac_key: str | bytes | None = None,
        require_hmac: bool = False,
    ) -> None:
        if trace_ledger is not None:
            self.trace_ledger = trace_ledger
        else:
            path = ledger_path or "data/trace_ledger.jsonl"
            self.trace_ledger = TraceLedger(path)

        self.require_hmac = require_hmac or (os.environ.get("SCP_REQUIRE_LEDGER_HMAC", "0") in ("1", "true", "yes"))

        if hmac_key is not None:
            self.hmac_key: bytes | None = hmac_key.encode("utf-8") if isinstance(hmac_key, str) else hmac_key
        else:
            env_key = os.environ.get("SCP_LEDGER_HMAC_KEY")
            self.hmac_key = env_key.encode("utf-8") if env_key else None

    @staticmethod
    def _hash_value(val: Any, key: bytes | str | None = None) -> str:
        """Compute canonical digest of a value. Uses HMAC-SHA256 if key is provided, else SHA-256."""
        raw = json.dumps(val, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        if key:
            k = key.encode("utf-8") if isinstance(key, str) else key
            return "hmac-sha256:" + hmac.new(k, raw.encode("utf-8"), hashlib.sha256).hexdigest()
        return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def compute_digest(self, val: Any) -> str:
        """Helper to compute digest using instance HMAC key if configured."""
        return self._hash_value(val, self.hmac_key)

    def commit_intent(
        self,
        task_id: str,
        step_id: str,
        tool_name: str,
        params: dict[str, Any],
        capability_token: Any,
        parent_trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Commit Phase 1: Tool invocation intent with parameter digest and optional HMAC signature."""
        if self.require_hmac and not self.hmac_key:
            raise RuntimeError("AutonomousAuditLedger fail-closed: HMAC key is required but missing; refusing to commit unauthenticated intent")

        if isinstance(capability_token, dict):
            token_id = str(capability_token.get("token_id", "") or params.get("token_id", ""))
            token_sig = str(capability_token.get("signature", ""))
        else:
            token_id = str(getattr(capability_token, "token_id", "") or params.get("token_id", ""))
            token_sig = str(getattr(capability_token, "signature", ""))

        token_hash = self.compute_digest({"token_id": token_id, "signature": token_sig})
        input_hash = self.compute_digest(redact_attributes(params))

        fields: dict[str, Any] = {
            "event": "AUTONOMOUS_TOOL_INTENT",
            "task_id": task_id,
            "step_id": step_id,
            "tool_name": tool_name,
            "input_sha256": input_hash,
            "token_id": token_id,
            "token_hash": token_hash,
            "parent_trace_id": parent_trace_id or "",
            "timestamp": time.time(),
        }
        if self.hmac_key:
            canonical_intent = json.dumps({
                "event": "AUTONOMOUS_TOOL_INTENT",
                "task_id": task_id,
                "step_id": step_id,
                "tool_name": tool_name,
                "input_sha256": input_hash,
                "parent_trace_id": parent_trace_id or "",
                "timestamp": str(fields.get("timestamp", "")),
            }, sort_keys=True, separators=(",", ":"))
            fields["hmac_sha256"] = hmac.new(self.hmac_key, canonical_intent.encode("utf-8"), hashlib.sha256).hexdigest()

        entry = self.trace_ledger.append(**fields)
        return entry

    def commit_result(
        self,
        task_id: str,
        step_id: str,
        tool_name: str,
        intent_entry_hash: str,
        result_data: dict[str, Any],
        evidence: dict[str, Any],
        status: str,
        duration_ms: float,
    ) -> dict[str, Any]:
        """Commit Phase 2: Tool execution result with evidence and output digest."""
        if self.require_hmac and not self.hmac_key:
            raise RuntimeError("AutonomousAuditLedger fail-closed: HMAC key is required but missing; refusing to commit unauthenticated result")

        output_hash = self.compute_digest(redact_attributes(result_data))
        evidence_hash = self.compute_digest(evidence)

        fields: dict[str, Any] = {
            "event": "AUTONOMOUS_TOOL_RESULT",
            "task_id": task_id,
            "step_id": step_id,
            "tool_name": tool_name,
            "intent_entry_hash": intent_entry_hash,
            "output_sha256": output_hash,
            "evidence_sha256": evidence_hash,
            "status": status,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
        }
        if self.hmac_key:
            canonical_result = json.dumps({
                "event": "AUTONOMOUS_TOOL_RESULT",
                "task_id": task_id,
                "step_id": step_id,
                "tool_name": tool_name,
                "intent_entry_hash": intent_entry_hash,
                "output_sha256": output_hash,
                "evidence_sha256": evidence_hash,
                "status": status,
                "timestamp": str(fields.get("timestamp", "")),
            }, sort_keys=True, separators=(",", ":"))
            fields["hmac_sha256"] = hmac.new(self.hmac_key, canonical_result.encode("utf-8"), hashlib.sha256).hexdigest()

        entry = self.trace_ledger.append(**fields)
        return entry

    def verify_provenance(self) -> dict[str, Any]:
        """Verify the immutable ledger hash chain and HMAC signatures for all autonomous steps."""
        verification = self.trace_ledger.verify()
        if not self.hmac_key:
            if self.require_hmac:
                errors = list(verification.get("errors", []))
                errors.append("missing_hmac_key: Autonomous audit ledger requires HMAC key (fail-closed)")
                return {
                    "entries": verification.get("entries", 0),
                    "hash_chain_valid": False,
                    "errors": errors,
                }
            return verification

        errors = list(verification.get("errors", []))
        ledger_path = getattr(self.trace_ledger, "path", None)
        if ledger_path and Path(ledger_path).exists():
            lines = Path(ledger_path).read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                try:
                    e = json.loads(line)
                    fields = e.get("fields", {})
                    event = fields.get("event")
                    recorded_hmac = fields.get("hmac_sha256")
                    if self.hmac_key and event in ("AUTONOMOUS_TOOL_INTENT", "AUTONOMOUS_TOOL_RESULT"):
                        if not recorded_hmac:
                            errors.append(f"missing_hmac_{'intent' if event == 'AUTONOMOUS_TOOL_INTENT' else 'result'}:{i}")
                            continue

                    if recorded_hmac and event == "AUTONOMOUS_TOOL_INTENT":
                        canonical = json.dumps({
                            "event": "AUTONOMOUS_TOOL_INTENT",
                            "task_id": fields.get("task_id", ""),
                            "step_id": fields.get("step_id", ""),
                            "tool_name": fields.get("tool_name", ""),
                            "input_sha256": fields.get("input_sha256", ""),
                            "parent_trace_id": fields.get("parent_trace_id", ""),
                            "timestamp": str(fields.get("timestamp", "")),
                        }, sort_keys=True, separators=(",", ":"))
                        expected = hmac.new(self.hmac_key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
                        if not hmac.compare_digest(recorded_hmac, expected):
                            errors.append(f"hmac_intent:{i}")
                    elif recorded_hmac and event == "AUTONOMOUS_TOOL_RESULT":
                        canonical = json.dumps({
                            "event": "AUTONOMOUS_TOOL_RESULT",
                            "task_id": fields.get("task_id", ""),
                            "step_id": fields.get("step_id", ""),
                            "tool_name": fields.get("tool_name", ""),
                            "intent_entry_hash": fields.get("intent_entry_hash", ""),
                            "output_sha256": fields.get("output_sha256", ""),
                            "evidence_sha256": fields.get("evidence_sha256", ""),
                            "status": fields.get("status", ""),
                            "timestamp": str(fields.get("timestamp", "")),
                        }, sort_keys=True, separators=(",", ":"))
                        expected = hmac.new(self.hmac_key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
                        if not hmac.compare_digest(recorded_hmac, expected):
                            errors.append(f"hmac_result:{i}")
                except Exception:
                    logger.debug("verify_provenance ignored", exc_info=True)
                    errors.append(f"parse_error:{i}")

        return {
            "entries": verification.get("entries", 0),
            "hash_chain_valid": len(errors) == 0,
            "errors": errors,
        }


__all__ = [
    "ProvenanceBlock",
    "AutonomousAuditLedger",
]
