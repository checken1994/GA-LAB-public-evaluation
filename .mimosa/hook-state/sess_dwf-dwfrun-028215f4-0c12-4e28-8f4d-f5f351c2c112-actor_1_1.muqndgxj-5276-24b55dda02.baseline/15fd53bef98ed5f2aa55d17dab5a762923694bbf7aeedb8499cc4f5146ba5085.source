"""SQLite-backed Persistent TraceStore Engine (Milestone 3 - Backward Traceability).

Implements durable storage for backward traceability with WAL mode, indexing,
and 5/6-stage causal DAG serialization adhering to PROJECT.md § Layer 3.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scp.core.runtime_paths import runtime_path

logger = logging.getLogger("scp.core.trace_store")


class TraceStore:
    """Persistent SQLite TraceStore adhering to PROJECT.md § Interface Contracts.

    Provides WAL mode, indexing by trace_id/session_id/timestamp,
    query/routing/retrieval/crosscheck/governance storage, and causal DAG serialization.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = runtime_path("SCP_TRACE_STORE_PATH", "trace_store.sqlite3")
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Create and configure a SQLite connection with WAL mode and NORMAL synchronous."""
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        """Initialize SQLite traces table and required indices."""
        conn = self._get_conn()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS traces (
                        trace_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        session_id TEXT,
                        query TEXT NOT NULL,
                        routing TEXT NOT NULL,
                        retrieval TEXT NOT NULL,
                        multi_llm_crosscheck TEXT NOT NULL,
                        governance TEXT NOT NULL,
                        final_decision TEXT NOT NULL,
                        causal_graph TEXT NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_session ON traces(session_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_timestamp ON traces(timestamp)")
        finally:
            conn.close()

    def record_trace(self, trace_data: dict[str, Any]) -> str:
        """Record a trace into SQLite and return trace_id."""
        trace_id = str(trace_data.get("trace_id") or f"trace-{uuid.uuid4().hex}")
        timestamp = str(trace_data.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        session_id = trace_data.get("session_id")
        if session_id is not None:
            session_id = str(session_id)
        query = str(trace_data.get("query", "") or "")

        def _json(v: Any) -> str:
            if isinstance(v, str):
                return v
            return json.dumps(v if v is not None else {}, ensure_ascii=False)

        routing_json = _json(trace_data.get("routing"))
        retrieval_json = _json(trace_data.get("retrieval"))
        crosscheck_json = _json(trace_data.get("multi_llm_crosscheck"))
        governance_json = _json(trace_data.get("governance"))
        final_decision_json = _json(trace_data.get("final_decision"))

        causal_graph = trace_data.get("causal_graph")
        if not causal_graph:
            causal_graph = self.build_causal_graph(trace_data)
        causal_graph_json = _json(causal_graph)

        conn = self._get_conn()
        try:
            with conn:
                conn.execute("""
                    INSERT OR REPLACE INTO traces (
                        trace_id, timestamp, session_id, query, routing, retrieval,
                        multi_llm_crosscheck, governance, final_decision, causal_graph
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trace_id, timestamp, session_id, query, routing_json, retrieval_json,
                    crosscheck_json, governance_json, final_decision_json, causal_graph_json,
                ))
        finally:
            conn.close()

        return trace_id

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Retrieve deserialized trace dictionary by trace_id, or None if not found."""
        conn = self._get_conn()
        try:
            cur = conn.execute("SELECT * FROM traces WHERE trace_id = ?", (str(trace_id),))
            row = cur.fetchone()
            if not row:
                return None

            def _parse(v: Any) -> Any:
                if isinstance(v, str):
                    try:
                        return json.loads(v)
                    except Exception:
                        logger.debug("_parse ignored", exc_info=True)
                        return v
                return v or {}

            return {
                "trace_id": row["trace_id"],
                "timestamp": row["timestamp"],
                "session_id": row["session_id"],
                "query": row["query"],
                "routing": _parse(row["routing"]),
                "retrieval": _parse(row["retrieval"]),
                "multi_llm_crosscheck": _parse(row["multi_llm_crosscheck"]),
                "governance": _parse(row["governance"]),
                "final_decision": _parse(row["final_decision"]),
                "causal_graph": _parse(row["causal_graph"]),
            }
        finally:
            conn.close()

    @staticmethod
    def build_causal_graph(trace_data: dict[str, Any]) -> dict[str, Any]:
        """Build a 5/6-stage causal DAG according to PROJECT.md § Layer 3."""
        nodes = [
            {"id": "node_query", "stage": "intake", "label": "User Query", "data": {"query": trace_data.get("query", "")}},
            {"id": "node_routing", "stage": "routing", "label": "Question Router", "data": trace_data.get("routing", {})},
            {"id": "node_retrieval", "stage": "retrieval", "label": "Autonomous Retrieval", "data": trace_data.get("retrieval", {})},
            {"id": "node_crosscheck", "stage": "adjudication", "label": "Multi-LLM Crosscheck", "data": trace_data.get("multi_llm_crosscheck", {})},
            {"id": "node_governance", "stage": "governance", "label": "Governance & WHY Gate", "data": trace_data.get("governance", {})},
            {"id": "node_output", "stage": "synthesis", "label": "Final Output", "data": trace_data.get("final_decision", {})},
        ]
        edges = [
            {"source": "node_query", "target": "node_routing"},
            {"source": "node_routing", "target": "node_retrieval"},
            {"source": "node_retrieval", "target": "node_crosscheck"},
            {"source": "node_crosscheck", "target": "node_governance"},
            {"source": "node_governance", "target": "node_output"},
        ]
        return {"nodes": nodes, "edges": edges}


# Class alias for contract compatibility
SqliteTraceStore = TraceStore

_global_trace_store: TraceStore | None = None
_global_trace_store_path: str | None = None
_store_lock = threading.Lock()


def get_trace_store(db_path: str | Path | None = None) -> TraceStore:
    """Return the TraceStore singleton accessor, reinitializing if path changes."""
    global _global_trace_store, _global_trace_store_path
    target_path = str(db_path or runtime_path("SCP_TRACE_STORE_PATH", "trace_store.sqlite3"))
    with _store_lock:
        if _global_trace_store is None or _global_trace_store_path != target_path:
            _global_trace_store = TraceStore(target_path)
            _global_trace_store_path = target_path
        return _global_trace_store


__all__ = ["TraceStore", "SqliteTraceStore", "get_trace_store"]
