/**
 * Round 10 Self-Audit — auditing the auditor-of-the-auditor-of-the-auditor
 * (DNA #22 recursive, level 4 — Round 10 Self-Audit of R8)
 *
 * The recursion is now visible at 4 levels:
 *   R7 (fictional beforeCode per SA-5) →
 *   R7-Full (audited R7 — found 8 discrepancies SA-1..8) →
 *   R8 (audited R7-Full — found 10 discrepancies SA-R8-1..10 + 7 NEW bugs) →
 *   R9 / Round 10 Self-Audit (this audit — audits R8, finds 6 discrepancies
 *   SA-R9-1..6, including a HIGH regression in R8-1).
 *
 * **SA-R9-2 (HIGH) cross-validates R9-7 (MEDIUM):** Subagent A (Round 10
 * Self-Audit) and Subagent B (R9 bugs) independently found the SAME race
 * condition in R8-1's _recent list iteration. Two independent observers
 * converging on the same bug is DNA #5 (ảo giác đồng thuận) in reverse —
 * here the consensus is REAL because Reality is the source (DNA #26).
 *
 * Source: scp/audit_r9/round10_self_audit.md + round10_findings.json
 */

export type SAR9Severity = "critical" | "high" | "medium" | "low"

export interface Round10Finding {
  id: string
  severity: SAR9Severity
  dna: string
  r8Claim: string
  reality: string
  r9Disposition: string
  evidence: string
  verdict: "FALSE" | "TRUE" | "UNVERIFIABLE"
  crossValidation?: string
}

export const ROUND10_FINDINGS: Round10Finding[] = [
  {
    id: "SA-R9-1",
    severity: "medium",
    dna: "#14 (Số đếm phải khớp) + #19 (Lineage) + #22 (PASS ≠ TRUE)",
    r8Claim:
      "AUTOFIX_V3_MANIFEST.md has inconsistent LOC totals: summary table (line 28) says 'Total new v3 LOC: 2,582'; footer (line 269) says 'Total NEW v3 LOC: 2,585'; per-file (line 264) says 'semantic_equiv.py (IMP-15) — 396 LOC'. Main R8 report (SCP_DNA_AUDIT_ROUND8_CHANGES.md) says '2,586 LOC'.",
    reality:
      "Actual: ast_diff_cache.py=412, confidence_ranker.py=402, semantic_equiv.py=397 (NOT 396), blast_radius.py=372, auto_rollback.py=575, parallel_scanner.py=428. Sum = 2,586 (matches main report). Manifest has TWO different wrong numbers (2,582 + 2,585) AND wrong per-file LOC for semantic_equiv.py.",
    r9Disposition:
      "Manifest should be corrected: summary table 2,582→2,586, footer 2,585→2,586, per-file semantic_equiv 396→397. Main R8 report's '2,586' is correct — no change needed there.",
    evidence:
      "$ wc -l on all 6 v3 files → 412+402+397+372+575+428 = 2586 total. Manifest summary table claims 2,582 (off by 4). Manifest footer claims 2,585 (off by 1, due to semantic_equiv claimed as 396 not 397). Main R8 report claims 2,586 (CORRECT).",
    verdict: "FALSE",
  },
  {
    id: "SA-R9-2",
    severity: "high",
    dna: "#22 (PASS ≠ TRUE — recursive) + #26 (Reality > Model) + #9 (No harm)",
    r8Claim:
      "R8-1 fix in api_server.py:367-372 + api/_lifespan.py:295-300: 'Query the in-memory UserNotificationSystem._recent list directly' to count governance_kill events in last 10min.",
    reality:
      "The fix iterates `_notif._recent` via generator expression `sum(1 for _n in _recent if ...)` with NO lock and NO snapshot copy. `_recent` is mutated by `notify()` (runtime/notifications.py:174 `self._recent.append(notification)`) called from judge.judge() in V98 pipeline thread + sync API endpoint threads. Iteration runs in background _attack_mode_monitor daemon thread. CPython list iterator caches ob_size; concurrent append raises `RuntimeError: list changed size during iteration`. The exception is swallowed by the existing `try/except Exception as e: logger.debug(...)` at api_server.py:383-384 — silently killing the monitor (same silent-failure pattern R8-1 was supposed to fix). **This is the SAME bug class as R8-6** (which R8 fixed for healing_history by adding threading.Lock). R8 was inconsistent: applied the lock to healing_history but NOT to _recent.",
    r9Disposition:
      "Add threading.Lock to UserNotificationSystem.__init__ (e.g., self._recent_lock = threading.Lock()). Guard notify() mutation with lock. Guard R8-1 iteration with snapshot pattern: `with _notif._recent_lock: snapshot = list(_notif._recent)` then iterate snapshot. Mirrors R8-6 pattern exactly. **Subagent D patched this as R9-7** in Task 2.",
    evidence:
      "api_server.py:367-372 has `kill_count = sum(1 for _n in _recent if ...)` with no lock. Compare to R8-6 fix at healing_v14.py:224+360 which uses `with self._history_lock: snapshot = list(self.healing_history)`. R8-6's own description explicitly identifies the mutation+iteration-without-lock pattern as the bug — yet R8-1 introduces the same pattern. notify() is called from 6+ sites in judge.py + judge_parts/judgecore_mixin.py + judge_parts/judgebg_mixin.py.",
    verdict: "FALSE",
    crossValidation:
      "DNA #5 (ảo giác đồng thuận — cross-validation): Subagent B independently found the SAME race condition and reported it as R9-7. Two independent subagents (A and B) converging on the same bug is strong evidence the bug is REAL (not a hallucination) — Reality is the source (DNA #26).",
  },
  {
    id: "SA-R9-3",
    severity: "medium",
    dna: "#22 (PASS ≠ TRUE) + #9 (No harm) + #26 (Reality > Model)",
    r8Claim:
      "R8-1 fix description: 'Fix: đếm trực tiếp từ in-memory UserNotificationSystem._recent, lọc theo event_type=governance_kill trong 10 phút gần nhất.' (implies bounded/cheap iteration)",
    reality:
      "UserNotificationSystem._recent grows UNBOUNDED — notify() at runtime/notifications.py:174 does `self._recent.append(notification)` with NO trim, NO maxlen, NO deque. R8-1's fix iterates this list every 5 minutes (300s sleep). Original SQL approach would have been O(1) per poll (COUNT with WHERE timestamp > ? using index). New approach is O(N) per poll where N = total notifications ever sent. Worst case: 1 notif/sec × 1 year = 31.5M entries × ~200 bytes/dict = ~6.3 GB RAM + ~5-10s CPU per poll. R8-1 EXPOSES pre-existing unbounded-growth bug (SQL path failed silently, so list was never iterated before R8-1).",
    r9Disposition:
      "In UserNotificationSystem.notify() (separate fix): add trim after append (`if len(self._recent) > 1000: del self._recent[:-1000]`) OR use collections.deque(maxlen=1000). In R8-1 fix: use snapshot under lock (see SA-R9-2 fix) AND document iteration cost. File separate R10 bug for unbounded _recent growth root cause.",
    evidence:
      "grep -nE '_recent' on notifications.py → 4 matches: line 95 (init, no maxlen), 174 (append, no trim), 257+259 (get_recent slice — doesn't trim list). No deque, no `if len > MAX: del`, no periodic prune.",
    verdict: "FALSE",
  },
  {
    id: "SA-R9-4",
    severity: "low",
    dna: "#19 (Lineage rõ ràng) + #26 (Reality > Model)",
    r8Claim:
      "R8-3 fix code comment at runtime/storage_manager.py:204-205: `# gen=2 → .1.gz index 0` and `# gen=2 → .2.gz index 1`",
    reality:
      "For gen=2: `src_path = gz_paths[gen-1] = gz_paths[1] = .2.gz` (NOT `.1.gz` as comment claims), `dst_path = gz_paths[gen] = gz_paths[2] = .3.gz` (NOT `.2.gz` as comment claims). The CODE is correct (moves `.2→.3` for gen=2, then `.1→.2` for gen=1, then writes new `.1`); only the inline COMMENT is misleading.",
    r9Disposition:
      "Update inline comments to: `# gen=2 → src=.2.gz (index 1), dst=.3.gz (index 2); gen=1 → src=.1.gz (index 0), dst=.2.gz (index 1)`. Cosmetic fix only — no behavioral change.",
    evidence:
      "Trace: `gz_paths = [f.with_suffix(f'.{gen}.gz') for gen in range(1, 4)]` → `[.1.gz, .2.gz, .3.gz]`. For gen=2 (loop var), src=gz_paths[1]=.2.gz, dst=gz_paths[2]=.3.gz. Comment says src=.1.gz and dst=.2.gz — both wrong.",
    verdict: "FALSE",
  },
  {
    id: "SA-R9-5",
    severity: "low",
    dna: "#19 (Lineage) + #22 (PASS ≠ TRUE)",
    r8Claim:
      "AUTOFIX_V3_MANIFEST.md 'Integration approach (light-touch)' section: 'Each module's docstring clearly states its integration point:' (followed by a TABLE of integration points)",
    reality:
      "Each v3 module's docstring has a 'Flow:' section describing USAGE PATTERN (e.g., `before_scan: ASTDiffCache.partition_files(...)`), but does NOT explicitly state the INTEGRATION POINT (e.g., 'wire this in engine.py:apply_fix() at line N'). Only confidence_ranker.py mentions 'engine.py integration' — and it's in a code COMMENT (line 344), not in the docstring. Integration point mappings are in the manifest's TABLE, separate from module docstrings.",
    r9Disposition:
      "Reword manifest claim: 'Each module's docstring describes its Flow (usage pattern). Specific integration points in the existing codebase are listed in the table below.'",
    evidence:
      "grep -niE 'wire|standalone|engine\\.py' on all 6 v3 files → only 1 match (confidence_ranker.py:344 code comment). Each module has 'Flow:' section but no explicit integration point in docstring.",
    verdict: "FALSE",
  },
  {
    id: "SA-R9-6",
    severity: "low",
    dna: "#23 (Coverage limits, honest disclosure) + #26 (Reality > Model) + #5 (ảo giác đồng thuận)",
    r8Claim:
      "R8 claims '371/371 .py ast.parse OK' + '57 total autofix .py (51 v2 + 6 v3)'",
    reality:
      "At R9 audit time, actual counts are 377 .py + 63 autofix .py. The +6 delta is NOT an R8 inaccuracy — it is R9 Subagent C concurrently creating 6 NEW v4 modules (IMP-19..IMP-24: property_validator.py, speculative_prefixer.py, callgraph_delta.py, shadow_canary.py, policy_gate.py, type_flow_verifier.py) at timestamps 20:19-20:25, DURING my Round 10 audit. R8 v3 modules were created at 20:14 (before R9 started). R8's counts were TRUE at R8 time.",
    r9Disposition:
      "META finding for orchestrator: R9 audit is racing with R9 implementation. R9 final report should re-verify counts AFTER all subagents finish. R8 is INNOCENT of any count inaccuracy. Final R9 counts should be: 377 .py, 63 autofix .py (51 v2 + 6 v3 + 6 v4), 6,904 LOC v3+v4 (2,586 v3 + 4,318 v4).",
    evidence:
      "ls -la on v3 files → all timestamped 20:14 (R8 time). ls -la on v4 files → timestamped 20:19-20:25 (R9 time, during this audit). 6 v4 files declare themselves as 'R9 v4 IMP-19..24' in first-line docstrings.",
    verdict: "TRUE",
  },
]

export const ROUND10_STATS = {
  total: ROUND10_FINDINGS.length,
  bySeverity: {
    critical: ROUND10_FINDINGS.filter((f) => f.severity === "critical").length,
    high: ROUND10_FINDINGS.filter((f) => f.severity === "high").length,
    medium: ROUND10_FINDINGS.filter((f) => f.severity === "medium").length,
    low: ROUND10_FINDINGS.filter((f) => f.severity === "low").length,
  },
  // 25 R8 claim groups audited: 19 TRUE, 6 FALSE, 8 UNVERIFIABLE.
  claimsAudited: 25,
  claimsTrue: 19,
  claimsFalse: 6,
  claimsUnverifiable: 8,
  // 7/7 R8 patches present + structurally correct
  patchesPresent: "7/7 (R8-1 through R8-7 all present at claimed file:line)",
  patchesCorrect: "7/7 structurally correct (no missing patches, no wrong-file-line citations); R8-1 has a HIGH regression (SA-R9-2 / R9-7)",
  // 6/6 v3 modules real Python, smoke-tested
  v3ModulesReal: "6/6 (all ast.parse OK, all import cleanly, all smoke-testable with documented API)",
  // SA-R9-2 + R9-7 cross-validation (DNA #5)
  crossValidationCount: 1,
}

/**
 * Round 10 methodology — 5 reproducible steps (DNA #19 + #22).
 */
export const ROUND10_METHODOLOGY: { step: string; detail: string }[] = [
  {
    step: "1. Read the R8 reports fully",
    detail:
      "Read all 5 R8 reference docs in docs/: SCP_DNA_AUDIT_ROUND8_CHANGES.md (412 lines), ROUND9_SELF_AUDIT.md (472 lines), R8_FINDINGS.md (485 lines), FIXES_APPLIED_R8.md (661 lines), AUTOFIX_V3_MANIFEST.md (316 lines). Extracted every concrete falsifiable claim into a list (counts, file:line citations, fix descriptions, ast.parse results, lint results, LOC numbers).",
  },
  {
    step: "2. Run Reality checks for each claim",
    detail:
      "For each claim: `python3 -c \"import ast; ast.parse(open('FILE').read())\"` for syntax validity, `grep`/`rg` (via Grep tool) for patch presence, `wc -l`/`find | wc -l` for file counts, `bun run lint` + `bun run build` for the lint claim, real Python `import` for the smoke-test claim.",
  },
  {
    step: "3. Verify each R8-1..7 patch present + CORRECT (not just present)",
    detail:
      "For each R8 patch: grep the actual fix in the actual file (e.g. R8-1 → api_server.py:354-385 + api/_lifespan.py:283-311). Read the surrounding code (~15 lines). Check for regressions (introduced bugs, missing root-cause fix, incomplete coverage of related access sites). Found R8-1 introduces a HIGH race condition regression (SA-R9-2).",
  },
  {
    step: "4. Smoke-test the 6 v3 modules — ast.parse + import + invocation",
    detail:
      "Real Python `import` for all 6 v3 files (ast_diff_cache, confidence_ranker, parallel_scanner, semantic_equiv, blast_radius, auto_rollback). All 6 import cleanly. Real invocation with documented API signatures: IMP-13 partition_files(['x']) → {scan:[], cached:[]}; IMP-14 make_fix(...); IMP-15 verify_semantic_equiv(...); IMP-16 compute_blast_radius('/tmp/nonexistent', ...) → {caller_count:0, risk_level:'LOW'}; IMP-17 register/check_regressions/unregister; IMP-18 dedup_findings([]) → [].",
  },
  {
    step: "5. Document discrepancies with exact command + output evidence",
    detail:
      "For each FALSE: wrote SA-R9-N with the claim, the reality, the exact command + output (evidence), and the R9 disposition. Marked UNVERIFIABLE anything that requires a runtime we don't have (Agent Browser checks, concurrent stress tests, in-production behavior, 12h+ runtime tests — 8 items total, orchestrator will re-verify via Agent Browser in Task 4).",
  },
]

