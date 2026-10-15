
from scp.interfaces.data_source import IDataSource
from scp.interfaces.severity import Severity, normalize_severity


class ConcreteDataSource(IDataSource):
    @property
    def name(self) -> str: return "mock_source"
    @property
    def priority(self) -> int: return 1
    @property
    def ttl(self) -> int: return 60
    def get_supported_intents(self) -> list[str]: return ["test_intent"]
    def can_handle(self, intent: str, entity: str | None = None) -> bool: return intent == "test_intent"
    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        return {"value": "42", "source": self.name} if self.can_handle(intent) else None
    def health_check(self) -> bool: return True

def test_interface_data_source_behavior():
    ds = ConcreteDataSource()
    assert ds.health_check() is True
    assert ds.can_handle("test_intent") is True
    assert ds.fetch("test_intent", "entity") == {"value": "42", "source": "mock_source"}
    assert ds.fetch("unknown", "entity") is None

def test_interface_severity_normalization():
    assert normalize_severity("CRITICAL") == "critical"
    assert normalize_severity(Severity.HIGH) == "high"
    assert normalize_severity("unknown_val") is None
