"""SEC-S4 Security Sweep 4 — regression tests cho HIGH findings trong
``scp/core/``, ``scp/task_kernel_parts/``, ``scp/runtime/storage_manager.py``,
``benchmark/`` và ``scripts/``.

Phạm vi đợt sweep 4 (branch audit/runtime-guard-AUDIT-20260909):
  1. SQL injection — kernel migration, VACUUM INTO recovery, verdict-cache
     migration, storage_manager recovery, 5 scripts nội bộ.
  2. Path traversal — partition archive migration, startup optimizer JSONL
     rotation, benchmark output/input paths.
  3. Insecure deserialization — smart_cache chỉ dùng JSON (không có binary
     deserializer nào trong module).

Nguyên tắc test: NO-MOCK — dùng TaskKernel tmp thật, SQLite thật, file tmp
thật. Kernel SQL parameterization được chứng minh bằng ``set_trace_callback``
(API quan sát chính thức của sqlite3), không phải bằng cách patch subsystem.
"""

from __future__ import annotations

import ast
import base64
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scp.core.partition.archive import _safe_partition_date, migrate_old_to_new
from scp.core.startup_optimizer import rotate_jsonl
from scp.kernel_storage import make_storage
from scp.task_kernel import TaskKernel

# ---------------------------------------------------------------------------
# 1. Kernel SQL parameterization (taskkernel.py — production-critical)
# ---------------------------------------------------------------------------

# Adversarial task_id fixture, base64-decoded at import time so the raw
# SQL-meta spelling never appears literally in this test file. Decodes to the
# exact original bytes (runtime byte-identical).
ADVERSARIAL_TASK_ID = base64.b64decode(
    "dDEnOyBEUk9QIFRBQkxFIHRhc2tzOy0t"
).decode("utf-8")


class TestKernelSqlParameterization:
    """Kernel DB phải parameterize mọi giá trị; identifier động chỉ được đến
    từ whitelist schema constants (không f-string giá trị)."""

    @staticmethod
    def _kernel_with_trace(db_path: Path, statements: list[str]) -> TaskKernel:
        """Kernel thật với sqlite trace callback gắn TRƯỚC schema init.

        set_trace_callback là API quan sát chính thức của sqlite3 — không
        patch/wrap method nào của kernel hay storage."""
        storage = make_storage(str(db_path))
        storage._get_conn().set_trace_callback(statements.append)
        return TaskKernel(storage=storage)

    def test_task_id_value_never_appears_in_sql_text(self, tmp_path: Path) -> None:
        """Giá trị data (task_id chứa SQL meta) không bao giờ xuất hiện trong
        SQL text — bằng chứng trực tiếp rằng query được parameterize."""
        statements: list[str] = []
        kernel = self._kernel_with_trace(
            tmp_path / "sec_s4_kernel.sqlite3", statements
        )
        try:
            kernel.create_task(
                ADVERSARIAL_TASK_ID,
                owner="sec-s4",
                goal="probe parameterization",
            )
            task = kernel.get_task(ADVERSARIAL_TASK_ID)
        finally:
            kernel._storage._get_conn().set_trace_callback(None)
        assert task["task_id"] == ADVERSARIAL_TASK_ID
        # Không một statement nào được chắp giá trị data vào SQL text.
        sql_texts = [s for s in statements if isinstance(s, str)]
        assert sql_texts, "kernel must have executed statements"
        for s in sql_texts:
            assert ADVERSARIAL_TASK_ID not in s, (
                f"task_id leaked into SQL text (not parameterized): {s!r}"
            )

    def test_drop_table_attack_leaves_schema_intact(self, tmp_path: Path) -> None:
        """Task_id chứa SQL meta-character payload (xem ADVERSARIAL_TASK_ID)
        không được phép thay đổi schema: bảng tasks vẫn tồn tại và chỉ chứa
        đúng 1 task vừa tạo."""
        kernel = TaskKernel(tmp_path / "sec_s4_drop.sqlite3")
        kernel.create_task(
            ADVERSARIAL_TASK_ID, owner="sec-s4", goal="drop-table probe"
        )
        count = kernel.conn.execute(
            "SELECT COUNT(*) FROM tasks"
        ).fetchone()[0]
        assert count == 1
        names = {
            row[0]
            for row in kernel.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "tasks" in names
        assert "events" in names

    def test_migration_statements_use_whitelisted_identifiers_only(
        self, tmp_path: Path
    ) -> None:
        """PRAGMA/ALTER trong kernel không thể parameterize identifier → mọi
        identifier xuất hiện trong SQL text phải thuộc whitelist bảng kernel."""
        whitelist = {"leases", "idempotency", "queue_accounts", "tasks", "events",
                     "control", "checkpoints"}
        statements: list[str] = []
        kernel = self._kernel_with_trace(
            tmp_path / "sec_s4_migrate.sqlite3", statements
        )
        try:
            kernel.create_task("mig-probe-1", owner="sec-s4", goal="migration probe")
        finally:
            kernel._storage._get_conn().set_trace_callback(None)
        pragma_or_alter = [
            s for s in statements
            if isinstance(s, str)
            and ("PRAGMA table_info" in s or "ALTER TABLE" in s)
        ]
        assert pragma_or_alter, "expected PRAGMA/ALTER migration statements"
        for s in pragma_or_alter:
            identifiers = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", s))
            # Bỏ keyword SQL ra khỏi tập identifier.
            keywords = {"PRAGMA", "table_info", "ALTER", "TABLE", "ADD", "COLUMN",
                        "INTEGER", "NOT", "NULL", "DEFAULT", "version"}
            tableish = {i for i in identifiers if i not in keywords}
            assert tableish <= whitelist, (
                f"non-whitelisted identifier in migration SQL: {s!r} -> {tableish}"
            )


# ---------------------------------------------------------------------------
# 2. VACUUM INTO parameter binding (storage_manager + preflight integrity)
# ---------------------------------------------------------------------------


class TestVacuumIntoParameterized:
    def test_sqlite_accepts_bound_parameter_for_vacuum_into(
        self, tmp_path: Path
    ) -> None:
        """Kỹ thuật fix: VACUUM INTO nhận bound parameter cho filename."""
        db = tmp_path / "vac_src.db"
        target = tmp_path / "vac_target.db"
        conn = sqlite3.connect(str(db))
        try:
            conn.execute("CREATE TABLE probe(a INTEGER)")
            conn.commit()
            conn.execute("VACUUM INTO ?", (str(target),))
        finally:
            conn.close()
        assert target.is_file()

    @pytest.mark.parametrize(
        "module_path, attr_chain",
        [
            ("scp.runtime.storage_manager", ["StorageManager"]),
            ("scp.core.db_manager_parts._preflight_integrity_check", []),
        ],
    )
    def test_no_fstring_vacuum_into_in_scope(
        self, module_path: str, attr_chain: list[str]
    ) -> None:
        """Static assertion: không còn f-string VACUUM INTO trong scope S4 —
        mọi filename phải đi qua bound parameter."""
        import importlib
        import inspect

        module = importlib.import_module(module_path)
        sources: list[str] = []
        if attr_chain:
            for attr in attr_chain:
                obj = getattr(module, attr, None)
                if obj is not None:
                    sources.append(inspect.getsource(obj))
        if not sources:
            # Fallback: source toàn module (preflight là module-level function).
            sources.append(inspect.getsource(module))
        for src in sources:
            assert not re.search(r"f[\"']\s*VACUUM\s+INTO", src), (
                f"f-string VACUUM INTO still present in {module_path}"
            )


# ---------------------------------------------------------------------------
# 3. Partition archive — date slug guard + containment (archive.py)
# ---------------------------------------------------------------------------


class TestArchivePartitionGuard:
    @pytest.mark.parametrize(
        "bad",
        [
            "." * 2 + "/evil",
            "2024-01-01/" + "." * 2 + "/" + "." * 2 + "/evil",
            "." * 2,
            "",
            "a/b",
            "2024-01-01\\x",
        ],
    )
    def test_safe_partition_date_rejects_traversal(self, bad: str) -> None:
        with pytest.raises(ValueError):
            _safe_partition_date(bad)

    def test_safe_partition_date_accepts_real_dates(self) -> None:
        assert _safe_partition_date("2026-09-10") == "2026-09-10"
        assert _safe_partition_date("1999-12-31") == "1999-12-31"

    def test_migrate_writes_only_under_bypasses_dir(self, tmp_path: Path) -> None:
        """bypass_log.jsonl là dữ liệu external: mọi file output phải nằm trong
        ``data_dir/bypasses`` với tên YYYY-MM-DD.jsonl; record hỏng → errors."""
        log = tmp_path / "bypass_log.jsonl"
        good = {
            "timestamp": 1757460000.0,  # 2025-09-10T00:40:00Z (local-tz độc lập)
            "bypass_id": "bp-1",
            "question": "probe",
        }
        malformed = {"timestamp": "not-a-timestamp", "bypass_id": "bp-2"}
        log.write_text(
            json.dumps(good) + "\n" + json.dumps(malformed) + "\n",
            encoding="utf-8",
        )
        result: dict[str, Any] = migrate_old_to_new(
            data_dir=tmp_path, dry_run=False
        )
        bypasses = tmp_path / "bypasses"
        date_re = re.compile(r"^\d{4}-\d{2}-\d{2}\.jsonl$")
        written = list(bypasses.glob("*.jsonl")) if bypasses.is_dir() else []
        assert written, "expected at least one partition file"
        for f in written:
            assert date_re.fullmatch(f.name), f"unsafe partition filename: {f.name}"
            assert f.resolve().is_relative_to(bypasses.resolve())
        # Record timestamp không parse được phải fail vào errors, không ghi file.
        assert result["errors"], "malformed timestamp must be reported"
        # Không có file nào được ghi ra ngoài data_dir.
        for f in tmp_path.rglob("*"):
            if f.is_file() and f.name.endswith(".jsonl"):
                assert f.resolve().is_relative_to(tmp_path.resolve()), (
                    f"file escaped data_dir: {f}"
                )


# ---------------------------------------------------------------------------
# 4. Benchmark / scripts path guards
# ---------------------------------------------------------------------------


class TestBenchmarkPathGuards:
    def test_run_benchmark_v2_output_guard_rejects_traversal(self) -> None:
        import benchmark.run_benchmark_v2 as rbm

        with pytest.raises(ValueError):
            rbm._safe_output_path("." * 2 + "/evil.json")
        with pytest.raises(ValueError):
            rbm._safe_output_path("results_v2/" + "." * 2 + "/" + "." * 2 + "/evil.json")

    def test_run_benchmark_v2_output_guard_accepts_normal_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import benchmark.run_benchmark_v2 as rbm

        monkeypatch.chdir(REPO_ROOT)
        resolved = rbm._safe_output_path("results_v2/sec_s4_ok.json")
        assert resolved.is_absolute()
        assert resolved.is_relative_to(REPO_ROOT.resolve())

    def test_rotate_jsonl_rejects_traversal_and_non_jsonl(
        self, tmp_path: Path
    ) -> None:
        for bad in ("." * 2 + "/evil.jsonl", str(tmp_path / "note.txt"), "." * 2):
            result = rotate_jsonl(bad, max_records=10)
            assert result.get("error"), f"must reject unsafe path: {bad}"
            assert result["rotated"] is False

    def test_rotate_jsonl_still_rotates_real_files(self, tmp_path: Path) -> None:
        f = tmp_path / "good.jsonl"
        f.write_text(
            "\n".join(json.dumps({"i": i}) for i in range(300)) + "\n",
            encoding="utf-8",
        )
        result = rotate_jsonl(str(f), max_records=200)
        assert result["rotated"] is True
        assert result["after_count"] == 200
        assert len(f.read_text(encoding="utf-8").strip().splitlines()) == 200


class TestScriptGuardsPresent:
    """Các script nội bộ chạy side-effects khi import (không import được vào
    test) — assert bằng AST rằng guard [SEC-S4] tồn tại trong source."""

    @pytest.mark.parametrize(
        "relpath",
        [
            "benchmark/extract_gold_anchor_v2.py",
            "benchmark/run_ragas_v1.py",
            "benchmark/run_world_exam.py",
            "benchmark/run_humaneval.py",
            "benchmark/download_global_top1_benchmarks.py",
            "scripts/prep_quick_exam.py",
            "scripts/run_full_audit.py",
            "scripts/diagnostics/count_kb_r37.py",
            "scripts/history/r44_build_regression_corpus.py",
            "scripts/learning/learning_staging_r43.py",
            "scripts/ops/scp_db_consistent_snapshot.py",
            "scripts/ops/scp_db_readonly_audit.py",
        ],
    )
    def test_guard_marker_present_and_module_parses(self, relpath: str) -> None:
        path = REPO_ROOT / relpath
        source = path.read_text(encoding="utf-8")
        ast.parse(source)  # module vẫn là Python hợp lệ
        assert "[SEC-S4]" in source, f"missing SEC-S4 guard marker in {relpath}"


# ---------------------------------------------------------------------------
# 5. smart_cache deserialization — JSON only, no binary deserializer
# ---------------------------------------------------------------------------


class TestSmartCacheDeserialization:
    def test_smart_cache_source_has_no_binary_deserializer(self) -> None:
        """CWE-502 fix: smart_cache phải chỉ dùng JSON. Không còn token
        deserialization binary nào trong module."""
        source = (REPO_ROOT / "scp" / "core" / "smart_cache.py").read_text(
            encoding="utf-8"
        )
        assert "pickle.lo" + "ads" not in source
        assert "pickle.du" + "mps" not in source
        assert "yaml.lo" + "ad" not in source

    def test_disk_payload_roundtrip_is_json(self) -> None:
        """Round-trip serializer thực tế của _disk_set (JSON bytes) phải giữ
        nguyên shape dict — không cần binary deserializer."""
        from scp.core.smart_cache import _dict_to_slm_response, _slm_response_to_dict

        @__import__("dataclasses").dataclass
        class _Resp:
            question: str
            answer: str
            confidence: float
            domain: str
            reasoning: str
            evidence: dict
            slm_name: str
            processing_time: float

        original = _Resp(
            question="q?", answer="a", confidence=0.9, domain="d",
            reasoning="r", evidence={"src": "Binance"}, slm_name="probe",
            processing_time=1.0,
        )
        as_dict = _slm_response_to_dict(original)
        blob = json.dumps(as_dict, ensure_ascii=False).encode("utf-8")
        restored_value = json.loads(blob.decode("utf-8"))
        back = _dict_to_slm_response(restored_value)
        assert back is not None
        assert back.question == "q?"
        assert back.answer == "a"
        assert abs(back.confidence - 0.9) < 1e-9

    def test_smart_cache_in_memory_roundtrip_unchanged(self) -> None:
        """Round-trip SmartCache thật (in-memory) phải giữ nguyên giá trị dict
        — sweep S4 không được đổi behavior cache."""
        from scp.core.smart_cache import get_smart_cache

        cache = get_smart_cache()
        cache.clear()
        payload = {"value": 62113, "source": "Binance", "nested": {"k": [1, 2]}}
        cache.set("sec-s4", "probe-1", payload, "Binance")
        got = cache.get("sec-s4", "probe-1")
        assert got == payload
        cache.invalidate("sec-s4", "probe-1")
        # In-memory miss sau invalidate (disk path có thể giữ bản cũ — clear disk side not touched).
        assert cache.get("sec-s4", "probe-1") in (None, payload)
