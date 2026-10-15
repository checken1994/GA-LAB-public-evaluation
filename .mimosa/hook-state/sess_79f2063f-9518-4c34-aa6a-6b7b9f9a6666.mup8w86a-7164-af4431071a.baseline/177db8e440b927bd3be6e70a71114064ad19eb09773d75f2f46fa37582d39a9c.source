# SCP Agent Instructions & System Skills Directives

> **QUY TẮC BẮT BUỘC TRƯỚC MỌI PHIÊN LÀM VIỆC (PRE-SESSION MANDATE)**
> Trước khi bắt đầu bất kỳ tác vụ nào trong workspace này, Agent **BẮT BUỘC** thực hiện theo thứ tự sau bằng cách gọi tool thực tế (KHÔNG dùng training memory thay thế):
> 1. **Tải `GA.md`** (gọi `view_file` trên nhánh `main`) → lấy live project state, current blockers, và next task.
> 2. **Tải `.agents/AGENTS.md`** (gọi `view_file`) → nạp đầy đủ FA-01 đến FA-13 vào context. `GEMINI.md` auto-load nhưng chỉ chứa tóm tắt — AGENTS.md mới là nguồn đầy đủ.
> 3. **Tải Skill tương ứng** (gọi `view_file` vào `.agents/skills/<tên-skill>/SKILL.md`) → kích hoạt skill phù hợp với task.
> **"Tải" = gọi tool `view_file` thực tế. Dùng training memory thay thế = Vi phạm Pre-session Mandate.**

---

## 1. Bộ Kỹ Năng SCP Cốt Lõi (SCP Skills Pack)

Toàn bộ các kỹ năng SCP được quản lý và version-control tại `.agents/skills/`.

| Kỹ năng (Skill) | Mục đích & Trọng tâm |
|---|---|
| **`scp-dna`** | Áp dụng 29 nguyên lý DNA: *Thực tế > Mô hình*, *PASS ≠ TRUE*, *Ảo giác đồng thuận*, *Tìm mảnh ghép còn thiếu (missing piece)*, *Fail-Closed*. |
| **`scp-reality-verifier`** | Tiêu chuẩn hóa 4 cấp độ bằng chứng (*Static → Integration → End-to-end → Recovery*). Bắt buộc chạy kiểm thử thực tế trước khi xác nhận sửa lỗi. |
| **`scp-runtime-audit`** | Kiểm toán trạng thái tiến trình thực tế, cổng dịch vụ, health probe và nhật ký hệ thống. |
| **`scp-task-kernel-review`** | Kiểm tra tính bất biến của State Machine trong Task Kernel (15 trạng thái hợp lệ, khóa chuyển đổi nguyên tử). |
| **`scp-capability-security-review`** | Phân quyền bảo mật theo tác vụ, bảo vệ chống bypass, injection và leo thang đặc quyền. |
| **`scp-release-evidence-gate`** | Tiêu chuẩn bằng chứng phát hành: không tuyên bố "hoàn hảo" khi chưa có kết quả kiểm thử tái lập độc lập. |
| **`scp-startup-troubleshooter`** | Xử lý lỗi khởi động, phát hiện xung đột cổng và bất đồng bộ biến môi trường. |
| **`scp-safe-latency-optimizer`** | Tối ưu hóa độ trễ mà không làm suy yếu các cổng an toàn hoặc cơ chế khôi phục. |
| **`scp-computer-use-recovery`** | Cơ chế phục hồi khi tác vụ ngoại vi, browser hoặc worker bị ngắt quãng giữa chừng. |
| **`scp-gateway-resilience`** | Kiểm soát LLM Gateway, Circuit Breakers, Model Fallback Cascade, và API rate limits — độ trễ và độ bền của tầng LLM outbound. |
| **`scp-learning-loop-guard`** | Kiểm soát vòng lặp học liên tục, Knowledge Warehouse, Deep Scraper, và Autofix engine — chống Knowledge Poisoning và Catastrophic Forgetting. |
| **`scp-web-orchestration-safety`** | Kiểm soát browser sessions, DOM manipulation, CDP protocol, và anti-honeypot tactics — chống bẫy thực thi trên web.. |
| **`scp-skill-review`** | Chuẩn audit bộ skill: index nhất quán, bằng chứng, calibration, và định xem skill nào đáng tin làm chuẩn sửa chính SCP. |
| **`typesafe-agent-eval`** | Đánh giá typed AI (noul/choice/score) cho quy trình Agent & Subagents: rà soát diff, duyệt plan, phân loại rủi ro và thẩm định độc lập. (Workflow only, không thuộc SCP runtime). |

---

## 2. Nguyên Tắc Vận Hành Bất Biến (Non-Negotiable Rules)

1. **Reality > Model (Thực tế > Mô hình):** Không tin vào suy đoán hay ảo giác của AI. Luôn xác minh bằng mã thực thi, AST và log thực tế trước khi kết luận hoặc xóa code.
2. **Fail-Closed by Default:** Khi thiếu context hoặc không chắc chắn về độ an toàn, hệ thống phải từ chối hoặc chuyển sang trạng thái `UNKNOWN`/`HUMAN_REVIEW`, tuyệt đối không tự bịa đặt câu trả lời.
3. **Zero Hardcoded Paths:** Tất cả các đường dẫn trong codebase phải giải quyết động (`Path(__file__).resolve().parent...`), nghiêm cấm hardcode đường dẫn người dùng cá nhân.
4. **Clean Workspace:** Tuyệt đối không để lại file rác, file debug tạm bợ tại thư mục gốc. Mọi kiểm thử phải có đường dẫn dọn dẹp hoặc nằm trong vùng `.gitignore`.
5. **Continuous Verification:** Sau mỗi chỉnh sửa code, bắt buộc chạy `run_reality_tests_portable.py` và pytest theo **tập test hiện hành được phát hiện từ source/runner**, không hard-code số lượng test. Không làm xanh test bằng delete/skip/xfail/hạ chuẩn; sửa đúng PRODUCT/HARNESS tại điểm lỗi.
6. **API-First Orchestration:** SCP là một Agent OS sinh ra để điều phối API ngoại vi thông qua Gateway. TUYỆT ĐỐI KHÔNG đề xuất cài đặt hoặc chạy các Local Inference Engine (như Ollama, vLLM) cho các tác vụ suy luận cốt lõi để bảo vệ ranh giới kiến trúc.
7. **Distributed Autonomy (Tự chủ phân tán):** Khi thiết kế hoặc audit SCP, khái niệm "External Reviewer" (Người đánh giá bên ngoài) phải được hiểu là một Subsystem độc lập (Ví dụ: Agent A kiểm duyệt Agent B), chứ không phải tạo Nút thắt cổ chai bằng cách đẩy cho Con người.
8. **Language & Identifiers:** Làm việc bằng tiếng Việt; giữ nguyên identifier kỹ thuật tiếng Anh khi cần.
9. **GA.md & Live Truth:** Trước mọi task phải đọc `GA.md` trên `main`. Sau đó refresh GitHub live, đọc DNA/Skills/authority mà `GA.md` yêu cầu. `Live repo + Reality/evidence > memory/chat history`. Không dùng hoặc lưu làm authority các trạng thái dễ lỗi thời như SHA, số test, blocker, branch state, roadmap hay next task.
10. **Session Lifecycle & Handoff:** 1 task SCP lớn = 1 session/chat riêng; cùng root cause thì tiếp tục cùng session. Cuối task lớn: cập nhật handoff trong `GA.md` trên `main` rồi mới chuyển session.

---

## 3. FORBIDDEN ACTIONS — Machine-Enforceable (Vi phạm = Blocker tuyệt đối)

Xem chi tiết đầy đủ tại `.agents/AGENTS.md` § 3.

Tóm tắt FA-01 đến FA-13:
- **FA-01:** Không loosen test. Test đỏ phải classify. HARNESS_BROKEN → sửa harness nhưng prove strictness preserved/increased. PRODUCT_FAIL → sửa product. PRODUCT_BLOCKED → không manufacture green.
- **FA-02:** KHÔNG delete/skip/xfail test.
- **FA-03:** KHÔNG claim Done/Pass khi chưa có full `pytest tests/` terminal output.
- **FA-04:** KHÔNG tạo simulated/manufactured VERIFIED.
- **FA-05:** KHÔNG self-grant authority.
- **FA-06:** KHÔNG sửa code trước baseline reconcile.
- **FA-07:** KHÔNG claim maturity từ code/test presence.
- **FA-08:** KHÔNG tự tạo bằng chứng (cấm giả lập file log).
- **FA-09:** CẤM claim lỗ hổng (logic/security) khi chưa có script reproduce chạy văng lỗi thật trên terminal.
- **FA-10:** CẤM giả định trạng thái code giữa các workspace/clone khác nhau (phải hash/diff trước).
- **FA-11:** CẤM LÀM NGƠ LỖ HỔNG LÂN CẬN (No Blind Eye). Khi sửa file, BẮT BUỘC rà soát logic bảo mật ngoại vi. Nếu phát hiện GAP mới: (1) Cấm lén lút sửa (Scope Creep). (2) Phải tạo Artifact báo cáo Sơ đồ Nhân quả. (3) Bắt buộc Halt & Escalate nếu lỗ hổng mới làm tác vụ hiện tại trở nên vô nghĩa.
- **FA-12:** NGHIỆM THU NHÂN QUẢ THỰC TẾ (End-to-End Empirical Closure). Cấm tuyên bố FIXED chỉ nhờ Unit Test. Bắt buộc: (1) Vẽ Causal Graph toàn bộ file. (2) Quét lỗi ẩn. (3) Chạy thực tế trên PC. (4) Đọc/phân tích DB/Log vật lý. (5) Chứng minh End-to-End luồng fix ĐÃ ĐƯỢC GỌI.
- **FA-13:** TEST TỪ NHÂN QUẢ (Causal-Driven Test Generation). Sau khi vẽ Causal Graph (FA-12 bước 1), BẮT BUỘC tạo Coverage Matrix: mỗi nhánh nhân quả phải có ít nhất 1 test. Nhánh thiếu test → viết test mới HOẶC ghi nhận `UNPROVEN_BRANCH` và báo Orchestrator. Không được tuyên bố FIXED khi còn nhánh chưa phủ test chưa được duyệt.

Enforcement: `tools/t00_meta_audit.py` (pre-commit hook) + `.github/workflows/scp_guardrails.yml` (CI).

Quy trình thực thi: `.agents/EXECUTION_PROTOCOL.md`.

---

## 4. CƠ CHẾ CƯỠNG CHẾ BỘ NHỚ (AGENT-LEVEL HARD CONSTRAINTS)

Để chống lại tình trạng Agent "Có Skill nhưng lười không dùng" và "Giao quyền quá mức cho Subagent", các cơ chế sau đây mang tính Ràng buộc Tuyệt đối:

1. **Forced Skill Activation (Chống ảo giác đồng thuận):**
   Agent Mẹ KHÔNG ĐƯỢC PHÉP chỉ dựa vào tóm tắt (summary) của Skill trên bề mặt. Trước khi phân tích mã nguồn hoặc đưa ra bất kỳ phán quyết nào, Agent BẮT BUỘC phải dùng tool `view_file` đọc trực tiếp file `SKILL.md` tương ứng tại `.agents/skills/<tên-skill>/SKILL.md`. Báo cáo kết quả mà thiếu bước gọi tool đọc file Skill = Vi phạm nghiêm trọng (Báo cáo vô hiệu).

2. **Subagent Prompt Injection (Trói buộc Đệ - Chống F01/F02 tái phát):**
   Khi dùng tool `invoke_subagent`, Agent Mẹ TUYỆT ĐỐI KHÔNG ĐƯỢC giao Prompt mở. Trong trường `Prompt` truyền cho Subagent, BẮT BUỘC phải nhúng kèm đoạn lệnh cưỡng chế sau (hoặc tương đương):
   > "MANDATORY BINDING: You are strictly bound by Zero-Trust and Fail-Closed principles. You MUST adhere to FA-01 through FA-13. You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables."

3. **Call Graph Navigation (Chống ngợp dữ liệu):**
   Khi thực hiện kiểm toán hoặc phân tích mã nguồn phức tạp, Agent BẮT BUỘC phải thiết lập bản đặc tả chi tiết "dòng code nào gọi dòng code nào" (Line-by-line Call Graph / Execution Trace). Dùng sơ đồ này làm bản đồ định vị (Navigation Map) thay vì tải và đọc hiểu chay toàn bộ văn bản code để tránh quá tải bộ nhớ và sinh ảo giác.

---

## 5. QUY TRÌNH SỬ DỤNG TYPESAFE AI (AGENT WORKFLOW ONLY)

> **LƯU Ý CỐT LÕI**: TypeSafe AI là công cụ đo lường và thẩm định **ĐỘC LẬP DÀNH RIÊNG CHO QUY TRÌNH LÀM VIỆC CỦA AGENT & SUBAGENT**. TypeSafe **KHÔNG** phải là runtime component, không được import vào bất kỳ module sản phẩm nào của SCP.

### 1. Vai trò trong quy trình của Agent
TypeSafe cung cấp cơ chế phán quyết định lượng (Typed Evaluation: `noul` xác suất 0..1, `choice` phân loại kèm confidence, `score` thứ bậc):
1. **Duyệt Kế Hoạch (Plan Review Gate)**: Trước khi thực hiện các thay đổi lớn, Agent chạy TypeSafe để đánh giá mức độ rủi ro (`risk_level`) và tính an toàn của kế hoạch (`safe_to_execute`).
2. **Kiểm Tra Diff Trước Khi Commit (Pre-commit Diff Gate)**: Chạy `python integrations/typesafe/typesafe_eval.py --file <diff_file>` để phát hiện tác dụng phụ (`has_breaking_side_effects`) và kiểm tra tính tuân thủ Fail-Closed.
3. **Thẩm Định Độc Lập Cho Subagent (Subagent Verification Gate)**: Sau khi Subagent hoàn thành nhiệm vụ, Agent Mẹ dùng TypeSafe như một quan tòa độc lập bên ngoài để xác minh kết quả có bị ảo giác (hallucination) hoặc sửa đổi hình thức (placebo pass) hay không.

### 2. Lệnh thực thi chuẩn
Key được tự động đọc từ `.env` (`TYPESAFE_API_KEY`).
```powershell
python integrations/typesafe/typesafe_eval.py `
    --file <đường_dẫn_file> `
    --choice "risk_level=low|medium|high|critical" `
    --noul "is_safe=Does this change maintain zero-trust without unintended side effects?"
```
*(Lưu ý PowerShell: Luôn bọc tham số có dấu `|` trong dấu ngoặc kép `""`)*.
