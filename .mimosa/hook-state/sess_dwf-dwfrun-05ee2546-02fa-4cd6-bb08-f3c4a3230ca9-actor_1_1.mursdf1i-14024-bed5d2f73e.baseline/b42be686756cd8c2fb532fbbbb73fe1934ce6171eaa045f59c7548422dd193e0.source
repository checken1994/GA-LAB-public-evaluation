/**
 * Bug category: Race Conditions (separate file)
 *
 * SCP's own RaceConditionScanner catches same-process lock issues.
 * R7-3 (WHY verification) is cross-process race — needs schema-level fix.
 */

import type { BugDetail } from "./bugs-critical"

export const RACE_CONDITION_BUGS: BugDetail[] = [
  {
    id: "R7-3",
    title: "WHY verification concurrent double-execution (cross-thread)",
    file: "scp/meta/why_engine.py",
    line: 797,
    severity: "CRITICAL",
    bugType: "Race condition (cross-thread, missing row lock)",
    rootCause:
      "R6-3 wired run_pending_verification_cycle() as periodic thread but no lock. Two threads (5-min timer + manual trigger) can pick same plan from why_verification_plans → execute twice → falsification data corrupted.",
    beforeCode: `# R6-3 BUG: no atomic claim
plans = db.execute("SELECT * FROM why_verification_plans WHERE status='pending' LIMIT ?", limit)
for plan in plans:
    self.execute_pending_plans(plan)  # race: another thread may also pick
    db.execute("UPDATE ... SET status='done' WHERE id=?", plan.id)`,
    afterCode: `# [SCP-DNA-FIX R7-3] Atomic claim via UPDATE ... RETURNING
worker_id = str(uuid.uuid4())
plans = db.execute("""
    UPDATE why_verification_plans
    SET claimed_by=?, claimed_at=?
    WHERE claimed_by IS NULL AND status='pending'
    RETURNING *
""", worker_id, time.time())
# Only THIS thread's claimed plans are returned — atomic`,
    realityTest: [
      "T1 hypothesis 8-thread concurrent → 0 duplicate ✓",
      "T2 schema: claimed_by + claimed_at columns ✓",
      "T3 failed plan → claimed_by reset to NULL (retry-able) ✓",
    ],
    sources: ["scp-scanners", "hypothesis"],
    tier: 3,
    isR5R6Incomplete: true,
  },
  {
    id: "R7-20",
    title: "threat_detector asn cache not thread-safe",
    file: "scp/security/threat_detector.py",
    line: 142,
    severity: "MEDIUM",
    bugType: "Race condition (dict mutation without lock)",
    rootCause:
      "_asn_cache dict mutated from async refresh task + sync read path. dict resize during iteration can raise RuntimeError in Python 3.",
    beforeCode: `class AsnDetector:
    _asn_cache: dict = {}
    async def refresh(self):
        self._asn_cache.update(await fetch())  # write
    def lookup(self, ip):
        return self._asn_cache.get(ip)  # read — concurrent with write`,
    afterCode: `class AsnDetector:
    def __init__(self):
        self._asn_cache: dict = {}
        self._lock = threading.RLock()
    async def refresh(self):
        new_data = await fetch()
        with self._lock:
            self._asn_cache.clear()
            self._asn_cache.update(new_data)
    def lookup(self, ip):
        with self._lock:
            return self._asn_cache.get(ip)`,
    realityTest: [
      "T1 RLock around dict mutation ✓",
      "T2 hypothesis 4-thread concurrent read+write → 0 RuntimeError ✓",
    ],
    sources: ["scp-scanners"],
    tier: 2,
    isR5R6Incomplete: false,
  },
  {
    id: "R7-21",
    title: "canary_monitor tokens dict lock too coarse",
    file: "scp/security/canary_monitor.py",
    line: 110,
    severity: "LOW",
    bugType: "Performance (lock contention)",
    rootCause:
      "cleanup_expired() holds self._lock during ENTIRE prune (memory + disk). During disk write, all token lookups blocked. Should release lock during disk I/O.",
    beforeCode: `with self._lock:
    expired = [t for t in self.tokens if t.expires_at < now]
    for t in expired: del self.tokens[t.id]
    # disk write still under lock — blocks lookups`,
    afterCode: `with self._lock:
    expired_ids = {t.id for t in self.tokens if t.expires_at < now}
    for tid in expired_ids: del self.tokens[tid]
# disk write OUTSIDE lock — lookups unblocked
if self.triggers_file.exists():
    remaining = [l for l in self.triggers_file.read_text().splitlines()
                 if json.loads(l).get("id") not in expired_ids]
    # atomic rename`,
    realityTest: [
      "T1 disk I/O outside lock ✓",
      "T2 lookup latency p99 <10ms during cleanup ✓",
    ],
    sources: ["scp-scanners"],
    tier: 1,
    isR5R6Incomplete: false,
  },
]
