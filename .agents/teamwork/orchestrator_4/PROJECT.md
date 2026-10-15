# Project: Triển khai Giai đoạn 1 & Giai đoạn 2 SCP (Agent OS)

## Architecture
- Module boundaries:
  1. `scp/runtime/domain_data_fork.py` + `scp/runtime/question_router.py` + `scp/data_sources/`
  2. `scp/api_server_parts/pipeline/` + `scp/api_server_parts/_ask_impl.py`
  3. `scp/knowledge/inbox_watcher.py` + `scp/knowledge/learning_db.py` + `data/inbox_knowledge/`
- Data flow:
  - Ingress request -> Pipeline Security Stage -> Pipeline Lookup Stage (delegating to `question_router` & `domain_data_fork`) -> Pipeline Generation Stage -> Pipeline Verification Stage -> Pipeline Ledger Stage -> Egress response.
  - Offline Knowledge -> `data/inbox_knowledge/` -> `inbox_watcher.py` -> `inspect_untrusted()` -> `claim_extractor` -> `antibody_system` -> `learning_db` (`learning.sqlite`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | USGS Earthquake Resolver | Fix metadata parsing (`top_events` extraction), add offline historical anchors, declare scoped egress host | M1 | Survey Track 1 |
| 2 | Biology Data Source Integration | Wire `BiologyDataSource` (codons, amino acids, organelles, constants, NCBI taxonomy) into `domain_data_fork.py` & `data_sources/__init__.py` | M1 | Survey Track 1 |
| 3 | Geology Data Source Integration | Wire `GeologyDataSource` (Mohs hardness scale 1-10, Earth layers, rock types) into `domain_data_fork.py` | M1 | Survey Track 1 |
| 4 | Question Router Taxonomy Extension | Add `biology_fact`, `geology_fact`, `earthquake_fact` to `_LOOKUP_RULES`; add `geology` to `_KNOWLEDGE_DOMAINS` and `shard.py` | M1 | Survey Track 1 |
| 5 | ConfigLoader Integration | Connect `DataSourceConfigLoader` to commercial/keyed data sources (`biology.py`, etc.) for fail-closed validation | M1 | Survey Track 1 |
| 6 | Ask Pipeline Modular Stages | Create `scp/api_server_parts/pipeline/` (`base.py`, `context.py`, `runner.py`, and 5 stages: Security, Lookup, Generation, Verification, Ledger) | M2 | Survey Track 2 |
| 7 | Backward-Compatibility Hybrid Facade | Refactor `_ask_impl.py` as facade with dynamic namespace resolution (`resolve()`), keeping module globals, AST anchors, string anchors | M2 | Survey Track 2 |
| 8 | Knowledge Inbox Security Gate | Add `inspect_untrusted()` check in `inbox_watcher.py` to quarantine prompt injections and leaked keys | M3 | Survey Track 3 |
| 9 | Knowledge Inbox Format Support | Add `.jsonl` streaming support and markdown chunking to `inbox_watcher.py` | M3 | Survey Track 3 |
| 10 | Knowledge Inbox Idempotency | Add SHA-256 content hashing to prevent duplicate ingestions across runs | M3 | Survey Track 3 |
| 11 | Knowledge Inbox DB & Concurrency | Add queryable schema / explicit connection close on Windows, and atomic `.processing` file staging | M3 | Survey Track 3 |
| 12 | Full System Verification & Audit | Run all 2,745+ tests, verify zero regressions, perform forensic integrity audit | M4 | System Gate |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Domain Data Fork & Question Router | `domain_data_fork.py`, `question_router.py`, `biology.py`, `geology.py`, `usgs.py`, `config_loader.py` | Survey | IN_PROGRESS |
| M2 | Pipeline Pattern Refactor for _ask_impl.py | `scp/api_server_parts/pipeline/*`, `scp/api_server_parts/_ask_impl.py` | Survey | PLANNED |
| M3 | Offline Knowledge Inbox Hardening | `scp/knowledge/inbox_watcher.py`, `scp/knowledge/learning_db.py`, `tests/test_inbox_watcher.py` | Survey | PLANNED |
| M4 | Full System Verification & Reality Audit | Pytest full suite (2,745+ tests), T00 meta audit, Reviewers, Challengers, Forensic Auditor | M1, M2, M3 | PLANNED |

## Code Layout
- M1 Exclusive Files:
  - `scp/runtime/domain_data_fork.py`
  - `scp/runtime/question_router.py`
  - `scp/core/partition/shard.py`
  - `scp/data_sources/biology.py`
  - `scp/data_sources/geology.py`
  - `scp/data_sources/usgs.py`
  - `scp/data_sources/__init__.py`
  - `tests/T02_contract/test_domain_data_fork.py`
- M2 Exclusive Files:
  - `scp/api_server_parts/pipeline/` (all files: `__init__.py`, `base.py`, `context.py`, `runner.py`, `security_stage.py`, `lookup_stage.py`, `generation_stage.py`, `verification_stage.py`, `ledger_stage.py`)
  - `scp/api_server_parts/_ask_impl.py`
  - `tests/T02_contract/test_ask_pipeline_pattern.py` (new tests for pipeline)
- M3 Exclusive Files:
  - `scp/knowledge/inbox_watcher.py`
  - `scp/knowledge/learning_db.py`
  - `scp/knowledge/__init__.py`
  - `tests/test_inbox_watcher.py`
- M4 Verification:
  - Read-only across all codebase and tests
