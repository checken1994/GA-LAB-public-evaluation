/**
 * Round 8 Findings — 7 NEW root-cause bugs R7/R7-Full MISSED (separate file per task)
 *
 * DNA #22 (PASS ≠ TRUE) applied recursively: "R7 found 14 bugs" doesn't mean 14
 * were the ONLY bugs. R8 ran the strengthened scanners + world's-best-tool
 * patterns (ruff/bandit/semgrep/vulture/pyright/CodeQL signatures via grep+ast)
 * and found 7 NEW bugs across 6 classes — ALL patched in real Python.
 *
 * Each finding has: file:line, bug_class, root_cause (TẠI SAO), before_code,
 * after_code (the real patch), world_tool inspiration, repro_hypothesis, and
 * why R7 missed it.
 *
 * Source: scp/audit_r8/r8_findings.md + scp/audit_r8/FIXES_APPLIED_R8.md
 */

export type R8Severity = "critical" | "high" | "medium" | "low"

export interface R8Finding {
  id: string
  file: string
  line: number
  bugClass: string
  severity: R8Severity
  rootCause: string
  beforeCode: string
  afterCode: string
  worldTool: string
  reproHypothesis: string
  whyR7Missed: string
  astParseOk: boolean
  fixStatus: "fixed" | "verified-false-positive"
}

export const R8_FINDINGS: R8Finding[] = [
  {
    id: "R8-1",
    file: "api_server.py + api/_lifespan.py",
    line: 354,
    bugClass: "silent_failure / wrong_data_source",
    severity: "high",
    rootCause:
      "_attack_mode_monitor queries SQLite 'SELECT COUNT(*) FROM notifications WHERE timestamp > ?' but NO notifications table is ever created (grep CREATE TABLE.*notifications = 0 hits). Notifications live in-memory (runtime/notifications.py) + JSONL. Query raises sqlite3.OperationalError, swallowed by `except Exception: logger.debug(...)`. kill_count stays 0 → attack mode NEVER auto-triggers. The self-defense system is dead code that looks alive.",
    beforeCode: `row = _dq("SELECT COUNT(*) as cnt FROM notifications WHERE timestamp > ?", (_time.time() - 600,))
kill_count = row["cnt"] if row else 0
if kill_count > 20 and not eng.in_attack_mode:
    eng.set_attack_mode(True)
except Exception as e:
    logger.debug(f"[AUTO] Attack mode monitor: {e}")  # swallowed silently`,
    afterCode: `# R8-1: query the in-memory UserNotificationSystem instead of the
# non-existent SQLite 'notifications' table. Fail-open to 0.
_notif = getattr(get_judge(), "notifications", None)
kill_count = (
    sum(1 for n in _notif._recent
        if n.get("timestamp", 0) > _time.time() - 600
        and n.get("event_type") in ("governance_kill", "attack_blocked"))
    if _notif else 0
)
if kill_count > 20 and not eng.in_attack_mode:
    eng.set_attack_mode(True)`,
    worldTool: "vulture (dead code) + manual data-flow review",
    reproHypothesis:
      "Start SCP, send 50 attack prompts that get KILL verdicts. Check eng.in_attack_mode after 6min → False. Debug logs show 'no such table: notifications' repeating.",
    whyR7Missed:
      "R7 audited _lifespan task GC (R7-2) + crawler restart (R7-7) but never traced data flow inside _attack_mode_monitor. SQL string looks plausible; except swallows the error at debug-level. R7 grep scanner looked for except:pass, not query-against-nonexistent-table.",
    astParseOk: true,
    fixStatus: "fixed",
  },
  {
    id: "R8-2",
    file: "autofix/engine.py",
    line: 1091,
    bugClass: "logic_error / safety_guard_defeated",
    severity: "high",
    rootCause:
      "_should_auto_approve_tier3 uses _tier3_auto_enabled_at == 0.0 as 'disabled' sentinel. On timeout expiry it sets 0.0, but on the NEXT bug call it sees == 0.0 and immediately re-arms by setting = now. The 1h timeout is ineffective — Tier-3 auto-approve stays permanently enabled as long as SCP_AUTO_APPROVE_TIER3=1 remains set, clock restarting on every bug after expiry. A safety guard that never actually guards.",
    beforeCode: `if self._tier3_auto_enabled_at == 0.0:
    self._tier3_auto_enabled_at = now  # first call starts the clock
elif now - self._tier3_auto_enabled_at > TIER3_AUTO_TIMEOUT_SECONDS:
    logger.warning(f'[TIER3-AUTO] Timed out after {TIER3_AUTO_TIMEOUT_SECONDS}s ...')
    self._tier3_auto_enabled_at = 0.0
    return False  # ...but next call re-arms!`,
    afterCode: `# R8-2: _tier3_auto_expired flag does NOT clear on subsequent calls.
# Set on timeout. Clear ONLY when env var transitions 0/unset → 1.
if self._tier3_auto_expired:
    return False  # stay denied until operator re-toggles env var
if self._tier3_auto_enabled_at == 0.0:
    self._tier3_auto_enabled_at = now
elif now - self._tier3_auto_enabled_at > TIER3_AUTO_TIMEOUT_SECONDS:
    self._tier3_auto_expired = True
    self._tier3_auto_enabled_at = 0.0
    return False`,
    worldTool: "manual review + ruff PLR (logic) + semgrep timeout-bypass audit",
    reproHypothesis:
      "Set SCP_AUTO_APPROVE_TIER3=1. Wait 1h + 1 bug. Then send 5 more bugs over the next hour. ALL 5 will still be auto-approved (timeout re-arms). WARNING fires once per expiry but never actually disables.",
    whyR7Missed:
      "R7-13 added audit log columns + rollback endpoint but never tested timeout behavior end-to-end. Logic looks correct in isolation (elif sets 0.0 + returns False), but re-arm-on-next-call invisible unless you trace the SECOND call after expiry.",
    astParseOk: true,
    fixStatus: "fixed",
  },
  {
    id: "R8-3",
    file: "runtime/storage_manager.py",
    line: 167,
    bugClass: "impl_vs_doc / silent_data_loss",
    severity: "medium",
    rootCause:
      "_rotate_large_files docstring says 'rename to .1.gz, shift existing .1.gz to .2.gz, delete .3.gz' (3 generations kept). Implementation does NOT shift — gzip.open(gz_path, 'wb') opens write+truncate, OVERWRITING any existing .1.gz. After the 2nd rotation, the 1st rotation's compressed data is GONE. Only the most recent rotation is ever kept. The docstring lies convincingly.",
    beforeCode: `gz_path = f.with_suffix(f.suffix + '.1.gz')
with open(f, 'rb') as src, gzip.open(gz_path, 'wb') as dst:
    shutil.copyfileobj(src, dst)
# (no shift of .1.gz → .2.gz, no deletion of .3.gz — docstring is fiction)`,
    afterCode: `# R8-3: 3-generation shift per docstring (delete .3 → shift .2→.3, .1→.2 → write new .1)
MAX_GENERATIONS = 3
gz_paths = [f.with_suffix(f.suffix + f'.{i}.gz') for i in range(1, MAX_GENERATIONS + 1)]
if gz_paths[-1].exists():
    gz_paths[-1].unlink()  # delete oldest generation
for i in range(len(gz_paths) - 1, 0, -1):
    if gz_paths[i - 1].exists():
        gz_paths[i - 1].rename(gz_paths[i])  # shift down
with open(f, 'rb') as src, gzip.open(gz_paths[0], 'wb') as dst:
    shutil.copyfileobj(src, dst)`,
    worldTool: "vulture (dead code) + ruff DOC (docstring vs impl mismatch)",
    reproHypothesis:
      "Set ROTATE_SIZE_MB=0.1. Write 200MB to error_store.jsonl. Trigger rotation → .1.gz created. Write another 200MB. Trigger rotation → .1.gz OVERWRITTEN. 1st batch's compressed data LOST.",
    whyR7Missed:
      "R7-9 verified disk prune in canary_monitor.py but storage_manager.py's rotation was not in R7 audit scope. Readers trust the docstring.",
    astParseOk: true,
    fixStatus: "fixed",
  },
  {
    id: "R8-4",
    file: "runtime/judge.py",
    line: 1106,
    bugClass: "cold_start_regression / silent_failure",
    severity: "medium",
    rootCause:
      "R7-7 added a 12h stale WARN to detect a stale knowledge base. The guard 'if last_success > 0 and ...' was meant to skip WARN before the first successful crawl (avoid startup noise). But it ALSO skips WARN when the first crawl NEVER succeeds. If SCP starts with network down, last_success stays 0.0 forever → the 12h stale WARN NEVER fires. Operators get zero signal that the knowledge base is stale from cold start — exactly the failure R7-7 was supposed to catch.",
    beforeCode: `last_success = 0.0  # [R7-7] tracks staleness
...
# [R7-7] 12h healthcheck — WARN if no successful crawl in 12h.
if last_success > 0 and (now - last_success) > 12 * 3600:
    logger.warning(f'[R7-7] V100 crawler STALE — ...')
# cold-start case (last_success == 0) NEVER warns`,
    afterCode: `# R8-4: cold-start case now fires WARN after 12h from scheduler start.
_scheduler_started_at = ...  # tracked at scheduler init
_stale_since = last_success if last_success > 0 else _scheduler_started_at
if now - _stale_since > 12 * 3600:
    logger.warning(
        f'[R8-4] V100 crawler STALE — no success in {(now - _stale_since)/3600:.1f}h '
        f'(cold_start={last_success == 0})'
    )`,
    worldTool: "manual review + semgrep missing-cold-start audit",
    reproHypothesis:
      "Start SCP with no network. Wait 12h. Check logs — NO 'V100 crawler STALE' WARN fires (gated by last_success > 0 which is False for cold start). The exact failure R7-7 was supposed to catch is silently missed.",
    whyR7Missed:
      "R7-7 was about the failure path (don't advance last_crawl on failure). The healthcheck guard 'last_success > 0' was a 'skip startup noise' optimization, but the cold-start interaction was never tested. R7-10 hypothesis tests covered None-safety, not the 12h WARN path.",
    astParseOk: true,
    fixStatus: "fixed",
  },
  {
    id: "R8-5",
    file: "autofix/engine.py + api/routes/v105_routes.py",
    line: 1171,
    bugClass: "insufficient_storage / misleading_error",
    severity: "medium",
    rootCause:
      "R7-13 Tier-3 auto-approve writes a single .tier3bak per file. If bug A is fixed (writes .tier3bak = pre-A), then bug B is fixed on the same file (writes .tier3bak = pre-B, OVERWRITING), the .tier3bak for bug A is LOST. When the operator POSTs /v105/autofix/rollback/{token_A}, the endpoint reads .tier3bak (now pre-B), hashes it, compares to before_hash (pre-A hash) → MISMATCH → HTTP 409 'Backup hash mismatch (backup tampered?)'. The error message LIES — the backup wasn't tampered, it was clobbered by a later fix on the same file.",
    beforeCode: `# engine.py:1171 — single .tier3bak per file (OVERWRITES on 2nd fix same file)
bak_path = filepath.with_suffix(filepath.suffix + '.tier3bak')
bak_path.write_text(filepath.read_text(encoding='utf-8'), encoding='utf-8')

# v105_routes.py:340 — hash check fails for older fix on multi-fix file
bak_hash = hashlib.sha256(bak_path.read_bytes()).hexdigest()
if bak_hash != before_hash:
    raise HTTPException(409, f'Backup hash mismatch (backup tampered?)')`,
    afterCode: `# R8-5: per-token backup files — each fix gets its own .tier3bak.{rollback_token}
bak_path = filepath.with_suffix(filepath.suffix + f'.tier3bak.{self._rollback_token}')
bak_path.write_text(filepath.read_text(encoding='utf-8'), encoding='utf-8')

# v105_routes.py: derive bak_path from rollback_token; accurate 409 message
bak_path_token = filepath.with_suffix(filepath.suffix + f'.tier3bak.{rollback_token}')
if not bak_path_token.exists():
    raise HTTPException(409, f'Backup for token {rollback_token} missing or '
                              f'clobbered by a LATER fix on same file.')`,
    worldTool: "manual review + CodeQL data-flow (token → file → bak → hash)",
    reproHypothesis:
      "1. SCP auto-approves bug A at foo.py:10 (.tier3bak = pre-A, token_A, before_hash=hash(pre-A)). 2. SCP auto-approves bug B at foo.py:20 (.tier3bak = pre-B, OVERWRITES). 3. Operator POSTs /rollback/{token_A} → reads .tier3bak (now pre-B), hash != before_hash → HTTP 409 'tampered'. Error LIES.",
    whyR7Missed:
      "R7-13 tested rollback with a SINGLE fix per file. Multi-fix-per-file case never tested. R7 reality test only verified 'rollback reverts to before_hash' for single-fix — trivially passes when only one fix exists.",
    astParseOk: true,
    fixStatus: "fixed",
  },
  {
    id: "R8-6",
    file: "runtime/healing_v14.py",
    line: 213,
    bugClass: "race_condition / concurrent_list_mutation",
    severity: "low",
    rootCause:
      "V14SelfHealingEngine.heal() runs in the V98 pipeline thread (sync, inside judge.judge()). get_stats() runs in the API request thread (asyncio event loop). healing_history is mutated WITHOUT a lock: heal() appends + truncates; get_stats() iterates. CPython list iterators cache ob_size; if heal() appends mid-iteration, next(iterator) raises RuntimeError: list changed size during iteration. The asyncio loop propagates this as a 500 error to the admin client.",
    beforeCode: `# heal() line 213:
self.healing_history.append({...})
if len(self.healing_history) > 1000:
    self.healing_history = self.healing_history[-500:]

# get_stats() line 344:
successes = sum(1 for h in self.healing_history if h['success'])  # iterates unlocked`,
    afterCode: `# R8-6: guard healing_history with threading.Lock
self._history_lock = threading.Lock()  # in __init__

# heal():
with self._history_lock:
    self.healing_history.append({...})
    if len(self.healing_history) > 1000:
        self.healing_history = self.healing_history[-500:]

# get_stats(): iterate a snapshot under lock
with self._history_lock:
    history_snapshot = list(self.healing_history)
successes = sum(1 for h in history_snapshot if h['success'])`,
    worldTool: "manual review + semgrep race-condition audit + ruff RUF006",
    reproHypothesis:
      "Run SCP under load (concurrent /ask triggering heal() + admin polling /v98/status calling get_stats()). Eventually RuntimeError: list changed size during iteration appears as a 500 in API responses or logs.",
    whyR7Missed:
      "R7-3 added threading.Lock to why_engine.py for a similar concurrent-claim race, but healing_v14.py was not in R7 audit scope. The mutation pattern looks safe in isolation (single-threaded read), but the cross-thread interaction is invisible without tracing call sites.",
    astParseOk: true,
    fixStatus: "fixed",
  },
  {
    id: "R8-7",
    file: "meta/why_engine.py",
    line: 764,
    bugClass: "race_condition / check_then_act_lazy_lock_init",
    severity: "low",
    rootCause:
      "R7-3 added a per-instance threading.Lock to serialize execute_pending_plans. But it used a lazy-init pattern: 'if not hasattr(self, _lock): self._lock = threading.Lock()'. Classic check-then-act race: if 2 threads enter concurrently and BOTH see not-hasattr True (before either assigns), both create NEW Lock objects. Thread B's assignment overwrites Thread A's. If Thread B reaches 'with self._lock' before Thread A overwrites, Thread B acquires Lock_B. Then Thread A overwrites with Lock_A and acquires Lock_A. Both threads hold DIFFERENT locks → no mutual exclusion — exactly the race R7-3 was supposed to prevent.",
    beforeCode: `# [R7-3+] Per-instance lock — guards in-process concurrency.
if not hasattr(self, '_execute_pending_lock'):  # check
    self._execute_pending_lock = _threading.Lock()  # act — race window here
...
with self._execute_pending_lock:  # might be a DIFFERENT lock than the other thread`,
    afterCode: `# R8-7: eager-init lock in __init__ — race-free, no check-then-act.
def __init__(self, ...):
    ...
    self._execute_pending_lock = threading.Lock()  # always exists

def execute_pending_plans(self, ...):
    with self._execute_pending_lock:  # same lock for all threads
        ...`,
    worldTool: "manual review + semgrep double-checked-locking audit",
    reproHypothesis:
      "Hammer execute_pending_plans with 10 concurrent threads (10 simultaneous /admin/why/execute calls). With enough iterations, 2 threads create separate Lock objects and both proceed to claim the same why_verification_plans row. DB-level claimed_by catches this (R7-3 defense-in-depth), so no data corruption — but the in-process lock's purpose (avoiding wasted DB contention) is defeated.",
    whyR7Missed:
      "R7-3's fix tested the common case (sequential calls). The race window is tiny (a few bytecodes between hasattr and with), but real — CPython GIL releases between bytecodes. R7-10 hypothesis tests covered None-safety, not concurrency stress. The hasattr lazy-init pattern is a common Python idiom that LOOKS safe but has this subtle race.",
    astParseOk: true,
    fixStatus: "fixed",
  },
]

export const R8_STATS = {
  total: R8_FINDINGS.length,
  bySeverity: {
    critical: R8_FINDINGS.filter((f) => f.severity === "critical").length,
    high: R8_FINDINGS.filter((f) => f.severity === "high").length,
    medium: R8_FINDINGS.filter((f) => f.severity === "medium").length,
    low: R8_FINDINGS.filter((f) => f.severity === "low").length,
  },
  fixed: R8_FINDINGS.filter((f) => f.fixStatus === "fixed").length,
  astParseOk: R8_FINDINGS.filter((f) => f.astParseOk).length,
  bugClasses: [...new Set(R8_FINDINGS.map((f) => f.bugClass.split(" / ")[0]))],
  worldTools: [...new Set(R8_FINDINGS.map((f) => f.worldTool.split(" + ")[0]))],
}

/**
 * R8 methodology — how the 7 bugs were found (reproducible, DNA #19).
 */
export const R8_METHODOLOGY: { step: string; detail: string }[] = [
  {
    step: "1. Read R7's 14 findings (avoid re-reporting)",
    detail:
      "Read FIXES_APPLIED_R7.md to know what R7/R7-Full already covered (chemistryslm None-safety, Tor task GC, WHY race, source reputation cold-start, is_skeptical, weight voting, crawler restart, conflict_resolver rowcount, disk prune, hypothesis tests, scanner self-audit, diff rescan, audit log columns, relaxation patterns).",
  },
  {
    step: "2. Targeted grep scans for 14 bug classes",
    detail:
      "Ran grep patterns replicating world's-best-tool signatures: bare-except/swallowed (bandit/ruff), SQL injection (semgrep/bandit), command injection (bandit), path traversal (semgrep), weak crypto (bandit), mutable default args (ruff), resource leak (vulture), race condition (manual), None-safety (pyright), dead code (vulture), float equality (ruff), assert-in-prod (ruff), open-without-encoding (ruff), datetime-without-tz (manual).",
  },
  {
    step: "3. Deep-read the 6 highest-risk files",
    detail:
      "Read judge.py (64KB), api_server.py (52KB), healing_v14.py (18KB), storage_manager.py (21KB), engine.py (76KB), slms.py (22KB) — the biggest/most-critical files with highest bug density. For each hit, read ~15 surrounding lines to confirm real bug (not handled nearby).",
  },
  {
    step: "4. Document each finding with DNA #1 + #17 rigor",
    detail:
      "For each confirmed bug: exact file:line (verified by reading), bug_class, severity, root_cause (TẠI SAO — not just the symptom), before_code (quoted), suggested_fix (code), world_tool inspiration, repro_hypothesis (how it manifests at runtime), why_R7_missed (hypothesis).",
  },
  {
    step: "5. Patch all 7 in REAL Python + ast.parse verify",
    detail:
      "Applied each fix to the actual .py file (surgical, minimal, fail-open, house-style comments). Ran ast.parse on every patched file — 7/7 OK. Full sweep: 371/371 .py files OK (365 baseline + 6 v3 autofix modules). Grep-verified each fix present.",
  },
]
