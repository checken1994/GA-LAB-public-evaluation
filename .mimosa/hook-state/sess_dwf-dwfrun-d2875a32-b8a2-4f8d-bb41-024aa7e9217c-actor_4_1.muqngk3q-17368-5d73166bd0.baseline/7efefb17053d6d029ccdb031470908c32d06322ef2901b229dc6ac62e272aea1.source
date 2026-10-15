"""
SCP V104 — Explainability for Non-Experts
==========================================
Tóm tắt verdict bằng ngôn ngữ ĐƠN GIẢN cho người không chuyên.

Ví dụ:
  Technical: "Verdict=PASS, conf=0.82, source=arXiv, factor=0.90, LineageDetector overlap=0.9"
  → Simple:  "SCP đã kiểm tra câu trả lời này với 2 nguồn độc lập và tin rằng nó ĐÚNG.
              Tuy nhiên, 2 nguồn này có cùng gốc nên độ tin cậy giảm xuống 82%."

3 mức độ giải thích:
  1. Simple: 1 câu tóm tắt
  2. Medium: 2-3 câu + lý do chính
  3. Technical: chi tiết đầy đủ (hiện tại)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("scp.meta.simple_explainer")


@dataclass
class SimpleExplanation:
    """Giải thích verdict cho người không chuyên."""
    one_line: str         # 1 câu tóm tắt
    medium: str           # 2-3 câu + lý do
    verdict_color: str   # green | yellow | red
    action_recommended: str = ""  # "An toàn dùng" | "Cần kiểm tra thêm" | "Không dùng"


class SimpleExplainer:
    """Tóm tắt verdict SCP bằng tiếng Việt đơn giản."""

    def explain(
        self,
        verdict: str,
        confidence: float,
        domain: str = "",
        sources: int = 0,
        has_attack: bool = False,
        has_bypass: bool = False,
        has_human_review: bool = False,
        lineage_overlap: float = 0.0,
        reliability_factor: float = 1.0,
    ) -> SimpleExplanation:
        """Tạo giải thích đơn giản từ verdict."""

        # Determine color
        if verdict in ("FAIL", "SKIP"):
            color = "red"
        elif verdict == "FLAGGED":
            color = "red"
        elif verdict == "UNKNOWN" or confidence < 0.5:
            color = "yellow"
        elif confidence < 0.7:
            color = "yellow"
        else:
            color = "green"

        # Build one-line summary
        if has_attack:
            one_line = "⚠️ Câu hỏi này chứa nội dung tấn công và đã bị chặn."
        elif has_bypass:
            one_line = "⚠️ SCP phát hiện lỗ hổng và đã chặn câu trả lời."
        elif verdict == "FAIL":
            one_line = "❌ SCP xác định câu trả lời này SAI."
        elif verdict == "PARTIAL":
            #  TẠI SAO: V104.34 #59 fix was incomplete — it set color="yellow"
            # but forgot to set `one_line` → NameError at `medium = one_line + ...` below,
            # swallowed by upstream except → every PARTIAL verdict (very common after
            # CognitiveGate downgrades) crashed the explainer silently. Fix: set one_line.
            color = "yellow"  # [V104.34 #59] PARTIAL shown as green "ĐÚNG" was wrong
            one_line = "⚖️ SCP xác định câu trả lời này chỉ ĐÚNG MỘT PHẦN."
        elif verdict == "UNKNOWN":
            one_line = "❓ SCP chưa đủ thông tin để kết luận."
        elif verdict == "SKIP":
            one_line = "⏭️ SCP bỏ qua câu hỏi này (không hợp lệ)."
        elif verdict == "FLAGGED":
            one_line = "🚩 SCP đánh dấu câu trả lời này đáng nghi."
        elif confidence >= 0.85:
            one_line = f"✅ SCP tin rằng câu trả lời này ĐÚNG (độ tin cậy {int(confidence*100)}%)."
        elif confidence >= 0.7:
            one_line = f"✅ SCP khá chắc câu trả lời này đúng (độ tin cậy {int(confidence*100)}%)."
        elif confidence >= 0.5:
            one_line = f"⚠️ SCP hơi chắc nhưng chưa hoàn toàn (độ tin cậy {int(confidence*100)}%)."
        else:
            one_line = f"❓ SCP không chắc lắm (độ tin cậy chỉ {int(confidence*100)}%)."

        # Build medium explanation
        reasons = []

        if has_attack:
            reasons.append("SCP phát hiện câu hỏi có dấu hiệu tấn công AI")
        if has_bypass:
            reasons.append("SCP phát hiện lỗ hổng bảo mật và đã chặn")
        if sources > 0:
            if lineage_overlap > 0.7:
                reasons.append(f"Kiểm tra {sources} nguồn nhưng chúng cùng gốc nên độ tin cậy giảm")
            else:
                reasons.append(f"Kiểm tra với {sources} nguồn độc lập")
        if reliability_factor < 0.8:
            reasons.append(f"Nguồn dữ liệu có độ tin cậy thấp ({int(reliability_factor*100)}%)")
        if has_human_review:
            reasons.append("Cần con người xem xét lại trước khi dùng")
        if confidence < 0.5 and not has_attack:
            reasons.append("Không đủ bằng chứng để kết luận chắc chắn")

        if not reasons:
            reasons.append(f"Đã qua {27} bước kiểm chứng")
            if domain:
                reasons.append(f"Lĩnh vực: {domain}")

        medium = one_line + " " + ". ".join(reasons) + "."

        # Recommended action
        if color == "red":
            action = "Không dùng câu trả lời này."
        elif color == "yellow":
            action = "Cần kiểm tra thêm trước khi dùng."
        else:
            action = "An toàn dùng."

        return SimpleExplanation(
            one_line=one_line,
            medium=medium,
            verdict_color=color,
            action_recommended=action,
        )


if __name__ == "__main__":
    print("=== Simple Explainer — Test ===\n")
    explainer = SimpleExplainer()

    tests = [
        {"verdict": "PASS", "confidence": 0.95, "domain": "geography", "sources": 3},
        {"verdict": "PASS", "confidence": 0.65, "domain": "history", "sources": 2, "lineage_overlap": 0.9},
        {"verdict": "FAIL", "confidence": 0.0, "has_attack": True},
        {"verdict": "UNKNOWN", "confidence": 0.3, "sources": 1},
        {"verdict": "PASS", "confidence": 0.55, "reliability_factor": 0.65},
        {"verdict": "FLAGGED", "confidence": 0.4, "has_human_review": True},
    ]

    for i, t in enumerate(tests, 1):
        exp = explainer.explain(**t)
        print(f"Test {i}: verdict={t['verdict']}, conf={t['confidence']}")
        print(f"  1-line: {exp.one_line}")
        print(f"  medium:  {exp.medium[:120]}")
        print(f"  action:  {exp.action_recommended}")
        print(f"  color:   {exp.verdict_color}")
        print()
