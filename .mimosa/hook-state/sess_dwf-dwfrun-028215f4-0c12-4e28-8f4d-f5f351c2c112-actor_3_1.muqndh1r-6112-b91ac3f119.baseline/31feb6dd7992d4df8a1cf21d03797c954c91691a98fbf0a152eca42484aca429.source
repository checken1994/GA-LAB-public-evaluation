"""[F-10-2] Regression: get_judge() fast-learning thread is OPT-IN.

The F-10-2 gate lives in scp/api_server_parts/helpers.py get_judge():
(a) SCP_FAST_LEARNING_THREAD unset  -> thread NOT started + visibility line logged;
(b) SCP_FAST_LEARNING_THREAD=1      -> thread start function IS invoked;
(c) the module actually imports ``os`` (the NameError regression: the gate
    referenced os.environ while the module had no ``import os``).

All boot side effects of get_judge() are neutralized via stubs — a REAL
network thread must never start inside tests (the thread-start functions are
monkeypatched with recorders).
"""
from __future__ import annotations

import logging
import os
import sys
import types

import pytest

from scp.api_server_parts import helpers

# helpers.py is a mixin historically exec'd with __name__="scp.api", so its
# module logger is helpers.logger (name "scp.api") — pin to the live object,
# never hardcode the name.
_LOG_NAME = helpers.logger.name


class _StubJudge:
    domain_experts: list = []

    def get_v98_status(self) -> None:
        return None


@pytest.fixture()
def isolated_get_judge(monkeypatch: pytest.MonkeyPatch) -> list:
    """Neutralize every boot side effect of get_judge() so the F-10-2 gate is
    the only real code under test. Returns the shared recorder list."""
    stub_modules: dict[str, types.ModuleType] = {
        "scp.runtime.judge": types.ModuleType("scp.runtime.judge"),
        "scp.prediction.predictive": types.ModuleType("scp.prediction.predictive"),
        "scp.meta.why_engine_parts.whyengine": types.ModuleType("scp.meta.why_engine_parts.whyengine"),
        "scp.interfaces.judge": types.ModuleType("scp.interfaces.judge"),
    }
    stub_modules["scp.runtime.judge"].RealityJudge = _StubJudge
    stub_modules["scp.prediction.predictive"].PredictiveOrchestrator = lambda **kw: object()
    stub_modules["scp.meta.why_engine_parts.whyengine"].WhyEngine = lambda: object()
    stub_modules["scp.interfaces.judge"].set_judge_provider = lambda judge: None
    for name, mod in stub_modules.items():
        monkeypatch.setitem(sys.modules, name, mod)

    class _StubCrawler:
        def __init__(self, *a, **kw) -> None:
            pass

    started: list = []
    monkeypatch.setattr(helpers, "AttackCrawler", _StubCrawler)
    monkeypatch.setattr(helpers, "start_crawl_thread", lambda **kw: started.append("crawler"))
    monkeypatch.setattr(
        helpers,
        "_cross_language_learner",
        type("_CLLStub", (), {"transfer_existing_vietnamese_patterns": staticmethod(list)})(),
    )
    # Never allow a real background thread/IO component to start:
    monkeypatch.setattr(helpers, "_V1043_AVAILABLE", False)
    monkeypatch.setattr(helpers, "_V1044_AVAILABLE", False)
    # Snapshot globals get_judge() mutates so monkeypatch restores them.
    monkeypatch.setattr(helpers, "_judge", None)
    monkeypatch.setattr(helpers, "_predictive_engine", None)
    monkeypatch.setattr(helpers, "_attack_crawler", None)
    return started


def test_helpers_module_imports_os_f10_2_nameerror_regression():
    """(c) The F-10-2 gate reads os.environ — the module must bind ``os``
    (the +1-line ``import os`` fix; without it get_judge() raised NameError)."""
    assert isinstance(helpers.os, types.ModuleType)
    assert helpers.os is os


def test_fast_learning_thread_not_started_by_default_and_visibility_logged(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, isolated_get_judge: list
):
    """(a) SCP_FAST_LEARNING_THREAD unset -> NO thread start + visibility line."""
    monkeypatch.delenv("SCP_FAST_LEARNING_THREAD", raising=False)
    started: list = []
    monkeypatch.setattr(helpers, "start_fast_learning_thread", lambda **kw: started.append(kw))
    monkeypatch.setattr(helpers, "_V1042_AVAILABLE", True)

    with caplog.at_level(logging.INFO, logger=_LOG_NAME):
        judge = helpers.get_judge()

    assert judge is not None
    assert started == [], "fast-learning thread must NOT start when SCP_FAST_LEARNING_THREAD is unset"
    assert "crawler" in isolated_get_judge, "sanity: get_judge boot path actually executed"
    assert "FastLearningEngine NOT started" in caplog.text
    assert "SCP_FAST_LEARNING_THREAD" in caplog.text
    assert "SCP_FAST_LEARNING_THREAD=1" in caplog.text


def test_fast_learning_thread_started_when_opt_in_via_env(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, isolated_get_judge: list
):
    """(b) SCP_FAST_LEARNING_THREAD=1 -> the start function IS invoked (recorder,
    never a real network thread)."""
    monkeypatch.setenv("SCP_FAST_LEARNING_THREAD", "1")
    started: list = []
    monkeypatch.setattr(helpers, "start_fast_learning_thread", lambda **kw: started.append(dict(kw)))
    monkeypatch.setattr(helpers, "_V1042_AVAILABLE", True)

    with caplog.at_level(logging.INFO, logger=_LOG_NAME):
        helpers.get_judge()

    # Expected path derives from the runtime_paths contract (absolute,
    # resolved). Patch start_fast_learning_thread via the same helpers the
    # production code uses so expectation == implementation contract.
    from scp.core.runtime_paths import runtime_data_dir, runtime_path
    assert started == [{
        "scp_db_path": str(runtime_path("SCP_DB_PATH", "v13.db")),
        "data_dir": str(runtime_data_dir()),
    }]
    assert "FastLearningEngine started" in caplog.text


def test_fast_learning_falls_back_to_learning_thread_when_v1042_unavailable(
    monkeypatch: pytest.MonkeyPatch, isolated_get_judge: list
):
    """FA-13 coverage: env opt-in with _V1042_AVAILABLE=False must take the
    documented V104.1 fallback branch (also recorded, never a real thread)."""
    monkeypatch.setenv("SCP_FAST_LEARNING_THREAD", "1")
    monkeypatch.setattr(helpers, "_V1042_AVAILABLE", False)
    fallback_started: list = []
    monkeypatch.setattr(helpers, "start_learning_thread", lambda **kw: fallback_started.append(dict(kw)))

    helpers.get_judge()

    from scp.core.runtime_paths import runtime_data_dir, runtime_path
    assert fallback_started == [{
        "scp_db_path": str(runtime_path("SCP_DB_PATH", "v13.db")),
        "data_dir": str(runtime_data_dir()),
    }]
