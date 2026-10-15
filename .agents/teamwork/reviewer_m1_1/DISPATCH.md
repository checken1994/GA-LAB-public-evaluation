# DISPATCH — reviewer_m1_1

## Identity
- Role: Reviewer (Independent Verification & Correctness Inspector)
- Type: teamwork_preview_reviewer
- Working Directory: D:\scp\.agents\teamwork\reviewer_m1_1
- Parent: orchestrator_4 (conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff)

## Mandatory Constraints & Bindings
MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13 (defined in d:\scp\.agents\AGENTS.md section 3 — read it first with view_file). You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.

You MUST read and apply skills:
- d:\scp\.agents\skills\scp-dna\SKILL.md
- d:\scp\.agents\skills\scp-delta-audit\SKILL.md
- d:\scp\.agents\skills\scp-reality-verifier\SKILL.md

Read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md before starting.
Also read D:\scp\GA.md, D:\scp\.agents\AGENTS.md, D:\scp\.agents\teamwork\orchestrator_4\PROJECT.md, and worker report at D:\scp\.agents\teamwork\worker_m1\handoff.md.

## Mission: Review Milestone 1 (Domain Data Fork & Question Router)
Examine correctness, completeness, robustness, and interface conformance of Worker M1's implementation:
- `scp/runtime/domain_data_fork.py`
- `scp/runtime/question_router.py`
- `scp/core/partition/shard.py`
- `scp/data_sources/biology.py`
- `scp/data_sources/geology.py`
- `scp/data_sources/usgs.py`
- `scp/data_sources/__init__.py`
- `tests/T02_contract/test_domain_data_fork.py`

Run test commands using:
`& "D:\opt\scp-venv-w16\Scripts\python.exe" -m pytest tests/T02_contract/test_domain_data_fork.py tests/test_config_loader.py tests/T07_learning/test_question_router_cascade.py tests/T07_learning/test_question_router_goldset.py tests/T07_learning/test_ask_lookup_fork.py -v`

Check:
1. USGS fixes: metadata extraction of top_events[0], offline historical anchors, scoped egress host.
2. Biology data source: codons, amino acids, organelles, constants, taxonomy, ConfigLoader usage.
3. Geology data source: Mohs scale 1-10, Earth layers, rock types.
4. Question Router: tags for biology_fact, geology_fact, earthquake_fact, and no regressions in existing routes.
5. Zero regressions in T00 Meta-Audit: `& "D:\opt\scp-venv-w16\Scripts\python.exe" tools/t00_meta_audit.py`.

Deliver your verdict (`APPROVE` or `REQUEST_CHANGES`) in `D:\scp\.agents\teamwork\reviewer_m1_1\handoff.md`.


## 2026-10-08T06:18:57Z
MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13 (defined in d:\scp\.agents\AGENTS.md section 3 — read it first with view_file). You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.

You MUST read and apply skills:
- d:\scp\.agents\skills\scp-dna\SKILL.md
- d:\scp\.agents\skills\scp-delta-audit\SKILL.md
- d:\scp\.agents\skills\scp-reality-verifier\SKILL.md

Read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md before starting.
Also read D:\scp\GA.md, D:\scp\.agents\AGENTS.md, D:\scp\.agents\teamwork\orchestrator_4\PROJECT.md, your dispatch at D:\scp\.agents\teamwork\reviewer_m1_1\DISPATCH.md, and worker report at D:\scp\.agents\teamwork\worker_m1\handoff.md.

Identity:
- Role: Reviewer (Independent Verification & Correctness Inspector)
- Working Directory: D:\scp\.agents\teamwork\reviewer_m1_1
- Parent: orchestrator_4 (conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff)

Mission: Review Milestone 1 (Domain Data Fork & Question Router). Run test commands using D:\opt\scp-venv-w16\Scripts\python.exe. Verify correctness, interface conformance, and zero regressions. Deliver verdict (APPROVE or REQUEST_CHANGES) in handoff.md and send_message back to orchestrator.
