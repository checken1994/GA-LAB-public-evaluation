# SCP Reality Verifier

## Core Methodology
Kiểm chứng claim và kết quả của SCP bằng evidence, postcondition, provenance và test profile; phân biệt static PASS với integration/end-to-end proof.
- Không hỏi model “có xong không?” rồi tin câu trả lời.
- Kiểm tra kết quả quan sát được, bằng chứng trước/sau, postcondition, provenance và phạm vi test.
- Levels of evidence:
  - A — Static (file, route, schema, pattern, assertion) - no runtime proof
  - B — Integration (modules connected)
  - C — End-to-end (real task through planner, policy, tool, verifier, audit, artifact)
  - D — Recovery proof (C + crash/timeout/restart/recovery)
- Postconditions independently checked: URL, text, schema, hash, response, transitions.
- Test PASS rules: test collected; no encoding/runner exits masked; service really started; PASS_WITHIN_SCOPE.
