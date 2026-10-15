"""Regression pins for A2 AUDIT-F-08 — StorageManager disk monitoring on Windows.

Previously ``_check_disk_space()`` used ``os.statvfs`` (POSIX-only). On
Windows it raised ``AttributeError`` which the broad except clause swallowed
at DEBUG level, so disk monitoring was a silent no-op: ``disk_free_mb`` and
``disk_free_percent`` stayed 0.0 forever on Windows deployments.

Post-fix the method uses ``shutil.disk_usage`` (cross-platform) with the same
alert threshold. The real-Windows pin FAILS against the pre-fix
implementation (stats would stay 0.0) and passes after it.
"""
from __future__ import annotations

import shutil as shutil_module
from pathlib import Path

import pytest

from scp.runtime.storage_manager import StorageManager


def test_check_disk_space_reports_real_disk_on_windows(tmp_path: Path):
    """Real-Windows pin: disk stats must reflect the actual volume, not 0.0."""
    manager = StorageManager(data_dir=str(tmp_path))
    manager._check_disk_space()

    reference = shutil_module.disk_usage(tmp_path)
    expected_free_mb = round(reference.free / (1024 * 1024), 1)
    expected_percent = round(reference.free / reference.total * 100, 1)

    assert manager._stats.disk_free_mb == pytest.approx(expected_free_mb, rel=0.01), (
        "disk_free_mb must be a real measurement, not the stale 0.0 no-op"
    )
    assert manager._stats.disk_free_percent == pytest.approx(expected_percent, rel=0.01)
    assert manager._stats.disk_free_mb > 0, "a working system disk always has some free space"
    assert 0 < manager._stats.disk_free_percent < 100


def test_check_disk_space_uses_shutil_disk_usage_values(tmp_path: Path, monkeypatch):
    """Deterministic pin: values come from shutil.disk_usage; threshold logic
    (DISK_ALERT_PERCENT) is unchanged."""
    observed: dict = {}

    class _FakeUsage:
        free = 2 * 1024 * 1024 * 1024  # 2 GiB
        total = 10 * 1024 * 1024 * 1024  # 10 GiB
        used = 8 * 1024 * 1024 * 1024

    def fake_disk_usage(path):
        observed["path"] = path
        return _FakeUsage()

    monkeypatch.setattr(
        "scp.runtime.storage_manager.shutil.disk_usage", fake_disk_usage
    )

    manager = StorageManager(data_dir=str(tmp_path))
    manager._check_disk_space()

    assert observed["path"] == manager.data_dir
    assert manager._stats.disk_free_mb == pytest.approx(2048.0)
    assert manager._stats.disk_free_percent == pytest.approx(20.0)


def test_check_disk_space_low_disk_alert_branch(tmp_path: Path, monkeypatch, caplog):
    """The DISK_ALERT_PERCENT branch still fires (and only via real stats):
    1 MiB free of 10 GiB -> ~0.0% -> warning, not silence."""
    import logging

    class _NearlyFullUsage:
        free = 1024 * 1024  # 1 MiB
        total = 10 * 1024 * 1024 * 1024
        used = 10 * 1024 * 1024 * 1024 - 1024 * 1024

    monkeypatch.setattr(
        "scp.runtime.storage_manager.shutil.disk_usage", lambda _p: _NearlyFullUsage()
    )

    manager = StorageManager(data_dir=str(tmp_path))
    with caplog.at_level(logging.WARNING, logger="scp.runtime.storage_manager"):
        manager._check_disk_space()

    assert manager._stats.disk_free_percent == pytest.approx(0.0, abs=0.1)
    assert any(
        "Disk space LOW" in record.getMessage() for record in caplog.records
    ), "low-disk condition must be logged loudly (fail-loud monitoring)"
