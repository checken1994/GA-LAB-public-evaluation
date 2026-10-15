/**
 * Round 8 Self-Audit — auditing the auditor (separate file per task)
 *
 * DNA #22 (PASS ≠ TRUE): R7 dashboard makes claims ("0 lint errors", "14
 * findings", "8 implemented improvements", "40 files created", etc.). Round 8
 * does NOT trust those claims — it audits each one against Reality (the actual
 * files in /home/z/my-project/src + /tmp/scp-r7-extract/scp-full-package/scp/).
 *
 * Each SelfAuditFinding documents a single R7 claim, what Reality shows, and
 * what we did to correct the discrepancy. Findings SA-1..SA-8 below.
 *
 * Methodology (see round8Methodology): read every data file + every component,
 * grep the SCP Python codebase for the cited patterns, count files with `ls`,
 * cross-reference executive-summary numbers against detailed listings.
 */

export type SelfAuditSeverity = "critical" | "high" | "medium" | "low"

export interface SelfAuditFinding {
  id: string
  r7Claim: string
  reality: string
  severity: SelfAuditSeverity
  dnaPrinciple: string
  rootCause: string
  fix: string
}

export const selfAuditFindings: SelfAuditFinding[] = [
  {
    id: "SA-1",
    r7Claim:
      "R7 report §1.2 + §8.1 claim '0 lint errors, 0 console warnings' after `bun run lint`.",
    reality:
      "`bun run lint` against the freshly-extracted R7 dashboard reported 1 error: `react-hooks/set-state-in-effect` in `src/components/layout/header.tsx` (the dark-mode toggle used `useEffect` + `setState`). After Main agent's fix (useSyncExternalStore), lint is genuinely 0 errors. R7's '0 lint errors' was a PASS-without-TRUE claim — the lint never actually ran clean.",
    severity: "high",
    dnaPrinciple: "#22 (PASS ≠ TRUE)",
    rootCause:
      "R7 dashboard was authored from a template/IDE view that did not enforce the `react-hooks` plugin rules at write time. The eslint.config.mjs has the rule enabled, but the report was written before running lint against the final code.",
    fix:
      "Main agent (Task 1) replaced the useEffect+setState pattern in header.tsx with `useSyncExternalStore` — the React 19 idiom for subscribing to an external store (the theme singleton). Re-ran `bun run lint` → 0 errors, 0 warnings. SA-1 documents this as the first Round 8 finding.",
  },
  {
    id: "SA-2",
    r7Claim:
      "R7 report §1.2 + §9 headline: '12 Autofix improvements (8 implemented, 1 in-progress, 3 planned)'.",
    reality:
      "The data file `autofix-improvements.ts` actually contains 9 `status: 'implemented'` entries (IMP-1..IMP-8 + IMP-10), 1 `in-progress` (IMP-9), and 2 `planned` (IMP-11, IMP-12). The `IMPROVEMENT_STATS` object computes this dynamically: 9/1/2. R7 report's own §4 table ALSO lists 9 implemented — so the executive summary (8/1/3) contradicts its own detailed table. The dashboard renders the correct 9/1/2 via dynamic stats; the markdown report's headline number is just wrong.",
    severity: "medium",
    dnaPrinciple: "#22 (PASS ≠ TRUE) + #26 (Reality > Model)",
    rootCause:
      "Executive summary was hand-written from memory before the data file was finalized; the detailed table was written last and reflects the actual array. The two were never reconciled. §9 'Câu hỏi tiếp' even misclassifies IMP-9 (in-progress) as 'planned' — second contradiction in the same report.",
    fix:
      "Round 8 self-audit surfaces this as a documentation drift finding. The dashboard already shows the correct 9/1/2 (computed from the array). R7 markdown report should be amended: replace '8 implemented, 1 in-progress, 3 planned' with '9 implemented, 1 in-progress, 2 planned'.",
  },
  {
    id: "SA-3",
    r7Claim:
      "R7 report §1.1 + §1.2: '40 Files tạo/sửa — 12 data files + 20 components + 3 API routes + 5 config/layout'.",
    reality:
      "Actual count in /home/z/my-project/src: 13 data files (`ls src/lib/audit-data/*.ts` = 13), 23 components (layout 3 + dashboard 4 + dna 1 + audit 3 + autofix 5 + scanners 1 + bugs 6 = 23), 3 R7 API routes (audit/autofix/scanners; `api/route.ts` is a leftover 'Hello, world' scaffold, not R7), 4 config/layout files (`layout.tsx`, `page.tsx`, `globals.css`, `eslint.config.mjs`). True total = 13+23+3+4 = 43, not 40. R7 report undercounted 3 of 4 buckets. The report's own §2 detailed file listing shows 13+23+3+4 entries — so §1.2 executive summary contradicts §2 listing.",
    severity: "medium",
    dnaPrinciple: "#26 (Reality > Model) + #19 (Tầng kiểm toán bằng chứng)",
    rootCause:
      "Executive summary numbers were drafted early ('round numbers' aesthetic) and never reconciled with the actual file manifest in §2. The '5 config/layout' bucket is especially wrong — only 4 such files exist; the report likely double-counted `package.json` or `tsconfig.json` (which were pre-existing scaffold, not R7-modified).",
    fix:
      "Round 8 self-audit corrects the count to 43 (13+23+3+4). Future reports should derive counts from `git diff --stat` rather than hand-counting.",
  },
  {
    id: "SA-4",
    r7Claim:
      "R7-2 (CRITICAL): 'Tor exit-node detection ALWAYS False — task GC'd before completion (RUF006)' at `scp/security/threat_detector.py:181`.",
    reality:
      // [Fix 4-c-022 · Task Local-C] SA-4 ITSELF IS FALSE (DNA #22 at recursion
      // level 3: R7 claimed a bug → R8 audited R7 and said 'R7-2 fix is fictional'
      // → R20 verifies R8's correction was wrong and R7-2 fix was actually applied).
      //
      // Original SA-4 narrative claimed the beforeCode was 'a fictional paraphrase'
      // and that the R7-2 narrative was 'unsupported by the code'. Both claims are
      // themselves FALSE: the actual fix (_tor_refresh_tasks: set + add_done_callback
      // pattern shown in bugs-critical.ts:83-94 afterCode) IS present at
      // scp/api/_lifespan.py:393-445 — verified by grep + read. The R7-2 fix is REAL.
      //
      // The auditor likely ran grep at a snapshot when _tor_refresh_tasks had not yet
      // landed; later rounds (R12+) added it. The dashboard's own self-audit
      // shipped a correction (SA-4) that was itself wrong, and the dashboard
      // displayed SA-4 as evidence of the 'auditor's paradox' — when in reality
      // SA-4 IS the paradox.
      //
      // Corrected in Phase 6 (Fix 4-c-005) which removed the fabricated beforeCode
      // snippet, and Phase Local-C (Fix 4-c-022) which flips SA-4's verdict from
      // 'claim not substantiated' to 'CORRECTION: SA-4 finding was FALSE — R7-2
      // fix IS real (verified at scp/api/_lifespan.py:393-445 via reality_4-c-022.py)'.
      "CORRECTION (Fix 4-c-022): SA-4 finding itself was FALSE. R7-2 fix IS real — verified by grep at `scp/api/_lifespan.py:393-445`: the file contains `_tor_refresh_tasks: set = set()`, `_tor_refresh_tasks.add(_tor_task)`, and `task.add_done_callback(_tor_refresh_tasks.discard)` — exactly the pattern shown in `bugs-critical.ts:83-94` afterCode. The original SA-4 narrative (below) claimed the R7-2 fix was 'fictional' and 'unsupported by the code' — that was the auditor's auditor being wrong, not the auditor. DNA #22 at recursion level 3: R7 (claim) → R8 SA-4 (claim) → R20 verifies R8 was wrong. Original SA-4 narrative (retained for traceability): line 181 of threat_detector.py is `self._tor_last_refresh = 0` (an init line, not a bug). The RUF006 'task-not-stored' bug the dashboard describes does NOT exist in the CURRENT codebase (the task IS stored in a module-level holder at `scp/api/_lifespan.py:180` `_background_task_holder['tor_refresh'] = asyncio.create_task(_tor_refresh_loop())`). The beforeCode previously shown in `bugs-critical.ts` (an `asyncio.create_task(...)` call labeled with a `# RUF006!` inline comment) was a fictional paraphrase of the R7 auditor's mental model — REMOVED in Phase 6-A (Fix 4-c-005).",
    severity: "high",
    dnaPrinciple: "#22 (PASS ≠ TRUE, recursion level 3 — auditor's auditor lies) + #26 (Reality > Model) + #14 (evidence must match)",
    rootCause:
      "SA-4 finding itself was FALSE — the R8 auditor ran grep at a snapshot when `_tor_refresh_tasks` had not yet landed (likely pre-R12). Subsequent rounds added the fix at `scp/api/_lifespan.py:393-445` but SA-4 was never re-verified. The dashboard displayed SA-4 as evidence of the 'auditor's paradox' — when in reality SA-4 IS the paradox (the auditor's auditor was wrong, not the auditor). DNA #22 recursion level 3.",
    fix:
      "Phase 6-A (Fix 4-c-005) already removed the fabricated beforeCode snippet from `bugs-critical.ts`. Phase Local-C (Fix 4-c-022) updates SA-4's `reality` field to record that the finding was FALSE — R7-2 fix IS real, verified at `scp/api/_lifespan.py:393-445`. Reality-test: tests/reality-tests/reality_4-c-022.py greps `_tor_refresh_tasks` against the actual file and asserts the pattern is present. The dashboard's display of SA-4 is retained for traceability of the recursion (R7 → R8 → R20), but the verdict is now CORRECT: R7-2 was a real bug, the fix IS applied, and the R8 auditor's claim that the fix was 'fictional' was itself fictional.",
  },
  {
    id: "SA-5",
    r7Claim:
      "R7-1 (CRITICAL): 'None>0 TypeError cluster — 8 sites, 5 files. R6-1 fix INCOMPLETE — only fixed 2/8 sites.' beforeCode shows `result = await fetch_crypto_price(symbol); if result.value > 0:`.",
    reality:
      "Two material errors. (A) The `beforeCode` is paraphrased, not actual code: real line 330 of conversionslm.py is `result = fetch_crypto_price(coin)` (SYNC, variable `coin`, not `await ... symbol`). (B) The 'R6-1 only fixed 2/8' narrative is FALSE — `rg \"is not None and .+ > 0\"` finds 9 sites ALREADY FIXED across 5 files (conversionslm ×2, misc_slms2 ×2, misc_slm ×2, numeric_data_slm ×2, chem_reality_astro ×1). R6-1 actually fixed ~8 sites, not 2. AND one site remains genuinely UNFIXED: `scp/runtime/slms_parts/chemistryslm.py:281` (`if result[\"value\"] > 0:` with no None guard) — a real None-comparison bug that R7-1 should have caught but the dashboard does not list chemistryslm.py anywhere. The auditor over-stated R6-1's incompleteness while missing the one site R6-1 actually left unfixed.",
    severity: "critical",
    dnaPrinciple: "#22 (PASS ≠ TRUE) + #26 (Reality > Model) + #5 (Ảo giác đồng thuận)",
    rootCause:
      "The R7 auditor likely trusted the R5/R6 narrative ('R6-1 was incomplete') without re-running `rg 'value > 0'` against the current codebase. The '8 sites, 5 files' figure was carried forward from R5 without verification. The beforeCode was reconstructed from memory rather than copied from git history, which is why the variable name and sync/async signature don't match.",
    fix:
      "Round 8 self-audit: (1) file:line for R7-1 should point to `scp/runtime/slms_parts/chemistryslm.py:281` — the one site that genuinely lacks a None guard. (2) The 'R6-1 only fixed 2/8' claim should be retracted — R6-1 fixed ~8 sites. (3) beforeCode should be replaced with the actual current line from chemistryslm.py:281. (4) A new fix is needed: add `if result['value'] is not None and result['value'] > 0:` at chemistryslm.py:281 (delegates to Task 2-c).",
  },
  {
    id: "SA-6",
    r7Claim:
      "scanners.ts header comment (lines 1-8): '18 SCP scanners + 6 external tools. Mỗi scanner có blind-spot được map.'",
    reality:
      "The `SCP_SCANNERS` array in scanners.ts actually contains 7 external entries: ext-ruff, ext-pyflakes, ext-pylint, ext-vulture, ext-mypy, ext-bandit, ext-hypothesis. The R7 markdown report's '25 scanners (18 SCP + 7 external)' is correct, but the data file's own header comment says '6 external' — internal inconsistency. The dashboard's scanner-grid renders 25 cards correctly (computed from the array), but a developer reading the file header would be misled.",
    severity: "low",
    dnaPrinciple: "#19 (Tầng kiểm toán bằng chứng — khả năng quan sát)",
    rootCause:
      "The header comment was written when only 6 external tools existed (R6 baseline); when hypothesis was added as source #7 in R7, the array was updated but the comment was not. Classic stale-comment drift.",
    fix:
      "Round 8 self-audit surfaces this. Comment should be updated to '18 SCP scanners + 7 external tools (6 static + 1 property-based: hypothesis)'. This is documentation-only; no runtime behavior affected.",
  },
  {
    id: "SA-7",
    r7Claim:
      "sources.ts header comment (lines 1-9): 'Round 7 dùng 7 nguồn (R6 dùng 6 — R7 thêm property-based testing).' R7 markdown report §1.2 says '9 audit sources'.",
    reality:
      "The `AUDIT_SOURCES` array actually contains 9 entries: ruff, pyflakes, pylint, vulture, mypy, bandit, scp-scanners (1 entry representing 18 sub-scanners), reality-log, hypothesis. The R7 markdown report's '9 audit sources' matches the array count. The data file's own header comment uses '7 nguồn' (lineage groups: 6 static + 1 property-runtime) which is a different counting basis than the array length (9). Two valid but inconsistent counting bases — 'nguồn' is overloaded between lineage groups (7) and array rows (9).",
    severity: "low",
    dnaPrinciple: "#14 (Đồng thuận ≠ đúng — lineage ≠ count)",
    rootCause:
      "The term 'nguồn' (source) is used in two senses: (a) lineage groups for cross-validation (7 groups, the basis for DNA #14's 'cross-lineage agreement' rule), and (b) array entries in the data file (9 rows, treating SCP's 18 scanners as 1 grouped entry plus reality-log). The header comment uses sense (a); the array and the markdown '9 audit sources' use sense (b). No reconciliation between the two senses.",
    fix:
      "Round 8 self-audit recommends the comment be rewritten as: 'Round 7 uses 9 source entries representing 7 independent lineage groups (DNA #14: count lineages, not entries).' The dashboard's source-comparison table correctly shows 9 rows.",
  },
  {
    id: "SA-8",
    r7Claim:
      "Sidebar SheetDescription: 'Điều hướng nhanh đến 14 phần của báo cáo audit Round 7.' R7 markdown §8.3 also claims 'Sidebar 14 items with scroll-spy active state'.",
    reality:
      "The `SECTIONS` array in `src/components/layout/sidebar.tsx` actually contains 15 entries (numbered 01 through 15: dashboard, DNA, methodology, sources, audit, autofix, improvements, scanners, bugs-critical, bugs-dead, bugs-type, bugs-race, bugs-sql, bugs-resource, download). The SheetDescription string and the markdown report both say '14' — off by one in two places. The visual nav renders 15 items correctly (mapped from the array), but the screen-reader description misleads assistive tech.",
    severity: "low",
    dnaPrinciple: "#26 (Reality > Model) + #11 (Human-in-the-loop thật — accessibility)",
    rootCause:
      "The sidebar was likely first built with 14 items, then a 15th ('download') was added without updating the description string. The markdown report's '14 items' claim was copied from the same stale mental model. Accessibility text is rarely re-verified.",
    fix:
      "Round 8 self-audit surfaces this. SheetDescription should be updated to '15 phần'. The markdown §8.3 '14 items' claim should also be amended. No functional impact — scroll-spy still works because it iterates the array.",
  },
]

export const selfAuditStats = {
  total: selfAuditFindings.length,
  bySeverity: {
    critical: selfAuditFindings.filter((f) => f.severity === "critical").length,
    high: selfAuditFindings.filter((f) => f.severity === "high").length,
    medium: selfAuditFindings.filter((f) => f.severity === "medium").length,
    low: selfAuditFindings.filter((f) => f.severity === "low").length,
  },
  // Total distinct R7 claims that Round 8 explicitly verified against Reality.
  // Includes the 8 SA-N findings above PLUS 5 claims that were CONFIRMED TRUE
  // (14 findings/4-5-3-2 severity, 26 DNA, 9 sources, 25 scanners, 4 tiers + 7 phases).
  claimsVerified: 13,
  claimsConfirmedTrue: 5,
  claimsFoundFalse: 8,
}

/**
 * How the self-audit was performed — each step is reproducible.
 * Rendered in the dashboard so readers can verify our method, not just our results.
 */
export const round8Methodology: { step: string; detail: string }[] = [
  {
    step: "1. Read every R7 data file",
    detail:
      "Read all 13 files in src/lib/audit-data/ (round7.ts, autofix-improvements.ts, dna.ts, scanners.ts, sources.ts, autofix-engine.ts, bugs-critical.ts, bugs-dead-controls.ts, bugs-type-errors.ts, bugs-resource-leaks.ts, bugs-race.ts, bugs-sql.ts, index.ts). Counted array lengths, status fields, severity fields by hand.",
  },
  {
    step: "2. Cross-reference markdown report vs data files",
    detail:
      "Compared each headline number in SCP_DNA_AUDIT_ROUND7_CHANGES.md §1.1/§1.2 against the actual array length and computed stats. Flagged every mismatch (e.g. '8 implemented' in §1.2 vs 9 `status: implemented` entries in the array).",
  },
  {
    step: "3. Grep the SCP Python codebase for cited patterns",
    detail:
      "For each finding's `file:line` and `beforeCode`, ran `sed -n 'N,Mp'` and `rg` against /tmp/scp-r7-extract/scp-full-package/scp/ to verify the file exists, the line number is in range, and the beforeCode pattern actually appears (or has already been fixed).",
  },
  {
    step: "4. Count files with ls / find",
    detail:
      "Used `ls src/lib/audit-data/*.ts | wc -l`, `find src/components/{layout,dashboard,...} -name '*.tsx' | wc -l`, etc. to verify the '40 files created' claim. Excluded pre-existing scaffold (api/route.ts 'Hello, world') from R7 counts.",
  },
  {
    step: "5. Re-run lint to confirm SA-1",
    detail:
      "Ran `bun run lint` against the extracted R7 dashboard. Confirmed Main agent's earlier finding: header.tsx had `react-hooks/set-state-in-effect` (R7 had claimed '0 lint errors'). After Main's useSyncExternalStore fix, lint is now genuinely 0 errors — SA-1 documents the original discrepancy.",
  },
]
