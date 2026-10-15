#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Support running from repository root without installation.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scp.forecast import ForecastContractError, ForecastLedger, ForecastRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SCP R44 fail-closed forecast registry loop")
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    unresolved = sub.add_parser("unresolved")
    unresolved.add_argument("case_id")
    unresolved.add_argument("--reason", required=True)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("case_id")
    resolve.add_argument("--outcome-code", required=True, type=int)
    resolve.add_argument("--evidence-url", required=True)
    resolve.add_argument("--evidence-sha256", required=True)
    resolve.add_argument("--adjudicator-id", required=True)
    resolve.add_argument("--resolved-at")
    resolve.add_argument("--rationale")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        registry = ForecastRegistry.load(args.registry)
        ledger = ForecastLedger(registry, args.ledger)
        if args.command == "status":
            result = ledger.status()
        elif args.command == "unresolved":
            result = ledger.record_unresolved(args.case_id, reason=args.reason)
        else:
            result = ledger.resolve_case(
                args.case_id,
                outcome_code=args.outcome_code,
                evidence_url=args.evidence_url,
                evidence_sha256=args.evidence_sha256,
                adjudicator_id=args.adjudicator_id,
                resolved_at=args.resolved_at,
                rationale=args.rationale,
            )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        if result.get("event") == "resolution_rejected":
            return 4
        return 0
    except ForecastContractError as exc:
        print(json.dumps({"status": "CONTRACT_ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 4
    except OSError as exc:
        print(json.dumps({"status": "IO_ERROR", "error": type(exc).__name__}, ensure_ascii=False), file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
