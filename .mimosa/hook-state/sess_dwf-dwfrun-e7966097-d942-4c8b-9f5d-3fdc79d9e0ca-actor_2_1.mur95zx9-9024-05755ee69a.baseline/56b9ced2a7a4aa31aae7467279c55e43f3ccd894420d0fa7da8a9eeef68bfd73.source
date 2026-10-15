"""
LAYER 4: PROOF GRAPH — DAG phụ thuộc chứng minh.

DAG của proof dependencies.

VD: Prove "BTC = $62000"
├── Node A: Get prices from ≥3 exchanges
│   ├── Node A1: Binance API available
│   ├── Node A2: Coinbase API available
│   └── Node A3: Kraken API available
├── Node B: Prices agree within 2%
│   └── depends on: Node A
├── Node C: Data is fresh (timestamp < 5min)
│   └── depends on: Node A
└── Node D: Final verdict
    └── depends on: Node B, Node C

If Node A1 fails → Node A status = "degraded"
If Node A fails → Node B, C = "paused"
If Node B or C fails → Node D = "failed"

Extracted from `meta/cognitive_engine.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("scp.cognitive")


@dataclass
class ProofNode:
    """1 node trong ProofGraph."""
    node_id: str
    description: str            # Cần chứng minh gì?
    status: str = "unproven"    # unproven / proving / proven / failed / paused
    dependencies: list[str] = field(default_factory=list)  # IDs of nodes this depends on
    evidence: dict | None = None
    verdict: str | None = None
    confidence: float = 0.0


@dataclass
class ProofGraph:
    """
    DAG của proof dependencies.

    VD: Prove "BTC = $62000"
    ├── Node A: Get prices from ≥3 exchanges
    │   ├── Node A1: Binance API available
    │   ├── Node A2: Coinbase API available
    │   └── Node A3: Kraken API available
    ├── Node B: Prices agree within 2%
    │   └── depends on: Node A
    ├── Node C: Data is fresh (timestamp < 5min)
    │   └── depends on: Node A
    └── Node D: Final verdict
        └── depends on: Node B, Node C

    If Node A1 fails → Node A status = "degraded"
    If Node A fails → Node B, C = "paused"
    If Node B or C fails → Node D = "failed"
    """
    root_claim: str
    nodes: dict[str, ProofNode] = field(default_factory=dict)
    overall_status: str = "unproven"  # unproven / proven / failed / paused

    def add_node(self, node: ProofNode) -> None:
        self.nodes[node.node_id] = node

    def evaluate(self) -> str:
        """Evaluate graph — topological sort + propagate status."""
        # Topological order (simple — since we build linearly)
        for _node_id, node in self.nodes.items():
            if node.status == "unproven":
                # Check if all dependencies are proven
                deps_proven = all(
                    self.nodes.get(dep_id, ProofNode("", "")).status == "proven"
                    for dep_id in node.dependencies
                )
                if not deps_proven:
                    # Check if any dependency failed
                    any_failed = any(
                        self.nodes.get(dep_id, ProofNode("", "")).status == "failed"
                        for dep_id in node.dependencies
                    )
                    if any_failed:
                        node.status = "paused"  # Can't proceed — dependency failed
                    else:
                        node.status = "paused"  # Waiting for dependencies

        # Overall status
        root = self.nodes.get("root")
        if root:
            self.overall_status = root.status

        return self.overall_status


class ProofGraphBuilder:
    """
    Build ProofGraph từ VerificationPlan.
    """

    def build_from_plan(self, plan, verdict: str, confidence: float,
                        sources_succeeded: list[str], sources_failed: list[str],
                        reality_check: dict) -> ProofGraph:
        """Build ProofGraph from WHY Engine's VerificationPlan + judge result."""
        graph = ProofGraph(root_claim=getattr(plan, 'question', ''))

        # Root node — the final claim
        root = ProofNode(
            node_id="root",
            description=f"Prove: {getattr(plan, 'target', '?')}",
            status="unproven",
        )
        graph.add_node(root)

        # Node 1: Source availability
        source_node = ProofNode(
            node_id="source_availability",
            description=f"≥1 source available (got {len(sources_succeeded)})",
            status="proven" if len(sources_succeeded) > 0 else "failed",
            verdict="PASS" if sources_succeeded else "FAIL",
            evidence={"succeeded": sources_succeeded, "failed": sources_failed},
        )
        source_node.dependencies = []
        graph.add_node(source_node)

        # Node 2: Source agreement (if multi-source)
        agreement_node = ProofNode(
            node_id="source_agreement",
            description=f"Sources agree (confidence={confidence:.2f})",
            status="proven" if confidence > 0.5 else "failed",
            confidence=confidence,
        )
        agreement_node.dependencies = ["source_availability"]
        graph.add_node(agreement_node)

        # Node 3: Freshness (for real-time data)
        evidence_type = getattr(plan, 'evidence_type', '')
        if "real_time" in evidence_type or "market" in evidence_type:
            freshness_node = ProofNode(
                node_id="data_freshness",
                description="Data is fresh (not stale)",
                status="proven" if verdict in ("PASS", "FAIL") else "unproven",
            )
            freshness_node.dependencies = ["source_availability"]
            graph.add_node(freshness_node)
            root.dependencies = ["source_agreement", "data_freshness"]
        else:
            root.dependencies = ["source_agreement"]

        # Root verdict
        root.status = "proven" if verdict == "PASS" else ("failed" if verdict == "FAIL" else "unproven")
        root.verdict = verdict
        root.confidence = confidence

        graph.evaluate()

        #  Save graph to DB for history/analysis
        self._save_graph_to_db(graph, getattr(plan, 'question', ''), verdict, confidence)

        return graph

    def _save_graph_to_db(self, graph, question: str, verdict: str, confidence: float):
        """ Persist ProofGraph to proof_graph_history table."""
        try:
            from scp.core.db_manager import db_exec, init_db
            init_db()
            db_exec("""
                CREATE TABLE IF NOT EXISTS proof_graph_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    question TEXT,
                    root_claim TEXT,
                    overall_status TEXT,
                    node_count INTEGER,
                    nodes_json TEXT,
                    verdict TEXT,
                    confidence REAL
                )
            """)
            db_exec("CREATE INDEX IF NOT EXISTS idx_pgh_ts ON proof_graph_history(timestamp)")
            db_exec("CREATE INDEX IF NOT EXISTS idx_pgh_status ON proof_graph_history(overall_status)")

            import json as _json
            from datetime import datetime
            ts = datetime.now().astimezone().isoformat()
            nodes_json = _json.dumps({
                nid: {
                    "description": n.description,
                    "status": n.status,
                    "verdict": n.verdict,
                    "confidence": n.confidence,
                    "dependencies": n.dependencies,
                }
                for nid, n in graph.nodes.items()
            }, ensure_ascii=False, default=str)
            db_exec(
                "INSERT INTO proof_graph_history "
                "(timestamp, question, root_claim, overall_status, node_count, nodes_json, verdict, confidence) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (ts, question[:500], graph.root_claim[:200], graph.overall_status,
                 len(graph.nodes), nodes_json, verdict, confidence)
            )
        except Exception as e:
            logger.debug(f"ProofGraph DB save error: {e}", exc_info=True)
