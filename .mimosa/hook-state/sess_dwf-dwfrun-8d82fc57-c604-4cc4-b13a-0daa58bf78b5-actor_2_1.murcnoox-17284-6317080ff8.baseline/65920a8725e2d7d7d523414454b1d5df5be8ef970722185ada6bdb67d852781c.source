/**
 * SCP Autofix Engine spec (separate file per task)
 *
 * Flow: detect → classify → tier → fix → verify
 * 4 tiers: T1 auto-fix / T2 auto-fix+log / T3 permission / T4 attack-mode
 *
 * Engine file: scp/autofix/engine.py (1341 LOC)
 * Runner file: scp/autofix/runner.py (525 LOC)
 * Classifier: scp/autofix/classifier.py (240 LOC)
 * LLM fixer: scp/autofix/llm_fix.py (815 LOC)
 */

export interface AutofixTier {
  id: number
  name: string
  description: string
  autonomy: string
  rateLimit: string
  examples: string[]
  guardColor: string
}

export const AUTOFIX_TIERS: AutofixTier[] = [
  {
    id: 1,
    name: "TIER_1_AUTO_FIX",
    description: "Implementation bugs — SCP fixes silently, no report.",
    autonomy: "Full auto (no human, no log)",
    rateLimit: "200/cycle, 1h cooldown same bug",
    examples: ["Typo in string", "Unused import", "Trailing whitespace", "Missing type hint"],
    guardColor: "emerald",
  },
  {
    id: 2,
    name: "TIER_2_AUTO_FIX_LOG",
    description: "Behavior bugs with clear correct answer — SCP fixes + logs to audit trail.",
    autonomy: "Auto + log (human can review later)",
    rateLimit: "200/cycle, 1h cooldown, audit log",
    examples: ["None>0 guard (R7-1)", "Missing try/except", "Wrong method name (R4 #8)"],
    guardColor: "amber",
  },
  {
    id: 3,
    name: "TIER_3_PERMISSION",
    description: "Logic bugs — changes WHAT SCP decides. SCP asks human permission, WAITS.",
    autonomy: "NEVER auto (even when SCP_AUTO_APPROVE_TIER3=1, with 6 safety guards)",
    rateLimit: "5/hour if auto-approve ON, 1h timeout, backup .tier3bak",
    examples: [
      "Verdict threshold change",
      "Evidence-First logic change",
      "Constitution/KILL logic",
      "Security policy change",
      "API boundary change",
      "Learning verification change",
    ],
    guardColor: "rose",
  },
  {
    id: 4,
    name: "TIER_4_ATTACK_MODE",
    description: "Restraints (tightening, not loosening) during active attack — auto-fixed, reversible + logged.",
    autonomy: "Auto during attack (post-hoc review)",
    rateLimit: "20/hour, all reversible",
    examples: ["Block IP during DDoS", "Increase canary sensitivity", "Throttle rate limit"],
    guardColor: "fuchsia",
  },
]

export interface AutofixPhase {
  id: string
  name: string
  description: string
  file: string
  isNew: boolean
  duration: string
}

export const AUTOFIX_PIPELINE: AutofixPhase[] = [
  {
    id: "detect",
    name: "1. Detect",
    description: "Run 18 SCP scanners + 7 external tools. Collect BugReports.",
    file: "scp/autofix/runner_phases/ast_scan.py",
    isNew: false,
    duration: "~45s (full scan)",
  },
  {
    id: "classify",
    name: "2. Classify",
    description: "BugClassifier assigns tier (1-4) based on LOGIC_PATTERNS + ATTACK_PATH_PATTERNS + RELAXATION_PATTERNS.",
    file: "scp/autofix/classifier.py",
    isNew: false,
    duration: "<1ms per bug",
  },
  {
    id: "permission",
    name: "3. Permission Gate",
    description: "Tier-3 → ask human (or auto-approve if SCP_AUTO_APPROVE_TIER3=1 with 6 guards). Tier-4 → attack-mode check.",
    file: "scp/autofix/permission.py",
    isNew: false,
    duration: "Tier-3: human response time",
  },
  {
    id: "fix",
    name: "4. Apply Fix",
    description: "Engine calls evolution_agent._apply_fix() (search-replace markers + ast.parse verify). LLM fixer for complex cases.",
    file: "scp/autofix/engine.py + llm_fix.py",
    isNew: false,
    duration: "Pattern: <100ms. LLM: 3-15s.",
  },
  {
    id: "post-verify",
    name: "5. Post-Fix Verify (NEW R7)",
    description: "Run vulture cross-file → assert dead method GONE. Run hypothesis property test → assert no TypeError. If fail → rollback + escalate.",
    file: "scp/autofix/runner_phases/post_fix_verify.py",
    isNew: true,
    duration: "~5s (vulture + hypothesis)",
  },
  {
    id: "audit",
    name: "6. Audit Log",
    description: "Write to data/autofix_audit.jsonl: {timestamp, file, line, fix, before_hash, after_hash, reality_test_result, rollback_token}.",
    file: "scp/autofix/engine.py (audit_log)",
    isNew: false,
    duration: "<1ms",
  },
  {
    id: "reality",
    name: "7. Reality Test (NEW R7)",
    description: "Import modified module + exercise key function. If ImportError/TypeError → rollback + alert.",
    file: "scp/autofix/runner_phases/reality_test.py",
    isNew: true,
    duration: "~2s per module",
  },
]

export interface AutofixConfig {
  key: string
  value: string
  description: string
  default: string
}

export const AUTOFIX_CONFIG: AutofixConfig[] = [
  {
    key: "MAX_FIXES_PER_CYCLE",
    value: "200",
    description: "Max auto-fixes per audit cycle. Was 10 (STARTUP-GATE blocked).",
    default: "200",
  },
  {
    key: "MAX_TIER4_PER_HOUR",
    value: "20",
    description: "Max attack-mode fixes per hour.",
    default: "20",
  },
  {
    key: "COOLDOWN_SAME_BUG_SECONDS",
    value: "3600",
    description: "Don't re-fix same bug within 1 hour.",
    default: "3600",
  },
  {
    key: "MAX_TIER3_AUTO_PER_HOUR",
    value: "5",
    description: "Hard cap: 5 logic-bug auto-fixes/hour (when SCP_AUTO_APPROVE_TIER3=1).",
    default: "5",
  },
  {
    key: "TIER3_AUTO_TIMEOUT_SECONDS",
    value: "3600",
    description: "Auto-approve env var expires after 1h.",
    default: "3600",
  },
  {
    key: "SCP_AUTO_APPROVE_TIER3",
    value: "0",
    description: "Master switch for Tier-3 auto-approve. Default OFF (DNA #4: human decides).",
    default: "0",
  },
  {
    key: "SCP_R7_POST_FIX_VERIFY (NEW)",
    value: "1",
    description: "R7 NEW: Run vulture cross-file + hypothesis after Tier-2 fix. Default ON.",
    default: "1",
  },
  {
    key: "SCP_R7_REALITY_TEST (NEW)",
    value: "1",
    description: "R7 NEW: Import + exercise modified module after fix. Default ON.",
    default: "1",
  },
  {
    key: "SCP_R7_CROSS_FILE_VULTURE (NEW)",
    value: "1",
    description: "R7 NEW: Run vulture on whole scp/ directory (not per-file). Default ON.",
    default: "1",
  },
]
