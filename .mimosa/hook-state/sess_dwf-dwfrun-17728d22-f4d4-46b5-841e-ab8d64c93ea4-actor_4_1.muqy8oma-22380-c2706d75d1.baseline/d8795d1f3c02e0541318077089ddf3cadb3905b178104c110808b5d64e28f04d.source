"""
SCP V104.3 — Startup Optimizer
==============================
Tối ưu startup time 3-5x:

Vấn đề V104.2:
  1. RealityJudge.__init__ chạy tuần tự: 53 SLM init = 200ms
  2. Background scheduler trigger crawl ngay lập tức (now-last=0 vs interval)
     → ThreatIntelCrawler blocks ~2s
     → ThreatSimulator blocks ~3s
     → SelfAdaptiveEngine cycle blocks ~10s
  3. SQLite WAL file có thể lớn (1.4MB sau nhiều cycles)
  4. error_store.jsonl + bypass_log.jsonl grow vô hạn

V104.3 Fixes:
  1. DEFERRED STARTUP: chờ 60s sau khi API sẵn sàng mới start background
  2. LAZY SLM: không init SLM ở __init__, chỉ init khi được route tới
  3. SQLITE MAINTENANCE: WAL checkpoint + vacuum khi data file > 5MB
  4. JSONL ROTATION: giữ 200 records gần nhất (vs vô hạn)
  5. STARTUP PROGRESS: hiển thị % hoàn thành trong dashboard

Benchmark dự kiến:
  V104.2: ~1.4-3s blocking (Windows + WAL lớn → 3-5s)
  V104.3: ~300ms blocking (3-5x nhanh hơn)
"""
from __future__ import annotations

import json
import logging
import os
import shutil  # [FALSE-POS-FIX] F402: moved module-level (was local import inside loop at L176 + L295)
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger("scp.core.startup_optimizer")

# V104.3 constants
STARTUP_DEFER_SECONDS = int(os.environ.get("SCP_STARTUP_DEFER", "60"))
WAL_CHECKPOINT_THRESHOLD = int(os.environ.get("SCP_WAL_THRESHOLD", str(5 * 1024 * 1024)))  # 5MB
JSONL_MAX_RECORDS = int(os.environ.get("SCP_JSONL_MAX", "200"))
DATA_DIR = Path(os.environ.get("SCP_DATA_DIR", "data"))


def optimize_sqlite_wal(db_path: str = "data/v13.db") -> dict:
    """V104.3.1: SQLite WAL checkpoint + auto-vacuum nếu WAL > 5MB.

    Returns: {before_size, after_size, vacuumed, checkpointed}
    """
    result = {
        "before_wal_size": 0,
        "after_wal_size": 0,
        "before_db_size": 0,
        "after_db_size": 0,
        "checkpointed": False,
        "vacuumed": False,
    }

    wal_path = f"{db_path}-wal"

    try:
        if os.path.exists(wal_path):
            result["before_wal_size"] = os.path.getsize(wal_path)
        if os.path.exists(db_path):
            result["before_db_size"] = os.path.getsize(db_path)

        # Checkpoint WAL → main DB
        if result["before_wal_size"] > 0:
            conn = sqlite3.connect(db_path, timeout=30.0)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            result["checkpointed"] = True
            # Auto-vacuum if DB > 5MB
            if result["before_db_size"] > WAL_CHECKPOINT_THRESHOLD:
                conn.execute("VACUUM")
                result["vacuumed"] = True
            conn.close()

        if os.path.exists(wal_path):
            result["after_wal_size"] = os.path.getsize(wal_path)
        else:
            result["after_wal_size"] = 0
        if os.path.exists(db_path):
            result["after_db_size"] = os.path.getsize(db_path)

        logger.info(f"V104.3 SQLite optimized: WAL "
                    f"{result['before_wal_size']}→{result['after_wal_size']} bytes, "
                    f"DB {result['before_db_size']}→{result['after_db_size']} bytes, "
                    f"vacuumed={result['vacuumed']}")
    except Exception as e:
        logger.warning(f"V104.3 SQLite optimize failed: {e}", exc_info=True)

    return result


def rotate_jsonl(file_path: str, max_records: int | None = None) -> dict:
    """V104.3.2: Giữ max_records gần nhất của JSONL.

    Returns: {before_count, after_count, before_size, after_size}
    """
    if max_records is None:
        max_records = JSONL_MAX_RECORDS

    result = {
        "before_count": 0, "after_count": 0,
        "before_size": 0, "after_size": 0, "rotated": False,
    }

    # [SEC-S4] Path guard: rotate_jsonl writes/renames the given file, so it
    # must be a concrete .jsonl file with no traversal ("..") components.
    _requested = Path(file_path)
    if ".." in _requested.parts or _requested.suffix != ".jsonl":
        result["error"] = "rejected: unsafe path"
        logger.warning(f"V104.3 JSONL rotate rejected unsafe path: {file_path}")
        return result

    try:
        if not os.path.exists(file_path):
            return result

        result["before_size"] = os.path.getsize(file_path)

        # Read streaming to prevent JSONL memory bloat (Gap 1)
        import collections
        count = 0
        kept_lines = collections.deque(maxlen=max_records)
        with open(file_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                count += 1
                kept_lines.append(line)

        result["before_count"] = count

        if count <= max_records:
            return result  # No rotation needed

        result["after_count"] = len(kept_lines)

        # Backup original
        backup_path = f"{file_path}.bak"
        os.rename(file_path, backup_path)

        # Write rotated
        with Path(file_path).open("w", encoding="utf-8") as f:
            f.writelines(kept_lines)

        result["after_size"] = os.path.getsize(file_path)
        result["rotated"] = True

        # Remove backup if rotation succeeded
        if os.path.exists(backup_path):
            os.remove(backup_path)

        logger.info(f"V104.3 JSONL rotated: {file_path} "
                    f"{result['before_count']}→{result['after_count']} records, "
                    f"{result['before_size']}→{result['after_size']} bytes")
    except Exception as e:
        logger.warning(f"V104.3 JSONL rotate failed for {file_path}: {e}", exc_info=True)

    return result


def cleanup_data_directory(data_dir: str = "data") -> dict:
    """V104.3.3: Cleanup all data files.

    - SQLite WAL checkpoint
    - JSONL rotation (bypass_log, error_store)
    - Remove stale __pycache__ in data/
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        return {"skipped": "data dir not exist"}

    results = {
        "sqlite": {},
        "jsonl": {},
        "removed_files": [],
    }

    # SQLite optimization
    for db_file in data_path.glob("*.db"):
        results["sqlite"][db_file.name] = optimize_sqlite_wal(str(db_file))

    # JSONL rotation
    for jsonl_file in data_path.glob("*.jsonl"):
        results["jsonl"][jsonl_file.name] = rotate_jsonl(str(jsonl_file))

    # Remove __pycache__ if exists
    for cache_dir in data_path.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)  # [FALSE-POS-FIX] F402: use module-level shutil import (line 296)
        results["removed_files"].append(str(cache_dir))

    return results


async def deferred_background_start(
    judge,
    delay_seconds: int | None = None,
) -> None:
    """V104.3.4: Start background schedulers sau delay (default 60s).

    Chạy await asyncio.sleep(delay) trước khi start schedule_background_jobs.
    → User có thể gọi /ask ngay lập tức, không bị block bởi:
    - ThreatIntelCrawler crawl (2s)
    - ThreatSimulator sim (3s)
    - SelfAdaptiveEngine cycle (10s)
    """
    import asyncio
    if delay_seconds is None:
        delay_seconds = STARTUP_DEFER_SECONDS

    logger.info(f"V104.3 Deferred background start: waiting {delay_seconds}s "
                f"before starting schedulers...")
    await asyncio.sleep(delay_seconds)
    logger.info("V104.3 Deferred: starting background schedulers now")

    # Now start the actual scheduler
    if hasattr(judge, "schedule_background_jobs"):
        await judge.schedule_background_jobs()
    elif hasattr(judge, "schedule_v100_background_jobs"):
        await judge.schedule_v100_background_jobs()


def get_data_directory_stats(data_dir: str = "data") -> dict:
    """V104.3.5: Get stats about data directory sizes."""
    data_path = Path(data_dir)
    if not data_path.exists():
        return {"exists": False}

    stats = {
        "exists": True,
        "total_size_bytes": 0,
        "files": {},
    }

    for f in data_path.rglob("*"):
        if f.is_file():
            size = f.stat().st_size
            stats["total_size_bytes"] += size
            stats["files"][str(f.relative_to(data_path))] = size

    stats["total_size_mb"] = round(stats["total_size_bytes"] / (1024 * 1024), 2)
    return stats


# ============================================================
# V104.3 Startup Optimization — Main entry
# ============================================================

async def run_startup_optimization(data_dir: str = "data") -> dict:
    """Run all V104.3 optimizations at startup (before background schedulers).

    Order:
    1. SQLite WAL checkpoint (synchronous, ~10ms)
    2. JSONL rotation (synchronous, ~5ms per file)
    3. Cleanup __pycache__
    4. Log data directory stats
    5. Schedule deferred background start (after 60s)
    """
    t0 = time.time()
    logger.info("V104.3 Startup optimization starting...")

    # Step 1-3: Cleanup data directory
    cleanup_results = cleanup_data_directory(data_dir)

    # Step 4: Stats
    stats = get_data_directory_stats(data_dir)

    elapsed_ms = int((time.time() - t0) * 1000)
    logger.info(f"V104.3 Startup optimization complete in {elapsed_ms}ms. "
                f"Data dir: {stats.get('total_size_mb', 0)}MB, "
                f"{len(stats.get('files', {}))} files")

    return {
        "elapsed_ms": elapsed_ms,
        "cleanup": cleanup_results,
        "data_stats": stats,
        "deferred_background_start_seconds": STARTUP_DEFER_SECONDS,
    }


if __name__ == "__main__":
    import asyncio
    print("=== V104.3 Startup Optimizer — Test ===\n")

    # Test 1: SQLite optimize on existing DB
    print("Test 1: SQLite WAL optimize")
    r = optimize_sqlite_wal("data/v13.db")
    print(f"  {r}")

    # Test 2: JSONL rotation (synthetic)
    print("\nTest 2: JSONL rotation")
    import tempfile
    tmpdir = tempfile.mkdtemp()
    test_jsonl = os.path.join(tmpdir, "test.jsonl")
    # [SEC-S4] Containment: synthetic test file must stay inside its tmpdir.
    assert Path(test_jsonl).resolve().is_relative_to(Path(tmpdir).resolve())  # noqa: S101
    with Path(test_jsonl).open("w") as f:
        for i in range(500):
            f.write(json.dumps({"i": i, "data": f"record {i}"}) + "\n")
    r = rotate_jsonl(test_jsonl, max_records=200)
    print(f"  {r}")
    # Verify
    with open(test_jsonl) as f:
        lines = f.readlines()
    print(f"  Final count: {len(lines)} (expected 200)")
    assert len(lines) == 200  # noqa: S101

    # Test 3: Full cleanup
    print("\nTest 3: Full cleanup_data_directory")
    r = cleanup_data_directory(tmpdir)
    print(f"  {r}")

    shutil.rmtree(tmpdir, ignore_errors=True)  # [FALSE-POS-FIX] F402: use module-level shutil

    # Test 4: Stats
    print("\nTest 4: Stats")
    s = get_data_directory_stats("data")
    print(f"  Total: {s.get('total_size_mb', 0)}MB, {len(s.get('files', {}))} files")

    # Test 5: Async deferred start
    print("\nTest 5: Deferred background start (will wait 2s)")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    class MockJudge:
        async def schedule_background_jobs(self):
            print("  [Mock] Background schedulers started")

    t0 = time.time()
    loop.run_until_complete(deferred_background_start(MockJudge(), delay_seconds=2))
    print(f"  Waited: {time.time()-t0:.1f}s")
    loop.close()

    print("\n✓ V104.3 test complete.")
