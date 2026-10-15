---
name: scp-learning-loop-guard
description: Govern the continuous learning loop, knowledge warehouse, Deep Scraper, and Autofix engine. Use when evaluating how SCP ingests external knowledge, updates its own AST, or prevents knowledge poisoning and catastrophic forgetting.
---

# SCP Learning Loop Guard

## Mục tiêu
Kiểm soát quy trình "Tự tiến hóa" (Evolution & Learning) của SCP. Đảm bảo rằng việc nạp tri thức từ bên ngoài (Internet, GitHub) và tự động sửa mã nguồn (Autofix) diễn ra an toàn, không nhiễm độc, và không gây Catastrophic Forgetting.

## Các năng lực phải kiểm soát

| Thành phần | Điều kiện an toàn bắt buộc |
|---|---|
| **Deep Scraper** | Phải qua Token Bucket. Dữ liệu cào về không được tin ngay (Fail-Closed Ingestion). |
| **Knowledge Quarantine** | Dữ liệu bên ngoài phải bị cách ly, kiểm tra độ độc hại (Poisoning/Prompt Injection) trước khi đưa vào KB. |
| **Wired Brain** | Khi Prompt ghép nối với Knowledge Warehouse, phải có chỉ thị từ chối nội dung mâu thuẫn với DNA. |
| **AST Mutator** | Autofix chỉ được phép thay đổi AST cục bộ, không phá vỡ cấu trúc Class/Method cha. |
| **Catastrophic Forgetting**| Bản vá mới không được ghi đè/làm hỏng các rào cản bảo mật (Tier-1 Guard, PEP) đã có. |

## Quy trình Review Learning Loop

1. **Kiểm tra Rate Limiting:** Mọi luồng cào dữ liệu (như `top_systems_learning.py`) phải đi qua Semaphore/TokenBucket cơ học.
2. **Kiểm tra Data Provenance:** Dữ liệu nạp vào phải lưu rõ nguồn gốc (URL, Commit Hash, Timestamp, Author).
3. **Phòng chống Poisoning:** Dữ liệu thô (như README) tuyệt đối không được parse trực tiếp thành `exec()` hoặc System Prompt Instruction. Nó chỉ được coi là `Context Data`.
4. **Kiểm tra Autofix Blast Radius:** Đánh giá xem bản vá do LLM sinh ra có vượt ra ngoài Scope của Bug không. Nếu Bug ở Hàm A, bản vá có lén sửa Hàm B không?
5. **Kiểm tra Reversibility (Rollback):** Mọi thay đổi codebase phải đi kèm với một bản snapshot để hệ thống tự động Rollback nếu Reality test fail.

## Ma trận Quyết định Nạp Tri thức

| Loại Dữ liệu | Trạng thái Mặc định | Hành động Cần thiết |
|---|---|---|
| Tài liệu Kiến trúc (README) | **QUARANTINE** | Đưa qua LLM để rút trích Concept, vứt bỏ toàn bộ Code/Script thực thi bên trong. |
| Mã nguồn (Code Snippets) | **DENY** | Không bao giờ được Copy-Paste thẳng. Chỉ dùng để tham khảo Logic. |
| Metadata (Stars, Forks) | **ALLOW** | Dùng để phân loại, nhưng không dùng làm trọng số độ tin cậy tuyệt đối. |

## Mẫu báo cáo Evolution Audit

```markdown
# SCP Learning Loop Audit

## Nguồn tri thức
| Nguồn | Token Bucket | Quarantine | Poison Check | Kết luận |
|---|---|---|---|---|

## Đánh giá Autofix
| Bug Target | Thay đổi AST | Blast Radius | Rollback Plan | Kết quả Reality Test |
|---|---|---|---|---|

## Cảnh báo
[Chỉ ra nguy cơ Catastrophic Forgetting hoặc Knowledge Conflict]
```
