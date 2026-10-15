---
name: typesafe-agent-eval
description: Sử dụng TypeSafe AI Evaluation API (noul/choice/score) trong quy trình làm việc của Antigravity Agent và Subagents để đánh giá typed diff, kế hoạch (plan), mức độ rủi ro, phân loại lỗi và kiểm chứng an toàn code độc lập. CHỈ dùng cho quy trình của Agent, KHÔNG thuộc runtime SCP.
---

# TypeSafe Agent Evaluation Skill

> **RANH GIỚI BẮT BUỘC (MANDATORY BOUNDARY)**
> - Công cụ này phục vụ **QUY TRÌNH LÀM VIỆC CỦA AGENT & SUBAGENT** (Planning, Code Review, Diff Verification, Subagent Judging).
> - **TUYỆT ĐỐI KHÔNG** biến TypeSafe thành runtime dependency của ứng dụng SCP. Code sản phẩm SCP không import `typesafe`.

---

## 1. Tổng Quan & Cấu Hình

TypeSafe AI (`api.typesafe.ai/v1/systemone`) là hệ thống đánh giá có cấu trúc (Typed Evaluation) sử dụng mô hình chuyên biệt `jev-latest`. Nó cung cấp các dạng câu hỏi định lượng chuẩn xác:
- **`noul`**: Đánh giá câu hỏi nhị phân thành xác suất từ `0.0` đến `1.0`.
- **`choice`**: Phân loại theo danh sách lựa chọn độc lập kèm phân phối xác suất và độ tự tin (`confidence`).
- **`score`**: Đánh giá theo thang đo thứ bậc có thứ tự (`level1|level2|...`).

### Nguồn API Key
CLI tự động đọc `TYPESAFE_API_KEY` từ file `.env` ở repo root (thư mục chứa `integrations/` — tuyệt đối không hardcode đường dẫn máy cá nhân) hoặc từ biến môi trường `TYPESAFE_API_KEY`. Key không bao giờ bị in ra log/stdout.

---

## 2. CLI Reference Dành Cho Agent

Script thực thi nằm tại: [`integrations/typesafe/typesafe_eval.py`](file:///D:/scp/integrations/typesafe/typesafe_eval.py)

```bash
python integrations/typesafe/typesafe_eval.py \
    [--file PATH | --state "NỘI DUNG"] \
    [--noul "NAME=CÂU_HỎI_XÁC_SUẤT"] \
    [--choice "NAME=opt1|opt2|opt3"] \
    [--score "NAME=level1|level2|level3"]
```

> [!IMPORTANT]
> **Quy tắc PowerShell trên Windows**: Khi chạy qua `run_command`, các tham số chứa ký tự `|` (như `--choice` hoặc `--score`) **BẮT BUỘC** phải được bọc trong dấu ngoặc kép `"..."`, nếu không PowerShell sẽ coi `|` là toán tử pipe và báo lỗi cú pháp.

---

## 3. Các Tình Huống Agent Phải Kích Hoạt TypeSafe

### A. Pre-execution Plan Gate (Duyệt Kế Hoạch Trước Khi Chạy)
Trước khi thực hiện các sửa đổi kiến trúc lớn hoặc refactor phức tạp:
```powershell
python integrations/typesafe/typesafe_eval.py `
    --file "C:\Users\check\.gemini\antigravity\brain\<conv_id>\implementation_plan.md" `
    --choice "risk_level=low|medium|high|critical" `
    --noul "safe_to_execute=Is this plan safe to execute without breaking existing test contracts?" `
    --score "plan_completeness=sketchy|partial|comprehensive|flawless"
```

### B. Pre-commit Diff Gate (Kiểm Tra Diff Trước Khi Commit)
Sau khi chỉnh sửa mã nguồn và trước khi chạy `git commit`:
```powershell
git diff > temp_diff.patch
python integrations/typesafe/typesafe_eval.py `
    --file temp_diff.patch `
    --choice "regression_risk=none|low|medium|high" `
    --noul "has_breaking_side_effects=Does this change introduce hidden breaking side effects?" `
    --noul "preserves_fail_closed=Does this diff uphold Fail-Closed and Evidence-First principles?"
Remove-Item temp_diff.patch
```

### C. Subagent Output Verification (Thẩm Định Kết Quả Của Subagent)
Khi Subagent hoàn thành một nhiệm vụ (ví dụ: DeepCoder vừa refactor xong), Agent Mẹ dùng TypeSafe như một **Third-party Judge độc lập** để đánh giá:
```powershell
python integrations/typesafe/typesafe_eval.py `
    --state "<Báo cáo tóm tắt hoặc diff của Subagent>" `
    --choice "verdict=approved|needs_revision|rejected" `
    --noul "is_placebo_free=Is this fix genuine rather than a cosmetic or placebo change?"
```

### D. Hypothesis Discrimination (Phân Biệt Giả Thuyết Khi Debug Lỗi Khó)
Khi hệ thống gặp lỗi khó tái lập và Agent có nhiều giả thuyết nguyên nhân gốc:
```powershell
python integrations/typesafe/typesafe_eval.py `
    --state "<Log lỗi + 3 giả thuyết H1, H2, H3>" `
    --choice "most_likely_root_cause=H1_RaceCondition|H2_PortConflict|H3_StateDrift"
```

---

## 4. Bảng Tiêu Chuẩn Phán Quyết (Evaluation Thresholds)

| Chỉ số TypeSafe | Ngưỡng Cho Phép | Hành Động Của Agent Nếu Không Đạt |
|---|---|---|
| `risk_level` | `low` hoặc `medium` | Nếu là `high` hoặc `critical`, dừng lại và thông báo cho người dùng xem xét. |
| `is_safe` / `safe_to_execute` | `noul >= 0.70` | Nếu `< 0.70`, rà soát lại các điểm có thể gây xung đột trước khi áp dụng. |
| `has_breaking_side_effects` | `noul <= 0.30` | Nếu `> 0.30`, kiểm tra lại các hàm gọi lân cận (FA-11). |
| `is_placebo_free` | `noul >= 0.80` | Nếu `< 0.80`, từ chối kết quả của Subagent và yêu cầu sửa lại. |

---

## 5. Tích Hợp Vào Prompt Của Subagent
Khi gọi `invoke_subagent`, Agent Mẹ bổ sung chỉ dẫn:
> "Sau khi hoàn thành diff, hãy tự kiểm chứng mã nguồn bằng cách chạy `python integrations/typesafe/typesafe_eval.py --file <patch_or_report>` với các tiêu chí an toàn trước khi báo cáo kết quả."
