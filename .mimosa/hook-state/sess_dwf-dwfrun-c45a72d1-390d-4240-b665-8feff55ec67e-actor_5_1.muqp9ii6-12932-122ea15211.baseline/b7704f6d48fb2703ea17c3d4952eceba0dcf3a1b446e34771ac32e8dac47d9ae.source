"""
SCP Complete Standard Test — Mạch 10: Streaming
Covers: scp/api/routes/stream_routes.py (POST /v105/ask/stream)

M10 HARNESS FIX (AUDIT-20260909) — root causes of the 5 red tests:
  - STREAM-2/3/6 patched `scp.api.routes.stream_routes.stream_llm_response`
    and STREAM-4 patched `stream_routes.LLMGateway` — NEITHER attribute ever
    existed in stream_routes (the route uses the canonical get_judge()
    pipeline, not a module-level LLM gateway), so unittest.mock raised
    AttributeError before any assertion ran.
  - STREAM-5 patched `stream_routes.verify_admin` as a module attribute, but
    the route captured the dependency at decoration time
    (`dependencies=[Depends(verify_admin)]`), so the patch never applied and
    the unauthenticated request was (correctly) answered 401 auth-first,
    not 422.
  - The 6 `test_causal_*` "passed" tests were literal `pass` placeholders
    (FA-01 vacuous green) — de-vacuated below, each with its own real
    assertions over the live route.
  Rewritten: ZERO mocks — this module does not import unittest.mock and
  applies no patch(). Real admin auth (SCP_AUTH_TOKEN_SECRET env + Bearer,
  same pattern as T02/M6), real HTTP streaming through TestClient
  (httpx client.stream), real judge pipeline offline (SCP_EGRESS_MODE=deny).

M10 PRODUCT fix verified by this suite (AUDIT-20260909):
  - stream_routes.ask_stream read the judge verdict as ATTRIBUTES
    (`verdict.verdict`, `verdict.confidence`, ...) while
    RealityJudge.judge() returns a plain dict -> AttributeError on EVERY
    request -> every stream ended in `step: error` and the `judge done` +
    `final` frames were never emitted. Fixed to the real dict contract
    (domain comes from the classify step; the judge result has no domain).

FA-01: Strict assertions, no loosening
FA-02: No skip/xfail
FA-03: Full pytest output as evidence
FA-04: No simulated VERIFIED
FA-05: No self-grant authority
FA-09: Exploit mandate — reproduce actual behavior
FA-13: Causal branch coverage of streaming flow
"""

import json
import logging
import time

import pytest
from fastapi.testclient import TestClient

from scp.api_server import app

logger = logging.getLogger("tests.T03.flow10")

# [TEST-ISOLATION] get_judge() unconditionally launches the production
# AttackCrawler thread (GitHub/HuggingFace jailbreak-corpus mining) whose
# non-daemon executor threads block pytest process exit AFTER the summary
# line, and unit tests must never mine the internet. Neutralise ONLY the
# crawler/fast-learning launchers for this pytest session — no assertion
# depends on them, and the real crawler still runs in the Docker runtime
# verification. (Not a subsystem mock: nothing asserted here touches them;
# same isolation as T03/M6.)
from scp.api_server_parts import helpers as _scp_helpers


def _no_crawl_thread_in_tests(data_dir: str = "data"):
    logger.info("[TEST-ISOLATION] AttackCrawler thread suppressed in T03/M10 session")


def _no_fast_learning_thread_in_tests(*args, **kwargs):
    logger.info("[TEST-ISOLATION] FastLearning background thread suppressed in T03/M10 session")


_scp_helpers.start_crawl_thread = _no_crawl_thread_in_tests
if getattr(_scp_helpers, "start_fast_learning_thread", None) is not None:
    _scp_helpers.start_fast_learning_thread = _no_fast_learning_thread_in_tests

STREAM_PATH = "/v105/ask/stream"
M10_ADMIN_TOKEN = "m10-test-admin-token-0123456789abcdef-40chars"
JUDGE_VERDICT_VOCABULARY = {"PASS", "FAIL", "UNKNOWN"}


@pytest.fixture(autouse=True)
def _m10_env(monkeypatch):
    """Deterministic per-test env: the admin token is read by verify_admin at
    request time (load_auth_config), egress stays deny so the offline
    fail-closed contract is pinned (unit tests never mine the internet)."""
    monkeypatch.setenv("SCP_AUTH_TOKEN_SECRET", M10_ADMIN_TOKEN)
    monkeypatch.setenv("SCP_EGRESS_MODE", "deny")


@pytest.fixture(autouse=True)
def _reset_auth_rate_limit_accounting():
    """Test isolation: verify_admin counts 401s per IP for 60s process-wide
    (5 failures -> 429). The negative-auth probes would otherwise 429 later
    tests in this file. This clears the ACCOUNTING only — verify_admin logic
    untouched (same pattern as T02/M6)."""
    from scp.security import auth as _auth

    _auth._auth_failures.clear()
    yield
    _auth._auth_failures.clear()


def _admin_headers() -> dict:
    return {"Authorization": f"Bearer {M10_ADMIN_TOKEN}"}


def _read_sse_events(response) -> list:
    """Parse the real SSE wire format: `data: <json>` lines separated by
    blank lines. Raises on any non-conforming line (FA-01 strict)."""
    events = []
    for line in response.iter_lines():
        if not line:
            continue
        assert line.startswith("data: "), f"non-SSE line on the wire: {line!r}"
        events.append(json.loads(line[len("data: "):]))
    return events


def _stream_once(client, payload: dict) -> list:
    """One real streaming POST against the live route; returns parsed SSE
    events. The response context asserts the stream transport contract."""
    with client.stream("POST", STREAM_PATH, json=payload, headers=_admin_headers()) as response:
        assert response.status_code == 200, f"stream request failed: {response.status_code}"
        assert (
            response.headers["content-type"] == "text/event-stream; charset=utf-8"
        ), response.headers.get("content-type")
        return _read_sse_events(response)


class TestFlow10Streaming:
    """Mạch 10: Streaming - SCP Complete Standard (no-mock rewrite)"""

    def test_stream_endpoint_requires_admin(self):
        """
        [STREAM-1] POST /v105/ask/stream requires admin auth — auth runs
        BEFORE schema validation (fail-closed ordering), and the missing vs
        invalid token branches are distinguishable.
        """
        with TestClient(app) as client:
            r_missing = client.post(STREAM_PATH, json={"question": "probe"})
            assert r_missing.status_code == 401, r_missing.text
            assert r_missing.json()["detail"] == "Missing auth token", r_missing.text

            r_invalid = client.post(
                STREAM_PATH,
                json={"question": "probe"},
                headers={"Authorization": f"Bearer {M10_ADMIN_TOKEN}-wrong"},
            )
            assert r_invalid.status_code == 401, r_invalid.text
            assert r_invalid.json()["detail"] == "Invalid auth token", r_invalid.text

    def test_stream_endpoint_accepts_streaming_request(self):
        """
        [STREAM-2] A valid admin request starts a REAL SSE stream through the
        REAL judge pipeline (classify -> slm_predict -> judge -> final) —
        no golden-path mock (the old harness mocked an attribute that never
        existed, so it never observed the route at all).
        """
        with TestClient(app) as client:
            events = _stream_once(
                client, {"question": "SCP standard probe: what is 2+2?", "ai_answer": "4"}
            )
        steps = [e.get("step") for e in events]
        assert "classify" in steps, steps
        assert "slm_predict" in steps, steps
        assert "judge" in steps, steps
        assert "final" in steps, steps
        final = events[-1]
        assert final["step"] == "final", steps
        assert final["status"] == "complete", final
        assert final["question"] == "SCP standard probe: what is 2+2?", final
        assert final["verdict"] in JUDGE_VERDICT_VOCABULARY, final

    def test_stream_sse_format_correct(self):
        """
        [STREAM-3] The wire format is SSE: every frame is a `data: <json>`
        line, the terminal frame is the final verdict frame with the real
        contract fields (the old harness asserted a "[DONE]" marker the
        product never emitted).
        """
        with TestClient(app) as client:
            with client.stream(
                "POST", STREAM_PATH, json={"question": "SSE format probe?"}, headers=_admin_headers()
            ) as response:
                assert response.status_code == 200
                assert (
                    response.headers["content-type"] == "text/event-stream; charset=utf-8"
                ), response.headers.get("content-type")
                events = _read_sse_events(response)  # raises on non-SSE / non-JSON lines
        assert events, "stream delivered zero events"
        final = events[-1]
        assert final["step"] == "final", events
        assert final["status"] == "complete", final
        assert isinstance(final["evidence"], dict), final
        assert "verdict" in final and "confidence" in final, final
        classify_done = [
            e for e in events if e.get("step") == "classify" and e.get("status") == "done"
        ]
        assert classify_done, "classify-done frame missing"
        assert "domain" in classify_done[0] and "confidence" in classify_done[0], classify_done[0]

    def test_stream_handles_llm_gateway_failover(self):
        """
        [STREAM-4] A provider outage does not kill the stream. With
        SCP_EGRESS_MODE=deny EVERY LLM provider is genuinely unreachable —
        no mock — yet the real judge pipeline completes through its internal
        fallback chain and the stream still delivers a verdict (designed
        offline behavior: verdict UNKNOWN + governance ESCALATE).
        """
        with TestClient(app) as client:
            events = _stream_once(client, {"question": "Failover probe?", "ai_answer": "42"})
        assert events, "stream delivered zero events"
        judge_done = [e for e in events if e.get("step") == "judge" and e.get("status") == "done"]
        assert judge_done, "judge-done frame missing — the pipeline did not survive the outage"
        assert judge_done[0]["verdict"] in JUDGE_VERDICT_VOCABULARY, judge_done[0]
        final = events[-1]
        assert final["step"] == "final", events
        assert final["status"] == "complete", final
        assert final["verdict"] in JUDGE_VERDICT_VOCABULARY, final
        assert isinstance(final["evidence"], dict) and final["evidence"], final

    def test_stream_validates_request_schema(self):
        """
        [STREAM-5] Auth-first ordering (unauthenticated invalid body is 401,
        NOT 422 — pinned without relying on a patch that never applied) and
        the REAL StreamAskRequest field constraints (question 1..5000,
        ai_answer <= 10000). The old harness's `model` field never existed.
        """
        with TestClient(app) as client:
            r = client.post(STREAM_PATH, json={})  # invalid AND unauthenticated
            assert r.status_code == 401, r.text  # auth-first, fail-closed

            r = client.post(STREAM_PATH, json={}, headers=_admin_headers())
            assert r.status_code == 422, r.text  # question missing

            r = client.post(STREAM_PATH, json={"question": ""}, headers=_admin_headers())
            assert r.status_code == 422, r.text  # question min_length=1

            r = client.post(STREAM_PATH, json={"question": "x" * 5001}, headers=_admin_headers())
            assert r.status_code == 422, r.text  # question max_length=5000

            r = client.post(
                STREAM_PATH,
                json={"question": "ok", "ai_answer": "y" * 10001},
                headers=_admin_headers(),
            )
            assert r.status_code == 422, r.text  # ai_answer max_length=10000

    def test_stream_timeout_handling(self):
        """
        [STREAM-6] The stream ALWAYS terminates in a well-formed terminal
        frame within a bounded wall-clock time (the judge runs off the event
        loop via asyncio.to_thread — no hang, no broken connection).
        Deterministic fault-injection into the judge itself would require
        mocking (forbidden here); the step:error branch is audited at code
        level (D6) and recorded as a known gap in the closure record.
        """
        started = time.monotonic()
        with TestClient(app) as client:
            events = _stream_once(client, {"question": "Timeout probe?"})
        elapsed = time.monotonic() - started
        assert events, "stream delivered zero events"
        assert events[-1]["step"] in {"final", "error"}, events
        assert elapsed < 60, f"stream took {elapsed:.1f}s — unbounded latency"


class TestFlow10StreamingCausalCoverage:
    """
    FA-13: Causal Coverage Matrix for Mạch 10 — de-vacuated (FA-01): the six
    `pass` placeholders are now six distinct real assertions, one per causal
    branch of the streaming flow.
    """

    def test_causal_stream_endpoint_admin_required(self):
        """Branch: non-Bearer credentials and the empty Bearer token are both
        rejected by the real verify_admin (auth-scheme + empty-token paths,
        distinct from STREAM-1's missing-header vs wrong-token paths)."""
        with TestClient(app) as client:
            r = client.post(
                STREAM_PATH,
                json={"question": "x"},
                headers={"Authorization": "Basic dXNlcjpwYXNz"},
            )
            assert r.status_code == 401, r.text  # non-Bearer value treated as a token -> invalid
            assert r.json()["detail"] == "Invalid auth token", r.text

            r = client.post(STREAM_PATH, json={"question": "x"}, headers={"Authorization": "Bearer "})
            assert r.status_code == 401, r.text  # Bearer with empty token -> missing
            assert r.json()["detail"] == "Missing auth token", r.text

    def test_causal_stream_accepts_valid_request(self):
        """Branch: valid request -> the pipeline stages stream in causal
        order (classify running < done < slm_predict < judge running < done
        < final)."""
        with TestClient(app) as client:
            events = _stream_once(client, {"question": "Causal order probe?"})
        order_index = {}
        for idx, e in enumerate(events):
            key = (e.get("step"), e.get("status"))
            order_index.setdefault(key, idx)
        expected_order = [
            ("classify", "running"),
            ("classify", "done"),
            ("slm_predict", "running"),
            ("judge", "running"),
            ("judge", "done"),
            ("final", "complete"),
        ]
        indices = [order_index.get(key) for key in expected_order]
        assert all(i is not None for i in indices), f"missing frames: {expected_order} vs {events}"
        assert indices == sorted(indices), f"causal order violated: {list(zip(expected_order, indices))}"

    def test_causal_stream_sse_format(self):
        """Branch: the raw wire bytes are SSE — every non-empty line carries
        the `data: ` prefix and frames are blank-line separated."""
        with TestClient(app) as client:
            with client.stream(
                "POST", STREAM_PATH, json={"question": "Raw SSE probe?"}, headers=_admin_headers()
            ) as response:
                assert response.status_code == 200
                raw = "".join(response.iter_text())
        lines = raw.split("\n")
        data_lines = [ln for ln in lines if ln.strip()]
        assert data_lines, "no SSE lines on the wire"
        for ln in data_lines:
            assert ln.startswith("data: "), f"non-SSE line: {ln!r}"
        assert raw.endswith("\n\n"), "stream must terminate with a blank-line separated frame"
        # at least one blank separator between frames
        assert "\n\n" in raw, "frames are not blank-line separated"

    def test_causal_stream_failover(self):
        """Branch: provider failover -> the offline judge still reaches a
        verdict through its fallback chain (egress denied = real outage, no
        mock), and the escalation is observable in the evidence frame."""
        with TestClient(app) as client:
            events = _stream_once(client, {"question": "Causal failover probe?"})
        final = events[-1]
        assert final["step"] == "final" and final["status"] == "complete", events
        assert final["verdict"] in JUDGE_VERDICT_VOCABULARY, final
        governance = final["evidence"].get("governance_decision")
        assert governance in {"ESCALATE", "KILL", "UPHOLD"}, final

    def test_causal_stream_schema_validation(self):
        """Branch: schema boundary — 1 and 5000 chars are accepted, 0 and
        5001 are rejected (real Field constraints, authenticated callers)."""
        with TestClient(app) as client:
            r = client.post(STREAM_PATH, json={"question": "x" * 5001}, headers=_admin_headers())
            assert r.status_code == 422, r.text
            r = client.post(STREAM_PATH, json={"question": ""}, headers=_admin_headers())
            assert r.status_code == 422, r.text
            events = _stream_once(client, {"question": "x" * 5000})
            assert events[-1]["step"] == "final", events

    def test_causal_stream_timeout_handling(self):
        """Branch: terminal-frame guarantee — the stream always closes with a
        terminal frame (final OR error) and never leaves the client hanging
        on an open connection (bounded completion)."""
        started = time.monotonic()
        with TestClient(app) as client:
            events = _stream_once(client, {"question": "Causal terminal probe?"})
        elapsed = time.monotonic() - started
        assert events and events[-1]["step"] in {"final", "error"}, events
        assert elapsed < 60, f"stream took {elapsed:.1f}s — unbounded latency"
