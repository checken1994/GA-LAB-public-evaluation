---
name: scp-task-kernel-review
description: Review kiến trúc và bằng chứng của SCP Task Kernel gồm state machine, event journal, queue, lease, checkpoint, idempotency, verifier, recovery, observability và kill switch. Use when the user asks whether SCP is becoming an Agent OS, requests a kernel architecture review, or wants to verify durable state and worker lifecycle.
---

# SCP Task Kernel Review

## Mục tiêu

Xác định Task Kernel có thật sự là source of truth cho lifecycle hay chỉ là một tập module rời. Review theo hợp đồng, transition và test runtime; không đánh giá bằng số file hoặc sơ đồ đẹp.

## Các năng lực phải kiểm tra

| Năng lực | Điều phải chứng minh |
|---|---|
| Task identity | Mỗi task có ID, owner, deadline, version và risk profile |
| State machine | Transition hợp lệ, có precondition/postcondition, không module tự set state |
| Event journal | Append-only, sequence tăng, hash chain, idempotent event ID |
| Projection | Có thể rebuild từ journal; journal thắng projection |
| Lease | TTL, heartbeat, fencing; worker cũ bị từ chối bằng `STALE_LEASE` |
| Queue/resource | Priority, fairness, quota, deadline và resource claim đo được |
| Checkpoint | Hash/reference, trước và sau side-effect boundary, không chứa secret |
| Idempotency | Logical action key ổn định qua các attempt |
| Verifier | Độc lập với planner/model, kiểm evidence và postcondition |
| Recovery | Phân biệt retryable, unknown-state, policy-denied, human-required |
| Kill switch | Task/cell/global kill độc lập với dashboard |
| Observability | Trace từ request → task → attempt → lease → tool → evidence → event |

## Quy trình review

1. Thu schema task, state enum, transition map, event schema, lease protocol, checkpoint schema và test list.
2. Vẽ lifecycle thực tế từ `CREATED` đến `COMPLETED`, `FAILED`, `CANCELLED`, `UNKNOWN` và `RECOVERING`.
3. So sánh transition trong code với transition được tài liệu hóa. Đánh dấu transition tự do hoặc thiếu guard.
4. Kiểm tra event journal có phải immutable source of truth không; thử logic rebuild projection.
5. Kiểm tra lease claim, heartbeat, expiry, fencing và commit rejection của worker cũ.
6. Kiểm tra checkpoint tại ranh giới side effect, hash validation, secret exclusion và resume rule.
7. Kiểm tra timeout/retry/unknown-state có nhánh riêng không. Không chấp nhận `retry_everything()`.
8. Kiểm tra verifier có dùng evidence/postcondition không, hay chỉ tin model nói “đã xong”.
9. Kiểm tra kill switch khi dashboard, provider hoặc projection chết.
10. Đối chiếu acceptance tests với integration/chaos tests thật. Unit test đơn lẻ không đủ để gọi là Agent OS.
11. Xếp kết luận `KERNEL_PROVEN`, `KERNEL_PARTIAL`, `ORCHESTRATOR_ONLY` hoặc `UNPROVEN`.

## State machine tối thiểu

```text
CREATED → PLANNING → READY → QUEUED → LEASED → RUNNING
RUNNING → WAITING_TOOL → VERIFYING → COMPLETED
RUNNING/WAITING_TOOL → RECOVERING/UNKNOWN/HUMAN_REVIEW/FAILED/CANCELLED
RECOVERING → CHECKPOINTED/QUEUED/HUMAN_REVIEW/FAILED
```

State cuối `COMPLETED`, `FAILED`, `CANCELLED` không được tự quay lại state chạy. `UNKNOWN` không được dispatch side effect mới.

## Acceptance tests tối thiểu

| Test | Kết quả bắt buộc |
|---|---|
| Hai worker claim một task | Chỉ một lease hợp lệ |
| Heartbeat mất | Lease hết hạn, task vào recovery |
| Worker cũ commit | Bị từ chối `STALE_LEASE` |
| Event gửi lại | Không duplicate event |
| Projection bị xóa | Rebuild đúng từ journal |
| Worker chết trước tool | Resume an toàn |
| Worker chết sau submit | `UNKNOWN` hoặc reconcile, không retry mù |
| Global kill | Không commit action mới |
| Dashboard tắt | Kernel/audit vẫn sống |
| Checkpoint hash sai | Không resume |

## Mẫu báo cáo

```markdown
# SCP Task Kernel Review

## Kết luận điều hành
[Kernel đã chứng minh đến đâu và vì sao]

## Contract matrix
| Thành phần | Có contract? | Đã test runtime? | Khoảng trống |
|---|---:|---:|---|

## State transition review
| Transition | Guard | Evidence | Verdict |
|---|---|---|---|

## Failure and recovery review
[Phân loại lỗi, retry, reconcile, human review]

## Acceptance matrix
| Test | Unit | Integration | Chaos | Kết quả |
|---|---:|---:|---:|---|

## Kết luận
[KERNEL_PROVEN / KERNEL_PARTIAL / ORCHESTRATOR_ONLY / UNPROVEN]
```

## Cảnh báo

Không gọi SCP là Agent OS chỉ vì có scheduler, dashboard, planner hoặc nhiều agent. Agent OS phải chứng minh durable state, lease fencing, capability, recovery, verifier, audit replay và kill switch bằng process thật.

## Tài liệu SCP tham chiếu

Đọc khi cần `Blueprint SCP Agent OS.md`, `Lộ trình chuyển SCP từ Agent Control Plane thành Agent OS.md` và `Failure Recovery cho Computer-Use Fast Lane.md`.
