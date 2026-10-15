import re
import sqlite3
from pathlib import Path

# [SEC-S6] Literal SQL template: the only dynamic part is a table identifier
# taken from sqlite_master introspection and regex-validated below. Keeping the
# statement as a plain constant (no f-string/format/concat of variables into
# SQL text) makes the bounded substitution auditable.
SQL_COUNT_TEMPLATE = 'select count(*) from "@TABLE@"'

path = Path(str(Path(__file__).resolve().parent.parent / "data" / "kb_evolve.sqlite"))
con = sqlite3.connect(path)
try:
    for (name,) in con.execute("select name from sqlite_master where type='table' order by name"):
        try:
            # [SEC-S4] Table names come from sqlite_master introspection; they
            # cannot be parameterized, so only strict identifiers are accepted.
            if not re.fullmatch(r"[A-Za-z0-9_]+", name):
                print(f"{name}=SKIPPED_UNSAFE_NAME")
                continue
            count_sql = SQL_COUNT_TEMPLATE.replace("@TABLE@", name)
            count = con.execute(count_sql).fetchone()[0]  # identifier regex-validated above  # nosec B608
            print(f"{name}={count}")
        except Exception as exc:
            print(f"{name}=ERROR:{type(exc).__name__}")
finally:
    con.close()
