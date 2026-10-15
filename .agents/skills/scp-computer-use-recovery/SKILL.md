---
name: scp-computer-use-recovery
description: Phục hồi task computer-use sau worker crash, timeout, mất response, browser chết, lease hết hạn hoặc capability bị revoke mà không lặp side effect. Use when an agent may have clicked, submitted, uploaded, sent, deleted, paid, published, or otherwise created an uncertain external effect.
---

# SCP Computer-Use Recovery

## Nguyên tắc cốt lõi

> **Mất response không đồng nghĩa với mất side effect.**

Dùng mô hình at-least-once execution kết hợp journal, checkpoint, lease fencing, idempotency và reconciliation. Không gọi retry side effect chỉ vì tool timeout.

## Phân loại risk

| Tier | Ví dụ | Tự resume? |
|---|---|---:|
| R0 | Đọc DOM, title, trạng thái, scroll | Có nếu state rõ |
| R1 | Ghi artifact workspace, draft chưa gửi | Có điều kiện |
| R2 | Submit, upload, gửi message, external write | Không mặc định |
| R3 | Credential, delete, payment, publish, đổi quyền | Không; human review |

Recovery không được hạ R2/R3 thành R0/R1 để chạy nhanh.

## Recovery workflow

1. Đóng băng side effect mới của task.
2. Thu hồi lease/attempt cũ; từ chối commit bằng `STALE_LEASE` nếu worker cũ quay lại.
3. Đọc checkpoint hợp lệ gần nhất và event journal sau checkpoint.
4. Phân loại điểm gián đoạn: trước proposal, sau policy, driver started, action dispatched, response lost, result recorded, verified hoặc committed.
5. Nếu chưa có bằng chứng action đã dispatch: tạo attempt mới từ checkpoint.
6. Nếu action có thể đã dispatch: chuyển `RECONCILING`; tuyệt đối không retry ngay.
7. Reconcile bằng provider request ID/idempotency query, read-only API, URL/title/DOM/accessibility, artifact hash hoặc network journal theo thứ tự tin cậy.
8. Phân loại kết quả `NOT_APPLIED`, `APPLIED`, `PARTIAL`, `CONFLICT`, `UNKNOWN`.
9. Chỉ resume khi risk thấp, checkpoint hợp lệ, capability/epoch còn hiệu lực, lease mới tồn tại, state sạch và không có dispatch chưa reconcile.
10. Nếu `UNKNOWN`, `CONFLICT`, R2/R3 hoặc thiếu evidence: chuyển `HUMAN_REVIEW`, không retry side effect.
11. Nếu đã có verifier verdict mà chưa commit: commit event idempotent, không chạy lại action.
12. Ghi recovery trace, nguyên nhân, phương pháp reconcile, kết quả và quyết định cuối.

## Các state cần nhận diện

`INTERRUPTED`, `RECOVERY_CLASSIFY`, `RECONCILING`, `RESUME_SAFE`, `UNKNOWN_SIDE_EFFECT`, `HUMAN_REVIEW`, `CANCELLED`, `FAILED` và lỗi `STALE_LEASE`.

## Idempotency

Dùng key theo logical action, không theo attempt:

```text
idempotency_key = hash(task_id, logical_step_id, action_type, resource_identity)
```

`attempt_id` có thể đổi sau recovery nhưng `idempotency_key` không đổi. Nếu provider không hỗ trợ idempotency, dùng read-before-write hoặc human review khi response mất.

## Decision object bắt buộc

```json
{
  "decision": "RECONCILE",
  "reason": "ACTION_DISPATCHED_WITHOUT_RESULT",
  "safe_to_retry": false,
  "required_evidence": ["provider_request_status", "read_only_state"],
  "next_state": "RECONCILING",
  "escalation": "human_review_if_unknown"
}
```

Không trả về boolean đơn giản cho recovery, vì dashboard, worker và audit cần dùng chung lý do và state tiếp theo.

## Invariant an toàn

- Một logical action không có hơn một committed external side effect.
- Worker không có lease hợp lệ không thể commit.
- Task ở `UNKNOWN_SIDE_EFFECT` không được dispatch side effect mới.
- Capability đã revoke không được dùng bởi attempt cũ.
- Checkpoint hash sai không được dùng để resume.
- `COMPLETED` luôn có verifier verdict và evidence reference.
- Kill switch chặn cả action đã cache `ALLOW`.
- Cleanup failure không trả cell bẩn về warm pool.
- Retry count bị giới hạn và không reset chỉ vì worker restart.

## Chaos tests tối thiểu

Kiểm tra kill worker trước proposal, sau policy, sau `ACTION_STARTED`, sau `ACTION_DISPATCHED`, sau result trước verifier, sau verifier trước commit, lease hết hạn với worker cũ quay lại, capability revoke giữa task, browser chết, dashboard chết, checkpoint bị sửa và egress proxy chết.

## Mẫu báo cáo recovery

```markdown
# Recovery Decision

| Trường | Giá trị |
|---|---|
| Task/attempt | |
| Risk tier | |
| Last checkpoint | |
| Last event | |
| Interruption reason | |
| Suspected side-effect boundary | |
| Reconciliation method | |
| Reconciliation result | |
| Final decision | |
| Safe to retry | |

## Bằng chứng
[Danh sách evidence reference, không nhúng secret]

## Lý do không retry mù
[Giải thích ngắn]
```

## Tài liệu SCP tham chiếu

Đọc khi cần `Failure Recovery cho Computer-Use Fast Lane.md`, `Blueprint SCP Agent OS.md` và `Lộ trình chuyển SCP từ Agent Control Plane thành Agent OS.md`.
