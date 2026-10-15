"""
Test contract giữa RealityJudge (builder) và IndependentVerifier (consumer).
DNA #14 — Đồng thuận ≠ đúng: không được ngầm định schema, phải có test chứng minh 2 đầu hiểu nhau.
"""
from scp.core.postcondition_schema import (
    PostconditionSchema,
    validate_postcondition_dict,
)
from scp.verifier import IndependentVerifier


def test_text_answer_contract():
    # 1. Builder (Judge) tạo schema
    schema = PostconditionSchema.for_text_answer("the sky is blue")
    postcondition_dict = schema.to_dict()
    
    # 2. Hệ thống (Verifier layer) validate schema
    validate_postcondition_dict(postcondition_dict)
    
    # 3. Consumer (Verifier) chấm điểm obs khớp
    verifier = IndependentVerifier()
    obs_pass = {"evidence_ref": "obs1", "text": "I know that the sky is blue today."}
    res_pass = verifier.verify(postcondition_dict, obs_pass)
    assert res_pass.verdict == "VERIFIED"
    assert "condition_0_failed" not in res_pass.failures

    # 4. Consumer chấm điểm obs không khớp
    obs_fail = {"evidence_ref": "obs2", "text": "the sky is red"}
    res_fail = verifier.verify(postcondition_dict, obs_fail)
    assert res_fail.verdict == "CONTRADICTED"
    assert "condition_0_failed" in res_fail.failures
