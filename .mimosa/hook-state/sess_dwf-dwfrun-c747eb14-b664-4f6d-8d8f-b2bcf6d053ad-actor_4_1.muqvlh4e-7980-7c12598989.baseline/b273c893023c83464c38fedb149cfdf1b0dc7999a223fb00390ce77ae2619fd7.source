from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTES = ROOT / "scp" / "api" / "routes" / "hands_routes.py"


def test_hands_reconcile_outcome_field_does_not_reject_partial_by_length() -> None:
    tree = ast.parse(ROUTES.read_text(encoding="utf-8"))
    request_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "HandsReconcileRequest"
    )
    outcome = next(
        node
        for node in request_class.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "outcome"
    )
    assert isinstance(outcome.value, ast.Call)
    assert isinstance(outcome.value.func, ast.Name) and outcome.value.func.id == "Field"
    keywords = {item.arg: item.value for item in outcome.value.keywords if item.arg}
    min_length = ast.literal_eval(keywords["min_length"])
    max_length = ast.literal_eval(keywords["max_length"])

    # The canonical target/Skill outcome set includes PARTIAL (7 chars) and
    # NOT_APPLIED (11 chars). Schema length guards must admit both; semantic
    # membership remains fail-closed in TaskKernel.
    assert min_length <= len("PARTIAL")
    assert max_length >= len("NOT_APPLIED")
