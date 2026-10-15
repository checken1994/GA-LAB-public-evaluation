import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.verify_complete_scp_reference import validate_reference

# ==============================================================================
# T00 - COMPLETE SCP REFERENCE INTEGRITY (26-P0.1)
# ==============================================================================
# The reference defines WHAT Complete SCP means and must stay free of
# implementation bindings (the "Complete SCP requires EpistemicScanner class"
# harness failure class). T00 enforces that the shipped reference itself can
# never reintroduce that failure mode.
# ==============================================================================

SPEC_PATH = ROOT / "spec" / "complete_scp_reference.yaml"


def test_shipped_reference_passes_fail_closed_validator():
    assert SPEC_PATH.is_file(), "spec/complete_scp_reference.yaml is a P0 artifact - it must exist"
    errors = validate_reference(SPEC_PATH)
    assert not errors, f"Complete SCP reference violates its own contract: {errors}"


def test_reference_never_binds_implementation_symbols():
    import re

    raw = SPEC_PATH.read_text(encoding="utf-8")
    offenders = [
        (number, line.strip())
        for number, line in enumerate(raw.splitlines(), start=1)
        if re.match(r"^\s*(class|method|module):\s*\S", line)
    ]
    assert not offenders, (
        f"Reference binds implementation details (must live in spec/implementation_bindings.yaml): {offenders}"
    )


def test_validator_rejects_a_reference_that_requires_a_class():
    """The exact historical failure mode (invented-class reference) must be caught."""
    import tempfile

    poisoned = SPEC_PATH.read_text(encoding="utf-8").replace(
        "  epistemic.evidence:\n", "  epistemic.evidence:\n    class: EpistemicScanner\n", 1
    )
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as handle:
        handle.write(poisoned)
        poisoned_path = handle.name
    errors = validate_reference(Path(poisoned_path))
    assert any("must not bind implementations" in error for error in errors), (
        f"Validator failed to catch an implementation-bound reference: {errors}"
    )


def test_implementation_bindings_map_reference_ids_to_real_modules():
    """P0-04b: the bindings file exists, speaks reference language only, and
    every binding marked required_now points at a REAL importable module."""
    import importlib

    import yaml

    bindings_path = ROOT / "spec" / "implementation_bindings.yaml"
    assert bindings_path.is_file(), (
        "spec/complete_scp_reference.yaml promises implementation_bindings.yaml - it must exist"
    )
    payload = yaml.safe_load(bindings_path.read_text(encoding="utf-8"))
    assert payload.get("schema_version") == 1
    assert payload.get("reference_id") == "complete-scp"

    reference_ids = set(
        yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))["capabilities"].keys()
    )
    bindings = payload.get("bindings") or {}
    assert bindings, "bindings must not be empty"
    for cap_id, binding in bindings.items():
        assert cap_id in reference_ids, (
            f"binding {cap_id!r} does not exist in the reference - bindings speak reference language"
        )
        implementations = binding.get("implementations") or []
        assert implementations, f"{cap_id}: binding must list at least one implementation module"
        for module_name in implementations:
            assert isinstance(module_name, str) and module_name.startswith("scp."), (
                f"{cap_id}: implementation must be an scp module path, got {module_name!r}"
            )
            if binding.get("required_now") is True:
                try:
                    importlib.import_module(module_name)
                except ImportError as exc:
                    raise AssertionError(
                        f"{cap_id}: required_now binding {module_name} is not importable ({exc})"
                    )
