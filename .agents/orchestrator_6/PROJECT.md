# Project: SCP (Secure Control Plane) Post-Merge PR #47 Audit Remediation

## Architecture
- **Web & API Gateway Layer**: `dashboard/src/`, `scp/api_server.py`, `scp/api_server_parts/`, `scp/api/`
- **Security & Policies**: `scp/security/`, `scp/policy/egress.py`, `scp/capabilities/tools.py`
- **Core Orchestration & Traceability**: `scp/core/`, `scp/core/autonomous_ledger.py`, `scp/hands/`
- **Runtime, Kernel & Judges**: `scp/runtime/judge.py`, `scp/task_kernel_parts/taskkernel.py`
- **Knowledge & Learning**: `scp/core/top_systems_learning.py`, `scp/knowledge/domain_knowledge.py`
- **Testing & Verification Tools**: `tests/`, `tools/t00_meta_audit.py`, `tools/adversarial_goal3_probe.py`
- **Evidence & Governance History**: `docs/evidence-summary/`, `RELOCATION_MANIFEST.md`

## Feature Inventory (25 Remediation Features Mapped to Milestones)
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | F01 | Dashboard middleware fail-open IP fix (`dashboard/src/middleware.ts:6-7`) | M1 | Survey R1 |
| 2 | F02 | Dashboard ask route JWT auto-minting removal (`dashboard/src/app/api/scp/ask/route.ts`) | M1 | Survey R1 |
| 3 | F03 | Chatbot lane KILL override to ALLOW removal (`scp/api_server_parts/_ask_impl.py`, `scp/api/chat.py`) | M1 | Survey R1 |
| 4 | F04 | JWT guard static key separation from JWT decoding (`scp/security/jwt_guard.py:37-43`) | M1 | Survey R1 |
| 5 | F05 | Evaluation API fail-closed defaults & confidence clamping (`scp/api/routes/evaluation_routes.py`) | M1 | Survey R1 |
| 6 | F06 | Critical security chain-break integration test suite (`tests/integration/test_critical_chain_severed.py`) | M1 | Survey R1 |
| 7 | F07 | Wire `SafeCommandRunnerTool` into `ActionRegistry`, `AutonomousCapabilityGovernor`, `HandsExecutor` | M2 | Survey R2 |
| 8 | F08 | Wire `EgressPolicy` into `url_safety.py` delegation across all 20+ runtime network callers | M2 | Survey R2 |
| 9 | F09 | Add HMAC-SHA256 to `AutonomousAuditLedger` and wire two-phase commit into `HandsExecutor.execute()` | M2 | Survey R2 |
| 10 | F10 | Fix Judge crosscheck crash fallback to degraded flag and fix text_contains tautology (`judge.py`) | M3 | Survey R3 |
| 11 | F11 | Add `cur.rowcount` OCC checks to 4 `expire_leases` branches in `taskkernel.py:805-850` | M3 | Survey R3 |
| 12 | F12 | Wire `inspect_untrusted()` in `top_systems_learning.py` for GitHub & Wikipedia external ingestion | M3 | Survey R3 |
| 13 | F13 | Eliminate SSRF in dashboard raw-fetch routes (`status`, `scanners`, `loop`, `loop/trigger`, `autofix`) | M3 | Survey R3 |
| 14 | F14 | Remove dev-default OPEN in `egress.py` & `url_safety.py` and eliminate TOCTOU DNS window | M3 | Survey R3 |
| 15 | F15 | Update `docs/SCP_ARCHITECTURE.md` to remove quorum references and clean up test import | M3 | Survey R3 |
| 16 | F16 | Add JWT, GitHub PAT, AWS, Google API key regexes to `ChatMemoryStore._SECRET_PATTERNS` | M3 | Survey R3 |
| 17 | F17 | Restore 16 essential evidence files from commit `87d78da~1` to `docs/evidence-summary/` | M4 | Survey R4 |
| 18 | F18 | Create `RELOCATION_MANIFEST.md` documenting relocation and git provenance for all 471 files | M4 | Survey R4 |
| 19 | F19 | Batch fix all 115 dangling references pointing to `docs/evidence-summary/` | M4 | Survey R4 |
| 20 | F20 | Verifiable backing link in `README.md` to `docs/evidence-summary/WITNESS-REPORT-W2-2026-09-11.md` | M4 | Survey R4 |
| 21 | F21 | Fix `tools/t00_meta_audit.py:356` path check and `tools/create_snapshot_manifest.py` paths | M4 | Survey R4 |
| 22 | F22 | Delete dead debris files `prev_ask_impl.py` and `sleeps.txt` | M4 | Survey R5 |
| 23 | F23 | Replace hardcoded fallback admin token in `tools/e2e_live_cluster_verifier.py:100` | M4 | Survey R5 |
| 24 | F24 | Fix FactSeparator 2-token overlap tautology in `scp/knowledge/domain_knowledge.py:526-532` | M4 | Survey R5 |
| 25 | F25 | Observability compose password env var & compose.test 127.0.0.1 port binding | M4 | Survey R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Sever Critical Security Chain (R1) | F01 - F06 | None | PLANNED |
| M2 | Wire Security Modules into Runtime (R2) | F07 - F09 | M1 | PLANNED |
| M3 | Fix Remaining Audit Findings (R3) | F10 - F16 | M1 | PLANNED |
| M4 | Evidence Restoration, Zero Dangling Refs & Hygiene (R4, R5) | F17 - F25 | None | PLANNED |
| M5 | Final Verification & Meta-Audit Gate | Full test suite, collect-only, t00_meta_audit, adversarial probe, grep audit | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### 1. Dashboard Middleware & API Gateway
- `middleware.ts`: Requests lacking verified client headers MUST fail-closed with 403. No hardcoded 127.0.0.1 fallback for missing headers.
- `/api/scp/ask`: NEVER auto-mint an admin token. Forward caller credentials or require authenticated session.
- `jwt_guard.py`: `verify_jwt_token(token)` MUST reject non-JWT strings with 401/InvalidTokenError. Static API keys must use separate authentication helper.

### 2. Governance KILL Enforcement
- `_ask_impl.py` & `chat.py`: When governance outputs `KILL`, the execution MUST terminate immediately with security violation / 403. Lane classification (including `LANE_CHATBOT`) MUST NOT override KILL to ALLOW or force verdict to PASS.

### 3. Evaluation API Fail-Closed
- `evaluation_routes.py`: Fallback verdict must be `UNCERTAIN` or `FAIL`. Verdicts must be strictly validated against `{"PASS", "FAIL", "UNCERTAIN"}`. Confidence float must be clamped to `[0.0, 1.0]`.

### 4. Runtime Capability & Egress Delegation
- `url_safety.py:enforce_egress_policy(url)` delegates directly to `EgressPolicy.enforce(url)`.
- `HandsExecutor.execute()` commits intent to `AutonomousAuditLedger` with HMAC before execution, runs command through `SafeCommandRunnerTool`, and commits result to ledger.

## Code Layout
- `scp/`: Core implementation packages
- `dashboard/`: Next.js web application
- `tests/`: Primary pytest suite
- `tools/`: Diagnostic and audit tools
- `docs/evidence-summary/`: Restored closure evidence records
