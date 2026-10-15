# SCP CIRCUIT: M13 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M13-closure.json)
"""
[OPT-1] KnowledgeArbiter — resolve knowledge conflicts using graph.
DNA SCP: when 2 sources disagree on same fact, don't pick "most popular" —
falsify BOTH and require independent verification.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("scp.meta.knowledge_arbiter")

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    logger.warning("[KnowledgeArbiter] networkx not installed — using dict fallback")


@dataclass
class KnowledgeNode:
    entity: str
    attribute: str
    value: str
    source: str
    confidence: float = 0.5
    verified: bool = False
    # [Fix 4-b-011] Lineage — the upstream "origin family" of this source.
    # Two sources with the same lineage are NOT independent (DNA #5: ảo
    #幻觉 đồng thuận). E.g. `source="wikipedia_cache"` and `source="wikipedia_api"`
    # both have `lineage="wikipedia"` — they share upstream curation, so
    # agreement between them is NOT independent verification.
    # Defaults to the source name itself (so backward-compatible callers
    # that don't pass `lineage=` are treated as each-its-own-lineage — same
    # behavior as before for them, but now `resolve()` can detect when
    # multiple DISTINCT lineages agree).
    lineage: str | None = None


class KnowledgeArbiter:
    """Resolve conflicts between knowledge entries from different sources.

    Architecture:
      - Graph nodes = (entity, attribute) facts with value + source
      - Graph edges = "agrees_with" or "contradicts" relationships
      - When 2 sources disagree → mark BOTH as unverified, require 3rd source

    Usage:
        arbiter = KnowledgeArbiter()
        arbiter.add_fact("Paris", "capital_of", "France", source="wikipedia", confidence=0.9)
        arbiter.add_fact("Paris", "capital_of", "Lyon", source="unreliable_blog", confidence=0.3)
        result = arbiter.resolve("Paris", "capital_of")
        # → {"value": "France", "confidence": 0.9, "conflict": True, "requires_verification": True}
    """

    def __init__(self, source_reputation=None):
        """Initialize the KnowledgeArbiter.

        [Task 33-A] Added optional ``source_reputation`` parameter (a
        ReputationStore-like instance). When supplied, conflict resolution
        weights facts by ``confidence * source_reputation`` instead of
        ``confidence`` alone — a high-confidence fact from a blocked source
        (reputation 0.1) should NOT beat a slightly lower-confidence fact
        from a trusted source (reputation 0.95).

        Backward compatible: ``source_reputation`` defaults to ``None``,
        so existing callers (``KnowledgeArbiter()``) keep their old behavior.
        """
        self.source_reputation = source_reputation  # SourceReputation instance
        if HAS_NETWORKX:
            self.graph = nx.DiGraph()
        else:
            self.graph = None  # fallback to dict
        self._facts: dict[tuple[str, str], list[KnowledgeNode]] = {}
        self._stats = {
            "total_facts": 0,
            "conflicts_detected": 0,
            "resolved_by_majority": 0,
            "resolved_by_confidence": 0,
            "requires_verification": 0,
        }

    def get_source_weight(self, source: str) -> float:
        """Get reputation weight for a source (0.0-1.0).

        [Task 33-A] Queries the wired SourceReputation (ReputationStore).
        If no reputation store is wired, returns 0.5 (neutral) so that
        behavior degrades gracefully to confidence-only resolution.
        """
        if not self.source_reputation:
            return 0.5  # default neutral
        try:
            rec = self.source_reputation.get(source)
            if rec is not None:
                # SourceReputation dataclass has reputation_score [0, 1]
                score = getattr(rec, "reputation_score", None)
                if score is None:
                    return 0.5
                # Guard against weird values
                return float(max(0.0, min(1.0, score)))
            return 0.5
        except Exception as e:
            logger.debug(
                f"[KnowledgeArbiter] get_source_weight({source}) failed: {e}"
            , exc_info=True)
            return 0.5

    def add_fact(self, entity: str, attribute: str, value: str,
                 source: str, confidence: float = 0.5,
                 lineage: str | None = None) -> None:
        """Add a fact to the arbiter. Detects conflicts automatically.

        [Fix 4-b-011] Previously: when `value` matched an existing node,
        the existing node's confidence was boosted and the function returned
        EARLY — the new (source, value) was NOT stored as a separate node.
        So `resolve()` always saw `len(nodes) == 1` for any agreeing set,
        and the `multi_source_agreement` branch was DEAD CODE (DNA #5 ảo
       幻觉 đồng thuận — 10 sources agreeing appeared as 1 source; DNA #8
        KB accumulation — agreement not recorded).
        Now: the new node is ALWAYS appended (deduped by (source, value)
        so the same source re-reporting the same value isn't counted twice).
        `resolve()` then sees N nodes with the same value and can fire
        `multi_source_agreement` — and crucially, only fires it when the
        sources are from INDEPENDENT lineages (DNA #5).
        """
        key = (entity.lower(), attribute.lower())
        # Effective lineage: if caller didn't supply one, treat source as
        # its own lineage (backward-compat: every distinct source is its
        # own lineage → N distinct sources = N distinct lineages).
        eff_lineage = lineage if lineage is not None else source
        node = KnowledgeNode(
            entity=entity, attribute=attribute, value=value,
            source=source, confidence=confidence,
            lineage=eff_lineage,
        )
        if key not in self._facts:
            self._facts[key] = []
        existing_values = {n.value.lower() for n in self._facts[key]}

        if value.lower() in existing_values:
            # Agreement — boost confidence of existing matching node(s).
            # [Fix 4-b-011] Do NOT early-return: append the new node too,
            # UNLESS this exact (source, value) was already recorded
            # (avoids counting the same source twice for the same value).
            already_recorded = any(
                n.value.lower() == value.lower() and n.source == source
                for n in self._facts[key]
            )
            if not already_recorded:
                self._facts[key].append(node)
                self._stats["total_facts"] += 1
                if self.graph:
                    self.graph.add_node(
                        f"{entity}.{attribute}.{source}",
                        data=node.__dict__,
                    )
            # Boost existing matching nodes (preserve old behavior —
            # agreement boosts confidence).
            for n in self._facts[key]:
                if n.value.lower() == value.lower():
                    n.confidence = min(1.0, n.confidence + 0.1)
                    n.verified = True
            return

        # Different value = conflict
        if existing_values:
            self._stats["conflicts_detected"] += 1
            logger.info(
                f"[KnowledgeArbiter] CONFLICT: {entity}.{attribute} "
                f"existing={existing_values} vs new='{value}' (source={source})"
            )
        self._facts[key].append(node)
        self._stats["total_facts"] += 1
        if self.graph:
            self.graph.add_node(
                f"{entity}.{attribute}.{source}",
                data=node.__dict__,
            )

    def resolve(self, entity: str, attribute: str) -> dict:
        """Resolve a fact. Returns dict with value, confidence, conflict status."""
        key = (entity.lower(), attribute.lower())
        nodes = self._facts.get(key, [])
        if not nodes:
            return {"value": None, "confidence": 0.0, "conflict": False,
                    "requires_verification": False, "reason": "no_data"}
        if len(nodes) == 1:
            n = nodes[0]
            return {"value": n.value, "confidence": n.confidence, "conflict": False,
                    "requires_verification": False, "reason": "single_source",
                    "source": n.source}
        # Multiple sources — check if they agree
        values = {n.value.lower() for n in nodes}
        if len(values) == 1:
            # All agree on value. [Fix 4-b-011] But agreement only counts
            # as `multi_source_agreement` when the sources are from
            # INDEPENDENT lineages (DNA #5: ảo幻觉 đồng thuận). E.g. 3 nodes
            # all from lineage="wikipedia" (cache + api + mirror) are NOT
            # independent — they share upstream curation. In that case we
            # return `single_lineage_agreement` (a weaker signal) so the
            # caller knows the agreement isn't truly cross-lineage.
            distinct_lineages = {n.lineage for n in nodes if n.lineage}
            avg_conf = sum(n.confidence for n in nodes) / len(nodes)
            if len(distinct_lineages) >= 2:
                # ≥2 INDEPENDENT lineages agree — strong signal (DNA #5).
                self._stats["resolved_by_majority"] += 1
                return {
                    "value": nodes[0].value,
                    "confidence": min(1.0, avg_conf + 0.2),
                    "conflict": False,
                    "requires_verification": False,
                    "reason": "multi_source_agreement",
                    "sources": [n.source for n in nodes],
                    "lineages": sorted(distinct_lineages),
                    "independent_lineages": len(distinct_lineages),
                }
            # All nodes share ONE lineage — agreement is real but NOT
            # independent (DNA #5: ảo幻觉 đồng thuận if treated as such).
            # Be honest: don't fire multi_source_agreement; report as
            # `single_lineage_agreement` with a smaller boost.
            self._stats["resolved_by_majority"] += 1
            return {
                "value": nodes[0].value,
                "confidence": min(1.0, avg_conf + 0.05),
                "conflict": False,
                "requires_verification": True,  # need cross-lineage confirmation
                "reason": "single_lineage_agreement",
                "sources": [n.source for n in nodes],
                "lineages": sorted(distinct_lineages),
                "independent_lineages": len(distinct_lineages),
            }
        # Conflict — pick highest *effective* score, mark requires_verification.
        # [Task 33-A] Effective score = confidence * source_reputation_weight.
        # When no reputation store is wired, get_source_weight() returns 0.5
        # for every source, so the relative ordering collapses to the
        # original confidence-only sort (backward compatible).
        nodes_sorted = sorted(
            nodes,
            key=lambda n: -(n.confidence * self.get_source_weight(n.source)),
        )
        winner = nodes_sorted[0]
        self._stats["resolved_by_confidence"] += 1
        self._stats["requires_verification"] += 1
        return {
            "value": winner.value, "confidence": winner.confidence * 0.7,  # penalize
            "conflict": True, "requires_verification": True,
            "reason": "conflict_resolved_by_confidence",
            "sources": [n.source for n in nodes],
            "conflicting_values": [n.value for n in nodes],
            "winner_source": winner.source,
            "winner_effective_score": winner.confidence * self.get_source_weight(winner.source),
        }

    def stats(self) -> dict:
        return {**self._stats, "unique_facts": len(self._facts)}


__all__ = ["KnowledgeArbiter", "KnowledgeNode"]
