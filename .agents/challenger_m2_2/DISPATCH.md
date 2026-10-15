# Dispatch for challenger_m2_2

**Milestone**: M2 (Wire Security Modules into Production Runtime)
**Scope**: Adversarial Stress Testing of F09 (AutonomousAuditLedger & 2PC) and Boundary Verification.

## Challenge Instructions
1. Test ledger tamper attacks against `AutonomousAuditLedger`:
   - Modify record bodies, attempt to recompute hash chains without HMAC key.
   - Verify `verify_provenance()` fails with `hash_chain_valid=False` and catches HMAC mismatch.
2. Test Two-Phase Commit in `HandsExecutor.execute()`:
   - Call with invalid token, expired token, missing token. Ensure execution is blocked and no orphaned intent is committed.
   - Simulate action execution failure. Ensure Phase 2 result block is committed with status `FAILED`.
3. Deliver verdict: APPROVE or REQUEST_CHANGES in `handoff.md`.

## 2026-09-22T20:15:29Z
You are challenger_m2_2.
Your working directory is D:\scp\.agents\challenger_m2_2.
You MUST read D:\scp\.agents\ORIGINAL_REQUEST.md before starting work.
Also read D:\scp\.agents\challenger_m2_2\DISPATCH.md, D:\scp\.agents\orchestrator_7\PROJECT.md, and D:\scp\.agents\worker_m2_1\handoff.md.

Your mission:
Adversarially challenge Milestone M2:
- Stress test AutonomousAuditLedger against tampering, recalculating hash chains without HMAC key.
- Stress test HandsExecutor Two-Phase Commit with invalid tokens, failure recovery, and orphan prevention.
Deliver verdict: APPROVE or REQUEST_CHANGES in D:\scp\.agents\challenger_m2_2\handoff.md.
When complete, notify parent orchestrator via send_message.
