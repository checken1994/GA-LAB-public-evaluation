"""
Tier-1 Deterministic Guard — chốt chặn cứng TRƯỚC mọi LLM (Cổng D).

TẠI SAO: Audit Cổng D chỉ ra RealityJudge (LLM) là điểm lệ thuộc xác suất.
Kiến trúc TOP 1% yêu cầu lớp verification DETERMINISTIC chạy trước trong
~1ms: các cấu trúc SAI một cách cơ học phải bị chém ngay, không tốn một
token LLM nào, không bao giờ hallucinate. LLM (Tier-2) chỉ còn phải phán
giá các vấn đề ngữ nghĩa.

Checks (thuần cấu trúc, không ngữ nghĩa, không mạng, không model):
  1. REJECT_EMPTY      — answer rỗng/whitespace
  2. REJECT_OVERLENGTH — vượt trần ký tự (DoS / prompt-stuffing)
  3. REJECT_CONTROL_CHARS — ký tự điều khiển/zero-width (lạm dụng tokenizer)
  4. REJECT_INTERNAL_MARKER — leak marker nội bộ [SCP: ...] ra client
  5. REJECT_GROUNDING  — RAG ask: candidate chứa chi tiết ngoài evidence context

Fail-closed: mọi check sai → REJECT với reason máy đọc được.
PASSED tier-1 KHÔNG có nghĩa là đúng — nó chỉ có nghĩa "không sai cấu trúc";
quyết định ngữ nghĩa vẫn thuộc Tier-2 (judge + governance).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

MAX_ANSWER_CHARS = 8_000
MAX_QUESTION_CHARS = 16_000
# zero-width + bidi override controls dùng để qua mặt tokenizer/filter
_SUSPECT_CHARS_RE = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\u2060\ufeff]")
_INTERNAL_MARKER_RE = re.compile(r"\[SCP:|\[ESCALATE|\[KERNEL")
_WHITESPACE_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[\wàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]{2,}", re.UNICODE)


@dataclass
class Tier1Result:
    passed: bool
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "failures": list(self.failures)}


def check_structure(question: str, answer: str) -> Tier1Result:
    """Deterministic structural gate. O(len) — microseconds."""
    failures: list[str] = []
    if not isinstance(answer, str) or not answer.strip():
        failures.append("REJECT_EMPTY")
    else:
        if len(answer) > MAX_ANSWER_CHARS:
            failures.append("REJECT_OVERLENGTH")
        if _SUSPECT_CHARS_RE.search(answer):
            failures.append("REJECT_CONTROL_CHARS")
        if _INTERNAL_MARKER_RE.search(answer):
            failures.append("REJECT_INTERNAL_MARKER")
    if isinstance(question, str) and len(question) > MAX_QUESTION_CHARS:
        failures.append("REJECT_QUESTION_OVERLENGTH")
    return Tier1Result(passed=not failures, failures=failures)


def _content_words(text: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(_WHITESPACE_RE.sub(" ", text or ""))}


def check_grounding(answer: str, context: str, min_overlap: float = 0.6) -> Tier1Result:
    """RAG evidence binding: candidate phải được đỡ bởi evidence context.

    Đo bằng tỉ lệ content-words của answer xuất hiện trong context (bất biến
    với biến đổi hình thái đơn giản nhất). < min_overlap → REJECT_GROUNDING.
    Khi context rỗng (chat ask) check này không áp dụng → passed.
    """
    ctx_words = _content_words(context)
    if not ctx_words:
        return Tier1Result(passed=True, failures=[])
    ans_words = _content_words(answer)
    if not ans_words:
        return Tier1Result(passed=False, failures=["REJECT_EMPTY"])
    overlap = sum(1 for w in ans_words if w in ctx_words) / len(ans_words)
    if overlap < min_overlap:
        return Tier1Result(passed=False, failures=[f"REJECT_GROUNDING({overlap:.2f})"])
    return Tier1Result(passed=True, failures=[])


def check(question: str, answer: str, context: str = "") -> Tier1Result:
    """Full Tier-1: structural luôn chạy; grounding chỉ khi có evidence."""
    result = check_structure(question, answer)
    if result.passed and (context or "").strip():
        grounding = check_grounding(answer, context)
        if not grounding.passed:
            result.failures.extend(grounding.failures)
            result.passed = False
    return result
