#!/usr/bin/env python3
"""Normalize Bandit JSON into reproducible, exact finding keys."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("Bandit JSON must contain a results list")
    return payload


def summarize(path: Path) -> dict[str, Any]:
    payload = _load(path)
    normalized: list[dict[str, Any]] = []
    for item in payload["results"]:
        if not isinstance(item, dict):
            raise ValueError("Bandit result must be an object")
        test_id = str(item.get("test_id", ""))
        filename = str(item.get("filename", ""))
        line = int(item.get("line_number", 0))
        severity = str(item.get("issue_severity", "")).upper()
        key = f"{test_id}|{filename}|{line}|{severity}"
        normalized.append(
            {
                "key": key,
                "test_id": test_id,
                "filename": filename,
                "line": line,
                "severity": severity,
                "confidence": str(item.get("issue_confidence", "")).upper(),
                "test_name": str(item.get("test_name", "")),
                "issue_text": str(item.get("issue_text", "")),
            }
        )
    normalized.sort(key=lambda item: (item["test_id"], item["filename"], item["line"], item["severity"], item["issue_text"]))
    canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    by_severity = Counter(item["severity"] for item in normalized)
    return {
        "schema_version": 1,
        "source": str(path),
        "total": len(normalized),
        "by_severity": dict(sorted(by_severity.items())),
        "findings_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "findings": normalized,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = summarize(args.report)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
