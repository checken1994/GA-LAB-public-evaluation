# SCP DNA — 29 Nguyên tắc cốt lõi

Nguồn: SCP Continuity Archive + DNA Audit Rounds.

Mỗi nguyên tắc là một "missing piece" mà SCP đã phát hiện qua quá trình phát triển. Dùng làm compass khi phân tích, thiết kế, debug, audit hoặc đưa ra phán quyết.

---

## 1. Hỏi Tại sao
**Title:** Bắt đầu bằng câu hỏi, không phải giải pháp
**Principle:** Không bắt đầu bằng giải pháp. Bắt đầu từ vấn đề → hỏi Tại sao → tìm giả định → tìm bằng chứng → phát hiện missing piece → thiết kế → thử → audit → sửa.
**Anti-pattern:** Nhảy thẳng đến code fix mà không hiểu root cause.

## 2. Vòng lặp khép kín
**Title:** Vòng lặp thay đổi hệ thống có thể khép kín
**Principle:** GỌI LLM + ĐỌC SOURCE + PHÁT HIỆN + SINH CODE + GHI/SỬA + CHẠY + KIỂM TRA + ĐIỀU KHIỂN RUNTIME + TẠO PROCESS = vòng lặp có thể khép kín.
**Anti-pattern:** Fix code nhưng không chạy lại để verify.

## 3. Câu hỏi tối hậu
**Title:** Có thứ gì mà chuỗi "Tại sao?" không được phép biến thành đối tượng cần xem xét?
**Principle:** Trong hệ thống có tồn tại bất kỳ thứ gì mà chính chuỗi "Tại sao?" không được phép biến thành một đối tượng cần xem xét và thay đổi hay không?
**Anti-pattern:** Coi scanner/autofix chính là vùng cấm audit.

## 4. Con người quyết định
**Title:** SCP tìm chỗ sai. Con người quyết định.
**Principle:** Hệ thống không có quyền phê duyệt quyết định cuối cùng. Hệ thống tìm lỗi, đề xuất fix, con người quyết định có apply không.
**Anti-pattern:** Tự động apply fix thay đổi logic quan trọng.

## 5. Ảo giác đồng thuận
**Title:** Không tin một tác nhân. Tin vào quá trình có khả năng phát hiện khi chính nó sai.
**Principle:** 10 tờ báo đưa cùng tin không phải 10 nguồn — nếu cùng sao chép từ 1 nguồn thì chỉ là 1 lineage. 100 AI cùng kết luận chưa chắc 100 nguồn độc lập.
**Anti-pattern:** Tin kết quả vì nhiều nguồn đều PASS cùng một lineage.

## 6. Gốc tin cậy bên ngoài
**Title:** Quyền cấp capability phải nằm ngoài miền hệ thống có thể tự sửa
**Principle:** Miền nhận thức / Gốc tin cậy bên ngoài / Miền thực thi (sandbox, rollback, audit log). Hệ thống bên trong không có quyền sửa gốc tin cậy.
**Anti-pattern:** Autofix tự sửa classifier để tự nâng tier.

## 7. Autofix an toàn
**Title:** 6 safety guards cho autofix kể cả khi auto-approve ON
**Principle:** 1. RELAXATION patterns KHÔNG bao giờ auto. 2. Rate limit. 3. Auto-timeout. 4. Audit log riêng. 5. Backup file. 6. Cooldown.
**Anti-pattern:** Autofix vô hạn, không rate limit, không cooldown.

## 8. KB accumulation
**Title:** Audit trail lưu lại mọi quyết định autofix
**Principle:** Mỗi quyết định quan trọng phải được log với before/after hash, reality test result, rollback token.
**Anti-pattern:** Fix không log, không audit, không rollback được.

## 9. No harm
**Title:** Fix phải có non-fatal guards — nếu fail thì fail-open
**Principle:** Mỗi fix có try/except + fallback. Không để fix mới gây regression.
**Anti-pattern:** Fix raise Exception → crash toàn pipeline.

## 10. Hội đồng đa hệ thống
**Title:** SCP: Còn thiếu gì? META: Có cần làm không? Thứ 3: Có cách khác không?
**Principle:** Ba hệ thống đối trọng. Bộ đánh giá hậu quả.
**Anti-pattern:** Một scanner duy nhất quyết định fix.

## 11. Human-in-the-loop thật
**Title:** Con người có thực sự hiểu điều mình đang phê duyệt không?
**Principle:** Không chỉ hỏi "đã bấm phê duyệt chưa?" mà hỏi "con người có hiểu không?". Nếu không hiểu → không được phê duyệt.
**Anti-pattern:** Rubber-stamp approval.

## 12. Nghịch lý thử-hiểu
**Title:** Phải thử mới hiểu, nhưng phải hiểu mới được thử
**Principle:** Phá vòng lặp bằng sandbox → giới hạn capability → quan sát → tăng mức hiểu → mở rộng từng bước.
**Anti-pattern:** Đợi "hiểu đủ" mãi mãi, không bao giờ chạy.

## 13. Không đứng số một
**Title:** Nếu hệ thống khác tốt hơn thật thì dùng nó
**Principle:** Không hỏi "hệ thống nào tốt hơn" mà hỏi "phù hợp hơn với loại vấn đề nào".
**Anti-pattern:** Not-Invented-Here syndrome.

## 14. Đồng thuận ≠ đúng
**Title:** Ba hệ thống đồng ý vì cùng chia sẻ giả định sai thì sao?
**Principle:** Đa số đồng ý = khả năng đúng cao hơn CHƯA được chứng minh. Cần góc nhìn không cùng lineage.
**Anti-pattern:** Vote đa số để quyết định.

## 15. Gà Lab bị audit
**Title:** Gà Lab tồn tại vì bằng chứng hay vì quán tính thể chế?
**Principle:** Hệ thống không thể là trọng tài duy nhất vì nó là sản phẩm của chính nó. Cần external reviewer.
**Anti-pattern:** Tự audit mà không có external reviewer.

## 16. Học nói phạm vi
**Title:** Chỉ dùng dữ liệu được phép — không tự vượt quyền
**Principle:** Chỉ dùng dữ liệu cung cấp / nguồn công khai / nguồn được phép. Không đủ bằng chứng → báo không đủ.
**Anti-pattern:** Autofix sửa file ngoài scope.

## 17. Hành động khi chưa biết hết
**Title:** Khi nào có thể hành động mà không cần giả vờ mọi câu hỏi đã giải quyết?
**Principle:** Hành động nhỏ + đảo ngược được + quan sát được + hậu quả giới hạn → thử được.
**Anti-pattern:** Apply toàn bộ fix batch mà không rollback plan.

## 18. Khẩu hiệu Gà Lab
**Title:** HỎI. THỬ NHỎ. NHÌN THỰC TẾ. SỬA.
**Principle:** Không phải học khi nào không cần hỏi nữa. Mà là khi nào có thể hành động mà không cần giả vờ rằng mọi câu hỏi đã được giải quyết.
**Anti-pattern:** Big-bang refactor.

## 19. Tầng kiểm toán bằng chứng
**Title:** Cơ chế tạo ra bằng chứng có khả năng nhìn thấy thứ cần nhìn thấy không?
**Principle:** Không chỉ "bằng chứng chưa đủ" mà "khả năng quan sát chưa đủ".
**Anti-pattern:** Tin scanner 100% mà không hỏi scanner mù gì.

## 20. Không kiểm tra vô hạn
**Title:** Chỉ cần biết công cụ có thể sai — không cần hiểu từng nguyên tử
**Principle:** Chỉ cần biết nó có thể sai không, sai bao nhiêu, kiểm tra bằng cách nào khác.
**Anti-pattern:** Paralysis bằng analysis — đòi proof tuyệt đối.

## 21. Không tin một tác nhân
**Title:** Tin vào quá trình có khả năng phát hiện khi chính nó sai
**Principle:** Nếu hệ thống trở thành thứ mọi người mặc định tin vì "được thiết kế để chống sai" thì nó đã thất bại.
**Anti-pattern:** Cult of the system — tin vô điều kiện.

## 22. PASS ≠ TRUE
**Title:** Một quy trình chống tự lừa dối cũng có thể bị dùng để tạo ra bằng chứng rằng chúng ta không tự lừa dối
**Principle:** Goodhart's Law. PASS chỉ có nghĩa: "không phát hiện lỗi trong phạm vi kiểm tra hiện tại với bằng chứng hiện tại."
**Anti-pattern:** Round N PASS → tưởng xong → không audit Round N+1.

## 23. Quay về điểm bắt đầu
**Title:** KHÔNG HOÀN THIỆN. KHÔNG THẤT BẠI. KHÔNG HOÀN TẤT. ĐANG HOẠT ĐỘNG.
**Principle:** Chuyển từ "TÌM CÂU TRẢ LỜI" sang "XÂY MỘT QUÁ TRÌNH CÓ KHẢ NĂNG SỬA CÂU TRẢ LỜI KHI THỰC TẾ CHỨNG MINH NÓ SAI."
**Anti-pattern:** Tuyên bố "done" và ngừng audit.

## 24. Đứa trẻ 20 năm sau
**Title:** Tại sao? — câu hỏi mở
**Principle:** Mỗi thế hệ kế thừa phải có khả năng đặt câu hỏi mới.
**Anti-pattern:** Audit trở thành ritual lặp lại.

## 25. Câu hỏi SCP không nghĩ ra
**Title:** SCP có câu hỏi nào mà SCP không thể nghĩ ra không?
**Principle:** KHÔNG THỂ CHỨNG MINH RẰNG KHÔNG CÒN MISSING PIECE.
**Anti-pattern:** Claim "no bugs remaining".

## 26. Reality có quyền cuối cùng
**Title:** DUY TRÌ KHẢ NĂNG ĐỂ THỰC TẾ BUỘC HỆ THỐNG NHẬN RA RẰNG NÓ ĐÃ BỎ SÓT ĐIỀU GÌ ĐÓ
**Principle:** Mục tiêu KHÔNG PHẢI trở thành hệ thống biết tất cả. Mục tiêu là duy trì khả năng để Reality buộc hệ thống nhận ra missing piece. Reality giữ quyền trả lời cuối cùng.
**Anti-pattern:** Hệ thống tự tuyên bố đúng.

## 27. Đào thải độc chất (Knowledge Quarantine)
**Title:** Không có sự thật nào an toàn tuyệt đối khi đến từ bên ngoài
**Principle:** Tri thức ngoại lai (Internet, GitHub) phải được đối xử như dữ liệu nhiễm độc. Phải qua quá trình cách ly (Quarantine), trích xuất logic và loại bỏ mã thực thi trước khi nạp vào Não bộ. Không nạp nguyên bản (raw data).
**Anti-pattern:** Tin tưởng tuyệt đối và học thẳng từ một README có 50,000 stars mà không qua bộ lọc.

## 28. Trí nhớ không phá hủy (Catastrophic Forgetting Guard)
**Title:** Học cái mới không được phép đè bẹp hệ miễn dịch cũ
**Principle:** Sự tiến hóa (Autofix, Learning) phải đảm bảo không phá vỡ các rào cản bảo mật đã thiết lập (Tier-1 Guard, Capability, Egress). Blast Radius của sự tiến hóa phải được kiểm soát bằng snapshot và rollback.
**Anti-pattern:** Xóa bỏ hàm kiểm duyệt bảo mật chỉ để code chạy nhanh hơn hoặc pass unit test.

## 29. Sự tự chủ phân tán (Distributed Autonomy)
**Title:** SCP tự audit SCP thông qua các hệ đối trọng không cùng huyết thống
**Principle:** "External Reviewer" không nhất thiết là con người. Sự tự chủ được hình thành từ một xã hội các Subsystem độc lập (Planner, Judge, Kernel) phản biện và phủ quyết lẫn nhau dựa trên bằng chứng toán học và mật mã học.
**Anti-pattern:** Gom tất cả các role (Lên kế hoạch, Thực thi, Đánh giá) vào cùng một LLM duy nhất để nó tự duyệt bài của chính mình.
