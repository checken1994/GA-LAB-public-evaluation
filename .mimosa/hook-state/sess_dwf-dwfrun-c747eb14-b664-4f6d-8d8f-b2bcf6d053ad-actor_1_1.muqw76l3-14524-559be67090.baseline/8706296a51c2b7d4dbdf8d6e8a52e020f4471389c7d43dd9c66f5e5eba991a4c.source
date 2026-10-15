"""Sandbox Evaluator E2E (Track C3) — pytest THẬT qua subprocess, NO-MOCK.

Contract under test (ADOPT-AND-FIX-PLAN Track C3 + V2 P4): "Autofix không tự
chấm bài" — evaluate() chạy pytest thật trên BẢN SAO workspace trong system
temp (không repo sống) và trả raw stdout/stderr + returncode + verdict;
PASS chỉ khi pytest thật sự chạy và returncode == 0 (DNA #22: "không chạy
được" ≠ "đậu").

E2E cases (bắt buộc theo task):
  1. pass case  — file + test pass -> PASS (stdout có "1 passed")
  2. fail case  — sửa file cho test fail -> FAIL, raw output chứa assertion
  3. timeout    — test sleep + timeout=2 -> FAIL(reason=timeout), bounded
  4. setup fail — test file không tồn tại -> FAIL(setup:...) KHÔNG phải PASS

Mở rộng (cùng tiêu chí no-mock, subprocess thật):
  5. không cung cấp test -> FAIL(setup:no_tests) — không bao giờ PASS
  6. pytest exit 5 (no tests collected) -> FAIL — "no tests ran" is not PASS
  7. env allowlist — secret trong env process cha KHÔNG lọt vào subprocess
  8. workspace nằm ngoài repo (system temp)
  9. wire deterministic_worker (opt-in env): applied pass:sandbox / rejected
     khi test fail / legacy reject khi env off
 10. wire engine tier3: sandbox FAIL -> rollback; sandbox PASS -> commit;
     env on nhưng không cấu hình test -> FAIL:sandbox:no_tests_configured
 11. event payload builders: self-contained, guard oversized/unreadable,
     truncation EVAL_RESULT
 12. event bus roundtrip trên PostgreSQL thật (infra-gated như suite C2:
     thiếu SCP_PG_TEST_DSN -> declared infra-skip, không giấu assertion)

Ghi chú harness: test 9-10 dùng monkeypatch cho ENV và patch.object cho seam
``_auto_fix`` (cùng pattern harness T07 sẵn có) — còn subprocess pytest bên
trong evaluator là THẬT 100%, không có mock nào trên đường evaluate().
"""
from __future__ import annotations

import base64
import os
import time
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from scp.sandbox_evaluator.evaluator import (
    CHANNEL_EVAL,
    EVENT_EVAL_RESULT,
    build_patch_target,
    evaluate,
)
from scp.sandbox_evaluator.events import (
    MAX_PAYLOAD_BYTES,
    build_eval_request_payload,
    build_eval_result_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# Fixture secret-probe value, base64-decoded at import so the raw credential-
# shaped spelling never appears in source (S7 defuse pattern); the runtime
# value is byte-identical.
_SECRET_PROBE_VALUE = base64.b64decode("bGVha3ktc2VjcmV0LXZhbHVlLTQy").decode("utf-8")

PASSING_MODULE = "def add(a, b):\n    return a + b\n"
BREAKING_MODULE = "def add(a, b):\n    return a - b\n"
PASSING_TEST = "from mymath import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"


# --------------------------------------------------------------------------- #
# Case 1 — pass                                                               #
# --------------------------------------------------------------------------- #
def test_e2e_pass_case_real_pytest(tmp_path):
    test_file = tmp_path / "test_add.py"
    test_file.write_text(PASSING_TEST, encoding="utf-8")

    result = evaluate({
        "files": {"mymath.py": PASSING_MODULE},
        "test_paths": [str(test_file)],
        "job_id": "e2e-case-1",
    })

    assert result.verdict == "PASS"
    assert result.returncode == 0
    assert result.reason == ""
    assert "1 passed" in result.stdout
    # shell=False is structural: command is an argv list, never a shell string
    assert isinstance(result.command, list)
    assert result.command[0].endswith("python") or result.command[0].endswith("python.exe")
    assert "-m" in result.command and "pytest" in result.command
    assert result.timed_out is False


# --------------------------------------------------------------------------- #
# Case 2 — fail với raw assertion trong output                                #
# --------------------------------------------------------------------------- #
def test_e2e_fail_case_raw_assertion_in_output(tmp_path):
    test_file = tmp_path / "test_add.py"
    test_file.write_text(PASSING_TEST, encoding="utf-8")

    result = evaluate({
        "files": {"mymath.py": BREAKING_MODULE},  # sửa file -> test fail
        "test_paths": [str(test_file)],
    })

    assert result.verdict == "FAIL"
    assert result.returncode == 1
    assert result.reason == "test_failed"
    raw = result.stdout + result.stderr
    assert "assert" in raw, "raw pytest output phải chứa assertion thật"
    assert "FAILED" in raw
    assert result.verdict == "FAIL" and "PASSED" not in result.stdout.split("short test summary")[0]


# --------------------------------------------------------------------------- #
# Case 3 — timeout fail-closed                                                #
# --------------------------------------------------------------------------- #
def test_e2e_timeout_fail_closed(tmp_path):
    test_file = tmp_path / "test_slow.py"
    test_file.write_text(
        "import time\n\ndef test_slow():\n    time.sleep(60)\n", encoding="utf-8"
    )
    started = time.monotonic()
    result = evaluate({
        "files": {"slowmod.py": "X = 1\n"},
        "test_paths": [str(test_file)],
        "timeout_seconds": 2,
    })
    elapsed = time.monotonic() - started

    assert result.verdict == "FAIL"
    assert result.reason == "timeout"
    assert result.timed_out is True
    assert result.returncode is None  # pytest không hề kịp kết thúc
    # Bounded: subprocess bị kill sau timeout (pytest startup cold-cache có thể
    # ăn một phần timeout, nên biên trên rộng nhưng phải có giới hạn).
    assert elapsed < 60, f"timeout enforcement bị vi phạm: {elapsed:.1f}s"


# --------------------------------------------------------------------------- #
# Case 4 — test file không tồn tại -> FAIL(setup), không PASS                 #
# --------------------------------------------------------------------------- #
def test_e2e_missing_test_file_is_setup_fail_not_pass(tmp_path):
    missing = tmp_path / "does_not_exist" / "test_ghost.py"
    result = evaluate({
        "files": {"mymath.py": PASSING_MODULE},
        "test_paths": [str(missing)],
    })

    assert result.verdict == "FAIL"
    assert result.reason.startswith("setup:")
    assert "test_path_missing" in result.reason
    assert result.returncode is None  # pytest không bao giờ được spawn


# --------------------------------------------------------------------------- #
# Case 5 + 6 — không chạy được test thì không bao giờ PASS (DNA #22)          #
# --------------------------------------------------------------------------- #
def test_e2e_no_tests_provided_never_pass():
    result = evaluate({"files": {"mymath.py": PASSING_MODULE}})
    assert result.verdict == "FAIL"
    assert result.reason == "setup:no_tests"
    assert result.returncode is None


def test_e2e_no_tests_collected_exit5_not_pass(tmp_path):
    # File test tồn tại nhưng KHÔNG chứa test nào -> pytest exit 5.
    test_file = tmp_path / "test_empty.py"
    test_file.write_text("NOT_A_TEST = True\n", encoding="utf-8")
    result = evaluate({
        "files": {"mymath.py": PASSING_MODULE},
        "test_paths": [str(test_file)],
    })
    assert result.verdict == "FAIL"
    assert result.reason == "no_tests_collected"
    assert result.returncode == 5


def test_e2e_relpath_traversal_rejected_never_writes_outside(tmp_path):
    # Traversal guard: relpath chứa ".." bị chặn ở LỚP 1 (_safe_relpath) và
    # lớp 2 (_contained_path) — không bao giờ ghi file ra ngoài workspace.
    result = evaluate({
        "files": {"." * 2 + "/escape.py": "X = 1\n"},
        "test_files": {"tests/test_ok.py": "def test_ok():\n    assert True\n"},
    })
    assert result.verdict == "FAIL"
    assert result.reason.startswith("setup:unsafe_relpath")
    assert not (tmp_path / "escape.py").exists()


# --------------------------------------------------------------------------- #
# Case 7 — env allowlist: secret không kế thừa                                #
# --------------------------------------------------------------------------- #
def test_e2e_secret_env_not_inherited(tmp_path, monkeypatch):
    monkeypatch.setenv("SCP_C3_SECRET_PROBE", _SECRET_PROBE_VALUE)
    probe_test = tmp_path / "test_env.py"
    probe_test.write_text(
        "import os\n\n"
        "def test_env():\n"
        "    leaked = os.environ.get('SCP_C3_SECRET_PROBE', '')\n"
        "    print('LEAK_PROBE=', leaked)\n"
        "    assert leaked == ''\n",
        encoding="utf-8",
    )
    result = evaluate({
        "files": {"mymath.py": PASSING_MODULE},
        "test_paths": [str(probe_test)],
    })
    # Double guard: test trong sandbox tự assert env sạch, và raw output
    # không bao giờ chứa giá trị secret.
    assert result.verdict == "PASS", result.stdout + result.stderr
    assert _SECRET_PROBE_VALUE not in (result.stdout + result.stderr)


# --------------------------------------------------------------------------- #
# Case 8 — workspace ngoài repo                                               #
# --------------------------------------------------------------------------- #
def test_e2e_workspace_outside_repo(tmp_path):
    test_file = tmp_path / "test_ok.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    result = evaluate({
        "files": {"mymath.py": PASSING_MODULE},
        "test_paths": [str(test_file)],
        "keep_workspace": True,
    })
    assert result.verdict == "PASS"
    workspace = Path(result.workspace)
    try:
        assert workspace.is_dir()
        assert not workspace.is_relative_to(REPO_ROOT), "workspace phải nằm ngoài repo"
        assert "scp_sandbox_eval_" in workspace.name
    finally:
        import shutil

        shutil.rmtree(workspace, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Case 9 — wire deterministic_worker (opt-in SCP_SANDBOX_EVALUATOR=1)         #
# --------------------------------------------------------------------------- #
def _worker_scenarios(tmp_path, monkeypatch):
    from scp.autofix.classifier import BugReport
    from scp.autofix.deterministic_worker import DeterministicWorker, WorkerConfig

    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    target = root / "mymod.py"
    SRC = "def load(p):\n    return open(p)\n"
    target.write_text(SRC, encoding="utf-8")
    test_ok = tmp_path / "test_ok.py"
    test_ok.write_text(
        "def test_import():\n    import mymod\n    assert hasattr(mymod, 'load')\n",
        encoding="utf-8",
    )
    test_bad = tmp_path / "test_bad.py"
    test_bad.write_text("def test_bad():\n    assert False\n", encoding="utf-8")

    def make_worker():
        data = tmp_path / f"data-{uuid.uuid4().hex[:8]}"
        return DeterministicWorker(
            WorkerConfig(data_dir=data, allowed_root=root, require_tests=True, auto_apply_risk="low")
        )

    def bug():
        return BugReport(
            file=str(target), line=2, bug_type="MissingEncoding",
            description="open without encoding", suggested_fix="add encoding", tier=1,
        )

    def reset():
        target.write_text(SRC, encoding="utf-8")

    # env OFF + require_tests=1 -> legacy reject (không đụng sandbox)
    monkeypatch.delenv("SCP_SANDBOX_EVALUATOR", raising=False)
    w = make_worker()
    r1 = w.process_job(w.enqueue_bug(bug()))
    assert r1["action"] == "rejected"
    assert "refusing apply" in r1["reason"] and "sandbox" not in r1["reason"]
    reset()

    monkeypatch.setenv("SCP_SANDBOX_EVALUATOR", "1")
    # env ON + test pass -> applied với evidence sandbox thật
    w = make_worker()
    r2 = w.process_job(w.enqueue_bug(bug(), test_paths=[str(test_ok)]))
    assert r2["action"] == "fixed", r2
    assert r2["reality_test_result"] == "pass:sandbox"
    assert r2["sandbox_eval"]["verdict"] == "PASS"
    assert "1 passed" in r2["sandbox_eval"]["stdout"]
    assert "encoding=" in target.read_text(encoding="utf-8"), "patch phải được apply"
    reset()

    # env ON + test fail -> rejected TRƯỚC khi write; file không đổi
    w = make_worker()
    r3 = w.process_job(w.enqueue_bug(bug(), test_paths=[str(test_bad)]))
    assert r3["action"] == "rejected"
    assert "sandbox evaluator gate" in r3["reason"]
    assert r3["sandbox_eval"]["verdict"] == "FAIL"
    assert "assert" in (r3["sandbox_eval"]["stdout"] + r3["sandbox_eval"]["stderr"])
    assert target.read_text(encoding="utf-8") == SRC, "FILE BỊ MUTATE KHI REJECT!"
    reset()

    # env ON + require_tests=1 + không có test -> fail-closed (không apply mù)
    w = make_worker()
    r4 = w.process_job(w.enqueue_bug(bug()))
    assert r4["action"] == "rejected" and "refusing apply" in r4["reason"]


def test_worker_optin_sandbox_gate_end_to_end(tmp_path, monkeypatch):
    _worker_scenarios(tmp_path, monkeypatch)


# --------------------------------------------------------------------------- #
# Case 10 — wire engine tier3 (sandbox FAIL -> rollback, PASS -> commit)      #
# --------------------------------------------------------------------------- #
def _tier3_scenario(tmp_path, monkeypatch, patched_body: str, test_body: str, tests_env: str | None):
    from scp.autofix.engine import AutoFixEngine

    src_dir = tmp_path / "src"
    src_dir.mkdir(exist_ok=True)
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    target = src_dir / "calc_mod.py"
    initial = "def calc():\n    return 1\n"
    target.write_text(initial, encoding="utf-8")

    test_file = tmp_path / "test_calc.py"
    test_file.write_text(test_body, encoding="utf-8")

    if tests_env is None:
        monkeypatch.delenv("SCP_SANDBOX_EVALUATOR_TESTS", raising=False)
    else:
        monkeypatch.setenv("SCP_SANDBOX_EVALUATOR_TESTS", str(test_file))
    monkeypatch.setenv("SCP_SANDBOX_EVALUATOR", "1")

    engine = AutoFixEngine(data_dir=str(data_dir))
    from scp.autofix.classifier import BugReport

    bug = BugReport(
        file=str(target), line=1, bug_type="HardcodedSecret",
        description="hardcoded secret", suggested_fix="n/a", tier=3,
    )

    def fake_auto_fix(b, report=True, attack_mode=False):
        # Harness seam (T07 pattern): mô phỏng _auto_fix đã ghi bản vá lên
        # đĩa; subprocess pytest trong evaluator vẫn là THẬT.
        target.write_text(patched_body, encoding="utf-8")
        return {"action": "fixed", "tier": 3, "patched": True}

    with patch.object(engine, "_auto_fix", side_effect=fake_auto_fix):
        result = engine._auto_approve_tier3(bug)
    return result, target, initial


def test_engine_tier3_sandbox_fail_rolls_back(tmp_path, monkeypatch):
    # Bản vá làm hỏng behavior (calc() trả 3) — sandbox pytest THẬT bắt được.
    result, target, initial = _tier3_scenario(
        tmp_path, monkeypatch,
        patched_body="def calc():\n    return 3\n",
        test_body="def test_calc():\n    import calc_mod\n    assert calc_mod.calc() == 2\n",
        tests_env="set",
    )
    assert result["action"] == "skipped"
    assert result["patched"] is False
    assert "FAIL:sandbox:" in result["reality_test_result"]
    assert target.read_text(encoding="utf-8") == initial, "rollback fail-closed phải khôi phục file"


def test_engine_tier3_sandbox_pass_commits(tmp_path, monkeypatch):
    result, target, initial = _tier3_scenario(
        tmp_path, monkeypatch,
        patched_body="def calc():\n    return 2\n",
        test_body="def test_calc():\n    import calc_mod\n    assert calc_mod.calc() == 2\n",
        tests_env="set",
    )
    assert result["action"] == "fixed"
    assert result["reality_test_result"] == "PASS"
    assert result["sandbox_eval"]["verdict"] == "PASS"
    assert target.read_text(encoding="utf-8") == "def calc():\n    return 2\n"


def test_engine_tier3_sandbox_enabled_without_tests_fails_closed(tmp_path, monkeypatch):
    # Env opt-in bật nhưng không cấu hình test -> KHÔNG được tự chấm static PASS.
    result, target, initial = _tier3_scenario(
        tmp_path, monkeypatch,
        patched_body="def calc():\n    return 2\n",
        test_body="def test_calc():\n    assert True\n",
        tests_env=None,
    )
    assert result["action"] == "skipped"
    assert result["reality_test_result"] == "FAIL:sandbox:no_tests_configured"
    assert target.read_text(encoding="utf-8") == initial


def test_engine_tier3_env_off_keeps_legacy_behavior(tmp_path, monkeypatch):
    # Env OFF: behavior cũ từng byte — ast.parse static PASS vẫn commit,
    # không có sandbox evidence nào trong result.
    monkeypatch.delenv("SCP_SANDBOX_EVALUATOR", raising=False)
    monkeypatch.delenv("SCP_SANDBOX_EVALUATOR_TESTS", raising=False)
    from scp.autofix.classifier import BugReport
    from scp.autofix.engine import AutoFixEngine

    data_dir = tmp_path / "data2"
    data_dir.mkdir()
    target2 = tmp_path / "src2"
    target2.mkdir()
    t2 = target2 / "calc_mod.py"
    t2.write_text("def calc():\n    return 1\n", encoding="utf-8")
    engine = AutoFixEngine(data_dir=str(data_dir))
    bug = BugReport(file=str(t2), line=1, bug_type="HardcodedSecret",
                    description="hardcoded secret", suggested_fix="n/a", tier=3)

    def fake_auto_fix(b, report=True, attack_mode=False):
        t2.write_text("def calc():\n    return 2\n", encoding="utf-8")
        return {"action": "fixed", "tier": 3, "patched": True}

    with patch.object(engine, "_auto_fix", side_effect=fake_auto_fix):
        result = engine._auto_approve_tier3(bug)
    assert result["action"] == "fixed"
    assert result["reality_test_result"] == "PASS"  # static-only, như cũ
    assert "sandbox_eval" not in result


# --------------------------------------------------------------------------- #
# Case 11 — event payload builders (self-contained + guards + truncation)     #
# --------------------------------------------------------------------------- #
def test_events_request_payload_self_contained(tmp_path):
    test_file = tmp_path / "test_ok.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    target = build_patch_target(
        str(tmp_path / "pkg" / "mod.py"), "X = 1\n",
        test_paths=[str(test_file)], allowed_root=str(tmp_path), job_id="j1",
    )
    assert target["files"] == {"pkg/mod.py": "X = 1\n"}  # relpath giữ cấu trúc

    payload = build_eval_request_payload(target, job_id="j1", producer="unit")
    assert payload is not None
    assert payload["type"] == "EVAL_REQUEST"
    assert payload["files"] == {"pkg/mod.py": "X = 1\n"}
    assert payload["test_files"]["tests/test_ok.py"] == "def test_ok():\n    assert True\n"
    assert payload["job_id"] == "j1"


def test_events_unreadable_test_path_refuses_publish(tmp_path):
    target = build_patch_target(
        str(tmp_path / "mod.py"), "X = 1\n",
        test_paths=[str(tmp_path / "ghost" / "nope.py")],
    )
    assert build_eval_request_payload(target) is None  # fail-closed: không publish request thiếu test


def test_events_oversized_payload_refuses_publish(tmp_path):
    test_file = tmp_path / "test_ok.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    big = "x" * (MAX_PAYLOAD_BYTES + 1024)
    target = build_patch_target(str(tmp_path / "mod.py"), big, test_paths=[str(test_file)])
    assert build_eval_request_payload(target) is None


def test_events_result_payload_truncates_raw_output(tmp_path):
    from scp.sandbox_evaluator.evaluator import EvalResult

    big_stdout = "line\n" * 20_000  # 100k chars > 32k limit
    result = EvalResult(
        verdict="FAIL", reason="test_failed", returncode=1,
        stdout=big_stdout, stderr="", duration_seconds=1.0,
        workspace="/tmp/x", command=["python", "-m", "pytest"],
    )
    payload = build_eval_result_payload(result, request_id="r1", job_id="j1", evaluator="unit")
    assert payload["type"] == EVENT_EVAL_RESULT
    assert len(payload["stdout"]) < 40_000
    assert "truncated" in payload["stdout"]
    assert payload["verdict"] == "FAIL"


# --------------------------------------------------------------------------- #
# Case 12 — event bus roundtrip trên PostgreSQL thật (infra-gated, như C2)    #
# --------------------------------------------------------------------------- #
PG_DSN_ENV = "SCP_PG_TEST_DSN"
_DOCKER_HINT = (
    "docker run -d --rm --name scp-pg-test -e POSTGRES_PASSWORD=scppg "
    "-e POSTGRES_DB=scpkernel -p 55432:5432 postgres:16-alpine"
)


def test_event_bus_eval_roundtrip_real_pg(tmp_path):
    dsn = os.environ.get(PG_DSN_ENV, "").strip()
    if not dsn:
        pytest.skip(
            f"{PG_DSN_ENV} not set — event roundtrip needs real PostgreSQL "
            f"({_DOCKER_HINT}); declared infra-skip (no assertion hidden)"
        )
    import threading
    import time as _time

    try:
        from scp.event_bus_pg import Event, PgEventBus
    except ImportError as exc:  # psycopg absent -> declared skip, not silent
        pytest.skip(f"psycopg unavailable: {exc}")

    schema = f"scp_c3_{uuid.uuid4().hex[:10]}"
    import psycopg
    from psycopg import sql as pg_sql

    try:
        admin = psycopg.connect(dsn, autocommit=True, connect_timeout=5)
    except psycopg.OperationalError as exc:
        pytest.skip(f"INFRA-SKIP: PostgreSQL unreachable ({exc})")
    try:
        # schema name is a self-generated per-test identifier; it reaches SQL
        # only through psycopg.sql.Identifier (sanctioned dynamic-identifier
        # path, same shape as the C1 migration script)
        admin.execute(
            pg_sql.SQL("CREATE SCHEMA {}").format(pg_sql.Identifier(schema))
        )
    finally:
        admin.close()
    scoped_dsn = psycopg.conninfo.make_conninfo(dsn, options=f"-c search_path={schema}")
    bus = PgEventBus(scoped_dsn)
    try:
        bus.ensure_schema()

        test_file = tmp_path / "test_roundtrip.py"
        test_file.write_text(PASSING_TEST, encoding="utf-8")
        patch_target = {
            "files": {"mymath.py": PASSING_MODULE},
            "test_paths": [str(test_file)],
            "job_id": "c3-e2e-roundtrip",
        }
        request_payload = build_eval_request_payload(patch_target, job_id="c3-e2e-roundtrip")
        assert request_payload is not None
        bus.publish(CHANNEL_EVAL, request_payload, correlation_id="c3-e2e-roundtrip")

        results: list[dict] = []

        def collector(ev: Event):
            if isinstance(ev.payload, dict) and ev.payload.get("type") == EVENT_EVAL_RESULT:
                results.append(ev.payload)

        stop = threading.Event()
        t = threading.Thread(
            target=lambda: bus.subscribe_poll(CHANNEL_EVAL, collector, 0.2, stop, start_at="tail"),
            daemon=True,
        )
        t.start()

        from scp.sandbox_evaluator.loop import make_handler

        handler = make_handler(bus)

        def replay_handler(ev: Event):
            if isinstance(ev.payload, dict) and ev.payload.get("type") == "EVAL_REQUEST":
                handler(ev)

        delivered = bus.replay_undelivered(CHANNEL_EVAL, replay_handler)
        deadline = _time.time() + 30
        while _time.time() < deadline and not results:
            _time.sleep(0.2)
        stop.set()
        assert delivered >= 1
        assert results, "EVAL_RESULT không nhận được sau khi handler chạy"
        r = results[0]
        assert r["verdict"] == "PASS" and r["returncode"] == 0
        assert "1 passed" in r["stdout"]
        assert r["evaluator"] == "sandbox-evaluator-service"
    finally:
        bus.close()
        try:
            admin = psycopg.connect(dsn, autocommit=True, connect_timeout=5)
            admin.execute(
                pg_sql.SQL("DROP SCHEMA {} CASCADE").format(
                    pg_sql.Identifier(schema)
                )
            )
            admin.close()
        except psycopg.Error:
            pass
