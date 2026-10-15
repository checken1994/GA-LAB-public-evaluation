"""Trace lookup router and implementation for SCP API (Milestone 3).

Exposes GET /api/scp/v3/trace/{trace_id} with sensitive attribute redaction
and causal graph serialization. Requires admin verification.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from scp.api._shared import verify_admin
from scp.core.runtime_paths import runtime_data_dir
from scp.core.trace_contract import redact_attributes
from scp.core.trace_store import get_trace_store

logger = logging.getLogger("scp.api.trace")

router = APIRouter(dependencies=[Depends(verify_admin)])


# [AUDIT-2026-09-29 Agent4] Bounded scan window for legacy-ledger trace lookups.
# TraceLedger.get_trace() is O(file): request_runs.jsonl is an append-only
# ledger with no size bound and reached ~110 MB in production on 2026-09-29,
# so every trace GET that fell back to it read the whole file. Files above
# this limit are scanned most-recent-first within a bounded byte window.
# Matches older than the window are reported as not found (trace lookups
# target recent requests; full history stays in TraceStore SQLite and in the
# ledger file itself).
_LEDGER_SCAN_LIMIT_BYTES = 32 * 1024 * 1024


def _scan_recent_match(file_path: Path, trace_id: str) -> dict[str, Any] | None:
    """Most-recent-first bounded scan mirroring TraceLedger.get_trace matching.

    Mirrors the predicate of ``TraceLedger.get_trace`` (entry ``trace_id``,
    ``fields.task_id`` or ``fields.trace_id``) without reading the whole
    file: only the most recent ``_LEDGER_SCAN_LIMIT_BYTES`` window is read.
    Torn/corrupt lines inside the window are skipped (report-only
    philosophy -- never raise on read paths).
    """
    window = _LEDGER_SCAN_LIMIT_BYTES
    with file_path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - window))
        chunk = handle.read(window).decode("utf-8", errors="replace")
    lines = chunk.splitlines()
    if size > window and lines:
        lines = lines[1:]  # first line is likely torn by the window cut
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            fields = entry.get("fields")
            if not isinstance(fields, dict):
                fields = {}
            if (
                entry.get("trace_id") == trace_id
                or fields.get("task_id") == trace_id
                or fields.get("trace_id") == trace_id
            ):
                return entry
        except Exception as exc:
            logger.debug("trace GET dosed scan skipped a line in %s: %s", file_path, exc)
            continue
    return None


def _load_ledger_record(file_path: Path, trace_id: str, ledger_cls) -> dict[str, Any] | None:
    """Read-only ledger lookup with a bounded scan cost on oversized files.

    Small ledgers keep the exact previous behavior
    (``TraceLedger.get_trace`` over the full file); oversized ledgers switch
    to the bounded most-recent window so a GET can never be turned into an
    O(file) read by unbounded ledger growth.
    """
    try:
        size = file_path.stat().st_size
    except OSError as exc:
        logger.debug("trace GET stat failed for %s: %s", file_path, exc)
        return None
    if size <= _LEDGER_SCAN_LIMIT_BYTES:
        # Read-only lookup: verify_on_init=False so a GET can never
        # trigger the boot CHAIN_RECOVERY re-anchor write (recovery
        # belongs to the boot/append path, not to read paths).
        return ledger_cls(file_path, verify_on_init=False).get_trace(trace_id)
    logger.info(
        "trace GET: ledger %s is %d bytes (> %d) -- dosing scan to the most-recent %d-byte window",
        file_path,
        size,
        _LEDGER_SCAN_LIMIT_BYTES,
        _LEDGER_SCAN_LIMIT_BYTES,
    )
    return _scan_recent_match(file_path, trace_id)


@router.get("/api/scp/v3/trace/{trace_id}")
@router.get("/api/v3/trace/{trace_id}")
@router.get("/v3/trace/{trace_id}")
async def get_trace_record(trace_id: str) -> dict[str, Any]:
    """Retrieve backward-traceable causal history for a specific trace_id."""
    store = get_trace_store()
    record = store.get_trace(trace_id)

    # Fallback to legacy ledgers if not found in primary SQLite TraceStore
    if not record:
        try:
            from scp.trace_ledger import TraceLedger

            data_dir = runtime_data_dir()

            configured_ledger = os.environ.get("SCP_REQUEST_RUN_LEDGER_PATH", "").strip()
            candidate_paths = []
            if configured_ledger:
                candidate_paths.append(Path(configured_ledger).expanduser())
            candidate_paths.extend(
                data_dir / candidate_filename
                for candidate_filename in (
                    "trace_ledger.jsonl",
                    "ask_task_kernel_trace.jsonl",
                    "trace.jsonl",
                    "request_runs.jsonl",
                )
            )
            for file_path in candidate_paths:
                if file_path.exists():
                    ledger_record = _load_ledger_record(file_path, trace_id, TraceLedger)
                    if ledger_record:
                        if isinstance(ledger_record.get("fields"), dict):
                            merged = dict(ledger_record["fields"])
                            merged.update({k: v for k, v in ledger_record.items() if k != "fields"})
                            merged["_ledger_entry"] = ledger_record
                            record = merged
                        else:
                            record = ledger_record
                        break
        except Exception as _exc:
            logger.debug("Legacy trace ledger fallback lookup error: %s", _exc, exc_info=True)

    if not record:
        raise HTTPException(status_code=404, detail=f"Trace record not found: {trace_id}")

    return redact_attributes(record)


__all__ = ["router", "get_trace_record"]
