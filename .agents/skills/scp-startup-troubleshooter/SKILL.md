---
name: scp-startup-troubleshooter
description: Chẩn đoán lỗi khởi động SCP, launcher Windows, lệch port, health/readiness, process cũ và dashboard không kết nối được. Use when the user reports error windows, SCP not opening, service not ready, port mismatch, broken start/stop scripts, or inconsistent launcher logs.
---

# SCP Startup Troubleshooter

## Mục tiêu

Tìm nguyên nhân thật của lỗi khởi động bằng cách so sánh **cấu hình mong đợi** với **runtime quan sát được**. Không sửa ngẫu nhiên và không kết luận từ một log cũ.

## Bốn service chuẩn cần kiểm tra

| Service | Port mặc định theo SCP | Readiness tối thiểu |
|---|---:|---|
| Backend | 8000 | `GET /health` và nếu có `/health/detailed` |
| Dashboard | 3000 | `GET /` |
| Loop scheduler | 3030 | `/healthz` hoặc endpoint được manifest quy định |
| LLM bridge | 11434 | endpoint bridge chuẩn, không nhầm với Ollama độc lập |

Nếu dự án chọn port khác, coi manifest hiện hành là nguồn chuẩn duy nhất và ghi rõ thay đổi.

## Quy trình an toàn

1. Không chạy lại launcher hỏng nhiều lần. Không dùng stop script chưa được kiểm tra để dọn process.
2. Lưu snapshot gồm thời điểm, danh sách process, port đang nghe, log stdout/stderr và nội dung launcher. Redact secret.
3. Đọc `.env`, service manifest, launcher, dashboard proxy và log. Lập bảng `expected_port` và `observed_port`.
4. Kiểm tra syntax/encoding của `start-scp.bat`, `stop-scp.bat`, PowerShell hoặc script tương ứng. Tìm lệnh bị nối, thiếu đầu/cuối, ký tự codepage lỗi và `cmd /k` lồng không cần thiết.
5. Kiểm tra từng port bằng probe thật, sau đó gọi health endpoint đúng service. Port mở nhưng health sai vẫn là `NOT_READY`.
6. Phân biệt process hiện tại với log cũ bằng PID, timestamp và `started_at`. Không dùng log stale làm trạng thái live.
7. Kiểm tra dependency theo thứ tự: bridge → scheduler → backend → dashboard, trừ khi manifest quy định khác.
8. Chuẩn hóa một nguồn contract gồm host, port, health URL, PID, dependency và config source. Không sửa từng file riêng lẻ mà không cập nhật contract.
9. Khôi phục launcher từ bản sạch hoặc viết lại tối thiểu. Mỗi service có stdout/stderr riêng.
10. Chạy clean stop đã kiểm soát, clean start một lần, readiness probe toàn bộ service, rồi mới chạy smoke test.
11. Chỉ sau khi bốn service nhất quán mới chạy reality test hoặc computer-use flow.

## Bảng phân loại nguyên nhân

| Nhãn | Ý nghĩa |
|---|---|
| `OBSERVED` | Được xác nhận trực tiếp từ process, port, endpoint hoặc log mới |
| `CONFIG_MISMATCH` | Cấu hình và runtime khác nhau, ví dụ 8000/8001 |
| `STALE_LOG` | Log cũ không chứng minh process hiện tại |
| `LAUNCHER_CORRUPTION` | Script bị trộn cú pháp, sai encoding hoặc sai trình tự |
| `DEPENDENCY_NOT_READY` | Service phụ thuộc chưa sẵn sàng |
| `UNPROVEN` | Chưa đủ bằng chứng để kết luận |

## Smoke test tối thiểu

```text
netstat -ano hoặc công cụ tương đương
GET backend /health
GET bridge endpoint
GET scheduler /healthz
GET dashboard /
kiểm tra PID và timestamp
```

Readiness chỉ đạt khi endpoint trả lời đúng service, đúng port và đúng phiên khởi động. Nếu launcher chờ `8000` nhưng backend thật chạy `8001`, ghi lỗi cụ thể `configured 8000, observed 8001`, không ghi chung chung “SCP chưa sẵn sàng”.

## Mẫu đầu ra

```markdown
# SCP Startup Diagnosis

## Kết luận
[Nguyên nhân có bằng chứng và giới hạn kết luận]

## Service map
| Service | Expected | Observed | Health | PID | Timestamp | Status |
|---|---:|---:|---|---:|---|---|

## Launcher review
| File | Syntax | Encoding | Trình tự | Kết luận |
|---|---|---|---|---|

## Chuỗi nguyên nhân
[launcher/config → port mismatch → readiness failure → dashboard impact]

## Sửa an toàn theo thứ tự
1. Snapshot và backup.
2. Chọn contract port duy nhất.
3. Khôi phục launcher sạch.
4. Sửa readiness probe.
5. Clean start/stop.
6. Smoke test.

## Chưa thể kết luận
[Danh sách giả thuyết cần log live hoặc test mới]
```

## Không được làm

Không xóa process tùy ý, không xóa log cũ, không sửa port chỉ trong `.env`, không báo “đã sửa” khi chưa chạy clean start/readiness/clean stop, và không khởi động autonomous flow khi service contract còn lệch.

## Tài liệu SCP tham chiếu

Đọc khi cần `Chẩn đoán lỗi khởi động SCP — hai cửa sổ báo lỗi.md`, `Audit nhanh bộ tệp SCP trên máy tính đã kết nối.md` và `Lộ trình chuyển SCP từ Agent Control Plane thành Agent OS.md`.
