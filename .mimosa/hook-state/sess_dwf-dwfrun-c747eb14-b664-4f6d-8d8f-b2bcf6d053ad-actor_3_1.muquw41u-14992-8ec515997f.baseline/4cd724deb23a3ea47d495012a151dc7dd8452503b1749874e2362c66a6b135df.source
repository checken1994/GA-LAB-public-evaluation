"""External behavioral audit for the semantic-judge cascade.

This file intentionally calls production ``scp.runtime.judge_llm._llm_judge``.
It must never be replaced by a filename/presence-only compliance check.
"""
from __future__ import annotations

from scp import llm_gateway
from scp.runtime import judge_llm


class _ScriptedGateway:
    def __init__(self, scripted: list[object]):
        self.scripted = list(scripted)
        self.calls: list[str] = []

    def chat_sync(self, _prompt: str, system_prompt: str = "", task: str = "default"):
        assert system_prompt == judge_llm._JUDGE_SYSTEM
        self.calls.append(task)
        if not self.scripted:
            raise AssertionError("gateway called more times than expected")
        item = self.scripted.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item, f"provider:{task}"


def _install(monkeypatch, *scripted: object) -> _ScriptedGateway:
    gateway = _ScriptedGateway(list(scripted))
    monkeypatch.setattr(llm_gateway, "get_gateway", lambda: gateway)
    return gateway


def test_primary_pass_short_circuits_second_opinion(monkeypatch):
    gateway = _install(monkeypatch, "PASS")
    assert judge_llm._llm_judge("q", "a", "ctx") is True
    assert gateway.calls == ["judge"]


def test_primary_ambiguous_escalates_without_guessing(monkeypatch):
    gateway = _install(monkeypatch, "I am not sure")
    assert judge_llm._llm_judge("q", "a", "ctx") is None
    assert gateway.calls == ["judge"]


def test_disagreement_escalates(monkeypatch):
    gateway = _install(monkeypatch, "FAIL", "PASS")
    assert judge_llm._llm_judge("q", "a", "ctx") is None
    assert gateway.calls == ["judge", "autofix"]


def test_double_fail_is_required_for_negative_verdict(monkeypatch):
    gateway = _install(monkeypatch, "FAIL", "FAIL")
    assert judge_llm._llm_judge("q", "a", "ctx") is False
    assert gateway.calls == ["judge", "autofix"]


def test_gateway_failure_is_unknown_not_pass(monkeypatch):
    gateway = _install(monkeypatch, RuntimeError("provider unavailable"))
    assert judge_llm._llm_judge("q", "a", "ctx") is None
    assert gateway.calls == ["judge"]
