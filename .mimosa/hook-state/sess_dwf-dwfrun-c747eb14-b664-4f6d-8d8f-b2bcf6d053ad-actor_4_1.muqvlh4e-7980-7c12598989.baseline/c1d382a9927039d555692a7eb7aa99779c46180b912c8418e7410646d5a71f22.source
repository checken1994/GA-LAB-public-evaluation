"""[HIST-LEDGER-CONTRACT 2026-09-26] History evidence hook phải hợp lệ.

Live sweep: hook ở scp/api_server_parts/_ask_impl.py từng ghi
kind='verdict_rendered' + status=v.verdict ('PASS'/'FAIL'), nhưng
scp/history/evidence_ledger.validate_record chỉ chấp nhận status='verified' +
kind trong {official_document, independent_runtime, independent_adjudication}
→ EvidenceContractError trên MỌI ask ("history hook failed" WARNING) và ledger
file không bao giờ được tạo.

Fix: _history_evidence_record() map verdict sang contract thật — PASS → một
record 'verified' kind 'independent_adjudication' (judge là independent
adjudicator); FAIL/withheld → không ghi gì (ledger không có status
rejected/abstain; ghi record sai contract chính là nguồn WARNING).

Test dùng validate_record THẬT — không mock contract.
"""
from __future__ import annotations

import json

import pytest

from scp.api_server_parts._ask_impl import _history_evidence_record
from scp.history.evidence_ledger import (
    EvidenceContractError,
    EvidenceRecord,
    append_record,
    validate_record,
)


def test_pass_verdict_record_validates_with_real_contract(tmp_path):
    """PASS → record ghi vào ledger phải đi qua validate_record thật."""
    record = _history_evidence_record(
        verdict="PASS",
        session_id="sess-abc",
        question="Thủ đô của Việt Nam là gì?",
    )
    assert record is not None

    # append_record tự gọi validate_record — raise nếu sai contract.
    payload = append_record(tmp_path / "history_evidence.jsonl", record)
    assert (tmp_path / "history_evidence.jsonl").exists()

    # Record đọc lại từ file phải validate độc lập bằng validate_record thật.
    row = json.loads(
        (tmp_path / "history_evidence.jsonl").read_text(encoding="utf-8").splitlines()[-1]
    )
    validate_record(EvidenceRecord(**row["record"]))
    assert row["record"]["status"] == "verified"
    assert row["record"]["kind"] == "independent_adjudication"
    assert row["record"]["lineage"] == "ask_endpoint"
    assert payload["record_hash"]


@pytest.mark.parametrize("verdict", ["FAIL", "UNKNOWN", "PARTIAL", "FLAGGED", ""])
def test_non_pass_verdicts_write_nothing(verdict, tmp_path):
    """FAIL/UNKNOWN/PARTIAL/FLAGGED/withheld → KHÔNG ghi claim sẽ fail
    validation; ledger file không được tạo; hook không còn WARNING."""
    target = tmp_path / f"ledger_{verdict or 'empty'}.jsonl"
    record = _history_evidence_record(verdict=verdict, session_id="s", question="q?")
    assert record is None, f"verdict {verdict!r} must not enter the ledger"
    assert not target.exists()


def test_empty_question_writes_nothing(tmp_path):
    """observed_claim là bắt buộc theo contract — question rỗng → không ghi."""
    record = _history_evidence_record(verdict="PASS", session_id="s", question="   ")
    assert record is None


def test_old_hook_shape_is_rejected_by_the_contract():
    """Contract pin (nguyên nhân root cause): shape cũ của hook
    (kind='verdict_rendered', status='PASS') BỊ validate_record từ chối —
    chứng minh fix là bắt buộc, không phải assertion hình thức."""
    old_shape = EvidenceRecord(
        subject_id="session_unknown",
        lineage="ask_endpoint",
        kind="verdict_rendered",
        locator="ask_impl",
        observed_claim="q?",
        independent_of="",
        status="PASS",
    )
    with pytest.raises(EvidenceContractError):
        validate_record(old_shape)


def test_rebound_ask_impl_namespace_can_resolve_history_helper():
    """[FA-12 closure] `_ask_impl` được rebind với globals() của scp.api_server
    (composition root). Nếu `_history_evidence_record` không có trong namespace
    đó, hook thật sẽ NameError → WARNING mỗi ask — đúng bug đang sửa. Test pin
    chuỗi rebind thật: helper phải resolve được trong globals của hàm đã rebind."""
    from scp import api_server

    assert api_server._ask_impl.__globals__ is api_server.__dict__
    assert "_history_evidence_record" in api_server._ask_impl.__globals__
    # Và helper trong namespace đó là CÙNG hàm với bản trong _ask_impl part.
    from scp.api_server_parts._ask_impl import _history_evidence_record as original

    assert api_server._ask_impl.__globals__["_history_evidence_record"] is original
