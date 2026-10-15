import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SPEC_PATH = ROOT / "spec" / "complete_scp_reference.yaml"

# ==============================================================================
# T02 - COMPLETE SCP REFERENCE SCHEMA (26-P0.1)
# ==============================================================================


def _reference() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def test_reference_declares_canonical_verdicts_and_levels():
    data = _reference()
    assert data["verdicts"] == ["VERIFIED", "CONTRADICTED", "INSUFFICIENT", "UNKNOWN"]
    assert data["evidence_levels"] == {"A": "static", "B": "integration", "C": "end_to_end", "D": "recovery"}


def test_every_capability_has_maturity_and_hard_security_edges():
    data = _reference()
    capabilities = data["capabilities"]
    assert capabilities, "reference must declare capabilities"
    for cap_id, spec in capabilities.items():
        assert spec.get("required") is True, f"{cap_id}: must be required"
        assert spec.get("minimum_maturity") in {"A", "B", "C", "D"}, f"{cap_id}: unknown minimum evidence level"

    assert capabilities["epistemic.lineage"]["default_independence"] == "UNKNOWN_INDEPENDENCE", (
        "Lineage default must be UNKNOWN_INDEPENDENCE - independence is never assumed"
    )
    # intelligence.zero_cost has been architecturally deprecated — verify
    # it is no longer declared in the spec (deprecation proof).
    assert "intelligence.zero_cost" not in capabilities, (
        "intelligence.zero_cost must be removed from capabilities (architectural deprecation)"
    )
    assert capabilities["risk.external_alert"].get("human_authority") is True, (
        "External alerts must be human-authority-gated by definition"
    )
