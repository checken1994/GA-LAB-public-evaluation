# HỒ SƠ PHÂN CÔNG ĐA AGENT — SCP Audit+Fix Campaign (Vòng 3)

> Coordinator: AutoCoder (OpenClaw). Mọi Agent LÀM VIỆC TRONG `D:\scp`.
> Thời điểm phân công: 2026-09-29 (HEAD ban đầu: 77d44816).

## QUY TẮC BẮT BUỘC (mọi Agent)

1. **Skill SCP bắt buộc**: Trước khi audit/fix, ĐỌC file SKILL.md của vùng mình theo bảng dưới + `.agents/skills/scp-dna/SKILL.md` (DNA 29 nguyên tắc bắt buộc cho mọi audit — FA-13/AGENTS.md). Ghi vào báo cáo: đã đọc skill nào (path).
2. **Cấm**: delete/skip/xfail test, hạ assertion/threshold, đổi fail-closed→fail-open, sửa `spec/`, commit, push, đụng `.env`/secrets, kill service thật của owner (8000/8081/3030/3000 đang chạy là service E2E — chỉ đo, không phá).
3. **Sửa code**: vá nhỏ, có rollback, kèm regression test chứng minh old-code-fail/new-code-pass khi sửa product code.
4. **Nộp kết quả**: ghi file markdown `D:\scp\.openclaw\multi-agent\<Tên>.md` theo mẫu cuối file này. KHÔNG commit — Coordinator review rồi commit hợp nhất.
5. **Báo cáo trung thực tuyệt đối**: phân biệt OBSERVED / SUPPORTED_INFERENCE / UNPROVEN; PASS chỉ có nghĩa "không thấy lỗi trong phạm vi đã chạy".

## PHÂN CÔNG

### Agent 1 — "Security Guard"
- **Skill bắt buộc**: `.agents/skills/scp-capability-security-review/SKILL.md`
- **Phạm vi file**: `scp/security/`, `scp/capabilities/`, `scp/policy/`
- **Nhiệm vụ**: audit quyền/capability/egress/policy fail-closed; tìm mọi nhánh fail-open mới; kiểm tra secret không lộ trong log/argv. Tìm thấy lỗi → vá + regression test.
- **Kiểm chứng**: chạy test liên quan trong `tests/T03_capability/` (nếu có thay đổi code).

### Agent 2 — "Kernel Keeper"
- **Skill bắt buộc**: `.agents/skills/scp-task-kernel-review/SKILL.md`
- **Phạm vi file**: `scp/task_kernel*.py`, `scp/kernel_storage*.py`, `scp/task_kernel_parts/`, `scp/ask_kernel_adapter.py`
- **Nhiệm vụ**: audit state machine, lease, journal hash-chain, backpressure, recovery. Đặc biệt rà xung đột semantics sau fix `in_flight_count` @ 77d44816. Tìm thấy lỗi → vá + regression test.
- **Kiểm chứng**: `python -m pytest tests/T04_kernel -q`.

### Agent 3 — "Gateway Sentinel"
- **Skill bắt buộc**: `.agents/skills/scp-gateway-resilience/SKILL.md`
- **Phạm vi file**: `scp/llm_gateway/`, `scp/api/routes/`, `scp/api_server*.py`, `mini-services/llm-bridge/` (chỉ audit; sửa TS phải chạy `bun run build` chứng minh)
- **Nhiệm vụ**: audit timeout/circuit breaker/fallback/dead-model breaker, auth route, rate limit. Tìm thấy lỗi → vá + regression test.
- **Kiểm chứng**: `python -m pytest tests/T05_gateway -q`.

### Agent 4 — "Data Steward"
- **Skill bắt buộc**: `.agents/skills/scp-learning-loop-guard/SKILL.md`
- **Phạm vi file**: `scp/persistence/`, `scp/knowledge/`, `scp/trace_ledger.py`, `scp/core/trace_store.py`, `scp/core/request_run_ledger.py`, `scp/data_sources/`
- **Nhiệm vụ**: audit persistence integrity (lock, WAL, hash chain, path resolution — đặc biệt vùng vừa fix @ 5ca303e5). Tìm thấy lỗi → vá + regression test.
- **Kiểm chứng**: `python -m pytest tests/T02_contract tests/T07_learning -q`.

### Agent 5 — "Delta Auditor" (không sửa — chỉ audit độc lập vùng 1-4)
- **Skill bắt buộc**: `.agents/skills/scp-delta-audit/SKILL.md` (+ `scp-reality-verifier` khi cần chất vấn claim)
- **Phạm vi**: nhảy ngẫu nhiên ≥20 file trong phạm vi 4 Agent trên + toàn bộ report `.openclaw/multi-agent/Agent1-4`
- **Nhiệm vụ**: chất vấn mỗi fix đã nêu: test có thật không, assertion có mạnh không, có hạ chuẩn ngầm không; probe FA-09 với mọi claim "đã fix". Ghi VERDICT per finding: CONFIRMED_OK / REGRESSION_RISK / FAKE_OR_WEAKENED.

## MẪU BÁO CÁO (mỗi Agent ghi vào file .md của mình)

```markdown
# Báo cáo <Tên Agent> — SCP Audit Vòng 3
- HEAD khi bắt đầu: <sha>
- Skill đã đọc: <đường dẫn SKILL.md>
- Phạm vi đã audit: <số file / danh sách>
- Findings: mỗi mục [OBSERVED|SUPPORTED_INFERENCE|UNPROVEN] + file:line + bằng chứng + mức (BLOCKER/HIGH/MEDIUM/LOW)
- Đã fix: mô tả + file + regression test + lệnh verify + exit status
- Đã verify: lệnh chạy thật + output trích dẫn
- Chưa xử lý / open questions: ...
```

## TIẾN ĐỘ

| Agent | Trạng thái | Báo cáo |
|---|---|---|
| Agent 1 Security Guard | HOÀN THÀNH (R2) — F1 [MEDIUM] egress numeric-spelling bypass ĐÃ VÁ @ 1def66c1 + probe a028ef69; 26 file audit + AST sweep 46 file; verify per-file 113 passed; 6 LOW documented; F8 UNPROVEN liệt kê 12 file chưa đọc đủ | .openclaw/multi-agent/Agent1-Security-Guard.md |
| Agent 2 Kernel Keeper | HOÀN THÀNH (2 lượt) — oracle A12 fix @ d30aa307; F4 [HIGH] transition-map authority ĐÃ VÁ @ f370c0ff (commit_failed/set_task_kill không còn journal edge ngoài ALLOWED_TRANSITIONS); verify T04 332 passed/23 skipped; 4 open questions documented (rebuild_projection hardening, telemetry 0.8*cap, WAITING_APPROVAL dual-source, backlog 199 task cần human review) | .openclaw/multi-agent/Agent2-Kernel-Keeper.md |
| Agent 3 Gateway Sentinel | HOÀN THÀNH (part) — 2 test gateway committed @ 0d61f32c (additive pins cho hành vi F-05 đã commit); audit websockets hub chưa hoàn tất (hết ngân sách) — chuyển vào scope Agent 5 | .openclaw/multi-agent/Agent3-Gateway-Sentinel.md |
| Agent 4 Data Steward | R2 TIMEOUT @15m (run bị watchdog kết thúc giữa chừng) — toàn bộ finding cốt lõi đã được Coordinator giữ lại & fix trước đó: F1 [HIGH] split-brain ledger writer/reader ĐÁ VÁ @ ff5ef4f1; [HIGH-DoS] bounded trace GET @ d2f515ef + test b1144dfb (production ledger ~110MB O(file) đọc cả file mỗi GET); trace_ledger lock/chain PASS; db.py PASS | .openclaw/multi-agent/Agent4-Data-Steward.md |
| Agent 5 Delta Auditor | PENDING (chạy sau 1-4) | .openclaw/multi-agent/Agent5-Delta-Auditor.md |
