"""
SCP V90 MINIMAL — GeneratorKhamPha (simplified)
Generates random exploration questions for curiosity/prediction modules.
"""
import logging
import random

logger = logging.getLogger("scp.generator")

# [Mimosa B311-fix 2026-09-30] Generator sinh câu hỏi khám phá từ pool
# math/science/general — sampling phi mật mã: không token, không secret,
# không ID/nonce cần unguessable; đoán trước câu được chọn không gây hại.
# Dùng instance Random RIÊNG (SystemRandom, seed từ os.urandom) thay cho
# global RNG để (1) tách biệt với mọi lời random.seed() của module khác
# và (2) làm rõ ràng tại call site rằng đây là nguồn ngẫu nhiên độc lập,
# phi bảo mật.
_GENERATOR_RNG = random.SystemRandom()


class KhamPhaHistory:
    """Track generated questions to avoid duplicates."""
    def __init__(self):
        self._seen = set()

    def add(self, q: str):
        self._seen.add(q)

    def has(self, q: str) -> bool:
        return q in self._seen


class GeneratorKhamPha:
    """Minimal question generator — picks from pools."""

    _POOLS = {
        "math": [
            "Tính {a} + {b}", "Tính {a} * {b}", "Tính {a} - {b}",
            "Số nguyên tố gần {a} là gì?", "Bình phương của {a} bằng bao nhiêu?",
            "Căn bậc hai của {a} bằng bao nhiêu?", "{a} có chia hết cho 3 không?",
        ],
        "science": [
            "Nhiệt độ nóng chảy của nước là bao nhiêu?",
            "Tốc độ ánh sáng là bao nhiêu km/s?",
            "Số nguyên tử trong phân tử nước là mấy?",
            "Khối lượng Trái Đất là bao nhiêu kg?",
        ],
        "general": [
            "Thủ đô của nước nào có tên bắt đầu bằng chữ {letter}?",
            "Con vật nào nhanh nhất trên cạn?",
            "Sông dài nhất thế giới là sông nào?",
        ],
    }

    def __init__(self):
        self.history = KhamPhaHistory()

    def sinh_ngau_nhien(self) -> dict:
        """Generate a random question spec."""
        domain = _GENERATOR_RNG.choice(list(self._POOLS.keys()))
        template = _GENERATOR_RNG.choice(self._POOLS[domain])
        a = _GENERATOR_RNG.randint(2, 999)
        b = _GENERATOR_RNG.randint(2, 99)
        letter = _GENERATOR_RNG.choice("ABCDEFGHIKLMNOPQRSTUVWXY")
        question = template.format(a=a, b=b, letter=letter)
        self.history.add(question)
        return {"question": question, "domain": domain}
