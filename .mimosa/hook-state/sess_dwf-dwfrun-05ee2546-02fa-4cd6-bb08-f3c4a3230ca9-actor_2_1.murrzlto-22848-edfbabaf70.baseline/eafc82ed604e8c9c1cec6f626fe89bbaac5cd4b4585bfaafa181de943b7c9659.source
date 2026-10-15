from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def _fail_closed_ci_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the parity profile test-scoped so collection cannot pollute other gates."""
    monkeypatch.setenv("SCP_JWT_SECRET", "god-split-parity-test-secret-32bytes")
    monkeypatch.setenv("SCP_PRODUCTION_MODE", "0")
    monkeypatch.setenv("SCP_SKIP_STARTUP_GATE", "0")
    monkeypatch.setenv("SCP_EGRESS_MODE", "deny")


TARGET_MODULES = (
    "scp.api_server",
    "scp.autofix.engine",
    "scp.autofix.llm_fix",
    "scp.autofix.scanners.cross_func_taint_scanner",
    "scp.benchmark.run_benchmark_v2",
    "scp.core.db_manager",
    "scp.core.fast_learning_engine",
    "scp.data_sources.domain_registry",
    "scp.knowledge.antibody_system",
    "scp.meta.why_engine",
    # [S26 2026-09-13] "scp.runtime.judge_parts.judgecore_mixin" removed:
    # judge_parts/ (god-split thế hệ cũ) đã bị xóa sau audit — 0 caller sống
    # (judge.py hiện hành = RealityJudge tier1+LLM, không import judge_parts;
    # điểm import code duy nhất chính là entry này). Xóa MODULE PRODUCT trước,
    # xóa contract entry theo sau — không phải hạ chuẩn cho module còn sống.
    "scp.task_kernel",
)


@pytest.mark.parametrize("module_name", TARGET_MODULES)
def test_split_target_imports(module_name: str) -> None:
    """A semantic split may not turn an importable production module into a syntax/import failure."""
    module = importlib.import_module(module_name)
    assert module is not None


def test_domain_registry_keeps_parent_registry_binding() -> None:
    from scp.data_sources.domain_registry import search_domains_by_keyword

    assert "geography" in search_domains_by_keyword("What is the capital of France?")


def test_benchmark_helpers_keep_normalization_dependencies() -> None:
    from scp.benchmark.run_benchmark_v2 import check_factual_correctness

    ok, method = check_factual_correctness("4", "4", "numeric")
    assert ok is True
    assert method.startswith("numeric_match")


def test_db_manager_parts_share_runtime_state(tmp_path: Path) -> None:
    from scp.core.db_manager import db_query_one
    from scp.core.db_manager_parts._get_path_conn import _path_conns

    db_path = str(tmp_path / "parity.db")
    try:
        row = db_query_one("SELECT 1 AS x", db_path=db_path)
        assert row == {"x": 1}
    finally:
        conn = _path_conns.pop(db_path, None)
        if conn:
            conn.close()


def test_db_manager_extracted_functions_bind_to_authoritative_globals() -> None:
    """DB split functions must mutate one facade-owned process state."""
    from scp.core import db_manager

    for fn in (
        db_manager._get_path_conn,
        db_manager.get_db,
        db_manager._preflight_integrity_check,
        db_manager.db_exec,
        db_manager.db_batch_flush,
        db_manager.init_db,
        db_manager._init_all_module_tables,
        db_manager._migrate_verdict_cache_schema,
        db_manager._migrate_knowledge_schema,
        db_manager._migrate_reverify_schema,
    ):
        assert fn.__globals__ is db_manager.__dict__


def test_fast_learning_engine_keeps_constants_and_schema(tmp_path: Path) -> None:
    from scp.core.db_manager_parts._get_path_conn import _path_conns
    from scp.core.fast_learning_engine import (
        FastLearningEngine,
        get_country_domain_matrix,
    )

    db_path = str(tmp_path / "learning.db")
    try:
        engine = FastLearningEngine(
            scp_db_path=db_path,
            data_dir=str(tmp_path / "data"),
        )
        assert engine is not None
        matrix = get_country_domain_matrix()
        assert "Việt Nam" in matrix
        assert "geography" in matrix["Việt Nam"]
    finally:
        conn = _path_conns.pop(db_path, None)
        if conn:
            conn.close()


def test_fast_learning_thread_guard_is_facade_owned() -> None:
    """The idempotent thread singleton must not fork into a part-module scalar."""
    import scp.core.fast_learning_engine as fast_learning

    assert fast_learning.start_fast_learning_thread.__globals__ is fast_learning.__dict__


def test_antibody_split_preserves_behavior() -> None:
    from scp.knowledge.antibody_system import DomainAntibodySystem

    system = DomainAntibodySystem()
    assert system.should_run(
        "dosage_validator",
        "What dosage should be used?",
        "medical",
        "paracetamol 500mg",
    ) is True


def test_why_engine_split_preserves_helper_wiring() -> None:
    from scp.meta.why_engine import WhyEngine

    engine = WhyEngine.__new__(WhyEngine)
    target, target_type, evidence_type = engine.identify_target("capital of France?")
    assert target
    assert target_type == "entity"
    assert evidence_type == "geographic_database"


def test_llm_fix_extracted_function_keeps_module_dependencies(tmp_path: Path) -> None:
    from scp.autofix.llm_fix import generate_fix_for_bug

    bug = SimpleNamespace(
        file=str(tmp_path / "does-not-exist.py"),
        line=1,
        bug_type="UnusedImport",
        description="unused import",
        suggested_fix="",
    )
    # Baseline contract: missing source file returns None; extraction must not
    # fail earlier with NameError because helper globals were left behind.
    assert generate_fix_for_bug(bug) is None


def test_cross_func_scanner_extracted_function_keeps_callgraph_helpers(tmp_path: Path) -> None:
    from scp.autofix.scanners.cross_func_taint_scanner import scan_file

    target = tmp_path / "safe_target.py"
    target.write_text("def identity(value):\n    return value\n", encoding="utf-8")
    result = scan_file(target)
    assert isinstance(result, list)


def test_cross_func_scanner_cache_is_facade_owned() -> None:
    """The expensive call-graph cache must be a single composition-root scalar."""
    import scp.autofix.scanners.cross_func_taint_scanner as scanner

    assert scanner._get_scp_call_graph.__globals__ is scanner.__dict__
    assert scanner.scan_file.__globals__ is scanner.__dict__
    assert scanner.scan_scp.__globals__ is scanner.__dict__


def test_task_kernel_split_preserves_create_contract(tmp_path: Path) -> None:
    from scp.task_kernel import TaskKernel

    kernel = TaskKernel(tmp_path / "kernel.db")
    try:
        task = kernel.create_task("parity-task", "parity", "prove split parity")
        assert task["task_id"] == "parity-task"
        assert task["state"] == "CREATED"
    finally:
        kernel.close()


def test_autofix_engine_constructs_after_split(tmp_path: Path) -> None:
    from scp.autofix.engine import AutoFixEngine

    engine = AutoFixEngine(data_dir=str(tmp_path / "autofix"))
    assert engine.data_dir.exists()


def test_api_server_keeps_public_service_identity() -> None:
    from scp.api_server import app

    assert getattr(app, "title", "")


def test_api_server_extracted_functions_bind_to_authoritative_globals() -> None:
    """Extracted API functions must execute against the composition root state."""
    from scp import api_server

    assert api_server._ask_impl.__globals__ is api_server.__dict__
    assert api_server._async_fact_check.__globals__ is api_server.__dict__

    lifespan_raw = getattr(api_server.lifespan, "__wrapped__", None)
    assert callable(lifespan_raw)
    assert lifespan_raw.__globals__ is api_server.__dict__


def test_api_server_keeps_detailed_health_contract() -> None:
    """The GOD split may not orphan or duplicate the detailed health endpoint."""
    from scp import api_server

    matches = [
        route
        for route in api_server.app.routes
        if getattr(route, "path", None) == "/health/detailed"
    ]
    assert len(matches) == 1

    route = matches[0]
    assert "GET" in (getattr(route, "methods", set()) or set())
    assert getattr(route, "endpoint", None) is api_server.health_detailed
    assert route.endpoint.__globals__ is api_server.__dict__


def test_split_facades_keep_public_module_identity() -> None:
    """Facade classes must retain the import identity they had before splitting."""
    from scp.autofix.engine import AutoFixEngine
    from scp.core.fast_learning_engine import FastLearningEngine
    from scp.knowledge.antibody_system import DomainAntibodySystem
    from scp.meta.why_engine import WhyEngine
    from scp.task_kernel import TaskKernel

    for exported_type, expected_module in (
        (AutoFixEngine, "scp.autofix.engine"),
        (FastLearningEngine, "scp.core.fast_learning_engine"),
        (DomainAntibodySystem, "scp.knowledge.antibody_system"),
        (WhyEngine, "scp.meta.why_engine"),
        (TaskKernel, "scp.task_kernel"),
    ):
        assert exported_type.__module__ == expected_module


def test_split_facades_keep_public_callable_identity() -> None:
    """Extracted public functions must not expose implementation-only part modules."""
    from scp.autofix.llm_fix import generate_fix_for_bug, process_bug_with_llm
    from scp.autofix.scanners.cross_func_taint_scanner import scan_file, scan_scp
    from scp.benchmark.run_benchmark_v2 import (
        check_factual_correctness,
        evaluate_questions_v2,
    )
    from scp.core.db_manager import db_exec, get_db, init_db
    from scp.core.fast_learning_engine import start_fast_learning_thread
    from scp.data_sources.domain_registry import search_domains_by_keyword
    from scp.meta.why_engine import init_why_db

    for exported_callable, expected_module in (
        (generate_fix_for_bug, "scp.autofix.llm_fix"),
        (process_bug_with_llm, "scp.autofix.llm_fix"),
        (scan_file, "scp.autofix.scanners.cross_func_taint_scanner"),
        (scan_scp, "scp.autofix.scanners.cross_func_taint_scanner"),
        (check_factual_correctness, "scp.benchmark.run_benchmark_v2"),
        (evaluate_questions_v2, "scp.benchmark.run_benchmark_v2"),
        (get_db, "scp.core.db_manager"),
        (db_exec, "scp.core.db_manager"),
        (init_db, "scp.core.db_manager"),
        (start_fast_learning_thread, "scp.core.fast_learning_engine"),
        (search_domains_by_keyword, "scp.data_sources.domain_registry"),
        (init_why_db, "scp.meta.why_engine"),
    ):
        assert exported_callable.__module__ == expected_module


# [S26 2026-09-13] test_judge_core_preserves_public_judge_contract removed:
# subject (scp/runtime/judge_parts/judgecore_mixin.py) deleted as dead code —
# see TARGET_MODULES note above. 11/12 god-split parity contracts remain.
def test_judge_parts_dead_code_stays_dead() -> None:
    """Guard ngược: judge_parts không được hồi sinh ngầm (re-import phải fail)."""
    import importlib.util
    import sys

    assert importlib.util.find_spec("scp.runtime.judge_parts") is None
    assert "scp.runtime.judge_parts" not in sys.modules
