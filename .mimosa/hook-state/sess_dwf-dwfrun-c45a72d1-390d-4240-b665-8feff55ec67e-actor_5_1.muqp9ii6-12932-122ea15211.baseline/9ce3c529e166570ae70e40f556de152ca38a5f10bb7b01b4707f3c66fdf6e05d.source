# SCP CIRCUIT: M14 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M14-closure.json)
import os
from pathlib import Path

from fastapi import APIRouter, Depends

from scp.api._shared import verify_admin
from scp.epistemic.evidence_store import EvidenceStore
from scp.self_model.capability_map import CapabilityMap

audit_router = APIRouter(tags=["Audit Engine"])
capability_router = APIRouter(tags=["Self Model"])

@audit_router.get("/v106/audit/reports", dependencies=[Depends(verify_admin)])
def get_audit_reports():
    '''Reads legacy audit reports from R8 and R9

    [M14-FIX] Added verify_admin — this endpoint used to be OPEN (no auth):
    probe-proven 200 without any token at runtime during the M14 closure,
    exposing audit report listings to unauthenticated callers (BFLA gap).
    '''
    results = {}
    for r_dir in ['audit_r8', 'audit_r9']:
        dpath = os.path.join("scp", r_dir)
        if os.path.exists(dpath):
            results[r_dir] = os.listdir(dpath)
    return {"status": "Audit engine active", "available_reports": results}

@capability_router.get("/v106/capabilities/{cap_id}", dependencies=[Depends(verify_admin)])
def get_capability(cap_id: str):
    '''Recomputes capability maturity on the fly

    [M14-FIX] Added verify_admin — this endpoint used to be OPEN (no auth):
    probe-proven 200 without any token at runtime during the M14 closure,
    exposing the self-model capability matrix to unauthenticated callers.
    '''
    _ROOT = Path(__file__).resolve().parent.parent.parent.parent
    _FOUNDATION = _ROOT / "data" / "foundation"

    os.makedirs(_FOUNDATION, exist_ok=True)
    os.makedirs(_FOUNDATION / "evidence_objects", exist_ok=True)
    if not os.path.exists(_FOUNDATION / "governance.sqlite"):
        open(_FOUNDATION / "governance.sqlite", 'a').close()

    _EVIDENCE_STORE = EvidenceStore(_FOUNDATION / "epistemic.sqlite", _FOUNDATION / "evidence_objects")

    cmap = CapabilityMap(
        governance_db_path=_FOUNDATION / "governance.sqlite",
        evidence_store=_EVIDENCE_STORE,
        reference_path=_ROOT / "spec" / "complete_scp_reference.yaml",
        bindings_path=_ROOT / "spec" / "implementation_bindings.yaml"
    )
    res = cmap.recompute_capability(cap_id, tested_sha="HEAD")
    cmap.db.close()
    return res
