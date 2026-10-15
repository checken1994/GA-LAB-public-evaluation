from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scp.kernel_storage import SQLiteKernelStorage, make_storage
from scp.task_kernel import TaskKernel


class TrackingStorage:
    """Small contract spy; SQL behaviour still comes from the real backend."""

    def __init__(self, db_path: Path) -> None:
        self.backend = SQLiteKernelStorage(db_path)
        self.db_path = str(db_path)
        self.begins = 0
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def begin(self) -> None:
        self.begins += 1
        self.backend.begin()

    def commit(self) -> None:
        self.commits += 1
        self.backend.commit()

    def rollback(self) -> None:
        self.rollbacks += 1
        self.backend.rollback()

    def execute(self, sql: str, params: Any = ()) -> Any:
        return self.backend.execute(sql, params)

    def executescript(self, script: str) -> None:
        self.backend.executescript(script)

    def fetchone(self, sql: str, params: Any = ()) -> Any | None:
        return self.backend.fetchone(sql, params)

    def fetchall(self, sql: str, params: Any = ()) -> list[Any]:
        return self.backend.fetchall(sql, params)

    @property
    def in_transaction(self) -> bool:
        return self.backend.in_transaction

    def backup_to(self, target: str | Path) -> None:
        self.backend.backup_to(target)

    def close(self) -> None:
        self.closed = True
        self.backend.close()


def test_task_kernel_uses_injected_storage_for_transaction_lifecycle(tmp_path: Path) -> None:
    storage = TrackingStorage(tmp_path / "kernel.sqlite3")
    kernel = TaskKernel(storage=storage)

    kernel.create_task("storage-contract", "test", "prove injected storage")
    kernel.transition("storage-contract", "PLANNING")

    assert kernel.get_task("storage-contract")["state"] == "PLANNING"
    assert storage.begins == 2
    assert storage.commits == 2
    assert storage.rollbacks == 0

    kernel.close()
    assert storage.closed is True


def test_task_kernel_backup_is_delegated_to_storage(tmp_path: Path) -> None:
    storage = TrackingStorage(tmp_path / "kernel.sqlite3")
    kernel = TaskKernel(storage=storage)
    kernel.create_task("backup-contract", "test", "prove backup delegation")

    result = kernel.backup(tmp_path / "backups", retain=1)

    backup_path = Path(result["backup"])
    assert backup_path.is_file()
    reopened = TaskKernel(backup_path)
    try:
        assert reopened.get_task("backup-contract")["state"] == "CREATED"
    finally:
        reopened.close()
        kernel.close()


def test_make_storage_spof_warning_docstring() -> None:
    """make_storage docstring must contain explicit SPOF warning for distributed deployments."""
    doc = make_storage.__doc__ or ""
    assert "WARNING: SQLite is a Single Point of Failure (SPOF) in distributed deployments." in doc
    assert "For high availability or multi-node production setups, a distributed storage backend is required." in doc


def test_make_storage_default_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """make_storage returns SQLiteKernelStorage when SCP_STORAGE_BACKEND is unset."""
    monkeypatch.delenv("SCP_STORAGE_BACKEND", raising=False)
    storage = make_storage(tmp_path / "default.sqlite3")
    try:
        assert isinstance(storage, SQLiteKernelStorage)
        assert storage.db_path == str(tmp_path / "default.sqlite3")
    finally:
        storage.close()


@pytest.mark.parametrize("backend_val", ["sqlite", "SQLite", "SQLITE", "  sqlite  ", ""])
def test_make_storage_explicit_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend_val: str) -> None:
    """make_storage returns SQLiteKernelStorage when SCP_STORAGE_BACKEND is sqlite or empty."""
    monkeypatch.setenv("SCP_STORAGE_BACKEND", backend_val)
    storage = make_storage(tmp_path / "test.sqlite3")
    try:
        assert isinstance(storage, SQLiteKernelStorage)
    finally:
        storage.close()


@pytest.mark.parametrize("unsupported", ["postgres", "mysql", "etcd", "redis", "distributed"])
def test_make_storage_unsupported_backend_raises_not_implemented(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unsupported: str
) -> None:
    """make_storage raises NotImplementedError when SCP_STORAGE_BACKEND is an unsupported backend."""
    monkeypatch.setenv("SCP_STORAGE_BACKEND", unsupported)
    with pytest.raises(NotImplementedError) as exc_info:
        make_storage(tmp_path / "test.sqlite3")

    msg = str(exc_info.value)
    assert f"Unsupported storage backend '{unsupported}'" in msg
    assert "Only 'sqlite' is currently supported" in msg
    assert "For distributed deployments, inject a custom Storage instance into TaskKernel." in msg


def test_task_kernel_fails_closed_on_unsupported_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TaskKernel constructor fails closed when SCP_STORAGE_BACKEND is unsupported."""
    monkeypatch.setenv("SCP_STORAGE_BACKEND", "postgres")
    with pytest.raises(NotImplementedError):
        TaskKernel(tmp_path / "kernel.sqlite3")


def test_gap05_multi_instance_concurrent_writes_without_rlock(tmp_path: Path) -> None:
    """Verify that independent SQLiteKernelStorage instances without in-memory RLock maintain OCC integrity."""
    db_path = tmp_path / "gap05_occ.sqlite3"
    init_storage = SQLiteKernelStorage(db_path)
    init_storage.executescript(
        "CREATE TABLE counters (id TEXT PRIMARY KEY, val INTEGER, version INTEGER DEFAULT 1);"
    )
    init_storage.execute("INSERT INTO counters (id, val, version) VALUES ('c1', 0, 1)")
    init_storage.close()

    s_a = SQLiteKernelStorage(db_path)
    s_b = SQLiteKernelStorage(db_path)
    try:
        # Transaction A updates version 1 -> 2
        s_a.begin()
        s_a.execute("UPDATE counters SET val=val+10, version=version+1 WHERE id='c1' AND version=1")
        s_a.commit()

        # Transaction B attempts update expecting stale version 1
        s_b.begin()
        cur = s_b.execute("UPDATE counters SET val=val+20, version=version+1 WHERE id='c1' AND version=1")
        assert cur.rowcount == 0  # OCC conflict detected at database level
        s_b.rollback()

        # Confirm value was updated only once
        row = s_a.fetchone("SELECT val, version FROM counters WHERE id='c1'")
        assert row["val"] == 10
        assert row["version"] == 2
    finally:
        s_a.close()
        s_b.close()

