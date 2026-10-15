# DISPATCH — challenger_m1_2

## Identity
- Role: Challenger (Adversarial Correctness Verifier)
- Type: teamwork_preview_challenger
- Working Directory: D:\scp\.agents\teamwork\challenger_m1_2
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
Adversarially probe routing collisions and contract boundaries:
1. Probe whether `question_router.py` misclassifies existing conversion, weather, or security questions after the new rules were added.
   - Run tests: `test_w12_conversion_lookup.py`, `test_w13_weather_lookup.py`, `test_question_router_goldset.py`.
2. Probe whether `ConfigLoader` integration in `biology.py` properly blocks invalid placeholder keys (e.g. `NCBI_API_KEY=demo` or `your_api_key_here`).
3. Verify that under `SCP_EGRESS_MODE=deny`, all local lookups succeed 100% offline without attempting external egress.
4. Run python probes using: `& "D:\opt\scp-venv-w16\Scripts\python.exe"`.

Deliver your verdict (`CONFIRMED` or `DISPROVEN` / `CHALLENGE_FAILED` / `APPROVE`) in `D:\scp\.agents\teamwork\challenger_m1_2\handoff.md`.


## 2026-10-08T06:18:57Z
Received dispatch message from orchestrator_4:
MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13 (defined in d:\scp\.agents\AGENTS.md section 3 — read it first with view_file). You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.

You MUST read and apply skills:
- d:\scp\.agents\skills\scp-dna\SKILL.md
- d:\scp\.agents\skills\scp-delta-audit\SKILL.md
- d:\scp\.agents\skills\scp-reality-verifier\SKILL.md

Read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md before starting.
Also read D:\scp\GA.md, D:\scp\.agents\AGENTS.md, D:\scp\.agents\teamwork\orchestrator_4\PROJECT.md, your dispatch at D:\scp\.agents\teamwork\challenger_m1_2\DISPATCH.md, and worker report at D:\scp\.agents\teamwork\worker_m1\handoff.md.

Identity:
- Role: Challenger (Adversarial Correctness Verifier)
- Working Directory: D:\scp\.agents\teamwork\challenger_m1_2
- Parent: orchestrator_4 (conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff)

Mission: Empirically challenge Milestone 1. Probe routing collisions against existing conversion/weather routes, test invalid placeholder key rejection with ConfigLoader, and verify 100% offline success under SCP_EGRESS_MODE=deny using D:\opt\scp-venv-w16\Scripts\python.exe. Deliver verdict in handoff.md and report back to orchestrator.
