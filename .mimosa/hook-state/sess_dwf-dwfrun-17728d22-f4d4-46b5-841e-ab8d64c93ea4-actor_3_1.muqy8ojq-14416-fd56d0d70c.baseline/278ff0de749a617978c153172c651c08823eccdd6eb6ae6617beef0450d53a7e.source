"""
scp/core/postcondition_schema.py
=================================
Shared PostconditionSchema — contract giữa builder (judge) và consumer (verifier).

DNA #14 — Đồng thuận ≠ đúng: hai module phải chia sẻ cùng schema thật sự, không ngầm định.
DNA #19 — Missing piece: schema này trước đây không tồn tại → format mismatch luôn FAIL.

Quy tắc:
  - Judge dùng build_*() để tạo postcondition.
  - Verifier dùng validate_schema() để kiểm tra input trước khi xử lý.
  - Không module nào được tự định nghĩa format riêng trong code.

Format hợp lệ:
  {
    "all": [                          # danh sách điều kiện AND
      {"kind": "text_contains",   "value": "..."},   # text chứa value
      {"kind": "url_matches",     "value": "..."},   # URL khớp chính xác
      {"kind": "artifact_hash",   "value": "..."},   # hash khớp
      {"kind": "network_response","method": "POST", "status": 200},
    ],
    "evidence_required": True,        # optional: bắt buộc phải có evidence_ref
  }
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# =============================================================================
# Các condition kinds được hỗ trợ
# =============================================================================

ConditionKind = Literal["text_contains", "url_matches", "artifact_hash", "network_response"]

VALID_KINDS: frozenset[str] = frozenset(
    ["text_contains", "url_matches", "artifact_hash", "network_response"]
)


@dataclass(frozen=True)
class PostconditionCondition:
    """Một điều kiện trong postcondition — immutable để tránh accidental mutation."""
    kind: str
    value: str = ""
    method: str = ""   # chỉ dùng cho network_response
    status: int = 0    # chỉ dùng cho network_response

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"kind": self.kind}
        if self.value:
            d["value"] = self.value
        if self.method:
            d["method"] = self.method
        if self.status:
            d["status"] = self.status
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PostconditionCondition:
        return cls(
            kind=d.get("kind", ""),
            value=d.get("value", ""),
            method=d.get("method", ""),
            status=int(d.get("status", 0)),
        )


@dataclass
class PostconditionSchema:
    """
    PostconditionSchema — schema chính thức cho toàn hệ thống.
    Builder tạo bằng class methods này, verifier nhận dict qua to_dict().
    """
    conditions: list[PostconditionCondition] = field(default_factory=list)
    evidence_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Chuyển sang dict format mà IndependentVerifier.verify() hiểu."""
        return {
            "all": [c.to_dict() for c in self.conditions],
            "evidence_required": self.evidence_required,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PostconditionSchema:
        """Parse dict → PostconditionSchema. Dùng trong verifier để validate input."""
        conditions = [
            PostconditionCondition.from_dict(c)
            for c in (d.get("all") or [])
            if isinstance(c, dict)
        ]
        return cls(
            conditions=conditions,
            evidence_required=bool(d.get("evidence_required", False)),
        )

    @classmethod
    def for_text_answer(cls, expected_answer: str, evidence_required: bool = True) -> PostconditionSchema:
        """
        Builder cho trường hợp phổ biến nhất: kiểm tra AI trả lời đúng text.
        
        Args:
            expected_answer: câu trả lời kỳ vọng (substring match)
            evidence_required: có cần evidence_ref không
        """  # noqa: W291,W293  # [hygiene-keep] whitespace inside string/docstring - keep content verbatim
        if not expected_answer:
            return cls(conditions=[], evidence_required=False)
        return cls(
            conditions=[PostconditionCondition(kind="text_contains", value=expected_answer[:500])],
            evidence_required=evidence_required,
        )

    @classmethod
    def for_url_navigation(cls, expected_url: str) -> PostconditionSchema:
        """Builder cho browser navigation — kiểm tra URL đích."""
        return cls(
            conditions=[PostconditionCondition(kind="url_matches", value=expected_url)],
            evidence_required=True,
        )

    @classmethod
    def for_artifact(cls, expected_hash: str) -> PostconditionSchema:
        """Builder cho file artifact — kiểm tra hash."""
        return cls(
            conditions=[PostconditionCondition(kind="artifact_hash", value=expected_hash)],
            evidence_required=True,
        )

    @classmethod
    def no_conditions(cls) -> PostconditionSchema:
        """Không có điều kiện cụ thể — verifier sẽ trả INSUFFICIENT (fail-safe)."""
        return cls(conditions=[], evidence_required=False)

    def is_empty(self) -> bool:
        return len(self.conditions) == 0


# =============================================================================
# Validation helper — dùng trong verifier để kiểm tra input đúng schema
# =============================================================================

class SchemaValidationError(ValueError):
    pass


def validate_postcondition_dict(d: Any) -> None:
    """
    Kiểm tra dict có đúng format PostconditionSchema không.
    Raise SchemaValidationError nếu sai.
    Dùng trong verifier lúc nhận input từ caller.
    """
    if d is None:
        return  # None là hợp lệ (no postcondition)
    if not isinstance(d, dict):
        raise SchemaValidationError(f"Postcondition phải là dict, nhận được: {type(d)}")
    all_conditions = d.get("all")
    if all_conditions is not None:
        if not isinstance(all_conditions, list):
            raise SchemaValidationError(f"'all' phải là list, nhận được: {type(all_conditions)}")
        for i, cond in enumerate(all_conditions):
            if not isinstance(cond, dict):
                raise SchemaValidationError(f"Condition[{i}] phải là dict")
            kind = cond.get("kind")
            if kind not in VALID_KINDS:
                raise SchemaValidationError(
                    f"Condition[{i}].kind='{kind}' không hợp lệ. "
                    f"Các kind được hỗ trợ: {sorted(VALID_KINDS)}"
                )
