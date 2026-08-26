# SCP implementation update — 2026-08-26

## Verified in the private canonical repository

The current GA-LAB main commit is `0ed26c07478ef20d279e37a45bf725d356a40323`. The branch that introduced these changes passed the Windows release-gate workflow before fast-forward merge, and main passed the same workflow afterward.

The update contains three concrete improvements:

| Improvement | What changed | Evidence |
|---|---|---|
| Canonical root discipline | GA-LAB is documented as the sole development root; the divergent `scp-agent` source is represented by a staged port backlog, not a wholesale copy | `ARCHITECTURE_CANONICAL_ROOT.md`, `reports/PORT_BACKLOG_SCP_AGENT_TO_GA_LAB_20260826.json`, `tools/verify_canonical_root.py` |
| Trace/span contract | API requests receive a bounded root span; ledger stages become child spans; input/output are hashed, sensitive attributes are redacted, and spans close on success/error/audit failure | `scp/core/trace_contract.py`, `tests/test_trace_contract.py` |
| Human review workflow | A reviewer-friendly CSV/HTML queue and fail-closed validator require reviewer identity, timezone-aware timestamp, source URL, evidence quote, decision hash and optional HMAC signature | `benchmark/review_workflow.py`, `benchmark/HUMAN_REVIEW_WORKFLOW.md`, `tests/test_review_workflow.py` |

The focused implementation tests and the complete local suite passed with `200 passed`. The Windows release-gate CI also passed compile, manifest verification, selective lint, full pytest, Bandit, reality tests, npm audit and dashboard build for the merged branch.

## Runtime evidence

A bounded full-system smoke on `127.0.0.1:8002` with `SCP_EGRESS_MODE=deny` passed health, Hands status/actions/plan, read-only Hands dry-run, and context-backed `/ask`. It returned HTTP 200, `verdict=PASS`, `run_status=SUCCESS`, and `ledger_status=OK`; cleanup confirmed both ports 8002 and 8000 were free. The workload did not perform external writes, provider outage tests, distributed tests, or OS-level sandbox proof.

## Explicit limits

The trace contract is not an OpenTelemetry exporter and does not prove distributed tracing. The human-review queue does not create human decisions. The current RAG candidates remain ineligible for official Gold/Ragas release scoring until real independent human review and complete provenance are supplied. This update does not claim production readiness, Agent OS status, MCP/A2A conformance, Temporal-level durability, or perfect 1,000-question RAG accuracy.
