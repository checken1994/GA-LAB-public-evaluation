""" SpaceMedicineDataSource"""
import logging

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)

class SpaceMedicineDataSource(IDataSource):
    def __init__(self):
        self._cache = {}
        self._effects = {
            "bone loss": "1-2% per month in microgravity",
            "muscle atrophy": "Loss of muscle mass in space",
            "radiation": "Higher exposure in space",
            "fluid shift": "Blood moves to upper body",
        }

    @property
    def name(self) -> str:
        return "SpaceMedicineDataSource"

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
        # [EXEC-3] TẠI SAO: space medicine is a high-risk medical subdomain —
        # NO dose/treatment advice without an aerospace medicine specialist.
        # Mirror medical.py abstain pattern: if intent is dose/treatment advice,
        # abstain rather than serving hardcoded reference strings as an answer.
        if intent in ('medical_dose_advice', 'medical_treatment_advice'):
            return {
                'value': None,
                'abstain': True,
                'reason': (
                    "SCP cannot provide space medicine advice. "
                    "Consult an aerospace medicine specialist."
                ),
                'source': 'SpaceMedicineDataSource (abstain policy)',
                'metadata': {
                    'intent': intent,
                    'abstain': True,
                    'disclaimer': (
                        "Space medicine decisions depend on mission profile, "
                        "radiation exposure history, microgravity duration, "
                        "and individual astronaut physiology. SCP's static "
                        "reference values are not personalized medical advice."
                    ),
                },
                'confidence': 0.0,
            }
        result = self.query(entity or intent)
        if result.get("found"):
            return {"value": result.get("answer", ""), "source": "SpaceMedicine", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True

    def query(self, q):
        if q in self._cache: return self._cache[q]
        result = {"found": False, "answer": None, "confidence": 0.0}
        for effect, desc in self._effects.items():
            if effect in q:
                result = {"found": True, "answer": f"{effect}: {desc}", "confidence": 1.0}
                break
        self._cache[q] = result
        return result
