---
name: scp-gateway-resilience
description: Review and govern the LLM Gateway, Circuit Breakers, Model Fallback Cascade, and API rate limits. Use when the user asks about API stability, model routing, fallback logic, or external AI dependency management.
---

# SCP Gateway Resilience

## Mục tiêu
Đảm bảo hệ thống LLM Gateway (luồng giao tiếp với OpenRouter, Anthropic, DeepSeek, v.v.) có khả năng tự phục hồi, chống nghẽn cổ chai (bottleneck), và không làm rò rỉ Context nhạy cảm khi thực hiện Fallback.

## Quy tắc Thiết kế LLM Gateway

1. **Circuit Breaker (Cầu dao tự ngắt):** Nếu một Provider liên tục Timeout hoặc trả về 429/500 (3 lần liên tiếp), Provider đó phải bị ngắt kết nối (Open) trong ít nhất 5 phút. Không gửi thêm Request để tránh treo Hàng đợi (Task Queue).
2. **Tri-State Cascade:** Kết quả của LLM không bao giờ là Chân lý tuyệt đối. Nếu Model A báo lỗi hoặc trả kết quả mơ hồ, phải có cơ chế tham vấn Model B (Cross-Falsification). Nếu cả hai bất đồng, trả về `UNKNOWN`.
3. **Data Privacy in Fallback:** Nếu Model A (được duyệt cho dữ liệu R3-Nhạy cảm) bị sập, hệ thống KHÔNG ĐƯỢC tự động Fallback sang Model C (Không an toàn/Ghi log) nếu Context chứa Secret.
4. **Semantic Caching:** Các câu hỏi lặp lại (Ví dụ: Đánh giá một hành động giống hệt nhau) phải được Cache dựa trên Hash của Context để tiết kiệm Token và Latency.
5. **Jitter Backoff:** Khi bị Rate Limit, hệ thống phải chờ theo thuật toán Exponential Backoff có Jitter (Random time) để tránh thảm họa Thundering Herd.

## Ma trận Kiểm tra Cửa ngõ (Gateway Audit)

| Chức năng | Tiêu chuẩn Bắt buộc | Trạng thái SCP hiện hành |
|---|---|---|
| Retry Logic | Exponential Backoff + Jitter | Đánh giá |
| Circuit Breaker | Có Timeout và Threshold rõ ràng | Đánh giá |
| Model Routing | Định tuyến dựa trên Task Complexity (Risk Tier) | Đánh giá |
| Fallback Privacy | Chặn Fallback nếu vi phạm Data Class | Đánh giá |

## Mẫu báo cáo Gateway Audit

```markdown
# SCP Gateway Resilience Audit

## Trạng thái Provider
| Provider/Model | Health | Latency p95 | Tỷ lệ Timeout | Trạng thái Cầu dao |
|---|---|---|---|---|

## Đánh giá Kiến trúc
[Phân tích khả năng chịu tải và chống sụp đổ dây chuyền]

## Cảnh báo Bảo mật
[Nêu rõ nếu việc Fallback vô tình gửi dữ liệu nhạy cảm ra ngoài]
```
