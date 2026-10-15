"""
SCP V105 — Meta schema initialization.

[Task 7-A Modularity] TẠI SAO tách init_meta_db ra file riêng?
- meta.py原本 1018 LOC (>1000 ISO 25010 Modularity threshold)
- init_meta_db() là 93 LOC pure DDL (CREATE TABLE + INSERT seed)
- Tách ra không thay đổi behavior, chỉ giảm LOC của meta.py xuống ~925
- Single Responsibility: schema init tách khỏi class definitions
"""
# [G3-CONSOLIDATE RE-17] Meta namespace status:
# - This file: init_meta_db() DDL — creates 5 SQLite tables (meta_goals,
#   meta_curiosity, meta_world_model, meta_principles, meta_identity) + seeds
#   10 default identity rows — 108 LOC. Called by MetaCognitionEngine.__init__
#   (meta.py:784), so 24/7-only (run_247.py).
# - NOT related to: scp/meta/meta.py (MetaCognitionEngine), scp/meta/scp_meta.py (council).
# - The 'meta' namespace contains 3 UNRELATED things:
#   1. meta.py — MetaCognitionEngine (5 sub-engines, 929 LOC)
#   2. scp_meta.py — SCPMeta council (4 enums + SCPMetaReview dataclass, 61 LOC)
#   3. meta_schema.py — DDL init (5 meta_* tables, 108 LOC)
# - No rename attempted (would break imports) — this marker documents reality.

from datetime import datetime

from scp.core.db_manager import db_exec, db_query_one


def init_meta_db():
    """Tạo 5 tables cho 5 tầng meta-cognition."""

    # 1. GOALS — Mission + Goals dài hạn
    db_exec("""
        CREATE TABLE IF NOT EXISTS meta_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,           -- 'mission' | 'goal' | 'sub_goal'
            description TEXT NOT NULL,
            status TEXT DEFAULT 'active', -- 'active' | 'paused' | 'completed' | 'abandoned'
            priority INTEGER DEFAULT 5,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            parent_id INTEGER,            -- Cho sub_goals
            progress REAL DEFAULT 0.0,    -- 0.0 to 1.0
            notes TEXT DEFAULT '',
            forbidden BOOLEAN DEFAULT 0   -- Forbidden goals
        )
    """)

    # 2. CURIOSITY — Câu hỏi được chọn dựa trên Information Gain
    db_exec("""
        CREATE TABLE IF NOT EXISTS meta_curiosity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            question TEXT NOT NULL,
            entity TEXT,
            domain TEXT,
            information_gain REAL DEFAULT 0.0,   -- 0-1, cao = đáng hỏi
            curiosity_type TEXT,                 -- 'gap' | 'contradiction' | 'novelty' | 'anomaly' | 'edge_case'
            reason TEXT,
            asked BOOLEAN DEFAULT 0,
            asked_at TEXT,
            result TEXT                          -- Kết quả sau khi hỏi
        )
    """)

    # 3. WORLD MODEL — Graph quan hệ
    db_exec("""
        CREATE TABLE IF NOT EXISTS meta_world_model (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,        -- entity (vd: "co2")
            relation TEXT NOT NULL,       -- quan hệ (vd: "is_a", "affects", "part_of")
            object TEXT NOT NULL,         -- target (vd: "gas", "greenhouse_gas", "climate")
            confidence REAL DEFAULT 0.5,
            source TEXT,
            timestamp TEXT NOT NULL,
            times_verified INTEGER DEFAULT 0,
            UNIQUE(subject, relation, object)
        )
    """)

    # 4. PRINCIPLES — Abstraction từ Lessons
    db_exec("""
        CREATE TABLE IF NOT EXISTS meta_principles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            principle TEXT NOT NULL,      -- "API unstable -> ưu tiên cache"
            derived_from TEXT,            -- IDs of lessons
            domain TEXT,
            confidence REAL DEFAULT 0.5,
            created_at TEXT NOT NULL,
            applied_count INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0
        )
    """)

    # 5. IDENTITY — Mission, boundaries, values
    db_exec("""
        CREATE TABLE IF NOT EXISTS meta_identity (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT
        )
    """)

    # Seed default identity if empty
    existing = db_query_one("SELECT COUNT(*) as cnt FROM meta_identity")["cnt"]
    if existing == 0:
        defaults = [
            ("mission", "Verify reality claims against ground truth. Learn from mistakes. Never hallucinate."),
            ("identity", "SCP — Self-Correcting Pipeline. A cognitive system that checks, learns, and evolves."),
            ("boundary", "Only verify claims that can be checked against external reality. Do not generate opinions."),
            ("value_1", "Truth over confidence. If unsure, say UNKNOWN."),
            ("value_2", "Evidence over assertion. Every verdict needs a source."),
            ("value_3", "Learning over perfection. Mistakes are data, not failures."),
            ("forbidden_1", "Do not fabricate data. If API fails, say UNKNOWN."),
            ("forbidden_2", "Do not delete raw history. Compress, never destroy."),
            ("forbidden_3", "Do not skip verification. Every claim must be checked."),
            ("long_term_goal", "Build a comprehensive knowledge base of verified facts across 100+ domains."),
        ]
        for key, value in defaults:
            db_exec("INSERT INTO meta_identity (key, value, updated_at) VALUES (?, ?, ?)",
                    (key, value, datetime.now().astimezone().isoformat()))
