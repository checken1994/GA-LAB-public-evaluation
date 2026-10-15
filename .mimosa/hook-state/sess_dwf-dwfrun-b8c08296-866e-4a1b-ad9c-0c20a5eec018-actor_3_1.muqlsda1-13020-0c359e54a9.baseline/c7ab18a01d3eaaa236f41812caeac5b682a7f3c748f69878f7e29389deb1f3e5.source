/**
 * SCP DNA — 26 nguyên tắc cốt lõi (separate file per task)
 *
 * Nguồn: SCP_CAU_CHUYEN_GA_TAI_SAO_CONTINUITY_ARCHIVE.md
 *
 * Mỗi nguyên tắc là một "missing piece" mà SCP đã phát hiện qua 13+ năm
 * phát triển. Round 7 audit dùng các nguyên tắc này làm compass.
 */

export interface DnaPrinciple {
  id: number
  shortName: string
  title: string
  principle: string
  antiPattern: string
  round7Application: string
  emoji: string
}

export const SCP_DNA: DnaPrinciple[] = [
  {
    id: 1,
    shortName: "Hỏi Tại sao",
    title: "Bắt đầu bằng câu hỏi, không phải giải pháp",
    principle:
      "Không bắt đầu bằng giải pháp. Bắt đầu từ vấn đề → hỏi Tại sao → tìm giả định → tìm bằng chứng → phát hiện missing piece → thiết kế → thử → audit → sửa.",
    antiPattern: "Nhảy thẳng đến code fix mà không hiểu root cause.",
    round7Application: "Mỗi bug R7 phải trả lời 5 lần 'Tại sao?' trước khi fix.",
    emoji: "❓",
  },
  {
    id: 2,
    shortName: "Vòng lặp khép kín",
    title: "Vòng lặp thay đổi hệ thống có thể khép kín",
    principle:
      "GỌI LLM + ĐỌC SOURCE + PHÁT HIỆN + SINH CODE + GHI/SỬA + CHẠY + KIỂM TRA + ĐIỀU KHIỂN RUNTIME + TẠO PROCESS = vòng lặp có thể khép kín.",
    antiPattern: "Fix code nhưng không chạy lại để verify.",
    round7Application: "Mỗi fix R7 phải chạy Reality test (import + exercise) sau khi apply.",
    emoji: "🔄",
  },
  {
    id: 3,
    shortName: "Câu hỏi tối hậu",
    title: "Có thứ gì mà chuỗi 'Tại sao?' không được phép biến thành đối tượng cần xem xét?",
    principle:
      "Trong SCP có tồn tại bất kỳ thứ gì mà chính chuỗi 'Tại sao?' không được phép biến thành một đối tượng cần xem xét và thay đổi hay không?",
    antiPattern: "Coi scanner/autofix chính SCP là vùng cấm audit.",
    round7Application: "R7 audit cả chính 18 scanners của SCP — không miễn trừ gì cả.",
    emoji: "🎯",
  },
  {
    id: 4,
    shortName: "Con người quyết định",
    title: "SCP tìm chỗ sai. Con người quyết định.",
    principle:
      "SCP không có quyền phê duyệt quyết định cuối cùng. SCP tìm lỗi, đề xuất fix, con người quyết định có apply không.",
    antiPattern: "SCP tự động apply fix thay đổi logic verdict.",
    round7Application:
      "Tier-3 bugs (logic) luôn require human approval, kể cả khi SCP_AUTO_APPROVE_TIER3=1.",
    emoji: "👤",
  },
  {
    id: 5,
    shortName: "Ảo giác đồng thuận",
    title: "Không tin một tác nhân. Tin vào quá trình có khả năng phát hiện khi chính nó sai.",
    principle:
      "10 tờ báo đưa cùng tin không phải 10 nguồn — nếu cùng sao chép từ 1 nguồn thì chỉ là 1 lineage. 100 AI cùng kết luận chưa chắc 100 nguồn độc lập.",
    antiPattern: "Tin R6 PASS vì 6 nguồn đều PASS.",
    round7Application:
      "R7 chạy ĐỘC LẬP — không đọc R6 kết luận trước, chỉ dùng same 6 sources + thêm nguồn thứ 7 (property-based testing).",
    emoji: "🎭",
  },
  {
    id: 6,
    shortName: "Gốc tin cậy bên ngoài",
    title: "Quyền cấp capability phải nằm ngoài miền hệ thống có thể tự sửa",
    principle:
      "Miền nhận thức / Gốc tin cậy bên ngoài / Miền thực thi (sandbox, rollback, audit log). Hệ thống bên trong không có quyền sửa gốc tin cậy.",
    antiPattern: "Autofix tự sửa classifier để tự nâng tier.",
    round7Application: "R7 kiểm tra classifier không bị autofix sửa trong chu kỳ audit.",
    emoji: "🏛️",
  },
  {
    id: 7,
    shortName: "Autofix an toàn",
    title: "6 safety guards cho autofix kể cả khi auto-approve ON",
    principle:
      "1. RELAXATION patterns KHÔNG bao giờ auto. 2. Rate limit. 3. Auto-timeout. 4. Audit log riêng. 5. Backup file. 6. Cooldown 1h cho cùng bug.",
    antiPattern: "Autofix vô hạn, không rate limit, không cooldown.",
    round7Application: "R7 thêm guard thứ 7: cross-file vulture verify trước khi Tier-2 fix.",
    emoji: "🛡️",
  },
  {
    id: 8,
    shortName: "KB accumulation",
    title: "Audit trail lưu lại mọi quyết định autofix",
    principle:
      "Mỗi auto-approve → data/tier3_auto_audit.jsonl. SCP hiểu quyền được cấp (không chỉ đọc env var).",
    antiPattern: "Fix không log, không audit, không rollback được.",
    round7Application:
      "R7 audit log có schema mới: before_hash, after_hash, reality_test_result, rollback_token.",
    emoji: "📚",
  },
  {
    id: 9,
    shortName: "No harm",
    title: "Fix phải có non-fatal guards — nếu fail thì fail-open",
    principle:
      "Mỗi fix có try/except + fallback. Không để fix mới gây regression.",
    antiPattern: "Fix raise Exception → crash toàn pipeline.",
    round7Application: "R7 mỗi fix có guard 'if X is not None and callable(X)' trước khi gọi.",
    emoji: "🩹",
  },
  {
    id: 10,
    shortName: "Hội đồng đa hệ thống",
    title: "SCP: Còn thiếu gì? META: Có cần làm không? Thứ 3: Có cách khác không?",
    principle:
      "Ba hệ thống đối trọng: SCP (tìm missing piece) / SCP-META (đặt lại vấn đề) / Hệ thống thứ 3 (tìm phương án khác). Bộ đánh giá hậu quả.",
    antiPattern: "Một scanner duy nhất quyết định fix.",
    round7Application: "R7 mỗi bug phải pass 2/3: AST scanner + external tool + semantic intent.",
    emoji: "⚖️",
  },
  {
    id: 11,
    shortName: "Human-in-the-loop thật",
    title: "Con người có thực sự hiểu điều mình đang phê duyệt không?",
    principle:
      "Không chỉ hỏi 'đã bấm phê duyệt chưa?' mà hỏi 'con người có hiểu không?'. Nếu không hiểu → không được phê duyệt.",
    antiPattern: "Rubber-stamp approval.",
    round7Application: "R7 Tier-3 fix hiển thị diff + giải thích TẠI SAO + hậu quả + rollback plan.",
    emoji: "🧠",
  },
  {
    id: 12,
    shortName: "Nghịch lý thử-hiểu",
    title: "Phải thử mới hiểu, nhưng phải hiểu mới được thử",
    principle:
      "Cần hiểu → mới được thử, nhưng cần thử → mới có thể hiểu đủ. Phá vòng lặp: sandbox → giới hạn capability → quan sát → tăng mức hiểu → mở rộng từng bước.",
    antiPattern: "Đợi 'hiểu đủ' mãi mãi, không bao giờ chạy.",
    round7Application: "R7 chạy trên snapshot read-only + dry-run mode trước khi apply thật.",
    emoji: "🔁",
  },
  {
    id: 13,
    shortName: "Không đứng số một",
    title: "Nếu hệ thống khác tốt hơn thật thì dùng nó",
    principle:
      "Tiếp tục dùng SCP chỉ để duy trì vị trí SCP sẽ mâu thuẫn với 'Thực tế > Mô hình'. Không hỏi 'hệ thống nào tốt hơn' mà hỏi 'phù hợp hơn với loại vấn đề nào'.",
    antiPattern: "Not-Invented-Here syndrome.",
    round7Application: "R7 dùng ruff/pyflakes/pylint/vulture/mypy/bandit — không tự viết lại.",
    emoji: "🤝",
  },
  {
    id: 14,
    shortName: "Đồng thuận ≠ đúng",
    title: "Ba hệ thống đồng ý vì cùng chia sẻ giả định sai thì sao?",
    principle:
      "Đa số đồng ý = khả năng đúng cao hơn CHƯA được chứng minh. Cần góc nhìn không cùng lineage + đánh giá đối kháng + kiểm tra độc lập thực sự.",
    antiPattern: "Vote đa số scanner để quyết định fix.",
    round7Application:
      "R7 track lineage của mỗi scanner (rust AST vs Python AST vs astroid vs type-inference) — chỉ tin cross-lineage agreement.",
    emoji: "🗳️",
  },
  {
    id: 15,
    shortName: "Gà Lab bị audit",
    title: "Gà Lab tồn tại vì bằng chứng hay vì quán tính thể chế?",
    principle:
      "SCP không thể là trọng tài duy nhất vì SCP là sản phẩm của Gà Lab. Thử nghiệm đối chứng: nhóm độc lập xây nhiều giải pháp hơn, Gà Lab xây ít hơn nhưng phát hiện vấn đề đặt sai.",
    antiPattern: "SCP tự audit SCP mà không có external reviewer.",
    round7Application:
      "R7 so sánh SCP's own 18 scanners với 6 external tools — đo recall/precision từng bên.",
    emoji: "🔍",
  },
  {
    id: 16,
    shortName: "Học nói phạm vi",
    title: "Chỉ dùng dữ liệu được phép — không tự vượt quyền",
    principle:
      "Chỉ dùng dữ liệu cung cấp / nguồn công khai / nguồn được phép. Không đủ bằng chứng → báo không đủ. Không tự mở rộng capability. Không tự sửa boundary.",
    antiPattern: "Autofix sửa file ngoài scope.",
    round7Application: "R7 scope giới hạn scp/ directory — không đụng tests/, scripts/, dashboard/.",
    emoji: "🚧",
  },
  {
    id: 17,
    shortName: "Hành động khi chưa biết hết",
    title: "Khi nào có thể hành động mà không cần giả vờ mọi câu hỏi đã giải quyết?",
    principle:
      "Hành động nhỏ + đảo ngược được + quan sát được + hậu quả giới hạn → thử được. Hành động lớn + khó đảo ngược + hậu quả rộng + bằng chứng yếu → hỏi nhiều hơn.",
    antiPattern: "Apply toàn bộ fix batch mà không rollback plan.",
    round7Application: "R7 fix theo nhóm nhỏ (≤5 bug/nhóm), mỗi nhóm có checkpoint rollback.",
    emoji: "📈",
  },
  {
    id: 18,
    shortName: "Khẩu hiệu Gà Lab",
    title: "HỎI. THỬ NHỎ. NHÌN THỰC TẾ. SỬA.",
    principle:
      "Không phải học khi nào không cần hỏi nữa. Mà là khi nào có thể hành động mà không cần giả vờ rằng mọi câu hỏi đã được giải quyết.",
    antiPattern: "Big-bang refactor.",
    round7Application: "R7 iterate: audit 1 module → fix → reality test → audit module tiếp.",
    emoji: "🐔",
  },
  {
    id: 19,
    shortName: "Tầng kiểm toán bằng chứng",
    title: "Cơ chế tạo ra bằng chứng có khả năng nhìn thấy thứ cần nhìn thấy không?",
    principle:
      "Không chỉ 'bằng chứng chưa đủ' mà 'khả năng quan sát chưa đủ'. Camera sai giờ, cảm biến lỗi, file bị sửa, phần mềm đọc sai, dữ liệu chỉ quan sát 10/100 biến.",
    antiPattern: "Tin scanner 100% mà không hỏi scanner mù gì.",
    round7Application:
      "R7 map blind-spot của từng scanner: ruff mù cross-module, mypy mù runtime, vulture mù dynamic dispatch.",
    emoji: "👁️",
  },
  {
    id: 20,
    shortName: "Không kiểm tra vô hạn",
    title: "Chỉ cần biết công cụ có thể sai — không cần hiểu từng nguyên tử",
    principle:
      "Ví dụ cái cân: không cần hiểu từng nguyên tử. Chỉ cần biết nó có thể sai không, sai bao nhiêu, kiểm tra bằng cách nào khác, nếu kết quả quan trọng thì có nên đo lại không.",
    antiPattern: "Paralysis bằng analysis — đòi proof tuyệt đối.",
    round7Application: "R7 dừng sau 3 nguồn cross-validate — không chạy vô hạn scanner.",
    emoji: "⚖️",
  },
  {
    id: 21,
    shortName: "Không tin một tác nhân",
    title: "Tin vào quá trình có khả năng phát hiện khi chính nó sai",
    principle:
      "Nếu SCP trở thành thứ mọi người mặc định tin vì 'SCP được thiết kế để chống sai' thì SCP đã thất bại. SCP cũng là mô hình, cũng có implementation, cũng có dữ liệu, cũng có giới hạn quan sát.",
    antiPattern: "Cult of SCP — tin SCP vô điều kiện.",
    round7Application: "R7 audit cả chính SCP autofix engine — tìm bug trong bug-finder.",
    emoji: "🚫",
  },
  {
    id: 22,
    shortName: "PASS ≠ TRUE",
    title: "Một quy trình chống tự lừa dối cũng có thể bị dùng để tạo ra bằng chứng rằng chúng ta không tự lừa dối",
    principle:
      "Goodhart: khi thước đo trở thành mục tiêu, nó không còn là thước đo tốt. PASS chỉ có nghĩa: 'không phát hiện lỗi trong phạm vi kiểm tra hiện tại với bằng chứng hiện tại.'",
    antiPattern: "Round N PASS → tưởng xong → không audit Round N+1.",
    round7Application: "R7 EXPLICITLY không tin R3-R6 PASS — chạy lại từ đầu với chiều sâu hơn.",
    emoji: "⚡",
  },
  {
    id: 23,
    shortName: "Quay về điểm bắt đầu",
    title: "KHÔNG HOÀN THIỆN. KHÔNG THẤT BẠI. KHÔNG HOÀN TẤT. ĐANG HOẠT ĐỘNG.",
    principle:
      "Chuyển từ 'TÌM CÂU TRẢ LỜI' sang 'XÂY MỘT QUÁ TRÌNH CÓ KHẢ NĂNG SỬA CÂU TRẢ LỜI KHI THỰC TẾ CHỨNG MINH NÓ SAI.' Nếu một ngày tuyên bố không còn gì cần kiểm tra, đó là lúc cần kiểm tra nhiều nhất.",
    antiPattern: "Tuyên bố 'done' và ngừng audit.",
    round7Application: "R7 kết luận bằng 'các câu hỏi tiếp' chứ không phải 'PASS'.",
    emoji: "♾️",
  },
  {
    id: 24,
    shortName: "Đứa trẻ 20 năm sau",
    title: "Tại sao? — câu hỏi mở",
    principle:
      "Một đứa trẻ hỏi 'Tại sao?' — màn hình SCP cũ sáng lên: PHÁT HIỆN CÂU HỎI MỚI. Mỗi thế hệ kế thừa phải có khả năng đặt câu hỏi mới.",
    antiPattern: "Audit trở thành ritual lặp lại.",
    round7Application: "R7 thêm nguồn thứ 7 (property-based testing) — câu hỏi mới không được R3-R6 đặt.",
    emoji: "🧒",
  },
  {
    id: 25,
    shortName: "Câu hỏi SCP không nghĩ ra",
    title: "SCP có câu hỏi nào mà SCP không thể nghĩ ra không?",
    principle:
      "Nếu tôi biết thì nó không còn là câu hỏi mà tôi không thể nghĩ ra. KHÔNG THỂ CHỨNG MINH RẰNG KHÔNG CÒN MISSING PIECE. KHÔNG THỂ QUAN SÁT TRỰC TIẾP NHỮNG GÌ NẰM NGOÀI KHẢ NĂNG TẠO CÂU HỎI HIỆN TẠI.",
    antiPattern: "Claim 'no bugs remaining'.",
    round7Application:
      "R7 acknowledge: bugs ngoài capability quan sát hiện tại không nhìn thấy. Cần nguồn thứ 8+ (fuzzing, runtime trace).",
    emoji: "🌌",
  },
  {
    id: 26,
    shortName: "Reality có quyền cuối cùng",
    title: "DUY TRÌ KHẢ NĂNG ĐỂ THỰC TẾ BUỘC HỆ THỐNG NHẬN RA RẰNG NÓ ĐÃ BỎ SÓT ĐIỀU GÌ ĐÓ",
    principle:
      "Mục tiêu KHÔNG PHẢI trở thành hệ thống biết tất cả. Mục tiêu là duy trì khả năng để Reality buộc hệ thống nhận ra missing piece. Reality giữ quyền trả lời cuối cùng.",
    antiPattern: "Hệ thống tự tuyên bố đúng.",
    round7Application:
      "R7 Reality test: import + exercise + cross-file vulture post-fix. Reality > Model.",
    emoji: "🌍",
  },
]

export const DNA_BY_ID = Object.fromEntries(SCP_DNA.map((d) => [d.id, d]))

export function getDnaPrinciple(id: number): DnaPrinciple | undefined {
  return DNA_BY_ID[id]
}
