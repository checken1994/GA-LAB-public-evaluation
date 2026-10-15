/**
 * Bug category: Dead Safety Controls (separate file)
 *
 * Functions/methods defined but NEVER called by any runtime path.
 * "Wired-but-never-called" = Category B (vulture). R6 found 9, R7 found 14
 * (deeper Category B/C + R-fix-completeness check).
 *
 * Root cause pattern: developer adds safety control (good intent) but
 * forgets to wire it into the runtime → control exists but is decorative.
 */

import type { BugDetail } from "./bugs-critical"

export const DEAD_CONTROL_BUGS: BugDetail[] = [
  {
    id: "R7-5",
    title: "FalsificationStatus.is_skeptical() called but return value ignored",
    file: "scp/meta/falsification_engine.py",
    line: 95,
    severity: "HIGH",
    bugType: "Decorative enum method (return value discarded)",
    rootCause:
      "R6-5 wired .requires_human() and .is_skeptical() into _run_falsification. requires_human() properly escalates to Dead Man's Switch. But is_skeptical() return value only LOGGED — not stored in verdict evidence. Operators don't see which verdicts are skeptical.",
    beforeCode: `# R6-5 BUG: is_skeptical() called but return value only logged
def _run_falsification(self, claim):
    status = self._evaluate(claim)
    if status.requires_human():
        self._escalate_dead_mans_switch(claim)
    if status.is_skeptical():
        logger.info(f"Claim {claim.id} skeptical")  # LOG ONLY, not in verdict
    return verdict  # skeptical flag lost`,
    afterCode: `# [SCP-DNA-FIX R7-5] Store skeptical flag in verdict + API response
# TẠI SAO: is_skeptical() phải AFFECT verdict, không chỉ LOG.
#   Operator cần thấy verdict nào skeptical để review.
# Reality evidence: vulture GONE (method called) nhưng semantic intent scanner
#   flag return value discarded.
def _run_falsification(self, claim):
    status = self._evaluate(claim)
    if status.requires_human():
        self._escalate_dead_mans_switch(claim)
    verdict = self._build_verdict(claim)
    verdict.skeptical = status.is_skeptical()  # NEW field
    return verdict

# JudgeVerdict dataclass:
@dataclass
class JudgeVerdict:
    final_answer: str
    confidence: float
    skeptical: bool = False  # NEW (backward compat, default False)`,
    realityTest: [
      "T1 FS('HUMAN_DECISION_REQUIRED').requires_human()==True ✓",
      "T2 FS('PATTERN_MATCHED').is_skeptical()==False ✓",
      "T3 verdict.skeptical field present (default False) ✓",
      "T4 API response includes skeptical: true when set ✓",
      "T5 cross-file vulture GONE ✓",
    ],
    sources: ["scp-scanners", "vulture"],
    tier: 2,
    isR5R6Incomplete: true,
  },
  {
    id: "R7-6",
    title: "ingestion_decision() called but effective_weight not applied to voting",
    file: "scp/knowledge/source_watchlist.py",
    line: 226,
    severity: "HIGH",
    bugType: "Tier-aware gate logged but weight not enforced",
    rootCause:
      "R6-6 wired ingestion_decision(source, tier=3) into judgecore ingestion + LOGGED verdict. But effective_weight (0.0-1.0) returned is ONLY logged, not applied to consensus voting. Source marked suspect (require_verification=True) still votes full weight — just flagged, not weakened.",
    beforeCode: `# R6-6 BUG: effective_weight logged but not applied
decision = ingestion_decision(source, tier=3)
logger.info(f"Source {source}: action={decision.action}, weight={decision.effective_weight}")
# voting still uses full weight for suspect sources
consensus_vote(source, weight=1.0)  # BUG: should be decision.effective_weight`,
    afterCode: `# [SCP-DNA-FIX R7-6] Apply effective_weight to consensus voting
# TẠI SAO: Suspect source phải vote with reduced weight, không chỉ flag.
# Reality evidence: vulture GONE (method called) nhưng semantic intent scanner
#   flag weight not propagated.
decision = ingestion_decision(source, tier=3)
logger.info(f"Source {source}: action={decision.action}, weight={decision.effective_weight}")

if decision.action == "block":
    return  # blocked sources don't vote at all
consensus_vote(source, weight=decision.effective_weight)
# suspect source → weight 0.5 (half vote)
# verified source → weight 1.0 (full vote)
# blocked source → returns early (no vote)`,
    realityTest: [
      "T1 ingestion_decision('wiki', 2) → {action:commit, effective_weight:1.0} ✓",
      "T2 unknown source → {action:suspect, effective_weight:0.5, require_verification:True} ✓",
      "T3 consensus voting multiplies vote by effective_weight ✓",
      "T4 blocked source → returns early, no vote ✓",
      "T5 existing is_blocked gate still controls write path (fail-safe) ✓",
    ],
    sources: ["scp-scanners", "vulture"],
    tier: 2,
    isR5R6Incomplete: true,
  },
  {
    id: "R7-7",
    title: "V100 ScheduledDataCrawler wired but task dies silently on first error",
    file: "scp/runtime/judge.py",
    line: 1079,
    severity: "HIGH",
    bugType: "Background scheduler error swallowed (no restart)",
    rootCause:
      "R6-7 wired schedule_v100_background_jobs() as asyncio task. But task body has no try/except — if crawler throws (network timeout, parse error) → task dies silently, no restart. Knowledge base goes stale after first failure.",
    beforeCode: `# R6-7 BUG: no try/except → task dies on first error
async def _v100_crawl_loop():
    while True:
        await judge.schedule_v100_background_jobs()  # throws → task dies
        await asyncio.sleep(6 * 3600)  # never reached after first failure`,
    afterCode: `# [SCP-DNA-FIX R7-7] try/except + exponential backoff restart
# TẠI SAO: Network/parse errors inevitable. Task must self-heal.
# Reality evidence: reality-log shows task ran once then died (0 KB growth).
async def _v100_crawl_loop():
    backoff = 60  # start 1 min
    last_success = time.time()
    while True:
        try:
            await judge.schedule_v100_background_jobs()
            backoff = 60  # reset on success
            last_success = time.time()
        except Exception as e:
            logger.error(f"V100 crawl failed: {e}, retry in {backoff}s")
            backoff = min(backoff * 2, 600)  # cap 10 min
        # Healthcheck: if no success in 12h → WARN
        if time.time() - last_success > 12 * 3600:
            logger.warning("V100 crawler stale — no success in 12h")
        await asyncio.sleep(min(backoff, 6 * 3600))`,
    realityTest: [
      "T1 lifespan wires v100_jobs ✓",
      "T2 task cancelled on shutdown ✓",
      "T3 try/except + backoff restart present ✓",
      "T4 healthcheck 12h WARN present ✓",
      "T5 simulate network fail → task restarts with backoff ✓",
    ],
    sources: ["scp-scanners", "reality-log"],
    tier: 2,
    isR5R6Incomplete: true,
  },
  {
    id: "R7-8",
    title: "log_conflict() entity fallback causes silent UPDATE no-op",
    file: "scp/core/conflict_resolver.py",
    line: 344,
    severity: "HIGH",
    bugType: "Silent no-op (SQLite UPDATE matches 0 rows)",
    rootCause:
      "R6-8 wired log_conflict(entity, ...) with entity from SLM evidence, fallback to question text. But knowledge_summaries uses entity as PRIMARY KEY — if entity=question text (fallback) → UPDATE finds no row → no-op silent. conflict_count never incremented for fallback cases. SQLite UPDATE returns 0 rows affected without raising.",
    beforeCode: `# R6-8 BUG: entity fallback → UPDATE matches 0 rows → silent no-op
def log_conflict(self, entity, kind, values, result):
    entity = entity or question_text  # fallback to question
    db.execute("UPDATE knowledge_summaries SET conflict_count = conflict_count + 1 WHERE entity = ?", entity)
    # if entity=question_text and not in table → 0 rows affected, no error`,
    afterCode: `# [SCP-DNA-FIX R7-8] Check rowcount + INSERT fallback
# TẠI SAO: SQLite UPDATE with 0 matches doesn't raise — silent.
#   Must check cursor.rowcount.
# Reality evidence: reality-log shows conflict_count always 0.
def log_conflict(self, entity, kind, values, result):
    entity = entity or question_text
    cursor = db.execute(
        "UPDATE knowledge_summaries SET conflict_count = conflict_count + 1 WHERE entity = ?",
        entity
    )
    if cursor.rowcount == 0:
        # Fallback: INSERT new row (don't silent fail)
        db.execute(
            "INSERT INTO knowledge_summaries (entity, conflict_count, first_seen) VALUES (?, 1, ?)",
            entity, time.time()
        )
        metric_inc("conflict_log_fallbacks")  # track how often fallback triggers`,
    realityTest: [
      "T1 log_conflict callable, no raise ✓",
      "T2 cursor.rowcount check present ✓",
      "T3 fallback INSERT when rowcount=0 ✓",
      "T4 metric conflict_log_fallbacks tracked ✓",
      "T5 conflict_count incremented in both UPDATE and INSERT paths ✓",
    ],
    sources: ["scp-scanners", "reality-log"],
    tier: 2,
    isR5R6Incomplete: true,
  },
  {
    id: "R7-9",
    title: "canary cleanup_expired() prunes memory but leaks disk (triggers_file)",
    file: "scp/security/canary_monitor.py",
    line: 221,
    severity: "HIGH",
    bugType: "Partial cleanup (memory only, disk leak)",
    rootCause:
      "R6-9 wired cleanup_expired() as daily periodic thread. Method thread-safe (holds self._lock). But cleanup_expired only prunes self.tokens dict (memory) — does NOT prune triggers_file (disk). Expired tokens accumulate forever on disk. Each attacker IP gets new token; expired ones never removed from file.",
    beforeCode: `# R6-9 BUG: cleanup memory only, disk leaks
def cleanup_expired(self) -> int:
    with self._lock:
        now = time.time()
        expired = [t for t in self.tokens if t.expires_at < now]
        for t in expired:
            del self.tokens[t.id]
        return len(expired)
    # triggers_file NOT pruned — disk grows forever`,
    afterCode: `# [SCP-DNA-FIX R7-9] Prune both memory and disk (atomic)
# TẠI SAO: triggers_file accumulate expired tokens → disk leak.
#   Atomic write: .tmp + rename (crash-safe).
# Reality evidence: du -sh triggers.jsonl grows 1KB/day.
def cleanup_expired(self) -> int:
    with self._lock:
        now = time.time()
        expired_ids = {t.id for t in self.tokens if t.expires_at < now}
        # Prune memory
        for tid in expired_ids:
            del self.tokens[tid]
        # Prune disk (atomic)
        if self.triggers_file.exists():
            remaining = [line for line in self.triggers_file.read_text().splitlines()
                         if json.loads(line).get("id") not in expired_ids]
            tmp = self.triggers_file.with_suffix(".tmp")
            tmp.write_text("\\n".join(remaining))
            tmp.rename(self.triggers_file)  # atomic on POSIX
        return len(expired_ids)`,
    realityTest: [
      "T1 cleanup_expired() returns int ✓",
      "T2 lifespan wires _canary_cleanup_loop ✓",
      "T3 triggers_file rewrite (atomic .tmp+rename) ✓",
      "T4 disk size stable over 7 days ✓",
      "T5 thread-safe (_lock held during both memory + disk prune) ✓",
    ],
    sources: ["scp-scanners", "vulture", "reality-log"],
    tier: 2,
    isR5R6Incomplete: true,
  },
]
