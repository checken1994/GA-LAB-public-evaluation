#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scp.autofix.speculative_prefixer import SpeculativeCache


def _bare_except_pass_count(source: str, filename: str) -> int:
    tree = ast.parse(source, filename=filename)
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler)
        and node.type is None
        and len(node.body) == 1
        and isinstance(node.body[0], ast.Pass)
    )


def _files(root: Path, limit: int) -> list[Path]:
    excluded = {"venv", "node_modules", "__pycache__", ".git", ".private-secrets"}
    result = []
    for path in sorted(root.rglob("*.py")):
        relative_parts = path.relative_to(root).parts
        if any(part in excluded for part in relative_parts):
            continue
        result.append(path)
        if len(result) >= limit:
            break
    return result


def run(root: Path, limit: int, cache_path: Path) -> dict[str, Any]:
    cache = SpeculativeCache(cache_file=str(cache_path), max_entries=max(100, limit * 2), ttl_seconds=3600)
    files_total = 0
    parse_failures = 0
    baseline_findings = 0
    candidate_findings = 0
    candidate_files = 0
    compile_pass = 0
    compile_fail = 0
    multi_finding_files = 0
    records: list[dict[str, Any]] = []
    for path in _files(root, limit):
        files_total += 1
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            baseline = _bare_except_pass_count(source, str(path))
        except (OSError, SyntaxError):
            parse_failures += 1
            continue
        candidate_count = cache.prefetch_candidates(str(path), ["bare_except_pass"], source_override=source)
        baseline_findings += baseline
        candidate_findings += candidate_count
        candidate_files += int(candidate_count > 0)
        multi_finding_files += int(baseline > 1)
        sha16 = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        candidate = cache.lookup(sha16, "bare_except_pass")
        patch_status = "none"
        if candidate is not None:
            try:
                ast.parse(candidate.full_patched_source, filename=str(path))
                compile_pass += 1
                patch_status = "compile_pass"
            except SyntaxError:
                compile_fail += 1
                patch_status = "compile_fail"
        if baseline or candidate_count:
            records.append({
                "path": str(path),
                "baseline_findings": baseline,
                "candidate_findings": candidate_count,
                "lookup_candidate": candidate is not None,
                "patch_status": patch_status,
            })
    return {
        "schema": "scp-bare-except-ab-r44",
        "root": str(root),
        "files_total": files_total,
        "parse_failures": parse_failures,
        "baseline_findings": baseline_findings,
        "candidate_findings": candidate_findings,
        "candidate_files": candidate_files,
        "multi_finding_files": multi_finding_files,
        "compile_pass": compile_pass,
        "compile_fail": compile_fail,
        "independent_true_positive_evidence": 0,
        "independent_false_positive_evidence": 0,
        "ground_truth_available": False,
        "policy_promotion": False,
        "cache_path": str(cache_path),
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCP R44 BareExceptPass A/B harness")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cache", type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 20_000:
        parser.error("--limit must be in [1, 20000]")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cache = args.cache or Path(tempfile.gettempdir()) / "scp-r44-bare-except-cache.json"
    result = run(args.root, args.limit, cache)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
