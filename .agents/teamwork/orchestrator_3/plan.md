# Live Operational Audit Plan — 2026-10-04

## Scope & Constraints
- Working Directory: `D:\scp`
- Baseline: Commit `1aef24a8` on branch `main`
- Mode: Pure Read-Only (`git status` 100% clean, no source file changes)
- Focus: Level C/D Runtime Operational Verification (Skip static unit tests)

## Milestones & Work Breakdown

### Milestone 1: Pre-boot Environment & Port Inspection
- Check `git rev-parse HEAD` == `1aef24a8` and `git status --short` is clean.
- Check ports 8000, 8081, 3000 via PowerShell. Terminate any orphaned processes if found.
- Verify environment variables, Python/Bun/Node runtimes, and startup commands.

### Milestone 2: Live Cluster Boot & Readiness Verification (R1)
- Boot API Server (FastAPI :8000).
- Boot Bun LLM Bridge (:8081).
- Boot Web Dashboard Next.js (:3000).
- Measure readiness latency per service, inspect boot logs, verify HTTP 200 on health/readiness endpoints.

### Milestone 3: Live Conversational & Retrieval Probing (R2)
- Probe conversational flow ("bạn là ai", greetings): check latency, verify verdict PASS, ensure response not withheld.
- Probe factual retrieval: trigger FactSeparator, check transparency badge, extract `trace_id`, inspect routing.

### Milestone 4: Live Security Boundary Audit (R3)
- Authorized probe on `/v3/trace/{trace_id}` with valid admin token: verify decision tree, HMAC ledger linkage, secret redaction.
- Unauthorized probe on `/v3/trace/{trace_id}` and internal routes (no token / bad token): verify fail-closed HTTP 401/403.
- Probe Bun LLM Bridge (:8081) directly: verify token protection.
- Probe Next.js Dashboard: verify IP anti-spoofing (`X-Forwarded-For`).

### Milestone 5: Task Lifecycle & Ledger Inspection (R4)
- TaskKernel lifecycle on real SQLite DB: create task -> claim lease -> renew heartbeat -> complete with evidence -> test idempotency.
- Audit ledger hash-chain verification: check `.jsonl` files and HMAC hash continuity.
- Runtime log inspection: scan `data/service-logs/` and runtime outputs for swallowed exceptions or leaks.

### Milestone 6: Clean Teardown & Port Release (R5)
- Terminate process trees for all 3 services cleanly.
- Verify 100% ports 8000, 8081, 3000 released without zombies.

### Milestone 7: Independent Victory Integrity Audit & Verification
- Dispatch Forensic Auditor / Reality Verifier to audit all runtime claims and evidence.

### Milestone 8: Final Synthesis & Reporting
- Compile comprehensive Live Operational Audit Report (`D:\scp\LIVE_OPERATIONAL_AUDIT_REPORT_20261004.md`).
- Generate final handoff to Sentinel.
