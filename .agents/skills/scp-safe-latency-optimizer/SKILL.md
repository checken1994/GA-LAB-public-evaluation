---
name: scp-safe-latency-optimizer
description: Phân tích và tối ưu latency của Policy Pipeline, Sandbox và computer-use SCP mà không tắt policy, verifier, revocation, egress control hoặc recovery guard. Use when the user asks why SCP is slow, wants to reduce p95/p99 latency, optimize policy/sandbox/browser execution, or tune concurrency safely.
---

# SCP Safe Latency Optimizer

## Nguyên tắc

> **Tối ưu latency đúng là làm đường an toàn ngắn hơn, không phải xóa đường an toàn.**

Không tối ưu bằng cảm giác hoặc latency trung bình. Đo từng đoạn, so sánh p50/p95/p99 và kiểm tra safety metric song song.

## Mô hình đo

```text
L_total = L_queue + L_policy + L_sandbox_attach + L_driver
        + L_observation + L_verifier + L_commit
```

Mỗi span cần `task_id`, `attempt_id`, `step_id`, `risk_tier`, `cache_hit`, `sandbox_profile`, `provider`, `state_hash_before`, `state_hash_after` và `outcome`.

## Quy trình tối ưu

1. Ghi baseline workload thật; không dùng một task quá nhỏ làm đại diện.
2. Instrument queue, policy, sandbox, driver, observation, verifier và commit.
3. Xác định critical path và bottleneck bằng p95/p99, queue depth, timeout và fallback.
4. Phân loại action R0 read-only, R1 local reversible, R2 external write và R3 sensitive/destructive.
5. Tối ưu policy hot path: schema validator local, capability verify, compiled policy lookup, quota check và PEP gần driver.
6. Cache capability có điều kiện theo task/attempt/tool/resource/data class/policy version/revocation epoch; invalidate khi revoke, kill, state đổi hoặc risk tăng.
7. Dùng fast lane chỉ cho R0/R1; R2/R3 vẫn fresh decision, approval và synchronous verification.
8. Dùng warm sandbox copy-on-write, session pinning và clean template; không reuse secret, cookie, workspace hoặc process tree bẩn.
9. Dùng observation ladder: driver result → accessibility/DOM diff → region screenshot → full screenshot → human review.
10. Chỉ bundle các action cùng risk/tool/domain và dừng khi URL, domain hoặc state hash lệch.
11. Chuyển upload evidence, dashboard projection, metrics aggregation và enrichment không-critical sang async.
12. Chạy adversarial benchmark và so sánh safety metrics trước khi chấp nhận tối ưu.

## Safety metrics không được xấu đi

`unknown_state_rate`, `duplicate_side_effect_count`, `policy_bypass_count`, `revocation_propagation_ms`, `cleanup_failure_rate`, `secret_leak_count` và `human_review_rate` phải được theo dõi cùng latency.

## Những tối ưu bị cấm

- Tắt Policy Gateway hoặc PEP.
- Bỏ verifier để giảm thời gian.
- Cache `ALLOW` theo model hoặc workflow chung.
- Async hóa capability, revocation, egress, path enforcement hoặc approval R2/R3.
- Retry click/submit khi timeout.
- Reuse browser profile giữa task.
- Cho phép subprocess tùy ý.
- Tăng concurrency trước khi đo queue và contention.
- Hạ R2/R3 thành R0 để đạt SLA.

## Mẫu báo cáo

```markdown
# SCP Safe Latency Review

## Baseline
| Span | p50 | p95 | p99 | Sample | Bottleneck? |
|---|---:|---:|---:|---:|---:|

## Workload and risk
[Task profile, R0–R3 mix, provider, sandbox profile]

## Optimization proposal
| Thay đổi | Lợi ích dự kiến | Safety impact | Rollback |
|---|---|---|---|

## Before/after
| Metric | Before | After | Đạt? |
|---|---:|---:|---:|

## Verdict
[ACCEPT / REJECT / NEED_MORE_DATA]
```

## Tiêu chí chấp nhận

Chỉ chấp nhận khi p95/p99 giảm với cùng workload, fast lane vẫn kiểm capability/epoch/scope/quota, strong lane không bypass approval, sandbox warm start sạch, kill/revoke trong ngân sách, audit replay được và không tăng unknown/duplicate/cleanup failure.

## Tài liệu SCP tham chiếu

Đọc khi cần `Tối ưu latency cho Policy Pipeline và Sandbox của SCP Agent OS.md`, `Phân tích điểm nghẽn trong sơ đồ quy trình.md` và `Blueprint SCP Agent OS.md`.
