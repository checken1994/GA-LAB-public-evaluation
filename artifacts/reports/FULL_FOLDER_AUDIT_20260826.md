# Full-folder audit — final evidence, 2026-08-26/27

> **Scope:** This public document summarizes evidence from the private GA-LAB/SCP audit. It is an evaluation record, not a copy of the private source tree and not a production-readiness claim.

## Release identity

| Item | Value |
|---|---|
| Canonical implementation repository | [`checken1994/GA-LAB`][1] |
| Final audited main commit | `fb12015a164777636d1540a4589382cdbe6a5a49` |
| Runtime contract | loopback `127.0.0.1:8002` |
| Local egress profile | `deny` |
| Hosted release gate | Run `32993592103`, completed `success` |
| Public repository role | Sanitized, history-free evaluation evidence pack |

## Why there had been extra SCP folders

The additional folders were old Git checkouts/worktrees, remediation outputs, codegraph artifacts, and evidence produced by earlier audit rounds. They were not proven to be parallel active SCP systems. The six auxiliary checkouts had no commits ahead of `origin/main` and no file diff against the origin baseline. The retired structure-debt workspaces were absent after cleanup.

The cleanup established one active development root on the Windows PC. Old material was moved into one archive container rather than deleted blindly, preserving rollback and provenance. The public repository contains neither the PC archive nor the private source tree.

| Group | Classification | Action | Postcondition |
|---|---|---|---|
| Canonical GA-LAB root | **CANONICAL** | Kept as the only active development root | Final PC checkout is `fb12015`; only six pre-existing codegraph evidence files remain untracked |
| Old checkouts/worktrees | **ARCHIVED** | Moved into one provenance archive after comparison with origin | No auxiliary checkout remains at the Downloads top level |
| Evidence/remediation/standalone outputs | **ARCHIVED** | Moved, not erased | Evidence remains available for private audit and rollback |
| Retired structure-debt workspaces | **ABSENT** | Not recreated | No second active SCP root was found |
| Unrelated Windows files | **UNRELATED** | Not touched | Outside the SCP scope |

## Confirmed fixes

The audit found and corrected three concrete reliability problems in the release path. First, a Windows run exposed an actual HTTP contract defect: the rate limiter could produce `Retry-After=61` for a configured 60-second window. The implementation now uses a bounded ceiling calculation, and a deterministic regression test requires the exact maximum of 60 seconds. Second, the shell reality runner passed Git-Bash `/c/...` paths directly to Windows Python during syntax checks; it now normalizes paths when `cygpath` is available. Third, the shell runner had no per-test timeout and could hang on a child process; it now applies a 90-second default timeout per Python reality test. The runner is also stored with executable mode `100755`.

Earlier cleanup work remains in the final history: active operational defaults were aligned to loopback port 8002, stale duplicate backup/portability artifacts were archived and removed from Git after hashing, the portable runner stopped injecting a missing `.env.test`, and a fixed-port reality test was changed to use an ephemeral port. These changes are described in the repository’s private audit record and public evidence pack.

## Verification evidence

| Gate | Result | Scope and limitation |
|---|---:|---|
| Python compilation on PC | **PASS** | `scp`, tests, and tools compiled with return code 0 |
| Full PC pytest | **212 passed** | Two warnings remained; this is not proof for every untested input |
| Focused Windows 429 contract | **4 passed** | Directly covers the observed `61 → <=60` defect |
| Portable reality runner on PC | **74/74 passed** | `0` fail, timeout, or error |
| Git-Bash shell reality runner on PC | **166/166 passed** | 28 static assertions plus 74 Phase-2 scripts and remaining static phases; `0` failed |
| Bounded PC system smoke | **PASS within scope** | Health, Hands, dry-run, context-backed `/ask`, egress-deny and port cleanup passed on 8002 |
| Hosted GitHub Release Gate | **PASS** | Run `32993592103` on final SHA; compile, snapshot verification, ruff, pytest, Bandit, portable reality, bounded smoke, artifact upload, npm audit and dashboard build completed successfully [2] |
| Snapshot provenance | **PASS within scope** | Captured Git tree has 1,319 tracked files; manifest verifier passed |
| Auxiliary archive provenance | **PASS within scope** | Private recursive manifest recorded 72,389 files and SHA-256 provenance; raw archive is intentionally not public |

The bounded smoke artifact reports all bounded checks as true and `pass=true`. Its cleanup record also reports `port_8002_free=true` and `port_8000_free=true`. It records `process_returncode=1` after the runner terminates the server. This is retained as an anomaly rather than hidden: the current runner treats freed ports plus successful checks as the cleanup condition, so the honest claim is **bounded smoke PASS within scope with a shutdown return-code anomaly**, not a claim of perfect clean-stop semantics.

## What remains unproven

A green release gate verifies the commands and workload that actually ran. It does not prove that SCP answers every question in a 1,000-row RAG benchmark, has a human-reviewed Gold set, has official Ragas or ARES scores, or is safe in every production and distributed deployment.

| Claim | Status | Correct interpretation |
|---|---|---|
| Human-reviewed Gold data for 1,000 RAG rows | **BLOCKED** | Independent review data and gold chunk/answer provenance are still required |
| Official Ragas/ARES admission | **BLOCKED** | A pilot or placeholder cannot be reported as an official score |
| Factual RAG success on all 1,000 questions | **UNPROVEN/BLOCKED** | No 1,000/1,000 correctness claim is made |
| Provider fallback across every live 429 path | **PARTIALLY VERIFIED** | The HTTP Retry-After contract is fixed; all live-provider fallback routes are not proven here |
| Distributed isolation and multi-host guarantees | **UNPROVEN** | The bounded test is local and loopback-only |
| Production-safe or bug-free status | **UNPROVEN** | Test PASS is limited to this profile and commit |
| Complete Agent OS release | **CANDIDATE_NOT_PROVEN** | Full runtime golden-task, chaos, recovery, lease and kill-switch evidence is still incomplete |

Compatibility names and historical terminology such as `SLM`, `slm_trace`, model aliases, old report labels, and test sentinels were not removed by blind search-and-replace. They may be part of API, fixture, or provenance contracts. Active runtime defaults were fixed separately from historical evidence. This is a compatibility decision, not an assertion that every legacy word has disappeared.

## Reviewer guidance

Reviewers should verify the final commit and hosted run directly, inspect the public evidence files, and label each claim `VERIFIED`, `REJECTED`, or `NEEDS_MORE_EVIDENCE`. A model-generated review, a green unit test, or a bounded smoke must not be upgraded into a stronger claim than its evidence supports.

> **Final public verdict:** The audited cleanup and Windows release candidate are **verified within the stated static, integration, bounded-runtime, and hosted CI scopes**. SCP remains **not proven production-ready and not proven factual-RAG-complete**.

## References

[1]: https://github.com/checken1994/GA-LAB "Private GA-LAB implementation repository"

[2]: https://github.com/checken1994/GA-LAB/actions/runs/32993592103 "SCP Windows Release Gate run 32993592103"

[3]: https://github.com/checken1994/GA-LAB-public-evaluation "Public sanitized evaluation evidence pack"
