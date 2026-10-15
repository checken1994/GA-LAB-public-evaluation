"""
SCP - Viet Nam | Self-Correcting Pipeline
 GenAIDataSource - Data source cho AI/ML
"""

import logging
import re
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


def _wb_match(key: str, text_lower: str) -> bool:
    """[ROOT-FIX 4] Word-boundary match — prevents 'AI' matching 'r**AI**n',
    'LLM' matching 'wi**LLM**an' (rare), 'RAG' matching 'f**RAG**ile', 'bias'
    matching 'biases' (intended?) — note 'biases' SHOULD match since it's the
    same concept, but 'bias' matching 'cobias' (rare) shouldn't.
    Uses Unicode-aware lookarounds so Vietnamese diacritics work too.
    """
    if not key or not text_lower:
        return False
    if key == text_lower:
        return True
    pattern = r'(?<![\wÀ-ỹ])' + re.escape(key) + r'(?![\wÀ-ỹ])'
    return bool(re.search(pattern, text_lower))


class GenAIDataSource(IDataSource):
    """
    Data source cho các câu hỏi AI/ML.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # AI/ML concepts
        self._concepts = {
            "machine learning": "Học từ dữ liệu thay vì lập trình rules",
            "deep learning": "Neural network nhiều layers",
            "neural network": "Mô hình lấy cảm hứng từ não người",
            "transformer": "Attention mechanism cho sequence",
            "LLM": "Large Language Model - mô hình ngôn ngữ lớn",
            "RAG": "Retrieval Augmented Generation",
            "fine-tuning": "Điều chỉnh model đã pretrained",
            "prompt engineering": "Thiết kế input để tối ưu output",
            "hallucination": "AI tạo thông tin sai nhưng nghe có lý",
            "bias": "Thiên kiến trong dữ liệu huấn luyện",
        }

        # Model sizes
        self._models = {
            "GPT-4": "1.76T params",
            "GPT-3.5": "175B params",
            "Claude": "137B params",
            "LLaMA": "70B params",
            "Gemini": "1.5T params",
            "Mistral": "7B params",
        }


    @property
    def name(self) -> str:
        return "GenAIDataSource"

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
            return {"value": result.get("answer", ""), "source": "GenAI", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True

    def query(self, question: str) -> dict[str, Any]:
        """Query AI/ML data."""
        q = question.lower().strip()

        if q in self._cache:
            return self._cache[q]

        result = {"found": False, "answer": None, "confidence": 0.0}

        for concept, description in self._concepts.items():
            # [ROOT-FIX 4] Was `concept in q` — substring match → 'AI' matched
            # 'rain'/'trail'/'certain', 'RAG' matched 'fragile'/'garage', 'bias'
            # matched 'biases'. Use word-boundary match.
            if _wb_match(concept.lower(), q):
                result = {
                    "found": True,
                    "answer": f"{concept}: {description}",
                    "confidence": 1.0,
                    "source": "AI/ML Database"
                }
                break

        for model, size in self._models.items():
            # [ROOT-FIX 4] Same substring → word-boundary fix.
            if _wb_match(model.lower(), q):
                result = {
                    "found": True,
                    "answer": f"{model}: {size}",
                    "confidence": 1.0,
                    "source": "AI Models Database"
                }
                break

        self._cache[q] = result
        return result
