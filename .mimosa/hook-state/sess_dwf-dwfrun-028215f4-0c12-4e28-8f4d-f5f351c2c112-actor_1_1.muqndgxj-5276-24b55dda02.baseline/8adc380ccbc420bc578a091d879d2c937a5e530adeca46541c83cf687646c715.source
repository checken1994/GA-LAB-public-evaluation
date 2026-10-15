"""
SCP - Viet Nam | Self-Correcting Pipeline
 MathDataSource - Data source cho Toán học
Note: Math SLM uses MathEvaluator directly, this is for completeness.
"""

import logging
import re as _re
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)
# [V104.32 #3] word-boundary matching for short keys


class MathDataSource(IDataSource):
    """Data source cho Toán học (deterministic)."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Mathematical constants
        self._constants = {
            "pi": 3.14159265358979323846,
            "e": 2.71828182845904523536,
            "phi": 1.61803398874989484820,  # Golden ratio
            "tau": 6.28318530717958647692,
            "sqrt2": 1.41421356237309504880,
            "sqrt3": 1.73205080756887729352,
        }

        # Greek letters
        self._greek = {
            "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ",
            "epsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ",
            "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ",
            "nu": "ν", "xi": "ξ", "omicron": "ο", "pi": "π",
            "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ",
            "phi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
        }

    def query(self, question: str) -> dict[str, Any]:
        q = question.lower().strip()
        if q in self._cache:
            return self._cache[q]

        result = {"found": False, "answer": None, "confidence": 0.0}

        # Check constants
        for name, value in self._constants.items():
            if (len(name) >= 3 and _re.search(r'\b' + _re.escape(name) + r'\b', q)) or name == q:
                result = {
                    "found": True,
                    "answer": f"{name} ≈ {value}",
                    "confidence": 1.0,
                    "source": "MathConstants"
                }
                break

        # Check greek letters
        if not result["found"]:
            for name, symbol in self._greek.items():
                if (len(name) >= 3 and _re.search(r'\b' + _re.escape(name) + r'\b', q)) or name == q:
                    result = {
                        "found": True,
                        "answer": f"{name} = {symbol}",
                        "confidence": 1.0,
                        "source": "GreekAlphabet"
                    }
                    break

        self._cache[q] = result
        return result

    @property
    def name(self) -> str:
        return "MathDataSource"

    @property
    def priority(self) -> int:
        return 1  # High priority - deterministic

    @property
    def ttl(self) -> int:
        return 604800  # 1 week - constants don't change

    def get_supported_intents(self) -> list[str]:
        return ["constant", "formula", "calculate"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        return intent in ["constant", "formula", "calculate"]

    def fetch(self, intent: str, entity: str, **kwargs):
        result = self.query(entity or intent)
        if result.get("found"):
            return {"value": result.get("answer", ""), "source": "Math", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True
