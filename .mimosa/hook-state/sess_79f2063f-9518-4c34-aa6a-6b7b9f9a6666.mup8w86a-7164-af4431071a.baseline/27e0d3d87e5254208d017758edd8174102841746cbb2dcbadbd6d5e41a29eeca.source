import json
from pathlib import Path
from typing import Any

ROOT = Path(str(Path(__file__).resolve().parent.parent))
BASE = ROOT / ".private-secrets" / "release-audit" / "scp-247"
LATEST = BASE / "hourly-latest.json"
JOURNAL = BASE / "hourly-monitor.jsonl"

TIMESTAMP_KEYS = {"timestamp", "timestamp_utc", "checked_at", "completed_at", "created_at", "started_at", "time", "ts"}
STATUS_KEYS = {"status", "state", "result", "verdict", "run_status", "health", "readiness", "decision"}
PROVENANCE_PARTS = ("commit", "head", "run_id", "attempt_id", "step_id", "check_id", "incident_id", "source", "profile", "provenance", "evidence_ref", "generated_at")
SENSITIVE_PARTS = ("secret", "token", "password", "cookie", "prompt", "question", "answer", "email", "credential", "private", "api_key", "apikey", "authorization")
COUNT_PARTS = ("count", "checks", "passed", "failed", "degraded", "success", "failure", "total", "restart", "uptime")


def is_sensitive(key: str) -> bool:
    key = key.lower().replace("-", "_")
    return any(part in key for part in SENSITIVE_PARTS)


def normalize_status(value: Any) -> str | None:
    if not isinstance(value, (str, int, float, bool)) or value is None:
        return None
    text = str(value)
    low = text.lower()
    if any(x in low for x in ("fail", "degrad", "error", "down", "unhealthy", "unknown", "blocked", "timeout", "crash")):
        return "BAD:" + text[:40]
    if any(x in low for x in ("pass", "healthy", "ok", "success", "running", "ready", "complete", "allow")):
        return "GOOD:" + text[:40]
    return "OTHER:" + text[:30]


def summarize(value: Any) -> dict[str, Any]:
    timestamps: list[str] = []
    statuses: list[str] = []
    counts: list[str] = []
    provenance = False
    bad = False
    visited = 0

    def walk(node: Any) -> None:
        nonlocal provenance, bad, visited
        if visited >= 20000:
            return
        visited += 1
        if isinstance(node, dict):
            for raw_key, child in node.items():
                key = str(raw_key)
                if is_sensitive(key):
                    continue
                low_key = key.lower()
                if low_key in TIMESTAMP_KEYS and isinstance(child, str) and child[:10].count("-") == 2:
                    timestamps.append(child[:40])
                elif low_key in STATUS_KEYS:
                    norm = normalize_status(child)
                    if norm is not None:
                        statuses.append(norm)
                        bad = bad or norm.startswith("BAD:")
                elif any(part in low_key for part in COUNT_PARTS) and isinstance(child, (int, float)) and not isinstance(child, bool):
                    counts.append(f"{key}={child}")
                elif any(part in low_key for part in PROVENANCE_PARTS):
                    provenance = True
                if isinstance(child, (dict, list)):
                    walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return {
        "timestamps": list(dict.fromkeys(timestamps))[:4],
        "statuses": list(dict.fromkeys(statuses))[:8],
        "counts": list(dict.fromkeys(counts))[:8],
        "provenance": provenance,
        "bad": bad,
        "visited": visited,
    }


def parse_text(text: str) -> tuple[str, dict[str, Any] | None, str, int | None, int | None]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        return "FAIL", None, type(exc).__name__, exc.lineno, exc.colno
    return "PASS", summarize(value), "", None, None


def safe_file_info(path: Path) -> None:
    print(f"file={path.name};exists={path.exists()};bytes={path.stat().st_size if path.exists() else 0}")


def main() -> None:
    safe_file_info(LATEST)
    if LATEST.exists():
        status, summary, error_type, line, col = parse_text(LATEST.read_text(encoding="utf-8-sig"))
        print(f"hourly_latest_parse={status}")
        if summary:
            print(f"hourly_latest_timestamps={'|'.join(summary['timestamps'])}")
            print(f"hourly_latest_statuses={'|'.join(summary['statuses'])}")
            print(f"hourly_latest_counts={'|'.join(summary['counts'])}")
            print(f"hourly_latest_provenance={summary['provenance']}")
            print(f"hourly_latest_bad={summary['bad']}")
        else:
            print(f"hourly_latest_error_type={error_type};line={line};col={col}")

    safe_file_info(JOURNAL)
    if JOURNAL.exists():
        lines = JOURNAL.read_text(encoding="utf-8-sig").splitlines()[-12:]
        print(f"hourly_monitor_tail_records={len(lines)}")
        for index, line_text in enumerate(lines):
            status, summary, error_type, line, col = parse_text(line_text)
            if summary:
                print(f"record={index};parse={status};timestamps={'|'.join(summary['timestamps'])};statuses={'|'.join(summary['statuses'])};counts={'|'.join(summary['counts'])};provenance={summary['provenance']};bad={summary['bad']}")
            else:
                print(f"record={index};parse={status};error_type={error_type};line={line};col={col}")


if __name__ == "__main__":
    main()
