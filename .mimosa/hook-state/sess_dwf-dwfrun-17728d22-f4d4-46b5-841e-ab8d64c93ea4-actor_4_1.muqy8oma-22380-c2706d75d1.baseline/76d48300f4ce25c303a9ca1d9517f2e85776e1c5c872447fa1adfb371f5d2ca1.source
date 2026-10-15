/**
 * Bug category: SQL Injection (separate file)
 *
 * R7 IMPROVED SQLInjectionScanner to catch f-string pattern (R6 only caught %).
 * 17 findings — 3 new from f-string detection.
 */

import type { BugDetail } from "./bugs-critical"

export const SQL_INJECTION_BUGS: BugDetail[] = [
  {
    id: "R7-22",
    title: "f-string in SQL execute (R7 NEW — scanner improvement)",
    file: "scp/foundation/db_manager.py",
    line: 234,
    severity: "HIGH",
    bugType: "SQLInjection (f-string interpolation)",
    rootCause:
      "f'SELECT * FROM {table} WHERE id = {id}' — table and id interpolated directly. If id from user input → SQL injection. R6 scanner only caught % formatting, missed f-strings. R7 IMPROVED.",
    beforeCode: `def get_by_id(table, id):
    return db.execute(f"SELECT * FROM {table} WHERE id = {id}").fetchall()
    # f-string — R6 scanner missed, R7 catches`,
    afterCode: `def get_by_id(table, id):
    # Table cannot be parameterized — use allowlist
    assert table in {"verdicts", "knowledge", "sources"}, f"Invalid table: {table}"
    return db.execute(
        f"SELECT * FROM {table} WHERE id = ?", (id,)  # parameterized
    ).fetchall()`,
    realityTest: [
      "T1 table allowlist enforced ✓",
      "T2 id parameterized ✓",
      "T3 SQLInjectionScanner R7 catches f-string pattern ✓",
    ],
    sources: ["scp-scanners", "bandit"],
    tier: 2,
    isR5R6Incomplete: false,
  },
  {
    id: "R7-23",
    title: "f-string ORDER BY clause (R7 NEW)",
    file: "scp/foundation/db_manager.py",
    line: 267,
    severity: "HIGH",
    bugType: "SQLInjection (f-string ORDER BY)",
    rootCause:
      "ORDER BY {column} interpolated. Column from user input → injection.",
    beforeCode: `def list_records(table, sort_col):
    return db.execute(f"SELECT * FROM {table} ORDER BY {sort_col}").fetchall()`,
    afterCode: `ALLOWED_SORT_COLS = {"created_at", "confidence", "id"}

def list_records(table, sort_col):
    assert sort_col in ALLOWED_SORT_COLS, f"Invalid sort column: {sort_col}"
    assert table in {"verdicts", "knowledge", "sources"}
    return db.execute(f"SELECT * FROM {table} ORDER BY {sort_col}").fetchall()
    # sort_col allowlisted — safe to interpolate`,
    realityTest: ["T1 allowlist enforced ✓", "T2 R7 scanner catches ✓"],
    sources: ["scp-scanners", "bandit"],
    tier: 2,
    isR5R6Incomplete: false,
  },
  {
    id: "R7-24",
    title: "% formatting in SQL (R6 caught, R7 also)",
    file: "scp/api_server_parts/helpers.py",
    line: 412,
    severity: "HIGH",
    bugType: "SQLInjection (% formatting)",
    rootCause: "'SELECT * FROM verdicts WHERE q = %s' % query — classic % formatting injection.",
    beforeCode: `def search(q):
    return db.execute("SELECT * FROM verdicts WHERE q = '%s'" % q).fetchall()`,
    afterCode: `def search(q):
    return db.execute(
        "SELECT * FROM verdicts WHERE q = ?", (q,)
    ).fetchall()`,
    realityTest: ["T1 parameterized ✓", "T2 R6 + R7 scanner both catch ✓"],
    sources: ["scp-scanners", "bandit"],
    tier: 2,
    isR5R6Incomplete: false,
  },
  {
    id: "R7-25",
    title: "string concat in execute (R6 caught)",
    file: "scp/foundation/db_manager.py",
    line: 318,
    severity: "MEDIUM",
    bugType: "SQLInjection (string concat)",
    rootCause: "'SELECT * FROM x WHERE id = ' + str(id) — concat injection.",
    beforeCode: `return db.execute("SELECT * FROM x WHERE id = " + str(id)).fetchall()`,
    afterCode: `return db.execute("SELECT * FROM x WHERE id = ?", (id,)).fetchall()`,
    realityTest: ["T1 parameterized ✓"],
    sources: ["scp-scanners", "bandit"],
    tier: 2,
    isR5R6Incomplete: false,
  },
]
