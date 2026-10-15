"""Run SCP's bounded live mutation gate and write machine-readable evidence."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from mutation_engine import MutationRunError, run_mutation_campaign


TARGETS: dict[str, dict[str, list[str]]] = {
    "scp/task_kernel_parts/taskkernel.py": {
        "functions": [
            "TaskKernel.create_task",
            "TaskKernel.transition",
            "TaskKernel.claim",
            "TaskKernel.start",
            "TaskKernel.commit_completed",
            "TaskKernel.verify_journal",
        ],
        "tests": [
            "tests/T04_kernel/test_task_kernel_mutation_contract.py",
            "tests/T04_kernel/test_kernel_storage.py",
        ],
    },
    "scp/core/capability_token.py": {
        "functions": ["mint_token", "verify_token"],
        "tests": ["tests/T03_capability/test_capability_token_mutation_contract.py"],
    },
    "scp/llm_gateway/client.py": {
        "functions": [
            "CircuitBreaker.__init__",
            "CircuitBreaker.is_open",
            "CircuitBreaker.record_success",
            "CircuitBreaker.record_failure",
        ],
        "tests": [
            "tests/T05_gateway/test_circuit_breaker_mutation_contract.py",
            "tests/T06_verifier/test_gemini_indictment_hardening.py",
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-score", type=float, default=0.40)
    parser.add_argument("--max-mutants", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/mutation/mutation_report.json"),
    )
    parser.add_argument(
        "--target",
        action="append",
        choices=sorted(TARGETS),
        help="Run only a named target (repeatable); default runs all targets.",
    )
    return parser.parse_args()


def _git(command: list[str]) -> str:
    completed = subprocess.run(
        ["git", *command], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    destination = path if path.is_absolute() else REPO_ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)


def main() -> int:
    args = parse_args()
    if not 0.0 <= args.min_score <= 1.0:
        print("ERROR: --min-score must be between 0 and 1", file=sys.stderr)
        return 2
    if args.max_mutants <= 0 or args.timeout_seconds <= 0:
        print("ERROR: max mutants and timeout must be positive", file=sys.stderr)
        return 2

    selected = args.target or list(TARGETS)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit": _git(["rev-parse", "HEAD"]),
        "working_tree_dirty": bool(_git(["status", "--porcelain"])),
        "threshold": args.min_score,
        "max_mutants_per_target": args.max_mutants,
        "targets": [],
        "status": "RUNNING",
    }
    infrastructure_failed = False
    threshold_failed = False

    for target in selected:
        print(f"\n[MUTATION] {target}")
        target_config = TARGETS[target]
        try:
            report = run_mutation_campaign(
                target,
                target_config["tests"],
                repo_root=REPO_ROOT,
                max_mutants=args.max_mutants,
                timeout_seconds=args.timeout_seconds,
                include_functions=target_config["functions"],
            )
            item = report.to_dict()
            item["threshold"] = args.min_score
            item["passed"] = report.score >= args.min_score
            threshold_failed |= not bool(item["passed"])
            payload["targets"].append(item)
            print(
                f"  score={report.score:.1%} killed={report.killed}/"
                f"{len(report.outcomes)} threshold={args.min_score:.1%}"
            )
        except (MutationRunError, OSError, subprocess.SubprocessError) as exc:
            infrastructure_failed = True
            payload["targets"].append(
                {"target": target, "passed": False, "error": f"{type(exc).__name__}: {exc}"}
            )
            print(f"  INVALID EVIDENCE: {type(exc).__name__}: {exc}", file=sys.stderr)

    if infrastructure_failed:
        payload["status"] = "INVALID"
        exit_code = 2
    elif threshold_failed:
        payload["status"] = "FAIL"
        exit_code = 1
    else:
        payload["status"] = "PASS"
        exit_code = 0
    _write_report(args.report, payload)
    print(f"\nRESULT: {payload['status']} (report: {args.report})")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
