"""
SCP - Viet Nam | Self-Correcting Pipeline
 StatisticsDataSource - Data source cho Thống kê
"""

import logging
import math
import re
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


def _wb_match(key: str, text_lower: str) -> bool:
    """[ROOT-FIX 4] Word-boundary match — prevents 'std' matching 'study',
    'mean' matching 'means', 'mode' matching 'model', etc.
    Uses Unicode-aware lookarounds so Vietnamese diacritics work too.
    """
    if not key or not text_lower:
        return False
    if key == text_lower:
        return True
    pattern = r'(?<![\wÀ-ỹ])' + re.escape(key) + r'(?![\wÀ-ỹ])'
    return bool(re.search(pattern, text_lower))


class StatisticsDataSource(IDataSource):
    """
    Data source cho các câu hỏi Thống kê.
    Hỗ trợ: mean, median, mode, variance, standard deviation, probability.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Statistical distributions
        self._distributions = {
            "normal": {
                "name": "Phân phối chuẩn",
                "parameters": ["μ (mean)", "σ (std)"],
                "formula": "f(x) = (1/(σ√(2π))) × e^(-(x-μ)²/(2σ²))"
            },
            "binomial": {
                "name": "Phân phối nhị thức",
                "parameters": ["n (trials)", "p (probability)"],
                "formula": "P(X=k) = C(n,k) × p^k × (1-p)^(n-k)"
            },
            "poisson": {
                "name": "Phân phối Poisson",
                "parameters": ["λ (rate)"],
                "formula": "P(X=k) = (λ^k × e^(-λ)) / k!"
            },
            "exponential": {
                "name": "Phân phối mũ",
                "parameters": ["λ (rate)"],
                "formula": "f(x) = λ × e^(-λx)"
            },
        }

        # Common statistics
        self._formulas = {
            "mean": "Σx / n",
            "variance": "Σ(x - μ)² / n",
            "std": "√(Σ(x - μ)² / n)",
            "correlation": "Σ(x - x̄)(y - ȳ) / √(Σ(x - x̄)² × Σ(y - ȳ)²)",
            "z-score": "(x - μ) / σ",
        }


    @property
    def name(self) -> str:
        return "StatisticsDataSource"

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
            return {"value": result.get("answer", ""), "source": "Statistics", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True

    def query(self, question: str) -> dict[str, Any]:
        """Query statistics data."""
        q = question.lower().strip()

        if q in self._cache:
            return self._cache[q]

        result = {"found": False, "answer": None, "confidence": 0.0}

        # Check distributions
        for name, data in self._distributions.items():
            # [ROOT-FIX 4] Was `name in q or data["name"].lower() in q` — substring
            # match → 'normal' matched 'abnormal', 'exponential' matched 'exponentially'.
            # Use word-boundary match.
            if _wb_match(name, q) or _wb_match(data["name"].lower(), q):
                result = {
                    "found": True,
                    "answer": f"{data['name']}\nFormula: {data['formula']}\nParameters: {', '.join(data['parameters'])}",
                    "confidence": 1.0,
                    "source": "Statistics Database"
                }
                break

        # Check formulas
        for name, formula in self._formulas.items():
            # [ROOT-FIX 4] Same substring → word-boundary fix.
            if _wb_match(name, q):
                result = {
                    "found": True,
                    "answer": f"{name}: {formula}",
                    "confidence": 1.0,
                    "source": "Statistics Formulas"
                }
                break

        self._cache[q] = result
        return result

    def calculate(self, operation: str, values: list[float]) -> float | None:
        """Calculate statistics."""
        if not values:
            return None

        if operation == "mean" or operation == "trung bình":
            return sum(values) / len(values)
        elif operation == "median" or operation == "trung vị":
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            if n % 2 == 0:
                return (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / 2
            return sorted_vals[n//2]
        elif operation == "mode" or operation == "yếu vị":
            from collections import Counter
            return Counter(values).most_common(1)[0][0]
        elif operation == "variance" or operation == "phương sai":
            mean = self.calculate("mean", values)
            if mean is None:
                return None  # [AUTOFIX-T1] mypy [operator]: mean can be None → TypeError
            return sum((x - mean) ** 2 for x in values) / len(values)
        elif operation == "std" or operation == "độ lệch chuẩn":
            variance = self.calculate("variance", values)
            if variance is None:
                return None  # [AUTOFIX-T1] mypy [operator]: variance can be None
            return math.sqrt(variance)

        return None
