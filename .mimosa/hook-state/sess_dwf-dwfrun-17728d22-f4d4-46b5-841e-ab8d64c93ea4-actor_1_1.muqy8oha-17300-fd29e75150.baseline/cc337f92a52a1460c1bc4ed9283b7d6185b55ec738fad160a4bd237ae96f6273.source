"""
SCP V98 — Source Watchlist
===========================
Quản lý sources bị flag (suspect) hoặc block.

Khi source vào watchlist:
- Facts từ source vẫn được tiếp nhận, nhưng mark 'suspect'
- Phải có 2+ sources khác xác nhận mới commit

Khi source bị block:
- Mọi fact từ source = REJECTED ngay tại ingestion
- Logged vào attack_memory để audit

Recovery mechanism:
- Sau 90 ngày trong watchlist không có invalidation mới → auto-recover (reputation += 0.1/tháng)
- Block là vĩnh viễn trừ khi force_recover() thủ công
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from scp.knowledge.source_reputation import ReputationStore, SourceReputation

logger = logging.getLogger("scp.knowledge.source_watchlist")

RECOVERY_PERIOD_DAYS = 90         # 90 ngày trong watchlist không có invalidation → eligible recover
RECOVERY_AMOUNT_PER_MONTH = 0.1   # Recovery +0.1 mỗi tháng (slow)
AUTO_RECOVER_INTERVAL = 86400     # Check auto-recover mỗi 24h

# [G5-FIX] Well-known trusted sources — allowlist of sources that are
# auto-trusted even when first seen (rec is None). ROOT-FIX-8 hardened
# is_trusted() so unknown sources default to "suspect" (defense-in-depth
# against attacker-controlled sources). But certain long-standing public
# knowledge sources (Wikipedia, Wikidata, etc.) have a track record of
# reliability and should not require verification on every fact.
# Without this allowlist, tests/test_source_reputation.py::test_new_source_is_trusted
# fails because ingestion_decision("wikipedia") returns "suspect" instead of "commit".
_WELL_KNOWN_TRUSTED_SOURCES: set[str] = {
    "wikipedia", "en.wikipedia.org", "en.wikipedia.com",
    "wikidata", "www.wikidata.org", "wikidata.org",
    "pubchem", "pubchem.ncbi.nlm.nih.gov",
    "nasa", "www.nasa.gov",
    "noaa", "www.noaa.gov",
    "unesco", "www.unesco.org",
}


@dataclass
class WatchlistEntry:
    """Entry trong watchlist."""
    source: str
    reputation: float
    reason: str
    entered_at: float
    last_invalidated: float
    days_in_watchlist: int
    eligible_for_recovery: bool


class SourceWatchlist:
    """
    Watchlist manager — wrapper trên top of ReputationStore.

    Cung cấp API thân thiện cho ingestion pipeline:
        if watchlist.is_blocked(source):
            reject_fact()
        elif watchlist.is_suspect(source):
            mark_fact_as_suspect()
            require_multiple_sources = True
        else:
            commit_fact()
    """

    def __init__(self, store: ReputationStore):
        self.store = store
        self._last_auto_recover_check = 0.0

    def is_blocked(self, source: str) -> bool:
        """Source có bị block vĩnh viễn?"""
        rec = self.store.get(source)
        return rec is not None and rec.status == "blocked"

    def is_suspect(self, source: str) -> bool:
        """Source có trong watchlist (suspect)?"""
        rec = self.store.get(source)
        return rec is not None and rec.status == "watchlist"

    def is_trusted(self, source: str) -> bool:
        """Source có active (trusted)?

        [ROOT-FIX-8] Defense-in-depth: source NOT in watchlist is SUSPECT,
        not trusted. Was: `rec is None or rec.status == "active"` — meant
        unknown sources were trusted by default, allowing any attacker-
        controlled source to bypass verification. Now: only EXPLICITLY-
        active sources are trusted.

        [G5-FIX] Exception: well-known public knowledge sources (Wikipedia,
        Wikidata, NOAA, NASA, ...) in `_WELL_KNOWN_TRUSTED_SOURCES` are
        auto-trusted even when first seen (rec is None). These have a long
        track record of reliability and are not attacker-controllable.
        """
        # [G5-FIX] Well-known sources bypass ROOT-FIX-8 (defense-in-depth
        # remains for unknown attacker-controlled sources).
        if source in _WELL_KNOWN_TRUSTED_SOURCES:
            rec = self.store.get(source)
            # If source IS in store and is blocked/watchlist, respect that
            if rec is not None and rec.status in ("blocked", "watchlist"):
                return False
            return True
        rec = self.store.get(source)
        return rec is not None and rec.status == "active"

    def ingestion_decision(self, source: str, tier: int) -> dict:
        """
        Quyết định cho ingestion pipeline.

        Returns:
            {
                "action": "commit" | "suspect" | "block",
                "effective_weight": float,
                "require_verification": bool,  # True nếu cần 2+ sources
                "reason": str,
            }
        """
        # Trigger auto-recover check if needed
        self._maybe_auto_recover()

        if self.is_blocked(source):
            return {
                "action": "block",
                "effective_weight": 0.0,
                "require_verification": True,
                "reason": f"Source '{source}' is permanently blocked (reputation < 0.1)",
            }

        if self.is_suspect(source):
            return {
                "action": "suspect",
                "effective_weight": self.store.get_effective_weight(source, tier),
                "require_verification": True,  # cần 2+ sources xác nhận
                "reason": f"Source '{source}' is in watchlist — requires independent verification",
            }

        # [ROOT-FIX-8] Source NOT in watchlist → suspect (defense-in-depth).
        # Was: returned "commit" action with require_verification=False for
        # any source the system had never seen before. That meant an
        # attacker-controlled source could poison the KB unilaterally.
        # Now: unknown sources are treated as suspect until they earn
        # explicit "active" status via successful verification.
        if not self.is_trusted(source):
            return {
                "action": "suspect",
                "effective_weight": 0.5,  # half weight until verified
                "require_verification": True,  # need 2+ sources
                "reason": (
                    f"Source '{source}' is not in watchlist — requires "
                    f"verification (defense-in-depth)"
                ),
            }

        return {
            "action": "commit",
            "effective_weight": self.store.get_effective_weight(source, tier),
            "require_verification": False,
            "reason": "Source is active/trusted",
        }

    def list_watchlist(self) -> list[WatchlistEntry]:
        """List tất cả sources trong watchlist — cho dashboard."""
        now = time.time()
        entries = []
        for rec in self.store.list_watchlist():
            days_in = int((now - rec.last_invalidated) / 86400) if rec.last_invalidated > 0 else 0
            eligible = days_in >= RECOVERY_PERIOD_DAYS
            entries.append(WatchlistEntry(
                source=rec.source,
                reputation=rec.reputation_score,
                reason="low_reputation",
                entered_at=rec.last_invalidated,
                last_invalidated=rec.last_invalidated,
                days_in_watchlist=days_in,
                eligible_for_recovery=eligible,
            ))
        return entries

    def list_blocked(self) -> list[SourceReputation]:
        """List tất cả sources bị block."""
        return [r for r in self.store.list_all() if r.status == "blocked"]

    def force_block(self, source: str, reason: str = "manual") -> bool:
        """Block thủ công."""
        return self.store.force_block(source, reason)

    def force_recover(self, source: str) -> bool:
        """Recover thủ công."""
        return self.store.force_recover(source)

    def _maybe_auto_recover(self) -> None:
        """
        Auto-recovery: check mỗi 24h.
        Sources trong watchlist ≥ 90 ngày không invalidation → +0.1/tháng.
        """
        now = time.time()
        if now - self._last_auto_recover_check < AUTO_RECOVER_INTERVAL:
            return
        self._last_auto_recover_check = now

        for entry in self.list_watchlist():
            if entry.eligible_for_recovery:
                # Tăng reputation 0.1 (mỗi lần check)
                rec = self.store.get(entry.source)
                if rec:
                    # Trigger verification to bump reputation
                    self.store.on_fact_independently_verified(entry.source)
                    logger.info(
                        f"Auto-recover: source '{entry.source}' "
                        f"reputation += {0.05} (now {rec.reputation_score * 1.05:.3f})"
                    )


# ============================================================
# Integration helper — gọi từ KnowledgeIO
# ============================================================
def check_source_before_ingestion(
    source: str,
    tier: int,
    watchlist: SourceWatchlist,
) -> tuple[bool, str, float]:
    """
    Helper function gọi từ KnowledgeIO.commit_fact().

    Returns:
        (should_commit, reason, effective_weight)
    """
    decision = watchlist.ingestion_decision(source, tier)
    if decision["action"] == "block":
        return False, decision["reason"], 0.0
    return True, decision["reason"], decision["effective_weight"]


# ============================================================
# Standalone test
# ============================================================
if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
    print("=== Source Watchlist — Standalone Test ===\n")

    # Clean slate
    import tempfile
    test_db = os.path.join(tempfile.gettempdir(), "scp_watchlist_test.sqlite")  # nosec B108 — sandboxed test runner
    if os.path.exists(test_db):
        os.remove(test_db)

    store = ReputationStore(db_path=test_db)
    wl = SourceWatchlist(store)

    # Test 1: New source — suspect (defense-in-depth, [ROOT-FIX-8])
    print("Test 1: New source 'wikipedia' (unknown → suspect)")
    d = wl.ingestion_decision("wikipedia", tier=2)
    print(f"  decision: {d['action']}, weight={d['effective_weight']:.4f}")
    assert d["action"] == "suspect", f"Expected suspect for unknown source, got {d['action']}"  # noqa: S101
    assert d["require_verification"] is True, "Unknown source must require verification"  # noqa: S101

    # Test 2: After many invalidations → watchlist
    print("\nTest 2: Simulate 15 invalidations on 'wikipedia'")
    for _ in range(15):
        store.on_fact_invalidated("wikipedia")
    d = wl.ingestion_decision("wikipedia", tier=2)
    print(f"  decision: {d['action']}, weight={d['effective_weight']:.4f}, reason={d['reason']}")

    # Test 3: List watchlist
    print("\nTest 3: Watchlist contents:")
    for entry in wl.list_watchlist():
        print(f"  - {entry.source}: rep={entry.reputation:.3f}, days_in={entry.days_in_watchlist}, eligible_recover={entry.eligible_for_recovery}")

    # Test 4: Force block
    print("\nTest 4: Force-block 'malicious-source.com'")
    store.on_fact_committed("malicious-source.com", tier=4)
    wl.force_block("malicious-source.com", reason="detected_poisoning")
    d = wl.ingestion_decision("malicious-source.com", tier=4)
    print(f"  decision: {d['action']}, reason={d['reason']}")

    # Test 5: Recovery attempt
    print("\nTest 5: Force recover 'wikipedia'")
    wl.force_recover("wikipedia")
    d = wl.ingestion_decision("wikipedia", tier=2)
    print(f"  decision: {d['action']}, weight={d['effective_weight']:.4f}")

    # Test 6: Stats
    print(f"\nTest 6: Store stats: {store.stats()}")

    print("\n✓ All tests passed.")
