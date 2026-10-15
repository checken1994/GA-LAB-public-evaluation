#!/usr/bin/env python3
import argparse
import json
import re
import sqlite3
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    args = parser.parse_args()
    path = Path(args.db).resolve()
    uri = f'file:{path.as_posix()}?mode=ro'
    result = {'db': str(path), 'read_only': True, 'integrity_check': None, 'tables': {}, 'errors': []}
    # [SEC-S6] Literal SQL template: only the regex-validated table name from
    # sqlite_master introspection is substituted into a constant statement.
    sql_count_template = 'SELECT COUNT(*) FROM "@TABLE@"'
    try:
        with sqlite3.connect(uri, uri=True, timeout=5) as conn:
            result['integrity_check'] = conn.execute('PRAGMA integrity_check').fetchone()[0]
            names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            for name in names:
                # [SEC-S4] Identifiers cannot be parameterized; names come from
                # sqlite_master introspection — enforce strict whitelist first.
                if not re.fullmatch(r"[A-Za-z0-9_]+", name):
                    result['errors'].append(f'{name}: SKIPPED_UNSAFE_NAME')
                    continue
                try:
                    count_sql = sql_count_template.replace('@TABLE@', name)
                    result['tables'][name] = conn.execute(count_sql).fetchone()[0]  # identifier regex-validated above  # nosec B608
                except Exception as exc:
                    result['errors'].append(f'{name}: {type(exc).__name__}: {exc}')
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result['integrity_check'] == 'ok' and not result['errors'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
