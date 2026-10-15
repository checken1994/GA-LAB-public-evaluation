# SCP Execution Protocol

> **Quy trình bắt buộc cho MỌI AI agent trước khi sửa code SCP.**
> File này được tự động nạp bởi các AI coding surface (Antigravity, ChatGPT, Codex, etc.)
> thông qua cơ chế `.agents/` directory loading.

---

## Phase 0: Reconcile (BẮT BUỘC — trước khi sửa bất kỳ file nào)

1. Đọc `GA.md` trên `main` — xác định trạng thái hiện tại và handoff notes.
2. Đọc chain audit gần nhất trong `reports/audit/audit-*.json` (sinh bởi `scripts/run_full_audit.py`) — xác định các gap ưu tiên còn mở; đối chiếu blockers hiện hành trong `GA.md` (CURRENT HANDOFF).
3. Xác định exact HEAD SHA: `git rev-parse HEAD`.
4. So sánh HEAD với baseline snapshot nếu cần: `git diff <baseline>..HEAD --stat`.
5. Tạo candidate branch nếu cần, hoặc xác nhận branch hiện tại.
6. **Báo cáo SHA cho user** và chờ xác nhận trước khi tiếp tục.
7. **KHÔNG mutation bất kỳ file nào trước khi Phase 0 hoàn tất.**

---

## Phase 1: Implement (CHỈ sau khi user duyệt)

1. Chỉ sửa files nằm trong scope được giao cho Wave/Agent hiện tại.
2. Mỗi thay đổi phải là **small reversible patch**.
3. **Nêu rõ exact files dự định sửa** trước khi bắt đầu.
4. Refresh branch HEAD trước mỗi mutation: `git pull --rebase origin main`.
5. Chạy scoped tests **SAU MỖI thay đổi** — không gom nhiều thay đổi rồi test một lần.
6. Nếu test đỏ → phân loại (HARNESS_BROKEN, PRODUCT_FAIL, PRODUCT_BLOCKED). Sửa harness phải giữ hoặc tăng strictness. Không được loosen assertion (FA-01).

---

## Phase 1.1: Architectural Deprecation Protocol (BẮT BUỘC khi xóa tính năng / Invariant)

Khi được yêu cầu xóa hoặc phế truất một thành phần cốt lõi, policy, hoặc invariant, Agent TUYỆT ĐỐI KHÔNG thực hiện "Bottom-Up Deletion" (chỉ xóa code và làm rỗng test). BẮT BUỘC tuân thủ 5 tầng Top-Down:

1. **Tầng 1 — Authority & Spec First:**
   - Cập nhật `spec/protected_invariants.yaml`, `spec/complete_scp_reference.yaml`, và `GA.md` TRƯỚC TIÊN.
   - Đảm bảo "luật" của hệ thống không còn bắt buộc invariant đó trước khi chạm vào implementation.

2. **Tầng 2 — Call-Graph & Symbol Elimination:**
   - Dùng `grep -rn` quét toàn bộ codebase (`scp/`, `tests/`, `scripts/`, `spec/`).
   - Xóa bỏ triệt để mọi class instantiation, import chết, caller function, và background worker liên quan. Cấm để lại dangling symbol.

3. **Tầng 3 — Semantic Test Rewriting (Bảo toàn FA-01 và FA-02):**
   - **Giữ nguyên 100% NodeID** (tên file và tên hàm test) để T00 Meta-Audit không báo lỗi xóa test (FA-02).
   - **CẤM Placebo Assertion:** Tuyệt đối không thay ruột test thành các câu lệnh rỗng như `assert not hasattr(module, "deleted_class")`.
   - **Viết lại Semantic Assertions:** Viết lại thân hàm test để assert **hành vi kiến trúc thay thế** (ví dụ: request đi thẳng qua Egress, fallback cascade khi không có cost wall, hoặc routing bỏ qua model không hợp lệ). Test phải thực sự chạy qua luồng logic mới.

4. **Tầng 4 — Đồng bộ Contract / Schema Tests:**
   - Cập nhật các test đọc metadata/capabilities YAML để assert sự vắng mặt hoặc schema mới của capability đã xóa.

5. **Tầng 5 — Hermetic Test Isolation:**
   - Tuyệt đối không gán `os.environ[...] = ...` trong fixture/test. Luôn sử dụng `monkeypatch.setenv` để tự động phục hồi môi trường sau test.

---

## Phase 2: Evidence (BẮT BUỘC — trước khi claim Done/Fixed/Pass)

1. Chạy **toàn bộ** test suite: `python -m pytest tests/ -v`.
2. **Paste terminal output thực tế** — không tóm tắt, không claim bằng lời.
3. Ghi exact SHA vào evidence: `git rev-parse HEAD`.
4. Nếu có test fail → phân loại:
   - `HARNESS_BROKEN` — test harness lỗi, cần sửa harness (giữ hoặc tăng strictness).
   - `PRODUCT_BLOCKED` — implementation thiếu, cần implement.
   - `PRODUCT_FAIL` — product lỗi, cần sửa product.
   - `STRUCTURAL_COVERAGE_GAP` — test coverage chưa đủ.
   - `BLOCKED` — phụ thuộc vào Wave/Agent khác.
5. Liệt kê **limitations và unresolved blockers** — không tự tuyên maturity.

---

## Phase 3: Handoff (SAU KHI evidence đầy đủ)

1. Cập nhật `GA.md` trên `main` với trạng thái mới.
2. Commit với message chuẩn: `fix(scope): mô tả ngắn gọn`.
3. **Chờ user review** trước khi mở Wave tiếp theo.
4. Không tự quyết định push — hỏi user.

---

## Wave Gate Rules (Kế hoạch GPT SOL 5.6)

### Thứ tự bắt buộc:
```
S0 (Baseline Reconcile)
  ↓
P0-A (A1 Epistemic, A2 Capability, A3 Recovery, A4 ZeroCost) — song song
  ↓
P0-B (B1 AutoFix Reality) — phụ thuộc A1
  ↓
P0 Integration Gate — kiểm tra toàn bộ P0
  ↓
P1-A/B/C/D — song song sau P0
  ↓
P2, P3, P4, P5 — tuần tự
```

### Không được song song:
- Hai agent sửa cùng authority file.
- AutoFix Reality trước khi EpistemicBoundary contract được khóa.
- Integration/release trong khi agent khác còn mutation production tree.
- Final auditor đồng thời là agent vừa sửa code.

### Mỗi agent phải:
1. Nhận dependency cone nhỏ.
2. Nêu exact files dự định sửa.
3. Refresh branch HEAD trước mutation.
4. Tạo small reversible patch.
5. Chạy scoped tests.
6. Lưu evidence.
7. Không tự tuyên maturity.
8. Trả lại: commit SHA + tests + limitations + unresolved blockers.

---

## Enforcement

Các quy tắc trên được enforce bởi:
- **Tier 1:** `tools/install_git_hooks.py` (pre-commit hook) -> `tools/t00_meta_audit.py`
- **Tier 2:** File này + `.agents/AGENTS.md` § FORBIDDEN ACTIONS (auto-loaded)
- **Tier 3:** `.github/workflows/scp_guardrails.yml` (CI — độc lập khỏi AI)
