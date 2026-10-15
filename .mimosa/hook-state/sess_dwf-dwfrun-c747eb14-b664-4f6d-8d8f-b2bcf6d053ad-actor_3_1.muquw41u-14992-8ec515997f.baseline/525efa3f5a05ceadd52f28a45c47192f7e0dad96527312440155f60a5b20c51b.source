"""SCP Audit Engine (isolated subsystem).

Isolation contract (tests/T03_capability/test_flow_14_reintegrated_systems_scp_standard.py
REINT-14, tests/T03_capability/test_flow_19_audit_engine_scp_standard.py,
tests/test_deadzone_audit_engine.py):

- This package must stay importable so its audit flow stays covered.
- It must NOT define FastAPI routers or router endpoints and must NOT
  register background jobs; nothing outside ``scp/audit_engine/`` may
  import it.
"""
