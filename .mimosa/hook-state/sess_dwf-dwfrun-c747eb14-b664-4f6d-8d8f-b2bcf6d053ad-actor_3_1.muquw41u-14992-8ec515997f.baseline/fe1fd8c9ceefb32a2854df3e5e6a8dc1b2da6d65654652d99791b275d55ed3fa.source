"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

#!/usr/bin/env python3
"""
SCP V14 — REALITY ANCHOR
========================
SHA-256 hash của các "ground truth" constants để verify không bị tam chỉnh.

Schema:
  reality_anchor(id, entity, attribute, value, sha256, source, timestamp)
"""
import hashlib
import os
from datetime import datetime

_RUNTIME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import logging

from scp.core.db_manager import db_exec, db_query_all, db_query_one

logger = logging.getLogger("scp.core.anchor")


# ============================================================
# ANCHOR CONSTANTS — các "ground truth" bất biến
# ============================================================
ANCHOR_CONSTANTS = [
    # (entity, attribute, value, source)
    ("speed_of_light", "value", 299792458, "CODATA 2018"),
    ("planck_constant", "value", 6.62607015e-34, "CODATA 2018"),
    ("avogadro_number", "value", 6.02214076e23, "CODATA 2018"),
    ("gravity_acceleration", "value", 9.80665, "CODATA 2018"),
    ("water_molecular_weight", "value", 18.01528, "PubChem"),
    ("ethanol_molecular_weight", "value", 46.06844, "PubChem"),
    ("methane_molecular_weight", "value", 16.04246, "PubChem"),
    ("absolute_zero", "value", -273.15, "CODATA 2018"),
    ("earth_radius_km", "value", 6371, "WGS84"),
    ("pi", "value", 3.141592653589793, "Math constant"),
    ("e", "value", 2.718281828459045, "Math constant"),
    ("golden_ratio", "value", 1.618033988749895, "Math constant"),
    ("hydrogen_atomic_weight", "value", 1.00794, "IUPAC"),
    ("oxygen_atomic_weight", "value", 15.9994, "IUPAC"),
    ("carbon_atomic_weight", "value", 12.0107, "IUPAC"),
    ("nitrogen_atomic_weight", "value", 14.0067, "IUPAC"),
]


class RealityAnchor:
    """Quản lý reality anchor — SHA-256 hash của các ground truth constants."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Tạo bảng reality_anchor trong v13.db."""
        try:
            db_exec("""
                CREATE TABLE IF NOT EXISTS reality_anchor (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity TEXT NOT NULL,
                    attribute TEXT NOT NULL,
                    value TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    source TEXT,
                    timestamp TEXT NOT NULL,
                    UNIQUE(entity, attribute)
                )
            """)
            # Seed anchors if table is empty
            cnt = db_query_one("SELECT COUNT(*) as cnt FROM reality_anchor")
            if cnt and cnt["cnt"] == 0:
                self._seed_anchors()
        except Exception as e:
            logger.warning(f"RealityAnchor init failed: {e}", exc_info=True)

    def _seed_anchors(self):
        """Seed các anchor constants."""
        ts = datetime.now().isoformat()
        for entity, attr, value, source in ANCHOR_CONSTANTS:
            try:
                sha = self._compute_sha(entity, attr, value)
                db_exec(
                    #  TẠI SAO: V104.37 #78 fix embedded a Python `#` comment
                    # INSIDE the SQL string literal. SQLite does NOT treat `#` as a
                    # comment → syntax error → except swallowed it → CODATA constants
                    # NEVER seeded → verify() always returned `no_anchor` → the ENTIRE
                    # anchor subsystem was dead. Fix: keep SQL clean (use `--` if a SQL
                    # comment is ever needed), statement on one logical line.
                    # INSERT OR IGNORE ensures CODATA constants can never be overwritten.
                    "INSERT OR IGNORE INTO reality_anchor "
                    "(entity, attribute, value, sha256, source, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (entity, attr, str(value), sha, source, ts)
                )
            except Exception as e:
                logger.warning(f"Anchor seed failed for {entity}: {e}", exc_info=True)

    @staticmethod
    def _compute_sha(entity: str, attribute: str, value) -> str:
        """Compute SHA-256 of (entity, attribute, value)."""
        s = f"{entity.lower()}|{attribute.lower()}|{value}"
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    def verify(self, entity: str, attribute: str, value) -> dict:
        """
        Verify if (entity, attribute, value) matches anchor.

        Returns: {match: bool, anchor_value: str, sha256: str, source: str}
        """
        try:
            row = db_query_one(
                "SELECT * FROM reality_anchor WHERE entity = ? AND attribute = ?",
                (entity.lower(), attribute.lower())
            )
            if not row:
                return {"match": False, "anchor_value": None, "reason": "no_anchor"}

            anchor_value = row["value"]
            sha_stored = row["sha256"]
            sha_input = self._compute_sha(entity, attribute, value)

            # Compare values (with float tolerance)
            try:
                anchor_float = float(anchor_value)
                value_float = float(value)
                # [V104.37 #79] TẠI SAO: old 0.001*max(abs,1) floor >> Planck 6.6e-34
                # → verify(planck, 0) returned match=True. Fix: relative tolerance
                # with tiny absolute floor for sub-1.0 constants.
                import math as _math
                is_match = _math.isclose(anchor_float, value_float, rel_tol=1e-3, abs_tol=1e-12)
            except (ValueError, TypeError) as exc:
                # silent-by-design: non-numeric values fall back to documented string comparison.
                logger.debug("anchor: numeric compare failed, using string compare: %s", exc, exc_info=True)
                is_match = str(anchor_value).strip().lower() == str(value).strip().lower()

            return {
                "match": is_match,
                "anchor_value": anchor_value,
                "sha256_match": sha_stored == sha_input,
                "source": row["source"],
            }
        except Exception as e:
            logger.debug(f"verify ignored: {e}", exc_info=True)
            return {"match": False, "error": str(e)}

    def get_all_anchors(self) -> list[dict]:
        """Get all anchor entries."""
        try:
            return db_query_all("SELECT * FROM reality_anchor ORDER BY entity")
        except Exception as exc:
            logger.warning("anchor: get_all_anchors query failed: %s", exc, exc_info=True)
            return []

    def get_stats(self) -> dict:
        """Get anchor stats."""
        try:
            cnt = db_query_one("SELECT COUNT(*) as cnt FROM reality_anchor")
            return {"total_anchors": cnt["cnt"] if cnt else 0}
        except Exception as exc:
            logger.warning("anchor: get_stats query failed: %s", exc, exc_info=True)
            return {"total_anchors": 0}

    def add_anchor(self, entity: str, attribute: str, value, source: str = "user") -> bool:
        """Add a new anchor.

         TẠI SAO: was `INSERT OR REPLACE` — allowed anyone to overwrite
        CODATA / seeded constants, defeating the "anchor" guarantee. Now uses
        `INSERT OR IGNORE`: if (entity, attribute) already exists, the existing
        anchor is preserved and we return False (caller knows it was a duplicate).
        Only NEW anchors can be added; existing ones are immutable from this API.
        To update an anchor, use a separate explicit `update_anchor()` that requires
        a higher privilege (not exposed here).

        [EXEC-1 B3] TẠI SAO: was `cur = db_exec(...)` then
        `inserted = getattr(cur, "rowcount", 1) if cur else 1`. But db_exec()
        returns an INT (rowcount), NOT a cursor — so `getattr(int, "rowcount", 1)`
        ALWAYS returned the default 1, meaning add_anchor ALWAYS returned True
        even when the row was ignored (duplicate). The "duplicate detection"
        was dead. Fix: use db_exec's return value directly — INSERT OR IGNORE
        returns 1 if inserted, 0 if ignored (duplicate).
        """
        try:
            sha = self._compute_sha(entity, attribute, value)
            inserted = db_exec(
                "INSERT OR IGNORE INTO reality_anchor (entity, attribute, value, sha256, source, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (entity.lower(), attribute.lower(), str(value), sha, source, datetime.now().isoformat())
            )
            # inserted is the rowcount returned by db_exec (1 = new row,
            # 0 = ignored because duplicate). No `getattr` needed — db_exec
            # always returns an int.
            return bool(inserted and inserted > 0)
        except Exception as e:
            logger.warning(f"add_anchor failed: {e}", exc_info=True)
            return False


# ============================================================
# AUTO-INIT ON IMPORT
# ============================================================
try:
    _anchor = RealityAnchor()
except Exception as e:
    logger.warning("RealityAnchor init failed: %s", e, exc_info=True)
    logger.debug(f"[WARN] RealityAnchor init failed: {e}")
    _anchor = None
