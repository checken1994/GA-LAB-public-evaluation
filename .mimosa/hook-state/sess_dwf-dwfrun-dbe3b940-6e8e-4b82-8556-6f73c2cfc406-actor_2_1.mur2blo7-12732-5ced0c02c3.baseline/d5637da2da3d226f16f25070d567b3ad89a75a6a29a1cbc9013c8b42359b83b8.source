# Auto-extracted from db_manager.py
import logging

logger = logging.getLogger(__name__)
def init_db():
    """Initialize all V14 tables + V62 all module tables."""
    db_exec("CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, question TEXT, ai_answer TEXT, frame TEXT, verdict TEXT, reason TEXT, status TEXT DEFAULT 'active', recovered_at TEXT)")  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    db_exec("CREATE TABLE IF NOT EXISTS meta_goals (\n        id INTEGER PRIMARY KEY AUTOINCREMENT,\n        type TEXT DEFAULT 'goal',\n        description TEXT,\n        status TEXT DEFAULT 'active',\n        priority REAL DEFAULT 5,\n        progress REAL DEFAULT 0,\n        notes TEXT,\n        created_at TEXT,\n        updated_at TEXT,\n        parent_id INTEGER\n    )")  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    db_exec("CREATE TABLE IF NOT EXISTS health_states (domain TEXT PRIMARY KEY, state TEXT DEFAULT 'UNKNOWN')")  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    try:
        db_exec('ALTER TABLE health_states ADD COLUMN last_updated TEXT')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    except Exception as e:
        logger.debug(f'[V104.37] core/db_manager.py: e={e}', exc_info=True)
    db_exec('CREATE TABLE IF NOT EXISTS health_counters (domain TEXT PRIMARY KEY, pass INTEGER DEFAULT 0, block INTEGER DEFAULT 0, inapplicable INTEGER DEFAULT 0, total INTEGER DEFAULT 0)')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    db_exec("CREATE TABLE IF NOT EXISTS recovery_issues (id TEXT PRIMARY KEY, timestamp TEXT, domain TEXT, question TEXT, ai_answer TEXT, error_type TEXT, cause TEXT, fix_action TEXT, status TEXT DEFAULT 'OPEN')")  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    db_exec("CREATE TABLE IF NOT EXISTS knowledge_memory (id TEXT PRIMARY KEY, timestamp TEXT, question TEXT, ai_answer TEXT, domain TEXT, error_type TEXT, cause TEXT, fix_action TEXT, fix_artifact TEXT, evidence TEXT, confidence REAL, status TEXT DEFAULT 'active', retest_result TEXT DEFAULT '', retest_count INTEGER DEFAULT 0)")  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    db_exec("CREATE TABLE IF NOT EXISTS error_history (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, question TEXT NOT NULL, ai_answer TEXT, frame TEXT, v13_verdict TEXT, final_verdict TEXT, verdict_detail TEXT, error_type TEXT, source TEXT, real_value TEXT, ai_value TEXT, reason TEXT, learned_from TEXT DEFAULT '', sha256 TEXT, importance_score REAL DEFAULT 50.0, last_accessed TEXT, is_foundational INTEGER DEFAULT 0, is_superseded INTEGER DEFAULT 0)")  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    # [Fix 4-b-019 runner 2026-09-25] Idempotent column migration. TẠI SAO:
    # CREATE TABLE IF NOT EXISTS ở trên là no-op khi bảng đã tồn tại với schema
    # cũ hơn (VD: schema tối thiểu do component/test khác tạo trước init_db) —
    # khi đó CREATE INDEX idx_error_importance dưới đây crash toàn bộ init_db
    # với "no such column: importance_score" (sqlite3.OperationalError, observed
    # on a fresh GitHub runner). Heal cột trước khi tạo index, cùng pattern
    # idempotent với cột `domain` ngay bên dưới. Lỗi thật (DB lock/không ghi
    # được) vẫn propagate ở bước CREATE INDEX — fail-closed giữ nguyên.
    try:
        db_exec('ALTER TABLE error_history ADD COLUMN importance_score REAL DEFAULT 50.0')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    except Exception as e:
        logger.debug(f'[V104.37] core/db_manager.py: e={e}', exc_info=True)
    db_exec('CREATE INDEX IF NOT EXISTS idx_error_frame ON error_history(frame)')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    db_exec('CREATE INDEX IF NOT EXISTS idx_error_verdict ON error_history(final_verdict)')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    db_exec('CREATE INDEX IF NOT EXISTS idx_error_source ON error_history(source)')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    db_exec('CREATE INDEX IF NOT EXISTS idx_error_importance ON error_history(importance_score)')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    try:
        db_exec("ALTER TABLE error_history ADD COLUMN domain TEXT DEFAULT ''")  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    except Exception as e:
        logger.debug(f'[V104.37] core/db_manager.py: e={e}', exc_info=True)
    try:
        db_exec('CREATE INDEX IF NOT EXISTS idx_error_domain ON error_history(domain)')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    except Exception as e:
        logger.debug(f'[V104.37] core/db_manager.py: e={e}', exc_info=True)
    db_exec('\n        CREATE TABLE IF NOT EXISTS knowledge_versions (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            timestamp TEXT NOT NULL,\n            entity TEXT NOT NULL,\n            attribute TEXT NOT NULL,\n            old_value TEXT,\n            new_value TEXT,\n            change_type TEXT,\n            source TEXT,\n            reason TEXT\n        )\n    ')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    db_exec('CREATE INDEX IF NOT EXISTS idx_kv_entity ON knowledge_versions(entity, attribute)')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    _init_all_module_tables()  # noqa: F821  # [hygiene-keep] _init_all_module_tables injected by db_manager.py rebind/wire
