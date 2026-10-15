from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CORPUS_SCHEMA = "scp-regression-corpus-r44"
LINEAGES = {"threat_simulator", "benchmark", "real_pc_probe", "reality_test", "unknown"}
_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+"),
)
_PATH_PATTERNS = (
    re.compile(r"(?i)[A-Z]:\\[^\r\n\t ]+"),
    re.compile(r"/home/[^\r\n\t ]+"),
    re.compile(r"/mnt/[^\r\n\t ]+"),
)


class CorpusContractError(ValueError):
    """Raised when a regression corpus row violates the evidence contract."""


@dataclass(frozen=True)
class CorpusConfig:
    max_cases: int = 10_000
    include_unknown: bool = True
    no_policy_promotion: bool = True


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def redact_input(value: Any) -> tuple[str, bool]:
    text = str(value or "")
    redacted = False
    for pattern in _SECRET_PATTERNS:
        text, count = pattern.subn(lambda match: match.group(0).split(match.group(0)[match.group(0).find("=") : match.group(0).find("=") + 1])[0] + "=<REDACTED>" if "=" in match.group(0) else "<REDACTED>", text)
        redacted = redacted or count > 0
    for pattern in _PATH_PATTERNS:
        text, count = pattern.subn("<PATH_REDACTED>", text)
        redacted = redacted or count > 0
    return text[:4000], redacted


def classify_lineage(source: Any, question_type: Any = None) -> str:
    value = str(source or "").lower()
    if "threat_simulator" in value:
        return "threat_simulator"
    if "benchmark" in value:
        return "benchmark"
    if any(token in value for token in ("e2e-real-pc", "real_local", "local_only", "api8010", "api8011", "fixed_trace")):
        return "real_pc_probe"
    if "reality" in value:
        return "reality_test"
    if str(question_type or "").upper() == "INTERNAL":
        return "real_pc_probe"
    return "unknown"


def make_case(row: dict[str, Any], source_artifact: str, source_sha256: str, captured_at: str) -> dict[str, Any]:
    event_id = row.get("id", row.get("event_id", row.get("question_id")))
    raw_input = row.get("question", row.get("prompt", row.get("input", "")))
    input_text, redacted = redact_input(raw_input)
    lineage = classify_lineage(row.get("source"), row.get("question_type"))
    observed = {
        "verdict": row.get("verdict"),
        "domain": row.get("domain"),
        "source": row.get("source"),
        "question_type": row.get("question_type"),
    }
    identity = {
        "source_artifact": source_artifact,
        "source_sha256": source_sha256,
        "source_event_id": event_id,
        "lineage": lineage,
        "input": input_text,
    }
    return {
        "case_id": _sha256_text(_canonical(identity))[:32],
        "source_lineage": lineage,
        "source_artifact": {"path": source_artifact, "sha256": source_sha256},
        "source_event_id": event_id,
        "input": input_text,
        "observed_output": observed,
        "ground_truth": None,
        "provenance": {
            "captured_at": captured_at,
            "extractor": "scp-history-regression-corpus-r44",
            "input_redacted": redacted,
        },
        "replay_policy": {"read_only": True, "bounded": True, "no_policy_promotion": True},
    }


def validate_case(case: dict[str, Any], config: CorpusConfig | None = None) -> None:
    cfg = config or CorpusConfig()
    required = {"case_id", "source_lineage", "source_artifact", "source_event_id", "input", "observed_output", "ground_truth", "provenance", "replay_policy"}
    missing = required - set(case)
    if missing:
        raise CorpusContractError(f"missing corpus fields: {sorted(missing)}")
    if case["source_lineage"] not in LINEAGES:
        raise CorpusContractError("invalid source lineage")
    if case["ground_truth"] is not None and not case["provenance"].get("independent_evidence"):
        raise CorpusContractError("ground_truth requires independent evidence")
    if case["replay_policy"] != {"read_only": True, "bounded": True, "no_policy_promotion": cfg.no_policy_promotion}:
        raise CorpusContractError("unsafe replay policy")
    if "pass=null" in str(case["observed_output"]).lower() and case["source_lineage"] == "reality_test":
        raise CorpusContractError("null reality result cannot become a valid replay label")


def build_cases(rows: Iterable[dict[str, Any]], source_artifact: str, source_sha256: str, config: CorpusConfig | None = None) -> list[dict[str, Any]]:
    cfg = config or CorpusConfig()
    captured_at = datetime.now(timezone.utc).isoformat()
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if index >= cfg.max_cases:
            raise CorpusContractError("corpus case bound exceeded")
        case = make_case(row, source_artifact, source_sha256, captured_at)
        if not cfg.include_unknown and case["source_lineage"] == "unknown":
            continue
        validate_case(case, cfg)
        if case["case_id"] in seen:
            continue
        seen.add(case["case_id"])
        cases.append(case)
    return cases


def write_corpus(cases: Iterable[dict[str, Any]], output: str | Path, source_artifacts: list[dict[str, str]]) -> dict[str, Any]:
    records = list(cases)
    for case in records:
        validate_case(case)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        for case in records:
            handle.write(_canonical(case) + "\n")
    temp.replace(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = {
        "schema": CORPUS_SCHEMA,
        "corpus_sha256": digest,
        "case_count": len(records),
        "lineage_counts": {lineage: sum(case["source_lineage"] == lineage for case in records) for lineage in sorted(LINEAGES)},
        "source_artifacts": source_artifacts,
        "ground_truth_count": sum(case["ground_truth"] is not None for case in records),
        "policy_promotion": False,
        "read_only": True,
    }
    manifest_path = target.with_suffix(target.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


__all__ = ["CORPUS_SCHEMA", "CorpusConfig", "CorpusContractError", "build_cases", "classify_lineage", "make_case", "redact_input", "validate_case", "write_corpus"]
