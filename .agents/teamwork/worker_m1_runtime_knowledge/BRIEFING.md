# BRIEFING — 2026-09-27T15:41:00Z

## Mission
Implement and verify fixes for SEC-R2-01, SEC-R2-02, R4-F01, R4-F03, R4-F04, and the 4 broken production imports in SCP codebase.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa
- Working directory: D:\scp\.agents\teamwork\worker_m1_runtime_knowledge
- Original parent: 2aaeeadc-d673-43f3-8c6c-2096e8377dec
- Milestone: M1 Remediation (Runtime & Knowledge)

## 🔒 Key Constraints
- Only edit assigned files: scp/runtime/judge.py, scp/api_server_parts/_ask_impl.py, scp/api/chat.py, scp/knowledge/domain_knowledge.py, scp/core/top_systems_learning.py, scp/rag/canonical_retriever.py, scp/release/evidence_authority.py, scp/core/exception_policy.py, scp/runtime/engine.py, scp/meta/reverify_scheduler.py, tests/T05_gateway/test_judge_sync_crosscheck_alive.py, and new/updated unit tests in tests/.
- Strict Fail-Closed & Evidence-First: no fake PASS, no hardcoded bypasses.
- Clamp degraded confidence < 0.50 on crosscheck failure, mark DEGRADED/UNCERTAIN.
- Remove bypass_verdict_pass and fail-closed on missing governance.
- FactSeparator rewrite with stopwords, min 3 content tokens, >= 60% ratio, semantic entity constraints.
- TopSystemsLearning Cyrillic/Greek homoglyphs normalization table + expanded invisible regex.
- CanonicalRetriever missing corpus logging and transparent fallback to DomainKnowledge.
- Fix 4 broken production imports.

## Current Parent
- Conversation ID: 2aaeeadc-d673-43f3-8c6c-2096e8377dec
- Updated: 2026-09-27T15:41:00Z

## Task Summary
- **What to build**: Fix SEC-R2-01, SEC-R2-02, R4-F01, R4-F03, R4-F04, and 4 broken production imports.
- **Success criteria**: stale_code_tripwire passes, pytest passes on targeted test suites, no regressions.
- **Interface contracts**: PROJECT.md, DISPATCH.md
- **Code layout**: D:\scp

## Change Tracker
- **Files modified**: None yet
- **Build status**: Testing baseline
- **Pending issues**: None

## Quality Status
- **Build/test result**: Running baseline
- **Lint status**: 0
- **Tests added/modified**: TBD

## Artifact Index
- D:\scp\.agents\teamwork\worker_m1_runtime_knowledge\BRIEFING.md — Persistent agent briefing
- D:\scp\.agents\teamwork\worker_m1_runtime_knowledge\progress.md — Execution progress heartbeat
- D:\scp\.agents\teamwork\worker_m1_runtime_knowledge\handoff.md — 5-component completion report
