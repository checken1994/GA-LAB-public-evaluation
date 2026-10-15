# Báo cáo Agent 2 — Kernel Keeper — SCP Audit Vòng 3 (2 lượt chạy)

- **HEAD khi bắt đầu (lượt 1):** 77d44816 (fix(kernel): admission control agrees with dedupe)
- **HEAD khi bắt đầu (lượt 2):** 0d61f32c (test(gateway)...) — công việc lượt 1 đã được Coordinator giải cứu trong commit **d30aa307** ("fix(acceptance): align A12 review-backlog oracle with new admission semantics"), sau đó Coordinator/Agent khác có thêm commit mới lên đầu (hiện HEAD di chuyển; kiểm chứng bằng `git log --oneline -1` lúc 03:1x là 0d61f32c).
- **Skill đã đọc:**
  - `D:\scp\.agents\skills\scp-task-kernel-review\SKILL.md`
  - `D:\scp\.agents\skills\scp-dna\SKILL.md`
  - `D:\scp\.openclaw\multi-agent\ASSIGNMENTS.md` (hồ sơ phân công)
- **Bối cảnh lượt 1:** giữa phiên, worktree bị stash-pop từ phiên khác → ~20 file conflict (chi tiết: `Agent2-Kernel-Keeper-MERGE-NOTES.md`, đã được Coordinator lưu trữ làm bằng chứng điều tra). Coordinator resolve về HEAD + commit d30aa307 giữ nguyên toàn bộ công việc của tôi.

## Phạm vi đã audit (tổng cộng 2 lượt: 9 file + commit diff 77d44816)

1. `scp/task_kernel_parts/definitions.py` (STATES/ALLOWED_TRANSITIONS/TERMINAL/checkpoint secret guard)
2. `scp/task_kernel_parts/taskkernel.py` (2053 dòng — toàn bộ: transition, claim/lease/heartbeat/renew, expire_leases, checkpoint/finalize, record_action_dispatched, enter_reconciling/reconcile_unknown, commit_completed/commit_approval/commit_failed/auto_resolve/fail_task_fail_closed, set_task_kill, auto_reconcile_orphans, recover_on_boot, verify_journal, rebuild_projection, recovery_decision, in_flight/pending_review)
3. `scp/task_kernel_parts/idempotency.py`
4. `scp/task_kernel.py` (public contract/re-export)
5. `scp/kernel_storage.py` (SQLite storage, per-context conn, BEGIN IMMEDIATE)
6. `scp/kernel_storage_pg.py` (PG storage, advisory-lock write slot, SQL dialect translation)
7. `scp/ask_kernel_adapter.py` (1239 dòng — begin/dedupe/backpressure, verify_response, finalize S19 paths, escalate, fail, heartbeat, ledger)
8. `scp/api/background_jobs.py` + `scp/api_server_parts/lifespan.py` (watchdog wiring — chỉ đọc để đánh giá "watchdog có đủ không")
9. `scripts/run_scp_acceptance.py`, `scripts/run_scp_acceptance_ci.py` (acceptance oracle A12) + tests/T04_kernel liên quan (mutation contract, lease fencing, gap13, adversarial, autonomous lifecycle)

## Findings

### [OBSERVED][HIGH] F1 — Acceptance oracle A12 chết vĩnh viễn sau 77d44816 (semantics giả định cũ)
- **file:line:** `scripts/run_scp_acceptance.py:904`, `scripts/run_scp_acceptance_ci.py:108`
- **Bằng chứng:** cả 2 oracle assert `kernel.in_flight_count() == len(expected_review_ids)` với expected_review_ids là 3 task **HUMAN_REVIEW**. Sau 77d44816, `in_flight_count()` loại HUMAN_REVIEW ⇒ biểu thức luôn `0 == 3` ⇒ mọi lần chạy acceptance sau này FAIL bắt buộc tại gate cuối. Đúng kịch bản "có chỗ khác giả định semantics cũ" trong nhiệm vụ.
- **Đã fix (lượt 1, được Coordinator commit trong d30aa307):** oracle đổi sang `pending_review_count()` (đếm đúng backlog review); hidden-active execution vẫn bị chặn bởi check `observed_nonterminal` (main) / `hidden_active` (CI) — không hạ chuẩn, strictness giữ nguyên.
- **Regression:** `tests/T04_kernel/test_admission_semantics_77d44816.py::test_acceptance_oracles_count_review_backlog_not_in_flight` — old-code-fail (source chứa assert cũ) / new-code-pass.

### [OBSERVED][LOW] F2 — Docstring `in_flight_count()` trỏ tới `pending_count()` không tồn tại
- **file:line:** `scp/task_kernel_parts/taskkernel.py:2086` (lúc audit)
- **Bằng chứng:** docstringFix 2026-09-29 viết "nếu cần đếm thô, dùng pending_count()" — method thật tên `pending_review_count()`; Python không fail nhưng escape-hatch nêu trong hợp đồng là dead-reference.
- **Đã fix (lượt 1, trong d30aa307):** đổi tên trong docstring.
- **Regression:** `test_kernel_docstring_points_to_existing_counter`.

### [OBSERVED][HIGH] F3 — Admission cap vẫn sống nhưng không có telemetry "backlog gần chạm cap" (đánh giá, không vá)
- **file:line:** `scp/ask_kernel_adapter.py:296`
- **Bằng chứng:** cap 200 chỉ raise khi ĐÃ chạm (`>=`), không có log/metric trước ngưỡng; sự cố 09-21→09-29 tích lũy 199/200 không ai thấy. `pending_review_count()` mới đã提供 telemetry cho review-backlog, nhưng in-flight load không có cảnh báo sớm (ví dụ log tại ≥80% cap). Đây là khoảng trống observability, không phải lỗi logic — **không vá** trong vòng này (tránh mở rộng mặt giải phóng); để open question cho Coordinator.

### [OBSERVED][HIGH→ĐÃ VÁ lượt 2] F4 — `commit_failed()`/`set_task_kill()` ghi state RAW, bỏ qua ALLOWED_TRANSITIONS ⇒ journal chứa edge ngoài luật
- **file:line:** `scp/task_kernel_parts/taskkernel.py` — `commit_failed` (~:1810-1830), `set_task_kill` (~:1893-1912) tại HEAD 0d61f32c
- **Bằng chứng (probe thực nghiệm, DB tạm):**
  - `set_task_kill` từ VERIFYING → journal ghi `VERIFYING→CANCELLED` (map cấm)
  - `set_task_kill` từ RECOVERING → `RECOVERING→CANCELLED` (map cấm)
  - `commit_failed(RETRYABLE)` từ VERIFYING → `VERIFYING→RETRY_SCHEDULED` (map cấm)
  - `commit_failed(class=UNKNOWN)` từ LEASED → `LEASED→UNKNOWN` (map cấm)
  - `verify_journal()` vẫn True (hash-chain chỉ lim keo记得 tính, không kiểm luật chuyển đổi) ⇒ edge ngoài luật **không bị phát hiện bởi bất kỳ check nào**.
- **Tác hại:** `rebuild_projection()` replay journal **không validate map** (chỉ lấy `to_state` cuối) — mọi projection rebuild/consumer kế thừa edge ngoài luật; hợp đồng "map = luật" bị chính writer của kernel phá (vi phạm nguyên tắc skill scp-task-kernel-review: "không module tự set state").
- **Đã fix (lượt 2):**
  1. Thêm `_legal_or_nearest(from_state, target, note)` — mọi raw-commit phải đi qua gate: target không có trong map → reroute tới NEAREST LEGAL edge giữ ý định an toàn (kill→FAILED fail-closed; UNKNOWN→RECOVERING theo `recovery_decision('LOST_RESPONSE',...)`; RETRY_SCHEDULED bất khả thi từ source → FAILED + `planned_retry` ghi trong payload), reroute luôn ghi trong `reason` của event.
  2. Áp gate vào `commit_failed()` (planned_target + reroute + `event_payload["planned_retry"]`) và `set_task_kill()` (kill_target/kill_reason).
  3. **Map được sửa để đồng bộ hợp đồng thật:** theo hợp đồng retry đã được 3 test hiện hữu chốt (b5 adversarial: `RUNNING→RETRY_SCHEDULED`; autonomous verification-fail: `RUNNING→RETRY_SCHEDULED`; gap13 drive: dùng để setup state RETRY_SCHEDULED), bổ sung `RETRY_SCHEDULED` vào mục tiêu hợp lệ của RUNNING/WAITING_TOOL/VERIFYING trong `definitions.py` — trước đó raw-code commit edge này ngoài luật (chính là dạng "map không đồng bộ code" mà audit phải tìm).
- **Rollback:** `git checkout -- scp/task_kernel_parts/taskkernel.py scp/task_kernel_parts/definitions.py` (nhỏ, không migration, không đổi schema).
- **Regression (old-code-fail/new-code-pass):** `tests/T04_kernel/test_transition_map_authority.py` — 5 test:
  - kill từ VERIFYING/RECOVERING → edge legal (FAILED + `kill_reroute` trong reason) — old code ghi edge ngoài luật;
  - kill từ QUEUED giữ nguyên hành vi CANCELLED (no-reroute);
  - retryable từ VERIFYING → `VERIFYING→RETRY_SCHEDULED` hợp lệ (map mới đồng bộ retry contract) — old map + old code fail;
  - uncertain từ LEASED → `LEASED→RECOVERING` + `planned_retry=UNKNOWN` — old code ghi `LEASED→UNKNOWN` ngoài luật.

### Kết luận khác (không phải finding)
- Lease/fencing: fencing token tăng đơn điệu per-task, `_assert_lease` chặn released/expired/epoch-lệch/token-cũ; `renew_lease` refuse đúng với non-renewable states; OCC version trên leases + tasks nhất quán. **Không thấy lỗi mới.**
- Checkpoint: `_assert_checkpoint_safe` chặn secret; `finalize_checkpoint` không fabricate, chặn khi task chưa quyết định; UNKNOWN checkpoint thuộc riêng reconcile. **Không thấy lỗi mới.**
- Journal/projection: hash-chain verify tốt; **điểm yếu cấu trúc đã biết** là rebuild_projection không validate map — F4 làm edge ngoài luật không thể sinh ra nữa từ các writer của kernel (mọi writer khác đều đi qua `transition()` có gate map). Việc thêm map-validation vào `rebuild_projection` là hardening đề xuất cho vòng sau (không vá vòng này vì cần quyết định tương thích dữ liệu cũ trong DB thật).
- Watchdog: `expire_leases` (30s) + `auto_reconcile_orphans` (60s) đều `required=True` trong registry; VERIFYING-expired → HUMAN_REVIEW (non-autonomous) → không còn bị chặn intake sau 77d44816 nhưng **vẫn nằm trong backlog telemetry** (`pending_review_count`) — đúng ý đồ fix 77d44816; task RUNNING treo vĩnh viễn vẫn được dọn bởi watchdog (lease-expiry + orphan reconcile). Không thấy lỗ hổng mới từ semantics change ngoài F1/F2/F4.

## Đã verify (lệnh chạy thật)

| Lượt | Lệnh | Kết quả |
|---|---|---|
| 1 (baseline trước vá, HEAD 77d44816) | `python -X utf8 -m pytest tests/T04_kernel -q` | **320 passed, 23 skipped — EXIT=0** (74.19s) |
| 1 (sau vá + test mới) | `python -X utf8 -m pytest tests/T04_kernel/test_admission_semantics_77d44816.py -q` | **3 passed — EXIT=0** (1.09s) |
| 1 (full suite sau vá) | `pytest tests/T04_kernel -q` | BỊ CHẶN bởi conflict ngoài phạm vi (2 file UU SyntaxError) — EXIT=2; sau đó Coordinator resolve + verify T04+T05 = **418 passed / 23 skipped**, t00_meta_audit 0 regressions |
| 2 (verify sau-giải cứu, yêu cầu #1) | `python -X utf8 -m pytest tests/T04_kernel -q` | **323 passed, 23 skipped — EXIT=0** (75.79s) — 0 collection error, gồm 3 test regression của tôi trong d30aa307 |
| 2 (sau vá F4) | `python -X utf8 -m pytest tests/T04_kernel -q` | **332 passed, 23 skipped — EXIT=0** (73.00s) — 323 cũ + 5 test mới − 0 fail; +9 test so với baseline lượt 1 (3 admission + ... trong đó d30aa307 đóng góp 3) |
| 2 (focus sau vá F4) | `pytest tests/T04_kernel/test_transition_map_authority.py test_task_kernel_mutation_contract.py test_adversarial_kernel_flaws.py -q` | **53 passed — EXIT=0** (6.79s) |

Không có test nào bị delete/skip/xfail; không hạ assertion; không đổi fail-closed→fail-open; không commit; không đụng `spec/`, `data/*.sqlite3`, service thật.

## Chưa xử lý / open questions

1. **[UNPROVEN→cần quyết định] Map-validation inside `rebuild_projection`:** nên thêm check `to_state ∈ ALLOWED_TRANSITIONS[src]` khi replay không? Cần quyết định xử lý dữ liệu lịch sử trong `data/ask_task_kernel.sqlite3` thật (nếu có edge ngoài luật từ trước — khả năng cao có, vì F4 tồn tại từ trước). Không vá trong vòng này.
2. **[SUPPORTED_INFERENCE] Telemetry gần-cap cho admission (F3):** đề xuất log WARNING khi `in_flight_count() >= 0.8*cap` + expose `pending_review_count()` qua endpoint health/metrics. Cần Coordinator duyệt phạm vi (chạm api routes).
3. **[SUPPORTED_INFERENCE] WAITING_APPROVAL nằm ngoài `STATES`:** `transition()` chấp nhận qua hard-code, map có key riêng — hoạt động, nhưng 2 nguồn sự thật (STATES vs map keys) dễ lệch nữa. Đề xuất gộp vào STATES trong vòng hardening sau (rộng hơn phạm vi vá nhỏ).
4. **[UNPROVEN] Backlog HUMAN_REVIEW thật trong `data/ask_task_kernel.sqlite3` (199 task):** không đụng DB thật theo quy tắc — không verify được hành vi post-fix trên dữ liệu sống; khuyến nghị human-flow review/resolve backlog này (ra quyết định cho từng task withheld).
5. Bản vá F4 chưa được Coordinator commit — đang ở working tree (diff 2 file + 1 test mới) để Coordinator review.
