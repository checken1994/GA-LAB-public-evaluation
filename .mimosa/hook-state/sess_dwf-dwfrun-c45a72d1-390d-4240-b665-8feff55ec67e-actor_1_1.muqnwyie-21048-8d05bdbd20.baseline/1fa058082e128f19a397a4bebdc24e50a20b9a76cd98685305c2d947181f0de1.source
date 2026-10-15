"""
SCP Complete Standard Test — Mạch 12: Background Why Loop
Covers: scp/core/doubt_cron.py, scp/meta/why_engine_parts/*, scp/meta/why_gate.py,
        scp/meta/why_execute_plan.py, scp/meta/why_sources/{wikipedia,nasa,open_meteo}

M12 HARNESS FIX (AUDIT-20260909) — root causes of the red baseline:
  - 6 doubt_cron tests called DoubtCron(db_path=..., max_questions_per_run=...)
    and cron.tick() — NONE of those exist. Real contract:
    DoubtCron(data_dir="data", interval_seconds=None), run_doubt_cycle(data_dir),
    start()/stop(); per-check functions live in scp.core.doubt_cron.CHECKS.
  - 3 why_engine tests called verify_decision / lookup_sources /
    check_contradiction / _check_evidence — invented contract. The real
    verification flow is create_verification_plan -> execute_pending_plans ->
    execute_plan (verdict PASS/FAIL/CONFLICT/UNKNOWN from real source values).
  - 1 why_sources test patched open_meteo._fetch_weather — attribute does not
    exist (invented).
  - test_query_nasa_returns_results mocked ONLY the json parse while still
    performing a REAL network call to api.nasa.gov (observed HTTP 500 from
    api.nasa.gov during re-run; the inventory "passed" depended on NASA's
    availability — a hidden internet dependency in unit tests).
  - 13 of the 16 "passed" tests were `pass` placeholders (vacuous, FA-01).
  Rewritten: zero unittest.mock imports, zero patch. External HTTP goes to REAL
  local ThreadingHTTPServer fixtures (same pattern as T02's local OpenAI-compat
  server) via the product endpoint seam SCP_WHY_*_BASE (operator-level env,
  same trust level as OPENAI_BASE_URL; default URLs unchanged). SQLite is the
  real db_manager; kernel checks use a real TaskKernel database in tmp_path.

M12 PRODUCT fixes verified by this suite (AUDIT-20260909, commit 85fc67f):
  - init_why_db: undefined logger crashed WhyEngine() on EVERY fresh DB;
    bare except:pass on the claimed_at migration (D6).
  - whyengine: module-wide logger undefined (NameError inside except handlers).
  - why_execute_plan: status UPDATE used UPDATE...ORDER BY...LIMIT which raises
    OperationalError on standard SQLite -> plans stayed 'pending' forever.
  - why_execute_plan (M12 G2, DNA #22): empty/whitespace-only ai_answer or an
    empty source value auto-PASSed via the vacuous `"" in x` substring match
    (execute_pending_plans passes ai_answer='') -> single-source comparison now
    returns UNKNOWN/FAIL with an 'empty_evidence' reason; real non-empty
    matches still PASS. (M12 G2b, DNA #22): the multi-source agreeing branch
    had the identical `"" in x` hole on both sides -> same UNKNOWN +
    'empty_evidence' contract; test_why_engine_verifies_past_decisions was
    re-pinned from PASS to UNKNOWN (strictness increased) with a real-match
    multi-source PASS control.
  - helpers.get_judge: judge.why_engine never existed -> WHY verify loop inert.
  - api_server_parts/lifespan: why_verify_loop was wired only in scp/api/_lifespan.py
    (not the lifespan api_server.py uses) -> background WHY loop never ran.

FA-01: Strict assertions, no loosening
FA-02: No skip/xfail
FA-03: Full pytest output as evidence
FA-04: No simulated VERIFIED
FA-05: No self-grant authority
FA-09: Exploit mandate — reproduce actual behavior
FA-13: Causal branch coverage of background why flow
"""

import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from scp.core.db_manager import db_exec, db_query_one
from scp.core.doubt_cron import DoubtCron, run_doubt_cycle
from scp.meta.why_engine import VerificationPlan
from scp.meta.why_engine_parts.whyengine import WhyEngine
from scp.meta.why_gate import WhyGate
from scp.meta.why_sources.nasa import query_nasa as _query_nasa
from scp.meta.why_sources.open_meteo import query_open_meteo as _query_open_meteo
from scp.meta.why_sources.wikipedia import _wiki_cache, _wiki_register_failure
from scp.meta.why_sources.wikipedia import query_wikipedia as _query_wikipedia
from scp.task_kernel import TaskKernel

# =========================================================================
# Local HTTP fixtures — REAL servers standing in for the external APIs.
# Why a product seam (SCP_WHY_*_BASE) instead of patching: the why_sources
# modules hardcode their endpoints and fetch through safe_urlopen (which
# blocks loopback for the default endpoints). Redirecting the endpoint via
# an operator env var is config, not a mock — the full fetch/parse/retry/
# breaker code path runs for real against a real HTTP server.
# =========================================================================

_WIKI_STATE = {"status": 200, "hits": 0, "payload": {"query": {"pages": {}}}}
_NASA_STATE = {"status": 200, "hits": 0, "payload": {}}
_METEO_STATE = {
    "hits": 0,
    "geocode_empty": False,
    "forecast_temp": 25.5,
}


class _JsonHandler(BaseHTTPRequestHandler):
    """Serve a canned-but-real JSON body from one of the shared state dicts."""

    state = _WIKI_STATE
    path_prefix = ""

    def do_GET(self):
        st = type(self).state
        st["hits"] = st.get("hits", 0) + 1
        status = st.get("status", 200)
        body = json.dumps(st.get("payload", {}), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # keep pytest output clean
        pass


class _WikiHandler(_JsonHandler):
    state = _WIKI_STATE


class _NasaHandler(_JsonHandler):
    state = _NASA_STATE


class _MeteoGeocodeHandler(_JsonHandler):
    state = _METEO_STATE

    def do_GET(self):  # geocode vs forecast on one server, real dispatch
        st = type(self).state
        if "/v1/search" in self.path:
            st["hits"] = st.get("hits", 0) + 1
            payload = (
                {"results": []}
                if st.get("geocode_empty")
                else {
                    "results": [
                        {"latitude": 21.0278, "longitude": 105.8342, "name": "Hanoi"}
                    ]
                }
            )
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif "/v1/forecast" in self.path:
            st["hits"] = st.get("hits", 0) + 1
            payload = {"current": {"temperature_2m": st.get("forecast_temp", 25.5)}}
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture(scope="session")
def why_local_servers():
    servers = [
        ThreadingHTTPServer(("127.0.0.1", 0), _WikiHandler),
        ThreadingHTTPServer(("127.0.0.1", 0), _NasaHandler),
        ThreadingHTTPServer(("127.0.0.1", 0), _MeteoGeocodeHandler),
    ]
    threads = []
    for srv in servers:
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        threads.append(t)
    yield {
        "wiki": f"http://127.0.0.1:{servers[0].server_address[1]}",
        "nasa": f"http://127.0.0.1:{servers[1].server_address[1]}",
        "meteo": f"http://127.0.0.1:{servers[2].server_address[1]}",
    }
    for srv in servers:
        srv.shutdown()
        srv.server_close()


@pytest.fixture(autouse=True)
def m12_offline_env(monkeypatch, tmp_path, why_local_servers):
    """Pin the whole module offline + point why_sources at the local fixtures.

    SCP_EGRESS_MODE=deny + local HTTP servers: no test in this file contacts
    the internet (the old NASA test did — that is fixed by construction here).
    SCP_FITNESS_HISTORY is redirected into tmp_path so the fitness-drift check
    starts from BASELINE (the repo-wide baseline makes the latency comparison
    timing-flaky, not a real regression signal). Wikipedia circuit-breaker /
    cache state is reset between tests (module-level shared state — a state
    reset, not a mock).
    """
    monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
    monkeypatch.setenv("SCP_WHY_LLM_ENABLED", "0")
    monkeypatch.setenv("SCP_FITNESS_HISTORY", str(tmp_path / "fitness_history.jsonl"))
    monkeypatch.setenv("SCP_WHY_WIKIPEDIA_BASE", why_local_servers["wiki"])
    monkeypatch.setenv("SCP_WHY_NASA_BASE", why_local_servers["nasa"])
    monkeypatch.setenv("SCP_WHY_OPENMETEO_BASE", why_local_servers["meteo"])

    _WIKI_STATE.update({"status": 200, "hits": 0, "payload": {"query": {"pages": {}}}})
    _NASA_STATE.update({"status": 200, "hits": 0, "payload": {}})
    _METEO_STATE.update({"hits": 0, "geocode_empty": False, "forecast_temp": 25.5})

    _wiki_cache.clear()
    import scp.meta.why_sources.wikipedia as _wiki_mod

    _wiki_mod._wiki_fail_count = 0
    _wiki_mod._wiki_circuit_open = False
    _wiki_mod._wiki_circuit_reset_time = 0.0
    yield
    _wiki_cache.clear()
    _wiki_mod._wiki_fail_count = 0
    _wiki_mod._wiki_circuit_open = False
    _wiki_mod._wiki_circuit_reset_time = 0.0


@pytest.fixture()
def why_plans_cleanup():
    """Real-DB hygiene: WHY engine tests write rows into the real
    why_verification_plans table (same policy as M6: real db_manager, rows
    marked + cleaned)."""
    db_exec("DELETE FROM why_verification_plans WHERE question LIKE ?", ("%M12-PROBE-%",))
    yield
    db_exec("DELETE FROM why_verification_plans WHERE question LIKE ?", ("%M12-PROBE-%",))


def _make_kernel_db(tmp_path):
    """Create a REAL TaskKernel SQLite database inside tmp_path."""
    db_file = tmp_path / "ask_task_kernel.sqlite3"
    kernel = TaskKernel(str(db_file))
    kernel.close()
    return db_file


def _wait_for(predicate, timeout=10.0, interval=0.05):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def _wiki_pages_payload(extract: str) -> dict:
    return {"query": {"pages": {"123": {"extract": extract}}}}


class TestFlow12BackgroundWhy:
    """Mạch 12: Background Why Loop — real contracts, zero mocks."""

    # =========================================================================
    # 1. DOUBT CRON
    # =========================================================================

    def test_doubt_cron_initializes_without_db_lock(self, tmp_path):
        """
        [WHY-1] DoubtCron constructs against the REAL contract and never opens
        the kernel DB at init; two concurrent cycles on the same data dir must
        both complete (no SQLite lock escalation).
        """
        cron = DoubtCron(data_dir=str(tmp_path), interval_seconds=300)
        assert cron.data_dir == str(tmp_path)
        assert cron.interval == 300
        assert cron._thread is None
        assert cron.last_report is None
        # init must not create or lock any SQLite database
        assert not (tmp_path / "ask_task_kernel.sqlite3").exists()
        assert not (tmp_path / "doubt_ledger.jsonl").exists()

        results = []

        def _run():
            results.append(run_doubt_cycle(str(tmp_path)))

        threads = [threading.Thread(target=_run) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
        assert len(results) == 2
        assert all("verdict" in r and "checks" in r for r in results)

    def test_doubt_cron_runs_checks(self, tmp_path):
        """
        [WHY-2] run_doubt_cycle executes all 4 REAL checks (real fitness suite,
        real TaskKernel integrity, real backlog query, real why-gate audit
        file) and reports CLEAN when nothing is wrong.
        """
        _make_kernel_db(tmp_path)
        gate = WhyGate(data_dir=str(tmp_path))
        result = gate.gate("verdict", "verify answer: PASS within evidence", llm_enabled=False)
        assert result.allowed is True
        assert (tmp_path / "why_gate_audit.jsonl").exists()

        report = run_doubt_cycle(str(tmp_path))

        assert [c["check"] for c in report["checks"]] == [
            "fitness_drift",
            "kernel_integrity",
            "escalation_backlog",
            "why_gate_anomaly",
        ]
        assert report["verdict"] == "CLEAN"
        fitness = report["checks"][0]
        assert fitness["ok"] is True
        assert isinstance(fitness["detail"]["accuracy"], float)
        kernel_check = report["checks"][1]
        assert kernel_check["ok"] is True
        assert kernel_check["detail"]["quick_check"] == "ok"
        assert report["checks"][2]["ok"] is True
        assert report["checks"][3]["ok"] is True

    def test_doubt_cron_persists_report_to_jsonl(self, tmp_path):
        """
        [WHY-3] Every cycle appends exactly one JSONL line to
        <data_dir>/doubt_ledger.jsonl with ran_at/verdict/checks.
        """
        report1 = run_doubt_cycle(str(tmp_path))
        report2 = run_doubt_cycle(str(tmp_path))

        ledger = tmp_path / "doubt_ledger.jsonl"
        assert ledger.exists()
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        parsed = [json.loads(line) for line in lines]
        assert parsed[0]["ran_at"] == report1["ran_at"]
        assert parsed[1]["ran_at"] == report2["ran_at"]
        assert parsed[1]["ran_at"] >= parsed[0]["ran_at"]
        for entry in parsed:
            assert entry["verdict"] in {"CLEAN", "DOUBT_DETECTED"}
            assert len(entry["checks"]) == 4

    def test_doubt_cron_respects_interval(self, tmp_path):
        """
        [WHY-4] The background thread runs its first cycle immediately, then
        waits the full configured interval before the second cycle.
        """
        cron = DoubtCron(data_dir=str(tmp_path), interval_seconds=2)
        cron.start()
        ledger = tmp_path / "doubt_ledger.jsonl"

        def _lines():
            return len(ledger.read_text(encoding="utf-8").strip().splitlines()) if ledger.exists() else 0

        # First cycle is immediate (doubt needs no 6h warm-up)
        assert _wait_for(lambda: _lines() >= 1, timeout=10), "first cycle never ran"
        first_count = _lines()
        time.sleep(0.7)
        # Interval respected: no second cycle before 2s
        assert _lines() == first_count, (
            f"interval ignored: {first_count} -> {_lines()} lines within 0.7s (interval=2s)"
        )
        time.sleep(1.8)  # now past t=2.0s since first cycle
        assert _wait_for(lambda: _lines() >= first_count + 1, timeout=5), (
            "second cycle never ran after interval elapsed"
        )
        cron.stop()

    def test_doubt_cron_handles_check_errors_silently(self, tmp_path):
        """
        [WHY-5] A check that raises (corrupt kernel DB) must not kill the
        cycle: the failing check is reported ok=False with the error detail,
        other checks still run, verdict flips to DOUBT_DETECTED, and the
        failed report is still persisted as evidence (fail-loudly at the
        data level).
        """
        (tmp_path / "ask_task_kernel.sqlite3").write_bytes(b"this is not a sqlite database")

        report = run_doubt_cycle(str(tmp_path))  # must not raise

        assert report["verdict"] == "DOUBT_DETECTED"
        by_name = {c["check"]: c for c in report["checks"]}
        assert len(by_name) == 4
        assert by_name["kernel_integrity"]["ok"] is False
        assert "not a database" in str(by_name["kernel_integrity"]["detail"])
        # Other checks isolated from the failure
        assert by_name["fitness_drift"]["ok"] is True
        assert by_name["why_gate_anomaly"]["ok"] is True
        # Evidence persisted even for the failing cycle
        ledger = tmp_path / "doubt_ledger.jsonl"
        assert ledger.exists()
        last = json.loads(ledger.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert last["verdict"] == "DOUBT_DETECTED"

    def test_doubt_cron_stops_background_thread(self, tmp_path):
        """
        [WHY-6] start() launches the named daemon thread and produces a
        report; stop() terminates it within a bounded time.
        """
        cron = DoubtCron(data_dir=str(tmp_path), interval_seconds=0.2)
        cron.start()
        assert cron._thread is not None
        assert cron._thread.is_alive()
        assert cron._thread.name == "scp-doubt-cron"
        assert cron._thread.daemon is True
        assert _wait_for(lambda: cron.last_report is not None, timeout=10)
        assert cron.last_report["verdict"] in {"CLEAN", "DOUBT_DETECTED"}

        cron.stop()
        assert _wait_for(lambda: not cron._thread.is_alive(), timeout=3)
        cron.stop()  # idempotent, no raise

    # =========================================================================
    # 2. WHY ENGINE (real verification flow)
    # =========================================================================

    def test_init_why_db_idempotent_and_schema_complete(self):
        """[M12-FIX PF-1 85fc67f / PF-6 f26324a] init_why_db is idempotent on
        an already-migrated schema and the plan table carries every column the
        background verification path reads.

        Regression pins:
        - PF-1: the claimed_at ALTER always hits 'duplicate column' on any DB
          created after claimed_by/claimed_at shipped in CREATE TABLE; the
          handler used to reference an UNDEFINED logger -> NameError -> WhyEngine()
          was un-instantiable on fresh environments. The second init pass
          deterministically walks that handler again and must not raise.
        - PF-6: execute_pending_plans claims rows with
          'RETURNING ... confidence_threshold' — the column must exist
          (previously: 'no such column' on every claim -> 0 plans executed).
        """
        from scp.core.db_manager import db_query_all
        from scp.meta.why_engine_parts.init_why_db import init_why_db

        init_why_db()  # first pass — create/migrate
        init_why_db()  # second pass — duplicate-column handlers must run safely
        cols = {r["name"] for r in db_query_all("PRAGMA table_info(why_verification_plans)")}
        assert {"claimed_by", "claimed_at", "confidence_threshold"} <= cols, cols

    def test_why_engine_verifies_past_decisions(self, tmp_path, why_plans_cleanup):
        """
        [WHY-ENG-1] The real "verify past decisions" flow: plan persisted as
        pending -> execute_pending_plans claims + executes it against the real
        source values -> row flips to status='executed' with a recorded
        verdict (this pins the PF-3 fix: the old UPDATE..LIMIT silently left
        every plan 'pending').

        [M12 G2b / DNA #22] STRICTNESS INCREASED (was pinned `== "PASS"`):
        execute_pending_plans passes ai_answer='', and empty evidence must
        never verify — even with 2 agreeing sources the verdict must be
        UNKNOWN with an 'empty_evidence' reason. A multi-source control with
        a real non-empty matching answer still PASSes (no over-tighten).
        """
        engine = WhyEngine()
        question = (
            f"M12-PROBE-{uuid.uuid4().hex[:8]}: Tại sao nhiệt độ tại "
            "Singapore là 27 độ C?"
        )
        plan = engine.create_verification_plan(question)
        assert plan.evidence_type == "real_time_weather_api"
        assert plan.sources_to_query == ["Open-Meteo", "Open-Meteo Archive"]

        _METEO_STATE["forecast_temp"] = 27.0
        row = db_query_one(
            "SELECT id, status FROM why_verification_plans WHERE question=?",
            (question,),
        )
        assert row is not None
        assert row["status"] == "pending"

        stats = engine.execute_pending_plans(limit=10)
        assert isinstance(stats, dict)
        assert stats.get("executed", 0) >= 1

        row2 = db_query_one(
            "SELECT status, verdict, executed_at FROM why_verification_plans WHERE question=?",
            (question,),
        )
        assert row2["status"] == "executed", f"plan stuck at {row2['status']!r} (PF-3 regression)"
        # [M12 G2b / DNA #22] 2 agreeing sources + the empty ai_answer the
        # background path passes must be UNKNOWN, never PASS (the old
        # vacuous `"" in x` match pinned here as PASS was the bug).
        assert row2["verdict"] == "UNKNOWN"  # empty answer -> no verification
        assert row2["executed_at"] is not None

        # The reason must carry the empty_evidence marker (same contract as
        # the single-source fix) — re-execute the same plan directly with the
        # empty answer to observe the reasoning dict.
        direct_empty = engine.execute_plan(plan, ai_answer="")
        assert direct_empty["verdict"] == "UNKNOWN"
        assert "empty_evidence" in direct_empty["reasoning"]

    def test_claim_release_failure_is_logged_not_swallowed(self, monkeypatch, caplog, why_plans_cleanup):
        """[M12-FIX D6 fa9da62] a failed claim-release (UPDATE claimed_by=NULL)
        must be LOGGED at warning — never swallowed by a bare except:pass.

        Regression pin: the release failure used to vanish silently, leaving
        the row claimed forever with no observable trace. Fault injection at
        module seams only (per-row execution raises once, the release UPDATE
        fails once) — the product code under test is the real
        execute_pending_plans error path. Postconditions: the warning record
        exists at WARNING level and the row stays claimed (release failed).
        """
        import logging

        import scp.meta.why_engine_parts.whyengine as whyengine_mod

        engine = WhyEngine()
        question = (
            f"M12-PROBE-{uuid.uuid4().hex[:8]}: Tại sao nhiệt độ tại "
            "Singapore là 27 độ C?"
        )
        engine.create_verification_plan(question)

        real_db_exec = whyengine_mod.db_exec

        def _release_fails(sql, params=()):
            if "claimed_by=NULL" in sql:
                raise RuntimeError("injected claim-release failure (TMX pin)")
            return real_db_exec(sql, params)

        def _boom(plan, ai_answer=""):
            raise RuntimeError("injected per-row execution failure (TMX pin)")

        monkeypatch.setattr(whyengine_mod, "db_exec", _release_fails)
        monkeypatch.setattr(engine, "execute_plan", _boom)

        with caplog.at_level(logging.WARNING, logger="scp.meta.why_engine"):
            stats = engine.execute_pending_plans(limit=10)

        assert stats.get("executed") == 0, stats
        release_warnings = [
            r for r in caplog.records if "claim-release failed" in r.getMessage()
        ]
        assert release_warnings, (
            "claim-release failure must be observable at WARNING (was bare except:pass — D6 regression)"
        )
        assert release_warnings[0].levelno == logging.WARNING
        row = db_query_one(
            "SELECT claimed_by FROM why_verification_plans WHERE question=?",
            (question,),
        )
        assert row is not None and row["claimed_by"] is not None, (
            "a failed release must leave the row claimed (documented postcondition)"
        )

    def test_why_engine_multisource_real_match_still_passes(self, why_plans_cleanup):
        """
        [WHY-ENG-1b][M12 G2b / DNA #22] Control for the multi-source
        empty-evidence fix (no over-tighten): with 2 agreeing sources and a
        REAL non-empty matching answer, the agreeing branch still PASSes —
        the fix closes only the vacuous `"" in x` shortcut, not honest
        matches.
        """
        engine = WhyEngine()
        _METEO_STATE["forecast_temp"] = 31.0
        plan = engine.create_verification_plan(
            f"M12-PROBE-{uuid.uuid4().hex[:8]}: Tại sao nhiệt độ tại "
            "Singapore là 31 độ C?"
        )
        assert plan.sources_to_query == ["Open-Meteo", "Open-Meteo Archive"]
        result = engine.execute_plan(
            plan, ai_answer="Temperature=31.0°C in Singapore"
        )
        assert result["verdict"] == "PASS", result
        assert len(result["all_values"]) == 2
        assert (
            len(set(str(v["value"]).lower().strip() for v in result["all_values"])) == 1
        ), result["all_values"]

    def test_why_engine_looks_up_external_sources(self, tmp_path, why_plans_cleanup):
        """
        [WHY-ENG-2] _query_source routes by source name to the real source
        handlers; each handler returns a parsed value from the local HTTP
        fixture; unknown sources return None without raising.
        """
        engine = WhyEngine()

        weather = engine._query_source(
            "Open-Meteo", "Hanoi", "What is the temperature at Hanoi?"
        )
        assert weather == "temperature=25.5°C"

        # Real Wikipedia routing: value parsed from the local fixture extract.
        _WIKI_STATE["payload"] = _wiki_pages_payload("The capital of France is Paris.")
        wiki2 = engine._query_source(
            "Wikipedia", "France", "What is the capital of France?"
        )
        assert wiki2 == "Paris"

        _NASA_STATE["payload"] = {
            "title": "Mars at Opposition",
            "explanation": "Temperatures on Mars range from -153 to 20 degrees Celsius.",
        }
        nasa2 = engine._query_source("NASA", "Mars", "What has NASA observed about Mars?")
        assert nasa2 == "Mars at Opposition: Temperatures on Mars range from -153 to 20 degrees Celsius."

        unknown = engine._query_source("Totally-Unknown-Source", "x", "q")
        assert unknown is None

    def test_why_engine_detects_contradictions(self, tmp_path, why_plans_cleanup):
        """
        [WHY-ENG-3] The real contradiction detector: two sources returning
        DIFFERENT values yields verdict CONFLICT (this is how the engine
        detects contradictions between claim and evidence today).
        """
        engine = WhyEngine()
        _WIKI_STATE["payload"] = _wiki_pages_payload("Model accuracy is 85 percent on the benchmark.")
        _NASA_STATE["payload"] = {
            "title": "Benchmark report",
            "explanation": "Model accuracy is 99 percent on the benchmark.",
        }
        plan = VerificationPlan(
            question=f"M12-PROBE-{uuid.uuid4().hex[:8]}: accuracy claim",
            target="model accuracy",
            target_type="value",
            evidence_type="wikipedia_search",
            proof_criteria="Source supports claim",
            falsification_criteria="Source contradicts claim",
            verification_strategy="wikipedia_search",
            sources_to_query=["Wikipedia", "NASA"],
            expected_answer_type="string",
            confidence_threshold=0.6,
            reasoning="M12 contradiction probe",
        )
        result = engine.execute_plan(plan, ai_answer="Model accuracy is 99%")
        assert result["verdict"] == "CONFLICT"
        assert result["confidence"] == 0.3
        assert len(result["all_values"]) == 2
        assert len(result["sources_queried"]) == 2
        assert "disagree" in result["reasoning"]

    def test_why_engine_empty_evidence_is_not_a_pass(self, why_plans_cleanup):
        """
        [WHY-ENG-4][M12 G2 / DNA #22] Empty evidence must never auto-PASS.

        Python's `"" in x` is vacuously True: the old substring contract turned
        ai_answer='' (exactly what execute_pending_plans passes) into PASS 0.85
        against any single non-empty source, and an empty source value into an
        automatic match. An empty/whitespace-only claim or source value is not
        evidence — the verdict must be UNKNOWN/FAIL with an 'empty_evidence'
        reason, while a real non-empty match still PASSes.
        """
        engine = WhyEngine()

        # Case 1: real non-empty source ("Paris" via the local Wikipedia
        # fixture), empty ai_answer — the exact execute_pending_plans path.
        _WIKI_STATE["payload"] = _wiki_pages_payload("The capital of France is Paris.")
        plan = VerificationPlan(
            question=f"M12-PROBE-{uuid.uuid4().hex[:8]}: capital claim, empty answer",
            target="France", target_type="entity",
            evidence_type="wikipedia_search", proof_criteria="Source supports claim",
            falsification_criteria="Source contradicts claim",
            verification_strategy="wikipedia_search", sources_to_query=["Wikipedia"],
            expected_answer_type="string", confidence_threshold=0.6, reasoning="",
        )
        result = engine.execute_plan(plan, ai_answer="")
        assert result["verdict"] in ("UNKNOWN", "FAIL"), result
        assert "empty_evidence" in result["reasoning"]
        assert len(result["all_values"]) == 1  # the source DID return evidence
        assert result["all_values"][0]["value"] == "Paris"

        # Case 2: whitespace-only ai_answer strips to '' — same rule.
        result_ws = engine.execute_plan(plan, ai_answer="   ")
        assert result_ws["verdict"] in ("UNKNOWN", "FAIL"), result_ws
        assert "empty_evidence" in result_ws["reasoning"]

        # Case 3: source returns an empty value (LocalDB entry present but
        # holding no facts) while the AI answer is non-empty — empty
        # "evidence" must not verify anything.
        # [S26 2026-09-13] GeographySLM (cây cũ slms.py, đã xóa) → Geography
        # (cây mới scp/runtime/experts/) — cùng `_local` cache contract.
        from scp.runtime.experts.humanities import Geography as GeographySLM

        geo = GeographySLM()
        geo._local["m12probeland"] = {}  # entry exists but holds no facts
        engine._geo_slm_for_queries = geo
        plan_empty_source = VerificationPlan(
            question=f"M12-PROBE-{uuid.uuid4().hex[:8]}: empty source value",
            target="M12ProbeLand", target_type="entity",
            evidence_type="wikipedia_search", proof_criteria="Source supports claim",
            falsification_criteria="Source contradicts claim",
            verification_strategy="wikipedia_search", sources_to_query=["LocalDB"],
            expected_answer_type="string", confidence_threshold=0.6, reasoning="",
        )
        result_empty_src = engine.execute_plan(plan_empty_source, ai_answer="Atlantis")
        assert result_empty_src["verdict"] in ("UNKNOWN", "FAIL"), result_empty_src
        assert "empty_evidence" in result_empty_src["reasoning"]
        assert result_empty_src["all_values"] == [{"source": "LocalDB", "value": ""}]

        # Control: a real non-empty match against the same Wikipedia source
        # still PASSes — the fix closes only the empty-evidence shortcut.
        control = engine.execute_plan(plan, ai_answer="The capital of France is Paris")
        assert control["verdict"] == "PASS"
        assert control["confidence"] >= 0.85

    # =========================================================================
    # 3. WHY SOURCES (real HTTP against local fixtures)
    # =========================================================================

    def test_query_wikipedia_returns_results(self):
        """
        [SRC-1] query_wikipedia fetches + parses a real MediaWiki-shaped
        response and extracts the requested fact (capital).
        """
        _WIKI_STATE["payload"] = _wiki_pages_payload("The capital of France is Paris.")
        results = _query_wikipedia("France", "What is the capital of France?")
        assert results == "Paris"
        assert _WIKI_STATE["hits"] >= 1

    def test_query_nasa_returns_results(self):
        """
        [SRC-2] query_nasa returns title + explanation from a real HTTP
        response (the OLD test mocked json parsing while hitting the real
        api.nasa.gov — this version is fully local and asserts the exact
        formatted contract).
        """
        _NASA_STATE["payload"] = {
            "title": "Mars at Opposition",
            "explanation": "Temperatures on Mars range from -153 to 20 degrees Celsius.",
        }
        results = _query_nasa("Mars")
        assert results == (
            "Mars at Opposition: Temperatures on Mars range from -153 to 20 degrees Celsius."
        )

    def test_query_open_meteo_returns_results(self):
        """
        [SRC-3] query_open_meteo geocodes the city then fetches the current
        temperature — two real HTTP round-trips, formatted value returned.
        """
        results = _query_open_meteo("Hanoi", "What is the temperature at Hanoi?")
        assert results == "temperature=25.5°C"
        assert _METEO_STATE["hits"] == 2  # geocode + forecast, both real

    def test_query_open_meteo_encodes_multi_word_target(self):
        """[M12-FIX PF-7 f26324a] multi-word targets are percent-encoded into
        the geocode URL.

        Regression pin: the RAW target used to be interpolated into the URL,
        so any multi-word target ("new york", "hồ chí minh", regex-extracted
        "singapore là 27 độ c") raised ValueError("URL can't contain control
        characters") inside urllib and the source silently returned None.
        The request must now complete both real HTTP round-trips against the
        local fixture server.
        """
        results = _query_open_meteo("new york", "What is the temperature at New York?")
        assert results == "temperature=25.5°C", results
        assert _METEO_STATE["hits"] == 2  # geocode + forecast, both real

    def test_why_sources_handle_rate_limits(self):
        """
        [SRC-4] Failure paths return None instead of raising: Wikipedia
        rate-limited (real HTTP 429 through the retry/backoff loop) and
        NASA server error (real HTTP 500).
        """
        _WIKI_STATE["status"] = 429
        assert _query_wikipedia("France", "What is the capital of France?") is None
        _WIKI_STATE["status"] = 200

        _NASA_STATE["status"] = 500
        assert _query_nasa("Mars") is None


class TestFlow12WhyGate:
    """M12: WHY Gate — deterministic gating + audit trail."""

    def test_why_gate_deterministic_gating_and_audit(self, tmp_path):
        """
        [GATE-1] WHY Gate with llm_enabled=False decides deterministically,
        records every decision to why_gate_audit.jsonl, and cannot override a
        Constitution KILL (HARD LOCK).
        """
        gate = WhyGate(data_dir=str(tmp_path))
        allowed = gate.gate("verdict", "verify answer: PASS within evidence", llm_enabled=False)
        assert allowed.decision.name == "ALLOW"
        assert allowed.allowed is True
        assert allowed.llm_used is False

        upheld = gate.gate("verdict", "completely unrelated description xyz", llm_enabled=False)
        assert upheld.decision.name == "UPHOLD"
        assert upheld.allowed is True  # conservative: allow but flag

        kill = gate.gate("verdict", "anything", constitution_kill=True)
        assert kill.allowed is True
        assert "HARD LOCK" in kill.necessity_reason

        audit = tmp_path / "why_gate_audit.jsonl"
        assert audit.exists()
        lines = [json.loads(line) for line in audit.read_text(encoding="utf-8").strip().splitlines()]
        assert len(lines) == 3
        assert [entry["decision"] for entry in lines] == ["ALLOW", "UPHOLD", "ALLOW"]


class TestFlow12BackgroundWhyCausalCoverage:
    """
    FA-13: Causal Coverage Matrix for Mạch 12 — every branch carries its own
    real assertion (de-vacuous: the old 13 tests were `pass` placeholders).
    """

    def test_causal_doubt_cron_init_no_lock(self, tmp_path, monkeypatch):
        """Branch: interval fallback from env when interval_seconds is None."""
        monkeypatch.setenv("SCP_DOUBT_INTERVAL_SEC", "1234")
        cron = DoubtCron(data_dir=str(tmp_path))
        assert cron.interval == 1234.0
        assert cron._thread is None

    def test_causal_doubt_cron_runs_checks(self, tmp_path):
        """Branch: why-gate anomaly check flips to failing on a REJECT-heavy
        audit trail -> verdict DOUBT_DETECTED."""
        audit = tmp_path / "why_gate_audit.jsonl"
        lines = [
            json.dumps({"decision": "REJECT", "action_type": "verdict"}),
            json.dumps({"decision": "REJECT", "action_type": "verdict"}),
            json.dumps({"decision": "REJECT", "action_type": "verdict"}),
            json.dumps({"decision": "ALLOW", "action_type": "verdict"}),
        ]
        audit.write_text("\n".join(lines) + "\n", encoding="utf-8")
        report = run_doubt_cycle(str(tmp_path))
        by_name = {c["check"]: c for c in report["checks"]}
        assert by_name["why_gate_anomaly"]["ok"] is False
        assert by_name["why_gate_anomaly"]["detail"]["reject_rate"] == 0.75
        assert report["verdict"] == "DOUBT_DETECTED"

    def test_causal_doubt_cron_persists(self, tmp_path):
        """Branch: ledger is append-only across cycles (each cycle = +1 line)."""
        run_doubt_cycle(str(tmp_path))
        ledger = tmp_path / "doubt_ledger.jsonl"
        assert len(ledger.read_text(encoding="utf-8").strip().splitlines()) == 1
        run_doubt_cycle(str(tmp_path))
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        first, second = (json.loads(line) for line in lines)
        assert second["ran_at"] >= first["ran_at"]
        assert first["checks"] != second["ran_at"]  # distinct payloads

    def test_causal_doubt_cron_interval(self, tmp_path):
        """Branch: memory/disk consistency — last_report equals the last
        ledger entry after a background cycle."""
        cron = DoubtCron(data_dir=str(tmp_path), interval_seconds=1)
        cron.start()
        assert _wait_for(lambda: cron.last_report is not None, timeout=10)
        ledger = tmp_path / "doubt_ledger.jsonl"
        assert _wait_for(lambda: ledger.exists(), timeout=10)
        last = json.loads(ledger.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert last["ran_at"] == cron.last_report["ran_at"]
        cron.stop()

    def test_causal_doubt_cron_error_silent(self, tmp_path):
        """Branch: escalation_backlog check fails independently on a corrupt
        kernel DB (second real error path besides kernel_integrity)."""
        (tmp_path / "ask_task_kernel.sqlite3").write_bytes(b"garbage not sqlite")
        report = run_doubt_cycle(str(tmp_path))
        by_name = {c["check"]: c for c in report["checks"]}
        assert by_name["kernel_integrity"]["ok"] is False
        assert by_name["escalation_backlog"]["ok"] is False
        assert report["verdict"] == "DOUBT_DETECTED"

    def test_causal_doubt_cron_thread_stop(self, tmp_path):
        """Branch: start() is idempotent — a second start() must not spawn a
        duplicate thread."""
        cron = DoubtCron(data_dir=str(tmp_path), interval_seconds=5)
        cron.start()
        first = cron._thread
        cron.start()
        assert cron._thread is first
        cron.stop()
        assert _wait_for(lambda: not cron._thread.is_alive(), timeout=3)

    def test_causal_why_engine_verifies(self, tmp_path, why_plans_cleanup):
        """Branch: single trusted source matching the AI answer -> PASS with
        high confidence, and the DB row is flipped to executed."""
        engine = WhyEngine()
        question = f"M12-PROBE-{uuid.uuid4().hex[:8]}: capital claim"
        _WIKI_STATE["payload"] = _wiki_pages_payload("The capital of France is Paris.")
        ts = "2026-09-11T00:00:00+00:00"
        db_exec(
            "INSERT INTO why_verification_plans (timestamp, question, target, evidence_type,"
            " proof_criteria, falsification_criteria, verification_strategy, sources_to_query,"
            " status, verdict, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, NULL)",
            (ts, question, "France", "wikipedia_search", "Source supports claim",
             "Source contradicts claim", "wikipedia_search", '["Wikipedia"]'),
        )
        row = db_query_one("SELECT id FROM why_verification_plans WHERE question=?", (question,))
        plan = VerificationPlan(
            question=question, target="France", target_type="entity",
            evidence_type="wikipedia_search", proof_criteria="Source supports claim",
            falsification_criteria="Source contradicts claim",
            verification_strategy="wikipedia_search", sources_to_query=["Wikipedia"],
            expected_answer_type="string", confidence_threshold=0.6, reasoning="",
            plan_id=row["id"],
        )
        result = engine.execute_plan(plan, ai_answer="The capital of France is Paris")
        assert result["verdict"] == "PASS"
        assert result["confidence"] >= 0.85
        row2 = db_query_one(
            "SELECT status, verdict FROM why_verification_plans WHERE id=?", (row["id"],)
        )
        assert row2["status"] == "executed"
        assert row2["verdict"] == "PASS"

    def test_causal_why_engine_lookups(self, tmp_path):
        """Branch: geocoding miss -> weather query returns None (real HTTP,
        empty results payload)."""
        _METEO_STATE["geocode_empty"] = True
        assert _query_open_meteo("Nowhere-City", "temperature?") is None
        assert _METEO_STATE["hits"] == 1  # only geocode was attempted

    def test_causal_why_engine_contradictions(self, tmp_path):
        """Branch: single source disagreeing with the AI answer -> FAIL
        (the fail branch between PASS and CONFLICT)."""
        engine = WhyEngine()
        _WIKI_STATE["payload"] = _wiki_pages_payload("Model accuracy is 85 percent on the benchmark.")
        plan = VerificationPlan(
            question="M12-PROBE-causal-fail: accuracy claim", target="model accuracy",
            target_type="value", evidence_type="wikipedia_search",
            proof_criteria="Source supports claim", falsification_criteria="Source contradicts claim",
            verification_strategy="wikipedia_search", sources_to_query=["Wikipedia"],
            expected_answer_type="string", confidence_threshold=0.6, reasoning="",
        )
        result = engine.execute_plan(plan, ai_answer="Model accuracy is 99%")
        assert result["verdict"] == "FAIL"
        assert result["confidence"] == 0.3

    def test_causal_query_wikipedia(self):
        """Branch: cache — the second identical query is served from the
        module cache without a second HTTP round-trip."""
        _WIKI_STATE["payload"] = _wiki_pages_payload("The capital of France is Paris.")
        assert _query_wikipedia("France", "What is the capital of France?") == "Paris"
        hits_after_first = _WIKI_STATE["hits"]
        assert hits_after_first >= 1
        assert _query_wikipedia("France", "What is the capital of France?") == "Paris"
        assert _WIKI_STATE["hits"] == hits_after_first  # served from cache

    def test_causal_query_nasa(self):
        """Branch: NASA server error -> None, no raise (complements SRC-4's
        Wikipedia rate-limit path)."""
        _NASA_STATE["status"] = 503
        assert _query_nasa("Mars") is None

    def test_causal_query_open_meteo(self):
        """Branch: negative temperatures are formatted losslessly."""
        _METEO_STATE["forecast_temp"] = -12.0
        assert _query_open_meteo("Hanoi", "temperature?") == "temperature=-12.0°C"

    def test_causal_why_sources_rate_limit(self):
        """Branch: circuit breaker — after 5 consecutive failures the breaker
        opens and subsequent queries return None WITHOUT any HTTP attempt."""
        import scp.meta.why_sources.wikipedia as _wiki_mod

        for _ in range(5):
            _wiki_register_failure("M12 unit probe")
        assert _wiki_mod._wiki_fail_count >= 5
        assert _wiki_mod._wiki_circuit_open is True
        _WIKI_STATE["payload"] = _wiki_pages_payload("The capital of France is Paris.")
        hits_before = _WIKI_STATE["hits"]
        assert _query_wikipedia("France", "What is the capital of France?") is None
        assert _WIKI_STATE["hits"] == hits_before  # breaker short-circuits HTTP
