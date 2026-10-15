"""[F-10] The deep audit boot cycle is env-gated (quota guard).

Default: the immediate boot+60s deep audit run is SKIPPED (it burns real LLM
quota on every server start before anyone asks for anything). The 24h cadence
is unchanged. SCP_DEEP_AUDIT_BOOT_RUN=1 restores the boot run.
"""
from __future__ import annotations

from scp.api_server_parts import lifespan as lifespan_module


def test_default_is_skip_boot_run(monkeypatch):
    monkeypatch.delenv("SCP_DEEP_AUDIT_BOOT_RUN", raising=False)
    assert lifespan_module.deep_audit_boot_run_enabled() is False


def test_explicit_opt_in_restores_boot_run(monkeypatch):
    monkeypatch.setenv("SCP_DEEP_AUDIT_BOOT_RUN", "1")
    assert lifespan_module.deep_audit_boot_run_enabled() is True


def test_other_values_are_falses(monkeypatch):
    for value in ("0", "", "true", "yes", "2"):
        monkeypatch.setenv("SCP_DEEP_AUDIT_BOOT_RUN", value)
        assert lifespan_module.deep_audit_boot_run_enabled() is False, value
