#!/usr/bin/env python3
"""Deterministic bootstrap/policy layer for SCP system acceptance.

The main runner exercises SCP as an external process. This layer supplies a
second provider *family* on the same loopback fixture so provider-independence
is tested without Internet/API dependency.

It also corrects one acceptance-oracle distinction discovered by the first real
run: HUMAN_REVIEW is an explicit fail-closed decision that only the
contradiction / provider-outage / hard-crash scenarios intentionally create. It
must not be confused with hidden active execution such as RUNNING/VERIFYING/
QUEUED. The final invariant therefore permits only terminal states plus a
HUMAN_REVIEW set that equals the exact expected review task ids (the
same stable-id derivation as the main runner's A12 oracle in
scripts/run_scp_acceptance.py); every other leftover state, and any missing or
unexpected HUMAN_REVIEW task, is rejected. An interrupted suite has incomplete
evidence and cannot satisfy the final invariant.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _arg_value(name: str, default: str) -> str:
    try:
        index = sys.argv.index(name)
    except ValueError:
        return default
    if index + 1 >= len(sys.argv):
        return default
    return sys.argv[index + 1]


def configure_acceptance_environment() -> None:
    provider_port = _arg_value("--provider-port", "18081")
    os.environ["SCP_LLM_FALLBACK_PROVIDERS"] = (
        "acceptance-independent:ACCEPTANCE_PROVIDER_KEY:"
        "ACCEPTANCE_PROVIDER_BASE_URL:ACCEPTANCE_PROVIDER_MODEL"
    )
    os.environ["ACCEPTANCE_PROVIDER_KEY"] = "acceptance-independent-key"
    os.environ["ACCEPTANCE_PROVIDER_BASE_URL"] = f"http://127.0.0.1:{provider_port}/v1"
    os.environ["ACCEPTANCE_PROVIDER_MODEL"] = "acceptance-independent-model"


def _final_state_invariant(suite: Any) -> dict[str, Any]:
    """Require intact evidence and no hidden executable work after the suite."""
    from scp.task_kernel import TaskKernel

    kernel = TaskKernel(suite.runtime.db_path)
    try:
        integrity = kernel.verify_integrity()
        suite_require = __import__("scripts.run_scp_acceptance", fromlist=["require"]).require
        suite_require(integrity.get("quick_check") == "ok", f"SQLite quick_check failed: {integrity}")

        rows = kernel.conn.execute("SELECT task_id, state FROM tasks ORDER BY created_at").fetchall()
        invalid_journals = []
        states = Counter()
        for row in rows:
            states[str(row["state"])] += 1
            verification = kernel.verify_journal(row["task_id"])
            if verification.get("hash_chain_valid") is not True:
                invalid_journals.append(
                    {"task_id": row["task_id"], "state": row["state"], "journal": verification}
                )
        suite_require(not invalid_journals, f"main acceptance journal contains invalid chains: {invalid_journals}")

        # HUMAN_REVIEW is intentionally produced ONLY by the contradiction/
        # provider-outage/hard-crash scenarios. It is explicit unresolved
        # evidence, not hidden active execution. Everything else non-terminal
        # is forbidden at suite end, and HUMAN_REVIEW tasks must belong to the
        # expected review set derived exactly like the main runner's A12
        # oracle. Missing mandatory review tasks are incomplete evidence.
        from scripts.run_scp_acceptance import stable_task_id

        expected_review_ids = {
            stable_task_id("scp-a04-contradiction", suite.contradiction_payload()),
            stable_task_id("scp-a06-provider-outage", suite.verified_payload("a06")),
            stable_task_id("scp-a09-hard-crash", suite.verified_payload("a09")),
        }
        allowed_end_states = {"COMPLETED", "FAILED", "CANCELLED", "HUMAN_REVIEW"}
        hidden_active = [dict(row) for row in rows if row["state"] not in allowed_end_states]
        suite_require(not hidden_active, f"acceptance left hidden active work: {hidden_active}")
        unexpected_reviews = [
            dict(row)
            for row in rows
            if row["state"] == "HUMAN_REVIEW" and row["task_id"] not in expected_review_ids
        ]
        suite_require(
            not unexpected_reviews,
            "acceptance left unexpected HUMAN_REVIEW tasks outside the expected "
            f"review set {sorted(expected_review_ids)}: {unexpected_reviews}",
        )
        observed_reviews = {row["task_id"] for row in rows if row["state"] == "HUMAN_REVIEW"}
        suite_require(
            observed_reviews == expected_review_ids,
            "acceptance review set differs from the exact expected human-review tasks",
        )
        suite_require(
            kernel.pending_review_count() == len(expected_review_ids),
            "TaskKernel review backlog no longer represents every expected "
            "withheld (HUMAN_REVIEW) task",
        )

        return {
            "quick_check": integrity.get("quick_check"),
            "task_count": len(rows),
            "state_counts": dict(states),
            "allowed_end_states": sorted(allowed_end_states),
            "human_review_is_explicit": states.get("HUMAN_REVIEW", 0),
            "human_review_within_expected_set": True,
            "expected_human_review_ids": sorted(expected_review_ids),
            "hidden_active_count": 0,
        }
    finally:
        kernel.close()


def main() -> int:
    configure_acceptance_environment()
    from scripts.run_scp_acceptance import AcceptanceSuite

    class CIAcceptanceSuite(AcceptanceSuite):
        def scenario(
            self,
            scenario_id: str,
            title: str,
            fn: Callable[[], dict[str, Any] | None],
        ) -> None:
            if scenario_id == "SCP-A12":
                return super().scenario(scenario_id, title, lambda: _final_state_invariant(self))
            return super().scenario(scenario_id, title, fn)

    parser = argparse.ArgumentParser(description="Run deterministic SCP system acceptance")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "scp_acceptance_ci")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--provider-port", type=int, default=18081)
    parser.add_argument("--concurrency", type=int, default=6)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    suite = CIAcceptanceSuite(args.output_dir.resolve(), args.port, args.provider_port, args.concurrency)
    passed = suite.run()
    print(f"SCP ACCEPTANCE: {'PASS' if passed else 'FAIL'} — evidence: {suite.report_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
