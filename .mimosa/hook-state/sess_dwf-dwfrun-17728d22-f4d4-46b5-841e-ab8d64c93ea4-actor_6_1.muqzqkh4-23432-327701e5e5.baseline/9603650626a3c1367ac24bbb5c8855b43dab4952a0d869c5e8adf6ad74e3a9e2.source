from __future__ import annotations

from pathlib import Path

import pytest

from scripts.mutation_engine import MutationRunError, run_mutation_campaign


def _write_project(root: Path, *, passing: bool = True) -> tuple[Path, Path]:
    source = root / "sample.py"
    tests = root / "tests" / "test_sample.py"
    tests.parent.mkdir(parents=True)
    source.write_text("def accepts(value):\n    return value >= 18\n", encoding="utf-8")
    expected = "assert accepts(18)" if passing else "assert not accepts(18)"
    tests.write_text(
        "from sample import accepts\n\n"
        f"def test_boundary():\n    {expected}\n",
        encoding="utf-8",
    )
    return source, tests


def test_campaign_kills_mutant_and_restores_source(tmp_path: Path) -> None:
    source, tests = _write_project(tmp_path)
    original = source.read_bytes()

    report = run_mutation_campaign(
        source.name,
        [tests.relative_to(tmp_path)],
        repo_root=tmp_path,
        max_mutants=1,
        timeout_seconds=20,
    )

    assert report.score == 1.0
    assert report.killed == 1
    assert source.read_bytes() == original


def test_campaign_rejects_failing_baseline_and_restores_source(tmp_path: Path) -> None:
    source, tests = _write_project(tmp_path, passing=False)
    original = source.read_bytes()

    with pytest.raises(MutationRunError, match="baseline tests failed"):
        run_mutation_campaign(
            source.name,
            [tests.relative_to(tmp_path)],
            repo_root=tmp_path,
            max_mutants=1,
            timeout_seconds=20,
        )

    assert source.read_bytes() == original


def test_campaign_requires_explicit_existing_tests(tmp_path: Path) -> None:
    source, _ = _write_project(tmp_path)

    with pytest.raises(MutationRunError, match="at least one explicit test"):
        run_mutation_campaign(source.name, [], repo_root=tmp_path)
    with pytest.raises(MutationRunError, match="test does not exist"):
        run_mutation_campaign(source.name, ["tests/missing.py"], repo_root=tmp_path)


def test_campaign_rejects_unknown_function_scope(tmp_path: Path) -> None:
    source, tests = _write_project(tmp_path)

    with pytest.raises(MutationRunError, match="selected functions not found"):
        run_mutation_campaign(
            source.name,
            [tests.relative_to(tmp_path)],
            repo_root=tmp_path,
            include_functions=["missing_function"],
        )
