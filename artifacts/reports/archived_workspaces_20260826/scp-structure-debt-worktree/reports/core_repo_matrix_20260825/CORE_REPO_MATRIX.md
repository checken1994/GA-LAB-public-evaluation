# Core Repository Matrix â€” scp-agent vs GA-LAB

> Generated:
2026-08-25T21:05:28.2565508+07:00

| Metric | Value |
|---|---:|
| repo_a_head | cb132a5af9f0dbcc6293b939ab32136cef22593c |
| repo_b_head | 23f41b7efae89b3b1e2a96c50cae51021ac9098d |
| repo_a_tracked | 689 |
| repo_b_tracked | 1172 |
| common_paths | 475 |
| common_blob_identical | 435 |
| common_blob_different | 40 |
| only_scp_agent | 214 |
| only_ga_lab | 697 |
| shared_kernel_paths | 6 |
| shared_stack_paths | 203 |
| kernel_only_scp_agent | 14 |
| stack_only_ga_lab | 174 |

## Merge rule

A shared path is not assumed to be the same implementation. Blob-identical paths are kept as one logical file; differing paths require review. Kernel-only files are not copied blindly into GA-LAB. GA-LAB stack files are treated as the integration surface.

## Common paths requiring review

| Path | Class | Blob equal | Decision |
|---|---|---:|---|
| `.gitignore` | common-core | False | SHARED_DIFF_REVIEW |
| `pytest.ini` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/api/routes/batch_benchmark_routes.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/api/routes/v102_v103_routes.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/api/routes/v104_routes.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/api/routes/v105_routes.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/api_server.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/autofix/concurrent_runner.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/autofix/deterministic_worker.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/autofix/engine.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/autofix/engine_extensions.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/autofix/evolution.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/autofix/evolution_parts/reflectmixin.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/autofix/llm_fix.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/autofix/llm_fix_cache.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/autofix/runner_phases/ast_scan.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/autofix/runner_phases/report.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/benchmark/run_benchmark_v2.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/capabilities/voice.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/core/agent_orchestrator.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/core/call_session_hub.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/core/conflict_resolver.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/core/policy_materializer.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/core/request_run_ledger.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/core/safe_process.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/core/subsystem_telemetry.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/forecast/ledger.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/GATEWAY.md` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/hands/planner.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/meta/why_engine.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/runtime/judge.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/runtime/judge_parts/judge_phase_4_governance.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/runtime/judge_parts/judgecore_mixin.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/runtime/slm_base.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/runtime/SLM_NAMING_NOTE.md` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/runtime/slms.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/security/bypass_encrypt.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/security/gcg_attack.py` | stack | False | SHARED_STACK_MERGE_REVIEW |
| `scp/tests/external_audit/test_cascade.py` | common-core | False | SHARED_DIFF_REVIEW |
| `scp/tests/property/test_none_safety.py` | common-core | False | SHARED_DIFF_REVIEW |
