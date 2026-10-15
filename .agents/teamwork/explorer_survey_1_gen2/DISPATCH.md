# DISPATCH — explorer_survey_1_gen2

## Identity
- Role: Explorer (Codebase & Architecture Investigator — Gen 2 Replacement)
- Type: teamwork_preview_explorer
- Working Directory: D:\scp\.agents\teamwork\explorer_survey_1_gen2
- Parent: orchestrator_4 (conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff)

## Mandatory Constraints & Bindings
MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13 (defined in d:\scp\.agents\AGENTS.md section 3 — read it first with view_file). You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.

You MUST read and apply skills:
- d:\scp\.agents\skills\scp-dna\SKILL.md
- d:\scp\.agents\skills\scp-delta-audit\SKILL.md
- d:\scp\.agents\skills\scp-reality-verifier\SKILL.md

Read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md before starting.
Also read D:\scp\GA.md and D:\scp\.agents\AGENTS.md.
Also check partial progress from predecessor at: D:\scp\.agents\teamwork\explorer_survey_1\progress.md.

## Mission: Survey Track 1 — Domain Data Fork & Question Router
Investigate Requirement 1:
"Hoàn tất kết nối dữ liệu chuyên ngành vào scp/runtime/domain_data_fork.py và scp/runtime/question_router.py (USGS Earthquake, Biology, Geology, ConfigLoader cho các API cần key)."

Investigate:
1. `scp/runtime/domain_data_fork.py`: Current state, classes, how data sources are registered/invoked, caching, error handling, fail-closed behavior.
2. `scp/runtime/question_router.py`: Current routing rules, keywords, regex, priority ordering, how domain questions are detected and routed.
3. `scp/data_sources/`: Check if USGS Earthquake, Biology, Geology data sources already exist or how other data sources (WeatherDataSource, ConversionDataSource) are implemented.
4. API Key configuration / ConfigLoader: How environment variables and API keys are currently loaded across `scp/`, how keys for external domain APIs should be loaded safely without hardcoding or leaking secrets.
5. Existing test coverage for domain data fork and router in `tests/`.

You are READ-ONLY (do NOT modify production code). Produce your comprehensive findings in `D:\scp\.agents\teamwork\explorer_survey_1_gen2\handoff.md` and report back via send_message to d48c23a1-aa94-4967-ac9a-ed40fa3f5fff.
