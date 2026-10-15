"""Absence-contract pin for F-H1 — scp.meta.logical_auditor deprecation.

The LogicalAuditorEngine module was retired as a historical stub
(EXECUTION_PROTOCOL Phase 1.1): it had zero production callers and carried
F821 residue that would have raised NameError on its only outbound path.
Re-appearance of the executable engine is a violation — this pin fails
closed if the engine symbols come back without a new architectural decision.
"""
from __future__ import annotations

import importlib


def test_logical_auditor_module_is_retired_stub():
    import scp.meta.logical_auditor as mod

    docstring = (mod.__doc__ or "").strip()
    assert docstring.startswith("HISTORICAL"), (
        "scp.meta.logical_auditor must carry the HISTORICAL retirement marker"
    )
    # The executable engine surface must be gone (re-appearance = violation).
    for symbol in (
        "LogicalAuditorEngine",
        "LogicalIssue",
        "LogicalAuditResult",
        "LOGICAL_AUDITOR_PROMPT",
    ):
        assert not hasattr(mod, symbol), (
            f"retired symbol {symbol} re-appeared in scp.meta.logical_auditor"
        )


def test_logical_auditor_egress_registration_removed():
    """The retired module must no longer be registered as an LLM egress path."""
    import yaml

    with open("spec/llm_outbound_paths.yaml", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)

    registered = [entry["path"] for entry in spec["paths"]]
    assert "scp/meta/logical_auditor.py" not in registered, (
        "retired stub must not be registered as a production LLM egress path"
    )


def test_no_module_in_tree_imports_logical_auditor_symbols():
    """Tầng 2 guarantee: no dangling imports of the retired symbols."""
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable, "-m", "rg", "--type", "py", "-l",
            "LogicalAuditorEngine|from scp.meta.logical_auditor import|from scp.meta import logical_auditor",
            "scp/", "tests/", "scripts/", "tools/",
        ],
        capture_output=True, text=True, cwd=".",
    )
    assert result.returncode in (0, 1), f"rg failed: {result.stderr}"
    assert result.stdout.strip() == "", (
        f"dangling references to the retired engine: {result.stdout}"
    )
