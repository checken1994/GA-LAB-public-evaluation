---
name: scp-skill-review
description: Review bộ SCP Skills (skill pack) theo chuẩn 6 chiều C1–C6 + 4 mức bằng chứng A–D, tổng hợp từ OpenAI (Practices for Governing Agentic AI Systems, GPT-5 System Card), Anthropic（Agent Skills spec, progressive disclosure, evaluation-driven development), Google DeepMind（AI co-scientist, AlphaEvolve） và LLM-as-judge/Braintrust evals。 Dùng khi cần audit skill pack, thêm/sửa skill, kiểm tra index nhất quán, hoặc định xem skill nào đáng tin làm ground truth trước khi dùng nó để sửa chính SCP
---

# SCP Skill Review — Chuẩn đánh giá bộ kỹ năng

## Mục tiêu

Bộ skill là một "hệ thống định nghĩa thiếu sót" — bản thân nó cũng có thể chứa missing piece（DNA #25). Chuẩn này biến bộ skill thành **đối tượng audit được**: mọi kết luận phải kèm mức bằng chứng（A static / B integration / C end-to-end / D recovery, không bao giờ tuyên bố"PASS" vô điều kiện（DNA #22, #23. Con người giữ quyết định cuối cùng（DNA #4.



## Khung tham chiếu（4 lineage độc lập)

| Nguồn | Nguyên lý mượn | Áp vào chiều nào |
|---|---|---|
| **OpenAI** — *Practices for Governing Agentic AI Systems*（2023）+ *GPT-5 System Card*（2025) | accountability assignment; action ledgers, capability boundaries, default behaviors, legibility, monitoring, controllability/interruptibility, instruction hierarchy | C5（trách nhiệm/quyền hạn）, C3（legibility/tính đọc được）, C4（giám sát/khả hồi |
| **Anthropic** — *Agent Skills*（SKILL.md spec, progressive disclosure, evaluation-driven development） | discovery-ready description（firing condition）; single-purpose scoping;; <~500 dòng/5k token; ref one-level-deep; test 3+ kịch bản thật;; re-test khi data/đường dẫn đổi | C1, C2, C3, C4 |
| **Google DeepMind** — *AI co-scientist*（tournament, debate, evolve）+ *AlphaEvolve*（generator ↔ verifier độc lập） | đa tác nhân đối trọng: generate → debate → evolve;; verifier KHÔNG cùng lineage generator/skill đang review;; diversity/số lượng chủng（tiling）kiểm soát khai thác hướng mới | C4（đối trọng）, C5（verifier độc lập）, C6（mở rộng có kiểm soát |
| **LLM-as-judge / Braintrust** — agent evals（2024–2026） | golden dataset từ task thật;; trace theo từng bước（step-wise）; code-scorer + LLM-judge;; calibration trước khi dùng judge;; đa trial（non-determinism;; offline + online monitoring | C4（test thật）, C5（calibration; cấm self-report làm judge độc lập）, C6（giám sát liên tục |

> **Ghi chú lineage（DNA #5, #14）：** Bốn nguồn này đến từ 4 tổ chức khác nhau（không cùng lineage）. Bất kỳ sự đồng thuận nào giữa chúng đều mạnh hơn 10 nguồn cùng một lineage. Nhưng mọi khuyến nghị vẫn phải đối chiếu với thực tế repo trước khi áp.



## Chuẩn 6 chiều（C1–C6）— mỗi skill phải đạt ĐỦ 6

| Chiều | Câu hỏi kiểm chứng | Bằng chứng tối thiểu |
|---|---|---|
| **C1 — Đúng mục đích & mô tả bắn được（Discovery）** | `name`/`description` có chính xác nhiệmd vụ? Mô tả có phải là **điều kiện bắn**（firing condition）— chứa từ khóa trigger rõ, không mơ hồ, không overclaim? | Static: frontmatter khớp nội dung;; mô tả có từ khóa kích hoạt cụ thể（vd"review", "audit", "tối ưu", "recover"...） |
| **C2 — Một nhiệmd vụ, phạm vi rõ（Scoping）** | Một skill chỉ chuyên **1 loại nhiệmd vụ**? Có trùng lặp hoặc lệch phạm vi với skill khác trong pack? | Static: map nhiệmd vụ ↔ skill là 1-1;; không hai skill cùng mô tả một việc |
| **C3 — Cấu trúc progressive disclosure tôn trọng ngữ cảnh（Context）** | SKILL.md ≤ ~500 dòng/≤ ~5k token? Chi tiết nằm `references/`/`assets/` được gọi **có điều kiện**? Ref chỉ sâu 1 mức（không lồng）? | Static: đếm dòng/token; các lời gọi ref one-level-deep |
| **C4 — Chuẩn test thực tế & vòng phản hồi（Evaluation）** | Skill có **≥3 kịch bản test** từ task thật, **chạy được**（không chỉ đọc source）? Có re-test khi data/đường dẫn/môi trường đổi? | Integration trở lên: chạy kịch bản thật, quan sát output. Static test đơn thuần = chưa đủ |
| **C5 — Tự kiểm chứng & calibration（Self-verification）** | Kết luận dựa **evidence độc lập** không? Judge/verifier có **khác lineage** generator/skill đang review không? Có chống ảo giác"đồng thuận" và "PASS vô điều kiện" không? | Integration: đối trọng 2 tác nhân/2 lineage;; verdict kèm evidence level A→D |
| **C6 — Trách nhiệm & bền vững（Accountability & Maintenance）** | Có version/ngày khảo sát/**ngày nguồn dữ liệu động** được ghi để biết khi nào phải re-check（vd danh sách models, chỉ số count、tài liệu tham chiếu）? Có tác giả/người chịu trách nhiệm, log cập nhật? | Static: tài liệu ghi provenance + ngày;; quy trình cập nhật（"re-check khi data đổi"）tồn tại là cam kết quy trình |

> **Hằng số meta（điều kiện bắt buộc của mọi bản review）：** Nếu tài liệu khai một con số（vd "26 nguyên tắc", "9 kỹ năng", "17 models"）thì **con số đó phải được kiểm tra lại bằng đếm thực tế** ngay trong bước C1/C3 — đây chính là cơ chế bắt được kiểu lỗi"26-vs-29" và "9-vs-12". Con số tự khai KHÔNG được dùng làm bằng chứng, chỉ dùng làm"giả thuyết cần xác minh".



## Quy trình review bộ skill（5 bước）

1. **Kê khai & map nhiệmd vụ** — Liệt kê mọi `SKILL.md` trong `.agents/skills/*/`;; map mỗi skill → 1 nhiệmd vụ;; đánh dấu trùng / khoảng trống chức năng（C1, C2.
2. **Kiểm index nhất quán** — `.agents/skills/README.md`, `.agents/AGENTS.md`, `.agents/GEMINI.md` phải liệt kê **ĐÚNG** tập hợp skill hiện có（không thiếu, không lỗi số đếm, không 2 file index lệch nhau）. Đây là phép kiểm"skill về skill" đầu tiên mà chuẩn này tự áp vào chính nó。
3. **Đo chiều C3** — Đếm dòng/token mỗi `SKILL.md`;; so ngưỡng ~500 dòng;; kiểm ref chỉ sâu 1 mức。
4. **Chạy test mẫu（C4⊥**_ — Chọn **3 task đại diện** từ lịch sử task thật của pack中; kích hoạt skill đúng theo trigger của `description`;; ghi observation;; verdict kèm evidence level（A–D. Không dùng self-report làm bằng chứng duy nhất（C5..
5. **Lập báo cáo & quyết định** — Bảng per-skill 6 chiều + evidence level;; tổng hợp per-pack;; skill nào <by（Integration）hoặc thiếu chiều → `UNKNOWN`/`HUMAN_REVIEW`, **không"PASS"**（DNA #4, #22.



## Ma trận kết luận

| Kết quả | Ý nghĩa | Hành động |
|---|---|---|
| `VERIFIED` | Đạt C1–C6 + bằng chứng B trở lên, không mâu thuẫn | Dùng bình thường;; ghi provenance trong báo cáo |
| `INSUFFICIENT` | Thiếu test thật / calibration / index chưa cập nhật | Bổ sung trước khi dùng skill làm chuẩn |
| `CONTRADICTED` | Tài liệu khai ≠ thực tế（vd "26 nguyên tắc" nhưng đếm 29;; "9 kỹ năng" nhưng đếm 12） | Sửa tài liệu/index;; gắn nhãn stale;; tái-review sau khi sửa |
| `UNKNOWN` | Không đủ bằng chứng quan sát được | Không kết luận；coi như **KHÔNG dùng** skill làm ground truth |
| `HUMAN_REVIEW` | Mâu thuẫn ảnh hưởng quyền hạn / scope / bảo mật | Con người quyết định（DNA #4; không tự sửa |

 | | | |
|---|---|---|---|



## Quy tắc bắt buộc khi audit skill

- **Không tự sửa skill khác khi chưa có verdict** — chỉ báo cáo + đề xuất（DNA #4.
- **Không dùng chính skill đang review làm judge cho chính nó**（C5 둘 DNA #29："External Reviewer" = subsystem độc lập, không phải nút thắt con người。
- **Mọi kết luận ghi evidence level**（A/B/C/D）gắn với commit/snapshot và thời điểm（DNA #2, #26。
- **Không tuyên bố"bộ skill xong"** khi chưa scan toàn bộ + chưa re-test sau thay đổi data（DNA #22, #23, #25。
- **Bất kỳ con số nào trong tài liệu cũng là giả thuyết cần đếm lại**, kể cả số trong chính chuẩn này。





##Mẫu báo cááo

```markdown
# Skill Review — <tên pack> @ <commit hoặc ngày>

## Phạm vi & bằng chứng
| SKILL | C1 | C2 | C3 | C4 | C5 | C6 | Evidence | Verdict |
|---|---|---|---|---|---|---|---|---|
| scp-dna | ✓ / ✗ | ✓ / ✗ | ✓ / ✗ | A–D | ✓ / ✗ | ✓ / ✗ | A–D | VERIFIED / … |
| … | | | | | | | | |

## Index consistency（C3 meta）
- `README.md` liệt kê: N/M skill（đúng/sai — nêu tên thiếu/thừa）
- `AGENTS.md` / `GEMINI.md` khớp nhau?（md5 diff）; mọi skill hiện có đều được liệt kê？

##Mâu thuẫn phát hiện
- ...
## Open questions（không thể biết với bằng chứng hiện có）
- ...
## Final verdict: INSUFFICIENT / VERIFIED / UNKNOWN / HUMAN_REVIEW
```



## Tự-đánh giá chuẩn này（bắt buộc trước khi dùng）

Chuẩn này tự áp 6 chiều:
- **C1：** mô tả nêu đúng trigger（"audit skill pack", "thêm/sửa skill", "kiểm index"）。 
 **C2:** một nhiệmd vụ duy nhất = review skill, không trùng skill khác。 
 **C3:** file này <300 dòng, toàn bộ chi tiết nằm ngay trong file（không ref sâu.
 
 **C4:** quy trình yêu cầu chạy test thật（bước 4）, nhưng **bản thân chuẩn chưa có golden 3-task** — ghi nhận là open question. 
 **C5:** yêu cầu verifier khác lineage + cấm tự-judge — phải có agent/reviewer ngoài xác nhận。 
 **C6:** số"6 chiều"/"4 nguồn" là giả thuyết — bước 1 của mọi review phải đếm lại;; ngày khảo sát phải ghi tại đầu báo cááo。


> **Rollback path:** mọi thay đổi hạ tầng skill đều có thể `git revert`;; skill mới chỉ là tài liệu Markdown, không đụng code runtime SCP — đúng DNA #7, #9, #17.