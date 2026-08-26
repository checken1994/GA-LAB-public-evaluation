# Full-folder audit — 2026-08-26

> **Scope:** canonical private GA-LAB root was audited for stale files, duplicate code, legacy names, port drift, forgotten artifacts, and configuration seams. This public document is an evidence summary only; it is not a copy of the private source tree and does not claim production readiness.

## Release identity

| Item | Value |
|---|---|
| Canonical implementation repository | `checken1994/GA-LAB` |
| Audited implementation commit | `f3efaf9d31d06e3097d35315b9184edf2a559851` |
| Previous baseline | `4a3dc3e5acc4e29fee2ed572ed6d82723c6af646` |
| Canonical runtime contract | loopback `127.0.0.1:8002` |
| Egress profile used for local evidence | `deny` |
| Public repository role | Sanitized evaluation evidence pack only |

## What was found and changed

The audit found seven tracked backup/portability artifacts that were not imported by runtime code and were not required by the canonical source tree. Their contents were archived outside Git and recorded with SHA-256 provenance before removal. Git history remains the rollback mechanism; the external archive is not published here because it contains private or machine-specific material.

Several active launchers, dashboard proxies, benchmark clients, test harnesses, and operator documents still defaulted to ports `8000` or `8001`, or contained machine-specific workspace paths. They were aligned to the canonical loopback backend `8002`, while sibling service ports such as the LLM bridge and scheduler were preserved. A duplicate full-stack harness was corrected according to its actual location instead of applying the repository-parent rule indiscriminately.

The portable reality runner previously injected an explicit `.env.test` path even when that file did not exist. This made sidecar tests fail closed for the wrong reason. The runner now uses the explicit file only when present and otherwise leaves the process-environment mode intact. The concurrent-trigger reality test now allocates an ephemeral stub port and shuts it down explicitly, eliminating a fixed-port collision that could produce misleading evidence.

The Tier-3 `pending_fixes/` queue was not auto-approved or deleted. Its README was corrected from an obsolete count of three to the observed count of twenty tracked candidate files across three target groups. Repeated hashes remain visible as unreviewed queue history. A pending suggestion is not proof that the target code is defective.

## Verification evidence

| Gate | Result | Scope and limitation |
|---|---:|---|
| Python compilation | PASS | `scp`, tests, and tools compiled without syntax errors. |
| Unit/integration test suite | **211 passed** | Three existing warnings remained; no test failure. |
| Portable reality suite | **74/74 passed** | Bun `1.4.0` installed in the audit sandbox; all discovered reality tests passed sequentially. |
| Shell/static reality checks | **166 passed, 0 failed** | Tier A and static phases; runtime Tier B is a separate profile. |
| Bounded system smoke | PASS | Health, Hands status/actions/plan/dry-run, context-backed ask, egress-deny profile, and cleanup completed on `127.0.0.1:8002`; both `8000` and `8002` were free afterward. |
| Snapshot manifest | PASS_WITHIN_SCOPE | Manifest tree/blob verification passed; it covers the tracked Git tree at its captured commit. |
| PC canonical sync | PASS | Windows root fast-forwarded to the audited commit; six pre-existing `_agent_*` codegraph artifacts were preserved and no retired workspace folder was recreated. |
| Remote GitHub Release Gate | **Not yet evidenced as green** | The Windows workflow was submitted, but the observed run remained queued and another run ended in `startup_failure` before a job started. This is an infrastructure/runner observation, not a code-pass claim. |

## Duplicate and legacy classification

Exact duplicate content was concentrated in historical reports, audit snapshots, package markers, benchmark fixtures, and intentionally repeated queue entries. Same basenames such as `engine.py`, `route.ts`, `index.ts`, and `__init__.py` belong to different packages or service boundaries; basename equality alone is not code duplication. No nested Git repository was found inside the canonical root.

Historical references to old ports, old workspace names, and former model terminology remain in archived reports, audit-data snapshots, migration records, compatibility fields, and test sentinels. They are not runtime defaults. The active runtime/configuration scan found and corrected the operational `8000`/`8001` defaults. The audit intentionally did not rename compatibility fields such as `slm_trace` or historical `MathSLM` references without a versioned contract decision.

## What this does not prove

This audit proves that the listed observations were checked and that the listed tests passed at the stated commit. It does **not** prove the absence of every unknown defect, human-verified Gold data, official Ragas/ARES success, 1,000-question factual RAG success, distributed isolation, or production safety. The remote Windows gate must be treated as pending until GitHub obtains a runner and executes the job successfully.

## Reviewer instructions

Reviewers should compare this report with the private repository commit named above, inspect the public evidence files in this repository, and label each claim as `VERIFIED`, `REJECTED`, or `NEEDS_MORE_EVIDENCE`. A green local test, a model-generated review, or a queued GitHub run must not be upgraded into a stronger claim than its evidence supports.
