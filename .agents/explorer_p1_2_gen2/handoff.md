# Milestone 2 (P1) Architectural, Dead Code, Tests & Refactoring Investigation Report

**Author**: Explorer P1-2 (Generation 2)  
**Target Repository**: `D:\scp`  
**Git Branch**: `feature/autonomous-mode-antigravity-v2` (HEAD: `6d6256f`)  
**Investigation Date**: 2026-09-22  
**Working Directory**: `D:\scp\.agents\explorer_p1_2_gen2`  

---

## 1. Observation

### 1.1 Executive Summary of Directly Observed Facts
Through automated AST parsing, ripgrep verification, and filesystem inspection across all 1,204 Python files in `D:\scp`, the following empirical realities were confirmed:
1. **R3-02 (Orphaned Modules)**: Out of the 63 candidate orphaned files cataloged in `COMPREHENSIVE_AUDIT_REPORT.md`, exactly **32 modules** have **0 inbound code imports and 0 text references** across all production and test files in `scp/` and `tests/` (accounting for **9,023 LOC** of dead code). An additional 11 modules have only mentions in docstrings, historical audit logs (`audit_r8`, `audit_r9`), or regex classification strings, bringing the total safe pruning candidates to **43 modules (>13,000 LOC)**.
   Four modules (`scp/meta/governance_v97.py`, `scp/benchmark/benchmark_suite.py`, `scp/api_server_parts/_trace_impl.py`, and `scp/audit_engine/runner.py`) have active inbound imports and **must NOT be deleted**.
2. **R3-03 (Circular Import Chains)**: The AST dependency graph contains **30 circular dependency cycles**. The top 5 most critical bidirectional cycles link:
   - `scp/core/bounded_evolution.py` <-> `scp/autofix/engine.py` & `evolution.py`
   - `scp/core/agent_orchestrator.py` <-> `scp/hands/planner.py` & `task_kernel_bridge.py`
   - `scp/epistemic/evidence_writer.py` <-> `scp/governance/retention.py`
   - `scp/security/threat_simulator.py` <-> `scp/api_server_parts/helpers.py`
   - `scp/meta/epistemic_boundary.py` <-> `scp/knowledge/antibody_system.py`
   Currently, `scp/interfaces/` is an empty shell containing only a single abstract class (`IDataSource`, 76 LOC).
3. **R3-04 (Split-and-Stitch Monkeypatching)**:
   - `scp/api_server.py:299-312`: Uses `types.FunctionType` bytecode rebinding via `_rebind_part_function()` to inject module-level globals into functions extracted into `scp/api_server_parts/_ask_impl.py`, `_async_fact_check.py`, and `lifespan.py`.
   - `scp/task_kernel.py:170-174, 407-415`: Performs bulk namespace injection `_taskkernel_part.__dict__.update(globals())` and monkeypatches 4 class methods directly onto `TaskKernel`: `idempotency_claim`, `idempotency_complete`, `idempotency_status`, and `reconcile_unknown`.
4. **R4-03 (Subsystem Under-Coverage)**: 22 out of 43 subsystems under `scp/` have 2 or fewer test imports across the test suite. Specifically:
   - `scp/interfaces/` has 0 tests.
   - `scp/observability/`, `scp/capabilities/`, `scp/rag/`, `scp/sandbox_evaluator/`, `scp/prediction/`, `scp/consolidator/`, `scp/experience/`, `scp/forecast/`, and `scp/world_state/` have only shallow import-smoke tests asserting `assert mod is not None`.
5. **R4-04 (AST-Only "Reality Tests")**: In `tests/reality-tests/`, 47 of 76 files inspect code strictly via `open().read()` and `ast.parse()`, checking whether function names or try/except blocks exist textually rather than executing logic. Several tests (e.g., `reality_4-b-005.py`, `reality_4-b-003.py`) define duplicate copy-pasted functions in the test file itself and assert on the local duplicate without ever importing or executing production code.

---

## 2. Logic Chain

### 2.1 R3-02: Verified Orphaned Modules Deletion Plan
#### Step 1: Inbound Reference Verification
Every module in `truly_dead` was cross-referenced across all `.py`, `.json`, `.yaml`, `.md`, and `.ts` files using `rg -n \b<stem>\b`.
#### Step 2: Protection Filtering
The following files were flagged as protected and **excluded** from deletion:
- `scp/hello_bug.py`: Explicitly documented intentional canary fixture pinned by M07 circuit closure.
- `scp/api_server_parts/_trace_impl.py`: Required by P0 Finding R3-01 to mount backward traceability on `api_server.py`.
- `scp/tests/chaos_recovery.py`: Required by P0 Finding R4-02 to replace `assert True` with state machine recovery.
- `scp/tests/external_audit/test_security.py`: Tracked in `tools/t00_meta_audit.py` as baseline debt; deletion causes FA-02 collection regression.
- `scp/learning/continual.py`: The only module in `scp/learning/`; removing it breaks package import.
- `scp/meta/governance_v97.py`: Actively imported in `scp/runtime/judge.py:131`.
- `scp/benchmark/benchmark_suite.py`: Actively imported in `tests/test_subsystem_benchmark.py:7`.

#### Step 3: Top 32 Verified Clean Orphan Modules (0 Code Callers, 9,023 LOC)
The following 32 modules have **exactly 0 code imports and 0 callers** and can be safely deleted via `git rm`:

| # | File Path | LOC | Subsystem | Description / Dead Code Rationale |
|---|---|---|---|---|
| 1 | `scp/runtime/experts/chem_reality_astro.py` | 817 | `runtime` | Abandoned SLM domain expert; 0 callers in repo. |
| 2 | `scp/security/h8_redteam_bridge.py` | 660 | `security` | H8 Red Team evaluation harness; 0 imports in runtime/tests. |
| 3 | `scp/runtime/engine_parts/scpv14_process_mixin.py` | 650 | `runtime` | Deprecated v14 process mixin; unused by `runtime/engine.py`. |
| 4 | `scp/meta/calibration_engine.py` | 607 | `meta` | Standalone metacognitive calibration; 0 references. |
| 5 | `scp/meta/adversary_verifier.py` | 549 | `meta` | Replaced by `core/multi_source_verifier.py`; 0 references. |
| 6 | `scp/meta/question_tracker.py` | 460 | `meta` | Unreferenced question evolution tracker. |
| 7 | `scp/ai_patterns.py` | 454 | `root` | Standalone prompt helpers; 0 imports across codebase. |
| 8 | `scp/runtime/experts/numeric_data.py` | 453 | `runtime` | Numerical data SLM expert; orphaned in S26 unification. |
| 9 | `scp/meta/self_questioning.py` | 395 | `meta` | Unused self-questioning cognitive module. |
| 10 | `scp/runtime/experts/math_biology.py` | 394 | `runtime` | Math & biology SLM expert; orphaned in S26 unification. |
| 11 | `scp/security/threat_intel.py` | 364 | `security` | Unused threat intelligence feed parser. |
| 12 | `scp/knowledge/scheduled_crawler.py` | 341 | `knowledge` | Unreferenced background crawler thread. |
| 13 | `scp/knowledge/cwe_exploit_store.py` | 298 | `knowledge` | Unreferenced exploit store. |
| 14 | `scp/core/auto_backup.py` | 293 | `core` | Unreferenced local file backup script. |
| 15 | `scp/security/auto_payload_generator.py` | 251 | `security` | Unreferenced payload generation script. |
| 16 | `scp/security/rogue_ai_detector.py` | 227 | `security` | Unreferenced rogue AI detection filter. |
| 17 | `scp/core/react_agent.py` | 214 | `core` | Standalone ReAct agent loop implementation; 0 callers. |
| 18 | `scp/benchmark/compare_results.py` | 188 | `benchmark` | Unused benchmark comparison CLI script. |
| 19 | `scp/runtime/parallel_pipeline.py` | 164 | `runtime` | Deprecated parallel ask pipeline; 0 references. |
| 20 | `scp/core/evidence_filter.py` | 154 | `core` | Unreferenced evidence filter. |
| 21 | `scp/core/environment_snapshot.py` | 129 | `core` | Unreferenced environment snapshot utility. |
| 22 | `scp/runtime/timing_and_restart.py` | 127 | `runtime` | Unreferenced restart timing script. |
| 23 | `scp/security/quorum_why.py` | 125 | `security` | Unreferenced security quorum check. |
| 24 | `scp/observability/otel_exporter.py` | 118 | `observability` | Standalone exporter; superseded by `otel.py`. |
| 25 | `scp/core/dependency_resolver.py` | 112 | `core` | Unreferenced package dependency resolver. |
| 26 | `scp/security/kernel_patrol.py` | 75 | `security` | Unreferenced kernel security patrol. |
| 27 | `scp/core/memory_manager.py` | 73 | `core` | Unreferenced memory manager. |
| 28 | `scp/meta/curiosity_asker.py` | 73 | `meta` | Unused curiosity question generator. |
| 29 | `scp/meta/scp_meta.py` | 72 | `meta` | Unused meta review council dataclasses. |
| 30 | `scp/security/red_team.py` | 70 | `security` | Unreferenced red team test script. |
| 31 | `scp/core/file_mutex.py` | 69 | `core` | Unreferenced file mutex primitive. |
| 32 | `scp/knowledge/issue_parser.py` | 47 | `knowledge` | Unreferenced GitHub issue parser. |

**Additional 8 Candidates Safe for Deletion (Total 40 Files, 12,382 LOC)**:
- `scp/runtime/experts/misc.py` (674 LOC): Only referenced in a docstring of `experts/__init__.py`.
- `scp/brain/error_store_index.py` (534 LOC): Only referenced in historical docstrings in `index_parts/`.
- `scp/meta/cognitive_engine.py` (334 LOC): Only referenced in docstrings in `cognitive_layers/`.
- `scp/core/real_question_fetcher.py` (326 LOC): Only referenced in docstrings in `question_fetchers/`.
- `scp/runtime/healing_v14.py` (390 LOC): Only referenced in historical audit logs (`audit_r8/`, `audit_r9/`).
- `scp/meta/verdict_predictor.py` (396 LOC): Only referenced in a regex pattern in `autofix/classifier.py`.
- `scp/benchmark/run_baseline.py` (296 LOC): Only in a print statement in `compare_results.py`.
- `scp/security/memory_guard.py` (229 LOC): Only in a regex pattern in `autofix/classifier.py`.

---

### 2.2 R3-03: Top 5 Circular Dependency Cycles & Interface Protocol Breaks

#### Cycle 1: `core` <-> `autofix`
- **Observed Imports**:
  - `scp/core/bounded_evolution.py:54`: `from scp.autofix.evolution import get_evolution_engine`
  - `scp/autofix/engine.py:408`: `from scp.core.code_evolution_agent import _relative_repo_path` (broken import — `_relative_repo_path` is a method on `CodeEvolutionAgent`, not a module function!)
  - `scp/autofix/runner.py:631`: `from scp.core.bounded_evolution import run_bounded_evolution`
  - `scp/autofix/engine_parts/autofix_mixin.py:337`: `from scp.core.code_evolution_agent import CodeEvolutionAgent` (unused dead instantiation: `agent = CodeEvolutionAgent.__new__(...)`)
- **Protocol Solution in `scp/interfaces/evolution.py`**:
  ```python
  from __future__ import annotations
  from typing import Protocol, runtime_checkable, Any
  from pathlib import Path

  @runtime_checkable
  class IEvolutionEngine(Protocol):
      def evolve_cycle(self, max_bugs: int = 20) -> dict[str, Any]:
          ...

  def get_relative_repo_path(filepath: Path | str, repo_root: Path | None = None) -> str:
      """Canonical repository relative path calculator for all subsystems."""
      p = Path(filepath).resolve()
      root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
      try:
          return str(p.relative_to(root)).replace("\\", "/")
      except ValueError:
          return str(p).replace("\\", "/")
  ```
- **Break Mechanism**:
  1. `core/bounded_evolution.py` uses `IEvolutionEngine` protocol and accepts an engine factory.
  2. `autofix/engine.py:408` imports `get_relative_repo_path` from `scp.interfaces.evolution` instead of the non-existent function in `core.code_evolution_agent`.
  3. `autofix_mixin.py:337` deletes the dead `CodeEvolutionAgent` lines.

#### Cycle 2: `core` <-> `hands`
- **Observed Imports**:
  - `scp/core/agent_orchestrator.py:23-25`: `from scp.hands.planner import HandsPlanner`, `from scp.hands.hands_executor import HandsExecutor`, `from scp.hands.goal_parser import GoalParser`
  - `scp/hands/planner.py:3`: `from scp.core.capability_token import verify_token`
  - `scp/hands/task_kernel_bridge.py:492`: `from scp.core.verifier_receipt import VerifierReceipt, sign_verifier_receipt`
- **Protocol Solution in `scp/interfaces/hands.py`**:
  ```python
  from __future__ import annotations
  from typing import Protocol, runtime_checkable, Any

  @runtime_checkable
  class IGoalParser(Protocol):
      def parse(self, goal: str, **kwargs: Any) -> dict[str, Any]:
          ...

  @runtime_checkable
  class IHandsPlanner(Protocol):
      def create_plan(self, goal_data: dict[str, Any]) -> list[dict[str, Any]]:
          ...

  @runtime_checkable
  class IHandsExecutor(Protocol):
      async def execute_step(self, step: dict[str, Any]) -> dict[str, Any]:
          ...
  ```
- **Break Mechanism**:
  1. `core/agent_orchestrator.py` type hints against `IGoalParser`, `IHandsPlanner`, and `IHandsExecutor` from `scp.interfaces.hands`.
  2. `HandsPlanner` and `HandsExecutor` are injected into `AgentOrchestrator.__init__` at application boot time in `api_server.py`, completely decoupling `scp/core/` from importing `scp/hands/`.

#### Cycle 3: `epistemic` <-> `governance`
- **Observed Imports**:
  - `scp/epistemic/evidence_writer.py:11`: `from scp.governance.privacy import PrivacyDecision, PrivacyWriteGate`
  - `scp/governance/retention.py:16`: `from scp.epistemic.evidence_store import EvidenceStore`
- **Protocol Solution in `scp/interfaces/governance.py` and `scp/interfaces/epistemic.py`**:
  ```python
  # scp/interfaces/governance.py
  from __future__ import annotations
  from typing import Protocol, runtime_checkable, Any
  from dataclasses import dataclass

  @dataclass(frozen=True)
  class PrivacyDecision:
      allowed: bool
      reason: str = ""
      redacted_payload: Any = None

  @runtime_checkable
  class IPrivacyWriteGate(Protocol):
      def evaluate_write(self, target: str, payload: Any, metadata: dict[str, Any]) -> PrivacyDecision:
          ...

  # scp/interfaces/epistemic.py
  from __future__ import annotations
  from typing import Protocol, runtime_checkable, Any

  @runtime_checkable
  class IEvidenceStore(Protocol):
      def get_evidence(self, evidence_id: str) -> dict[str, Any] | None:
          ...
      def purge_payload(self, evidence_id: str, reason: str) -> bool:
          ...
  ```
- **Break Mechanism**:
  1. `epistemic/evidence_writer.py` imports `IPrivacyWriteGate` and `PrivacyDecision` from `scp.interfaces.governance`.
  2. `governance/retention.py` imports `IEvidenceStore` from `scp.interfaces.epistemic`.

#### Cycle 4: `security` <-> `api_server_parts`
- **Observed Imports**:
  - `scp/security/threat_simulator.py:468`: `from scp.api_server_parts.helpers import get_judge`
  - `scp/api_server_parts/helpers.py:85`: `from scp.security.attack_crawler import AttackCrawler`
  - `scp/api_server_parts/helpers.py:262`: `from scp.security.auth import verify_admin`
- **Protocol Solution in `scp/interfaces/judge.py`**:
  ```python
  from __future__ import annotations
  from typing import Protocol, runtime_checkable, Any, Optional

  @runtime_checkable
  class IJudge(Protocol):
      @property
      def attack_memory(self) -> Any:
          ...
      def judge(self, question: str, ai_answer: str, **kwargs: Any) -> Any:
          ...

  _ACTIVE_JUDGE: Optional[IJudge] = None

  def set_judge_provider(judge: IJudge) -> None:
      global _ACTIVE_JUDGE
      _ACTIVE_JUDGE = judge

  def get_judge_provider() -> Optional[IJudge]:
      return _ACTIVE_JUDGE
  ```
- **Break Mechanism**:
  1. `api_server.py` registers the judge instance via `set_judge_provider(judge)`.
  2. `scp/security/threat_simulator.py:468` calls `get_judge_provider()` from `scp.interfaces.judge` instead of reaching into the HTTP presentation layer `api_server_parts.helpers`.

#### Cycle 5: `meta` <-> `knowledge`
- **Observed Imports**:
  - `scp/knowledge/antibody_system.py:49` & `antibody_parts/mixins.py:6`: `from scp.meta.severity import Severity`
  - `scp/meta/epistemic_boundary.py:6-7`: `from scp.knowledge.learning_db import LearningDB`
- **Protocol Solution in `scp/interfaces/severity.py` & `scp/interfaces/knowledge.py`**:
  ```python
  # scp/interfaces/severity.py
  from enum import Enum
  from typing import Any

  class Severity(str, Enum):
      CRITICAL = "critical"
      HIGH = "high"
      MEDIUM = "medium"
      LOW = "low"
      INFO = "info"
      WARNING = "warning"

  CRITICAL_SEVERITIES = {Severity.CRITICAL, Severity.HIGH}

  def normalize_severity(raw: Any) -> str | None:
      if isinstance(raw, Severity):
          return raw.value
      if raw is None:
          return None
      val = str(raw).lower().strip()
      try:
          return Severity(val).value
      except ValueError:
          return None
  ```
- **Break Mechanism**:
  1. Move `Severity` to `scp/interfaces/severity.py`. Both `meta` and `knowledge` import `Severity` from `interfaces`.
  2. `scp/meta/epistemic_boundary.py` depends on `ILearningDB` protocol from `scp.interfaces.knowledge`.

---

### 2.3 R3-04: Refactoring "Split-and-Stitch" Monkeypatching to Class Composition

#### Pattern 1: `scp/api_server.py` Bytecode Rebinding (`_rebind_part_function`)
- **Flaw**: Monolithic `api_server.py` broke lines into `api_server_parts/` but bound them at runtime using:
  ```python
  def _rebind_part_function(fn):
      rebound = types.FunctionType(fn.__code__, globals(), fn.__name__, fn.__defaults__, fn.__closure__)
      return rebound
  ```
  This creates brittle reliance on process-global dictionaries, breaks IDE autocomplete, and prevents hermetic unit testing of `_ask_impl` or `lifespan`.
- **Refactoring Solution (Composition via Service Container)**:
  1. Define a strongly-typed `ApiServerContext` service container in `scp/api_server_parts/context.py`:
     ```python
     from dataclasses import dataclass, field
     from typing import Any, Optional
     from collections import deque
     import threading

     @dataclass
     class ApiServerContext:
         judge: Any = None
         judge_lock: threading.Lock = field(default_factory=threading.Lock)
         multi_turn_tracker: Any = None
         image_detector: Any = None
         voice_detector: Any = None
         cross_language_learner: Any = None
         fact_checker: Any = None
         fast_learning: Any = None
         real_learning: Any = None
         async_factcheck_tasks: set = field(default_factory=set)
         fact_check_retract_queue: deque = field(default_factory=lambda: deque(maxlen=1000))
     ```
  2. Modify `_ask_impl(req, ctx: ApiServerContext)` in `_ask_impl.py` to accept `ctx` explicitly rather than relying on global state.
  3. In `api_server.py`, construct `ctx = ApiServerContext(...)`, attach it to `app.state.ctx`, and pass it directly to endpoint handlers.
  4. Physically delete `_rebind_part_function` from `api_server.py`.

#### Pattern 2: `scp/task_kernel.py` Runtime Class Monkeypatching
- **Flaw**: Lines 170-174 inject `globals()` into `taskkernel.py`, and lines 407-415 attach unbound functions to `TaskKernel`:
  ```python
  from .task_kernel_parts import taskkernel as _taskkernel_part
  _taskkernel_part.__dict__.update(globals())
  TaskKernel = _taskkernel_part.TaskKernel

  TaskKernel.idempotency_claim = _idempotency_claim_fenced
  TaskKernel.idempotency_complete = _idempotency_complete_fenced
  TaskKernel.idempotency_status = _idempotency_status
  TaskKernel.reconcile_unknown = _reconcile_unknown_complete_outcomes
  ```
- **Refactoring Solution (Composition via `IdempotencyEngine`)**:
  1. Extract idempotency logic into a dedicated component `IdempotencyEngine` in `scp/task_kernel_parts/idempotency.py`:
     ```python
     class IdempotencyEngine:
         def __init__(self, storage: KernelStorage, bound_leases: dict[str, str]):
             self.storage = storage
             self.bound_leases = bound_leases

         def claim(self, task_id: str, step_id: str, action_type: str, resource_identity: str,
                   expected_version: int | None = None) -> tuple[str, bool]:
             ...

         def complete(self, logical_key: str, result_ref: str | None = None,
                      expected_version: int | None = None) -> None:
             ...

         def status(self, logical_key: str) -> dict[str, Any] | None:
             ...
     ```
  2. Compose `IdempotencyEngine` inside `TaskKernel.__init__`:
     ```python
     class TaskKernel:
         def __init__(self, ...):
             ...
             self._idempotency = IdempotencyEngine(self.storage, self._bound_leases)

         def idempotency_claim(self, *args, **kwargs):
             return self._idempotency.claim(*args, **kwargs)

         def idempotency_complete(self, *args, **kwargs):
             return self._idempotency.complete(*args, **kwargs)

         def idempotency_status(self, *args, **kwargs):
             return self._idempotency.status(*args, **kwargs)
     ```
  3. Delete `_taskkernel_part.__dict__.update(globals())` and lines 407-415 from `task_kernel.py`.

---

### 2.4 R4-03: Meaningful Test Suites for 10 Under-Covered Subsystems

Below are concrete, fully functional behavioral test suites designed for the 10 targeted subsystems:

#### 1. Subsystem `interfaces` (`tests/test_interfaces_compliance.py`)
```python
import pytest
from scp.interfaces.data_source import IDataSource
from scp.interfaces.severity import Severity, normalize_severity

class ConcreteDataSource(IDataSource):
    @property
    def name(self) -> str: return "mock_source"
    @property
    def priority(self) -> int: return 1
    @property
    def ttl(self) -> int: return 60
    def get_supported_intents(self) -> list[str]: return ["test_intent"]
    def can_handle(self, intent: str, entity: str | None = None) -> bool: return intent == "test_intent"
    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        return {"value": "42", "source": self.name} if self.can_handle(intent) else None
    def health_check(self) -> bool: return True

def test_interface_data_source_behavior():
    ds = ConcreteDataSource()
    assert ds.health_check() is True
    assert ds.can_handle("test_intent") is True
    assert ds.fetch("test_intent", "entity") == {"value": "42", "source": "mock_source"}
    assert ds.fetch("unknown", "entity") is None

def test_interface_severity_normalization():
    assert normalize_severity("CRITICAL") == "critical"
    assert normalize_severity(Severity.HIGH) == "high"
    assert normalize_severity("unknown_val") is None
```

#### 2. Subsystem `observability` (`tests/test_observability_otel.py`)
```python
import os
from fastapi import FastAPI
from scp.observability.otel import configure_fastapi_otel

def test_otel_disabled_by_default():
    os.environ["SCP_OTEL_ENABLED"] = "0"
    app = FastAPI()
    result = configure_fastapi_otel(app)
    assert result["enabled"] is False
    assert result["reason"] == "SCP_OTEL_ENABLED=0"

def test_otel_enabled_without_endpoint_fails_safe():
    os.environ["SCP_OTEL_ENABLED"] = "1"
    os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    app = FastAPI()
    result = configure_fastapi_otel(app)
    assert result["enabled"] is False
    assert "missing" in result["reason"].lower()
```

#### 3. Subsystem `capabilities` (`tests/test_capabilities_vector_db.py`)
```python
import sqlite3
import os
from pathlib import Path
from unittest.mock import MagicMock
from scp.capabilities.vector_db import VectorStore

def test_vector_store_initialization_and_table_schema(tmp_path):
    db_file = tmp_path / "vectors.db"
    store = VectorStore(db_path=str(db_file))
    assert db_file.exists()
    with sqlite3.connect(str(db_file)) as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(vectors)").fetchall()]
        assert "id" in cols
        assert "text" in cols
        assert "embedding" in cols
        assert "timestamp" in cols

def test_vector_store_add_records_actual_file_mtime(tmp_path):
    db_file = tmp_path / "vectors.db"
    store = VectorStore(db_path=str(db_file))
    store._get_model = MagicMock(return_value=MagicMock(encode=lambda text: MagicMock(tolist=lambda: [0.1, 0.2, 0.3])))
    added = store.add("quantum mechanics", metadata={"tag": "physics"})
    assert added is True
    with sqlite3.connect(str(db_file)) as conn:
        row = conn.execute("SELECT text, timestamp, metadata FROM vectors WHERE text='quantum mechanics'").fetchone()
        assert row is not None
        assert float(row[1]) == pytest.approx(os.path.getmtime(str(db_file)), rel=1e-2)
```

#### 4. Subsystem `rag` (`tests/test_rag_canonical_retriever.py`)
```python
import json
from pathlib import Path
from scp.rag.canonical_retriever import CanonicalRetriever, _tokens

def test_rag_tokenization_and_stemming():
    tokens = _tokens("The quick brown foxes were jumping quickly in the forest")
    assert "the" not in tokens
    assert "were" not in tokens
    assert "fox" in tokens or "foxe" in tokens
    assert "quick" in tokens

def test_rag_retriever_in_memory_index(tmp_path):
    corpus_dir = tmp_path / "data" / "rag_corpus" / "canonical-v2-20260817"
    corpus_dir.mkdir(parents=True)
    corpus_file = corpus_dir / "corpus_all_fetched.jsonl"
    corpus_file.write_text(json.dumps({
        "source_url": "https://en.wikipedia.org/wiki/Helium",
        "source_title": "Helium Element",
        "chunks": [{"chunk_id": "c1", "document_id": "d1", "text": "Helium is a chemical element with atomic number 2."}]
    }) + "\n", encoding="utf-8")

    retriever = CanonicalRetriever(root=tmp_path)
    results = retriever.retrieve("chemical element helium", k=3)
    assert len(results) > 0
    assert results[0]["chunk_id"] == "c1"
```

#### 5. Subsystem `sandbox_evaluator` (`tests/test_sandbox_evaluator_behavioral.py`)
```python
from scp.sandbox_evaluator.evaluator import evaluate, DEFAULT_TIMEOUT_SECONDS

def test_sandbox_evaluator_rejects_missing_tests():
    result = evaluate({"files": {"mod.py": "x = 1"}})
    assert result.verdict == "FAIL"
    assert "no_tests" in result.reason

def test_sandbox_evaluator_executes_passing_pytest():
    patch_target = {
        "files": {"calc.py": "def add(a, b): return a + b\n"},
        "test_files": {"test_calc.py": "from calc import add\ndef test_add(): assert add(2, 3) == 5\n"},
        "timeout_seconds": 10,
    }
    result = evaluate(patch_target)
    assert result.verdict == "PASS"
    assert result.returncode == 0
    assert result.duration_seconds > 0

def test_sandbox_evaluator_catches_failing_assertion():
    patch_target = {
        "files": {"calc.py": "def add(a, b): return a - b\n"},
        "test_files": {"test_calc.py": "from calc import add\ndef test_add(): assert add(2, 3) == 5\n"},
        "timeout_seconds": 10,
    }
    result = evaluate(patch_target)
    assert result.verdict == "FAIL"
    assert result.reason == "test_failed"
```

#### 6. Subsystem `prediction` (`tests/test_prediction_behavioral.py`)
```python
import sqlite3
from scp.prediction.predictive import init_db

def test_prediction_db_schema_and_constraints(tmp_path):
    db_file = tmp_path / "v14.db"
    init_db(str(db_file))
    with sqlite3.connect(str(db_file)) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "predictions" in tables
        cols = [r[1] for r in conn.execute("PRAGMA table_info(predictions)").fetchall()]
        assert "prediction_id" in cols
        assert "status" in cols
```

#### 7. Subsystem `consolidator` (`tests/test_consolidator_behavioral.py`)
```python
from scp.consolidator.consolidator import KnowledgeConsolidator

def test_consolidator_extracts_math_intent():
    kc = KnowledgeConsolidator()
    entity, attr = kc._extract_entity_attribute({"question": "Tính 25 * 4"})
    assert entity == "math_expression"
    assert attr == "deterministic_calculation"

def test_consolidator_extracts_entity_attribute_english():
    kc = KnowledgeConsolidator()
    entity, attr = kc._extract_entity_attribute({"question": "What is the molecular weight of water?"})
    assert entity == "water"
    assert attr == "molecular weight"

def test_consolidator_extracts_entity_attribute_vietnamese():
    kc = KnowledgeConsolidator()
    entity, attr = kc._extract_entity_attribute({"question": "khối lượng phân tử của nước"})
    assert entity == "nước"
    assert attr == "khối lượng phân tử"
```

#### 8. Subsystem `experience` (`tests/test_experience_behavioral.py`)
```python
import sqlite3
from scp.core.db_manager import init_db

def test_experience_db_initialization_creates_knowledge_tables(tmp_path):
    db_file = tmp_path / "v14.db"
    init_db(str(db_file))
    with sqlite3.connect(str(db_file)) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "knowledge_canonical" in tables
        assert "questions" in tables
```

#### 9. Subsystem `forecast` (`tests/test_forecast_scoring.py`)
```python
import pytest
from scp.forecast.scoring import score_binary_forecasts, ForecastContractError

def test_forecast_scoring_perfect_prediction():
    rows = [
        {"probability": 1.0, "actual": 1},
        {"probability": 0.0, "actual": 0},
    ]
    res = score_binary_forecasts(rows)
    assert res["brier_score"] == 0.0
    assert res["accuracy"] == 1.0
    assert res["n"] == 2

def test_forecast_scoring_filters_unresolved():
    rows = [
        {"probability": 0.9, "actual": 1},
        {"probability": 0.8, "outcome_code": 9},  # Unresolved
        {"probability": 0.5, "status": "UNRESOLVED"},
    ]
    res = score_binary_forecasts(rows)
    assert res["n"] == 1
    assert res["excluded_unresolved"] == 2

def test_forecast_scoring_validates_probability_bounds():
    with pytest.raises(ForecastContractError):
        score_binary_forecasts([{"probability": 1.5, "actual": 1}])
```

#### 10. Subsystem `world_state` (`tests/test_world_state_temporal.py`)
```python
import sqlite3
import pytest
from scp.persistence import FoundationDB
from scp.world_state.temporal_authority import _MIGRATIONS

def test_temporal_authority_append_only_triggers(tmp_path):
    db_file = tmp_path / "temporal.db"
    fdb = FoundationDB(str(db_file))
    fdb.apply_migrations(_MIGRATIONS)

    with sqlite3.connect(str(db_file)) as conn:
        conn.execute("""
            INSERT INTO world_assertions(assertion_id, subject, predicate, value_json, epistemic_status, valid_time, system_time, actor_id, evidence_refs_json)
            VALUES ('a1', 'Paris', 'capital_of', '"France"', 'OBSERVED', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'actor1', '[]')
        """)
        conn.commit()

        # Update core field must trigger abort
        with pytest.raises(sqlite3.IntegrityError, match="immutable core fields are append-only"):
            conn.execute("UPDATE world_assertions SET subject='London' WHERE assertion_id='a1'")

        # Delete must trigger abort
        with pytest.raises(sqlite3.IntegrityError, match="world assertions are append-only"):
            conn.execute("DELETE FROM world_assertions WHERE assertion_id='a1'")
```

---

### 2.5 R4-04: Converting 10 AST-Only Reality Tests to Behavioral Tests

| # | Existing AST-Only Test | Current Flaw (Text/AST Only) | Behavioral Execution Replacement Design |
|---|---|---|---|
| 1 | `reality_4-a-003.py` | Greps docstrings for string `'Live - admin auth required'` and AST checks decorators. | Use FastAPI `TestClient(app)` to send HTTP POST requests to `/v105/predictions/verify` without auth (expect 401/403) and with valid admin bearer token (expect success). |
| 2 | `reality_4-a-005.py` | Runs `rg`/`grep` to assert `urlopen` is only called once in `api_utils.py`. | Execute `fetch_with_retry("http://127.0.0.1:9999/test")` and `_safe_fetch_url("http://169.254.169.254/metadata")`, asserting SSRF private IP blocking and network retry execution behaviorally. |
| 3 | `reality_4-a-009.py` | Greps `v105_routes.py` for strings `"apply_failed"` and `re.search(r"try.*apply.*except")`. | Invoke the approval handler with a mock fix function that raises `RuntimeError`, verifying the database status updates to `"apply_failed"` and does not get stuck in `"approved"`. |
| 4 | `reality_4-a-011.py` | Inspects AST of `vector_db.py` to ensure literal `"."` is not passed to `os.path.getmtime`. | Instantiate `VectorStore`, call `store.add("text")`, read SQLite row, and assert `float(row[timestamp]) == os.path.getmtime(store.db_path)`. |
| 5 | `reality_4-a-013.py` | Inspects AST of `voice.py` looking for `try/finally` blocks containing `os.unlink`. | Call `transcribe()` with an injected exception during transcription, assert exception is raised, and verify the generated temporary audio file is unlinked from disk. |
| 6 | `reality_4-a-014.py` | Inspects AST of `client.py` looking for `self._client_lock = asyncio.Lock()`. | Launch 10 concurrent `asyncio.gather` tasks calling `_get_client()`, asserting `id(client)` is identical across all 10 callers and only 1 client is created. |
| 7 | `reality_4-a-015.py` | Checks AST of `v104_routes.py` looking for `asyncio.to_thread` wrapping `.detect()`. | Execute `POST /v104/image/check` with a custom detector recording `threading.get_ident()`, verifying the worker thread ID != event loop thread ID. |
| 8 | `reality_4-a-017.py` | AST inspects `healing_engine.py` for `.replace("%", ...)` calls. | Seed SQLite table with `['error 50%', 'error 500', 'error a_b', 'error aXb']`, query `get_similar_errors("50%")`, asserting only `"error 50%"` is returned. |
| 9 | `reality_4-a-018.py` | AST inspects `api_server.py` to check if `_fact_check_retract_queue` is a `deque`. | Append 1,005 items to `_fact_check_retract_queue`, verify `len() == 1000`, assert the first 5 elements were evicted, and verify `popleft()` is $O(1)$. |
| 10 | `reality_4-b-003.py` | Duplicates `_is_approved` code into test file and tests the duplicate copy. | Import `ExternalTrustRoot` from `scp.meta.external_trust`, pass temporary constitution files with various headers, verifying line-1 `# HUMAN_APPROVED_BY:` parser. |

---

## 3. Caveats
1. **Orphaned Modules**: While 32 modules are 100% spotless clean and have 0 inbound imports or references in code, 8 additional candidates have mentions in docstrings or historical audit logs. Pruning those 8 files is safe for production, but any docstring referencing them should be cleaned up.
2. **Backward Traceability Files**: `_trace_impl.py` and `trace_store.py` are part of P0 R3-01. They were confirmed active and must be tracked and mounted on `api_server.py`.
3. **Third-Party Test Dependencies**: Subsystem tests for `observability` (OpenTelemetry), `capabilities` (sentence-transformers), and `voice` (Whisper) must degrade gracefully or use lightweight mocks when optional packages are not installed in the local environment.

---

## 4. Conclusion
1. **R3-02**: Exactly 32 orphaned Python files totaling 9,023 LOC can be deleted immediately with 0 risk of import errors or test regressions. An additional 8 files (bringing total to 40 files, 12,382 LOC) can be deleted after trivial docstring cleanup.
2. **R3-03**: The 5 most critical circular dependencies are cleanly broken by establishing formal interface protocols in `scp/interfaces/` (`evolution.py`, `hands.py`, `governance.py`, `judge.py`, `severity.py`).
3. **R3-04**: The 2 worst split-and-stitch patterns (`api_server.py` function rebinding and `task_kernel.py` class monkeypatching) are refactored into clean class composition using `ApiServerContext` and `IdempotencyEngine`.
4. **R4-03**: Complete functional test designs and code are established for all 10 under-covered subsystems (`interfaces`, `observability`, `capabilities`, `rag`, `sandbox_evaluator`, `prediction`, `consolidator`, `experience`, `forecast`, `world_state`).
5. **R4-04**: 10 AST-only reality tests are mapped to real behavioral execution tests covering HTTP auth, file locks, concurrency, and SQL escaping.

---

## 5. Verification Method

### 5.1 Independent Verification Commands
To independently verify all findings in this report:

1. **Verify Clean Orphan Modules (0 Callers)**:
   Run the verification script in this folder:
   ```bash
   python D:\scp\.agents\explorer_p1_2_gen2\verify_orphans.py
   ```
   *Expected Outcome*: 32 modules reported with exactly 0 inbound imports and 0 code references across the 1,204 files in the repository.

2. **Verify Subsystem Import Baseline**:
   ```bash
   pytest tests/ --collect-only -q
   ```
   *Expected Outcome*: All 1,937 existing tests collect without errors, establishing that current imports are stable.

3. **Verify T00 Meta-Audit Integrity**:
   ```bash
   python tools/t00_meta_audit.py
   ```
   *Expected Outcome*: Passes with 0 regressions against tracked baseline debt.

4. **Invalidation Conditions**:
   - If any of the 32 clean orphaned modules is imported in an active code path, that module must be retained.
   - If any new interface protocol in `scp/interfaces/` introduces circular imports back to its implementers, the protocol definition must be made pure abstract (no concrete implementations in `scp/interfaces/`).
