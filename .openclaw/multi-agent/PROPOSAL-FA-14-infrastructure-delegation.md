# ĐỀ XUẤT: FA-14 — Cấm tự ý sửa hạ tầng / khởi động lại hệ thống (No Solo Infrastructure Mutations)

- Nguồn: tìm thấy trong stash cũ của repo (khôi phục 2026-09-29, nội dung nguyên bản lưu tại
  `.openclaw/multi-agent/pre-recovery-snapshot.diff` — vùng staged `.agents/AGENTS.md` + `.agents/GEMINI.md`).
- Coordinator KHÔNG tự commit thay đổi governance: đây là hợp đồng dự án, cần chủ sở hữu phê duyệt.

## Nội dung đề xuất (nguyên văn từ stash)

**FA-14: CẤM TỰ Ý SỬA HẠ TẦNG/KHỞI ĐỘNG LẠI HỆ THỐNG (No Solo Infrastructure Mutations).**
Orchestrator (Agent mẹ) TUYỆT ĐỐI KHÔNG ĐƯỢC tự ý dùng các công cụ edit file hay chạy shell commands
để trực tiếp sửa đổi các file cấu hình môi trường (VD: .env, supervisor.ps1, docker-compose.yml) hoặc
trực tiếp restart/kill server. Mọi tác vụ can thiệp vào tiến trình (process) hoặc hạ tầng khởi động
BẮT BUỘC phải được Ủy quyền (Delegation) cho một Subagent chuyên trách (VD: DeepCoder, DevOps Agent)
thực thi. Phải có một Subagent khác kiểm chứng chéo (Reality Verify) trạng thái toàn vẹn của tất cả
các tiến trình liên quan sau khi khởi động.

## Vị trí thêm (theo stash)
- `.agents/AGENTS.md`: ngay sau mục FA-13 (trước "Enforcement").
- `.agents/GEMINI.md`: ngay sau dòng tóm tắt FA-13.

## Lý do nên cân nhắc
- Buộc mọi can thiệp process/hạ tầng đi qua agent chuyên trách + kiểm chứng chéo — giảm rủi ro
  "solo mutation" làm hỏng service thật (đúng bài học stash-conflict 2026-09-29).
- Nhất quán với FA-11/FA-12 về human authority và empirical closure.

## Việc cần nếu duyệt
1. Thêm FA-14 vào cả 2 file ở vị trí trên.
2. Cập nhật dòng "FORBIDDEN ACTIONS (FA-01→FA-07)" trong AGENTS.md gốc → "FA-01→FA-14".
3. Kiểm tra `tools/t00_meta_audit.py` + `.github/workflows/scp_guardrails.yml` có cần pin số FA không.
