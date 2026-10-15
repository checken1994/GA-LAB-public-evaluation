/**
 * Canonical dashboard identity. Release version and audit round are
 * different concepts. Legacy v98/v100/... labels are protocol paths.
 */
export const SCP_RELEASE_VERSION = "14.0.0"
export const SCP_RELEASE_LABEL = `SCP ${SCP_RELEASE_VERSION}`
export const SCP_CANONICAL_MODEL_ID = `scp-${SCP_RELEASE_VERSION}`
export const SCP_LEGACY_MODEL_IDS = ["scp-v99"] as const
export const SCP_LEGACY_PROTOCOLS = ["v98", "v100", "v102", "v103", "v104", "v105"] as const
export const DOMAIN_EXPERT_TERM = "Domain Expert"
export const DOMAIN_EXPERT_ENSEMBLE_TERM = "Domain Expert Ensemble"
export const RED_TEAM_PAYLOAD_TERM = "Red-Team Payload Mutation"

/**
 * Single source of truth for the dashboard's round number.
 *
 * [Fix 4-c-008 · Task Local-C] Previously the round number was duplicated as
 * a string literal across 7+ files — and they disagreed:
 *   - layout.tsx metadata.title said "Round 9"
 *   - header.tsx badge said "9" while subtitle said "Round 8"
 *   - hero.tsx h1 said "Round 9"
 *   - footer.tsx, sidebar.tsx, stats-grid.tsx each had their own copy
 *   - (R10 dashboard further drifted to "Round 10" in places)
 * An operator looking at header badge (9) + subtitle (8) + browser tab (9)
 * saw three different numbers simultaneously. DNA #22 (PASS ≠ TRUE) + #14
 * (evidence consistency): a single value must not have N representations.
 *
 * Now every consumer imports CURRENT_ROUND + CURRENT_ROUND_LABEL from here.
 * Bumping the round is a one-line change. Rollback: revert each consumer to
 * its own string literal if the import path breaks.
 *
 * The round is set to 20 — the SCP-DNA worklog is currently at Round 20
 * (worklog.md line 1: "SCP-DNA Audit Worklog — Round 20"). The dashboard
 * renders the current round so an operator can see at a glance whether the
 * UI matches the audit phase they are running.
 */

export const CURRENT_ROUND = 20

/** Long-form label shown in subtitles, footers, and metadata titles. */
export const CURRENT_ROUND_LABEL = `${SCP_RELEASE_LABEL} · Audit Round ${CURRENT_ROUND} · PASS ≠ TRUE (recursive)`

/** Short label for badges (e.g. the header dot). */
export const CURRENT_ROUND_BADGE = String(CURRENT_ROUND)
