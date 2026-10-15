/**
 * Round 9 Self-Audit — auditing the auditor's auditor (DNA #22 recursive, level 3)
 *
 * R7 audited SCP codebase → found 14 bugs.
 * R7-Full (Round 8) audited R7 → found 8 discrepancies (SA-1..SA-8).
 * R8 (Round 9 Self-Audit) audits R7-Full → found 10 discrepancies (SA-R8-1..10).
 *
 * The recursion is now visible at 3 levels: R7 (fictional beforeCode per SA-5)
 * → R7-Full (claimed "0 lint errors" without re-running lint, documented SA-8
 * fix but didn't apply it, R7-6 wrong file:line, R7-4 "Bayesian prior"
 * fictional — same failure modes R7-Full flagged in R7) → R8 (this audit, also
 * incomplete per DNA #23). Each round finds the previous round's
 * PASS-without-TRUE violations. **The process never terminates — that is the
 * feature.** (DNA #21 + #23)
 *
 * Source: scp/audit_r8/round9_self_audit.md + scp/audit_r8/round9_findings.json
 */

export type SAR8Severity = "critical" | "high" | "medium" | "low"

export interface Round9Finding {
  id: string
  severity: SAR8Severity
  dna: string
  r7FullClaim: string
  reality: string
  evidence: string
  verdict: "FALSE" | "TRUE" | "UNVERIFIABLE"
  fix: string
}

export const ROUND9_FINDINGS: Round9Finding[] = [
  {
    id: "SA-R8-1",
    severity: "critical",
    dna: "#22 (PASS ≠ TRUE)",
    r7FullClaim:
      "R7-Full §7.1 + §1.2: '0 lint errors, 0 warnings ← R7 had 1 error (header.tsx), now genuinely 0'",
    reality:
      "`bun run lint` against the R7-Full dashboard returns 2 errors: carousel.tsx:98 (onSelect(api) → setState-in-effect) + use-mobile.ts:14 (setIsMobile in useEffect). SAME bug class as SA-1's header.tsx. R7-Full fixed header.tsx with useSyncExternalStore but never re-ran lint — so it shipped 2 MORE instances of the exact bug its own SA-1 finding raised against R7. The auditor's paradox made flesh.",
    evidence:
      "cd r7full-ref/dashboard && bun install && bun run lint → 2 errors (carousel.tsx:98, use-mobile.ts:14). react-hooks/set-state-in-effect.",
    verdict: "FALSE",
    fix:
      "R8 dashboard deletes the unused carousel.tsx and rewrites use-mobile.ts with useSyncExternalStore (same idiom as header.tsx). R8's '0 lint errors' claim is genuinely TRUE — re-verified after the fix.",
  },
  {
    id: "SA-R8-2",
    severity: "high",
    dna: "#21 (Audit the auditor) + #22 (PASS ≠ TRUE)",
    r7FullClaim:
      "R7-Full SA-8 finding: 'Sidebar 14 phần vs 15 sections — off-by-one. Fix: Updated to 15.'",
    reality:
      "The fix was documented in self-audit.ts as a recommendation but NEVER applied to the source. sidebar.tsx:114 STILL says '14 phần'. R7-Full's own self-audit finding was itself a PASS-without-TRUE: it identified the bug, wrote the fix description, then didn't apply it. Two layers of the auditor's paradox.",
    evidence:
      "grep -n '14 phần' r7full-ref/dashboard/src/components/layout/sidebar.tsx → line 114: 'Điều hướng nhanh đến 14 phần của báo cáo audit Round 7.'",
    verdict: "FALSE",
    fix:
      "R8 sidebar rewritten with correct section count + R8 sections. SheetDescription updated to accurate count.",
  },
  {
    id: "SA-R8-3",
    severity: "high",
    dna: "#19 (Lineage rõ ràng — file:line accuracy)",
    r7FullClaim:
      "R7-Full §4 table R7-6: file patched = 'runtime/judge.py' (+35 LOC, effective_weight not in voting)",
    reality:
      "The actual R7-6 patch is in runtime/judge_parts/judgecore_mixin.py + core/conflict_resolver.py, NOT runtime/judge.py. This is the SAME class of file:line inaccuracy R7-Full flagged in R7's SA-4 (R7-2 threat_detector.py:181) and SA-5 (R7-1 fictional beforeCode). The auditor committed the exact sin it accused the previous auditor of.",
    evidence:
      "grep -rn 'effective_weight' r7full-ref/scp/runtime/judge.py → 0 hits in the patched region. grep in judgecore_mixin.py + conflict_resolver.py → hits where R7-6 weight-voting patch actually lives.",
    verdict: "FALSE",
    fix:
      "R8 documents this as SA-R8-3. R7-6's file citation should be corrected to judgecore_mixin.py + conflict_resolver.py.",
  },
  {
    id: "SA-R8-4",
    severity: "medium",
    dna: "#22 (PASS ≠ TRUE) + #26 (Reality > Model)",
    r7FullClaim:
      "R7-Full §4 R7-4: 'Cold-start rep=0.0 drags verdict. Fix: Bayesian prior + min-sample threshold.'",
    reality:
      "Only the min-sample threshold + cold-start skip was implemented. There is NO Bayesian math anywhere in source_reputation.py — no prior, no posterior, no beta distribution. 'Bayesian prior' is a fictional description of a simpler threshold check. The fix description oversells what the code does.",
    evidence:
      "grep -rn 'bayes\\|prior\\|posterior\\|beta' r7full-ref/scp/knowledge/source_reputation.py → 0 hits. grep 'COLD_START_THRESHOLD' → 1 hit (the actual mechanism).",
    verdict: "FALSE",
    fix:
      "R7-4 description should read 'min-sample threshold + cold-start skip', not 'Bayesian prior + min-sample threshold'. OR: actually implement a Bayesian prior (would be a real R8 improvement).",
  },
  {
    id: "SA-R8-5",
    severity: "medium",
    dna: "#14 (Số đếm phải khớp) + #26 (Reality > Model)",
    r7FullClaim:
      "R7-Full §4: '13/13 patched files ast.parse OK' + §4.1 'Totals: 11 files patched + 1 test file = ~737 LOC'",
    reality:
      "The report's own math says 11+1=12, but the headline claims '13/13'. The 13th file is never identified. Reality: 12 patched files (11 .py + test_none_safety.py + __init__.py = 13 entries but __init__.py is a 1-line re-export, not a patch). The count is off-by-one internally.",
    evidence:
      "Section 4 table lists 11 distinct patched files + 1 test file = 12. Section 4.1 'Totals' repeats 11+1. But §1.2 + §7.2 claim '13/13'.",
    verdict: "FALSE",
    fix:
      "R7-Full should say '12/12 patched files ast.parse OK'. R8 uses the verified 12 count.",
  },
  {
    id: "SA-R8-6",
    severity: "medium",
    dna: "#22 (PASS ≠ TRUE) + #19 (Lineage)",
    r7FullClaim:
      "R7-Full §4 R7-9: 'verified already-fixed by R6-9 — Memory + disk prune + atomic rename already in place; added metric. isR5R6Incomplete: true is INACCURATE.'",
    reality:
      "The description 'already in place' is INACCURATE. canary_monitor.py:224+ ADDS NEW disk prune + atomic rename (~35 LOC). The comment in the code says 'Now rewrites' not 'already'. R7-Full both claimed R6-9 was complete AND added new code — contradictory.",
    evidence:
      "Read canary_monitor.py around line 224: new disk-prune + atomic-rename logic with comment 'Now rewrites triggers file atomically'. This is NEW code, not pre-existing.",
    verdict: "FALSE",
    fix:
      "R7-9 description should read 'R6-9 was incomplete; R7-Full added disk prune + atomic rename + metric', not 'already in place'.",
  },
  {
    id: "SA-R8-7",
    severity: "low",
    dna: "#14 (Số đếm phải khớp) + #19 (Lineage)",
    r7FullClaim:
      "R7-Full §5.1: '21 components — +1 vs R7' (audit/, autofix/, bugs/, dashboard/, dna/, layout/, scanners/)",
    reality:
      "The actual count in r7full-ref/dashboard/src/components/ (excluding ui/) is 24 custom components, not 21. R7-Full's own §5.1 detailed listing also shows 24 when you count the bullets. Internal inconsistency: headline says 21, listing shows 24.",
    evidence:
      "find r7full-ref/dashboard/src/components -name '*.tsx' -not -path '*/ui/*' | wc -l → 24.",
    verdict: "FALSE",
    fix:
      "R7-Full should say '24 components'. R8 dashboard uses the verified count.",
  },
  {
    id: "SA-R8-8",
    severity: "low",
    dna: "#14 (Số đếm phải khớp)",
    r7FullClaim: "R7-Full §5.1: '13 data files (mỗi task 1 file) — +1 vs R7'",
    reality:
      "The actual count in r7full-ref/dashboard/src/lib/audit-data/ is 14 .ts files (including index.ts), not 13. Off-by-one — likely index.ts wasn't counted as a 'data file' but it lives in the same directory.",
    evidence:
      "ls r7full-ref/dashboard/src/lib/audit-data/*.ts | wc -l → 14.",
    verdict: "FALSE",
    fix:
      "R7-Full should say '14 data files (13 data + 1 index)'. R8 dashboard uses the verified count.",
  },
  {
    id: "SA-R8-9",
    severity: "low",
    dna: "#19 (Lineage rõ ràng — counting basis must be disclosed)",
    r7FullClaim: "R7-Full §10: 'Totals: 498 files, 6.5 MB'",
    reality:
      "The zip contains 500 entries (559 per unzip -l counting directories). 498 is only correct if excluding 2 README.md files. The counting method (which files excluded) is undisclosed. Not a material error, but a lineage gap — the reader can't reproduce the count.",
    evidence:
      "unzip -l 'scp-dna-audit-round7-full (1).zip' | tail -1 → 559 entries (incl. dirs). find extracted -type f | wc -l → 500.",
    verdict: "FALSE",
    fix:
      "R7-Full should disclose the counting basis: '498 files (500 total minus 2 README.md)'. R8 report discloses its own counting basis explicitly.",
  },
  {
    id: "SA-R8-10",
    severity: "low",
    dna: "#26 (Reality > Model) + #19 (Lineage)",
    r7FullClaim: "R7-Full §10: '6.5 MB' zip size",
    reality:
      "The .zip file is 1.7 MB. 6.5 MB is the EXTRACTED size. 'File zip Full package' in the user's request refers to the .zip — so 1.7 MB is the honest number. 6.5 MB is misleading (sounds bigger/more impressive).",
    evidence:
      "ls -la 'scp-dna-audit-round7-full (1).zip' → 1.7 MB. du -sh extracted/ → 6.5 MB.",
    verdict: "FALSE",
    fix:
      "R7-Full should say '1.7 MB zip (6.5 MB extracted)'. R8 report gives both numbers honestly.",
  },
]

export const ROUND9_STATS = {
  total: ROUND9_FINDINGS.length,
  bySeverity: {
    critical: ROUND9_FINDINGS.filter((f) => f.severity === "critical").length,
    high: ROUND9_FINDINGS.filter((f) => f.severity === "high").length,
    medium: ROUND9_FINDINGS.filter((f) => f.severity === "medium").length,
    low: ROUND9_FINDINGS.filter((f) => f.severity === "low").length,
  },
  // 18 R7-Full claim groups audited: 8 TRUE, 10 FALSE, 0 UNVERIFIABLE.
  claimsAudited: 18,
  claimsTrue: 8,
  claimsFalse: 10,
  claimsUnverifiable: 0,
}

/**
 * Round 9 methodology — 5 reproducible steps (DNA #19 + #22).
 */
export const ROUND9_METHODOLOGY: { step: string; detail: string }[] = [
  {
    step: "1. Read the R7-Full report fully",
    detail:
      "Read all 473 lines of SCP_DNA_AUDIT_ROUND7_CHANGES.md. Extracted every concrete, falsifiable claim into a list (51/51 ast.parse, 13/13 patched, 12/12 IMP, 14 bugs, 8 SA findings, file counts, 0 lint errors, line numbers).",
  },
  {
    step: "2. Run a Reality check per claim",
    detail:
      "For each claim: ast.parse on the named files, grep for the cited patterns, wc -l for file counts, Read at the cited line number, bun run lint for the lint claim. Classified each: TRUE / FALSE / UNVERIFIABLE.",
  },
  {
    step: "3. Verify the SPECIFIC patches were applied",
    detail:
      "For each R7-1..14: grep the actual fix in the actual file (e.g. R7-1 → grep 'is not None and' in chemistryslm.py; R7-2 → grep 'add_done_callback' in _lifespan.py; R7-3 → grep 'threading.Lock' in why_engine.py). Confirmed 11/14 patches real; 3 had inaccurate descriptions (R7-4, R7-6 file, R7-9).",
  },
  {
    step: "4. Verify the SA-1..8 findings' own accuracy",
    detail:
      "For each R7-Full self-audit finding: check if the finding's claim + fix were accurate AND applied. Found SA-1 fix real, SA-8 fix NOT applied (sidebar still says 14), SA-5 accurate. The auditor's own audit had its own bugs.",
  },
  {
    step: "5. Document discrepancies with exact evidence",
    detail:
      "For each FALSE: wrote SA-R8-N with the claim, the reality, the exact command + output (evidence), and a recommended fix. Honest about what couldn't be verified in this environment (browser checks, IMP-11/12 speedup benchmarks — acknowledged by R7-Full itself).",
  },
]
