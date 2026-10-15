"""T00-integrity tests for the stale-code tripwire (T00-extension, S25 2026).

Hermetic: every test builds a throwaway tmp tree (scp/ package + optional
data/governance/) and runs the tool against that tree — the real repository
is never modified and no scp module is imported into this test process.

Covered cases (task contract a-f plus two fail-closed guards):
  (a) import of a non-existent class  -> check 2 FAIL
  (b) blueprint module missing        -> check 1 FAIL
  (c) identical prompt template in 2 files -> check 3 FAIL
  (d) clean tree                      -> PASS (no FAIL findings)
  (e) baseline file absent            -> baseline created, first run PASS
  (f) silent-except count above baseline +5% -> check 4 FAIL
  (g) dynamic provider (module-level __getattr__) -> SKIP, never false FAIL
  (h) t00 delta mode: known findings tracked as debt, NEW finding fails
"""
import importlib.util
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = PROJECT_ROOT / "tools" / "stale_code_tripwire.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("stale_code_tripwire_test_sut", TOOL_PATH)
    mod = importlib.util.module_from_spec(spec)
    # Must register before exec: @dataclass resolves annotations via
    # sys.modules[cls.__module__]; unregistered modules crash the dataclass
    # decorator (caught here by these tests, per T00 fail-closed discipline).
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_tree(tmp_path: Path) -> Path:
    (tmp_path / "scp").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scp" / "__init__.py").write_text("", encoding="utf-8")
    return tmp_path


def _write(root: Path, relpath: str, content: str) -> None:
    target = root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


SCV = "scp/"  # readability in _write calls


def test_a_unresolved_import_is_caught(tmp_path):
    tool = _load_tool()
    root = _make_tree(tmp_path)
    _write(root, "scp/lib.py", "class Real:\n    pass\n\n\ndef ok():\n    return 1\n")
    _write(root, "scp/app.py", "from scp.lib import Missing\n\n\ndef run():\n    return Missing()\n")
    report = tool.run_all(root, baseline_path=root / "baseline.json",
                          blueprint_modules=())
    kinds = [f.kind for f in report.fails]
    assert "unresolved_import" in kinds
    finding = next(f for f in report.fails if f.kind == "unresolved_import")
    assert finding.file == "scp/app.py"
    assert "Missing" in finding.detail


def test_b_missing_blueprint_module_fails(tmp_path):
    tool = _load_tool()
    root = _make_tree(tmp_path)
    _write(root, "scp/present.py", "VALUE = 1\n")
    report = tool.run_all(root, baseline_path=root / "baseline.json",
                          blueprint_modules=("scp.ghost_module", "scp.present"))
    kinds = [f.kind for f in report.fails]
    assert "blueprint_missing" in kinds
    ghost = next(f for f in report.fails if f.kind == "blueprint_missing")
    assert "scp.ghost_module" in ghost.detail
    assert not any("scp.present" in f.detail for f in report.fails
                   if f.kind == "blueprint_missing")


def test_c_duplicate_prompt_template_fails(tmp_path):
    tool = _load_tool()
    root = _make_tree(tmp_path)
    judge_body = (
        "def build(q, c, a):\n"
        "    return (\n"
        "        f\"Question: {q}\\nContext: {c}\\nAI Answer: {a}\\n\"\n"
        "        \"Evaluate if the AI Answer correctly answers the Question based ONLY on \"\n"
        "        \"the Context (if provided) or general knowledge. Output only PASS or FAIL.\"\n"
        "    )\n"
    )
    _write(root, "scp/judge_one.py", judge_body)
    _write(root, "scp/judge_two.py", judge_body)
    report = tool.run_all(root, baseline_path=root / "baseline.json",
                          blueprint_modules=())
    dup = [f for f in report.fails if f.kind == "duplicate_prompt_template"]
    assert len(dup) == 1
    assert "2 files" in dup[0].detail
    assert "scp/judge_one.py" in dup[0].detail and "scp/judge_two.py" in dup[0].detail


def test_d_clean_tree_passes(tmp_path):
    tool = _load_tool()
    root = _make_tree(tmp_path)
    _write(root, "scp/lib.py", "class Real:\n    def helper(self):\n"
                               "        for i in range(10):\n            i += 1\n"
                               "        return i\n")
    _write(root, "scp/app.py", "from scp.lib import Real\n\n\ndef run():\n    return Real()\n")
    report = tool.run_all(root, baseline_path=root / "baseline.json",
                          blueprint_modules=("scp.lib",))
    assert report.fails == []
    assert report.baseline_created  # first run on this tmp tree


def test_e_missing_baseline_is_created_and_first_run_passes(tmp_path):
    tool = _load_tool()
    root = _make_tree(tmp_path)
    _write(root, "scp/app.py", "def run():\n    print('once')\n")
    baseline = root / "data" / "governance" / "tripwire_baseline.json"
    report = tool.run_all(root, baseline_path=baseline, blueprint_modules=())
    assert report.fails == []
    assert report.baseline_created
    data = json.loads(baseline.read_text(encoding="utf-8"))
    assert data["metrics"]["print_calls"] == 1
    assert data["metrics"]["silent_except_pass"] == 0
    assert data["git_sha"]
    assert "created_at" in data
    assert data["known_findings"] == []


def test_f_silent_except_drift_above_threshold_fails(tmp_path):
    tool = _load_tool()
    root = _make_tree(tmp_path)
    for i in range(3):
        _write(root, f"scp/mod{i}.py", "def f():\n    try:\n        pass\n    except Exception:\n        pass\n")
    baseline = root / "baseline.json"
    baseline.write_text(json.dumps({
        "schema_version": 1,
        "metrics": {"print_calls": 0, "silent_except_pass": 1},
        "thresholds": {"metric_drift_max_increase_pct": 5},
        "known_findings": [],
    }), encoding="utf-8")
    report = tool.run_all(root, baseline_path=baseline, blueprint_modules=())
    drift = [f for f in report.fails if f.kind == "metric_drift"]
    assert len(drift) == 1
    assert "silent_except_pass" in drift[0].detail


def test_g_dynamic_provider_is_skipped_not_failed(tmp_path):
    tool = _load_tool()
    root = _make_tree(tmp_path)
    _write(root, "scp/dyn.py",
           "def __getattr__(name):\n    raise AttributeError(name)\n")
    _write(root, "scp/app.py", "from scp.dyn import Anything\n\n\ndef run():\n    return 1\n")
    report = tool.run_all(root, baseline_path=root / "baseline.json",
                          blueprint_modules=())
    assert not [f for f in report.fails if f.kind == "unresolved_import"]
    assert any("scp/app.py" in s for s in report.skips)


def test_h_t00_delta_mode_known_debt_vs_new_finding(tmp_path):
    tool = _load_tool()
    root = _make_tree(tmp_path)
    _write(root, "scp/lib.py", "class Real:\n    pass\n")
    _write(root, "scp/old.py", "from scp.lib import Missing\n")
    baseline = root / "baseline.json"

    # First t00 run: finding becomes seeded known debt, no violations.
    violations = tool.run_for_t00(root, baseline_path=baseline)
    assert violations == []
    data = json.loads(baseline.read_text(encoding="utf-8"))
    seeded = {(e["kind"], e["file"], e["detail"]) for e in data["known_findings"]}
    assert any(kind == "unresolved_import" for kind, _f, _d in seeded)

    # Second t00 run, unchanged tree: still only debt.
    assert tool.run_for_t00(root, baseline_path=baseline) == []

    # New broken import appears: delta mode must FAIL on it.
    _write(root, "scp/new.py", "from scp.lib import AlsoMissing\n")
    new_violations = tool.run_for_t00(root, baseline_path=baseline)
    assert len(new_violations) == 1
    assert "scp/new.py" in new_violations[0]
    assert "AlsoMissing" in new_violations[0]


def test_i_t00_wiring_runs_tripwire(tmp_path):
    """The t00 wiring helper must load the tool by file path and fail-closed."""
    tool = _load_tool()
    root = _make_tree(tmp_path)
    violations = tool.run_for_t00(root)
    assert violations == []
    assert (root / "data" / "governance" / "tripwire_baseline.json").exists()


def test_j_metric_drift_within_threshold_passes(tmp_path):
    tool = _load_tool()
    root = _make_tree(tmp_path)
    _write(root, "scp/app.py", "def run():\n    print('a')\n    print('b')\n")
    baseline = root / "baseline.json"
    baseline.write_text(json.dumps({
        "schema_version": 1,
        "metrics": {"print_calls": 100, "silent_except_pass": 0},
        "thresholds": {"metric_drift_max_increase_pct": 5},
        "known_findings": [],
    }), encoding="utf-8")
    report = tool.run_all(root, baseline_path=baseline, blueprint_modules=())
    assert not [f for f in report.fails if f.kind == "metric_drift"]


def test_k_star_import_reexport_resolves(tmp_path):
    """`from pkg import Name` through a star-import facade must NOT fail."""
    tool = _load_tool()
    root = _make_tree(tmp_path)
    _write(root, "scp/inner.py", "class Exported:\n    pass\n")
    _write(root, "scp/facade.py", "from scp.inner import *\n")
    _write(root, "scp/app.py", "from scp.facade import Exported\n")
    report = tool.run_all(root, baseline_path=root / "baseline.json",
                          blueprint_modules=())
    assert not [f for f in report.fails if f.kind == "unresolved_import"]


def test_l_baseline_invalid_is_fail_closed_not_reset(tmp_path):
    tool = _load_tool()
    root = _make_tree(tmp_path)
    _write(root, "scp/app.py", "def run():\n    return 1\n")
    baseline = root / "baseline.json"
    baseline.write_text("{not-json", encoding="utf-8")
    report = tool.run_all(root, baseline_path=baseline, blueprint_modules=())
    assert [f for f in report.fails if f.kind == "baseline_invalid"]
    # The corrupt baseline must NOT be silently overwritten.
    assert baseline.read_text(encoding="utf-8") == "{not-json"


if __name__ == "__main__":
    sys.exit(0)
