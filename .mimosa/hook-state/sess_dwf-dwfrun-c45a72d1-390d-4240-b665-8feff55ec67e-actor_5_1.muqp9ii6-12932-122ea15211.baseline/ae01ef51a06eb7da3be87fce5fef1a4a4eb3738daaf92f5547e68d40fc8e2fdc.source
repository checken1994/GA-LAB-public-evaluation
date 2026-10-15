"""[F-01/F-02 regression 2026-09-25] Unified trace-ledger final decision.

Runtime audit RUNTIME-AUDIT-20260925-0411 findings:

* F-01 (MEDIUM): the unified ledger (data/trace_ledger.jsonl — the record
  served by GET /v3/trace/{trace_id}) recorded the JUDGE-level
  verdict/governance even when the API boundary/kernel verification later
  overrode the run to FAIL/ESCALATE — the audit trail contradicted the HTTP
  response. Fix: _safe_response is computed BEFORE the ledger append and the
  entry now carries final_verdict / final_governance / final_outcome which
  MUST equal the values /ask returns for that run. Judge-level fields stay
  as provenance.

* F-02 (LOW): the security-lane withhold message embedded the judge verdict
  ("[SCP: Answer withheld — verdict: PASS]" while the API returned FAIL).
  Fix: message dropped the verdict interpolation. The behavioral proof for
  F-02 is the live runtime re-check; here we keep a source tripwire against
  reintroducing the stale interpolation.

FA-13: the boundary-escalated ledger branch previously had no test asserting
ledger==API equality; these tests close that unproven branch.
"""
from __future__ import annotations

import pytest

from scp.ask_kernel_adapter import AskKernelAdapter
from scp.trace_ledger import TraceLedger


@pytest.fixture(autouse=True)
def _no_crosscheck(monkeypatch):
    monkeypatch.setenv("SCP_MULTI_LLM_CROSSCHECK", "0")


@pytest.fixture()
def judge_gate(monkeypatch):
    """Hermetic semantic judge (same seam as test_ask_kernel_adapter_verify)."""
    import scp.runtime.judge_llm as judge_mod

    state = {"pass": True, "calls": 0}

    async def _fake_judge(question: str, ai_answer: str, context: str = "") -> bool:
        state["calls"] += 1
        return state["pass"]

    monkeypatch.setattr(judge_mod, "_llm_judge_async", _fake_judge)
    return state


class DummyReq:
    question = "what color is the sky?"
    contexts = ["sky is blue"]
    retrieved_context = ""
    session_id = "trace-final-decision-test"


JUDGE_LEVEL_RESPONSE = {
    "final_answer": "The sky is blue",
    "verdict": "PASS",
    "governance_decision": "UPHOLD",
    "v98_classification": {"provenance": "input_context_only"},
}


def _make_adapter(tmp_path, monkeypatch) -> AskKernelAdapter:
    # [audit-r2 CI fix 2026-10-01] Pin the unified-ledger data root to the
    # test sandbox: on a GitHub-hosted runner there is no owner `.env`, so
    # SCP_DATA_DIR is unset and runtime_data_dir() falls back to the repo
    # root — the ledger landed there instead of tmp_path/data and every
    # assertion below failed with "entry missing". chdir(tmp_path) alone is
    # an env-pollution-dependent contract (owner `.env` sets
    # SCP_DATA_DIR=data, a cwd-relative path); pinning the env var makes the
    # contract deterministic on every machine without loosening any
    # assertion (same pattern as tests/T02_contract/test_unified_ledger_runtime_dir.py).
    monkeypatch.setenv("SCP_DATA_DIR", str(tmp_path / "data"))
    return AskKernelAdapter(
        db_path=str(tmp_path / "kernel.sqlite3"),
        trace_path=str(tmp_path / "adapter_trace.jsonl"),
    )


def _read_unified_entry(tmp_path, trace_id: str) -> dict:
    ledger = TraceLedger(tmp_path / "data" / "trace_ledger.jsonl")
    entry = ledger.get_trace(trace_id)
    assert entry is not None, "unified ledger entry missing for run trace_id"
    return entry


@pytest.mark.asyncio
async def test_escalated_run_ledger_records_final_decision_equal_to_api(judge_gate, monkeypatch, tmp_path):
    """F-01 core rule: boundary FAIL/ESCALATE run -> ledger final_* fields must
    equal exactly what the adapter returns to /ask; judge-level fields stay."""
    monkeypatch.chdir(tmp_path)  # unified ledger data/ dir lands inside tmp_path
    judge_gate["pass"] = False  # kernel verification CONTRADICTED -> FAIL/ESCALATE
    adapter = _make_adapter(tmp_path, monkeypatch)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        result = await adapter.finalize(task, dict(JUDGE_LEVEL_RESPONSE), req)

        safe = result["safe_response"]
        assert safe["verdict"] == "FAIL"
        assert safe["governance_decision"] == "ESCALATE"

        entry = _read_unified_entry(tmp_path, safe["trace_id"])
        fields = entry["fields"]
        # Fail-closed equality: ledger final decision == API-returned decision
        assert fields["final_verdict"] == safe["verdict"] == "FAIL"
        assert fields["final_governance"] == safe["governance_decision"] == "ESCALATE"
        assert fields["final_outcome"] == result["task"]["state"] == "HUMAN_REVIEW"
        # Judge-level provenance preserved (never rewritten)
        assert fields["verdict"] == "PASS"
        assert fields["governance_decision"] == "UPHOLD"
        # Hash chain stays intact with the new fields included
        assert TraceLedger(tmp_path / "data" / "trace_ledger.jsonl").verify()["hash_chain_valid"] is True
    finally:
        adapter.kernel.close()


@pytest.mark.asyncio
async def test_verified_run_ledger_final_fields_match_delivered_response(judge_gate, monkeypatch, tmp_path):
    """Verified (COMPLETED) run: final_* fields must equal the delivered
    response and must not diverge from the judge-level fields."""
    monkeypatch.chdir(tmp_path)
    judge_gate["pass"] = True
    adapter = _make_adapter(tmp_path, monkeypatch)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        result = await adapter.finalize(task, dict(JUDGE_LEVEL_RESPONSE), req)

        safe = result["safe_response"]
        assert result["task"]["state"] == "COMPLETED"

        entry = _read_unified_entry(tmp_path, safe["trace_id"])
        fields = entry["fields"]
        assert fields["final_verdict"] == safe["verdict"] == "PASS"
        assert fields["final_governance"] == safe["governance_decision"] == "UPHOLD"
        assert fields["final_outcome"] == "COMPLETED"
        assert fields["verdict"] == "PASS"  # no divergence on verified runs
    finally:
        adapter.kernel.close()


def test_security_withhold_message_carries_no_judge_verdict_interpolation():
    """F-02 tripwire: the security-lane withhold text must not interpolate the
    judge verdict — the boundary may override it afterwards (FAIL/ESCALATE),
    so a stale 'verdict: PASS' inside a withheld answer misled consumers.
    Behavioral proof for the message shape is the live runtime re-check."""
    import inspect

    from scp.api_server_parts import _ask_impl

    source = inspect.getsource(_ask_impl)
    assert "Answer withheld — verdict:" not in source
    assert "'[SCP: Answer withheld]'" in source


# ---------------------------------------------------------------------------
# [SECOND-PASS FIX 2026-09-30] Ledger honesty regressions:
#   (a) missing governance_decision must record "UNKNOWN", never "ALLOW";
#   (b) the schema-builder docstring must not overclaim that final_answer is
#       the delivered text (it is pre-safe judge-level provenance);
#   (c) the fail() path writes a documented kernel-disposition SUBSET —
#       response-derived fields are omitted, not fabricated.
# ---------------------------------------------------------------------------

JUDGE_LEVEL_RESPONSE_WITHOUT_GOVERNANCE = {
    "final_answer": "The sky is blue",
    "verdict": "PASS",
    "v98_classification": {"provenance": "input_context_only"},
}


@pytest.mark.asyncio
async def test_unified_ledger_missing_governance_records_unknown_not_allow(judge_gate, monkeypatch, tmp_path):
    """(a) A run whose response carries NO governance decision is recorded as
    governance_decision='UNKNOWN' (fail-closed), never 'ALLOW' — the audit
    trail must not fabricate an ALLOW clearance (SEC-R2-02). Pre-fix the
    ledger recorded 'ALLOW' for exactly this shape."""
    monkeypatch.chdir(tmp_path)
    judge_gate["pass"] = True
    adapter = _make_adapter(tmp_path, monkeypatch)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        result = await adapter.finalize(task, dict(JUDGE_LEVEL_RESPONSE_WITHOUT_GOVERNANCE), req)

        safe = result["safe_response"]
        entry = _read_unified_entry(tmp_path, safe["trace_id"])
        fields = entry["fields"]
        assert fields["governance_decision"] == "UNKNOWN", (
            "missing governance must be recorded as UNKNOWN, never as an ALLOW clearance"
        )
        # F-01 contract intact: final_governance equals the DELIVERED decision
        # (the boundary view, which fail-closes missing governance itself).
        assert fields["final_governance"] == safe["governance_decision"]
    finally:
        adapter.kernel.close()


def test_fail_path_ledger_records_kernel_disposition_subset(monkeypatch, tmp_path):
    """(c) fail() writes the documented kernel-disposition subset: final_* +
    terminal state present; response-derived fields (trace_id/question/
    final_answer) are OMITTED, not fabricated — no response existed on this
    path. The hash chain must stay intact."""
    import json

    monkeypatch.chdir(tmp_path)
    adapter = _make_adapter(tmp_path, monkeypatch)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        adapter.fail(task, "ask_rag_exception_test")

        ledger_path = tmp_path / "data" / "trace_ledger.jsonl"
        entries = [
            json.loads(line)
            for line in ledger_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        fail_fields = [e["fields"] for e in entries if "failure_classification" in e.get("fields", {})]
        assert fail_fields, "fail() must append a unified-ledger entry"
        fields = fail_fields[-1]
        assert fields["final_verdict"] == "FAIL"
        assert fields["final_governance"] == "KILL"
        assert fields["outcome"] == "FAILED"
        assert "trace_id" not in fields
        assert "question" not in fields
        assert "final_answer" not in fields
        assert TraceLedger(ledger_path).verify()["hash_chain_valid"] is True
    finally:
        adapter.kernel.close()


def test_unified_ledger_docstring_and_fail_comment_honesty_tripwire():
    """(b)+(c) Source tripwires: the schema-builder docstring must state that
    final_answer is pre-safe provenance (no 'final_* MUST equal' overclaim),
    and fail()'s comment must not claim 'same schema' with the happy path."""
    import inspect

    doc = inspect.getdoc(AskKernelAdapter._unified_ledger_fields)
    assert doc is not None
    assert "pre-safe provenance" in doc
    assert "final_* fields MUST equal" not in doc

    fail_source = inspect.getsource(AskKernelAdapter.fail)
    assert "same schema and same" not in fail_source
