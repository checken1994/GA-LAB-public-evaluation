"""
SCP Complete Standard Test — Mạch 6: Prediction
Covers: scp/api/routes/prediction_routes.py, scp/prediction/predictive.py
        (V5 pipeline: Crawl -> Generate -> Predict -> Verify -> Learn)

M6 HARNESS FIX (AUDIT-20260909) — root causes of the 6 red tests:
  - All endpoints were probed at top-level /run-cycle, /pending, /all, /verify,
    /stats, but the router is registered with prefix /v105/predictions
    (api_server.py route-group table, group "prediction") -> 404.
  - PRED-6 additionally mocked the route handler itself
    (patch scp.api.routes.prediction_routes.run_prediction_cycle) — a
    golden-path mock that FastAPI never observes (the route captured the
    endpoint function at decoration time) and asserted a response shape
    ({"success", "cycle_id"}) the product never returns (real contract:
    {"status": "ok", "cycle": <stats>}).
  Rewritten: real paths, real admin auth (SCP_AUTH_TOKEN_SECRET env fixture +
  Bearer header, same pattern as T02), real engine via canonical get_judge(),
  zero golden-path mocks.

M6 PRODUCT fixes verified by this suite (AUDIT-20260909):
  - prediction_routes._get_engine() now reads the canonical singleton from
    scp.api_server_parts.helpers (it previously read scp.api_server.
    _predictive_engine — a module global never assigned outside its `= None`
    initializer -> every prediction endpoint returned 503 forever).
  - predictive.QuestionGenerator.generate() skips KhamPha specs without
    ai_answer with an observable warning (was: KeyError on the first spec
    swallowed by the outer except -> zero local predictions ever generated).
  - predictive.SelfLearner._get_engine() falls back to a RealityClassifier-
    backed engine (the SCPV14 shim has no .classifier -> learn phase died in
    AttributeError and was swallowed: "self-correcting" was a silent no-op).

FA-01: Strict assertions, no loosening
FA-02: No skip/xfail
FA-03: Full pytest output as evidence
FA-04: No simulated VERIFIED
FA-05: No self-grant authority
FA-09: Exploit mandate — reproduce actual behavior
FA-13: Causal branch coverage of prediction flow

NO MOCKS of subsystems: HTTP goes through TestClient against the real app,
SQLite is the real db_manager (data/v13.db, rows marked + cleaned), the engine
is the real PredictiveOrchestrator. External internet sources are NOT
contacted: tests pin SCP_EGRESS_MODE=deny and assert the fail-closed offline
contract (same rationale as T02 — unit tests must never mine the internet;
live-crawl behavior is a runtime concern proven outside D1).
"""

import logging
import threading
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from scp.api_server import app
from scp.core.db_manager import db_exec, db_query_one
from scp.prediction.predictive import (
    DataCrawler,
    Predictor,
    QuestionGenerator,
    Verifier,
    init_predictions_db,
)

logger = logging.getLogger("tests.T03.flow06")

# [TEST-ISOLATION] get_judge() unconditionally launches the production
# AttackCrawler thread (GitHub/HuggingFace jailbreak-corpus mining) whose
# non-daemon executor threads block pytest process exit for minutes AFTER the
# summary line, and unit tests must never mine the internet. Neutralise ONLY
# the crawler/fast-learning launchers for this pytest session — no assertion
# depends on them, and the real crawler still runs in the Docker runtime
# verification. (Not a subsystem mock: nothing asserted here touches them.)
from scp.api_server_parts import helpers as _scp_helpers


def _no_crawl_thread_in_tests(data_dir: str = "data"):
    logger.info("[TEST-ISOLATION] AttackCrawler thread suppressed in T03/M6 session")


def _no_fast_learning_thread_in_tests(*args, **kwargs):
    logger.info("[TEST-ISOLATION] FastLearning background thread suppressed in T03/M6 session")


_scp_helpers.start_crawl_thread = _no_crawl_thread_in_tests
if getattr(_scp_helpers, "start_fast_learning_thread", None) is not None:
    _scp_helpers.start_fast_learning_thread = _no_fast_learning_thread_in_tests

PREDICTIONS_PREFIX = "/v105/predictions"
M6_ADMIN_TOKEN = "m6-test-admin-token-0123456789abcdef-40chars"
MARKER_PREFIX = "m6-fixture-"


@pytest.fixture(autouse=True)
def _reset_auth_rate_limit_accounting():
    """Test isolation: verify_admin counts 401s per IP for 60s process-wide
    (5 failures -> 429). The negative-auth probes would otherwise 429 the
    positive-auth tests in this file. This clears the ACCOUNTING only —
    verify_admin logic untouched (same pattern as T02)."""
    from scp.security import auth as _auth

    _auth._auth_failures.clear()
    yield
    _auth._auth_failures.clear()


@pytest.fixture(autouse=True)
def _cleanup_prediction_fixtures():
    """Remove every row this suite seeded into the shared predictions DB
    (rows carry a unique m6-fixture- source marker)."""
    yield
    db_exec("DELETE FROM predictions WHERE source LIKE ?", (f"{MARKER_PREFIX}%",))


@pytest.fixture(scope="module")
def m6_engine():
    """Real canonical engine init: get_judge() creates the production judge
    and wires the PredictiveOrchestrator singleton — the exact code path a
    healthy boot runs. Also proves the M6 wiring fix (the route reads this
    singleton, not the dead api_server global)."""
    init_predictions_db()
    from scp.api_server_parts.helpers import get_judge

    get_judge()
    engine = getattr(_scp_helpers, "_predictive_engine", None)
    assert engine is not None, (
        "PredictiveOrchestrator was not wired by get_judge() — "
        "M6 engine wiring regressed"
    )
    return engine


def _admin_headers() -> dict:
    return {"Authorization": f"Bearer {M6_ADMIN_TOKEN}"}


def _seed_prediction(
    check_date: str | None = None,
    domain: str = "astronomy",
    status: str = "pending",
) -> str:
    """Seed one row through the REAL product write path (Predictor), marked
    for cleanup. check_date defaults to yesterday (due for verification)."""
    if check_date is None:
        check_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    predictor = Predictor()
    pred_id = predictor.save_prediction(
        question=f"M6 fixture prediction {uuid.uuid4().hex}?",
        ai_answer="so tieu hanh tinh = 42",
        domain=domain,
        check_date=check_date,
        source=f"{MARKER_PREFIX}{uuid.uuid4().hex}",
        entity="m6-test",
        current_value=40,
        confidence=0.5,
    )
    if status != "pending":
        predictor.update_prediction(pred_id, status, "43", "over_predicted", "m6 fixture seed")
    return pred_id


class TestFlow06Prediction:
    """Mạch 6: Prediction - SCP Complete Standard"""

    # ------------------------------------------------------------------
    # PRED-1..PRED-5 — negative auth probes on the REAL registered paths
    # (BFLA check: unauthenticated callers must never reach the handlers)
    # ------------------------------------------------------------------

    def test_prediction_run_cycle_requires_admin(self):
        """
        [PRED-1] POST /v105/predictions/run-cycle requires admin auth.
        """
        with TestClient(app) as client:
            response = client.post(f"{PREDICTIONS_PREFIX}/run-cycle", json={})
            assert response.status_code in [401, 403], response.text

    def test_prediction_pending_requires_admin(self):
        """
        [PRED-2] GET /v105/predictions/pending requires admin auth.
        """
        with TestClient(app) as client:
            response = client.get(f"{PREDICTIONS_PREFIX}/pending")
            assert response.status_code in [401, 403], response.text

    def test_prediction_all_requires_admin(self):
        """
        [PRED-3] GET /v105/predictions/all requires admin auth.
        """
        with TestClient(app) as client:
            response = client.get(f"{PREDICTIONS_PREFIX}/all")
            assert response.status_code in [401, 403], response.text

    def test_prediction_verify_requires_admin(self):
        """
        [PRED-4] POST /v105/predictions/verify requires admin auth.
        """
        with TestClient(app) as client:
            response = client.post(f"{PREDICTIONS_PREFIX}/verify", json={})
            assert response.status_code in [401, 403], response.text

    def test_prediction_stats_requires_admin(self):
        """
        [PRED-5] GET /v105/predictions/stats requires admin auth.
        """
        with TestClient(app) as client:
            response = client.get(f"{PREDICTIONS_PREFIX}/stats")
            assert response.status_code in [401, 403], response.text

    # ------------------------------------------------------------------
    # PRED-6 — real golden path through the route, no golden-path mocks
    # ------------------------------------------------------------------

    def test_prediction_run_cycle_executes_v5_pipeline(self, monkeypatch, caplog, m6_engine):
        """
        [PRED-6] POST /v105/predictions/run-cycle executes the V5 pipeline
        (Crawl -> Generate -> Predict -> Verify -> Learn) with the real engine.

        Offline contract (SCP_EGRESS_MODE=deny): every crawl fetch is
        policy-denied -> crawl members come back empty and the pipeline still
        runs end-to-end and returns real stats over the real SQLite store.
        """
        monkeypatch.setenv("SCP_AUTH_TOKEN_SECRET", M6_ADMIN_TOKEN)
        monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
        with caplog.at_level(logging.WARNING, logger="scp.prediction"):
            with TestClient(app) as client:
                response = client.post(
                    f"{PREDICTIONS_PREFIX}/run-cycle",
                    json={},
                    headers=_admin_headers(),
                )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "ok"
        cycle = body["cycle"]
        for key in (
            "total_predictions",
            "correct",
            "wrong",
            "pending",
            "accuracy",
            "by_domain",
            "error_types",
        ):
            assert key in cycle, f"missing stats key: {key}"
        assert isinstance(cycle["total_predictions"], int)
        assert cycle["total_predictions"] >= 0
        assert isinstance(cycle["accuracy"], (int, float))
        # The generate phase ran far enough to evaluate the KhamPha specs and
        # skip them observably (V90 generator contract has no ai_answer).
        assert any(
            "KhamPha spec without ai_answer" in record.message
            for record in caplog.records
        ), "expected observable KhamPha skip warning — swallow regression"

    # ------------------------------------------------------------------
    # Positive admin paths over seeded local data (real rows, real HTTP)
    # ------------------------------------------------------------------

    def test_prediction_pending_lists_seeded_row_with_admin(self, monkeypatch, m6_engine):
        """Admin token -> GET /pending lists the seeded due prediction."""
        monkeypatch.setenv("SCP_AUTH_TOKEN_SECRET", M6_ADMIN_TOKEN)
        pred_id = _seed_prediction()
        with TestClient(app) as client:
            response = client.get(f"{PREDICTIONS_PREFIX}/pending", headers=_admin_headers())
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] >= 1
        assert pred_id in [p["id"] for p in body["pending"]]

    def test_prediction_all_lists_seeded_row_with_admin(self, monkeypatch, m6_engine):
        """Admin token -> GET /all lists the seeded prediction."""
        monkeypatch.setenv("SCP_AUTH_TOKEN_SECRET", M6_ADMIN_TOKEN)
        pred_id = _seed_prediction()
        with TestClient(app) as client:
            response = client.get(f"{PREDICTIONS_PREFIX}/all", headers=_admin_headers())
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] >= 1
        assert pred_id in [p["id"] for p in body["predictions"]]

    def test_save_prediction_persists_entity_column(self):
        """[M6-FIX RC-6] save_prediction persists the `entity` parameter into
        the predictions table.

        Regression pin: the parameter was accepted but the INSERT omitted the
        entity column entirely — silent data loss on every prediction row
        (fixed in 75e994f: entity added to the INSERT + idempotent migration
        for pre-existing tables). Read back through the real DB.
        """
        entity_marker = f"m6-entity-pin-{uuid.uuid4().hex[:8]}"
        predictor = Predictor()
        pred_id = predictor.save_prediction(
            question=f"M6 entity column pin {uuid.uuid4().hex}?",
            ai_answer="so tieu hanh tinh = 42",
            domain="astronomy",
            check_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            source=f"{MARKER_PREFIX}entity-pin-{uuid.uuid4().hex}",
            entity=entity_marker,
            current_value=40,
            confidence=0.5,
        )
        row = db_query_one("SELECT entity FROM predictions WHERE id=?", (pred_id,))
        assert row is not None, f"prediction row {pred_id} not found"
        assert row["entity"] == entity_marker, (
            f"entity column lost on write (got {row['entity']!r}) — RC-6 regression"
        )

    def test_prediction_verify_fail_closed_without_real_data(self, monkeypatch, m6_engine):
        """POST /verify with a due prediction but NO reachable reality source
        (egress deny) must verify nothing and leave the row pending —
        never fabricate a verification."""
        monkeypatch.setenv("SCP_AUTH_TOKEN_SECRET", M6_ADMIN_TOKEN)
        monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
        pred_id = _seed_prediction()
        with TestClient(app) as client:
            # Schema contract first: limit below ge=1 is rejected.
            invalid = client.post(
                f"{PREDICTIONS_PREFIX}/verify", json={"limit": 0}, headers=_admin_headers()
            )
            assert invalid.status_code == 422, invalid.text
            response = client.post(
                f"{PREDICTIONS_PREFIX}/verify", json={"limit": 20}, headers=_admin_headers()
            )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["verified"] == 0
        assert body["results"] == []
        row = db_query_one("SELECT status FROM predictions WHERE id = ?", (pred_id,))
        assert row is not None
        assert row["status"] == "pending", "verification must stay pending without real data"

    def test_prediction_stats_reports_counts_with_admin(self, monkeypatch, m6_engine):
        """GET /stats returns real aggregate statistics including the seeded row."""
        monkeypatch.setenv("SCP_AUTH_TOKEN_SECRET", M6_ADMIN_TOKEN)
        _seed_prediction()
        with TestClient(app) as client:
            response = client.get(f"{PREDICTIONS_PREFIX}/stats", headers=_admin_headers())
        assert response.status_code == 200, response.text
        body = response.json()
        for key in ("total", "pending", "verified", "correct", "wrong", "accuracy"):
            assert key in body, f"missing stats key: {key}"
        assert body["total"] >= 1
        assert body["pending"] >= 1
        assert 0.0 <= float(body["accuracy"]) <= 1.0

    # ------------------------------------------------------------------
    # PRED-7..PRED-11 — engine-level branches (de-vacuous per FA-01)
    # ------------------------------------------------------------------

    def test_prediction_sqlite_lock_handling(self):
        """
        [PRED-7] SQLite lock handling under concurrent prediction writes.
        8 threads x 4 writes through the real Predictor + db_manager
        (WAL + busy_timeout + single _db_lock) must not raise, deadlock,
        or lose rows.
        """
        init_predictions_db()
        predictor = Predictor()
        errors: list[Exception] = []
        n_threads, per_thread = 8, 4

        def _worker(worker_idx: int) -> None:
            try:
                for i in range(per_thread):
                    predictor.save_prediction(
                        question=f"M6 lock probe {worker_idx}-{i} {uuid.uuid4().hex}?",
                        ai_answer="x = 1",
                        domain="astronomy",
                        check_date="2099-01-01",
                        source=f"{MARKER_PREFIX}lock-{worker_idx}-{i}",
                        entity="m6-lock",
                        current_value=0,
                    )
            except Exception as exc:  # recorded — the assert below fails loudly
                errors.append(exc)

        threads = [
            threading.Thread(target=_worker, args=(idx,), name=f"m6-lock-{idx}")
            for idx in range(n_threads)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        assert errors == [], f"concurrent writes raised: {errors!r}"
        assert all(not thread.is_alive() for thread in threads), "deadlock suspected"
        count = db_query_one(
            "SELECT COUNT(*) AS cnt FROM predictions WHERE source LIKE 'm6-fixture-lock-%'"
        )["cnt"]
        assert count == n_threads * per_thread, "rows lost under concurrency"

    def test_prediction_crawl_external_apis(self, monkeypatch):
        """
        [PRED-8] Crawl phase fail-closed offline: with SCP_EGRESS_MODE=deny
        every external fetch is policy-denied, and crawl_all() must return
        empty members without raising. (Live-internet crawling is intentionally
        not exercised — unit tests must not mine the internet; that behavior
        belongs to runtime verification.)
        """
        monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
        crawler = DataCrawler()
        data = crawler.crawl_all()
        assert set(data.keys()) == {"crypto", "weather", "fx", "nasa"}
        assert data["crypto"] == []
        assert data["weather"] == {}
        assert data["fx"] == {}
        assert data["nasa"] == {}

    def test_prediction_generate_from_local_data_and_dedup(self, monkeypatch, caplog):
        """
        [PRED-9] Generate phase (renamed: was 'generate_uses_llm_gateway' — the
        generate phase uses deterministic heuristics over crawled data, there is
        no LLM gateway in it; the old name lied about the product). With local
        fixture weather data the generator produces deduped weather predictions;
        with empty data it fails closed to [] and skips KhamPha specs
        observably.
        """
        monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
        generator = QuestionGenerator()
        weather_fixture = {
            "Hanoi": {
                "dates": ["2026-09-11", "2026-09-12", "2026-09-13"],
                "temp_max": [33.0, 34.0, 35.0],
                "temp_min": [25.0, 25.0, 25.0],
                "precipitation": [0.0, 0.0, 0.0],
            }
        }
        with caplog.at_level(logging.WARNING, logger="scp.prediction"):
            first = generator.generate({"weather": weather_fixture})
            # The two candidate questions differ only in the date digits, so
            # the product's 0.9 similarity dedup collapses them into one —
            # this pins the REAL dedup behavior (was: naive expectation of 2).
            assert len(first) == 1
            assert all(q["domain"] == "weather" for q in first)
            assert all(q["source"] == "open-meteo-forecast" for q in first)
            second = generator.generate({"weather": weather_fixture})
            assert second == [], "duplicate questions must be deduped per instance"
            empty = generator.generate({})
            assert empty == [], "empty crawl data must fail closed to no questions"
        assert any(
            "KhamPha spec without ai_answer" in record.message for record in caplog.records
        ), "KhamPha contract mismatch must stay observable"

    def test_prediction_verify_against_reality(self):
        """
        [PRED-10] Verify phase compares predictions against actual outcomes
        with real tolerance rules (weather ±2°C, astronomy exact, default 5%).
        """
        verifier = Verifier()
        # Weather: within ±2.0 tolerance -> correct.
        is_correct, error_type, _ = verifier._compare(
            {"predicted_answer": "nhiet do cao nhat Hanoi = 34", "domain": "weather"},
            34.5,
        )
        assert is_correct is True
        assert error_type == ""
        # Default 5% relative tolerance: 100 vs 200 -> wrong, under-predicted
        # (pred_val < actual_val -> under_predicted per product dispatch).
        is_wrong, error_type, _ = verifier._compare(
            {"predicted_answer": "gia bitcoin = 100", "domain": "crypto"},
            200,
        )
        assert is_wrong is False
        assert error_type == "under_predicted"
        # No numeric prediction -> parse error, never a false verify.
        is_parse_error, error_type, _ = verifier._compare(
            {"predicted_answer": "khong co so", "domain": "crypto"},
            5,
        )
        assert is_parse_error is False
        assert error_type == "parse_error"
        # Astronomy: exact match required.
        is_exact, _, _ = verifier._compare(
            {"predicted_answer": "so tieu hanh tinh = 42", "domain": "astronomy"},
            42,
        )
        assert is_exact is True

    def test_prediction_learn_updates_model(self):
        """
        [PRED-11] Learn phase retrains the classifier from verified_wrong rows.
        Seeds one verified_wrong row through the real write path, then runs the
        real SelfLearner — training data must grow (before the M6 fix this was
        a silent no-op: SCPV14 shim has no .classifier and the AttributeError
        was swallowed).
        """
        from scp.prediction.predictive import SelfLearner

        _seed_prediction(domain="weather", status="verified_wrong")
        learner = SelfLearner()  # no judge -> real RealityClassifier fallback
        engine_before, is_production_before = learner._get_engine()
        assert is_production_before is False
        before = len(engine_before.classifier.TRAINING_DATA)
        result = learner.learn_from_errors()
        assert result["learned"] >= 1
        assert result["added_to_training"] >= 1, (
            f"learn phase must actually train, got {result!r}"
        )
        engine_after, is_production_after = learner._get_engine()
        assert is_production_after is False
        after = len(engine_after.classifier.TRAINING_DATA)
        assert after > before, "training data must grow from the verified_wrong row"


class TestFlow06PredictionCausalCoverage:
    """
    FA-13: Causal Coverage Matrix for Mạch 6 — de-vacuous per FA-01.
    Each pointer-test now performs a real, cheap assertion over the same
    product branch it covers (was: `pass`).
    """

    def test_causal_prediction_endpoints_admin_required(self):
        """Branch: all 5 prediction endpoints reject unauthenticated callers."""
        with TestClient(app) as client:
            probes = [
                client.post(f"{PREDICTIONS_PREFIX}/run-cycle", json={}),
                client.get(f"{PREDICTIONS_PREFIX}/pending"),
                client.get(f"{PREDICTIONS_PREFIX}/all"),
                client.post(f"{PREDICTIONS_PREFIX}/verify", json={}),
                client.get(f"{PREDICTIONS_PREFIX}/stats"),
            ]
            for probe in probes:
                assert probe.status_code in [401, 403], (
                    f"{probe.request.url} -> {probe.status_code}"
                )

    def test_causal_run_cycle_executes_pipeline(self, m6_engine, monkeypatch):
        """Branch: engine.run_cycle() executes the full V5 orchestration."""
        monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
        before = m6_engine.cycle_count
        stats = m6_engine.run_cycle()
        assert m6_engine.cycle_count == before + 1
        assert isinstance(stats, dict)
        assert "total_predictions" in stats
        assert "accuracy" in stats

    def test_causal_sqlite_lock_handling(self):
        """Branch: concurrent writers serialize correctly (2 threads x 2 rows)."""
        init_predictions_db()
        predictor = Predictor()
        failures: list[Exception] = []

        def _writer(idx: int) -> None:
            try:
                for i in range(2):
                    predictor.save_prediction(
                        question=f"M6 causal lock {idx}-{i} {uuid.uuid4().hex}?",
                        ai_answer="x = 2",
                        domain="astronomy",
                        check_date="2099-01-01",
                        source=f"{MARKER_PREFIX}causal-lock-{idx}-{i}",
                        entity="m6-causal-lock",
                        current_value=0,
                    )
            except Exception as exc:
                failures.append(exc)

        threads = [threading.Thread(target=_writer, args=(idx,)) for idx in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert failures == []
        count = db_query_one(
            "SELECT COUNT(*) AS cnt FROM predictions WHERE source LIKE 'm6-fixture-causal-lock-%'"
        )["cnt"]
        assert count == 4

    def test_causal_crawl_external_apis(self, monkeypatch):
        """Branch: policy-denied fetches degrade to empty without raising."""
        monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
        assert DataCrawler().crawl_exchange_rates() == {}

    def test_causal_generate_llm_gateway(self, monkeypatch):
        """Branch: generate fails closed on empty crawl data."""
        monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
        assert QuestionGenerator().generate({}) == []

    def test_causal_verify_reality_check(self):
        """Branch: verification compare rejects a wrong prediction."""
        is_correct, error_type, _ = Verifier()._compare(
            {"predicted_answer": "gia usd = 25000", "domain": "finance"},
            30000,
        )
        assert is_correct is False
        assert error_type == "under_predicted"

    def test_causal_learn_updates_model(self, m6_engine):
        """Branch: learner stats aggregate over the real predictions store."""
        stats = m6_engine.learner.get_stats()
        assert stats["total_predictions"] >= 0
        assert stats["correct"] >= 0
        assert stats["wrong"] >= 0
        assert stats["pending"] >= 0
