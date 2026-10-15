# SCP Agent Instructions & System Skills Directives

> **QUY TẮC BẮT BUỘC TRƯỚC MỌI PHIÊN LÀM VIỆC (PRE-SESSION MANDATE)**
> Trước khi bắt đầu bất kỳ tác vụ nào trong workspace này, Agent **BẮT BUỘC** thực hiện theo thứ tự sau bằng cách gọi tool thực tế (KHÔNG dùng training memory thay thế):
> 1. **Tải `GA.md`** (gọi `view_file` trên nhánh `main`) → lấy live project state, current blockers, và next task.
> 2. **Tải `.agents/AGENTS.md`** (gọi `view_file`) → nạp đầy đủ FA-01 đến FA-13 vào context. `GEMINI.md` auto-load nhưng chỉ chứa tóm tắt — AGENTS.md mới là nguồn đầy đủ.
> 3. **Tải Skill tương ứng** (gọi `view_file` vào `.agents/skills/<tên-skill>/SKILL.md`) → kích hoạt skill phù hợp với task.
> **"Tải" = gọi tool `view_file` thực tế. Dùng training memory thay thế = Vi phạm Pre-session Mandate.**


---

## 1. Bộ Kỹ Năng SCP Cốt Lõi (SCP Skills Pack)

Toàn bộ 13 kỹ năng SCP được quản lý và version-control tại `.agents/skills/`. Việc một ChatGPT surface/plugin có cài các skill này hay không là trạng thái triển khai riêng và **không được suy ra từ sự tồn tại của file trong repo**; khi chưa có bằng chứng cài đặt trên surface hiện hành, phải coi là `NOT_INSTALLED_ON_SURFACE`.


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

Mọi AI agent làm việc với SCP đều BỊ CẤM thực hiện các hành động sau.
Vi phạm bất kỳ điều nào là blocker — commit sẽ bị chặn bởi T00 Meta-Audit
và CI workflow `scp_guardrails.yml`.

**FA-01: KHÔNG loosen assertion / KHÔNG tạo Placebo Assertion.**
Không thay đổi assertion trong `tests/` theo hướng chấp nhận thêm giá trị,
giảm độ chính xác, thêm `any()` / `or` / fallback condition quanh assert.
*Đặc biệt:* CẤM thay thế ruột test cũ bằng các assertion hình thức (ví dụ: `assert not hasattr(module, 'feature')`) khi phế truất tính năng. Mọi bài test giữ lại NodeID phải kiểm chứng hành vi thực tế của kiến trúc thay thế.
TEST RED ↓ classify
├─ HARNESS_BROKEN → sửa harness, prove strictness preserved/increased
├─ PRODUCT_BLOCKED → capability/evidence chưa đủ → không manufacture green
└─ PRODUCT_FAIL → sửa product

**FA-02: KHÔNG delete/skip/xfail test.**
Không xóa test file, thêm `@pytest.mark.skip`, `@pytest.mark.xfail`,
`pytest.skip()`, hoặc comment out assertion để test pass.
Khi phế truất tính năng kiến trúc (Architectural Deprecation), bắt buộc tuân theo Phase 1.1 của `EXECUTION_PROTOCOL.md`.

**FA-03: KHÔNG tuyên bố "PASS/Done/Fixed" khi chưa có evidence.**
Mọi tuyên bố test xanh phải kèm terminal output thực tế
của `pytest tests/` trên exact SHA đang làm việc.
Không chấp nhận kết quả từ subset test làm bằng chứng toàn bộ.

**FA-04: KHÔNG tạo simulated/manufactured VERIFIED.**
Không trả `VERIFIED` từ stub, mock, hoặc hardcoded return.
`VERIFIED` chỉ được phép khi có Reality observation thật.

**FA-05: KHÔNG self-grant authority.**
Executor không tự issue token. Caller phải cung cấp token
đã được cấp bởi authority riêng biệt.

**FA-06: KHÔNG sửa production code trước baseline reconcile.**
Mọi session mới phải xác định exact HEAD SHA, đọc `GA.md`,
và tạo candidate branch trước khi mutation bất kỳ file nào.

**FA-07: KHÔNG claim maturity từ code/test presence.**
M4 cần C-level Reality evidence trên exact SHA.
M5 cần D-level recovery evidence.
Có class/test file không đồng nghĩa đạt maturity.


**FA-08: KHÔNG tự tạo bằng chứng (No Forged Provenance).**
Tuyệt đối cấm Agent tự ý dùng lệnh write_to_file để tạo ra các file .log, .txt, .out chứa nội dung giả lập kết quả thực thi. Mọi bằng chứng (Evidence) phải là kết quả raw stdout/stderr sinh ra từ lệnh shell hệ thống (ví dụ: pytest > log, python script.py). Ảo giác output terminal là vi phạm nghiêm trọng.

**FA-09: CẤM kết luận lỗi mà không có kịch bản chứng minh (The Exploit Mandate).**
Không được phép khẳng định hệ thống có lỗ hổng (logic, concurrency, security...) chỉ bằng việc phân tích mã nguồn (Static AST). Để claim một lỗi, BẮT BUỘC phải viết và chạy một script mô phỏng/tấn công độc lập. Nếu script không văng lỗi (Crash/Exception) trong thực tế terminal, giả thuyết lỗi đó phải bị loại bỏ.

**FA-10: CẤM giả định trạng thái giữa các thư mục/workspace (Cross-Workspace Isolation).**
Khi được yêu cầu kiểm tra một thư mục mới (clone, audit workspace, external repos), cấm mặc định rằng code của nó giống với thư mục gốc. Bắt buộc phải kiểm tra HEAD SHA, hash hoặc chạy diff trước khi phân tích.

**FA-11: CẤM LÀM NGƠ LỖ HỔNG LÂN CẬN (Mandatory Peripheral Audit & No Blind Eye).**
Khi mở bất kỳ file nào để sửa code, Agent BẮT BUỘC thoát khỏi tư duy "đường hầm" (task myopia) và phải quét nhanh logic bảo mật ngoại vi (State Machine, Evidence Gates, Quyền hạn) của các hàm lân cận. Nếu phát hiện lỗ hổng ngoài phạm vi (Out-of-scope GAP), BẮT BUỘC tuân thủ 3 bước:
1. **Cấm lén lút sửa (Anti-Scope Creep):** KHÔNG ĐƯỢC lén lút vá lỗ hổng mới khi chưa chạy quy trình Probe (Probe Before Patch).
2. **Báo cáo Nhân quả Bắt buộc (Mandatory Causal Report):** KHÔNG ĐƯỢC ghi log suông. Bắt buộc tạo một Artifact độc lập (VD: `EMERGENCY_GAP_REPORT.md`), trong đó phải vẽ Sơ đồ Nhân quả (Mermaid Causal Graph) chỉ rõ: Trigger -> Local Failure -> System Impact.
3. **Quyền Phủ Quyết (Halt & Escalate):** Nếu lỗ hổng lân cận làm cho tác vụ hiện tại đang làm trở nên vô nghĩa, Agent BẮT BUỘC PHẢI DỪNG TÁC VỤ HIỆN TẠI, trả về trạng thái FAILED/BLOCKED, và ép Orchestrator ưu tiên xử lý lỗ hổng nền tảng trước.

**FA-12: NGHIỆM THU NHÂN QUẢ THỰC TẾ (End-to-End Empirical Closure).**
Tuyệt đối không được tuyên bố "Hoàn thành" (FIXED/DONE) chỉ bằng việc chạy Unit Test. Quá trình đóng (close) một lỗ hổng BẮT BUỘC phải qua 5 bước:
1. **Bản đồ Nhân quả Toàn phần:** Vẽ Causal Graph cho *toàn bộ file* vừa sửa (không chỉ hàm bị lỗi).
2. **Truy quét Lỗi ẩn:** Đối chiếu bản đồ, xác định xem trong file đó còn lỗ hổng nào đang bị "chìm" (chưa được báo cáo) hay không.
3. **Thực thi Vật lý:** Chạy tác vụ thực tế trên PC (Live Environment / Terminal).
4. **Khám nghiệm Runtime Data:** Đọc và phân tích trực tiếp dữ liệu thực tế sinh ra sau khi chạy (VD: raw SQLite rows, physical logs).
5. **Bằng chứng End-to-End:** Dùng data thực tế đó để đối chiếu ngược lại Sơ đồ Nhân quả, chứng minh bằng mắt thật rằng: *Chuỗi nhân quả của đoạn code vừa fix ĐÃ THỰC SỰ ĐƯỢC GỌI và chạy thành công từ đầu đến cuối.*

**FA-13: TEST TỪ NHÂN QUẢ (Causal-Driven Test Generation).**
Sau khi vẽ Causal Graph (bước 1 của FA-12), Agent BẮT BUỘC tạo một **Coverage Matrix**: mỗi nhánh nhân quả trong graph phải có ít nhất 1 test tương ứng trong `tests/`. Nhánh nào thiếu test phải xử lý theo một trong hai cách:
1. **Viết test mới** bao phủ nhánh đó (ưu tiên).
2. **Ghi nhận `UNPROVEN_BRANCH`** vào báo cáo và báo cáo ngay lên Orchestrator để được duyệt trước khi tiếp tục.
Không được phép tuyên bố FIXED/DONE khi còn nhánh nhân quả chưa được phủ test mà không có lý do được Orchestrator chấp thuận.

**Phạm vi bao phủ bắt buộc:** Coverage Matrix phải bao gồm TOÀN BỘ chuỗi nhân quả của **tất cả file đang sửa** VÀ **các file liên quan** (file nào gọi vào hoặc được gọi từ file đang sửa). Không được chỉ test mỗi nhánh vừa fix — toàn bộ state machine và call graph liên quan đều phải được kiểm kê và phân loại COVERED / UNPROVEN_BRANCH.



---

## 4. Enforcement Infrastructure

| Tầng | Cơ chế | File |
|---|---|---|
| Tier 1 | Git pre-commit hook | `tools/install_git_hooks.py`, `tools/t00_meta_audit.py` |
| Tier 2 | Agent instruction files (auto-loaded) | `.agents/AGENTS.md`, `.agents/GEMINI.md`, `.agents/EXECUTION_PROTOCOL.md` |
| Tier 3 | GitHub Actions CI (độc lập khỏi AI) | `.github/workflows/scp_guardrails.yml` |

Cài đặt hook: `python tools/install_git_hooks.py`

## 5. CƠ CHẾ CƯỠNG CHẾ BỘ NHỚ (AGENT-LEVEL HARD CONSTRAINTS)

Để chống lại tình trạng Agent "Có Skill nhưng lười không dùng" và "Giao quyền quá mức cho Subagent", 2 cơ chế sau đây mang tính Ràng buộc Tuyệt đối (Forced Constraints) đối với bất kỳ Agent nào hoạt động trong SCP:

1. **Forced Skill Activation (Chống ảo giác đồng thuận):**
   Agent Mẹ KHÔNG ĐƯỢC PHÉP chỉ dựa vào tóm tắt (summary) của Skill từ training memory hoặc GEMINI.md. Trước khi phân tích mã nguồn hoặc đưa ra bất kỳ phán quyết nào, Agent BẮT BUỘC phải **gọi tool `view_file`** để tải nội dung file `SKILL.md` tương ứng tại `.agents/skills/<tên-skill>/SKILL.md` vào context window. **"Tải" ≠ "Nhớ từ training"**. Báo cáo kết quả mà thiếu bước gọi tool tải file Skill = Vi phạm nghiêm trọng (Báo cáo vô hiệu).

2. **Subagent Prompt Injection (Trói buộc Đệ - Chống F01/F02 tái phát):**
   Khi dùng tool `invoke_subagent`, Agent Mẹ TUYỆT ĐỐI KHÔNG ĐƯỢC giao Prompt mở. Trong trường `Prompt` truyền cho Subagent, BẮT BUỘC phải nhúng kèm đoạn lệnh cưỡng chế sau (hoặc tương đương):
   > "MANDATORY BINDING: You are strictly bound by Zero-Trust and Fail-Closed principles. You MUST adhere to FA-01 through FA-13. You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables."

  3. **Call Graph Navigation (Chống ngợp dữ liệu):**
     Khi thực hiện kiểm toán hoặc phân tích mã nguồn phức tạp, Agent BẮT BUỘC phải thiết lập bản đặc tả chi tiết "dòng code nào gọi dòng code nào" (Line-by-line Call Graph / Execution Trace). Dùng sơ đồ này làm bản đồ định vị (Navigation Map) thay vì tải và đọc hiểu chay toàn bộ văn bản code để tránh quá tải bộ nhớ và sinh ảo giác.

---

## 6. QUY TRÌNH SỬ DỤNG TYPESAFE AI (AGENT WORKFLOW ONLY)

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


