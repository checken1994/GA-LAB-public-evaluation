# Worker M3 Dispatch
Scope: Milestone 3 - Backward Traceability Engine & API (R3)

## 2026-09-21T12:15:00Z
You are Worker M3 (teamwork_preview_worker) for the SCP project.
Your working directory is: D:\scp\.agents\worker_m3
Workspace root: D:\scp

MANDATORY: Read D:\scp\.agents\ORIGINAL_REQUEST.md (specifically section ## 2026-09-21T10:17:56Z) before starting.
Read project architecture: D:\scp\.agents\orchestrator_1\PROJECT.md
Read M1 handoff: D:\scp\.agents\worker_m1\handoff.md
Read M2 handoff: D:\scp\.agents\worker_m2\handoff.md
Read test references: tests/T12_unified_chatbot/test_tier1_feature_coverage.py (Features 13, 14, 15, 16) and tests/T12_unified_chatbot/conftest.py (SqliteTraceStore)

FILE OWNERSHIP:
You exclusively own and may modify/create:
- scp/core/trace_store.py
- scp/core/trace_contract.py
- scp/api_server_parts/_trace_impl.py
- scp/api_server_parts/_ask_impl.py (wire trace recording and headers)
- scp/api/chat.py (wire trace recording for websocket chat)
- scp/api_server.py (mount trace router/endpoint)
- tests/ (accompanying tests for M3)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

SCOPE & TASK - MILESTONE 3 (Backward Traceability Engine & API - R3):
1. SQLite TraceStore Engine (scp/core/trace_store.py):
   - Implement `TraceStore` (and alias `SqliteTraceStore`) backed by SQLite (default: `data/trace_store.sqlite3`, configurable via `SCP_TRACE_STORE_PATH`).
   - SQLite configuration: WAL mode (`PRAGMA journal_mode=WAL`), `PRAGMA synchronous=NORMAL`.
   - Table `traces` with schema:
     * `trace_id TEXT PRIMARY KEY`
     * `timestamp TEXT NOT NULL`
     * `session_id TEXT`
     * `query TEXT NOT NULL`
     * `routing TEXT NOT NULL`
     * `retrieval TEXT NOT NULL`
     * `multi_llm_crosscheck TEXT NOT NULL`
     * `governance TEXT NOT NULL`
     * `final_decision TEXT NOT NULL`
     * `causal_graph TEXT NOT NULL`
   - Indices on `session_id` and `timestamp`.
   - Methods:
     * `record_trace(trace_data: dict[str, Any]) -> str`: Returns trace_id.
     * `get_trace(trace_id: str) -> dict[str, Any] | None`: Returns deserialized trace dictionary with all 10 fields, or None if not found.
     * `build_causal_graph(trace_data: dict[str, Any]) -> dict[str, Any]`: Builds 5/6-stage causal DAG:
       Nodes: intake (User Query), routing (Question Router), retrieval (Autonomous Retrieval), adjudication (Multi-LLM Crosscheck), governance (Governance & WHY Gate), synthesis (Final Output).
       Edges: node_query -> node_routing -> node_retrieval -> node_crosscheck -> node_governance -> node_output.
     * `get_trace_store() -> TraceStore` singleton accessor.

2. Trace Contract & Redaction (scp/core/trace_contract.py):
   - Implement `redact_attributes(data: dict[str, Any]) -> dict[str, Any]`:
     Recursively masks sensitive values (keys containing "token", "password", "secret", "authorization", "key", "api_key", "bearer") with `"[REDACTED]"`.

3. Trace ID Propagation & Recording:
   - In `scp/api_server_parts/_ask_impl.py`:
     * Generate `trace_id = f"trace-{uuid.uuid4().hex}"` if not already set.
     * Ensure `trace_id` is included in `AskResponse` body and returned in response headers (`X-SCP-Trace-ID`).
     * Asynchronously or synchronously record the complete trace to `TraceStore` upon request completion (including routing lane, retrieval facts, crosscheck verdicts, why-gate decision, and final answer).
   - In `scp/api/chat.py`:
     * Ensure WebSocket response frames include `trace_id`.
     * Record trace to `TraceStore`.

4. Trace Lookup API (scp/api_server_parts/_trace_impl.py & scp/api_server.py):
   - Implement endpoint `GET /api/scp/v3/trace/{trace_id}`.
   - Return 200 with full trace dictionary (with `redact_attributes` applied), or 404 if trace does not exist.
   - Ensure router is included in FastAPI `app` in `scp/api_server.py`.

5. Verification:
   - Add unit tests for M3 in `tests/T07_learning/test_m3_traceability_engine.py`.
   - Run tests:
     pytest tests/T12_unified_chatbot/test_tier1_feature_coverage.py -q
     pytest tests/T07_learning -q
     pytest tests/T02_contract -q
     python tools/t00_meta_audit.py
   - Ensure 0 new regressions.

OUTPUT:
Write detailed implementation notes and verification results to D:\scp\.agents\worker_m3\handoff.md.
When complete, send a concise message to your parent.
