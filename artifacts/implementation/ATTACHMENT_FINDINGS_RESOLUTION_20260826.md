# Attachment findings resolution — 2026-08-26

## Scope

This document records a source-plus-runtime verification of six findings raised against the GA-LAB main codebase, followed by bounded fixes and regression checks. It is an evaluation record, not a claim of production readiness.

The implementation was merged into GA-LAB `main` at commit `4a3dc3e5acc4e29fee2ed572ed6d82723c6af646`. The release-gate workflow passed on Windows in run `32972855657`. The full local test suite passed with `211 passed, 3 warnings`. The bounded runtime smoke passed on loopback `127.0.0.1:8002` with external egress denied; both ports 8002 and 8000 were free after cleanup.

## Finding-by-finding result

| Finding | Observation on the audited main | Resolution | Evidence level after fix |
|---|---|---|---|
| urllib3 2.5.0 | Runtime dependency was pinned below the official 2.7.0 security release | Pin upgraded to `urllib3==2.7.0` and CI installs the pinned dependency set | Static + CI dependency installation; advisory-specific exposure still depends on callsite usage |
| SSRF DNS TOCTOU | Hostname was validated and then connected by hostname, allowing a design-level validation/connect gap | Canonical fetcher now resolves all addresses, rejects disallowed ranges, pins the validated IP for the connection, preserves Host/SNI, manually revalidates and repins every redirect hop | Unit/integration tests with local server, mixed DNS answer, redirect and metadata redirect; not a proof against every OS/network edge case |
| Escalation state | Active/timer/history state existed only in RAM and timeout did not terminalize state | Added atomic `escalation_state.json`, deadline persistence, restart re-arm, timeout cleanup and terminal history | Durable-state tests for restart and timeout; not multi-process distributed durability |
| safe_process basename bypass | A path such as `/tmp/git` was accepted because the basename was allowlisted | Path-qualified executables now require exact realpath membership in the whitelist; basename alone is insufficient | Runtime test blocks `/tmp/git` and another malicious path; bare legacy tool names remain an explicit compatibility surface |
| Auth IP wiring | FastAPI injected `unknown` because the dependency parameter was not typed as `Request` | `verify_admin` now uses a real keyword-only `Request` parameter | Real FastAPI TestClient integration: IP A reaches 429 after five failures while IP B remains allowed |
| Base64 image/audio bounds | v104 routes decoded Base64 without an application-level budget | Strict Base64 decoding now checks encoded length before decode and decoded byte budgets; over-budget payloads return 413 | Four functional tests; image and audio OCR/Whisper CPU budgets and image dimensions/audio duration remain separate controls |

## Runtime evidence gate

The release workflow now executes `tools/run_bounded_system_smoke.py` after reality tests. The runner starts the actual application, checks health, Hands status/actions/plan, a read-only Hands dry-run, and a context-backed `/ask`, then terminates the process and verifies that ports 8002 and 8000 are free. The smoke remains intentionally bounded: it does not perform external writes, distributed chaos, live provider outage testing, OS-level sandbox validation, or a factual 1,000-row RAG benchmark.

## What this does not prove

A green CI run means these checks passed for this commit and profile. It does not prove that no unknown security issue exists. The repository still needs independent work for OS-level isolation, distributed durable execution, protocol conformance, hidden/adversarial evaluation, and human-reviewed RAG ground truth. Ragas/ARES and 1,000-row factual RAG remain blocked when their admission preconditions are absent.

## References

[1]: https://urllib3.readthedocs.io/en/stable/changelog.html "urllib3 official changelog"

[2]: https://github.com/urllib3/urllib3/security/advisories/GHSA-mf9v-mfxr-j63j "urllib3 official decompression-bomb advisory"

[3]: https://github.com/urllib3/urllib3/security/advisories/GHSA-qccp-gfcp-xxvc "urllib3 official sensitive-header redirect advisory"

[4]: https://fastapi.tiangolo.com/reference/request/ "FastAPI Request reference"
