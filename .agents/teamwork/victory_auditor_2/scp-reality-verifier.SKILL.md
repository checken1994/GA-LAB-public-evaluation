# Copied from C:\Users\check\.gemini\config\plugins\scp-skills\skills\scp-reality-verifier\SKILL.md

# SCP Reality Verifier

## Mục tiêu

Không hỏi model “có xong không?” rồi tin câu trả lời. Kiểm tra **kết quả quan sát được**, bằng chứng trước/sau, postcondition, provenance và phạm vi test.

## Cấp độ bằng chứng

| Cấp | Ý nghĩa | Có chứng minh runtime không? |
|---|---|---:|
| A — Static | File, route, schema, pattern hoặc assertion tồn tại | Không |
| B — Integration | Một số module/process nối được với nhau | Một phần |
| C — End-to-end | Task thật đi qua planner, policy, tool, verifier, audit và artifact | Có, trong workload đó |
| D — Recovery proof | Cấp C cộng crash/timeout/restart/unknown-state được xử lý đúng | Có, với recovery |

Không nâng cấp từ A lên C chỉ vì nhiều test PASS.

## Quy trình kiểm chứng

1. Xác định claim cần kiểm tra và điều kiện hoàn thành chính xác.
2. Xác định test profile, commit, runtime, input hash và phạm vi workload.
3. Thu evidence trước action, action proposal, policy verdict, tool result, observation sau action, verifier result và artifact.
4. Kiểm tra postcondition độc lập: URL, text, schema, file hash, network response, provider request ID, state transition hoặc invariant.
5. Kiểm tra provenance: evidence đến từ đâu, thời điểm nào, task/attempt/step nào, có bị log cũ hoặc dữ liệu untrusted không.
6. Đánh giá consistency giữa event journal, projection, checkpoint, tool output và artifact.
7. Phân loại verdict `VERIFIED`, `CONTRADICTED`, `INSUFFICIENT` hoặc `UNKNOWN`.
8. Ghi rõ điều chưa kiểm tra. Không dùng từ “chắc chắn” khi chỉ có static evidence.

## Quy tắc với test PASS

- Kiểm tra test có thật sự được thu thập hay không; `no tests ran` không phải PASS.
- Kiểm tra lỗi encoding/runner có thể làm sai exit code.
- Kiểm tra test có khởi động service thật hay chỉ đọc source.
- Gắn mọi kết quả với commit/snapshot/test profile.
- Ghi `PASS_WITHIN_SCOPE`, không mở rộng thành “hệ thống production-ready”.
- Nếu `claims_checked: 0`, coi đó là module health chứ chưa phải verifier proof.
