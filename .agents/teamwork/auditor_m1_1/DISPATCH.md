# DISPATCH — auditor_m1_1

## Identity
- Role: Forensic Auditor (Integrity Forensics & Anti-Cheating Inspector)
- Type: teamwork_preview_auditor
- Working Directory: D:\scp\.agents\teamwork\auditor_m1_1
- Parent: orchestrator_4 (conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff)

## Mandatory Constraints & Bindings
MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13 (defined in d:\scp\.agents\AGENTS.md section 3 — read it first with view_file). You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.

You MUST read and apply skills:
- d:\scp\.agents\skills\scp-dna\SKILL.md
- d:\scp\.agents\skills\scp-delta-audit\SKILL.md
- d:\scp\.agents\skills\scp-reality-verifier\SKILL.md

Read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md before starting.
Also read D:\scp\GA.md, D:\scp\.agents\AGENTS.md, D:\scp\.agents\teamwork\orchestrator_4\PROJECT.md, and worker report at D:\scp\.agents\teamwork\worker_m1\handoff.md.

## Mission: Forensic Audit Milestone 1
Perform forensic integrity verification on all code modified in Milestone 1:
- `scp/runtime/domain_data_fork.py`
- `scp/runtime/question_router.py`
- `scp/core/partition/shard.py`
- `scp/data_sources/biology.py`
- `scp/data_sources/geology.py`
- `scp/data_sources/usgs.py`
- `scp/data_sources/__init__.py`
- `tests/T02_contract/test_domain_data_fork.py`

Run forensic checks:
1. Anti-Cheating Check: Are there hardcoded test answers, dummy/facade returns designed solely to pass specific test queries?
2. FA-01 / FA-02 Check: Were any existing test assertions loosened, commented out, or bypassed?
3. FA-04 Check: Are returned results from real reference tables/data sources, not manufactured `VERIFIED` stubs?
4. Static & Runtime Checks:
   - Run git diff to inspect exact code delta: `git diff scp/ tests/`
   - Run meta audit: `& "D:\opt\scp-venv-w16\Scripts\python.exe" tools/t00_meta_audit.py`
   - Run full contract test: `& "D:\opt\scp-venv-w16\Scripts\python.exe" -m pytest tests/T02_contract/test_domain_data_fork.py -v`

Deliver your verdict (`CLEAN` or `INTEGRITY_VIOLATION`) in `D:\scp\.agents\teamwork\auditor_m1_1\handoff.md`.
⚠️ NOTE: An INTEGRITY VIOLATION verdict constitutes a binary veto and immediately fails the iteration.


## 2026-10-08T06:18:57Z
MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13 (defined in d:\scp\.agents\AGENTS.md section 3 — read it first with view_file). You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.

You MUST read and apply skills:
- d:\scp\.agents\skills\scp-dna\SKILL.md
- d:\scp\.agents\skills\scp-delta-audit\SKILL.md
- d:\scp\.agents\skills\scp-reality-verifier\SKILL.md

Read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md before starting.
Also read D:\scp\GA.md, D:\scp\.agents\AGENTS.md, D:\scp\.agents\teamwork\orchestrator_4\PROJECT.md, your dispatch at D:\scp\.agents\teamwork\auditor_m1_1\DISPATCH.md, and worker report at D:\scp\.agents\teamwork\worker_m1\handoff.md.

Identity:
- Role: Forensic Auditor (Integrity Forensics & Anti-Cheating Inspector)
- Working Directory: D:\scp\.agents\teamwork\auditor_m1_1
- Parent: orchestrator_4 (conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff)

Mission: Forensic Audit Milestone 1. Run git diff and integrity forensics against FA-01 to FA-13. Check for hardcoded test answers, fake passes, or loosened assertions. Run tools/t00_meta_audit.py using D:\opt\scp-venv-w16\Scripts\python.exe. Deliver verdict (CLEAN or INTEGRITY_VIOLATION) in handoff.md and send_message back to orchestrator.
