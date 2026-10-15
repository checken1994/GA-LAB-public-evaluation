# DISPATCH

## 2026-09-27T08:22:36Z
You are the Project Orchestrator (orchestrator_2) for the comprehensive autonomous remediation, re-audit, live operational verification, and runtime fixing cycle on the SCP system.

## Working Environment
- Project Root: D:\scp
- Orchestrator Working Directory: D:\scp\.agents\teamwork\orchestrator_2
- Integrity Mode: development
- User Request: Read D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md (specifically the latest request dated 2026-09-27T08:21:00Z)
- Primary Audit Reference: D:\scp\DEEP_AUDIT_REPORT_20260927.md (1,260 lines, 57 findings across R1-R6)
- Standards: .agents/AGENTS.md, 26 SCP DNA principles, Fail-Closed & Evidence-First invariants (FA-01 to FA-13)

## Mission & Requirements
1. R1: Full remediation of all 12 Critical vulnerabilities:
   - SEC-R1-01: scp/pc_control/pc_controller.py:246-250 (HumanConfirmationStore mandatory)
   - SEC-R1-02: scp/capabilities/tools.py:382-425 (bounds check dir/ls, tighten SafeCommandRunnerTool sandbox, block python -c)
   - SEC-R2-01: scp/runtime/judge.py:305-325 (no fail-open single-vendor downgrade, mark DEGRADED/UNCERTAIN)
   - SEC-R2-02: scp/api_server_parts/_ask_impl.py:688-689 & scp/api/chat.py (remove bypass_verdict_pass=True, fail-closed on missing governance)
   - SEC-R3-01: scp/task_kernel_parts/taskkernel.py:860-863 (check cur.rowcount > 0, raise OptimisticLockError)
   - SEC-R3-02: scp/task_kernel_parts/taskkernel.py:820-850 (check task['active_lease_id'] == lease['lease_id'] before reclaim)
   - R4-F01: scp/knowledge/domain_knowledge.py:436-464 (rewrite FactSeparator with stopwords, min 3 content tokens, semantic entity constraints, remove tautology)
   - R4-F03: scp/core/top_systems_learning.py:95-107 (Unidecode / Cyrillic/Greek homoglyphs normalization in Semantic Firewall)
   - R4-F04: scp/rag/canonical_retriever.py:41-54 (fix corpus_all_fetched.jsonl missing file handling, transparent fallback)
   - SEC-R6-01 & SEC-R6-02: Replace 131 empty `pass` tests and 13 placebo tests (`assert _AVAILABLE`) with real behavior assertions; fix 4 broken imports in production code (admin_v100.py, v105_routes.py, reverify_scheduler.py, ask_kernel_adapter.py).

2. R2: Fix High (P1) reliability & boundary vulnerabilities:
   - Pseudo-auth in extractCallerAuth (dashboard)
   - IP spoofing prevention (X-Forwarded-For, X-Real-IP in dashboard/src/middleware.ts; tighten private IP allowlist)
   - Bun microservices endpoint token protection (mini-services/llm-bridge)
   - Enforce enforce_egress_policy() on network calls & browser sessions

3. R3: Independent Re-Audit & Verification Gate:
   - pytest tests/ --collect-only -q (0 collection errors)
   - python tools/t00_meta_audit.py (0 regressions vs baseline)
   - python tools/stale_code_tripwire.py (0 broken imports or drift)
   - pytest tests/integration/ -v (contract & integration tests pass)

4. R4: Live Cluster Launch & Full Operational Probing:
   - Start API Server (port 8000), Bun LLM Bridge (port 8081), Dashboard Next.js (port 3000)
   - Probe live conversational chat ("bạn là ai", "hôm nay thế nào") -> PASS verdict, not withheld
   - Probe factual query triggering retrieval & FactSeparator -> valid trace_id
   - Probe /v3/trace/{trace_id} with admin token -> inspect decision tree & audit ledger
   - Probe autonomous task execution (safe tool invocation, TaskKernel queue & lease heartbeat)
   - Fix any runtime errors/exceptions that emerge during live operation
   - Clean teardown: Stop all service processes, freeing ports 8000, 8081, 3000 completely

5. Protocol:
   - Create and maintain plan.md, progress.md, and BRIEFING.md in your working directory D:\scp\.agents\teamwork\orchestrator_2
   - Dispatch workers and reviewers under D:\scp\.agents\teamwork/
   - Follow strict SCP DNA and Fail-Closed & Evidence-First principles
   - When all requirements are met and verified, write handoff.md and send a message claiming victory to the Sentinel.

## 2026-09-27T10:53:49Z
[SERVER RESTART RESUME NOTICE]
Hệ thống vừa khởi động lại sau thời gian gián đoạn.
- Tất cả các tác vụ nền và subagent nội bộ đã bị dừng theo cơ chế restart của hệ thống.
- Yêu cầu Orchestrator:
  1. Kiểm tra trạng thái hiện tại của các worker (worker_m1_core, worker_m1_runtime_knowledge, worker_m1_tests, worker_m2_p1_boundary) thông qua manage_subagents(Action="list") hoặc tệp progress.md của từng worker.
  2. Gửi tin nhắn đánh thức (revive) hoặc tái khởi động (re-dispatch) các worker để tiếp tục hoàn thành các phần việc đang dang dở trong Milestone 1 (P0 Critical) và Milestone 2 (P1 High).
  3. Tiến hành Milestone 3 (Re-Audit Gate: kiểm tra 0 regression bằng tools/t00_meta_audit.py, tools/stale_code_tripwire.py, pytest tests/ --collect-only -q, pytest tests/integration/).
  4. Thực thi Milestone 4 (Live Cluster Launch & Automated Probing: API 8000, Bun 8081, Dashboard 3000; kiểm tra luồng chat, tra cứu tri thức + trace_id, /v3/trace HMAC audit ledger, task kernel execution; sửa lỗi runtime; clean teardown giải phóng cổng).
  5. Khi toàn bộ các mục tiêu hoàn tất và được xác thực, nộp handoff.md và gửi tin nhắn tuyên bố chiến thắng về cho Sentinel để tiến hành Victory Audit độc lập.

## 2026-09-27T11:37:56Z
[SERVER RESTART #2 RESUME DIRECTIVE]
Server vừa khởi động lại lần thứ 2. Hiện trạng thực tế trên đĩa:
- Đã sửa đổi 45 tệp, +1,974/-377 dòng code.
- worker_m1_runtime_knowledge_gen2: ĐÃ XONG 100%, có handoff.md.
- worker_m2_p1_boundary_gen2: ĐÃ XONG 100%, có handoff.md.
- worker_m1_core_gen2: ~95% xong (đã sửa xong pc_controller.py, tools.py, taskkernel.py, 15/15 tests passed), chỉ thiếu handoff.md.
- worker_m1_tests_gen2: ~70% xong (13 placebo đã thay, còn batch empty pass tests cuối cùng).

Chỉ thị hành động cho Orchestrator:
1. Xác nhận worker_m1_core_gen2 (viết hoặc thu thập handoff.md) và yêu cầu worker_m1_tests_gen2 (hoặc trực tiếp xử lý) thay thế nốt batch empty pass tests cuối cùng.
2. Tiến hành chạy ngay Cổng Tái Kiểm Toán Độc Lập - Milestone 3 (Re-Audit Gate):
   - pytest tests/ --collect-only -q (xác nhận 0 collection errors)
   - python tools/t00_meta_audit.py (xác nhận 0 hồi quy)
   - python tools/stale_code_tripwire.py (xác nhận 0 drift/broken imports)
   - Chạy integration test suite (pytest tests/integration/ -v)
3. Triển khai ngay Milestone 4 (Live Cluster Launch & Operational Probing):
   - Khởi chạy API Server (:8000), Bun LLM Bridge (:8081), Dashboard Next.js (:3000).
   - Kiểm tra luồng chat thực tế ("bạn là ai", "hôm nay thế nào") -> nhận phản hồi, verdict PASS, không bị withheld.
   - Kiểm tra truy vấn tra cứu thực tế -> kích hoạt FactSeparator và trả về trace_id.
   - Kiểm tra /v3/trace/{trace_id} với token admin -> kiểm chứng cây quyết định và HMAC audit ledger.
   - Kiểm tra thực thi lệnh của tác nhân tự trị (safe tool invocation, task kernel queue & lease heartbeat).
   - Sửa bất kỳ lỗi runtime nào phát sinh ngay tại chỗ.
   - Dọn dẹp sạch sẽ (Clean Teardown): Dừng toàn bộ các tiến trình dịch vụ, giải phóng hoàn toàn các cổng 8000, 8081, 3000.
4. Tổng hợp báo cáo handoff.md và gửi tin nhắn tuyên bố chiến thắng (victory claim) về cho Sentinel để Sentinel kích hoạt Victory Auditor độc lập thẩm định nghiệm thu.
