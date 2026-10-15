#!/usr/bin/env python3
"""Fail only on HIGH or a medium finding count above the explicit baseline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("--max-medium", type=int, required=True)
    args = parser.parse_args()
    data = json.loads(args.summary.read_text(encoding="utf-8"))
    high = int(data.get("by_severity", {}).get("HIGH", 0))
    medium = int(data.get("by_severity", {}).get("MEDIUM", 0))
    print(json.dumps({"status": "PASS_WITHIN_SCOPE" if high == 0 and medium <= args.max_medium else "FAIL", "high": high, "medium": medium, "max_medium": args.max_medium, "total": data.get("total")}, indent=2))
    if high:
        raise SystemExit("Bandit HIGH findings are not allowed")
    if medium > args.max_medium:
        raise SystemExit(f"Bandit MEDIUM baseline regressed: {medium} > {args.max_medium}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
