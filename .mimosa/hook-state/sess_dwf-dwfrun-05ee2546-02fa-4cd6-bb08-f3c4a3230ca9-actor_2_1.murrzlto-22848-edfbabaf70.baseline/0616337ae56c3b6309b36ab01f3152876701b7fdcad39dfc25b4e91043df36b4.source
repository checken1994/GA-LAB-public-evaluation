# SCP CIRCUIT: M02 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M02-closure.json)
"""
World-State routes (X08) — bitemporal world assertions & entity events.

Routes:
  GET  /v105/world/stats          — TemporalAuthority stats
  POST /v105/world/assertions     — Record a world observation/assertion
  GET  /v105/world/assertions     — Query world assertions by subject
  POST /v105/world/events         — Record entity event
  GET  /v105/world/projection     — Get world-state projection snapshot
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from scp.api._shared import verify_admin
from scp.contracts.time import now_utc_iso
from scp.core.request_run_ledger import RequestRunLedger, traced_request
from scp.world_state import EntityEventAuthority, TemporalAuthority, WorldStateProjection

router = APIRouter(prefix="/v105/world", tags=["world-state"])
_LEDGER = RequestRunLedger()

_DATA_DIR = Path(os.environ.get("SCP_DATA_DIR", "data"))

logger = logging.getLogger("scp.api.routes.world_state")


def _internal_error(exc: Exception) -> HTTPException:
    """[AUDIT-20260909 MACH2-BUG4] 500 fail-closed, không leak message nội bộ."""
    logger.warning("[world_state] internal error: %s", exc, exc_info=True)
    return HTTPException(status_code=500, detail="internal error")


def _get_temporal() -> TemporalAuthority:
    """Lazy-init TemporalAuthority — creates DB on first call."""
    return TemporalAuthority(db_path=str(_DATA_DIR / "world_state.sqlite"))


@router.get("/stats", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="world_stats")
async def world_stats():
    """World-State subsystem status and assertion count."""
    try:
        temporal = _get_temporal()
        rows = temporal.db.query("SELECT COUNT(*) AS n FROM world_assertions")
        count = rows[0]["n"] if rows else 0
        temporal.close()
        return {
            "subsystem": "world_state",
            "status": "active",
            "total_assertions": count,
            "append_only": True,
            "epistemic_statuses": ["OBSERVED", "INFERRED", "PREDICTED"],
        }
    except Exception as exc:
        raise _internal_error(exc) from exc


@router.post("/assertions", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=True, action="world_record_assertion")
async def record_assertion(request: Request):
    """
    Record a bitemporal world assertion.

    Body: {
      "subject": "entity:covid-19",
      "predicate": "status:active",
      "value": {...},
      "epistemic_status": "OBSERVED|INFERRED|PREDICTED",
      "valid_time": "2024-01-01T00:00:00Z",
      "evidence_refs": ["ev-001"],
      "actor_id": "scp-system"
    }
    """
    body = await request.json()
    temporal = _get_temporal()
    try:
        result = temporal.record_observation(
            subject=str(body.get("subject", "")),
            predicate=str(body.get("predicate", "")),
            value=body.get("value", {}),
            valid_time=str(body.get("valid_time", now_utc_iso())),
            evidence_refs=body.get("evidence_refs", []),
            actor_id=str(body.get("actor_id", "scp-api")),
            epistemic_status=str(body.get("epistemic_status", "OBSERVED")),
        )
        return result
    finally:
        temporal.close()


@router.get("/assertions", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="world_query_assertions")
async def query_assertions(subject: str = "", limit: int = 50):
    """Query world assertions by subject prefix."""
    temporal = _get_temporal()
    try:
        if subject:
            rows = temporal.db.query(
                "SELECT * FROM world_assertions WHERE subject LIKE ? ORDER BY system_time DESC LIMIT ?",
                (f"{subject}%", limit),
            )
        else:
            rows = temporal.db.query(
                "SELECT * FROM world_assertions ORDER BY system_time DESC LIMIT ?",
                (limit,),
            )
        return {"assertions": rows, "count": len(rows)}
    finally:
        temporal.close()


@router.post("/events", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=True, action="world_record_event")
async def record_event(request: Request):
    """
    Record an entity event (wrapper over TemporalAuthority).

    Body: {
      "entity_id": "covid-19",
      "event_kind": "case_count_update",
      "payload": {"count": 1000},
      "valid_time": "2024-01-01T00:00:00Z",
      "evidence_refs": ["ev-001"],
      "actor_id": "scp-system"
    }
    """
    body = await request.json()
    temporal = _get_temporal()
    try:
        eea = EntityEventAuthority(temporal)
        result = eea.record_event(
            entity_id=str(body.get("entity_id", "")),
            event_kind=str(body.get("event_kind", "update")),
            payload=body.get("payload", {}),
            valid_time=str(body.get("valid_time", now_utc_iso())),
            evidence_refs=body.get("evidence_refs", []),
            actor_id=str(body.get("actor_id", "scp-api")),
        )
        return result
    finally:
        temporal.close()


@router.get("/projection", dependencies=[Depends(verify_admin)])
@traced_request(_LEDGER, require_write=False, action="world_projection")
async def world_projection(subject: str = "", limit: int = 100):
    """
    Get deterministic World-State projection rebuilt from the append log.
    """
    temporal = _get_temporal()
    try:
        projection = WorldStateProjection(temporal)
        snapshot = projection.project(subject_filter=subject or None, limit=limit)
        temporal.close()
        return {"projection": snapshot, "subject_filter": subject or "*"}
    except Exception as exc:
        temporal.close()
        raise _internal_error(exc) from exc
