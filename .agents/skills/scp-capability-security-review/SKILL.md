---
name: scp-capability-security-review
description: Review capability security, policy enforcement, sandbox, egress, filesystem scope, secret handling và approval của SCP agent/tool. Use when the user asks whether an agent has too much permission, whether a tool can escape its sandbox, whether a policy is safe, or requests a security review of computer-use actions.
---

# SCP Capability Security Review

## Mục tiêu

Kiểm tra quyền theo **task + attempt + resource + action**, không đánh giá bằng role rộng như `admin` hoặc `agent`. Mọi kết luận phải phân biệt policy decision, enforcement thực tế và bằng chứng runtime.

## Mô hình quyền tối thiểu

Mỗi capability cần có:

```text
capability_id
subject = task_id + attempt_id
single tool hoặc nhóm tool hẹp
resource = domain/path/window/process cụ thể
operation = read/write/submit/delete/spawn
max data class
side effect = none/local-write/external-write/destructive
expiry và max uses
approval ID nếu cần
revocation epoch
policy hash
```

## Quy trình review

1. Lập action inventory: tool, operation, resource, data class, side effect, actor và nơi thực thi.
2. Chuẩn hóa resource: domain, URL path, canonical file path, window session, process identity và network destination.
3. Xác định risk tier: R0 read-only, R1 local reversible, R2 external write, R3 credential/destructive/financial/privilege/production.
4. Kiểm tra deny-by-default: không có capability thì tool phải bị từ chối.
5. Kiểm tra cấp quyền theo task/attempt, không theo model hoặc workflow chung.
6. Kiểm tra capability ở ba thời điểm: lúc cấp, ngay trước gọi tool và lúc commit side effect.
7. Kiểm tra expiry, max uses, policy version, revocation epoch và kill switch invalidation.
8. Kiểm tra PEP nằm ngay trước driver; không chỉ tin PDP hoặc quyết định từ lúc lập kế hoạch.
9. Kiểm tra OS/runtime sandbox: user riêng, workspace riêng, process tree, resource quota, network proxy, egress allowlist và path enforcement.
10. Kiểm tra secret broker: không raw secret trong prompt, screenshot, stdout, log, exception, trace hoặc artifact.
11. Kiểm tra approval: submit, upload, delete, payment, credential, publish, đổi quyền và production change phải có policy riêng.
12. Kiểm tra untrusted data: web, DOM, file, email, repository, MCP response và tool output không được parse thành system instruction.
13. Xếp verdict `ALLOW`, `APPROVE`, `DENY` hoặc `UNKNOWN`. `UNKNOWN` phải dừng, không tự nâng thành `ALLOW`.

## Ma trận review nhanh

| Hành động | Verdict mặc định | Điều kiện |
|---|---|---|
| `browser.read` domain allowlist | ALLOW | Capability còn hạn, data class phù hợp |
| `file.write` trong workspace | ALLOW/APPROVE | Đúng path, đúng artifact scope |
| Submit form/upload/send | APPROVE | Approval theo action và evidence sau action |
| Delete/payment/credential/publish | APPROVE hoặc DENY | Human-controlled, strong sandbox |
| Đọc `.env`, cookie, SSH key, secret store | DENY | Không cấp qua prompt |
| Gọi domain ngoài allowlist | DENY | Egress proxy phải chặn |
| Model yêu cầu tự cấp thêm quyền | DENY | Ghi audit prompt-injection attempt |
| Thiếu context hoặc resource mơ hồ | UNKNOWN | Chuyển review |

## Các lỗi phải bắt

- Cache `ALLOW` theo model thay vì task/resource.
- Capability chung cho cả workflow.
- Tool wrapper an toàn nhưng subprocess/child process vượt quyền.
- Ghi ngoài workspace chỉ bị chặn ở application layer.
- Egress trực tiếp không qua proxy.
- Secret raw xuất hiện trong model context hoặc log.
- Approval chung cho mọi action.
- Policy cho phép dựa vào prompt thay vì token được cấp bởi policy engine.
- Browser profile/cookie/workspace reuse giữa task.
- Capability bị revoke nhưng action cache vẫn chạy.

## Mẫu báo cáo

```markdown
# SCP Capability Security Review

## Kết luận điều hành
[Phạm vi, verdict và giới hạn bằng chứng]

## Action matrix
| ID | Tool/operation | Resource | Risk | Capability | PEP | Approval | Verdict | Evidence |
|---|---|---|---|---|---|---|---|---|

## Sandbox checks
| Control | Kết quả | Bằng chứng | Khoảng trống |
|---|---|---|---|

## Secret and untrusted-data checks
[Không hiển thị secret raw]

## Findings
| ID | Severity | Vi phạm | Tác động | Cách khắc phục |
|---|---|---|---|---|

## Verdict
[ALLOW / APPROVE / DENY / UNKNOWN]
```

## Nguyên tắc an toàn

Không coi human approval là lớp bảo vệ duy nhất. Sandbox, policy bất biến, egress, filesystem và secret broker vẫn phải chặn đường nguy hiểm khi người dùng approve nhầm. Không mở rộng capability chỉ vì model nói rằng cần quyền đó.

## Tài liệu SCP tham chiếu

Đọc khi cần `Blueprint SCP Agent OS.md`, `Lộ trình chuyển SCP từ Agent Control Plane thành Agent OS.md` và `Tối ưu latency cho Policy Pipeline và Sandbox của SCP Agent OS.md`.
