# DISPATCH — explorer_survey_3

## Identity
- Role: Explorer (Codebase & Architecture Investigator)
- Type: teamwork_preview_explorer
- Working Directory: D:\scp\.agents\teamwork\explorer_survey_3
- Parent: orchestrator_4 (conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff)

## Mandatory Constraints & Bindings
MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13 (defined in d:\scp\.agents\AGENTS.md section 3 — read it first with view_file). You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.

You MUST read and apply skills:
- d:\scp\.agents\skills\scp-dna\SKILL.md
- d:\scp\.agents\skills\scp-delta-audit\SKILL.md
- d:\scp\.agents\skills\scp-reality-verifier\SKILL.md

Read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md before starting.
Also read D:\scp\GA.md and D:\scp\.agents\AGENTS.md.

## Mission: Survey Track 3 — Offline Knowledge Inbox
Investigate the codebase regarding Requirement 3:
"Xây dựng hộp thư tự học offline data/inbox_knowledge/ qua scp/knowledge/inbox_watcher.py tích hợp claim_extractor, antibody_system, và learning.sqlite."

Investigate:
1. Existing knowledge subsystem in `scp/knowledge/`:
   - Check if `claim_extractor.py`, `antibody_system.py`, or similar modules already exist in `scp/knowledge/` or elsewhere in the repo (search for classes/functions related to claim extraction and antibodies/toxins).
   - Check SQLite database usage in `scp/knowledge/`, specifically `learning.sqlite` or existing learning databases.
   - Check existing background watchers/schedulers (e.g. `reverify_scheduler.py`, `inbox_watcher.py`, etc.).
2. Architecture requirements for `scp/knowledge/inbox_watcher.py`:
   - Watch directory: `data/inbox_knowledge/` (what file formats: markdown, json, txt, jsonl?).
   - Inbox processing loop: file discovery -> quarantine/staging -> parsing -> claim extraction (`claim_extractor`) -> antibody & safety check (`antibody_system`) -> persistence into `learning.sqlite`.
   - Concurrency, locking, WAL mode, idempotency, corrupted/malformed file handling (fail-closed, move to dead-letter or quarantine folder).
   - Tests in `tests/` targeting `knowledge/` or learning databases.

You are READ-ONLY (do NOT modify production code). Produce your comprehensive findings in `D:\scp\.agents\teamwork\explorer_survey_3\handoff.md` and send a message when done.
