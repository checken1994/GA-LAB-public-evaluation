# DISPATCH — worker_m1

## Identity
- Role: Worker (Implementation & Verification Engineer)
- Type: teamwork_preview_worker
- Working Directory: D:\scp\.agents\teamwork\worker_m1
- Parent: orchestrator_4 (conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff)

## Mandatory Constraints & Bindings
MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13 (defined in d:\scp\.agents\AGENTS.md section 3 — read it first with view_file). You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You MUST read and apply skills:
- d:\scp\.agents\skills\scp-dna\SKILL.md
- d:\scp\.agents\skills\scp-delta-audit\SKILL.md
- d:\scp\.agents\skills\scp-reality-verifier\SKILL.md

Read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md before starting.
Also read D:\scp\GA.md, D:\scp\.agents\AGENTS.md, D:\scp\.agents\teamwork\orchestrator_4\PROJECT.md, and the explorer findings at D:\scp\.agents\teamwork\explorer_survey_1_gen2\handoff.md.

## Exclusive Write Ownership
You exclusively own and may modify ONLY these files:
- `scp/runtime/domain_data_fork.py`
- `scp/runtime/question_router.py`
- `scp/core/partition/shard.py`
- `scp/data_sources/biology.py`
- `scp/data_sources/geology.py`
- `scp/data_sources/usgs.py`
- `scp/data_sources/__init__.py`
- `tests/T02_contract/test_domain_data_fork.py`

DO NOT modify any files outside this list.

## Mission: Implement Milestone 1 — Domain Data Fork & Question Router Integration
Implement Requirement 1 based on the design specification in `D:\scp\.agents\teamwork\explorer_survey_1_gen2\handoff.md`:

1. **USGS Earthquake Integration & Fixes** (`scp/runtime/domain_data_fork.py` & `scp/data_sources/usgs.py`):
   - In `usgs.py`: Declare `USGS_EGRESS_HOST = "earthquake.usgs.gov"` and forward `extra_allowed_hosts=frozenset({USGS_EGRESS_HOST})` in `safe_urlopen`.
   - In `domain_data_fork.py`: Fix `_resolve_usgs` metadata extraction (extract from `meta["top_events"][0]` when available, not just `meta.get("magnitude")` which is None for recent event lists). Add historical earthquake anchors (e.g. Valdivia 1960 M9.5, Sumatra 2004 M9.1) so offline tests work hermetically.

2. **Biology Data Source Integration** (`scp/runtime/domain_data_fork.py`, `scp/data_sources/biology.py`, `scp/data_sources/__init__.py`):
   - Wire `BiologyDataSource` into `domain_data_fork.py` with `_resolve_biology`: support codons (TTT, ATG, etc.), 20 amino acids, organelles (ty thể/mitochondria, ribosome, lục lạp, nucleus), biological constants (46 chromosomes, 3.2B bp genome), and taxonomy fallback.
   - In `data_sources/biology.py`: use `get_api_key("biology", required=False)` from `scp.data_sources.config_loader`.
   - In `data_sources/__init__.py`: instantiate `BiologyDataSource()` in `register_all_sources()`.

3. **Geology Data Source Integration** (`scp/runtime/domain_data_fork.py`, `scp/data_sources/geology.py`):
   - Wire `GeologyDataSource` into `domain_data_fork.py` with `_resolve_geology`: full Mohs hardness scale (talc 1 to diamond 10), Earth layers (crust, mantle, outer core, inner core), and rock types (magma, sedimentary, metamorphic).

4. **Question Router Taxonomy Extension** (`scp/runtime/question_router.py` & `scp/core/partition/shard.py`):
   - Add regex rules for `biology_fact`, `geology_fact`, `earthquake_fact` to `_LOOKUP_RULES`.
   - Add `"geology"` to `_KNOWLEDGE_DOMAINS` in `question_router.py`.
   - Add `"geology"` to `DOMAIN_KEYWORDS` in `scp/core/partition/shard.py`.
   - Ensure existing tests in T07 (such as `test_ask_lookup_fork.py`, `test_w12_conversion_lookup.py`, `test_w12_domain_hint_repair.py`) remain completely green!

5. **Unit Tests** (`tests/T02_contract/test_domain_data_fork.py`):
   - Add comprehensive tests covering:
     * USGS lookup (recent quakes format, historical quakes)
     * Biology lookup (codon, amino acid, organelle, chromosome count)
     * Geology lookup (Mohs scale, Earth layer, rock type)
     * ConfigLoader integration in biology
   - Run verification using the Python environment: `D:\opt\scp-venv-w16\Scripts\python.exe`.
   - Verify `tests/T02_contract/test_domain_data_fork.py`, `tests/test_config_loader.py`, `tests/T07_learning/test_question_router_cascade.py`, `tests/T07_learning/test_question_router_goldset.py`, and `tools/t00_meta_audit.py`.

Deliver complete handoff report in `D:\scp\.agents\teamwork\worker_m1\handoff.md`.
