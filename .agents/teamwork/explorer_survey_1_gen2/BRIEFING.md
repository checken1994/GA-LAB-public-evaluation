# BRIEFING — 2026-10-08T05:56:00Z

## Mission
Survey Track 1: Investigate connecting domain data sources (USGS Earthquake, Biology, Geology, ConfigLoader for keyed APIs) into scp/runtime/domain_data_fork.py and scp/runtime/question_router.py.

## 🔒 My Identity
- Archetype: explorer
- Roles: Codebase & Architecture Investigator — Gen 2 Replacement
- Working directory: D:\scp\.agents\teamwork\explorer_survey_1_gen2
- Original parent: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff
- Milestone: Survey Phase (Requirement 1: Domain Data Fork & Question Router)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / do NOT modify production code
- Bound by Fail-Closed & Evidence-First principles (FA-01 through FA-13)
- Never simulate PASS or forge evidence
- Write findings to handoff.md and send_message to orchestrator

## Current Parent
- Conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff
- Updated: 2026-10-08T05:56:00Z

## Investigation State
- **Explored paths**:
  - `scp/runtime/domain_data_fork.py`
  - `scp/runtime/question_router.py`
  - `scp/data_sources/usgs.py`
  - `scp/data_sources/biology.py`
  - `scp/data_sources/geology.py`
  - `scp/data_sources/config_loader.py`
  - `scp/data_sources/__init__.py`
  - `scp/security/url_safety.py`
  - `scp/core/partition/shard.py`
  - `scp/data_sources/domain_classifier.py`
  - `tests/T02_contract/test_domain_data_fork.py`
  - `tests/test_config_loader.py`
  - `tests/T07_learning/test_question_router_cascade.py`
  - `tests/T07_learning/test_question_router_goldset.py`
  - `tests/T02_contract/test_w13_weather_fork_contract.py`
  - `tests/T05_gateway/test_w13_weather_egress.py`
- **Key findings**:
  1. `domain_data_fork.py` already resolves Astronomy, Chemistry, Physics, Geography, Math, and has a partial draft for USGS. Missing Biology and Geology handlers entirely.
  2. `USGSDataSource` is in `scp/data_sources/usgs.py`, but `domain_data_fork.py:_resolve_usgs` has a metadata parsing bug on recent quakes (`_query_recent` yields `None` magnitude and place) and lacks scoped egress allowance for `earthquake.usgs.gov`.
  3. `BiologyDataSource` in `scp/data_sources/biology.py` has local genetic codes (codons -> amino acids), amino acid names, organelles, biological constants, and remote NCBI Taxonomy via E-utilities. Currently not wired into `domain_data_fork.py` and omitted from `register_all_sources()` instantiation in `data_sources/__init__.py`.
  4. `GeologyDataSource` in `scp/data_sources/geology.py` has minerals (diamond, quartz, gold, iron, feldspar) and a crude duplicate USGS fetcher. Can be enriched with full Mohs scale (1-10), rock types (magma, trầm tích, biến chất), and Earth layers.
  5. `ConfigLoader` (`scp/data_sources/config_loader.py`) is fully implemented with fail-closed checks, placeholder rejection, and secret masking, with 100% passing tests in `tests/test_config_loader.py`, but is NOT YET WIRED into `scp/data_sources/` (sources still use raw `os.environ.get()`).
  6. `question_router.py`: `_LOOKUP_RULES` lacks explicit regex rules for `biology_fact`, `geology_fact`, and `earthquake_fact`. `_KNOWLEDGE_DOMAINS` lacks `"geology"`. `shard.py` lacks `"geology"` in `DOMAIN_KEYWORDS`.
  7. Verification: Python environment is at `D:\opt\scp-venv-w16\Scripts\python.exe` (Python 3.12.14, pytest 9.1.1). All existing tests (27 + 46) pass and `t00_meta_audit.py` passes with 0 regressions.
- **Unexplored areas**: None for Track 1 scope.

## Key Decisions Made
- Formulate concrete architecture, integration steps, and proposed code diffs in `handoff.md` without modifying production code.

## Artifact Index
- D:\scp\.agents\teamwork\explorer_survey_1_gen2\BRIEFING.md — Situational awareness
- D:\scp\.agents\teamwork\explorer_survey_1_gen2\progress.md — Heartbeat and progress tracking
- D:\scp\.agents\teamwork\explorer_survey_1_gen2\handoff.md — Final 5-component handoff report
