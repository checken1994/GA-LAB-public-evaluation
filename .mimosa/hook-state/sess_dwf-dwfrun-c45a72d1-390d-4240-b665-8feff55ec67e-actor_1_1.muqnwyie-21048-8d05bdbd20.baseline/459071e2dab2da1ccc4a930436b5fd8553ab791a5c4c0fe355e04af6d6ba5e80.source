"""Immutable prediction -> Reality resolution calibration ledger (26-P0.08/09).

Calibration measures how well predictions/confidence track later Reality. It is
not an epistemic authority: confidence never upgrades a canonical Verdict.
"""
from __future__ import annotations

import json
from pathlib import Path

from scp.contracts.ids import new_id
from scp.contracts.time import now_utc_iso
from scp.contracts.verdicts import Verdict, parse_verdict
from scp.persistence import FoundationDB

_CALIBRATION_MIGRATIONS = [
    (
        "0001_calibration_ledger",
        [
            """CREATE TABLE IF NOT EXISTS calibration_predictions (
                   prediction_id TEXT PRIMARY KEY,
                   domain TEXT NOT NULL,
                   task_class TEXT NOT NULL,
                   predictor_type TEXT NOT NULL,
                   predictor_id TEXT NOT NULL,
                   predictor_version TEXT,
                   subject_claim_id TEXT,
                   prediction_json TEXT NOT NULL,
                   confidence REAL,
                   semantic_verdict_at_prediction TEXT NOT NULL
                     CHECK(semantic_verdict_at_prediction IN ('VERIFIED','CONTRADICTED','INSUFFICIENT','UNKNOWN')),
                   input_hash TEXT,
                   tested_sha TEXT,
                   policy_hash TEXT,
                   evidence_refs_json TEXT NOT NULL DEFAULT '[]',
                   predicted_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS calibration_resolutions (
                   resolution_id TEXT PRIMARY KEY,
                   prediction_id TEXT NOT NULL,
                   outcome TEXT NOT NULL
                     CHECK(outcome IN ('VERIFIED','CONTRADICTED','INSUFFICIENT','UNKNOWN')),
                   resolver_type TEXT NOT NULL,
                   resolver_id TEXT NOT NULL,
                   evidence_refs_json TEXT NOT NULL,
                   resolved_at TEXT NOT NULL,
                   supersedes_resolution_id TEXT,
                   FOREIGN KEY(prediction_id) REFERENCES calibration_predictions(prediction_id),
                   FOREIGN KEY(supersedes_resolution_id) REFERENCES calibration_resolutions(resolution_id))""",
            "CREATE INDEX IF NOT EXISTS idx_calibration_prediction_domain ON calibration_predictions(domain,task_class)",
            "CREATE INDEX IF NOT EXISTS idx_calibration_resolution_prediction ON calibration_resolutions(prediction_id,resolved_at)",
            """CREATE TRIGGER IF NOT EXISTS calibration_prediction_no_update
                   BEFORE UPDATE ON calibration_predictions
                   BEGIN SELECT RAISE(ABORT, 'calibration prediction is immutable'); END;""",
            """CREATE TRIGGER IF NOT EXISTS calibration_resolution_no_update
                   BEFORE UPDATE ON calibration_resolutions
                   BEGIN SELECT RAISE(ABORT, 'calibration resolution is immutable'); END;""",
        ],
    ),
]


class CalibrationLedger:
    def __init__(self, db_path: str | Path) -> None:
        self.db = FoundationDB(db_path, _CALIBRATION_MIGRATIONS)

    def record_prediction(
        self,
        *,
        domain: str,
        task_class: str,
        predictor_type: str,
        predictor_id: str,
        prediction: object,
        semantic_verdict: Verdict | str = Verdict.UNKNOWN,
        confidence: float | None = None,
        predictor_version: str | None = None,
        subject_claim_id: str | None = None,
        input_hash: str | None = None,
        tested_sha: str | None = None,
        policy_hash: str | None = None,
        evidence_refs: list[str] | tuple[str, ...] = (),
        predicted_at: str | None = None,
    ) -> dict:
        if confidence is not None and not 0.0 <= float(confidence) <= 1.0:
            raise ValueError("confidence must be in [0,1]")
        verdict = parse_verdict(semantic_verdict)
        prediction_id = new_id("pred")
        row = {
            "prediction_id": prediction_id,
            "domain": str(domain).strip() or "unknown",
            "task_class": str(task_class).strip() or "unknown",
            "predictor_type": str(predictor_type).strip() or "unknown",
            "predictor_id": str(predictor_id).strip() or "unknown",
            "predictor_version": predictor_version,
            "subject_claim_id": subject_claim_id,
            "prediction_json": json.dumps(prediction, ensure_ascii=False, sort_keys=True),
            "confidence": None if confidence is None else float(confidence),
            "semantic_verdict_at_prediction": verdict.value,
            "input_hash": input_hash,
            "tested_sha": tested_sha,
            "policy_hash": policy_hash,
            "evidence_refs_json": json.dumps(list(evidence_refs), ensure_ascii=False, sort_keys=True),
            "predicted_at": predicted_at or now_utc_iso(),
        }
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO calibration_predictions
                   (prediction_id,domain,task_class,predictor_type,predictor_id,predictor_version,
                    subject_claim_id,prediction_json,confidence,semantic_verdict_at_prediction,input_hash,
                    tested_sha,policy_hash,evidence_refs_json,predicted_at)
                   VALUES (:prediction_id,:domain,:task_class,:predictor_type,:predictor_id,:predictor_version,
                    :subject_claim_id,:prediction_json,:confidence,:semantic_verdict_at_prediction,:input_hash,
                    :tested_sha,:policy_hash,:evidence_refs_json,:predicted_at)""",
                row,
            )
        return self.get_prediction(prediction_id)

    def resolve(
        self,
        prediction_id: str,
        *,
        outcome: Verdict | str,
        resolver_type: str,
        resolver_id: str,
        evidence_refs: list[str] | tuple[str, ...],
        supersedes_resolution_id: str | None = None,
        resolved_at: str | None = None,
    ) -> dict:
        # A Reality resolution without evidence is not a valid calibration
        # outcome. Keep the prediction unresolved instead of manufacturing truth.
        evidence = [str(item) for item in evidence_refs if str(item).strip()]
        if not evidence:
            raise ValueError("Reality resolution requires at least one evidence reference")
        self.get_prediction(prediction_id)
        verdict = parse_verdict(outcome)
        if supersedes_resolution_id is not None:
            old = self.get_resolution(supersedes_resolution_id)
            if old["prediction_id"] != prediction_id:
                raise ValueError("superseded resolution belongs to a different prediction")
        row = {
            "resolution_id": new_id("res"),
            "prediction_id": prediction_id,
            "outcome": verdict.value,
            "resolver_type": str(resolver_type).strip() or "unknown",
            "resolver_id": str(resolver_id).strip() or "unknown",
            "evidence_refs_json": json.dumps(evidence, ensure_ascii=False, sort_keys=True),
            "resolved_at": resolved_at or now_utc_iso(),
            "supersedes_resolution_id": supersedes_resolution_id,
        }
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO calibration_resolutions
                   (resolution_id,prediction_id,outcome,resolver_type,resolver_id,evidence_refs_json,
                    resolved_at,supersedes_resolution_id)
                   VALUES (:resolution_id,:prediction_id,:outcome,:resolver_type,:resolver_id,
                    :evidence_refs_json,:resolved_at,:supersedes_resolution_id)""",
                row,
            )
        return self.get_resolution(row["resolution_id"])

    def get_prediction(self, prediction_id: str) -> dict:
        rows = self.db.query(
            "SELECT * FROM calibration_predictions WHERE prediction_id=?", (prediction_id,)
        )
        if not rows:
            raise KeyError(prediction_id)
        row = dict(rows[0])
        row["prediction"] = json.loads(row.pop("prediction_json"))
        row["evidence_refs"] = json.loads(row.pop("evidence_refs_json"))
        return row

    def get_resolution(self, resolution_id: str) -> dict:
        rows = self.db.query(
            "SELECT * FROM calibration_resolutions WHERE resolution_id=?", (resolution_id,)
        )
        if not rows:
            raise KeyError(resolution_id)
        row = dict(rows[0])
        row["evidence_refs"] = json.loads(row.pop("evidence_refs_json"))
        return row

    def current_resolution(self, prediction_id: str) -> dict | None:
        """Return the latest non-superseded resolution for a prediction."""
        rows = self.db.query(
            """SELECT r.* FROM calibration_resolutions r
               WHERE r.prediction_id=?
                 AND NOT EXISTS (
                   SELECT 1 FROM calibration_resolutions newer
                   WHERE newer.supersedes_resolution_id=r.resolution_id)
               ORDER BY r.resolved_at DESC, r.resolution_id DESC LIMIT 1""",
            (prediction_id,),
        )
        if not rows:
            return None
        row = dict(rows[0])
        row["evidence_refs"] = json.loads(row.pop("evidence_refs_json"))
        return row

    def metrics(self, *, domain: str | None = None, task_class: str | None = None) -> dict:
        filters: list[str] = []
        params: list[object] = []
        if domain is not None:
            filters.append("p.domain=?")
            params.append(domain)
        if task_class is not None:
            filters.append("p.task_class=?")
            params.append(task_class)
        where = " WHERE " + " AND ".join(filters) if filters else ""
        predictions = self.db.query(
            # `where` joins only hardcoded predicate fragments ("p.domain=?",
            # "p.task_class=?"); user values are bound via `params`.
            "SELECT p.* FROM calibration_predictions p" + where + " ORDER BY p.predicted_at",  # nosec B608 — hardcoded predicate fragments only, values bound via `params`
            params,
        )
        resolved: list[tuple[dict, dict]] = []
        unknown = 0
        insufficient = 0
        for pred in predictions:
            res = self.current_resolution(pred["prediction_id"])
            if res is None:
                continue
            resolved.append((pred, res))
            if res["outcome"] == Verdict.UNKNOWN.value:
                unknown += 1
            if res["outcome"] == Verdict.INSUFFICIENT.value:
                insufficient += 1

        binary: list[tuple[float, float]] = []
        for pred, res in resolved:
            conf = pred["confidence"]
            if conf is None:
                continue
            # P0 only computes a binary score where the prediction itself made
            # a VERIFIED claim and Reality later verified/contradicted it.
            if pred["semantic_verdict_at_prediction"] != Verdict.VERIFIED.value:
                continue
            if res["outcome"] == Verdict.VERIFIED.value:
                binary.append((float(conf), 1.0))
            elif res["outcome"] == Verdict.CONTRADICTED.value:
                binary.append((float(conf), 0.0))

        brier = None
        if binary:
            brier = sum((p - y) ** 2 for p, y in binary) / len(binary)

        buckets: list[dict] = []
        if binary:
            for lo_i in range(10):
                lo = lo_i / 10.0
                hi = 1.0 if lo_i == 9 else (lo_i + 1) / 10.0
                values = [(p, y) for p, y in binary if p >= lo and (p <= hi if lo_i == 9 else p < hi)]
                if not values:
                    continue
                buckets.append({
                    "lo": lo,
                    "hi": hi,
                    "count": len(values),
                    "mean_confidence": sum(p for p, _ in values) / len(values),
                    "accuracy": sum(y for _, y in values) / len(values),
                })
        ece = None
        if binary and buckets:
            total = len(binary)
            ece = sum(
                (bucket["count"] / total) * abs(bucket["mean_confidence"] - bucket["accuracy"])
                for bucket in buckets
            )

        return {
            "count": len(predictions),
            "resolved_count": len(resolved),
            "unresolved_count": len(predictions) - len(resolved),
            "coverage": (len(resolved) / len(predictions)) if predictions else 0.0,
            "unknown_count": unknown,
            "insufficient_count": insufficient,
            "binary_scored_count": len(binary),
            "brier_score": brier,
            "ece": ece,
            "confidence_buckets": buckets,
        }

    def close(self) -> None:
        self.db.close()
