"""World-State Projection (X08): deterministic rebuild from the append log."""
from __future__ import annotations

from scp.contracts.time import parse_utc_iso


class WorldStateProjection:
    def __init__(self, temporal) -> None:
        self.temporal = temporal

    def rebuild(self, *, as_of_system_time: str | None = None) -> dict:
        rows = self.temporal.db.query(
            "SELECT * FROM world_assertions ORDER BY system_time, rowid")
        cutoff = parse_utc_iso(as_of_system_time) if as_of_system_time else None
        system_times = {row["assertion_id"]: parse_utc_iso(row["system_time"]) for row in rows}
        state: dict = {}
        for row in rows:
            row_time = system_times[row["assertion_id"]]
            if cutoff is not None and row_time > cutoff:
                continue
            superseded_by = row["superseded_by"]
            if superseded_by:
                superseder_time = system_times.get(superseded_by)
                if cutoff is None:
                    continue
                if superseder_time is None or superseder_time <= cutoff:
                    continue
            subject = row["subject"]
            state.setdefault(subject, {}).setdefault(row["predicate"], []).append({
                "assertion_id": row["assertion_id"],
                "value": __import__("json").loads(row["value_json"]),
                "epistemic_status": row["epistemic_status"],
                "valid_time": row["valid_time"],
                "system_time": row["system_time"],
            })
        return state

    def current(self, subject: str, predicate: str) -> dict | None:
        state = self.rebuild()
        entries = state.get(subject, {}).get(predicate) or []
        return entries[-1] if entries else None

    def changes(self, subject: str, predicate: str) -> list[dict]:
        rows = self.temporal.db.query(
            """SELECT assertion_id, value_json, valid_time, system_time,
                      epistemic_status, superseded_by
               FROM world_assertions
               WHERE subject=? AND predicate=?
               ORDER BY valid_time, system_time, rowid""",
            (subject, predicate),
        )
        active_rows = [row for row in rows if not row["superseded_by"]]
        changes: list[dict] = []
        previous = None
        for row in active_rows:
            value = __import__("json").loads(row["value_json"])
            if previous is not None and previous["value"] != value:
                changes.append({
                    "from_assertion_id": previous["assertion_id"],
                    "to_assertion_id": row["assertion_id"],
                    "from_value": previous["value"],
                    "to_value": value,
                    "from_valid_time": previous["valid_time"],
                    "to_valid_time": row["valid_time"],
                })
            previous = {"assertion_id": row["assertion_id"], "value": value,
                        "valid_time": row["valid_time"]}
        return changes
