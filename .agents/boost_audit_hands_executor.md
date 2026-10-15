# Kích hoạt /boost — SCP Delta Audit Mode
**Mục tiêu (TARGET):** `scp/hands/hands_executor.py` và cơ chế Cấp quyền (Authority/Capability).

**Tình huống:** Báo cáo Delta Audit gốc nghi ngờ tồn tại một Tử huyệt bạo chúa (FA-05 Violation) tại `HandsExecutor`: Hệ thống cho phép tự sinh Capability Token (Tự phong quyền) nếu Caller không cung cấp. Điều này phá vỡ hoàn toàn nguyên tắc Fail-Closed PEP (Policy Enforcement Point).

**Nhiệm vụ của bạn:**
Áp dụng **TUYỆT ĐỐI** bộ luật trong kỹ năng `scp-delta-audit` (đã lưu tại `.agents/skills/scp-delta-audit/SKILL.md`).
Hãy thực hiện đầy đủ 5 Phase của quy trình Delta Audit lên module `scp/hands/hands_executor.py`:
1. TARGET MANIFEST
2. REALITY SCAN
3. CAUSAL GAP ANALYSIS
4. PROBE BEFORE PATCH (Bắt buộc thiết kế Anti-Placebo)
5. EVOLUTION PATH

**Yêu cầu Output:** 
Đóng gói toàn bộ 10 mục của OUTPUT CONTRACT vào file `hands_executor_audit_report.md`.
**KHÔNG ĐƯỢC PHÉP SỬA CODE SẢN PHẨM Ở GIAI ĐOẠN NÀY!** Khẩu quyết là "Probe Before Patch". Bạn chỉ đang lập hồ sơ truy tố, chưa được phép thi hành án.
