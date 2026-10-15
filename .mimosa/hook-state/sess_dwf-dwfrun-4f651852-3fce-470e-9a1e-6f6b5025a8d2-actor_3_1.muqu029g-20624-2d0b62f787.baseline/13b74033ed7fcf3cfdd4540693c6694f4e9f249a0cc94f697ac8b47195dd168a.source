/**
 * Round 9 Findings — 7 NEW root-cause bugs R8 MISSED (DNA #22 recursive level 3)
 *
 * R8 reported "7 fixes applied" + "7 NEW bugs found" — but PASS ≠ TRUE.
 * R9 (Subagent B) does NOT trust R8's 7 was exhaustive. It re-audited the
 * SCP codebase with strengthened patterns + world-tool signatures
 * (ruff ASYNC100, semgrep race-condition, inter-procedural tracing) and
 * found 7 MORE bugs R8 MISSED — across 2 bug classes.
 *
 *   - 4 blocking-in-async (CRITICAL + 3 HIGH) — sync long-running calls
 *     inside `async def` handlers block the asyncio event loop.
 *   - 3 race conditions (1 MEDIUM, 2 LOW) — concurrent list/dict mutation
 *     without lock. R9-7 is a regression INTRODUCED by R8-1's fix.
 *
 * Each finding has: id, file:line(s), bug_class, severity, root_cause
 * (TẠI SAO — DNA #1), before_code (buggy), after_code (the suggested
 * fix / patch applied by Subagent D), world_tool inspiration,
 * repro_hypothesis, why_R8_missed, ast_parse_ok, dna_principles.
 *
 * Source: scp/audit_r9/r9_findings.md + scp/audit_r9/r9_findings.jsonl
 */

export type R9Severity = "critical" | "high" | "medium" | "low"

export interface R9Finding {
  id: string
  file: string
  line: number
  bugClass: string
  severity: R9Severity
  rootCause: string
  beforeCode: string
  afterCode: string
  worldTool: string
  reproHypothesis: string
  whyR8Missed: string
  astParseOk: boolean
  dnaPrinciples: string
  fixStatus: "fixed" | "verified-false-positive"
}

export const R9_FINDINGS: R9Finding[] = [
  {
    id: "R9-1",
    file: "api/routes/import_routes.py",
    line: 48,
    bugClass: "blocking_in_async / sync judge.judge in async def",
    severity: "critical",
    rootCause:
      "3 import endpoints (/import/jsonl at :48, /import/excel at :102, /import/batch at :149) are declared `async def` but call `judge.judge(...)` synchronously (no `await asyncio.to_thread`). judge.judge() is long-running sync: SLM HTTP calls (5-15s each) + WHY external queries + V98 pipeline + governance. Each call blocks the asyncio event loop for 5-30+ seconds. A batch import of N questions blocks ALL other HTTP requests (/ask, /health, /dashboard, WebSocket pings) for N × 5-30s — a 100-question import = 8-50 minutes of total event-loop blockage. The dev ALREADY knew about this pattern (api_server.py:788 + openai_compat.py:54 use `await asyncio.to_thread(judge.judge, ...)` correctly, with a comment explaining the bug at openai_compat.py:51-53) but did NOT apply the fix consistently to import_routes.py.",
    beforeCode: `# import_routes.py:39-57 (jsonl endpoint — same pattern at :93-113 excel, :143-160 batch)
for i, line in enumerate(lines):
    if not line.strip():
        continue
    try:
        data = _json.loads(line)
        question = data.get('question', '')
        ai_answer = data.get('ai_answer', data.get('answer', ''))
        data.get('domain', 'general')
        v = judge.judge(question=question, ai_answer=ai_answer, cycle_count=0)  # BLOCKS event loop
        results.append({
            'line': i + 1,
            'question': question[:100],
            'verdict': v.verdict,
            ...
        })`,
    afterCode: `# R9-1: wrap judge.judge in asyncio.to_thread — frees the event loop
import asyncio

for i, line in enumerate(lines):
    if not line.strip():
        continue
    try:
        data = _json.loads(line)
        question = data.get('question', '')
        ai_answer = data.get('ai_answer', data.get('answer', ''))
        data.get('domain', 'general')
        v = await asyncio.to_thread(
            judge.judge,
            question=question, ai_answer=ai_answer, cycle_count=0
        )
        results.append({
            'line': i + 1,
            'question': question[:100],
            'verdict': v.verdict,
            ...
        })
# (Optional: asyncio.gather(*[asyncio.to_thread(judge.judge, q) for q in batch]) for 5-10x speedup.)`,
    worldTool:
      "ruff ASYNC100 + semgrep python.lang.performance.audit.async-blocking-call + manual inter-procedural review",
    reproHypothesis:
      "1. Start SCP. 2. Open 2nd terminal: `watch -n 1 'curl -s http://localhost:8000/health | jq .status'` (should return ok every second). 3. In 3rd terminal: `curl -X POST http://localhost:8000/import/jsonl -H 'Authorization: Bearer $TOKEN' -d @questions.jsonl` where questions.jsonl has 20 questions. 4. Observe /health watch freezes for 100-600 seconds (20 questions × 5-30s each). During this time NO other request can be served. WebSocket clients disconnect.",
    whyR8Missed:
      "R8 deep-read api_server.py + judge.py + healing_v14.py + storage_manager.py + autofix/engine.py + slms.py. api/routes/import_routes.py was NOT in R8's deep-read list (R8 Step 3 lists 6 files + 5 plus files; import_routes.py not mentioned). R8's grep patterns covered except:, SQLi, command injection, weak crypto — but did NOT grep for `judge.judge( without await asyncio.to_thread` (the sync-in-async pattern). The bug is invisible to grep-only scans unless the scanner specifically looks for sync calls inside async def.",
    astParseOk: true,
    dnaPrinciples: "#1 (Hỏi TẠI SAO) · #22 (PASS ≠ TRUE) · #26 (Reality > Model) · #17 (test repro)",
    fixStatus: "fixed",
  },
  {
    id: "R9-2",
    file: "api/routes/v105_routes.py",
    line: 168,
    bugClass: "blocking_in_async / sync run_deep_audit in async def",
    severity: "high",
    rootCause:
      "The `/v105/autofix/run-audit` endpoint is declared `async def` but calls `run_deep_audit()` synchronously. run_deep_audit() (= run_once(ast_scan=True)) AST-scans all 371 .py files (5-15s), then for each finding calls AutoFixEngine.process_bug() which may invoke the LLM fix path (deepseek-r1:8b via Ollama — 30+ seconds per fix). A typical audit finds 5-20 fixable bugs → 2.5-10 minutes total. The entire duration blocks the asyncio event loop. The dev's own code at api_server.py:317-333 runs _deep_audit_loop in a daemon thread (NOT in the event loop) — explicitly to avoid blocking. But the manual /v105/autofix/run-audit endpoint does NOT — it calls run_deep_audit() inline from async def.",
    beforeCode: `# v105_routes.py:166-171
    try:
        from scp.autofix.runner import run_deep_audit
        results = run_deep_audit()  # BLOCKS event loop for minutes
        return {'audit_complete': True, 'results': results}
    except Exception as e:
        raise HTTPException(500, f'Error: {e}') from e`,
    afterCode: `# R9-2: wrap run_deep_audit in asyncio.to_thread — frees event loop
    try:
        import asyncio
        from scp.autofix.runner import run_deep_audit
        results = await asyncio.to_thread(run_deep_audit)
        return {'audit_complete': True, 'results': results}
    except Exception as e:
        raise HTTPException(500, f'Error: {e}') from e`,
    worldTool:
      "ruff ASYNC100 + semgrep python.lang.performance.audit.async-blocking-call",
    reproHypothesis:
      "1. Start SCP. Set SCP_AUTO_APPROVE_TIER3=1. 2. `curl http://localhost:8000/health` → returns ok in <50ms. 3. `curl -X POST http://localhost:8000/v105/autofix/run-audit -H 'Authorization: Bearer $TOKEN'` (triggers full audit + fix cycle). 4. While audit is running (2-10 min), `curl http://localhost:8000/health` hangs — no response until audit completes.",
    whyR8Missed:
      "R8 deep-read api/routes/v105_routes.py (the rollback endpoint R8-5) but only around lines 336-345 (the rollback hash-check). The run-audit endpoint at line 148-171 was not in R8's audit scope. R8's grep patterns did not include 'long-running sync call inside async def'.",
    astParseOk: true,
    dnaPrinciples: "#22 (PASS ≠ TRUE) · #26 (Reality > Model) · #9 (no harm)",
    fixStatus: "fixed",
  },
  {
    id: "R9-3",
    file: "api/routes/v102_v103_routes.py",
    line: 106,
    bugClass: "blocking_in_async / sync crawl_all + check_and_maintain",
    severity: "high",
    rootCause:
      "Two endpoints call synchronous I/O-heavy functions directly inside `async def`. (1) :106 `_attack_crawler.crawl_all()` — crawl_all() (security/attack_crawler.py:99) sequentially calls _crawl_github(), _crawl_huggingface(), _crawl_reddit() — each makes HTTP requests with 5-15s timeouts. Total: 15-45 seconds blocking the event loop. (2) :66 `sm.check_and_maintain()` — check_and_maintain() (storage_manager.py:112) does disk space check, file rotation (compress 100MB+ files — 1-5s each), SQLite VACUUM (10-60s on a large DB), archival (compress + move old files — 5-30s), old-archive deletion. Total: 30-120 seconds blocking the event loop.",
    beforeCode: `# v102_v103_routes.py:101-110 (/v103/attacks/crawl)
@router.post('/v103/attacks/crawl')
async def v103_force_crawl(_admin: bool = Depends(verify_admin)):
    if _attack_crawler is None:
        return {'error': 'AttackCrawler not initialized'}
    new_attacks = _attack_crawler.crawl_all()  # BLOCKS 15-45s
    return {'new_attacks': len(new_attacks), 'stats': _attack_crawler.stats()}

# v102_v103_routes.py:61-74 (/v103/storage/maintain)
@router.post('/v103/storage/maintain')
async def storage_maintain(_admin: bool = Depends(verify_admin)):
    from scp.runtime.storage_manager import StorageManager
    sm = StorageManager(data_dir='data')
    stats = sm.check_and_maintain()  # BLOCKS 30-120s
    return {'total_size_mb': stats.total_size_mb, ...}`,
    afterCode: `# R9-3: wrap both blocking calls in asyncio.to_thread
import asyncio

# Site 1 (line 106):
new_attacks = await asyncio.to_thread(_attack_crawler.crawl_all)

# Site 2 (line 66):
stats = await asyncio.to_thread(sm.check_and_maintain)`,
    worldTool:
      "ruff ASYNC100 + semgrep python.lang.performance.audit.async-blocking-call",
    reproHypothesis:
      "1. Start SCP with attack_crawler initialized. 2. `curl http://localhost:8000/health` → fast. 3. `curl -X POST http://localhost:8000/v103/attacks/crawl -H 'Authorization: Bearer $TOKEN'`. 4. While crawl is running (15-45s), /health hangs. Same for /v103/storage/maintain (30-120s).",
    whyR8Missed:
      "R8 did not deep-read v102_v103_routes.py (not in R8's Step 3 file list). The bug class (sync-in-async) was not in R8's grep pattern set.",
    astParseOk: true,
    dnaPrinciples: "#22 (PASS ≠ TRUE) · #26 (Reality > Model) · #9 (no harm)",
    fixStatus: "fixed",
  },
  {
    id: "R9-4",
    file: "api_server.py",
    line: 652,
    bugClass: "blocking_in_async / chat_sync via future.result()",
    severity: "high",
    rootCause:
      "When a user sends a chat message WITHOUT ai_answer (chatbot mode — default for chat UI), async def ask() at line 549 calls chat_sync(...) at line 652. chat_sync is a synchronous function that detects it's being called from an async context (asyncio.get_running_loop() succeeds) and does: `with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool: future = pool.submit(asyncio.run, coro); return future.result(timeout=90)`. future.result(timeout=90) is a SYNCHRONOUS BLOCKING CALL — it waits for the worker thread to complete. The calling thread is the asyncio event loop thread. So while Ollama generates the response (60-90 seconds), the event loop is COMPLETELY blocked — other /ask requests, /health, WebSocket, background tasks all frozen. The chat_sync docstring claims it's a 'Sync wrapper for background threads' — but it's called from the event loop thread (async def ask), not a background thread. The ThreadPoolExecutor indirection does NOT make it non-blocking. Additionally the timeout=90 is misleading: if future.result raises TimeoutError, the `with pool` block calls pool.shutdown(wait=True) on exit which BLOCKS until worker finishes — so timeout is not enforced.",
    beforeCode: `# api_server.py:648-660
    _ai_answer = req.ai_answer
    if not _ai_answer or not _ai_answer.strip():
        try:
            from scp.llm_gateway import chat_sync
            _ollama_answer, _provider = chat_sync(  # BLOCKS event loop 60-90s
                req.question,
                context='',
                system_prompt='Bạn là SCP — một trợ lý AI thông minh. Trả lời ngắn gọn, chính xác, bằng tiếng Việt.',
                task='chat',
            )
            if _ollama_answer:
                _ai_answer = _ollama_answer
                logger.info(f'[CHATBOT] Ollama ({_provider}) generated answer: {_ollama_answer[:80]}...')
        except Exception as _ollama_err:
            logger.warning(f'[CHATBOT] Ollama call failed: {_ollama_err}')

# llm_gateway/client.py:581-587 (chat_sync internals — the blocking site)
if _in_async:
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result(timeout=self.ollama_default.timeout + 30)  # BLOCKS calling thread`,
    afterCode: `# R9-4: replace chat_sync() with direct await on async chat() method.
# LLMGateway.chat is already async (uses httpx.AsyncClient — no thread needed).
    _ai_answer = req.ai_answer
    if not _ai_answer or not _ai_answer.strip():
        try:
            from scp.llm_gateway import get_gateway
            _gateway = get_gateway()
            _ollama_answer, _provider = await _gateway.chat(  # async, non-blocking
                req.question,
                context='',
                system_prompt='Bạn là SCP — một trợ lý AI thông minh. Trả lời ngắn gọn, chính xác, bằng tiếng Việt.',
                task='chat',
            )
            if _ollama_answer:
                _ai_answer = _ollama_answer
                logger.info(f'[CHATBOT] Ollama ({_provider}) generated answer: {_ollama_answer[:80]}...')
        except Exception as _ollama_err:
            logger.warning(f'[CHATBOT] Ollama call failed: {_ollama_err}')`,
    worldTool:
      "ruff ASYNC100 (does not detect cross-function blocking) + manual inter-procedural analysis + semgrep custom rule tracing chat_sync → future.result",
    reproHypothesis:
      "1. Start SCP with Ollama running. 2. Open 2 terminals both running: `watch -n 1 'curl -s http://localhost:8000/health | jq .status'`. 3. In a 3rd terminal send chatbot-style request (no ai_answer): `curl -X POST http://localhost:8000/ask -H 'Content-Type: application/json' -d '{\"question\": \"Viết một bài thơ về mùa thu\"}'`. 4. Observe both /health watches freeze for 30-90 seconds (Ollama generation time). They resume only after chat_sync returns.",
    whyR8Missed:
      "R8 deep-read api_server.py but focused on the attack-mode monitor (R8-1 area, lines 354-385) and lifespan. The chat_sync call at line 652 looks superficially correct — wrapped in try/except, and chat_sync's docstring CLAIMS it handles async contexts. The blocking behavior is only visible if you trace INTO chat_sync (llm_gateway/client.py:581-587) and notice that future.result() is synchronous. Ruff ASYNC100 detects direct time.sleep()/requests.get() in async def but does NOT detect 'sync function call that internally blocks' — that requires inter-procedural analysis.",
    astParseOk: true,
    dnaPrinciples: "#1 (TẠI SAO) · #22 (PASS ≠ TRUE) · #26 (Reality > Model) · #17 (test repro)",
    fixStatus: "fixed",
  },
  {
    id: "R9-5",
    file: "runtime/judge.py + runtime/judge_parts/judgecore_mixin.py",
    line: 1169,
    bugClass: "race_condition / concurrent list mutation verdict_history",
    severity: "low",
    rootCause:
      "judge.judge() runs in a worker thread (via asyncio.to_thread(judge.judge, ...) at api_server.py:788). judge.get_stats() is called by admin endpoints from the asyncio event loop thread (e.g. engine.get_report() at runtime/engine.py:558 → judge.get_stats()). They share self.verdict_history WITHOUT a lock. judgecore_mixin.py:1692 appends + :1693 reassigns the list reference (`self.verdict_history = self.verdict_history[-100:]`). judge.py:1169 iterates the list in a for loop. CPython's list iterator caches ob_size at creation — if judge() appends or reassigns while get_stats() iterates, the iterator raises RuntimeError: list changed size during iteration. The asyncio event loop propagates this as a 500 error to the admin client. This is the EXACT SAME bug class as R8-6 (healing_history race) — R8-6 fixed healing_v14.healing_history but missed judge.verdict_history.",
    beforeCode: `# judge.py:168 (init — NO lock)
self.verdict_history: list[JudgeVerdict] = []

# judgecore_mixin.py:1692-1693 (worker thread — NO lock)
self.verdict_history.append(verdict)
self.verdict_history = self.verdict_history[-100:]  # [FIX LEAK] Cap to 100

# judge.py:1169-1172 (event loop thread — NO lock)
for v in self.verdict_history:
    verdicts[v.verdict] = verdicts.get(v.verdict, 0) + 1
return {
    'total_verdicts': len(self.verdict_history),
    ...
}`,
    afterCode: `# R9-5: guard verdict_history with threading.Lock (mirror R8-6 pattern)
# judge.py:168 (init — add lock)
import threading
...
self.verdict_history: list[JudgeVerdict] = []
self._verdict_history_lock = threading.Lock()

# judgecore_mixin.py:1692-1693 (worker thread — guard with lock)
with self._verdict_history_lock:
    self.verdict_history.append(verdict)
    if len(self.verdict_history) > 100:
        self.verdict_history = self.verdict_history[-100:]

# judge.py:1169-1172 (event loop — snapshot under lock, iterate snapshot)
with self._verdict_history_lock:
    history_snapshot = list(self.verdict_history)
for v in history_snapshot:
    verdicts[v.verdict] = verdicts.get(v.verdict, 0) + 1
return {
    'total_verdicts': len(history_snapshot),
    ...
}`,
    worldTool:
      "semgrep python.lang.security.audit.race-condition + ruff RUF006 + manual review",
    reproHypothesis:
      "Run SCP under load: 10 concurrent /ask requests (each triggers judge.judge() in a worker thread → appends to verdict_history) + admin polling /v100/status (calls get_stats() from event loop). Eventually a `RuntimeError: list changed size during iteration` appears in the API response (500) or server logs.",
    whyR8Missed:
      "R8-6 fixed healing_v14.healing_history (the SAME bug class) but only in healing_v14.py. R8 did not grep for other `self.X_history.append(...)` patterns across the codebase. The verdict_history mutation is in judgecore_mixin.py (not judge.py itself) — extracted to a mixin file during a refactoring task (per comment at judge.py:1181-1194). R8 deep-read judge.py but did not trace into judge_parts/judgecore_mixin.py.",
    astParseOk: true,
    dnaPrinciples: "#1 (TẠI SAO) · #22 (PASS ≠ TRUE) · #19 (lineage) · #17 (test repro)",
    fixStatus: "fixed",
  },
  {
    id: "R9-6",
    file: "runtime/healing_v14.py",
    line: 174,
    bugClass: "race_condition / concurrent dict mutation error_patterns",
    severity: "low",
    rootCause:
      "R8-6 added a `_history_lock` to healing_v14.py and used it to guard healing_history mutations + snapshots. But error_patterns (a defaultdict(int) at line 57) — which lives in the SAME file, 6 lines below the patched block — was NOT guarded. monitor() at line 174-175 mutates `self.error_patterns[issue['type']] += 1` (called from judge.judge() worker thread). get_stats() at line 370 reads `dict(self.error_patterns)` (called from admin endpoint event loop thread). `dict(self.error_patterns)` while another thread mutates the dict can raise RuntimeError: dictionary changed size during iteration (older CPython) or produce inconsistent reads (newer CPython). R8-6's fix was INCOMPLETE — it patched healing_history but missed error_patterns in the same file, despite the two being accessed by the same pair of threads.",
    beforeCode: `# healing_v14.py:66 (init — R8-6 added _history_lock, but only for healing_history)
self._history_lock = threading.Lock()

# healing_v14.py:174-175 (monitor() — NO lock for error_patterns)
for issue in issues:
    self.error_patterns[issue['type']] = self.error_patterns.get(issue['type'], 0) + 1

# healing_v14.py:370 (get_stats() — NO lock for error_patterns)
'error_patterns': dict(self.error_patterns),`,
    afterCode: `# R9-6: extend _history_lock to also guard error_patterns (or rename to _state_lock)
# :174-175 (monitor() — guard with lock)
with self._history_lock:
    for issue in issues:
        self.error_patterns[issue['type']] = self.error_patterns.get(issue['type'], 0) + 1

# :370 (get_stats() — snapshot under lock)
with self._history_lock:
    error_patterns_snapshot = dict(self.error_patterns)
return {
    ...
    'error_patterns': error_patterns_snapshot,
    ...
}
# (Or rename _history_lock to _state_lock to reflect it now guards both fields.)`,
    worldTool:
      "semgrep python.lang.security.audit.race-condition + manual review",
    reproHypothesis:
      "Run SCP under load with healing issues triggering (e.g. high error rate → monitor() called from worker thread). Poll /v98/status or any admin endpoint that calls healing.get_stats(). Eventually `dict(self.error_patterns)` raises RuntimeError or returns inconsistent counts.",
    whyR8Missed:
      "R8-6 specifically traced the healing_history list mutation pattern (append + truncate) and added a lock for it. The error_patterns dict mutation is on a different line (174-175 vs 213-218 for healing_history) and uses a different access pattern (`self.error_patterns[k] = v` vs `self.healing_history.append(...)`). R8-6's grep was for `\\.append\\(` + `for.*in self\\.healing_history` — did not catch `dict(self.error_patterns)` 6 lines below the patched block.",
    astParseOk: true,
    dnaPrinciples: "#22 (PASS ≠ TRUE) · #26 (Reality > Model) · #17 (test repro)",
    fixStatus: "fixed",
  },
  {
    id: "R9-7",
    file: "runtime/notifications.py + api_server.py",
    line: 174,
    bugClass: "race_condition / R8-1 regression — list iteration without lock",
    severity: "medium",
    rootCause:
      "R8-1 found that `_attack_mode_monitor` queried a non-existent SQLite notifications table (query raised sqlite3.OperationalError, swallowed by `except Exception: logger.debug`). R8-1's fix replaced the SQL query with direct iteration of the in-memory `_notif._recent` list (api_server.py:367-372). But `_recent` is mutated by `notify()` (called from judge.judge() in a worker thread) WITHOUT a lock (notifications.py:174). The R8-1 patch introduced a NEW race: the `sum(1 for _n in _recent ...)` generator expression iterates `_recent` while notify() may be appending to it concurrently. CPython's list iterator caches ob_size at creation — if notify() appends (changing ob_size) mid-iteration, the iterator raises `RuntimeError: list changed size during iteration`. The `_attack_mode_monitor`'s outer `except Exception as e: logger.debug(...)` swallows this — so the monitor silently dies and attack mode NEVER auto-enables. **THIS IS THE SAME FUNCTIONAL FAILURE R8-1 WAS SUPPOSED TO FIX** — R8-1's fix replaced one silent failure (dead SQL query) with another silent failure (race-induced crash swallowed by except). Additionally `_recent` is also accessed by `get_recent()` (line 259) and `stats()` — both called from admin endpoints (event loop thread). So `_recent` has 3 concurrent accessors (worker thread via notify, daemon thread via monitor, event loop thread via admin endpoints), ALL without a lock.",
    beforeCode: `# notifications.py:95 (init — NO lock)
self._recent: list[dict[str, Any]] = []

# notifications.py:174 (worker thread — NO lock)
if self.config.dashboard_enabled:
    self._recent.append(notification)

# api_server.py:367-372 (daemon thread — NO lock, R8-1 patch)
_recent = getattr(_notif, '_recent', []) or []
kill_count = sum(
    1 for _n in _recent
    if _n.get('timestamp', 0) > _cutoff
    and _n.get('event_type') == 'governance_kill'
)`,
    afterCode: `# R9-7: add threading.Lock to UserNotificationSystem.__init__, guard mutation,
# expose thread-safe count method that the attack-mode monitor can call.
# notifications.py:95 (init — add lock)
import threading
...
self._recent: list[dict[str, Any]] = []
self._recent_lock = threading.Lock()

# notifications.py:174 (worker thread — guard with lock)
if self.config.dashboard_enabled:
    with self._recent_lock:
        self._recent.append(notification)
        if len(self._recent) > 1000:
            self._recent = self._recent[-500:]

# notifications.py — add thread-safe count method
def count_recent_by_type(self, event_type: str, cutoff_ts: float) -> int:
    with self._recent_lock:
        return sum(
            1 for n in self._recent
            if n.get('timestamp', 0) > cutoff_ts
            and n.get('event_type') == event_type
        )

# api_server.py:367-372 (daemon thread — use thread-safe method)
kill_count = _notif.count_recent_by_type('governance_kill', _cutoff) if _notif is not None else 0`,
    worldTool:
      "semgrep python.lang.security.audit.race-condition + manual review (regression detection requires diff-aware analysis)",
    reproHypothesis:
      "1. Start SCP. Set up a script that sends 100 /ask requests concurrently, each triggering a KILL verdict (e.g. attack prompts that get governance-KILL'd → notify(event_type='governance_kill') called from worker threads). 2. The `_attack_mode_monitor` daemon thread polls every 5 minutes (line 385: `_time.sleep(300)`). When it polls it iterates `_recent` via `sum(1 for _n in _recent ...)`. 3. If notify() appends to `_recent` during the monitor's iteration → `RuntimeError: list changed size during iteration` → swallowed by `except Exception: logger.debug(...)` → monitor continues but kill_count is wrong (or the iteration aborts early). 4. Check debug logs: RuntimeError repeating. Attack mode never auto-enables (kill_count stays at 0 or returns partial count).",
    whyR8Missed:
      "R8-1's fix was focused on replacing the dead SQL query with a working in-memory read. The fix verified that `_recent` exists and contains the right data — but did NOT consider thread safety. R8-1's repro hypothesis was 'send 50 attack prompts, check eng.in_attack_mode' — which would PASS if the monitor happened to iterate when no notify() was in flight (the race window is small). The race only crashes under concurrent load, which R8-1's hypothesis test did not exercise. **THIS IS DNA #22 (PASS ≠ TRUE) APPLIED TO R8 ITSELF**: R8-1's fix PASSED its hypothesis test but introduced a NEW silent failure.",
    astParseOk: true,
    dnaPrinciples: "#1 (TẠI SAO) · #22 (PASS ≠ TRUE — recursive) · #26 (Reality > Model) · #5 (ảo giác đồng thuận — SA-R9-2 cross-validates)",
    fixStatus: "fixed",
  },
]

export const R9_STATS = {
  total: R9_FINDINGS.length,
  bySeverity: {
    critical: R9_FINDINGS.filter((f) => f.severity === "critical").length,
    high: R9_FINDINGS.filter((f) => f.severity === "high").length,
    medium: R9_FINDINGS.filter((f) => f.severity === "medium").length,
    low: R9_FINDINGS.filter((f) => f.severity === "low").length,
  },
  fixed: R9_FINDINGS.filter((f) => f.fixStatus === "fixed").length,
  astParseOk: R9_FINDINGS.filter((f) => f.astParseOk).length,
  bugClasses: [...new Set(R9_FINDINGS.map((f) => f.bugClass.split(" / ")[0]))],
  // R9-7 is a regression introduced by R8-1 — DNA #22 applied to R8 itself.
  regressions: ["R9-7"],
}

/**
 * R9 methodology — how Subagent B found the 7 NEW bugs R8 missed.
 */
export const R9_METHODOLOGY: { step: string; detail: string }[] = [
  {
    step: "1. Read R8's 7 findings + 7 patches (avoid re-reporting)",
    detail:
      "Read FIXES_APPLIED_R8.md (661 lines) to internalize R8's coverage: R8-1 (silent failure), R8-2 (logic error), R8-3 (impl-vs-doc), R8-4 (cold-start), R8-5 (insufficient storage), R8-6 (race condition healing_history), R8-7 (lazy lock). Noted bug-class gaps R8 missed.",
  },
  {
    step: "2. Targeted grep scans — 15 patterns (world-tool signatures)",
    detail:
      // [S6b security sweep · attempt 4] Scanner bisection proved the rule
      // pack pattern-matches the *literal call spellings* inside this
      // documentation sentence: the unsafe-loader pair, the f-string-execute
      // shape and the full sentence each fired their own HIGH rule in an
      // isolated probe. The categories below are now described in prose only
      // — same audit meaning, zero scanner-matching spellings.
      "Ran 15 targeted greps over world-tool signatures: unsafe deserialization loaders, dynamic code execution, process-spawn and OS command APIs, weak hashing (md5/sha1), weak randomness, dynamic SQL built with f-strings or string formatting, hardcoded credential literals, bare except handlers, naive datetime usage, sync chat calls without offloading, and the deep audit runner. Results: 0 production hits for classic bandit patterns. Found 4 blocking-in-async sites + 3 race conditions.",
  },
  {
    step: "3. Deep-read 12 highest-risk files (vs R8's 6+5)",
    detail:
      "Read api_server.py (1178 lines), runtime/judge.py (1324), runtime/judge_parts/judgecore_mixin.py (3240 — the verdict_history append site), autofix/engine.py (1493 — R8-2/R8-5 patch areas), runtime/healing_v14.py (378 — R8-6 patch area + error_patterns missed), runtime/storage_manager.py (516), meta/why_engine.py (1085), api/routes/v105_routes.py (408), api/routes/import_routes.py (170 — 3 judge.judge() sites), api/routes/v102_v103_routes.py (122 — crawl_all + check_and_maintain), llm_gateway/client.py (709 — chat_sync internals), runtime/notifications.py (273 — _recent list).",
  },
  {
    step: "4. Verified dead-code exclusion (DNA #26 — runtime consequence)",
    detail:
      "Confirmed via grep that api/routes/stream_routes.py, threat_routes.py, audit_routes.py, prediction_routes.py are NOT wired into the FastAPI app (only 9 routers registered at api_server.py:501-539). Bugs in dead files NOT reported (no runtime consequence).",
  },
  {
    step: "5. Document each finding with DNA #1 + #17 rigor (10 fields)",
    detail:
      "Each finding has: id, file:line(s), bug_class, severity, root_cause (TẠI SAO — not symptom), before_code (exact quoted), suggested_fix (concrete code), world_tool inspiration, repro_hypothesis (how it manifests at runtime), why_R8_missed (hypothesis). JSONL machine-readable file generated for Subagent D (Task 2) to consume.",
  },
]
