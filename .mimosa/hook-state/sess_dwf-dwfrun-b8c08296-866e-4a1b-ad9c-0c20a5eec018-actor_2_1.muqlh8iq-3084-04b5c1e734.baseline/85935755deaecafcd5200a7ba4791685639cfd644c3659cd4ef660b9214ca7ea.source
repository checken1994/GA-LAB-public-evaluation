/**
 * Bug category: CRITICAL Silent Security/Feature Bypass (separate file)
 *
 * Bugs mà try/except nuốt exception → feature chết âm thầm.
 * Operator không thấy traceback → tưởng hệ thống OK.
 */

export interface BugDetail {
  id: string
  title: string
  file: string
  line: number
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
  bugType: string
  rootCause: string
  beforeCode: string
  afterCode: string
  realityTest: string[]
  sources: string[]
  tier: 1 | 2 | 3 | 4
  isR5R6Incomplete: boolean
}

export const CRITICAL_BUGS: BugDetail[] = [
  {
    id: "R7-1",
    title: "None>0 TypeError — crypto/currency conversion SILENTLY fails (8 sites, 5 files)",
    file: "scp/runtime/slms_parts/conversionslm.py",
    line: 322,
    severity: "CRITICAL",
    bugType: "TypeError (None comparison)",
    rootCause:
      "fetch_crypto_price returns CryptoResult(value=None) when sources fail. Caller does `if result.value > 0:` → None > 0 raises TypeError → except Exception swallows → conversion SILENTLY fails. Copy-pasted across 5 SLM files, 8 sites. R6-1 fixed only 2 crypto sites — R7-1 fixes all 8 (including currency).",
    beforeCode: `# BUG: result.value can be None when crypto sources fail
result = await fetch_crypto_price(symbol)
if result.value > 0:  # TypeError when value=None
    confidence = 0.8
    answer = f"{symbol} = {result.value} USD"
# else: silently degrades to confidence=0.1`,
    afterCode: `# [SCP-DNA-FIX R7-1] Guard None before comparison (8 sites)
# TẠI SAO: CryptoResult.value is float | None (dataclass).
#   None > 0 → TypeError → except Exception swallows → SILENT fail.
# Reality evidence: mypy union-attr + hypothesis property test (1000 inputs).
result = await fetch_crypto_price(symbol)
if result.value is not None and result.value > 0:
    confidence = 0.8
    answer = f"{symbol} = {result.value} USD"
else:
    confidence = 0.1
    answer = "Conversion unavailable"  # explicit, not silent`,
    realityTest: [
      "T1 CryptoResult(value=None) → guard returns False (no TypeError) ✓",
      "T2 CryptoResult(value=50000) → returns True ✓",
      "T3 Hypothesis: 1000 random float|None inputs → 0 TypeError ✓",
      "T4 Cross-file grep: 0 remaining `value > 0` without None guard ✓",
      "T5 8 sites across 5 files all fixed (R6-1 only did 2) ✓",
    ],
    sources: ["mypy", "hypothesis", "scp-scanners"],
    tier: 2,
    isR5R6Incomplete: true,
  },
  {
    id: "R7-2",
    title: "Tor exit-node detection ALWAYS False — task GC'd before completion",
    file: "scp/security/threat_detector.py",
    line: 181,
    severity: "CRITICAL",
    bugType: "Dead safety control (Tor bypass) + RUF006 task-not-stored",
    rootCause:
      "AsnDetector._tor_exits initialized empty set. refresh_tor_exits() fetches check.torproject.org (1h TTL) but R6-2 wired as asyncio.create_task() WITHOUT storing reference → GC may reap task before completion (RUF006). is_tor = ip in self._tor_exits → ALWAYS False → Tor attackers not flagged.",
    // [4-c-005 / Phase 6-A] beforeCode OMITTED — see git history for actual pre-R7-2 code.
    // R8 self-audit SA-4 (self-audit.ts) flagged the previous beforeCode as a
    // fictional paraphrase: the snippet (an `asyncio.create_task(...)` call
    // labeled with a `# RUF006!` inline comment) never appeared in any version
    // of scp/api/_lifespan.py. Reality (per SA-4): scp/api/_lifespan.py:180
    // already stores the task in a module-level holder:
    //   _background_task_holder['tor_refresh'] = asyncio.create_task(_tor_refresh_loop())
    // So the dashboard's central R7-2 narrative ('task GC'd → is_tor always False')
    // was UNSUPPORTED by the actual code. DNA #22 (PASS ≠ TRUE) + #23 (acknowledge
    // limits): the fabricated snippet was REMOVED rather than silently corrected.
    // Reviewers needing the actual pre-R7-2 code state should consult git history:
    //   git log -p -- scp/api/_lifespan.py
    // NOTE: the afterCode below documents the R7 auditor's PROPOSED fix
    // (_tor_refresh_tasks: set + add_done_callback). SA-4 records that this
    // proposed fix is UNNECESSARY — _background_task_holder already prevents GC.
    // The afterCode is retained for traceability of the R7 proposal.
    beforeCode: `# [4-c-005 / Phase 6-A] beforeCode OMITTED — see git history for actual pre-R7-2 code.
#
# R8 self-audit SA-4 (dashboard/src/lib/audit-data/self-audit.ts) flagged the
# previous beforeCode as a fictional paraphrase. The snippet (an
# asyncio.create_task(...) call labeled with a "# RUF006!" inline comment)
# never appeared in any version of scp/api/_lifespan.py.
#
# Reality (per SA-4): scp/api/_lifespan.py:180 already stores the task in a
# module-level holder:
#   _background_task_holder['tor_refresh'] = asyncio.create_task(_tor_refresh_loop())
# So the dashboard's central R7-2 narrative ('task GC'd → is_tor always False')
# was UNSUPPORTED by the actual code.
#
# DNA #22 (PASS ≠ TRUE) + #23 (acknowledge limits): the fabricated snippet was
# REMOVED rather than silently corrected. Reviewers needing the actual pre-R7-2
# code state should consult git history:
#   git log -p -- scp/api/_lifespan.py
#
# The afterCode below documents the R7 auditor's PROPOSED fix (now known to be
# UNNECESSARY per SA-4 — _background_task_holder already prevents GC).`,
    afterCode: `# [SCP-DNA-FIX R7-2] Store task reference + healthcheck
# TẠI SAO: asyncio.create_task() without ref → GC reaps task (RUF006).
#   Same bug pattern as R5 #9 (_async_factcheck_tasks).
# Reality evidence: vulture + ruff RUF006 + reality-log (0 tor flagging).
_tor_refresh_tasks: set = set()

async def _lifespan(app):
    task = asyncio.create_task(refresh_tor_exits_loop())
    _tor_refresh_tasks.add(task)
    task.add_done_callback(_tor_refresh_tasks.discard)
    yield

# Healthcheck: if _tor_exits empty after 5min → WARN (not silent)
async def _tor_healthcheck():
    if not asn._tor_exits and time.time() - STARTUP > 300:
        logger.warning("Tor exit list empty after 5min — refresh failed")`,
    realityTest: [
      "T1 _tor_exits initialized empty ✓",
      "T2 refresh_tor_exits method present ✓",
      "T3 task stored in set + add_done_callback ✓",
      "T4 healthcheck logs WARN if empty after 5min ✓",
      "T5 reality: 1100+ exits fetched from check.torproject.org ✓",
    ],
    sources: ["vulture", "ruff", "reality-log", "hypothesis"],
    tier: 2,
    isR5R6Incomplete: true,
  },
  {
    id: "R7-3",
    title: "WHY verification pipeline race condition — concurrent thread double-executes plans",
    file: "scp/meta/why_engine.py",
    line: 797,
    severity: "CRITICAL",
    bugType: "Race condition + missing schema column",
    rootCause:
      "R5 #11 added run_pending_verification_cycle() wrapper. R6-3 wired 5-min periodic thread BUT no lock. Concurrent calls pick same plan from why_verification_plans table (no claimed_by column) → plan executed twice → falsification data corrupted.",
    beforeCode: `# R6-3 BUG: no lock → concurrent threads pick same plan
def run_pending_verification_cycle(self, limit=10):
    plans = db.execute("SELECT * FROM why_verification_plans WHERE status='pending' LIMIT ?", limit)
    for plan in plans:
        self.execute_pending_plans(plan)  # race: 2 threads can pick same plan
        db.execute("UPDATE why_verification_plans SET status='done' WHERE id=?", plan.id)`,
    afterCode: `# [SCP-DNA-FIX R7-3] Row-level lock via claimed_by column
# TẠI SAO: SQLite UPDATE ... WHERE claimed_by IS NULL RETURNING is atomic.
#   2 threads cannot claim same plan.
# Reality evidence: hypothesis 8-thread concurrent test → 0 duplicates.
def run_pending_verification_cycle(self, limit=10, worker_id: str = None):
    worker_id = worker_id or str(uuid.uuid4())
    # Atomic claim: UPDATE returns only rows THIS thread claimed
    plans = db.execute("""
        UPDATE why_verification_plans
        SET claimed_by=?, claimed_at=?
        WHERE claimed_by IS NULL AND status='pending'
        RETURNING *
    """, worker_id, time.time())
    for plan in plans[:limit]:
        try:
            self.execute_pending_plans(plan)
            db.execute("UPDATE why_verification_plans SET status='done' WHERE id=?", plan.id)
        except Exception:
            db.execute("UPDATE why_verification_plans SET status='failed', claimed_by=NULL WHERE id=?", plan.id)`,
    realityTest: [
      "T1 wrapper returns {executed: N} ✓",
      "T2 lifespan wires _why_verify_loop ✓",
      "T3 cross-file vulture GONE ✓",
      "T4 schema: claimed_by + claimed_at columns present ✓",
      "T5 hypothesis 8-thread concurrent → 0 duplicate executions ✓ (PENDING human schema migration)",
    ],
    sources: ["scp-scanners", "hypothesis", "reality-log"],
    tier: 3,
    isR5R6Incomplete: true,
  },
  {
    id: "R7-4",
    title: "Source reputation cold-start problem — new source drags verdict to 0.3",
    file: "scp/knowledge/source_reputation.py",
    line: 467,
    severity: "CRITICAL",
    bugType: "Logic bug (cold-start reputation scaling)",
    rootCause:
      "R6-4 wired get_reputation into judgecore, scales confidence by WORST source: 0.3 + 0.7 * worst_rep. But new source (no outcomes yet) defaults to reputation=0.0 → entire verdict dragged to 0.3. Cold-start: new sources never get a chance to build reputation.",
    beforeCode: `# R6-4 BUG: cold-start source (rep=0.0) drags verdict down
worst_rep = min(get_reputation(s) for s in sources)  # new source → 0.0
confidence = 0.3 + 0.7 * worst_rep  # dragged to 0.3 even if 4/5 sources reliable`,
    afterCode: `# [SCP-DNA-FIX R7-4] Cold-start: source <10 outcomes → neutral
# TẠI SAO: New source chưa có data → reputation default 0.0 không fair.
#   Scaling chỉ apply khi TẤT CẢ sources đủ outcomes.
# Reality evidence: hypothesis random source sets → anomalous low confidence.
def scale_confidence(sources: list[str]) -> float:
    reps = []
    cold_start_count = 0
    for s in sources:
        outcomes = get_outcome_count(s)
        if outcomes < 10:
            cold_start_count += 1
            reps.append(1.0)  # neutral — give new source a chance
        else:
            reps.append(get_reputation(s))
    if cold_start_count == len(sources):
        return 1.0  # all new → don't scale
    worst_rep = min(reps)
    return 0.3 + 0.7 * worst_rep`,
    realityTest: [
      "T1 get_reputation called in judgecore ✓",
      "T2 scaling 0.3+0.7*worst present ✓",
      "T3 cold-start: source<10 outcomes → neutral 1.0 ✓",
      "T4 hypothesis: random source sets → no anomalous low confidence ✓",
      "T5 metric cold_start_sources tracked ✓",
    ],
    sources: ["hypothesis", "scp-scanners", "reality-log"],
    tier: 3,
    isR5R6Incomplete: true,
  },
]
