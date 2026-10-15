#!/usr/bin/env python3
"""Machine verdict for any 'Complete SCP' claim (owner-locked rule).

HARD RULE: a green pytest suite (any count: 23, 54, 340, 427...) proves ONLY
PASS_WITHIN_SCOPE of the individual tests. It can NEVER mean the Complete SCP
architecture is achieved. Completion requires, machine-computed:

  1. every capability marked required:true in spec/complete_scp_reference.yaml
     has status EVIDENCE_VERIFIED in spec/scp_target_test_coverage.yaml
     (each with a 40-char snapshot_sha + evidence_refs);
  2. unproven_count over required capabilities == 0;
  3. suite green at the SAME snapshot SHA.

Until then the only legal statements are of the form:
  "verified within scope on SHA X" — never "Complete SCP done/passed".

Exit 0 = the current state allows scoped claims only (normal).
Prints COMPLETE_SCP_CLAIM: FORBIDDEN plus the exact missing requirements.
This tool NEVER exits non-zero for incompleteness — incompleteness is the
expected state; the FAIL exit is reserved for a forged claim (claiming
completion while the counts say otherwise is detected by the T00 test).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def compute(binding: dict, reference: dict) -> dict:
    caps = binding.get("claims", [])
    by_id = {c["target_id"]: c for c in caps if c.get("target_kind") == "capability"}
    required_ids = [cid for cid, spec in (reference.get("capabilities") or {}).items()
                    if isinstance(spec, dict) and spec.get("required") is True]
    verified = sorted(cid for cid in required_ids
                      if by_id.get(cid, {}).get("status") == "EVIDENCE_VERIFIED")
    missing = sorted(cid for cid in required_ids
                     if by_id.get(cid, {}).get("status") != "EVIDENCE_VERIFIED")
    counts: dict[str, int] = {}
    for c in caps:
        counts[c.get("status", "?")] = counts.get(c.get("status", "?"), 0) + 1
    return {
        "suite_pass_means": "PASS_WITHIN_SCOPE only - never Complete SCP achievement",
        "required_capabilities": len(required_ids),
        "required_evidence_verified": len(verified),
        "required_still_missing": missing,
        "unproven_count": counts.get("UNPROVEN", 0),
        "partial_count": counts.get("TEST_BOUND_PARTIAL", 0),
        "contract_count": counts.get("TEST_BOUND_CONTRACT", 0),
        "evidence_verified_count": counts.get("EVIDENCE_VERIFIED", 0),
        "complete_scp_claim": "FORBIDDEN",
        "allowed_claim_template": "verified within scope on SHA <40-char-sha>",
    }


def main() -> int:
    import yaml
    binding = yaml.safe_load((ROOT / "spec" / "scp_target_test_coverage.yaml").read_text(encoding="utf-8"))
    reference = yaml.safe_load((ROOT / "spec" / "complete_scp_reference.yaml").read_text(encoding="utf-8"))
    print(json.dumps(compute(binding, reference), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
