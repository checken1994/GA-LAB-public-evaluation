"""
SCP V88 — Auto-backup SQLite to Hugging Face Hub
Pushes v13.db to HF dataset every N cycles to prevent data loss on container restart.
"""
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("scp.github_backup")

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
DB_PATH = BASE_DIR / "data" / "v13.db"
BACKUP_REPO = os.environ.get("HF_BACKUP_REPO", "checken9x/scp-backup")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
BACKUP_INTERVAL_CYCLES = 10
# [FIX 2026-07-09] Cycle-count gating alone is unsafe now that cycles run as
# fast as ~14s each (post throughput optimization): every restart re-attempts
# immediately once cycle count crosses 10, and legit periodic attempts can
# still add up to 2 commits each. Confirmed LIVE: HF returned 429 "exceeded
# rate limit for repository commits (128 per hour)" with 34 consecutive
# failures within minutes of this container starting. Adding a hard wall-clock
# floor makes this robust regardless of cycle speed or how many times the
# container restarts within an hour.
BACKUP_MIN_SECONDS_BETWEEN = 240  # at most 15/hour attempts -> <=30 commits/hour, safely under the 128/hour cap
# [FIX] Skip the extra timestamped snapshot most of the time — it's a nice-to-have
# point-in-time history, not required for restore (v13.db alone is the restore
# source on boot). Only take a snapshot every Nth successful backup to cut commit
# volume roughly in half without losing restore capability.
SNAPSHOT_EVERY_N_BACKUPS = 5

_last_backup_cycle = 0
_last_backup_time = 0.0
_backup_success_count = 0

# [FIX 2026-07-09] Observability + resilience state, exposed to health.json so
# backup staleness is visible on /health instead of silently going undetected.
# Root cause found live: backups went stale for ~8.7h (01:23->10:05 UTC) with
# zero visibility on the dashboard — the only way to notice was manually
# inspecting HF dataset commit history. Also found the two uploads (v13.db +
# timestamped snapshot) were NOT independently resilient: if the 2nd upload
# raised, the whole function's except-block swallowed it AND skipped updating
# _last_backup_cycle, but there was no record of *which* upload failed or when.
_last_backup_result = {
    "last_attempt_at": None,
    "last_success_at": None,
    "last_error": None,
    "consecutive_failures": 0,
}


def get_backup_status() -> dict:
    """Expose backup health for inclusion in write_health()."""
    return dict(_last_backup_result)


def backup_to_hf(cycle_num: int) -> bool:
    """
    Backup v13.db to Hugging Face dataset repo.
    Called every cycle, but only uploads every BACKUP_INTERVAL_CYCLES AND at
    most once per BACKUP_MIN_SECONDS_BETWEEN (whichever gate is stricter).
    """
    # [FALSE-POS-FIX] F824: removed `_last_backup_result` from global —
    # only dict key assignments (_last_backup_result["key"] = val), NOT name rebinding.
    # The other 3 names ARE assigned: _last_backup_cycle (L162), _last_backup_time (L163),
    # _backup_success_count (L164 +=).
    global _last_backup_cycle, _last_backup_time, _backup_success_count

    import time as _time
    if cycle_num - _last_backup_cycle < BACKUP_INTERVAL_CYCLES:
        return False
    if _time.time() - _last_backup_time < BACKUP_MIN_SECONDS_BETWEEN:
        return False

    _last_backup_result["last_attempt_at"] = datetime.now().isoformat()

    if not DB_PATH.exists():
        logger.warning(f"[BACKUP] DB not found: {DB_PATH}")
        _last_backup_result["last_error"] = "db_not_found"
        return False

    if not HF_TOKEN:
        logger.warning("[BACKUP] No HF_TOKEN set, skipping backup")
        _last_backup_result["last_error"] = "no_hf_token"
        return False

    try:
        from huggingface_hub import HfApi, upload_file
        api = HfApi(token=HF_TOKEN)

        # Create repo if not exists
        try:
            api.create_repo(repo_id=BACKUP_REPO, repo_type="dataset", exist_ok=True)
        except Exception as e:
            logger.debug(f"[V104.37] core/github_backup.py: e={e}", exc_info=True)

        # Copy DB to temp (avoid locking issues)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name

        # [V104.35 #72] TẠI SAO: shutil.copy2 only copies v13.db, NOT v13.db-wal.
        # SCP runs in WAL mode → recent writes live in -wal file until checkpoint.
        # Without checkpoint, backup misses last N minutes of data → silent data loss
        # on container restart. Fix: checkpoint WAL before copy (mirror auto_backup.py).
        try:
            import sqlite3 as _sqlite3
            _conn = _sqlite3.connect(str(DB_PATH), timeout=10.0)
            _conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            _conn.close()
        except Exception as _e:
            logger.warning(f"[V104.35 #72] WAL checkpoint failed (proceeding anyway): {_e}", exc_info=True)

        shutil.copy2(str(DB_PATH), tmp_path)

        # [FIX] Each upload now independently try/except'd so a transient
        # failure on ONE of the two files doesn't silently hide the other's
        # outcome or leave zero trace of what happened.
        # [FIX] Snapshot copy only every SNAPSHOT_EVERY_N_BACKUPS successful
        # backups — cuts commit volume roughly in half to stay under HF's
        # 128 commits/hour cap. v13.db (updated every time) is what's used to
        # restore on boot, so this doesn't reduce actual crash-safety.
        main_ok = False
        snap_ok = None  # None = skipped this round (not attempted, not a failure)
        errors = []

        try:
            upload_file(
                path_or_fileobj=tmp_path,
                path_in_repo="v13.db",
                repo_id=BACKUP_REPO,
                repo_type="dataset",
                token=HF_TOKEN,
            )
            main_ok = True
        except Exception as e:
            logger.debug(f"backup_to_hf ignored: {e}", exc_info=True)
            errors.append(f"main_upload: {e}")

        if main_ok and (_backup_success_count % SNAPSHOT_EVERY_N_BACKUPS == 0):
            try:
                upload_file(
                    path_or_fileobj=tmp_path,
                    path_in_repo=f"backups/v13_{timestamp}.db",
                    repo_id=BACKUP_REPO,
                    repo_type="dataset",
                    token=HF_TOKEN,
                )
                snap_ok = True
            except Exception as e:
                logger.debug(f"backup_to_hf ignored: {e}", exc_info=True)
                snap_ok = False
                errors.append(f"snapshot_upload: {e}")

        try:
            os.unlink(tmp_path)
        except Exception as e:
            logger.debug(f"[V104.37] core/github_backup.py: e={e}", exc_info=True)

        db_size = DB_PATH.stat().st_size / 1024

        if main_ok:
            # [FIX] Only advance cycle/time gates when the primary v13.db copy
            # succeeded — that's the actual restore source on boot. Snapshot
            # (if attempted) is a bonus, not required for crash-safety.
            _last_backup_cycle = cycle_num
            _last_backup_time = _time.time()
            _backup_success_count += 1
            _last_backup_result["last_success_at"] = datetime.now().isoformat()
            _last_backup_result["consecutive_failures"] = 0
            if errors:
                _last_backup_result["last_error"] = "; ".join(errors)
                logger.warning(f"[BACKUP] Partial success (main=True, snapshot={snap_ok}): {errors}")
            else:
                _last_backup_result["last_error"] = None
            logger.info(f"[BACKUP] v13.db ({db_size:.0f}KB) uploaded to HF dataset: {BACKUP_REPO} "
                        f"(main=True, snapshot={snap_ok})")
            return True
        else:
            _last_backup_result["consecutive_failures"] += 1
            _last_backup_result["last_error"] = "; ".join(errors)
            # [FIX] Back off harder on rate-limit (429) errors specifically —
            # retrying every cycle against an hour-long rate-limit window just
            # burns more attempts once the window resets. Push the time-gate
            # forward so we don't hammer it again for a while.
            if any("429" in e or "rate limit" in e.lower() for e in errors):
                _last_backup_time = _time.time() - BACKUP_MIN_SECONDS_BETWEEN + 900  # wait ~15 extra min
                logger.warning(f"[BACKUP] Rate-limited (429) — backing off ~15min extra before next attempt (failure #{_last_backup_result['consecutive_failures']})")
            else:
                logger.warning(f"[BACKUP] Failed entirely (attempt #{_last_backup_result['consecutive_failures']}): {errors}")
            return False

    except Exception as e:
        _last_backup_result["consecutive_failures"] += 1
        _last_backup_result["last_error"] = str(e)
        logger.warning(f"[BACKUP] Failed: {e}", exc_info=True)
        return False
