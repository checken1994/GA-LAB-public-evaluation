"""External audit test suite for SCP — RC-10 fix.

This package breaks the RC-8↔RC-10 cycle (convenience > security ↔
self-exemption). SCP's own autofix scanners audit SCP's own code = circular
reinforcement. These tests run INDEPENDENTLY from SCP's scanners — they invoke
external tools (ruff, bandit, grep) directly and assert on the tool output.

Why this matters (from SCP_DEEP_ROOT_CAUSE.md WHY 10):
- 3 AIs (GLM + ChatGPT + Z.ai) all share the same lineage → ảo幻觉 đồng thuận
- An external tool (ruff/bandit/grep) has a DIFFERENT lineage → real check
- If SCP's autofix scanners ever lie or skip a rule, these tests still catch it.

Compliance: DNA SCP #2 (PASS ≠ ĐÚNG — phải có bằng chứng) — these tests
provide the independent evidence SCP's own scanners cannot.
"""
