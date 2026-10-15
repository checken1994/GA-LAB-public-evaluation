"""
LAYER 3: COUNTER QUESTION ENGINE — đổi câu hỏi, không đổi data.

Counter-Question — phản biện bằng cách THAY ĐỔI câu hỏi.

Khác CounterExample (thay đổi data/input):
    CounterExample: "2+3=5" → test "1/0" (đổi input)
    CounterQuestion: "2+3=5" → "Trong số nguyên hay số phức?" (đổi framing)

Types of reframing:
    - domain_specification: "Trong hệ nào?" (số nguyên/modulo/phức)
    - temporal: "Khi nào?" (hiện tại/lịch sử/tương lai)
    - scope: "Ở đâu?" (exchange/location/jurisdiction)
    - assumption: "Giả sử gì?" (định nghĩa/đơn vị/phương pháp)

Extracted from `meta/cognitive_engine.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("scp.cognitive")


@dataclass
class CounterQuestion:
    """Một counter-question — thay đổi framing của câu hỏi."""
    original_question: str
    counter_question: str
    reframing_type: str      # "domain_specification", "temporal", "scope", "assumption"
    why_it_matters: str      # Tại sao câu hỏi này quan trọng?
    potential_to_invalidate: bool  # Có thể invalid claim không?


class CounterQuestionEngine:
    """
    Counter-Question — phản biện bằng cách THAY ĐỔI câu hỏi.

    Khác CounterExample (thay đổi data/input):
        CounterExample: "2+3=5" → test "1/0" (đổi input)
        CounterQuestion: "2+3=5" → "Trong số nguyên hay số phức?" (đổi framing)

    Types of reframing:
        - domain_specification: "Trong hệ nào?" (số nguyên/modulo/phức)
        - temporal: "Khi nào?" (hiện tại/lịch sử/tương lai)
        - scope: "Ở đâu?" (exchange/location/jurisdiction)
        - assumption: "Giả sử gì?" (định nghĩa/đơn vị/phương pháp)
    """

    # Reframing patterns per domain
    REFRAMING_PATTERNS = {
        "math": [
            ("domain_specification", "Trong số nguyên hay số thực?", "Kết quả khác nhau cho division"),
            ("domain_specification", "Trong modulo bao nhiêu?", "Kết quả thay đổi theo modulo"),
            ("assumption", "Có xét đến overflow không?", "Integer overflow thay đổi kết quả"),
        ],
        "finance": [
            ("scope", "Ở exchange nào?", "Giá khác nhau giữa exchanges"),
            ("temporal", "Tại thời điểm nào?", "Giá thay đổi từng giây"),
            ("assumption", "Đã bao gồm phí giao dịch chưa?", "Net price ≠ spot price"),
        ],
        "weather": [
            ("temporal", "Nhiệt độ hiện tại hay trung bình ngày?", "Current ≠ daily avg"),
            ("scope", "Ở trạm khí tượng nào?", "Different stations, different temps"),
            ("assumption", "Độ cao bao nhiêu so với mực nước biển?", "Temperature varies with altitude"),
        ],
        "geography": [
            ("temporal", "Thủ đô hiện tại hay lịch sử?", "Capitals change over time"),
            ("assumption", "Theo định nghĩa chính trị hay hành chính?", "Different definitions"),
        ],
        "chemistry": [
            ("assumption", "Phân tử lượng của dạng nào? (anhydrous/hydrate)", "Different forms, different MW"),
            ("assumption", "Đơn vị là g/mol hay Dalton?", "Same value, different units"),
        ],
        "history": [
            ("temporal", "Theo lịch nào? (Dương lịch/Âm lịch)", "Different calendars, different dates"),
            ("assumption", "Theo nguồn nào? (Chính thức/dân gian)", "Different sources, different accounts"),
        ],
        "reality": [
            ("assumption", "Trong chân không hay trong môi trường?", "Speed of light varies by medium"),
            ("temporal", "Giá trị CODATA năm nào?", "Constants get refined over time"),
        ],
        "biology": [
            ("scope", "Ở người hay ở loài khác?", "Chromosome count varies by species"),
            ("assumption", "Định nghĩa 'nhiệt độ cơ thể' ở đâu đo?", "Core vs surface temperature"),
        ],
        "logic": [
            ("domain_specification", "So sánh số nguyên hay float?", "1.0 == 1 is True for float, type-dependent"),
        ],
        "statistics": [
            ("assumption", "Mean là arithmetic hay geometric?", "Different formulas, different results"),
            ("assumption", "Population hay sample statistics?", "Different denominator (N vs N-1)"),
        ],
        "astronomy": [
            ("temporal", "Giá trị theo epoch nào? (J2000, J2050)", "Planetary positions change over epochs"),
            ("assumption", "Khối lượng riêng trung bình hay tại bề mặt?", "Different measurements, different values"),
        ],
        #  V46 domains — new reframing patterns
        "medical": [
            ("temporal", "Hướng dẫn điều trị năm nào? (y văn cập nhật liên tục)", "Outdated guidelines may be wrong"),
            ("scope_narrowing", "Liều cho người trưởng thành hay trẻ em?", "Dosage differs by age/weight"),
            ("assumption_challenging", "Có chống chỉ định với bệnh nhân không?", "Same drug, different contraindications"),
        ],
        "technology": [
            ("temporal", "Phiên bản công nghệ nào? (frameworks change fast)", "API changes between versions"),
            ("scope_narrowing", "Ngôn ngữ/platform nào cụ thể?", "Same concept, different implementations"),
            ("assumption_challenging", "Production hay development environment?", "Defaults differ by environment"),
        ],
        "sports": [
            ("temporal", "Kỷ lục năm nào? (có thể đã bị phá)", "Records get broken over time"),
            ("scope_narrowing", "Giải đấu nào? (Olympic, World Cup, regional)", "Different tournaments, different records"),
            ("assumption_challenging", "Theo thể thức cũ hay mới?", "Rules change between tournaments"),
        ],
        "legal": [
            ("temporal", "Luật phiên bản nào? (luật được sửa đổi)", "Amended laws supersede old versions"),
            ("scope_narrowing", "Áp dụng ở quốc gia/jurisdiction nào?", "Same act, different countries, different rules"),
            ("assumption_challenging", "Còn hiệu lực hay đã hết hạn?", "Laws can be repealed or expire"),
        ],
        "arts": [
            ("temporal", "Tác phẩm thời kỳ nào của tác giả?", "Artist style evolves over career"),
            ("scope_narrowing", "Attribution theo catalog nào? (catalogue raisonné)", "Different catalogs, different attributions"),
            ("assumption_challenging", "Tác phẩm gốc hay bản sao?", "Copies exist for famous works"),
        ],
    }

    def generate_counter_questions(self, question: str, domain: str) -> list[CounterQuestion]:
        """Generate counter-questions for a claim."""
        patterns = self.REFRAMING_PATTERNS.get(domain, [])
        results = []

        for reframing_type, counter_q, why in patterns:
            results.append(CounterQuestion(
                original_question=question,
                counter_question=counter_q,
                reframing_type=reframing_type,
                why_it_matters=why,
                potential_to_invalidate=True,  # All counter-questions can potentially invalidate
            ))

        #  If ≥2 counter-questions suggest ambiguity, enqueue for auto-verify
        # Ambiguity = scope_narrowing AND assumption_challenging both present
        ambiguity_types = {r.reframing_type for r in results}
        if "scope_narrowing" in ambiguity_types and "assumption_challenging" in ambiguity_types:
            self._enqueue_for_reverification(question, domain, results)

        return results

    def _enqueue_for_reverification(self, question: str, domain: str,
                                     counter_questions: list[CounterQuestion]):
        """ When ambiguity detected, enqueue question for re-verification queue.

        CuriosityAsker can pick this up and re-ask the question with different framings
        to actively probe for the truth, instead of just downgrading verdict.
        """
        try:
            from scp.core.db_manager import db_exec, init_db
            init_db()
            db_exec("""
                CREATE TABLE IF NOT EXISTS pending_reverification (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    question TEXT,
                    domain TEXT,
                    counter_questions TEXT,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0
                )
            """)
            import json as _json
            from datetime import datetime
            ts = datetime.now().astimezone().isoformat()
            cqs_json = _json.dumps([
                {"question": cq.counter_question, "type": cq.reframing_type, "why": cq.why_it_matters}
                for cq in counter_questions
            ], ensure_ascii=False)
            db_exec(
                "INSERT INTO pending_reverification (timestamp, question, domain, counter_questions) "
                "VALUES (?, ?, ?, ?)",
                (ts, question[:500], domain, cqs_json)
            )
            logger.info(f"[CounterQuestion V50] Ambiguity detected — enqueued for re-verification: '{question[:50]}'")
        except Exception as e:
            logger.debug(f"CounterQuestion enqueue error: {e}", exc_info=True)
