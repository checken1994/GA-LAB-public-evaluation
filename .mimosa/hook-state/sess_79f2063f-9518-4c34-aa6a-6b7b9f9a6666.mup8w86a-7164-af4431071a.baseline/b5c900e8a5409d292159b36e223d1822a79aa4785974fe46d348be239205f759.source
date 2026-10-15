# [V5.9-SCANNER] SchemaMismatchScanner — detect DB schema drift.
#
# TẠI SAO scanner này tồn tại?
#   PATTERN-MAP audit (SCP_CONTEXT_MEMORY.md section 11): "knowledge table
#   has 5 definitions, 2 PK shapes" — brain.py used `id INTEGER PRIMARY KEY
#   AUTOINCREMENT`, db_manager used `PRIMARY KEY (entity, attribute)`.
#   `CREATE TABLE IF NOT EXISTS` is first-creation-wins → behavior depends
#   on module load order. Race-on-init bug.
#
#   V5.8 consolidated via `_KNOWLEDGE_CANONICAL_DDL` constant — but the
#   pattern can recur for OTHER tables. This scanner detects any new drift.
#
# LOGIC:
#   1. Walk all .py files in scp/ (skip tests, __pycache__)
#   2. Find `CREATE TABLE [IF NOT EXISTS] <name> (<columns>)` (regex)
#   3. Group by table name → for each table with MULTIPLE definitions,
#      compare column sets + PK shape
#   4. If column sets differ OR PK shapes differ → bug "SchemaMismatch"
#
#   NOTE: This is a heuristic — we use regex (not AST) because:
#   - SQL strings inside Python are not parsed by ast (they're just strings)
#   - Regex catches multi-line CREATE TABLE statements with re.DOTALL
#   - We extract column names + PK clause, not full DDL (good enough for drift)
#
# RETURNS:
#   list[BugReport] — bug_type="SchemaMismatch"
from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.schema")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_FILES = 500

# Regex: CREATE TABLE [IF NOT EXISTS] <name> ( <body> )
# - re.DOTALL so body can span multiple lines
# - re.IGNORECASE for case-insensitive SQL
# - Name captures table identifier (allow word chars + underscore)
_CREATE_TABLE_RE = re.compile(
    r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["\'`]?(\w+)["\'`]?\s*\((.*?)\)\s*["\'`]',
    re.IGNORECASE | re.DOTALL,
)

# Skip these tables — they're known to have variant shapes by design
# (e.g. `knowledge_versions` is a separate table from `knowledge`).
# We only flag tables that have INCONSISTENT shapes across files.
# (No hardcoded skip list — let the comparison find real drift.)

# Parse a column body to extract:
#   - column names (lowercased)
#   - PK clause shape ("PRIMARY KEY (a, b)" or "id INTEGER PRIMARY KEY AUTOINCREMENT")
def _parse_columns(body: str) -> tuple[set[str], str]:
    """Parse CREATE TABLE body.

    Returns (column_names_set, pk_shape_string).
    pk_shape is one of:
      - "" (no PK)
      - "single:id"  (id INTEGER PRIMARY KEY AUTOINCREMENT)
      - "composite:a,b"  (PRIMARY KEY (a, b))
      - "inline:colname"  (colname TEXT PRIMARY KEY)
    """
    cols: set[str] = set()
    pk_shape = ""
    # Split on commas (top-level only — naive, but works for SCP schemas)
    # Use a regex split that respects parentheses depth
    parts = _split_top_level(body, ",")

    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Skip standalone constraints (PRIMARY KEY (...), FOREIGN KEY, UNIQUE, etc.)
        upper = part.upper()
        if upper.startswith("PRIMARY KEY"):
            # PRIMARY KEY (a, b) or PRIMARY KEY(a, b)
            m = re.search(r"\(([^)]+)\)", part)
            if m:
                pk_cols = [c.strip().strip('"`[]') for c in m.group(1).split(",")]
                pk_shape = "composite:" + ",".join(c.lower() for c in pk_cols)
            continue
        if upper.startswith(("FOREIGN KEY", "UNIQUE", "CHECK", "CONSTRAINT")):
            continue
        # It's a column def: first token is column name
        # Handle quoted names: "my col" or [my col] or `my col`
        m = re.match(r'["\'`\[]?(\w+)["\'`\]]?\s+(.*)', part)
        if m:
            col_name = m.group(1).lower()
            rest = m.group(2).upper()
            cols.add(col_name)
            # Inline PK: `id INTEGER PRIMARY KEY AUTOINCREMENT` or `x TEXT PRIMARY KEY`
            if "PRIMARY KEY" in rest and "AUTOINCREMENT" in rest:
                pk_shape = "single:" + col_name
            elif "PRIMARY KEY" in rest and not pk_shape:
                pk_shape = "inline:" + col_name
    return cols, pk_shape


def _split_top_level(s: str, sep: str) -> list[str]:
    """Split string on separator, respecting parentheses depth."""
    parts: list[str] = []
    depth = 0
    cur = []
    for c in s:
        if c == "(":
            depth += 1
            cur.append(c)
        elif c == ")":
            depth -= 1
            cur.append(c)
        elif c == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    if cur:
        parts.append("".join(cur))
    return parts


def _iter_python_files(root: Path, limit: int = _MAX_FILES):
    count = 0
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if "tests" in path.parts:
            continue
        if path.name.startswith("test_"):
            continue
        if count >= limit:
            break
        yield path
        count += 1


class SchemaMismatchScanner:
    """Detect CREATE TABLE definitions that drift across files."""

    name: str = "SchemaMismatchScanner"
    bug_type: str = "SchemaMismatch"

    def __init__(self, scp_root: Path | None = None, max_files: int = _MAX_FILES):
        self.scp_root = scp_root or _SCP_ROOT
        self.max_files = max_files

    def scan(self) -> list[BugReport]:
        """Walk scp/ files, group CREATE TABLEs by name, flag drift."""
        # table_name -> list of (file, line, columns, pk_shape, raw_body)
        schemas: dict[str, list[dict]] = defaultdict(list)

        files_scanned = 0
        for path in _iter_python_files(self.scp_root, limit=self.max_files):
            files_scanned += 1
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
            except Exception as read_err:  # noqa: S112
                # silent-by-design: best-effort file read inside scan loop.
                logger.debug("schema_scanner: skipping unreadable file %s: %s", path, read_err, exc_info=True)
                continue
            for m in _CREATE_TABLE_RE.finditer(source):
                table_name = m.group(1).lower()
                body = m.group(2)
                # Compute line number from match position
                line = source.count("\n", 0, m.start()) + 1
                cols, pk_shape = _parse_columns(body)
                schemas[table_name].append({
                    "file": str(path),
                    "line": line,
                    "columns": cols,
                    "pk_shape": pk_shape,
                    "body_preview": body[:200].replace("\n", " "),
                })

        bugs: list[BugReport] = []
        for table_name, defs in schemas.items():
            if len(defs) < 2:
                continue  # only one definition → no drift possible
            # Compare column sets
            col_sets = [frozenset(d["columns"]) for d in defs]
            pk_shapes = [d["pk_shape"] for d in defs]

            # Check 1: column set mismatch
            col_mismatch = len(set(col_sets)) > 1
            # Check 2: PK shape mismatch
            pk_mismatch = len(set(pk_shapes)) > 1

            if not col_mismatch and not pk_mismatch:
                continue  # all definitions identical

            # Build description with file:line for each def
            def_lines = [
                f"  - {Path(d['file']).name}:{d['line']} "
                f"PK={d['pk_shape']!r} cols={sorted(d['columns'])}"
                for d in defs
            ]
            mismatch_type = []
            if col_mismatch:
                mismatch_type.append("column sets differ")
            if pk_mismatch:
                mismatch_type.append(f"PK shapes differ ({set(pk_shapes)})")

            # Report at first definition's location
            first = defs[0]
            bugs.append(BugReport(
                file=first["file"],
                line=first["line"],
                bug_type=self.bug_type,
                description=(
                    f"SchemaMismatch: table {table_name!r} has {len(defs)} "
                    f"different CREATE TABLE definitions across files — "
                    f"{'; '.join(mismatch_type)}. "
                    f"`CREATE TABLE IF NOT EXISTS` is first-creation-wins → "
                    f"behavior depends on module load order (race-on-init).\n"
                    f"Definitions found:\n" + "\n".join(def_lines)
                ),
                suggested_fix=(
                    f"Consolidate all CREATE TABLE {table_name!r} into ONE "
                    f"canonical DDL constant (like _KNOWLEDGE_CANONICAL_DDL "
                    f"in db_manager.py) and import it in every site that "
                    f"creates the table. Add a migration guard to detect "
                    f"legacy shapes and rebuild."
                ),
                tier=BugTier.TIER_3_PERMISSION,  # schema migration → logic
                affects_logic=True,
            ))

        logger.info(
            f"[SchemaMismatchScanner] found {len(bugs)} schema drift(s) "
            f"(scanned {files_scanned} files, {len(schemas)} unique tables)"
        )
        return bugs
