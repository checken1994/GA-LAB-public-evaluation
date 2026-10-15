# Exploration Report & Test Expansion Plan: Goal 2 — Subsystem Functional Test Coverage & Concurrency Stress Testing

**Agent**: `explorer_o4_2`  
**Working Directory**: `D:\scp\.agents\explorer_o4_2`  
**Timestamp**: 2026-09-22T13:00:00Z  
**Target Milestone**: Goal 2 — Subsystem Functional Test Coverage & Concurrency Stress Testing  
**Reference Baseline**: 2,049 tests collected, 0 meta-audit regressions  

---

## 1. Observation

### 1.1 Test Landscape & Meta-Audit Baseline
1. **Pytest Collection Command**:
   ```bash
   python -m pytest tests/ --collect-only -q
   ```
   **Output observed**:
   - `2049 tests collected in 2.84s`
   - Exit code: `0` (0 errors, 0 collection failures).
   - Test directories defined in `pytest.ini` (`testpaths = tests tests/internal`).

2. **Meta-Audit Authority**:
   ```bash
   python tools/t00_meta_audit.py
   ```
   **Output observed**:
   - Exit code: `0`
   - Message: `[T00 Meta-Audit] All integrity checks passed (0 new regressions).`
   - Verified rules enforced by `tools/t00_meta_audit.py`:
     - **FA-01 (`AuditVisitor`, lines 75–158)**: Monitors AST for `skip`, `xfail`, `skipif`, `pytest.skip()`, `pytest.xfail()`, `pytest.importorskip()`. Zero new skips are tolerated; baseline skips are tracked as non-blocking `BASELINE_DEBT`.
     - **FA-02 (`check_real_test_deletion`, lines 242–260)**: Compares current candidate test nodeids against trusted baseline (`get_baseline_nodeids`). Any deleted test nodeid raises a fail-closed violation (`FA-02: Deleted test nodeid: <nodeid>`). Total test count must strictly increase or preserve.
     - **FA-04 (`get_fa04_signatures`, lines 160–170)**: Scans for regex `["']simulated\s+verifi(ed|cation)["']` and `return\s*\{.*["']status["'].*["']VERIFIED["']`. Any newly introduced hardcoded or simulated passes are rejected.
     - **Stale Code Tripwire (`run_stale_code_tripwire_check`, lines 277–300)**: Detects missing blueprint modules, orphaned imports, and duplicate prompts.

### 1.2 Subsystem Implementation Details & Code Locations

#### A. Epistemic Engine (`scp/epistemic/`, `scp/meta/`)
- **`scp/epistemic/evidence_store.py`** (321 LOC):
  - Line 94–98: Immutability trigger:
    ```sql
    CREATE TRIGGER IF NOT EXISTS evidence_no_update
    BEFORE UPDATE ON evidence
    BEGIN SELECT RAISE(ABORT, 'evidence is immutable - supersede instead'); END;
    ```
  - Line 147–151: Validation: `kind` must be in `EVIDENCE_KINDS` (`HTTP_RESPONSE`, `FILE_OBSERVATION`, `RUNTIME_OBSERVATION`, `TEST_RESULT`, `CONFIG_SNAPSHOT`, `GIT_SNAPSHOT`, `MODEL_RESPONSE`, `HUMAN_ATTESTATION`); content must be non-empty `bytes`.
  - Line 154–171: Crash-ordered blob write: writes to `.staging/<uuid>.hex`, fsyncs, then atomic rename (`os.replace`) to content-addressed path `sha256/xx/yy/<hash>`. Cleans up `.staging` leftovers on startup.
  - Line 192–194: Record tampering detection via `record_hash`: SHA-256 over 16 canonical immutable fields.
  - Line 221–229 & 231–266: `get()` and `verify_integrity()` detect raw SQL tampering (`record_hash mismatch`) and blob tampering (`blob content hash mismatch (C4 tamper)` or missing file) and fail-closed raising `EvidenceIntegrityError`.
  - Line 282–286: `supersede()` links old and new observations with `relation="SUPERSEDES"`.
  - Line 288–307: `purge_payload()` unlinks blob from disk, transitions `payload_state='PURGED'`, records `retention_events`, preserving durable metadata and hashes while preventing content read.
  - Line 309–320: `scan_orphans()` identifies unreferenced blobs on disk.
- **`scp/epistemic/lineage.py`** (290 LOC):
  - Line 18–23: `IndependenceStatus`: `UNKNOWN_INDEPENDENCE`, `SAME_LINEAGE`, `LIKELY_SHARED_LINEAGE`, `INDEPENDENT`.
  - Line 32–33: SQLite schema forces `DEFAULT 'UNKNOWN_INDEPENDENCE'`.
  - Line 126–136: `record_relation()` rejects `INDEPENDENT` without explicit independence basis (e.g. `independent_primary_observation`, `explicit_distinct_origin`).
  - Line 212–286: `assess_independent_support()` uses disjoint-set union-find over shared lineage edges to collapse sources and computes a conservative lower bound of independent lineages.
- **`scp/epistemic/source_identity.py`** (212 LOC):
  - Line 39–66: `canonicalize_url()` strips fragments, strips default ports (:80, :443), forces lowercase IDNA hostname, and rejects credentials (`ValueError("URL source identity must not contain credentials")`).
  - Line 68–82: `canonicalize_repository()` validates `owner/name`, verifies hex git sha, formats `github:owner/name@sha:path`.
- **`scp/epistemic/evidence_writer.py`** (64 LOC):
  - Line 39–46: `GovernedEvidenceWriter.observe()` evaluates content against `privacy_gate`. If `DENY_STORAGE`, raises `PrivacyWriteDenied`.
- **`scp/meta/falsification_engine.py`** (988 LOC):
  - Line 68–102: `FalsificationStatus` skeptical language (`UNREFUTED_IN_CURRENT_SCOPE`, `NO_CONTRADICTION_FOUND`, `CONTRADICTION_DETECTED`, `HUMAN_DECISION_REQUIRED`, `REFUTED_BY_REALITY`).
  - Line 121–147: `Deviation` dataclass measuring relative delta `|llm - ref| / |ref|` across severity thresholds (LOW <2%, MEDIUM <10%, HIGH <25%, CRITICAL >=25%).
- **`scp/meta/epistemic_boundary.py`** (94 LOC):
  - Line 42–72: `record_contradiction()` converts reality contradiction into `MissingPieceRecord` and `OpenQuestionRecord` in `LearningDB`.

#### B. TaskKernel (`scp/task_kernel.py`, `scp/task_kernel_parts/`, `scp/kernel_storage.py`)
- **`scp/task_kernel_parts/definitions.py`** (162 LOC):
  - Line 13–19: States: `CREATED`, `PLANNING`, `WAITING_APPROVAL`, `READY`, `QUEUED`, `LEASED`, `RUNNING`, `WAITING_TOOL`, `VERIFYING`, `CHECKPOINTED`, `UNKNOWN`, `RECOVERING`, `RECONCILING`, `HUMAN_REVIEW`, `RETRY_SCHEDULED`, `COMPLETED`, `FAILED`, `CANCELLED`. Terminal: `COMPLETED`, `FAILED`, `CANCELLED`.
  - Line 20–39: `ALLOWED_TRANSITIONS` graph.
  - Line 128–157: `_checkpoint_contains_secret()` and `_assert_checkpoint_safe()` scan state payloads for `password`, `secret`, `token`, `api_key`, `bearer`, and private keys, raising `KernelError("checkpoint contains secret material")`.
- **`scp/task_kernel_parts/taskkernel.py`** (1,969 LOC):
  - Line 379–440: `transition()` enforces state transition allowlist, checks global and task kill switches, validates version OCC, and logs to `task_events` hash chain.
  - Line 530–558: `claim()` acquires lease for worker, increments task fencing token, sets `expires_at`.
  - Line 633–660: `start()` transitions `LEASED` -> `RUNNING`.
  - Line 663–710: `heartbeat()` validates active lease and extends expiration.
  - Line 714–750: `renew_lease()` validates fencing token; raises `StaleLease` if token does not match.
  - Line 805–845: `expire_leases(now)` queries tasks whose leases expired and transitions them to `RECOVERING`.
  - Line 899–934: `checkpoint()` verifies checkpoint safety and records state hash.
  - Line 1175–1195: `idempotency_claim()`, `idempotency_complete()`, and `idempotency_status()`.
  - Line 1662–1685: `set_global_kill()` and `set_task_kill()` activate kill switches.
  - Line 1819–1865: `recover_on_boot()` cleans up orphaned tasks left in `RUNNING`/`LEASED`.
  - Line 1888–1907: `verify_journal()` verifies the SHA-256 hash chain of all events in `task_events`.
- **`scp/kernel_storage.py`** (254 LOC):
  - `SQLiteKernelStorage`: ContextVar-safe connection management, connection pool with max bounded connections (`_max_conns=16`), WAL mode, `PRAGMA busy_timeout=10000`, `begin()` uses `BEGIN IMMEDIATE` with retry.

#### C. Self-Model (`scp/self_model/capability_map.py`)
- Line 28–36: `CapabilityStatus`: `UNKNOWN`, `DECLARED`, `STATIC_PRESENT`, `INTEGRATED`, `RUNTIME_VERIFIED`, `RECOVERY_VERIFIED`, `DEGRADED`, `UNAVAILABLE`.
- Line 72–75: Immutability trigger:
  ```sql
  CREATE TRIGGER IF NOT EXISTS capability_proofs_no_update
  BEFORE UPDATE ON capability_proofs
  BEGIN SELECT RAISE(ABORT, 'capability proof is immutable'); END;
  ```
- Line 107–140: `record_proof()` verifies proof evidence metadata matches `tested_sha` and `evidence_level` before insertion.
- Line 142–235: `recompute_capability()` recomputes capability maturity dynamically from `spec/complete_scp_reference.yaml`, `spec/implementation_bindings.yaml`, module importability, and verified evidence matching the current SHA. Ignores historical proofs from other SHAs.
- Line 236–273: `add_blindspot()` and `list_blindspots()` manage cognitive and capability blindspots.

#### D. Observability (`scp/observability/`, `scp/core/subsystem_telemetry.py`)
- **`scp/core/subsystem_telemetry.py`** (410 LOC):
  - Line 65–132: `SubsystemTelemetry` creates SQLite heartbeat database with WAL mode and `subsystem_heartbeat` + `subsystem_heartbeat_events` tables, plus append-only JSONL run ledger.
  - Line 42–63: `_safe_error()` and `_json_safe()` redact `token=`, `password=`, `api_key=`, `authorization:`.
  - Line 143–210: `tick()`, `record_cycle_start()`, `record_cycle_complete()`, `record_cycle_failure()`.
- **`scp/observability/otel.py`** (51 LOC):
  - Line 14–48: `configure_fastapi_otel()` disables cleanly when `SCP_OTEL_ENABLED=0` or `OTEL_EXPORTER_OTLP_ENDPOINT` is missing. Sanitizes headers (`authorization`, `cookie`, `set-cookie`) when active.

#### E. Concurrency & Persistence Subsystems
- **`scp/core/chat_memory_store.py`** (222 LOC):
  - Line 35–90: `_ReentrantFileLock` with OS file lock (`msvcrt.locking` on Windows, `fcntl.flock` on POSIX) and `threading.RLock`.
  - Line 140–160 & 189–219: Thread and file-lock safe `append()` and `_prune_if_needed()`.
- **`scp/trace_ledger.py`** (163 LOC):
  - Line 33–50: `_LedgerState` per-path `RLock`.
  - Line 57–94: Backwards tail reader `_read_tail()` in binary mode.
  - Line 95–121: `append()` appends hash-chained entries with fsync.
  - Line 122–142: `verify()` verifies cryptographic hash chain integrity and sequence continuity.
- **`scp/core/db_manager.py`** (191 LOC):
  - Line 27–34: `_db_lock = threading.RLock()`, `_read_lock = threading.Lock()`.
  - Line 139–161: `db_query_all` and `db_query_one` hold lock across query execution and `fetchall`/`fetchone`.

### 1.3 Current Subsystem Tests Status & Gaps
Direct inspection of `tests/test_subsystem_*.py`:
1. `tests/test_subsystem_epistemic.py`: **Only 1 test** (`test_subsystem_epistemic_importable`). Only tests creating an `EvidenceStore`, writing a single test result, and reading content back. Zero assertions on: SQLite triggers, tampering detection, C4 payload corruption, purge retention, `supersede` linking, URL/repo canonicalization, lineage independence proofs, or falsification engine deviations.
2. `tests/test_subsystem_task_kernel.py`: **Only 1 test** (`test_subsystem_task_kernel_importable`). Only tests a single 3-step transition (`CREATED` -> `PLANNING` -> `READY`). Zero tests for worker leases, heartbeat, lease expiration, fencing tokens, stale leases, checkpoint secret protection, kill switches, idempotency, or crash recovery.
3. `tests/test_subsystem_self_model.py`: **Only 3 tests** (`test_subsystem_self_model_importable`, `test_subsystem_self_model_has_capability_map`, `test_subsystem_self_model_capability_status_levels`). Tests only verify class attributes and enum member count. Zero tests for proof immutability triggers, SHA isolation, maturity level progression (M1->M5), missing bindings degradation, or blindspots tracking.
4. `tests/test_subsystem_observability.py`: **Only 1 test** (`test_subsystem_observability_importable`). Only asserts that `configure_fastapi_otel` returns `status["enabled"] is False`. Zero tests for `SubsystemTelemetry` heartbeat, cycle metrics, error secret redaction, JSONL run ledger, or OTel endpoint configuration.
5. `tests/test_p0_persistence_concurrency.py`: Only 4 tests with small iteration counts. Zero concurrency tests for `KernelStorage` connection pools or `TaskKernel` worker claim races.

---

## 2. Logic Chain

```
[Observation 1: 2,049 tests collected, 0 meta-audit regressions, strict FA-01 / FA-02 rules]
        │
        ▼
[Inference 1: New test suites must NEVER use pytest.skip/xfail, must NEVER delete any test nodeid,
              and must add ONLY deterministic, self-contained, fail-closed behavioral assertions]
        │
        ▼
[Observation 2: Core subsystems (Epistemic, TaskKernel, SelfModel, Observability) have critical
                fail-closed invariants implemented in code but completely omitted from test suites]
        │
        ▼
[Inference 2: Subsystem tests are currently superficial (import checks & basic stubs).
              Expanding coverage requires genuine functional tests exercising real SQLite triggers,
              tamper detection, state machines, lease fencing, and secret scrubbing]
        │
        ▼
[Observation 3: Concurrency primitives in ChatMemoryStore, TraceLedger, SQLiteKernelStorage, and db_manager
                were hardened in audit milestones M1/M2 but lack high-thread stress testing]
        │
        ▼
[Inference 3: Concurrency stress tests with 8–12 threads executing concurrent appends, pruning,
              hash chaining, OCC transactions, and worker claim races will prove runtime stability]
        │
        ▼
[Conclusion: Formulate a 5-suite expansion plan adding 48 comprehensive tests, expanding collection
             from 2,049 to 2,097 tests, verifying fail-closed boundaries with 0 regressions]
```

---

## 3. Caveats

1. **Test Execution Time**: Concurrency and stress tests must balance thread contention against execution time. Tests are scoped to 8–12 threads with 20–50 iterations each, completing within 0.1–0.8s per test, avoiding timeouts in CI/CD while creating genuine lock contention.
2. **File System Locking on Windows**: `ChatMemoryStore` uses `msvcrt.locking` on Windows and `fcntl.flock` on POSIX. Tests must use `tmp_path` fixtures to prevent file path collisions and allow Windows locks to release cleanly.
3. **Pre-existing Skip Debt**: There are 14 historical skips in `tests/` marked as `BASELINE_DEBT` in `tools/t00_meta_audit.py`. New test files must have 0 skips to prevent FA-01 violations.
4. **Scope Boundary**: As an Explorer agent, this report provides read-only investigation, architectural analysis, and exact test specifications. Code implementation is reserved for the Implementer agent.

---

## 4. Conclusion & Test Expansion Plan

We specify **5 new test suites** comprising **48 comprehensive behavioral tests**:

```
tests/
├── test_epistemic_functional.py      (14 tests: triggers, tampering, CAS, lineage, canonicalization, falsification)
├── test_task_kernel_stress.py        (10 tests: state transitions, lease fencing, checkpoint secrets, kill switch, worker claim race, recovery)
├── test_self_model_behavioral.py     (8 tests: maturity progression, proof immutability, SHA isolation, blindspots, degraded status)
├── test_observability_functional.py   (8 tests: telemetry heartbeat, cycle metrics, secret scrubbing, run ledger, OTel modes)
└── test_concurrency_stress_v2.py     (8 tests: ChatMemoryStore prune stress, TraceLedger 12-thread hash chain, KernelStorage pool, db_manager locks)
```

**Projected Test Collection**: `2,049` (baseline) + `48` (new) = **`2,097` tests**.

---

### Detailed Test Specifications

#### Suite 1: `tests/test_epistemic_functional.py` (14 Tests)

```python
"""Comprehensive functional tests for Epistemic Engine (26-P0.05 - 26-P0.07).

Validates:
- EvidenceStore immutability trigger (evidence_no_update)
- Record tampering detection (record_hash mismatch)
- Blob tampering detection (C4 tamper / hash mismatch)
- Missing blob fail-closed behavior
- Retention payload purging and event auditing
- Evidence superseding and link relations
- Orphan blob scanning and staging cleanup
- LineageStore DB default UNKNOWN_INDEPENDENCE
- Independence requires explicit basis
- Independence assessment and shared-lineage collapsing
- URL canonicalization and credential stripping
- Repository canonicalization and hex sha verification
- FalsificationEngine skeptical status and deviation thresholds
- EpistemicBoundary contradiction recording into OpenQuestionAuthority
"""
```

1. **`test_evidence_store_immutable_trigger_fails_closed(tmp_path)`**:
   - **Target**: `scp/epistemic/evidence_store.py:94` (`evidence_no_update`).
   - **Execution**: Create `EvidenceStore(tmp_path / "ev.db", tmp_path / "objs")`. Observe a record. Execute direct raw SQL: `store.db.execute("UPDATE evidence SET kind='MODIFIED' WHERE evidence_id=?", (ev["evidence_id"],))`.
   - **Assertion**: Expect `sqlite3.OperationalError` with message `'evidence is immutable - supersede instead'`.
2. **`test_evidence_store_record_tampering_fails_closed(tmp_path)`**:
   - **Target**: `scp/epistemic/evidence_store.py:231` (`verify_integrity`).
   - **Execution**: Observe evidence. Modify metadata row directly in SQL: `store.db.execute("UPDATE evidence SET collector_id='hacked' WHERE evidence_id=?", (ev["evidence_id"],))`. Call `store.verify_integrity(ev["evidence_id"])`.
   - **Assertion**: Result has `ok is False`, `errors` contains `"record_hash mismatch - immutable metadata was tampered with"`. Calling `store.get(ev["evidence_id"])` raises `EvidenceIntegrityError`.
3. **`test_evidence_store_blob_tampering_c4_fails_closed(tmp_path)`**:
   - **Target**: `scp/epistemic/evidence_store.py:256` (C4 tamper detection).
   - **Execution**: Observe `b"original data"`. Locate on-disk blob via `ev["content_ref"]`. Overwrite with `b"tampered data"`. Call `store.verify_integrity(ev["evidence_id"])`.
   - **Assertion**: `ok is False`, `payload_state == "MISSING"`, `errors` contains `"blob content hash mismatch (C4 tamper)"`. Calling `store.read_content(ev["evidence_id"])` raises `EvidenceIntegrityError`.
4. **`test_evidence_store_missing_blob_fails_closed(tmp_path)`**:
   - **Target**: `scp/epistemic/evidence_store.py:252` (missing blob check).
   - **Execution**: Observe evidence. Unlink blob file on disk. Call `store.verify_integrity()`.
   - **Assertion**: `ok is False`, `errors` contains `"blob file missing (C4)"`.
5. **`test_evidence_store_purge_payload_and_retention_event(tmp_path)`**:
   - **Target**: `scp/epistemic/evidence_store.py:288` (`purge_payload`).
   - **Execution**: Observe evidence. Call `store.purge_payload(ev["evidence_id"], reason="GDPR erasure", policy="retention-v1")`.
   - **Assertion**: Blob file is deleted (`not blob_path.exists()`). Table `retention_events` contains row with `target == ev["evidence_id"]`, `reason == "GDPR erasure"`. Calling `store.read_content()` raises `EvidenceIntegrityError`.
6. **`test_evidence_store_supersede_and_link(tmp_path)`**:
   - **Target**: `scp/epistemic/evidence_store.py:282` (`supersede`).
   - **Execution**: Observe `ev1`. Call `store.supersede(ev1["evidence_id"], kind="TEST_RESULT", content=b"v2", collector_id="pytest", collector_version="1")`.
   - **Assertion**: Replacement record exists. Table `evidence_links` has `(parent=ev1, child=replacement, relation="SUPERSEDES")`. `ev1` remains unaltered in table.
7. **`test_evidence_store_scan_orphans_and_staging_cleanup(tmp_path)`**:
   - **Target**: `scp/epistemic/evidence_store.py:125, 309`.
   - **Execution**: Write an unreferenced file into `objects_dir / sha256/aa/bb/aabb...`. Write leftover into `.staging`.
   - **Assertion**: `store.scan_orphans()` returns path of unreferenced file. Re-instantiating `EvidenceStore` unlinks `.staging` leftover.
8. **`test_lineage_store_unknown_independence_default(tmp_path)`**:
   - **Target**: `scp/epistemic/lineage.py:32, 71` (`ensure_relation`).
   - **Execution**: Call `lineage.ensure_relation("src_beta", "src_alpha")`.
   - **Assertion**: Canonical pair ordered `("src_alpha", "src_beta")`. Status is `IndependenceStatus.UNKNOWN_INDEPENDENCE`.
9. **`test_lineage_store_independent_requires_explicit_basis(tmp_path)`**:
   - **Target**: `scp/epistemic/lineage.py:128` (explicit independence basis rule).
   - **Execution**: Call `lineage.record_relation("a", "b", status=IndependenceStatus.INDEPENDENT, basis=[{"type": "different_domain"}])`.
   - **Assertion**: Raises `ValueError("INDEPENDENT requires an explicit independence basis...")`. Calling with `{"type": "independent_primary_observation"}` succeeds.
10. **`test_lineage_store_assess_independent_support_collapses_shared(tmp_path)`**:
    - **Target**: `scp/epistemic/lineage.py:212` (`assess_independent_support`).
    - **Execution**: Register 4 sources: s1, s2, s3, s4. Relate s1-s2 as `SAME_LINEAGE`, s3-s4 as `LIKELY_SHARED_LINEAGE`. Relate s1-s3 as `INDEPENDENT`. Assess support.
    - **Assertion**: `source_count == 4`, `shared_components == [["s1", "s2"], ["s3", "s4"]]`, `known_independent_lineages == 2`.
11. **`test_source_store_url_canonicalization_and_credential_rejection()`**:
    - **Target**: `scp/epistemic/source_identity.py:39` (`canonicalize_url`).
    - **Execution**: Test URLs: `HTTP://EXAMPLE.COM:80/path?x=1#frag`, `https://example.com:443/`, `http://user:pass@example.com/`.
    - **Assertion**: Normalizes to `http://example.com/path?x=1` and `https://example.com/`. Credential URL raises `ValueError("URL source identity must not contain credentials")`. Non-http raises `ValueError`.
12. **`test_source_store_repo_canonicalization()`**:
    - **Target**: `scp/epistemic/source_identity.py:68` (`canonicalize_repository`).
    - **Execution**: Normalize `owner/repo` with sha `a1b2c3d4` and path `src/lib.py`. Attempt with non-hex sha `g1h2i3j4`.
    - **Assertion**: Returns `github:owner/repo@a1b2c3d4:src/lib.py`. Non-hex sha raises `ValueError("commit_sha must be hexadecimal")`.
13. **`test_falsification_engine_skeptical_status_and_deviations()`**:
    - **Target**: `scp/meta/falsification_engine.py:68–147`.
    - **Execution**: Test `FalsificationStatus` methods `is_skeptical()` and `requires_human()`. Create `Deviation` instances across delta ranges (1.5%, 8%, 20%, 30%).
    - **Assertion**: `UNREFUTED_IN_CURRENT_SCOPE.is_skeptical() is True`, `REFUTED_BY_REALITY.requires_human() is True`. Severities classify as `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
14. **`test_epistemic_boundary_records_contradiction_and_open_question(tmp_path)`**:
    - **Target**: `scp/meta/epistemic_boundary.py:42` (`record_contradiction`).
    - **Execution**: Initialize `EpistemicBoundary(db_path=tmp_path / "learning.sqlite")`. Call `record_contradiction(MissingPieceFinding(blind_spot="network timeout", affected_coverage="web_test", evidence_refs=["ev_1"]))`.
    - **Assertion**: `boundary.verdict == "CONTRADICTED"`. Open question created in `LearningDB` with `trigger == QuestionTrigger.CONTRADICTION`.

---

#### Suite 2: `tests/test_task_kernel_stress.py` (10 Tests)

```python
"""Behavioral and stress tests for TaskKernel (GAP-13, State Machine, Worker Leases, Recovery).

Validates:
- Strict state transition allowlist and terminal state finality
- Worker lease claim, start, heartbeat, and renewal lifecycle
- Stale lease fencing token rejection (OCC optimistic locking)
- Checkpoint secret protection (fail-closed on password/token/key)
- Cryptographic event journal hash chain verification and tamper detection
- Global and task kill switches (immediate fail-closed execution halting)
- High-concurrency worker claim competition (zero duplicate claims)
- Orphaned in-flight task boot recovery
- Request idempotency claim and completion caching
- KernelStorage connection pool boundaries and WAL transaction serialization
"""
```

1. **`test_task_kernel_invalid_state_transitions_fail_closed(tmp_path)`**:
   - **Target**: `scp/task_kernel_parts/definitions.py:20` (`ALLOWED_TRANSITIONS`), `taskkernel.py:379`.
   - **Execution**: Create task `t-1`. Attempt direct transition `CREATED -> COMPLETED`. Transition `CREATED -> PLANNING -> READY -> CANCELLED`. Attempt transition from terminal `CANCELLED -> READY`.
   - **Assertion**: Raises `InvalidTransition` in both cases. Terminal states allow 0 transitions.
2. **`test_task_kernel_worker_lease_lifecycle(tmp_path)`**:
   - **Target**: `scp/task_kernel_parts/taskkernel.py:530, 633, 663, 714`.
   - **Execution**: Move task to `QUEUED`. Worker 1 calls `claim(task_id, "w1", ttl_seconds=300)`. Call `start()`. Call `heartbeat(extend_seconds=60)`. Call `renew_lease(fencing_token=lease.fencing_token)`.
   - **Assertion**: State progresses `QUEUED -> LEASED -> RUNNING`. Lease object contains valid `fencing_token == 1`. Expiration extends.
3. **`test_task_kernel_stale_lease_fencing_token_rejection(tmp_path)`**:
   - **Target**: `scp/task_kernel_parts/taskkernel.py:714, 805`.
   - **Execution**: Worker 1 claims task (fencing token 1). Fast-forward time via `expire_leases(now=lease.expires_at + 10)`. Worker 2 claims task (fencing token 2). Worker 1 attempts to renew lease or transition with old lease.
   - **Assertion**: Raises `StaleLease` or `OptimisticLockError`. Worker 2 retains ownership.
4. **`test_task_kernel_checkpoint_secrets_scrubbing_fails_closed(tmp_path)`**:
   - **Target**: `scp/task_kernel_parts/definitions.py:154` (`_assert_checkpoint_safe`), `taskkernel.py:899`.
   - **Execution**: Task in `RUNNING`. Attempt `checkpoint` with payload containing: `{"password": "supersecret123"}`, then with `{"token": "sk-test-token"}`, then with `{"headers": "Bearer abcdefgh12345678"}`. Finally checkpoint with `{"step": 1, "status": "ok"}`.
   - **Assertion**: All secret payloads raise `KernelError("checkpoint contains secret material")`. Clean payload commits successfully.
5. **`test_task_kernel_cryptographic_journal_verification_and_tamper_detection(tmp_path)`**:
   - **Target**: `scp/task_kernel_parts/taskkernel.py:1888` (`verify_journal`).
   - **Execution**: Execute 4 state transitions (`CREATED -> PLANNING -> READY -> CANCELLED`). Verify journal. Tamper with event 2 in raw SQL (`UPDATE task_events SET reason='tampered' WHERE seq=2`). Verify journal again.
   - **Assertion**: Initial journal verification has `hash_chain_valid is True`, `event_count == 4`. Tampered journal has `hash_chain_valid is False` with errors.
6. **`test_task_kernel_global_and_task_kill_switches(tmp_path)`**:
   - **Target**: `scp/task_kernel_parts/taskkernel.py:1662, 1675`.
   - **Execution**: Create task. Call `set_global_kill(True)`. Attempt `transition()`. Call `set_global_kill(False)`. Call `set_task_kill(task_id)`. Attempt `transition()`.
   - **Assertion**: Both raise `KillSwitchActive`.
7. **`test_task_kernel_concurrent_worker_claim_race(tmp_path)`**:
   - **Target**: `scp/task_kernel_parts/taskkernel.py:560` (`claim_next`).
   - **Execution**: Queue 15 tasks. Launch 8 threads, each calling `claim_next(worker_id=f"worker_{i}")` in a loop until queue empty.
   - **Assertion**: Exactly 15 tasks claimed total. Zero double claims (`len(claimed_tasks) == len(set(claimed_tasks))`). Fencing tokens valid.
8. **`test_task_kernel_boot_recovery_orphaned_tasks(tmp_path)`**:
   - **Target**: `scp/task_kernel_parts/taskkernel.py:1819` (`recover_on_boot`).
   - **Execution**: Create tasks left in `LEASED` and `RUNNING` simulating an abrupt process termination. Call `recover_on_boot()`.
   - **Assertion**: Orphaned tasks are transitioned to `RECOVERING` or `CHECKPOINTED`. No task remains stuck in active lease.
9. **`test_task_kernel_idempotency_engine_claim_and_complete(tmp_path)`**:
   - **Target**: `scp/task_kernel_parts/idempotency.py:1175`.
   - **Execution**: Worker claims logical key `k1` -> returns `(key, claimed=True)`. Second worker claims same key -> returns `(key, claimed=False)`. Complete with result `res_1`. Query status.
   - **Assertion**: Second worker gets `claimed is False`. Status returns `COMPLETED` with `result_ref == "res_1"`.
10. **`test_sqlite_kernel_storage_transaction_isolation_and_close(tmp_path)`**:
    - **Target**: `scp/kernel_storage.py:69` (`SQLiteKernelStorage`).
    - **Execution**: Create `SQLiteKernelStorage(tmp_path / "k.db", max_conns=4)`. Open transaction, insert records, commit. Check `in_transaction` property before and after. Verify `close()` cleanly closes all connections.
    - **Assertion**: `in_transaction` is True during block, False after. Data persisted.

---

#### Suite 3: `tests/test_self_model_behavioral.py` (8 Tests)

```python
"""Behavioral tests for Self-Model and CapabilityMap (26-P0.10).

Validates:
- Complete-SCP reference and bindings resolution
- Capability status transitions across maturity ladder (M1 -> M5)
- Proof SHA isolation (historical proofs from other commits never verify current commit)
- Proof immutability SQLite trigger (capability_proofs_no_update)
- Metadata validation during proof recording (tested_sha and evidence_level exact match)
- Degradation when binding implementation module is missing
- Unknown capability handling (M0_IDEA fallback)
- Blindspot tracking and filtering lifecycle
"""
```

1. **`test_capability_map_status_transitions_through_maturity_levels(tmp_path)`**:
   - **Target**: `scp/self_model/capability_map.py:142` (`recompute_capability`).
   - **Execution**: Initialize with `epistemic.evidence`. Step through:
     - No proofs: `status == STATIC_PRESENT`, `maturity == M2`.
     - Record Level B proof: `status == INTEGRATED`, `maturity == M3`.
     - Record Level C proof: `status == RUNTIME_VERIFIED`, `maturity == M4`.
     - Record Level D proof: `status == RECOVERY_VERIFIED`, `maturity == M5`.
   - **Assertion**: Each proof dynamically elevates status and maturity.
2. **`test_capability_map_proof_sha_isolation(tmp_path)`**:
   - **Target**: `scp/self_model/capability_map.py:205` (stale SHA proofs).
   - **Execution**: Record Level D proof for `sha-commit-1`. Recompute capability for `sha-commit-2`.
   - **Assertion**: Capability for `sha-commit-2` remains `STATIC_PRESENT` (`M2`). Limitations note contains `"historical proof(s) belong to other SHA(s) and were ignored"`.
3. **`test_capability_map_immutable_proof_trigger_fails_closed(tmp_path)`**:
   - **Target**: `scp/self_model/capability_map.py:72` (`capability_proofs_no_update`).
   - **Execution**: Record proof. Execute raw SQL: `model.db.execute("UPDATE capability_proofs SET evidence_level='D' WHERE proof_id=?", (proof_id,))`.
   - **Assertion**: Raises `sqlite3.OperationalError` with `'capability proof is immutable'`.
4. **`test_capability_map_rejects_mismatched_evidence_metadata(tmp_path)`**:
   - **Target**: `scp/self_model/capability_map.py:124–128`.
   - **Execution**: Create evidence with metadata `tested_sha="sha-A", evidence_level="B"`. Attempt `record_proof(tested_sha="sha-B")`. Attempt `record_proof(evidence_level="C")`.
   - **Assertion**: Both raise `ValueError` ("mismatch").
5. **`test_capability_map_unknown_capability_returns_m0_idea(tmp_path)`**:
   - **Target**: `scp/self_model/capability_map.py:145`.
   - **Execution**: Recompute capability for `"totally.unknown.capability"`.
   - **Assertion**: Returns `status == "UNKNOWN"`, `maturity == "M0"`, with limitation `"capability is not declared in Complete-SCP reference"`.
6. **`test_capability_map_degraded_when_implementation_missing(tmp_path)`**:
   - **Target**: `scp/self_model/capability_map.py:212`.
   - **Execution**: Create mock reference & bindings declaring capability `"test.missing"` bound to nonexistent module `"scp.does_not_exist"`. Record Level C proof.
   - **Assertion**: Returns `status == "DEGRADED"` and limitations include `"evidence exists but current implementation binding is unavailable"`.
7. **`test_capability_map_blindspots_lifecycle(tmp_path)`**:
   - **Target**: `scp/self_model/capability_map.py:236` (`add_blindspot`, `list_blindspots`).
   - **Execution**: Add blindspot for `"epistemic.evidence"` with unobservable reason `"kernel crash"`, affected claims `["claim_1"]`. List blindspots with and without filter.
   - **Assertion**: Stored with status `"OPEN"`, created timestamp, filtered listing returns only matching records.
8. **`test_capability_map_clean_database_close(tmp_path)`**:
   - **Target**: `scp/self_model/capability_map.py:274`.
   - **Execution**: Initialize model, perform operations, call `model.close()`.
   - **Assertion**: Database connection cleanly closed without leaks.

---

#### Suite 4: `tests/test_observability_functional.py` (8 Tests)

```python
"""Functional tests for Observability and Telemetry subsystems.

Validates:
- SubsystemTelemetry heartbeat lifecycle, PID recording, and tick tracking
- Monitored cycle metrics (started, completed, asked, verified, stored, rejected)
- Fail-closed secret scrubbing in error summaries and json payloads
- Subsystem append-only JSONL run ledger
- OpenTelemetry graceful disable when unconfigured or disabled by env
- OpenTelemetry header sanitization and route exclusion when active
- Stale process detection threshold
- Database WAL configuration and busy timeout tolerance
"""
```

1. **`test_subsystem_telemetry_heartbeat_and_tick(tmp_path)`**:
   - **Target**: `scp/core/subsystem_telemetry.py:65` (`SubsystemTelemetry`).
   - **Execution**: Initialize `SubsystemTelemetry("crawler", data_dir=tmp_path)`. Call `tick(status="RUNNING")`.
   - **Assertion**: Table `subsystem_heartbeat` contains record with `subsystem == "crawler"`, current `owner_pid`, `last_status == "RUNNING"`, valid UTC ISO timestamp.
2. **`test_subsystem_telemetry_cycle_metrics_tracking(tmp_path)`**:
   - **Target**: `scp/core/subsystem_telemetry.py:165` (`record_cycle_start`, `record_cycle_complete`).
   - **Execution**: Call `record_cycle_start("cycle-1")`. Call `record_cycle_complete(status="SUCCESS", run_id="cycle-1", asked=3, verified=3, stored=2, rejected=1)`.
   - **Assertion**: `cycles_started == 1`, `cycles_completed == 1`, `last_status == "SUCCESS"`, `asked == 3`, `verified == 3`, `stored == 2`, `rejected == 1`.
3. **`test_subsystem_telemetry_secret_scrubbing_in_errors(tmp_path)`**:
   - **Target**: `scp/core/subsystem_telemetry.py:42` (`_safe_error`).
   - **Execution**: Call `record_cycle_failure(RuntimeError("HTTP 401 token=sk-super-secret-key-12345 password=mypassword"))`.
   - **Assertion**: `last_error_summary` in heartbeat table contains `token=<redacted>`, does NOT contain `sk-super-secret-key` or `mypassword`.
4. **`test_subsystem_telemetry_json_safe_payload_scrubbing(tmp_path)`**:
   - **Target**: `scp/core/subsystem_telemetry.py:55` (`_json_safe`).
   - **Execution**: Call `record_cycle_complete(run_id="c2", secret_data={"password": "secret", "token": "xyz", "safe_count": 42})`.
   - **Assertion**: Ledger payload strips keys `password`, `token`; preserves `safe_count == 42`.
5. **`test_subsystem_telemetry_run_ledger_append_only(tmp_path)`**:
   - **Target**: `scp/core/subsystem_telemetry.py:134` (`_append_ledger`).
   - **Execution**: Run 3 cycles. Read `<subsystem>_runs.jsonl`.
   - **Assertion**: File contains exactly 3 JSON lines, each parseable, with monotonically increasing `seq` and timestamp.
6. **`test_otel_configuration_disabled_by_env(monkeypatch)`**:
   - **Target**: `scp/observability/otel.py:14`.
   - **Execution**: Monkeypatch `SCP_OTEL_ENABLED="0"`. Call `configure_fastapi_otel(FastAPI())`.
   - **Assertion**: Returns `{"enabled": False, "reason": "SCP_OTEL_ENABLED=0"}`.
7. **`test_otel_configuration_missing_endpoint_degrades_gracefully(monkeypatch)`**:
   - **Target**: `scp/observability/otel.py:17`.
   - **Execution**: Monkeypatch `SCP_OTEL_ENABLED="1"`, `OTEL_EXPORTER_OTLP_ENDPOINT=""`. Call `configure_fastapi_otel(FastAPI())`.
   - **Assertion**: Returns `{"enabled": False, "reason": "OTEL_EXPORTER_OTLP_ENDPOINT is missing"}` without crashing.
8. **`test_otel_configuration_header_sanitization_rules()`**:
   - **Target**: `scp/observability/otel.py:43`.
   - **Execution**: Inspect sanitized fields in `configure_fastapi_otel`.
   - **Assertion**: Sensitive headers `authorization`, `cookie`, `set-cookie` are explicitly configured for sanitization.

---

#### Suite 5: `tests/test_concurrency_stress_v2.py` (8 Tests)

```python
"""High-concurrency and stress tests for persistence, ledger, and lock primitives.

Validates:
- ChatMemoryStore multi-threaded concurrent appends (10 threads x 50 records)
- ChatMemoryStore file lock re-entrancy and concurrent write during pruning
- TraceLedger multi-threaded concurrent appends (12 threads x 25 records)
- TraceLedger sequence continuity (1..N) and cryptographic hash chain verification
- TraceLedger backwards tail reader performance and consistency under concurrent writes
- SQLiteKernelStorage connection pool bounds (max_conns) and BEGIN IMMEDIATE concurrency
- db_manager concurrent readers and writers under read/write lock synchronization
- Zero file corruption, zero deadlocks, zero lost records under parallel stress
"""
```

1. **`test_chat_memory_store_high_concurrency_append_and_load(tmp_path)`**:
   - **Target**: `scp/core/chat_memory_store.py:140, 162`.
   - **Execution**: 10 worker threads appending 40 records each (400 total records) to session `"sess_stress"`. Concurrently, 4 reader threads continuously call `load("sess_stress")`.
   - **Assertion**: All 400 appends return `True`. Read lines parse with 0 JSON errors. Record hashes valid.
2. **`test_chat_memory_store_concurrent_append_under_prune_pressure(tmp_path, monkeypatch)`**:
   - **Target**: `scp/core/chat_memory_store.py:189` (`_prune_if_needed`).
   - **Execution**: Monkeypatch prune threshold to lower value (e.g. 5KB) to force repeated pruning during writes. 8 threads appending messages rapidly.
   - **Assertion**: Zero `PermissionError` on Windows (`msvcrt`). No file corruption. File remains valid JSONL.
3. **`test_trace_ledger_high_concurrency_hash_chain_integrity(tmp_path)`**:
   - **Target**: `scp/trace_ledger.py:95, 122`.
   - **Execution**: 12 worker threads each appending 25 trace entries (300 total) to `TraceLedger(tmp_path / "traces.jsonl")`.
   - **Assertion**: Total records = 300. `verify()["hash_chain_valid"] is True`. Sequence numbers form unbroken sequence `1..300` with 0 duplicates or omissions.
4. **`test_trace_ledger_tail_reader_accuracy_under_concurrent_writes(tmp_path)`**:
   - **Target**: `scp/trace_ledger.py:57` (`_read_tail`).
   - **Execution**: Interleave writes and tail-reads across 6 threads.
   - **Assertion**: Tail reader always reads valid `(seq, hash)` matching the most recently committed record.
5. **`test_sqlite_kernel_storage_connection_pool_bounds_and_concurrency(tmp_path)`**:
   - **Target**: `scp/kernel_storage.py:79` (`SQLiteKernelStorage`).
   - **Execution**: Initialize storage with `max_conns=8`. Spawn 16 concurrent threads executing `begin()`, `execute("INSERT ...")`, `commit()` 10 times each.
   - **Assertion**: All 160 transactions succeed. `len(storage._all_conns) <= 8` (pool capacity enforced without connection leak).
6. **`test_sqlite_kernel_storage_busy_timeout_retry_under_write_contention(tmp_path)`**:
   - **Target**: `scp/kernel_storage.py:140` (`begin` retry loop).
   - **Execution**: Multiple threads attempting immediate transactions simultaneously.
   - **Assertion**: Retries succeed within busy timeout; 0 unhandled `sqlite3.OperationalError: database is locked`.
7. **`test_db_manager_concurrent_readers_writers_under_lock(tmp_path)`**:
   - **Target**: `scp/core/db_manager.py:141, 150, 114` (`_db_lock`, `_read_lock`).
   - **Execution**: Test DB with table `counter`. 8 reader threads calling `db_query_all` / `db_query_one`. 4 writer threads calling `db_exec("INSERT ...")`.
   - **Assertion**: No crashes or query errors. Reader results are consistent snapshots.
8. **`test_db_manager_checkpoint_wal_under_concurrency(tmp_path)`**:
   - **Target**: `scp/core/db_manager.py:163` (`checkpoint_wal`).
   - **Execution**: Call `checkpoint_wal()` while reader threads run.
   - **Assertion**: Checkpoint executes cleanly without deadlocking active readers.

---

## 5. Verification Method

### 5.1 Programmatic Verification Commands

1. **Test Collection Verification**:
   ```bash
   python -m pytest tests/ --collect-only -q
   ```
   *Pass criteria*: Exit code 0, 0 collection errors, collected test count strictly exceeds baseline (expected: `2,097 tests collected`).

2. **Meta-Audit Authority Verification**:
   ```bash
   python tools/t00_meta_audit.py
   ```
   *Pass criteria*: Exit code 0, message `[T00 Meta-Audit] All integrity checks passed (0 new regressions)`. No new FA-01 (skips), FA-02 (deletions), or FA-04 (manufactured pass).

3. **Subsystem Functional Test Execution**:
   ```bash
   python -m pytest tests/test_epistemic_functional.py tests/test_task_kernel_stress.py tests/test_self_model_behavioral.py tests/test_observability_functional.py tests/test_concurrency_stress_v2.py -v
   ```
   *Pass criteria*: All 48 tests pass with `PASSED` status, 0 failures, 0 errors, 0 skips.

4. **Full Regression Suite Check**:
   ```bash
   python -m pytest tests/test_subsystem_*.py tests/test_p0_*.py -q
   ```
   *Pass criteria*: All existing subsystem tests continue to pass alongside new tests.

### 5.2 Invalidation Conditions
- Any test using `pytest.skip()` or `pytest.xfail()` (violates FA-01).
- Any existing test nodeid removed from `tests/` (violates FA-02).
- Any test creating real network connections or hardcoding port bindings.
- Any test failing to clean up temporary SQLite database files or locks.
- Concurrency test deadlocking on Windows due to unreleased `msvcrt` file lock handles.
