# Agent3-Gateway-Sentinel — MERGE NOTES (2026-09-29)

## 1. Nguyên nhân (TRUNG THỰC: do tôi gây ra)

Trong quá trình verify regression test (muốn chứng minh old-code-fail/new-code-pass cho finding 402-sentinel), tôi đã chạy:

```
git stash push -- scp/llm_gateway/client.py   # -> NO-OP im lặng: client.py KHÔNG có thay đổi so với HEAD (tôi chưa sửa file nào)
git stash pop                                  # -> POP PHẢI stash@{0} CÓ SẴN TỪ TRƯỚC ("WIP on audit/runtime-guard-AUDIT-20260909: 1fc58c7" — của session/branch khác) lên tree main sạch
```

Kết quả: stash@{0} (WIP lạ) được apply lên main @ 77d44816 -> conflict UU ở ~20 file. Tôi đã dừng toàn bộ thao tác git ngay sau khi nhận lệnh Coordinator.

**Quan trọng:** `git stash pop` khi có conflict KHÔNG drop stash — stash@{0} vẫn còn nguyên trong stash list. WIP của chủ sở hữu KHÔNG bị mất. Chỉ có working tree/index bị bẩn.

## 2. Trạng thái cây trước sự cố (bằng chứng)

Lệnh `git status --short` ĐẦU TIÊN của tôi trong session (trước mọi stash) chỉ có:
```
?? .openclaw/
```
-> Tree sạch, không có UU/M nào trước khi tôi pop.

## 3. File bị ảnh hưởng bởi pop (không phải của tôi, tôi không resolve)

Conflicted/unmerged (UU/UD/DU):
- .agents/skills/scp-delta-audit/SKILL.md (UD)
- scp/api/routes/openai_compat.py (UU) — NẰM TRONG SCOPE AUDIT CỦA TÔI nhưng tôi KHÔNG đụng, chờ Coordinator
- test_api.py (DU)
- tests/T02_contract/test_flow_02_ask_chat_scp_standard.py, test_flow_03_openai_compat_scp_standard.py (UU)
- tests/T03_capability/test_flow_07_autofix_scp_standard.py, test_flow_09_threat_analysis_scp_standard.py, test_security_sweep_s3.py, s4.py, s5.mjs, test_ssrf_sweep_s1.py, s2.py (UU)
- tests/T04_kernel/test_gap13_adversarial_challenge.py, test_verifier_receipt_branches.py (UU)
- tests/T09_golden_task/test_golden_b_epistemic_loop.py (UU)
- tests/reality-tests/reality_4-a-005.py, reality_4-b-013.py, reality_4-d-011.py, run-reality-tests.sh (UU)

Staged (do stash apply đưa vào index): .agents/AGENTS.md, .agents/GEMINI.md (M)
Unstaged M: scp/task_kernel_parts/taskkernel.py, scripts/run_scp_acceptance.py, scripts/run_scp_acceptance_ci.py

## 4. Đề xuất phía nào thắng cho từng marker (đề xuất, KHÔNG tự xử lý)

Với TẤT CẢ các file conflict: đề xuất phía **"Updated upstream" (= HEAD/main @ 77d44816) thắng**, tức hiệu quả là UNDO toàn bộ stash application về trạng thái pre-pop (tree sạch). Lý do: (1) việc apply là TAI NẠN operación của tôi, không phải chủ ý hợp nhất; (2) nội dung stash thuộc branch làm việc khác (audit/runtime-guard-AUDIT-20260909 @ 1fc58c7) — chủ sở hữu stash cần merge branch-level, không phải qua pop ẩu trên main; (3) stash@{0} vẫn còn nguyên trong list nên không mất dữ liệu nào.

Cụ thể:
- UU files: giữ nguyên phiên bản HEAD (Updated upstream), bỏ phía "Stashed changes".
- UD .agents/skills/scp-delta-audit/SKILL.md: giữ phiên bản HEAD (file tồn tại) — stash muốn xóa.
- DU test_api.py: giữ trạng thái HEAD (đã xóa) — stash muốn sửa lại.
- File M trong index (.agents/AGENTS.md, .agents/GEMINI.md): restore về HEAD.
- File M unstaged (taskkernel.py, run_scp_acceptance*.py): TÔI KHÔNG SỬA các file này — không rõ xuất xứ (có thể do stash apply thêm vào worktree); đề xuất Coordinator so `git diff` rồi restore về HEAD nếu nội dung trùng stash.

## 5. File của tôi (untracked, xin GIỮ — không xóa)

- tests/T05_gateway/test_gateway_402_breaker.py — 3 tests, PASS exit 0 (chạy trên gateway code = HEAD, không phụ thuộc file conflict)
- tests/T05_gateway/test_gateway_hedge_pool.py — 3 tests, PASS exit 0 (như trên)
- (Chưa copy sang D:\scp: tests/T05_gateway/test_gateway_kill_switches.py đang nằm trong workspace tmp của agent, sẽ copy + chạy SAU KHI Coordinator restore tree)

Tôi KHÔNG có chỉnh sửa nào trong bất kỳ file conflicted nào ở trên. `git diff HEAD -- scp/llm_gateway/client.py` = 0 dòng (client.py nguyên vẹn).

## 6. Việc đang dở / chờ gì để tiếp tục

- Audit read-only: ĐÃ ĐỌC XONG toàn bộ phạm vi (scp/llm_gateway/*, scp/api/routes/*, scp/api_server.py, scp/api_server_parts/*, mini-services/llm-bridge/* TS).
- Chờ: (1) Coordinator restore tree về HEAD; (2) sau đó tôi copy file test thứ 3, chạy `pytest tests/T05_gateway -q` lần cuối (baseline trước sự cố: 89 passed exit 0), và viết báo cáo .openclaw/multi-agent/Agent3-Gateway-Sentinel.md.
- Tôi sẽ KHÔNG chạy thêm lệnh git nào cho đến khi có lệnh mới từ Coordinator.
