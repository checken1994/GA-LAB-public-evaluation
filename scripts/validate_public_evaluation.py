from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {'.md', '.json', '.jsonl', '.csv', '.yml', '.yaml', '.txt'}
FORBIDDEN_PATTERNS = [
    re.compile(r'OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|AWS_SECRET_ACCESS_KEY'),
    re.compile(r'BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY'),
    re.compile(r'Bearer\s+[A-Za-z0-9._-]{12,}'),
    re.compile(r'C:\\\\Users\\\\check'),
    re.compile(r'/home/ubuntu/'),
    re.compile(r'/tmp/'),
    re.compile(r'\\.env(?:\.|$)'),
]
FORBIDDEN_NAMES = {'.git', '__pycache__', '.pytest_cache', '.mypy_cache', 'node_modules'}
FORBIDDEN_SUFFIXES = {'.log', '.sqlite', '.db', '.pyc', '.bak', '.zip', '.tar', '.gz'}


def main() -> None:
    problems: list[str] = []
    for path in ROOT.rglob('*'):
        relative = path.relative_to(ROOT)
        if '.git' in relative.parts:
            continue
        if any(part in FORBIDDEN_NAMES for part in relative.parts):
            problems.append(f'forbidden directory: {relative}')
        if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
            problems.append(f'forbidden file suffix: {relative}')
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and '.github' not in relative.parts:
            text = path.read_text(encoding='utf-8-sig', errors='replace')
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(text):
                    problems.append(f'forbidden pattern {pattern.pattern!r} in {relative}')
    for path in ROOT.rglob('*.json'):
        if '.git' in path.relative_to(ROOT).parts:
            continue
        try:
            json.loads(path.read_text(encoding='utf-8-sig'))
        except Exception as exc:
            problems.append(f'invalid JSON {path.relative_to(ROOT)}: {exc}')
    review = ROOT / 'REVIEW_SHEET_50.csv'
    if not review.exists():
        problems.append('missing REVIEW_SHEET_50.csv')
    else:
        import csv
        with review.open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != 50:
            problems.append(f'expected 50 review rows, got {len(rows)}')
    if problems:
        print('\n'.join(problems))
        raise SystemExit(1)
    print('public-evaluation checks: PASS')


if __name__ == '__main__':
    main()
