---
name: scp-release-evidence-gate
description: Review và kiểm tra release candidate của SCP bằng commit snapshot, service manifest, test runner, smoke test, golden task, chaos test, security gate, reproducibility và rollback evidence. Use when evaluating release readiness, before calling an SCP build stable, production candidate, Agent OS release, or after claiming that findings are fixed.
---

# SCP Release Evidence Gate

## Mục tiêu

Ngăn việc gọi một bản build là “ổn định” chỉ vì nhiều unit test PASS. Release phải có bằng chứng runtime, security, recovery và tái hiện được. Theo SCP DNA #22 và #26, PASS luôn bị giới hạn bởi scope/evidence và Reality giữ quyền cuối cùng.

## Quy trình gate

1. Xác định release ID, commit, branch, working-tree status và thời điểm.
2. Kiểm tra dependency lock, service manifest, launcher hash, test runner hash và cấu hình không chứa secret.
3. Chạy static gate: lint/type/import, schema/contract check và test collection.
4. Chạy runtime gate: clean start, readiness từng service, smoke task, clean stop.
5. Chạy golden task ít rủi ro: planner → policy → tool → observation → verifier → audit → artifact.
6. Chạy chaos gate: worker crash, provider timeout, dashboard down, lease expiry, checkpoint corruption, capability revoke và egress failure.
7. Chạy security gate: policy deny, path traversal, secret leakage, egress deny, prompt injection qua untrusted data và startup bypass flags.
8. Kiểm tra audit replay/dry-run và evidence provenance.
9. Kiểm tra rollback artifact, known limitations và hướng phục hồi.
10. Đánh verdict `PASS`, `CANDIDATE`, `BLOCKED` hoặc `FAIL`. Một gate thiếu evidence là `BLOCKED`, không tự coi là PASS.

## Skill + SCP DNA contract bắt buộc

- Mọi **mandatory release gate** phải có mapping máy-đọc được trong `.agents/skills/release-gate-skill-dna-bindings.json`.
- Mỗi gate phải bind `scp-dna` **và ít nhất một domain Skill** phù hợp với loại bằng chứng đang kiểm tra.
- Mỗi gate bắt buộc mang DNA #22 (`PASS ≠ TRUE`) và DNA #26 (`Reality có quyền cuối cùng`); domain gate bổ sung DNA tương ứng với rủi ro của nó.
- `tests/test_scp_skill_dna_contract.py` là fail-closed authority cho tính đầy đủ/hợp lệ của mapping. Thiếu Skill, sai Skill manifest, DNA ngoài #1..#29, thiếu gate, hoặc gate không có #22/#26 đều là **release blocker**.
- RC verdict và customer-handoff verdict phải ghi lại `skill_scp_dna_contract=PASS`; không được suy diễn PASS nếu contract này chưa chạy trên chính SHA đang xét.

## Các gate bắt buộc

| Gate | Evidence bắt buộc | Nếu thiếu |
|---|---|---|
| Config | Manifest, secret reference hợp lệ, không bypass flag | BLOCKED |
| Static | Lint/type/import và test contract | FAIL/BLOCKED |
| Runtime | Clean start/readiness/clean stop | BLOCKED |
| Golden task | Một task an toàn chạy end-to-end | BLOCKED |
| Chaos | Crash/timeout/unknown-state/recovery đúng | BLOCKED |
| Security | Deny, path, secret, egress và injection test | BLOCKED |
| Reproducibility | Commit, lockfile, snapshot, rollback | BLOCKED |

## Quy tắc claim

- `PASS` nghĩa là gate đã chạy trong phạm vi workload và evidence cụ thể.
- `CANDIDATE` nghĩa là có thành phần đạt nhưng còn giới hạn chưa chứng minh.
- `BLOCKED` nghĩa là chưa đủ evidence, không phải hệ thống chắc chắn hỏng.
- `FAIL` nghĩa là gate đã chạy và điều kiện bắt buộc không đạt.
- Không dùng câu “đã sửa hết” nếu không có test/evidence cho từng finding.
- Không ghi secret raw, token, cookie, password hoặc dữ liệu cá nhân vào report.

## Mẫu release record

```markdown
# SCP Release Evidence Gate

## Release identity
| Trường | Giá trị |
|---|---|
| Release ID | |
| Commit | |
| Git status | |
| Runtime versions | |
| Test profile | |

## Gate results
| Gate | Status | Command/profile | Skill/DNA binding | Evidence | Limitation |
|---|---|---|---|---|---|

## Known limitations
[Phần chưa được chứng minh hoặc chỉ mới static-test]

## Rollback
[Artifact, commit và thao tác rollback đã kiểm tra]

## Final verdict
[PASS / CANDIDATE / BLOCKED / FAIL]
```

## Điều kiện gọi là Agent OS release

Chỉ dùng nhãn Agent OS khi task kernel, durable state, lease fencing, capability, supervisor, verifier, recovery, observability, kill switch và golden task đều có evidence runtime phù hợp. Nếu còn phần chỉ có sơ đồ hoặc unit test, ghi `Agent Runtime candidate`.

## Tài liệu SCP tham chiếu

Đọc khi cần `Audit nhanh bộ tệp SCP trên máy tính đã kết nối.md`, `Lộ trình chuyển SCP từ Agent Control Plane thành Agent OS.md` và `Blueprint SCP Agent OS.md`.
