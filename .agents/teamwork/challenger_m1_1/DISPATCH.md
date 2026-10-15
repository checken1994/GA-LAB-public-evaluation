# DISPATCH — challenger_m1_1

## Identity
- Role: Challenger (Adversarial Correctness Verifier)
- Type: teamwork_preview_challenger
- Working Directory: D:\scp\.agents\teamwork\challenger_m1_1
- Parent: orchestrator_4 (conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff)

## Mandatory Constraints & Bindings
MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13 (defined in d:\scp\.agents\AGENTS.md section 3 — read it first with view_file). You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.

You MUST read and apply skills:
- d:\scp\.agents\skills\scp-dna\SKILL.md
- d:\scp\.agents\skills\scp-delta-audit\SKILL.md
- d:\scp\.agents\skills\scp-reality-verifier\SKILL.md

Read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md before starting.
Also read D:\scp\GA.md, D:\scp\.agents\AGENTS.md, D:\scp\.agents\teamwork\orchestrator_4\PROJECT.md, and worker report at D:\scp\.agents\teamwork\worker_m1\handoff.md.

## Mission: Empirically Challenge Milestone 1
Adversarially stress-test `scp/runtime/domain_data_fork.py` and `scp/runtime/question_router.py`:
1. Craft adversarial boundary inputs:
   - Malformed earthquake questions (e.g. "động đất xyz 9999", empty strings, non-numeric magnitudes)
   - Ambiguous biology questions (invalid codons e.g. "ZZZ", overlapping amino acid names)
   - Geology questions on borderline Mohs numbers or non-existent minerals
   - Cross-domain queries (e.g. "động đất và thời tiết Hà Nội")
2. Verify that `domain_data_fork.py` never crashes (no unhandled exceptions) and returns clean `None` or verified dictionaries.
3. Verify that `USGSDataSource` respects `extra_allowed_hosts` and fails closed without crashing if network is unavailable or denied.
4. Run python probes using: `& "D:\opt\scp-venv-w16\Scripts\python.exe"`.

Deliver your verdict (`CONFIRMED` or `DISPROVEN` / `CHALLENGE_FAILED` / `APPROVE`) in `D:\scp\.agents\teamwork\challenger_m1_1\handoff.md`.

## 2026-10-08T06:18:57Z
Sender: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff
Content:
MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13 (defined in d:\scp\.agents\AGENTS.md section 3 — read it first with view_file). You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.

You MUST read and apply skills:
- d:\scp\.agents\skills\scp-dna\SKILL.md
- d:\scp\.agents\skills\scp-delta-audit\SKILL.md
- d:\scp\.agents\skills\scp-reality-verifier\SKILL.md

Read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md before starting.
Also read D:\scp\GA.md, D:\scp\.agents\AGENTS.md, D:\scp\.agents\teamwork\orchestrator_4\PROJECT.md, your dispatch at D:\scp\.agents\teamwork\challenger_m1_1\DISPATCH.md, and worker report at D:\scp\.agents\teamwork\worker_m1\handoff.md.

Identity:
- Role: Challenger (Adversarial Correctness Verifier)
- Working Directory: D:\scp\.agents\teamwork\challenger_m1_1
- Parent: orchestrator_4 (conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff)

Mission: Empirically challenge Milestone 1. Adversarially probe boundary conditions, malformed inputs, cross-domain questions, and fail-closed handling in domain_data_fork.py and question_router.py using D:\opt\scp-venv-w16\Scripts\python.exe. Deliver verdict in handoff.md and report back to orchestrator.
