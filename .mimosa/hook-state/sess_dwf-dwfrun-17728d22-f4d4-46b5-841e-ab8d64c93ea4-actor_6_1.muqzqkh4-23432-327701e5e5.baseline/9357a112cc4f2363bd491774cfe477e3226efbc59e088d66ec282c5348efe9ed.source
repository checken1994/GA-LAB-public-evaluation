"""Acceptance must be hermetic and must never overwrite evidence."""
from __future__ import annotations

import json
import secrets
from pathlib import Path

import pytest

from scripts import run_scp_acceptance as acceptance


def _parent_sentinel(tag: str) -> str:
    """Runtime-assembled canary value.

    No credential-shaped literal may sit in source (Mimosa HIGH); the value is
    only used to prove the child environment never inherits parent secrets, so
    a random per-run value is equivalent. Mirrors the SECRET precedent in
    tests/T02_contract/test_llm_bridge_cache_auth.py.
    """
    return f"parent-{tag}-" + secrets.token_hex(8)


def test_runtime_environment_never_inherits_parent_credentials(tmp_path, monkeypatch):
    sentinels = {
        "OPENROUTER_API_KEY": _parent_sentinel("openrouter"),
        "OPENAI_API_KEY": _parent_sentinel("openai"),
        "SCP_CAPABILITY_SECRET": _parent_sentinel("capability"),
        "SCP_PG_TEST_DSN": _parent_sentinel("pg"),
        "HTTPS_PROXY": _parent_sentinel("proxy"),
    }
    monkeypatch.setattr(acceptance.os, "environ", dict(sentinels))
    runtime = acceptance.RuntimeHarness(tmp_path, 18180, 18181)
    child = runtime.environment()
    assert not ({value for value in sentinels.values()}.intersection(child.values()))
    assert child["SCP_EGRESS_MODE"] == "deny"
    assert child["SCP_SKIP_STARTUP_GATE"] == "0"
    assert Path(child["SCP_TRACE_STORE_PATH"]).is_relative_to(tmp_path)
    assert child["SCP_LLM_FALLBACK_PROVIDERS"] == acceptance.LOCAL_FALLBACK_SPEC


def test_acceptance_refuses_existing_evidence_before_overwriting(tmp_path):
    sentinel = tmp_path / "existing-evidence.txt"
    sentinel.write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError):
        acceptance.AcceptanceSuite(tmp_path, 18180, 18181, 2)
    assert sentinel.read_text(encoding="utf-8") == "preserve"


def test_incomplete_acceptance_report_never_claims_pass(tmp_path):
    suite = acceptance.AcceptanceSuite(tmp_path, 18180, 18181, 2)
    suite.scenarios.append({"id": "SCP-A01", "passed": True})
    suite._write_report(final=True)
    report = json.loads(suite.report_path.read_text(encoding="utf-8"))
    assert report["overall_pass"] is False
