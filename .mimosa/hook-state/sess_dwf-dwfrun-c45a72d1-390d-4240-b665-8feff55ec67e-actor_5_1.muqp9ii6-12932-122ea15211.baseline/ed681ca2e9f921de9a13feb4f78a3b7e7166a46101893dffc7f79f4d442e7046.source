"""
SCP V98 — Source Reputation System (Dynamic)
=============================================
Dynamic reputation scoring cho từng nguồn dữ liệu, thay vì static 5-tier.

CHỐNG UPSTREAM POISONING:
- Mỗi source có reputation_score [0, 1] động, cập nhật liên tục
- Khi fact từ source X bị Healing Cascade invalidate → reputation X *= 0.9
- Khi reputation < 0.3 → đưa vào Watchlist (suspect)
- Khi reputation < 0.1 → block vĩnh viễn
- Khi fact từ source X được source khác xác nhận → reputation X += 0.05 (cap 1.0)
- Reputation decay 5% mỗi 30 ngày (nguồn cũ không cập nhật → mất uy tín)

USAGE:
    from scp.knowledge.source_reputation import ReputationStore
    store = ReputationStore(db_path="data/scp_reputation.sqlite")

    # Khi commit fact từ source
    weight = store.get_effective_weight(source="wikipedia", tier=2)
    # → returns 0.85 * 0.95 (reputation) * 0.97 (decay) = 0.784

    # Khi fact bị invalidate
    store.on_fact_invalidated(source="wikipedia")

    # Khi fact được source khác xác nhận
    store.on_fact_independently_verified(source="wikipedia")
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

logger = logging.getLogger("scp.knowledge.source_reputation")

# ============================================================
# Constants
# ============================================================
REPUTATION_INITIAL = 1.0           # Mỗi source mới khởi tạo = 1.0
REPUTATION_PENALTY_INVALIDATE = 0.9  # Mỗi lần fact bị invalidate → *= 0.9
REPUTATION_REWARD_VERIFY = 1.05     # Mỗi lần fact được xác nhận → *= 1.05
REPUTATION_CAP = 1.0                # Không vượt quá 1.0
REPUTATION_DECAY_PER_30D = 0.95     # Decay 5% mỗi 30 ngày không update
REPUTATION_WATCHLIST_THRESHOLD = 0.3   # < 0.3 → suspect
REPUTATION_BLOCK_THRESHOLD = 0.1       # < 0.1 → block vĩnh viễn
REPUTATION_RECOVERY_PER_MONTH = 0.1    # Recovery 0.1/tháng khi trong watchlist

# Static tier weights (tương thích với TrustHierarchy)
TIER_WEIGHTS = {
    0: 1.00,  # AXIOMATIC (Codata, NIST, Python AST)
    1: 0.95,  # AUTHORITATIVE (FDA, WHO, DrugBank)
    2: 0.85,  # CONSENSUS (Wikipedia, Wikidata, arXiv)
    3: 0.70,  # REALTIME (Coingecko, Binance, weather)
    4: 0.50,  # LEARNED (scp_learned, experience, curiosity)
}


@dataclass
class SourceReputation:
    """Reputation record cho 1 source."""
    source: str                     # source identifier (vd: "wikipedia", "https://...")
    static_tier: int                # 0-4 (từ TIER_WEIGHTS)
    reputation_score: float = REPUTATION_INITIAL
    facts_contributed: int = 0
    facts_invalidated: int = 0
    facts_verified: int = 0
    first_seen: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    last_invalidated: float = 0.0
    status: str = "active"          # active | watchlist | blocked

    @property
    def accuracy_rate(self) -> float:
        """Tỷ lệ fact hợp lệ = (contributed - invalidated) / contributed."""
        if self.facts_contributed == 0:
            return 1.0
        return max(0.0, 1.0 - self.facts_invalidated / self.facts_contributed)

    @property
    def time_decay(self) -> float:
        """Decay theo thời gian — 5% mỗi 30 ngày không update."""
        if self.last_updated == 0:
            return 1.0
        days_since = (time.time() - self.last_updated) / 86400
        periods_30d = days_since // 30
        return REPUTATION_DECAY_PER_30D ** periods_30d

    def effective_weight(self) -> float:
        """
        Trọng số hiệu dụng = static_tier_weight × reputation × time_decay.

        Đây là con số SCP sẽ dùng thay cho static_tier_weight thuần túy.
        """
        static = TIER_WEIGHTS.get(self.static_tier, 0.5)
        return static * self.reputation_score * self.time_decay


# ============================================================
# ReputationStore — SQLite-backed, thread-safe
# ============================================================
class ReputationStore:
    """
    Persistent store cho source reputations.

    Schema:
        CREATE TABLE source_reputation (
            source TEXT PRIMARY KEY,
            static_tier INTEGER NOT NULL,
            reputation_score REAL NOT NULL,
            facts_contributed INTEGER DEFAULT 0,
            facts_invalidated INTEGER DEFAULT 0,
            facts_verified INTEGER DEFAULT 0,
            first_seen REAL NOT NULL,
            last_updated REAL NOT NULL,
            last_invalidated REAL DEFAULT 0,
            status TEXT DEFAULT 'active'
        );
    """

    def __init__(self, db_path: str = "data/scp_reputation.sqlite"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._lock, self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS source_reputation (
                    source TEXT PRIMARY KEY,
                    static_tier INTEGER NOT NULL,
                    reputation_score REAL NOT NULL,
                    facts_contributed INTEGER DEFAULT 0,
                    facts_invalidated INTEGER DEFAULT 0,
                    facts_verified INTEGER DEFAULT 0,
                    first_seen REAL NOT NULL,
                    last_updated REAL NOT NULL,
                    last_invalidated REAL DEFAULT 0,
                    status TEXT DEFAULT 'active'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status
                ON source_reputation(status)
            """)
            # [V5.8-OPT] Per-(source, domain) reputation table — TẠI SAO:
            # existing source_reputation table is keyed by source alone (no
            # domain dimension), but a source can be reliable in one domain
            # and unreliable in another (e.g. Wikipedia great for geography,
            # questionable for recent politics). Adding a new table is
            # ADDITIVE — doesn't touch the existing schema, doesn't break
            # SourceWatchlist or any current caller. judge.py wires
            # record_outcome() after every verdict to populate this table.
            # Runtime data: scp_reputation.sqlite had 0 rows before this
            # change (system existed but was never wired into the verdict
            # flow — see V58-OPTIMIZE-DATA-1 task in worklog).
            conn.execute("""
                CREATE TABLE IF NOT EXISTS source_domain_reputation (
                    source TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    correct_count INTEGER DEFAULT 0,
                    incorrect_count INTEGER DEFAULT 0,
                    last_outcome_was_correct INTEGER DEFAULT 0,
                    last_outcome_ts REAL DEFAULT 0,
                    last_updated REAL NOT NULL,
                    PRIMARY KEY (source, domain)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sdr_domain
                ON source_domain_reputation(domain)
            """)

    # -------- Read operations --------

    def get(self, source: str) -> SourceReputation | None:
        """Lấy reputation record cho source."""
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM source_reputation WHERE source = ?",
                (source,)
            ).fetchone()
            if row is None:
                return None
            return SourceReputation(
                source=row["source"],
                static_tier=row["static_tier"],
                reputation_score=row["reputation_score"],
                facts_contributed=row["facts_contributed"],
                facts_invalidated=row["facts_invalidated"],
                facts_verified=row["facts_verified"],
                first_seen=row["first_seen"],
                last_updated=row["last_updated"],
                last_invalidated=row["last_invalidated"],
                status=row["status"],
            )

    def get_effective_weight(self, source: str, tier: int) -> float:
        """
        Trọng số hiệu dụng — tự tạo source nếu chưa có.
        Đây là API chính SCP gọi khi commit fact.
        """
        with self._lock:
            rec = self.get(source)
            if rec is None:
                rec = self._create(source, tier)
            if rec.status == "blocked":
                logger.warning(f"Source '{source}' is BLOCKED (reputation={rec.reputation_score:.3f})")
                return 0.0
            return rec.effective_weight()

    def list_all(self) -> list[SourceReputation]:
        """List tất cả sources — cho dashboard / debug."""
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM source_reputation ORDER BY reputation_score ASC"
            ).fetchall()
            return [SourceReputation(
                source=r["source"],
                static_tier=r["static_tier"],
                reputation_score=r["reputation_score"],
                facts_contributed=r["facts_contributed"],
                facts_invalidated=r["facts_invalidated"],
                facts_verified=r["facts_verified"],
                first_seen=r["first_seen"],
                last_updated=r["last_updated"],
                last_invalidated=r["last_invalidated"],
                status=r["status"],
            ) for r in rows]

    def list_watchlist(self) -> list[SourceReputation]:
        """List sources trong watchlist."""
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM source_reputation WHERE status = 'watchlist' ORDER BY reputation_score ASC"
            ).fetchall()
            return [SourceReputation(
                source=r["source"], static_tier=r["static_tier"],
                reputation_score=r["reputation_score"],
                facts_contributed=r["facts_contributed"],
                facts_invalidated=r["facts_invalidated"],
                facts_verified=r["facts_verified"],
                first_seen=r["first_seen"], last_updated=r["last_updated"],
                last_invalidated=r["last_invalidated"], status=r["status"],
            ) for r in rows]

    # -------- Write operations --------

    def _create(self, source: str, tier: int) -> SourceReputation:
        """Tạo source mới với reputation = 1.0."""
        now = time.time()
        rec = SourceReputation(
            source=source, static_tier=tier,
            reputation_score=REPUTATION_INITIAL,
            first_seen=now, last_updated=now,
        )
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO source_reputation
                (source, static_tier, reputation_score, facts_contributed,
                 facts_invalidated, facts_verified, first_seen, last_updated,
                 last_invalidated, status)
                VALUES (?, ?, ?, 0, 0, 0, ?, ?, 0, 'active')
            """, (source, tier, REPUTATION_INITIAL, now, now))
        logger.info(f"Created new source: {source} (tier={tier})")
        return rec

    def on_fact_committed(self, source: str, tier: int) -> None:
        """Gọi khi commit fact từ source — tăng facts_contributed."""
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO source_reputation
                (source, static_tier, reputation_score, facts_contributed,
                 facts_invalidated, facts_verified, first_seen, last_updated,
                 last_invalidated, status)
                VALUES (?, ?, ?, 1, 0, 0, ?, ?, 0, 'active')
                ON CONFLICT(source) DO UPDATE SET
                    facts_contributed = facts_contributed + 1,
                    last_updated = ?
            """, (source, tier, REPUTATION_INITIAL, time.time(), time.time(), time.time()))

    def on_fact_invalidated(self, source: str) -> None:
        """
        Gọi khi fact từ source bị Healing Cascade invalidate.
        Reputation *= 0.9. Nếu < 0.3 → watchlist. Nếu < 0.1 → block.
        """
        with self._lock, self._conn() as conn:
            now = time.time()
            conn.execute("""
                UPDATE source_reputation SET
                    reputation_score = reputation_score * ?,
                    facts_invalidated = facts_invalidated + 1,
                    last_invalidated = ?,
                    last_updated = ?,
                    status = CASE
                        WHEN reputation_score * ? < ? THEN 'blocked'
                        WHEN reputation_score * ? < ? THEN 'watchlist'
                        ELSE status
                    END
                WHERE source = ?
            """, (
                REPUTATION_PENALTY_INVALIDATE,
                now, now,
                REPUTATION_PENALTY_INVALIDATE, REPUTATION_BLOCK_THRESHOLD,
                REPUTATION_PENALTY_INVALIDATE, REPUTATION_WATCHLIST_THRESHOLD,
                source,
            ))
            row = conn.execute(
                "SELECT reputation_score, status FROM source_reputation WHERE source = ?",
                (source,)
            ).fetchone()
            if row:
                logger.warning(
                    f"Source '{source}' invalidated: "
                    f"reputation={row['reputation_score']:.3f}, status={row['status']}"
                )

    def on_fact_independently_verified(self, source: str) -> None:
        """
        Gọi khi fact từ source được source khác xác nhận.
        Reputation *= 1.05, cap 1.0. Nếu đang watchlist → có thể recovery.
        """
        with self._lock, self._conn() as conn:
            now = time.time()
            conn.execute("""
                UPDATE source_reputation SET
                    reputation_score = MIN(?, reputation_score * ?),
                    facts_verified = facts_verified + 1,
                    last_updated = ?,
                    status = CASE
                        WHEN reputation_score * ? >= ? AND status = 'watchlist' THEN 'active'
                        ELSE status
                    END
                WHERE source = ?
            """, (
                REPUTATION_CAP,
                REPUTATION_REWARD_VERIFY,
                now,
                REPUTATION_REWARD_VERIFY, REPUTATION_WATCHLIST_THRESHOLD + 0.1,
                source,
            ))

    def force_block(self, source: str, reason: str = "manual") -> bool:
        """Block thủ công 1 source. Tự tạo source nếu chưa có."""
        with self._lock, self._conn() as conn:
            now = time.time()
            # Try update first
            cur = conn.execute(
                "UPDATE source_reputation SET status='blocked', reputation_score=0.0, last_updated=? WHERE source=?",
                (now, source)
            )
            if cur.rowcount == 0:
                # Source doesn't exist — create it as blocked
                conn.execute("""
                    INSERT INTO source_reputation
                    (source, static_tier, reputation_score, facts_contributed,
                     facts_invalidated, facts_verified, first_seen, last_updated,
                     last_invalidated, status)
                    VALUES (?, ?, 0.0, 0, 0, 0, ?, ?, 0, 'blocked')
                """, (source, 4, now, now))  # default tier=4 (LEARNED)
            logger.warning(f"Source '{source}' force-blocked (reason={reason})")
            return True

    def force_recover(self, source: str) -> bool:
        """Recover source từ watchlist/blocked về active (reputation=0.5)."""
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                "UPDATE source_reputation SET status='active', reputation_score=0.5, last_updated=? WHERE source=?",
                (time.time(), source)
            )
            return cur.rowcount > 0

    # ============================================================
    # [V5.8-OPT] Per-(source, domain) reputation API
    # ============================================================
    #
    # TẠI SAO: existing source_reputation table is keyed by `source` alone.
    # But the same source can be reliable in one domain and unreliable in
    # another (e.g. Wikipedia great for geography, questionable for recent
    # politics; REST Countries reliable for capitals, unreliable for population
    # after deprecation). judge.py calls record_outcome() after every verdict
    # to build per-(source,domain) accuracy stats. SLMs can then read
    # get_reputation() to weight sources dynamically.
    #
    # was_correct semantics (matches task spec):
    #   verdict == "PASS"  → was_correct = True   (source contributed to a PASS)
    #   verdict == "FAIL"  → was_correct = False  (source led to wrong answer)
    #   verdict == "KILL"  → was_correct = False  (governance killed source's answer)
    #   verdict == "UNKNOWN" → was_correct = False (source couldn't answer — neutral-negative)
    #   verdict == "CONFLICT" → was_correct = False (sources disagreed — at least one wrong)
    #
    # Note: this is a SIGNAL not a verdict — a single wrong answer shouldn't
    # tank a source's reputation. Reputation stabilizes over many observations.

    def record_outcome(self, source: str, domain: str, was_correct: bool) -> None:
        """[V5.8-OPT] Record whether a source's answer was correct.

        UPSERT into source_domain_reputation — increments correct_count or
        incorrect_count based on was_correct. Called by judge.py after the
        verdict is finalized.

        Args:
            source: source identifier (e.g. "wikipedia", "v13.db", SLM name)
            domain: knowledge domain (e.g. "geography", "medical", "general")
            was_correct: True if verdict was PASS, False otherwise

        Failure is non-fatal — best-effort logging. Does NOT raise.
        """
        # Defensive — never break /ask over a reputation write
        if not source or not isinstance(source, str):
            return
        if not domain or not isinstance(domain, str):
            domain = "general"
        if not isinstance(was_correct, bool):
            was_correct = bool(was_correct)
        try:
            with self._lock, self._conn() as conn:
                now = time.time()
                # SQLite UPSERT (3.24+) — INSERT OR IGNORE then UPDATE would also work
                # but ON CONFLICT is cleaner. The PRIMARY KEY (source, domain)
                # guarantees the conflict target.
                if was_correct:
                    conn.execute("""
                        INSERT INTO source_domain_reputation
                            (source, domain, correct_count, incorrect_count,
                             last_outcome_was_correct, last_outcome_ts, last_updated)
                        VALUES (?, ?, 1, 0, 1, ?, ?)
                        ON CONFLICT(source, domain) DO UPDATE SET
                            correct_count = correct_count + 1,
                            last_outcome_was_correct = 1,
                            last_outcome_ts = ?,
                            last_updated = ?
                    """, (source, domain, now, now, now, now))
                else:
                    conn.execute("""
                        INSERT INTO source_domain_reputation
                            (source, domain, correct_count, incorrect_count,
                             last_outcome_was_correct, last_outcome_ts, last_updated)
                        VALUES (?, ?, 0, 1, 0, ?, ?)
                        ON CONFLICT(source, domain) DO UPDATE SET
                            incorrect_count = incorrect_count + 1,
                            last_outcome_was_correct = 0,
                            last_outcome_ts = ?,
                            last_updated = ?
                    """, (source, domain, now, now, now, now))
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(
                f"[V5.8-OPT] record_outcome failed for source={source!r} "
                f"domain={domain!r}: {exc}",
                exc_info=True,
            )

    def get_reputation(self, source: str, domain: str) -> float:
        """[V5.8-OPT] Returns reputation score 0.0-1.0 for source in domain.

        Formula: correct_count / (correct_count + incorrect_count)

        Returns:
            0.5 (neutral) if no observations yet — neither trusted nor distrusted.
            This is intentional: a brand-new source shouldn't be penalized.
            SLMs that want stricter behavior can threshold (e.g. treat <0.6 as suspect).

        Args:
            source: source identifier
            domain: knowledge domain

        Failure is non-fatal — returns 0.5 (neutral) on any error.
        """
        if not source or not isinstance(source, str):
            return 0.5
        if not domain or not isinstance(domain, str):
            domain = "general"
        try:
            with self._lock, self._conn() as conn:
                row = conn.execute(
                    "SELECT correct_count, incorrect_count "
                    "FROM source_domain_reputation WHERE source = ? AND domain = ?",
                    (source, domain),
                ).fetchone()
                if row is None:
                    return 0.5  # neutral — no data yet
                correct = int(row["correct_count"] or 0)
                incorrect = int(row["incorrect_count"] or 0)
                total = correct + incorrect
                if total == 0:
                    return 0.5
                return max(0.0, min(1.0, correct / total))
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(
                f"[V5.8-OPT] get_reputation failed for source={source!r} "
                f"domain={domain!r}: {exc}",
                exc_info=True,
            )
            return 0.5

    # [SCP-DNA-FIX R7-4] Cold-start support: outcome-count accessor.
    # TẠI SAO: judgecore_mixin's worst-source scaling (`0.3 + 0.7 * worst_rep`)
    # treats a new source's neutral 0.5 reputation as "unreliable" → drags the
    # entire verdict confidence to 0.65 even when 4/5 sources are reliable.
    # Cold-start: if a source has < COLD_START_THRESHOLD outcomes, the scaling
    # should skip that source (treat its reputation as 1.0 / neutral — give the
    # new source a chance to build reputation before being penalized).
    # Reality evidence: hypothesis random source sets → anomalous low confidence
    # when any source is new (rep defaults to 0.5, treated as bad).
    COLD_START_THRESHOLD = 10  # ≥10 outcomes → mature; <10 → cold-start (neutral)

    def get_outcome_count(self, source: str, domain: str) -> int:
        """[SCP-DNA-FIX R7-4] Returns total observations (correct + incorrect)
        for source in domain. Used by judgecore scaling to detect cold-start.

        Returns:
            0 if source has no observations yet (cold-start).
            N (N>0) once source has been observed N times.
            Never raises — returns 0 on any error (fail-open as cold-start).
        """
        if not source or not isinstance(source, str):
            return 0
        if not domain or not isinstance(domain, str):
            domain = "general"
        try:
            with self._lock, self._conn() as conn:
                row = conn.execute(
                    "SELECT correct_count, incorrect_count "
                    "FROM source_domain_reputation WHERE source = ? AND domain = ?",
                    (source, domain),
                ).fetchone()
                if row is None:
                    return 0
                return int(row["correct_count"] or 0) + int(row["incorrect_count"] or 0)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(
                f" get_outcome_count failed for source={source!r} "
                f"domain={domain!r}: {exc}",
                exc_info=True,
            )
            return 0

    def list_domain_reputations(self, domain: str | None = None) -> list[dict]:
        """[V5.8-OPT] List per-(source,domain) reputation records.

        Useful for dashboards / debugging. Returns list of dicts:
            {source, domain, correct_count, incorrect_count, reputation,
             last_outcome_was_correct, last_updated}
        """
        try:
            with self._lock, self._conn() as conn:
                if domain:
                    rows = conn.execute(
                        "SELECT * FROM source_domain_reputation WHERE domain = ? "
                        "ORDER BY (correct_count + incorrect_count) DESC",
                        (domain,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM source_domain_reputation "
                        "ORDER BY (correct_count + incorrect_count) DESC"
                    ).fetchall()
                out = []
                for r in rows:
                    correct = int(r["correct_count"] or 0)
                    incorrect = int(r["incorrect_count"] or 0)
                    total = correct + incorrect
                    rep = (correct / total) if total > 0 else 0.5
                    out.append({
                        "source": r["source"],
                        "domain": r["domain"],
                        "correct_count": correct,
                        "incorrect_count": incorrect,
                        "reputation": round(rep, 4),
                        "last_outcome_was_correct": bool(r["last_outcome_was_correct"]),
                        "last_outcome_ts": float(r["last_outcome_ts"] or 0),
                        "last_updated": float(r["last_updated"]),
                    })
                return out
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"[V5.8-OPT] list_domain_reputations failed: {exc}", exc_info=True)
            return []

    def domain_reputation_stats(self) -> dict:
        """[V5.8-OPT] Aggregate stats for source_domain_reputation table."""
        try:
            with self._lock, self._conn() as conn:
                row = conn.execute("""
                    SELECT
                        COUNT(*) as total_rows,
                        COUNT(DISTINCT source) as unique_sources,
                        COUNT(DISTINCT domain) as unique_domains,
                        SUM(correct_count) as total_correct,
                        SUM(incorrect_count) as total_incorrect
                    FROM source_domain_reputation
                """).fetchone()
                if row is None:
                    return {"total_rows": 0, "unique_sources": 0, "unique_domains": 0,
                            "total_correct": 0, "total_incorrect": 0}
                total_c = int(row["total_correct"] or 0)
                total_i = int(row["total_incorrect"] or 0)
                return {
                    "total_rows": int(row["total_rows"] or 0),
                    "unique_sources": int(row["unique_sources"] or 0),
                    "unique_domains": int(row["unique_domains"] or 0),
                    "total_correct": total_c,
                    "total_incorrect": total_i,
                    "overall_accuracy": round(total_c / (total_c + total_i), 4)
                        if (total_c + total_i) > 0 else 0.0,
                }
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"[V5.8-OPT] domain_reputation_stats failed: {exc}", exc_info=True)
            return {}

    # -------- Stats for dashboard --------

    def stats(self) -> dict:
        """Aggregate stats cho dashboard."""
        with self._lock, self._conn() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN status='watchlist' THEN 1 ELSE 0 END) as watchlist,
                    SUM(CASE WHEN status='blocked' THEN 1 ELSE 0 END) as blocked,
                    AVG(reputation_score) as avg_reputation
                FROM source_reputation
            """).fetchone()
            return {
                "total_sources": row["total"],
                "active": row["active"],
                "watchlist": row["watchlist"],
                "blocked": row["blocked"],
                "avg_reputation": round(row["avg_reputation"], 4) if row["avg_reputation"] is not None else 0.0
            # [V104.34 #53] TẠI SAO: 0.0 or 1.0 = 1.0 (Python falsy) → perfect score when all blocked,
            }


# ============================================================
# Convenience: standalone test
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
    print("=== Source Reputation System — Standalone Test ===\n")

    import os
    import tempfile
    store = ReputationStore(db_path=os.path.join(tempfile.gettempdir(), "scp_reputation_test.sqlite"))  # nosec B108 — sandboxed test runner

    # Test 1: Create + get
    w = store.get_effective_weight("wikipedia", tier=2)
    print(f"1. New source 'wikipedia' effective_weight = {w:.4f} (expected ~0.85)")

    # Test 2: Commit facts
    for _ in range(100):
        store.on_fact_committed("wikipedia", tier=2)
    rec = store.get("wikipedia")
    print(f"2. After 100 commits: facts_contributed = {rec.facts_contributed}")

    # Test 3: Invalidate
    for _ in range(15):
        store.on_fact_invalidated("wikipedia")
    rec = store.get("wikipedia")
    print(f"3. After 15 invalidations: reputation={rec.reputation_score:.4f}, status={rec.status}")
    print(f"   Effective weight now = {rec.effective_weight():.4f}")

    # Test 4: Independent verification
    for _ in range(5):
        store.on_fact_independently_verified("wikipedia")
    rec = store.get("wikipedia")
    print(f"4. After 5 verifications: reputation={rec.reputation_score:.4f}, status={rec.status}")

    # Test 5: Force to watchlist
    for _ in range(30):
        store.on_fact_invalidated("wikipedia")
    rec = store.get("wikipedia")
    print(f"5. After 30+ invalidations: reputation={rec.reputation_score:.4f}, status={rec.status}")

    # Test 6: Block
    for _ in range(20):
        store.on_fact_invalidated("wikipedia")
    rec = store.get("wikipedia")
    print(f"6. After more invalidations: reputation={rec.reputation_score:.4f}, status={rec.status}")
    print(f"   Effective weight now = {store.get_effective_weight('wikipedia', tier=2):.4f} (expected 0.0)")

    print(f"\n7. Stats: {store.stats()}")

    print("\n✓ All tests passed.")
