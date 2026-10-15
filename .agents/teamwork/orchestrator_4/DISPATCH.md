# DISPATCH — orchestrator_4

## Date: 2026-10-08T05:32:10Z
## Recipient: orchestrator_4 (teamwork_preview_orchestrator)
## Working Directory: D:\scp\.agents\teamwork\orchestrator_4
## Project Root: D:\scp

## Mandatory Binding
MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13 (defined in d:\scp\.agents\AGENTS.md section 3 — read it first with view_file). You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.
You MUST read and apply skills: d:\scp\.agents\skills\scp-dna\SKILL.md, d:\scp\.agents\skills\scp-delta-audit\SKILL.md, d:\scp\.agents\skills\scp-reality-verifier\SKILL.md.

## Task Objective
Triển khai toàn bộ Giai đoạn 1 & Giai đoạn 2 của phương án hệ thống SCP (Agent OS).

## Authoritative Reference
- `D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md` (entry `2026-10-08T05:32:10Z`)
- `D:\scp\GA.md`
- `D:\scp\.agents\AGENTS.md`
- `D:\scp\.agents\GEMINI.md`

## Requirements
1. Hoàn tất kết nối dữ liệu chuyên ngành vào `scp/runtime/domain_data_fork.py` và `scp/runtime/question_router.py` (USGS Earthquake, Biology, Geology, ConfigLoader cho các API cần key).
2. Tái cấu trúc `_ask_impl.py` thành Pipeline Pattern trong `scp/api_server_parts/pipeline/` (security, lookup, generation, verification, ledger) đảm bảo 2.745+ test hiện hành giữ nguyên màu xanh.
3. Xây dựng hộp thư tự học offline `data/inbox_knowledge/` qua `scp/knowledge/inbox_watcher.py` tích hợp `claim_extractor`, `antibody_system`, và `learning.sqlite`.
4. Chạy kiểm chứng toàn bộ tests sau khi hoàn thành. Không được delete/skip/xfail bất kỳ test nào.

## 2026-10-08T05:34:20Z
Sender: 60b091db-c8ae-4485-a6bf-ec46ad572318
Task: Triển khai toàn bộ Giai đoạn 1 & Giai đoạn 2 của phương án hệ thống SCP (Agent OS).
Requirements:
1. Hoàn tất kết nối dữ liệu chuyên ngành vào scp/runtime/domain_data_fork.py và scp/runtime/question_router.py (USGS Earthquake, Biology, Geology, ConfigLoader cho các API cần key).
2. Tái cấu trúc _ask_impl.py thành Pipeline Pattern trong scp/api_server_parts/pipeline/ (security, lookup, generation, verification, ledger) đảm bảo 2.745+ test hiện hành giữ nguyên màu xanh.
3. Xây dựng hộp thư tự học offline data/inbox_knowledge/ qua scp/knowledge/inbox_watcher.py tích hợp claim_extractor, antibody_system, và learning.sqlite.
4. Chạy kiểm chứng toàn bộ tests sau khi hoàn thành. Không được delete/skip/xfail bất kỳ test nào.
