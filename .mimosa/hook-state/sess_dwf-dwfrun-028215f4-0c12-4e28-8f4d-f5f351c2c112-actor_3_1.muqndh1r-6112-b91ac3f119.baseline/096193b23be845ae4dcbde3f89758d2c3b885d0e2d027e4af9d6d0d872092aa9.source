import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.foundation import AIParser


def test_subsystem_foundation_importable():
    """Foundation parser: verify mathematical and unit conversion extractions."""
    # Math extraction
    assert AIParser.parse_math("what is 2 + 3", "2 + 3 = 5") == "5"
    assert AIParser.parse_math("calc", "Ket qua la 42") == "42"
    
    # Temperature extraction
    assert AIParser.parse_temperature("weather", "Temperature is 25°C") == "25"
    
    # Currency conversion extraction
    assert AIParser.parse_conversion("USD to EUR", "1 USD = 0.92 EUR") == "0.92"
