"""
SCP - Viet Nam | Self-Correcting Pipeline
 PsychologyDataSource - Data source cho Tâm lý học
"""

import logging
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)
# [V104.32 #14] word-boundary matching for short keys


class PsychologyDataSource(IDataSource):
    """
    Data source cho các câu hỏi Tâm lý học.
    Hỗ trợ: rối loạn, hiệu ứng, lý thuyết.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Psychological disorders (DSM-5 simplified)
        self._disorders = {
            "depression": {"symptoms": "buồn kéo dài, mất interés, mệt mỏi", "treatment": "CBT, thuốc"},
            "anxiety": {"symptoms": "lo âu, tim đập nhanh, đổ mồ hôi", "treatment": "therapy, thuốc"},
            "bipolar": {"symptoms": "thay đổi tâm trạng cực đoan", "treatment": "mood stabilizers"},
            "PTSD": {"symptoms": "flashback, ác mộng, né tránh", "treatment": "EMDR, CBT"},
            "OCD": {"symptoms": "ám ảnh, cưỡng ép", "treatment": "ERP, thuốc"},
            "schizophrenia": {"symptoms": "hoang tưởng, ảo giác", "treatment": "thuốc chống loạn thần"},
        }

        # Psychological effects
        self._effects = {
            "placebo": "Hiệu ứng giả dược - tin rằng thuốc có tác dụng thì sẽ có",
            "Dunning-Kruger": "Người kém năng lực thường đánh giá quá cao bản thân",
            "confirmation bias": "倾向 tìm thông tin xác nhận niềm tin sẵn có",
            "halo effect": "Đánh giá tổng thể tốt dựa trên 1 đặc điểm tốt",
            "Pavlov": "Điều kiện hóa đáp ứng - chuông → thức ăn → nước bọt",
            "Maslow": "Tháp nhu cầu - sinh lý → an toàn → xã hội → tôn trọng → tự thực hiện",
            "Stanford Prison": "Thí nghiệm tù Stanford - vai trò quyết định hành vi",
            "Milgram": "Thí nghiệm điện giật - con người tuân lệnh authority",
        }

        # Big Five personality traits
        self._big_five = {
            "Openness": "Mở lòng với trải nghiệm mới",
            "Conscientiousness": "Tổ chức, có trách nhiệm",
            "Extraversion": "Hướng ngoại, thích giao tiếp",
            "Agreeableness": "Thiện chí, tin tưởng người khác",
            "Neuroticism": "Nhạy cảm với cảm xúc tiêu cực",
        }


    @property
    def name(self) -> str:
        return "PsychologyDataSource"

    @property
    def priority(self) -> int:
        return 5

    @property
    def ttl(self) -> int:
        return 86400

    def get_supported_intents(self) -> list[str]:
        return ["lookup", "query", "fact"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        return True

    def fetch(self, intent: str, entity: str, **kwargs):
        result = self.query(entity or intent)
        if result.get("found"):
            return {"value": result.get("answer", ""), "source": "Psychology", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True

    def query(self, question: str) -> dict[str, Any]:
        """Query psychology data."""
        q = question.lower().strip()

        if q in self._cache:
            return self._cache[q]

        result = {"found": False, "answer": None, "confidence": 0.0}

        # Check disorders
        for disorder, info in self._disorders.items():
            if disorder.lower() in q:  # [V104.32 #14] was: uppercase PTSD/OCD never matched:
                result = {
                    "found": True,
                    "answer": f"{disorder}: triệu chứng - {info['symptoms']}, điều trị - {info['treatment']}",
                    "confidence": 0.9,
                    "source": "DSM-5"
                }
                break

        # Check effects
        for effect, description in self._effects.items():
            if effect.lower() in q:
                result = {
                    "found": True,
                    "answer": f"{effect}: {description}",
                    "confidence": 1.0,
                    "source": "Psychology Database"
                }
                break

        self._cache[q] = result
        return result
