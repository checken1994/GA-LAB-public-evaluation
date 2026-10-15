#!/usr/bin/env python3
"""Validate spec/complete_scp_reference.yaml - fail-closed reference integrity.

Machine-checkable rules (26-P0.1):
  - reference block: id, semver version, schema_version present
  - the 6 core principles are present and true
  - the 4 canonical verdicts are all declared
  - evidence_levels cover A/B/C/D
  - capability IDs are unique (YAML silently dedupes duplicate keys)
  - every capability has required=true and a known minimum_maturity
  - epistemic.lineage declares default_independence=UNKNOWN_INDEPENDENCE
  - intelligence.zero_cost stays ABSENT: the zero-cost architecture was
    deprecated across all 5 layers by authority decision (GA.md B13, commit
    9c01dca) - its reappearance in the reference is a violation (fail-closed)
  - the reference never binds an implementation (no class/method/module keys)

Exit 0 = valid, exit 1 = invalid (prints every violation).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DEFAULT_SPEC = Path(__file__).resolve().parents[1] / "spec" / "complete_scp_reference.yaml"

REQUIRED_PRINCIPLES = (
    "reality_over_model",
    "pass_not_equal_true",
    "fail_closed_unknown",
    "external_data_untrusted",
    "independent_lineage_required",
    "reversible_change_required",
)
REQUIRED_VERDICTS = {"VERIFIED", "CONTRADICTED", "INSUFFICIENT", "UNKNOWN"}
REQUIRED_EVIDENCE_LEVELS = {"A", "B", "C", "D"}
KNOWN_MATURITIES = {"A", "B", "C", "D"}  # minimum_maturity = minimum evidence level
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def validate_reference(path: Path = DEFAULT_SPEC) -> list[str]:
    import yaml

    errors: list[str] = []
    raw_text = path.read_text(encoding="utf-8")

    # YAML silently collapses duplicate keys - detect them in the raw text.
    seen: set[str] = set()
    for line in raw_text.splitlines():
        match = re.match(r"^  ([a-z][a-z0-9_.]+):\s*$", line)
        if match:
            cap_id = match.group(1)
            if cap_id in seen:
                errors.append(f"duplicate capability id: {cap_id}")
            seen.add(cap_id)

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        return [f"yaml parse error: {exc}"]

    reference = data.get("reference") or {}
    if reference.get("id") != "complete-scp":
        errors.append("reference.id must be 'complete-scp'")
    if not SEMVER_RE.match(str(reference.get("version", ""))):
        errors.append(f"reference.version must be semver, got {reference.get('version')!r}")
    if reference.get("schema_version") != 1:
        errors.append("reference.schema_version must be 1")

    principles = data.get("principles") or {}
    for name in REQUIRED_PRINCIPLES:
        if principles.get(name) is not True:
            errors.append(f"missing/false core principle: {name}")

    verdicts = set(data.get("verdicts") or [])
    missing = REQUIRED_VERDICTS - verdicts
    if missing:
        errors.append(f"missing canonical verdicts: {sorted(missing)}")

    levels = data.get("evidence_levels") or {}
    if set(levels) != REQUIRED_EVIDENCE_LEVELS:
        errors.append(f"evidence_levels must cover exactly A/B/C/D, got {sorted(levels)}")

    capabilities = data.get("capabilities") or {}
    if not capabilities:
        errors.append("capabilities must not be empty")
    for cap_id, spec in capabilities.items():
        if not isinstance(spec, dict):
            errors.append(f"{cap_id}: capability spec must be a mapping")
            continue
        if spec.get("required") is not True:
            errors.append(f"{cap_id}: required must be true")
        maturity = spec.get("minimum_maturity")
        if maturity not in KNOWN_MATURITIES:
            errors.append(f"{cap_id}: unknown minimum_maturity {maturity!r}")

    lineage = capabilities.get("epistemic.lineage") or {}
    if lineage.get("default_independence") != "UNKNOWN_INDEPENDENCE":
        errors.append("epistemic.lineage must declare default_independence: UNKNOWN_INDEPENDENCE")

    # Zero-cost architecture was deprecated by authority decision (GA.md B13,
    # commit 9c01dca: removed from this reference and from
    # spec/protected_invariants.yaml). The capability must stay absent;
    # silently re-adding it (with or without the old $0 fields) is a
    # contract violation. Reintroduction requires a new authority decision.
    if "intelligence.zero_cost" in capabilities:
        errors.append(
            "intelligence.zero_cost is deprecated (GA.md B13) and must stay absent "
            "from the reference; reintroduction requires a new authority decision"
        )

    # The reference defines WHAT, never HOW: no implementation bindings here.
    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        if re.match(r"^\s*(class|method|module):\s*\S", line):
            errors.append(
                f"line {line_number}: reference must not bind implementations "
                f"({line.strip()!r}) - use spec/implementation_bindings.yaml"
            )
    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SPEC
    if not path.is_file():
        print(f"FAIL: reference spec not found: {path}")
        return 1
    errors = validate_reference(path)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"OK: {path.name} is a valid Complete SCP reference")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
