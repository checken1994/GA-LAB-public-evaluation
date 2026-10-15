# Agent2 Kernel-Keeper — MERGE NOTES (2026-09-29, giữa chiến dịch Vòng 3)

HEAD làm việc của tôi: 77d44816 (không đổi). Tôi KHÔNG khởi phát merge/stash-pop nào
trong phiên này; không có thao tác git index nào được tôi thực hiện ngoài `git status`,
`git diff`, `git show`, `git log`, `git grep` (chỉ đọc). Trạng thái UU/UD/DU hiện tại
xuất hiện từ bên ngoài (agent/process khác trên cùng worktree) trong lúc tôi chạy
verify sau-patch; phát hiện lúc pytest collection báo SyntaxError ở 2 file T04.

## 1. File tôi đã đụng (đầy đủ) — TẤT CẢ ĐÃ XONG, KHÔNG nằm trong tập conflict

| File | Loại thay đổi | Trạng thái marker | Kết quả cuối mong muốn |
|---|---|---|---|
| scp/task_kernel_parts/taskkernel.py | Sửa docstring `in_flight_count()`: `pending_count()` (không tồn tại) → `pending_review_count()` | 0 marker (working tree sạch marker) | GIỮ NGUYÊN bản working tree hiện tại (diff 2 dòng, revert bằng `git checkout -- scp/task_kernel_parts/taskkernel.py`) |
| scripts/run_scp_acceptance.py | Oracle A12: `in_flight_count() == len(expected_review_ids)` → `pending_review_count() == len(expected_review_ids)` + đổi message | 0 marker | GIỮ NGUYÊN bản working tree hiện tại (revert: `git checkout -- scripts/run_scp_acceptance.py`) |
| scripts/run_scp_acceptance_ci.py | Như trên cho CI runner | 0 marker | GIỮ NGUYÊN bản working tree hiện tại (revert: `git checkout -- scripts/run_scp_acceptance_ci.py`) |
| tests/T04_kernel/test_admission_semantics_77d44816.py | File MỚI (untracked), regression 3 test — đã PASS (3 passed) trước khi conflict nổ ra | 0 marker | GIỮ — không xóa (untracked, không dính index) |
| D:\scp\.openclaw\tmp\agent2_kernel_patch.py | Script vá (scratch) | — | Có thể xóa khi dọn dẹp |

Không một dòng thay đổi nào của tôi nằm trong các file đang UU/UD/DU (đã verify:
marker check = 0 trên cả 4 file của tôi; `git diff` của tôi chỉ chạm đúng 3 file tracked ở trên).

## 2. Lựa chọn nội dung cho từng marker conflict (bên "Updated upstream" / "Stashed changes")

Tôi KHÔNG có stake trong bất kỳ file conflict nào — không có edits của tôi bên trong
chúng, nên tôi không đề nghị phía nào thắng cho từng marker. Tập conflict (theo
`git status --porcelain` lúc 02:4x):

- UD: .agents/skills/scp-delta-audit/SKILL.md
- DU: test_api.py
- UU: scp/api/routes/openai_compat.py
- UU: tests/T02_contract/test_flow_02_ask_chat_scp_standard.py
- UU: tests/T02_contract/test_flow_03_openai_compat_scp_standard.py
- UU: tests/T03_capability/test_flow_07_autofix_scp_standard.py
- UU: tests/T03_capability/test_flow_09_threat_analysis_scp_standard.py
- UU: tests/T03_capability/test_security_sweep_s3.py
- UU: tests/T03_capability/test_security_sweep_s4.py
- UU: tests/T03_capability/test_security_sweep_s5.mjs
- UU: tests/T03_capability/test_ssrf_sweep_s1.py
- UU: tests/T03_capability/test_ssrf_sweep_s2.py
- UU: tests/T04_kernel/test_gap13_adversarial_challenge.py
- UU: tests/T04_kernel/test_verifier_receipt_branches.py
- UU: tests/T09_golden_task/test_golden_b_epistemic_loop.py
- UU: tests/reality-tests/reality_4-a-005.py
- UU: tests/reality-tests/reality_4-b-013.py
- UU: tests/reality-tests/reality_4-d-011.py
- UU: tests/run-reality-tests.sh
- M  (staged, không marker): .agents/AGENTS.md, .agents/GEMINI.md — không phải của tôi

Lưu ý vận hành: 2 file UU trong T04 (test_gap13_adversarial_challenge.py,
test_verifier_receipt_branches.py) đang chứa marker `<<<<<<< Updated upstream` tại
dòng ~904/2xx → SyntaxError → BLOCK toàn bộ `pytest tests/T04_kernel` (collection
error). Cho tới khi Coordinator resolve, lệnh verify chuẩn của Agent2 KHÔNG chạy
được đầy đủ; số verify hợp lệ hiện có ghi ở mục 3.

## 3. Trạng thái verify của Agent2 (bằng chứng, theo thứ tự thời gian)

1. Baseline TRƯỚC khi vá, tại HEAD 77d44816 (tree khi đó chưa conflict):
   `python -X utf8 -m pytest tests/T04_kernel -q` → **320 passed, 23 skipped, EXIT=0** (74.19s).
2. Sau khi vá 3 file + thêm test mới:
   `python -X utf8 -m pytest tests/T04_kernel/test_admission_semantics_77d44816.py -q`
   → **3 passed, EXIT=0** (1.09s).
   `py_compile scripts/run_scp_acceptance.py scripts/run_scp_acceptance_ci.py` → EXIT=0.
3. Full-suite sau-vá: **BỊ CHẶN** bởi conflict ngoài phạm vi tôi (2 file UU T04
   SyntaxError khi collection — EXIT=2). Đây là blocker môi trường, không phải lỗi
   của thay đổi Agent2.

## 4. Cam kết

- Tôi đã DỪNG mọi thao tác git index/merge/stash từ lúc nhận chỉ thị; không commit,
  không add/restore/checkout lên file UU, không stash pop/drop/apply.
- Không tự resolve tiếp các conflict. Chờ quyết định Coordinator.
- Các sửa của Agent2 (mục 1) độc lập hoàn toàn với tập conflict; nếu Coordinator
  cần revert-thành-trống để gỡ rối merge, revert 3 file tracked không ảnh hưởng
  test mới (untracked).
