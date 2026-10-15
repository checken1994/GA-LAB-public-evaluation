import json
from pathlib import Path

ROOT = Path(str(Path(__file__).resolve().parent.parent))
BASE = ROOT / ".private-seCRETS" / "release-audit" / "scp-247"
# Correct the case-sensitive Windows path without displaying it.
BASE = ROOT / ".private-secrets" / "release-audit" / "scp-247"
LATEST = BASE / "hourly-latest.json"
JOURNAL = BASE / "hourly-monitor.jsonl"
SENSITIVE = ("secret", "token", "password", "cookie", "prompt", "question", "answer", "email", "credential", "private", "api_key", "apikey", "authorization")
TIME_KEYS = {"timestamp", "timestamp_utc", "checked_at", "completed_at", "created_at", "started_at", "time", "ts"}
STATUS_KEYS = {"status", "state", "result", "verdict", "run_status", "health", "readiness", "decision"}
PROV = ("commit", "head", "run_id", "attempt_id", "step_id", "check_id", "incident_id", "source", "profile", "provenance", "evidence_ref", "generated_at")
BAD_WORDS = ("fail", "degrad", "error", "down", "unhealthy", "unknown", "blocked", "timeout", "crash")
GOOD_WORDS = ("pass", "healthy", "ok", "success", "running", "ready", "complete", "allow")


def classify(value):
    if not isinstance(value, (str, int, float, bool)) or value is None:
        return None
    text = str(value).lower()
    if any(w in text for w in BAD_WORDS):
        return "BAD"
    if any(w in text for w in GOOD_WORDS):
        return "GOOD"
    return "OTHER"


def summarize(value):
    timestamps = []
    classes = []
    provenance = False

    def walk(node):
        nonlocal provenance
        if isinstance(node, dict):
            for key, child in node.items():
                key_s = str(key)
                if any(part in key_s.lower().replace("-", "_") for part in SENSITIVE):
                    continue
                low = key_s.lower()
                if low in TIME_KEYS and isinstance(child, str) and len(child) >= 10 and child[:10].count("-") == 2:
                    timestamps.append(child[:40])
                if low in STATUS_KEYS:
                    category = classify(child)
                    if category:
                        classes.append(category)
                if any(part in low for part in PROV):
                    provenance = True
                if isinstance(child, (dict, list)):
                    walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    unique_timestamps = list(dict.fromkeys(timestamps))
    unique_classes = list(dict.fromkeys(classes))
    return unique_timestamps, unique_classes, provenance


def parse(line):
    try:
        return summarize(json.loads(line)), True
    except (json.JSONDecodeError, TypeError, ValueError):
        return ([], [], False), False


def main():
    if not LATEST.exists() or not JOURNAL.exists():
        print(f"files_present={LATEST.exists() and JOURNAL.exists()}")
        return
    latest, latest_ok = parse(LATEST.read_text(encoding="utf-8-sig"))
    lines = JOURNAL.read_text(encoding="utf-8-sig").splitlines()
    tail = lines[-12:]
    results = [parse(line) for line in tail]
    timestamps = [t for (summary, ok) in results for t in summary[0]]
    categories = [c for (summary, ok) in results for c in summary[1]]
    bad_records = sum(1 for (summary, ok) in results if "BAD" in summary[1])
    provenance_missing = sum(1 for (summary, ok) in results if not summary[2])
    parse_fail = sum(1 for (summary, ok) in results if not ok)
    print(f"latest_parse={'PASS' if latest_ok else 'FAIL'}")
    print(f"latest_timestamp={(latest[0][0] if latest[0] else 'missing')}")
    print(f"latest_status_classes={','.join(latest[1]) or 'none'}")
    print(f"latest_provenance={latest[2]}")
    print(f"journal_total_lines={len(lines)}")
    print(f"journal_tail_records={len(tail)}")
    print(f"tail_parse_fail={parse_fail}")
    print(f"tail_bad_records={bad_records}")
    print(f"tail_provenance_missing={provenance_missing}")
    print(f"tail_first_timestamp={(timestamps[0] if timestamps else 'missing')}")
    print(f"tail_last_timestamp={(timestamps[-1] if timestamps else 'missing')}")
    print(f"tail_status_classes={','.join(sorted(set(categories))) or 'none'}")
    for idx, (summary, ok) in enumerate(results):
        ts = summary[0][0] if summary[0] else "missing"
        cls = ",".join(summary[1]) or "none"
        print(f"tail_record={idx};parse={'PASS' if ok else 'FAIL'};timestamp={ts};status_class={cls};provenance={'yes' if summary[2] else 'no'};bad={'yes' if 'BAD' in summary[1] else 'no'}")


if __name__ == "__main__":
    main()
