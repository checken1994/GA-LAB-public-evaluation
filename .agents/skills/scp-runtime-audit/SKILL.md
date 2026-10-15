---
name: scp-runtime-audit
description: Audit trạng thái vận hành của SCP bằng cách đối chiếu service, port, health, log, test runner, end-to-end proof, security guard và khả năng tái hiện release. Use when the user asks whether SCP is really running, requests a runtime audit, production-readiness review, evidence audit, or wants to distinguish test PASS from real system proof.
---

# SCP Runtime Audit

## Mục tiêu

Đánh giá SCP bằng **bằng chứng quan sát được**, không kết luận chỉ từ số module, README hoặc một con số test PASS. Phân biệt rõ ba mức: static assertion, integration proof và end-to-end runtime proof.

## Quy trình bắt buộc

1. Xác định thư mục, máy, thời điểm và snapshot đang kiểm tra. Đọc `AGENTS.md` gần nhất nếu có. Không đọc hoặc ghi secret.
2. Ghi `git rev-parse HEAD`, `git status --short`, phiên bản runtime, tên file cấu hình và hash của launcher/runner. Không đưa giá trị secret vào báo cáo.
3. Tạo service inventory gồm `service_name`, `host`, `configured_port`, `actual_port`, `health_url`, `pid`, `started_at`, `config_source` và `evidence_ref`.
4. Kiểm tra process và port thật. Không suy ra service đang sống chỉ vì log cũ hoặc process cha còn tồn tại.
5. Gọi health/readiness endpoint đúng service. Phân biệt `health` của module với `readiness` của toàn stack.
6. Đối chiếu port trong manifest, `.env`, launcher, log, dashboard proxy và runtime. Nếu lệch, ghi từng cặp lệch và tác động.
7. Kiểm tra test runner: test có được thu thập không, có lỗi encoding không, kết quả có lặp lại không, và test có khởi động service thật không.
8. Tìm bằng chứng cho một golden task: planner → policy → tool → observation → verifier → audit → artifact. Nếu không có, ghi `E2E_NOT_PROVEN`.
9. Kiểm tra các guard chính: deny-by-default, startup fail-closed, egress deny, secret redaction, kill switch và không auto-approve nguy hiểm.
10. Kiểm tra reproducibility: commit, lockfile, manifest, test profile, snapshot và rollback artifact.
11. Xếp hạng phát hiện theo `BLOCKER`, `HIGH`, `MEDIUM`, `LOW`. Mỗi phát hiện phải có quan sát, nguồn bằng chứng, tác động và cách xác minh.
12. Kết luận một trong bốn trạng thái: `NOT_RUNNING`, `PARTIALLY_RUNNING`, `CANDIDATE_NOT_PROVEN`, `RUNTIME_PROVEN`.

## Quy tắc không được vi phạm

- Không coi `73/73 PASS` hoặc một số PASS bất kỳ là bằng chứng end-to-end nếu runner không chứng minh điều đó.
- Không sửa file, restart service, kill process hoặc xóa log trong lúc audit nếu chưa lưu snapshot và được người dùng yêu cầu.
- Không biến suy đoán thành nguyên nhân chắc chắn. Dùng các nhãn `OBSERVED`, `SUPPORTED_INFERENCE`, `UNPROVEN`.
- Không kiểm tra bằng secret raw. Redact token, cookie, API key, `.env` value và dữ liệu cá nhân.
- Nếu dashboard chết, vẫn kiểm tra Kernel/API/journal độc lập; dashboard không phải source of truth.

## Mẫu báo cáo đầu ra

```markdown
# SCP Runtime Audit

## Kết luận điều hành
[1–2 đoạn: trạng thái hiện tại và giới hạn bằng chứng]

## Snapshot
| Trường | Giá trị |
|---|---|
| Commit | |
| Git status | |
| Thời điểm | |
| Test profile | |

## Service contract
| Service | Configured | Actual | Health/readiness | Trạng thái | Evidence |
|---|---:|---:|---|---|---|

## Test credibility
| Runner | Collected | Result | Runtime thật? | Đánh giá |
|---|---:|---:|---:|---|

## Phát hiện
| ID | Mức | Nhãn bằng chứng | Quan sát | Tác động | Việc cần kiểm tra |
|---|---|---|---|---|---|

## Proof matrix
| Năng lực | Đã chứng minh? | Bằng chứng | Khoảng trống |
|---|---:|---|---|

## Kết luận trạng thái
[NOT_RUNNING / PARTIALLY_RUNNING / CANDIDATE_NOT_PROVEN / RUNTIME_PROVEN]
```

## Tiêu chí `RUNTIME_PROVEN`

Chỉ dùng nhãn này khi service contract nhất quán, readiness thật đạt, test runner đáng tin, có ít nhất một golden task end-to-end, verifier có evidence thật, audit có trace và snapshot có thể tái hiện. Nếu thiếu một phần, dùng `CANDIDATE_NOT_PROVEN` và nói rõ thiếu gì.

## Tài liệu SCP tham chiếu

Đọc khi cần: `Audit nhanh bộ tệp SCP trên máy tính đã kết nối.md`, `Blueprint SCP Agent OS.md` và `Lộ trình chuyển SCP từ Agent Control Plane thành Agent OS.md` trong thư mục dự án SCP.
