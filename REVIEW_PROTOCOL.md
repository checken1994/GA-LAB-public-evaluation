# Independent Human Review Protocol

## Mục tiêu

Quy trình này giúp một người đánh giá không cần hiểu toàn bộ mã nguồn vẫn có thể kiểm tra 50 ứng viên RAG theo cách có thể truy nguyên. **Không tự động chuyển ứng viên thành Gold.** Chỉ người đánh giá thật, có danh tính và thời gian review, mới được ghi quyết định human-verified.

## Cách làm cho từng dòng

Mở `REVIEW_SHEET_50.csv`. Với mỗi `question_id`, mở `source_url` và đọc đúng phần nguồn liên quan. Đối chiếu bốn mục: câu hỏi có đúng chủ đề của nguồn không; câu trả lời có được nguồn hỗ trợ trực tiếp không; câu trả lời có bỏ sót điều kiện quan trọng không; và các con số/ngày tháng hoặc tuyên bố hiện tại có được nguồn xác nhận không.

Nếu nguồn không mở được, nguồn lệch câu hỏi, hoặc câu hỏi cần dữ liệu mới hơn nguồn, chọn `NEEDS_MORE_EVIDENCE`, không đoán. Nếu câu trả lời trái nguồn hoặc không trả lời đúng câu hỏi, chọn `REJECTED`. Chỉ chọn `VERIFIED` khi có đoạn trích đủ rõ để một người khác kiểm tra lại mà không cần tin vào người review.

## Biểu mẫu quyết định tối thiểu

| Trường | Nội dung bắt buộc |
|---|---|
| `question_id` | ID nguyên bản trong CSV |
| `decision` | `VERIFIED`, `REJECTED`, hoặc `NEEDS_MORE_EVIDENCE` |
| `evidence_quote` | Trích dẫn ngắn từ nguồn, giữ nguyên ngôn ngữ gốc |
| `source_url` | URL canonical đã kiểm tra |
| `reviewer_id` | Tên, tổ chức, hoặc mã reviewer có thể truy nguyên |
| `reviewed_at_utc` | Thời gian ISO-8601 UTC |
| `notes` | Lý do ngắn, đặc biệt với current/high-stakes |

## Quy tắc chống tự xác nhận

Bản review do mô hình tạo trong artifact này chỉ là **independent LLM triage**. Không được copy trường `static_core_promote` thành `VERIFIED`, không được coi `source_relevant=true` là bằng chứng đủ, và không được dùng câu trả lời do chính hệ thống sinh ra làm xác nhận độc lập cho chính nó.

Các câu hỏi current/high-stakes phải có nguồn chính thức hoặc nguồn chuyên ngành phù hợp và vẫn cần người review thật. Nếu thiếu nguồn canonical hoặc thiếu đoạn trích, giữ trạng thái `NEEDS_MORE_EVIDENCE`.

## Đóng gói kết quả

Lưu quyết định thành JSONL/CSV riêng, không sửa artifact gốc. Mỗi dòng phải giữ `question_id`, `source_url`, `evidence_quote`, `reviewer_id`, `reviewed_at_utc`, và `decision`. Tính hash file sau khi hoàn tất. Nếu hai reviewer khác quyết định, giữ `NEEDS_MORE_EVIDENCE` cho tới khi có adjudication được ghi rõ.

## Tiêu chí mở Gate

Gate chỉ có thể chuyển trạng thái khi đủ số dòng **human-verified**, có source provenance và ground truth được review độc lập theo đúng schema của runner. Independent LLM review, token overlap, HTTP 200, hoặc một pilot điểm đơn lẻ không tự mở Gate. Nếu thiếu một điều kiện, runner phải trả trạng thái blocked thay vì tạo điểm đẹp.
