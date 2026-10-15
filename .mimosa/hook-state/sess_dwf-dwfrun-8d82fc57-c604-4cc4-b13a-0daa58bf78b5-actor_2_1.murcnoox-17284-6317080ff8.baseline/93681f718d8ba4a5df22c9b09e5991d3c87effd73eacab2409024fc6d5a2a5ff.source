#!/usr/bin/env python3
"""Reality test for pending-fix human-review behavior.

A review process is only meaningful when a real queued item creates the
operator guidance beside it. This test uses an isolated temporary project,
forces the safe-patch parser to reject a suggestion, and verifies that the
source stays unchanged while a review item and actionable review guide appear.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    import scp.core.code_evolution_agent as evolution

    original_root = evolution.SCP_ROOT
    with tempfile.TemporaryDirectory(prefix="scp-pending-review-reality-") as tmp:
        root = Path(tmp)
        source_dir = root / "scp"
        source_dir.mkdir(parents=True)
        spec_dir = root / "spec"
        spec_dir.mkdir(parents=True)
        (spec_dir / "protected_invariants.yaml").write_text('{"schema_version": 1}', encoding="utf-8")
        
        source = source_dir / "sample_module.py"
        original = "def answer():\n    return 1\n"
        source.write_text(original, encoding="utf-8")

        evolution.SCP_ROOT = root
        try:
            agent = evolution.CodeEvolutionAgent()
            # Deliberately not a SEARCH/REPLACE block and not a fenced function.
            # Correct behavior is to queue for human review, never alter source.
            applied = agent._apply_fix(
                source,
                "Suggested change cannot be represented as a safe automatic patch.",
            )
        finally:
            evolution.SCP_ROOT = original_root

        assert applied is False, "FAIL: unsafe/unparseable suggestion was treated as applied"
        assert source.read_text(encoding="utf-8") == original, (
            "FAIL: source changed even though the suggestion was queued for review"
        )
        print("PASS [1/5]: unparseable suggestion fails closed and source is unchanged")

        pending_dir = root / "pending_fixes"
        pending_items = sorted(p for p in pending_dir.glob("*.py") if p.is_file())
        assert len(pending_items) == 1, (
            f"FAIL: expected exactly one queued review item, found {len(pending_items)}"
        )
        print(f"PASS [2/5]: one concrete review item queued: {pending_items[0].name}")

        queued = pending_items[0].read_text(encoding="utf-8")
        assert "sample_module.py" in queued, "FAIL: queued item is not grounded in its source file"
        assert "Suggested change" in queued, "FAIL: queued item lost the proposed change"
        print("PASS [3/5]: queued item preserves source identity and proposed change")

        readme = pending_dir / "README.md"
        assert readme.exists(), (
            "FAIL: review item exists but README.md was not created beside it — "
            "human-review process is non-operational"
        )
        guide = readme.read_text(encoding="utf-8").lower()
        assert "review" in guide, "FAIL: review guide does not explain review"
        assert any(word in guide for word in ("approve", "reject", "defer")), (
            "FAIL: review guide has no explicit operator decision"
        )
        assert any(word in guide for word in ("apply", "manually")), (
            "FAIL: review guide does not explain how an approved fix is applied"
        )
        print("PASS [4/5]: review guide documents review, decision, and manual apply")

        assert pending_items[0].name in readme.read_text(encoding="utf-8"), (
            "FAIL: review guide is not grounded in the queued item created by this run"
        )
        print("PASS [5/5]: review guide references the concrete queued item")

    print("\n✓ Reality test 4-d-024 PASSED (behavioral human-review invariant)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
