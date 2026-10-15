"""
SCP KB Accumulation Store + Scanner Evolution Engine.

TẠI SAO module này tồn tại?
  v9.1: SCP fix bug → WHY reflect → lesson_learned → ĐỂ ĐÓ (không dùng)
  v10.0: SCP fix bug → WHY reflect → lesson → KB save → scanner evolve

  Gap v9.1:
    1. Lesson không lưu vào KB → SCP fix cùng bug lặp lại
    2. Scanner dùng patterns cố định → không detect bug mới
    3. KB không feedback vào verify → verify yếu

  v10.0 fix:
    1. LessonStore — save lessons từ reflect
    2. PatternStore — save patterns mới cho scanner
    3. ScannerEvolver — scanner đọc patterns từ KB (dynamic)
    4. WHY lookup KB — "Đã gặp pattern này chưa?"

Flow:
  Bug fixed → WHY reflect → lesson_learned
    → LessonStore.save(lesson)
    → PatternStore.save(pattern, bug_type)
    → Scanner.add_dynamic_pattern(pattern)
    → Next scan: scanner detects new pattern
    → KB accumulates → "càng chạy càng thông minh"
"""
from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("scp.meta.kb_evolve")


@dataclass
class Lesson:
    """A lesson learned from fixing a bug."""
    lesson_id: str
    timestamp: float
    bug_type: str
    bug_file: str
    bug_line: int
    root_cause: str           # WHY: "Tại sao bug xảy ra?"
    lesson: str               # Short summary
    fix_pattern: str          # How it was fixed
    fix_verified: bool        # Did _verify_fix pass?
    occurrence_count: int = 1 # How many times this lesson applied
    # [GAP-03 fail-closed] Default 0.0 (was 1.0): lesson CHƯA verify không được
    # mặc định success_rate=1.0 — consumer lọc verified_lesson_candidates theo
    # success_rate >= 0.8, nên default 1.0 = poisoning KB bằng lesson chưa
    # verify. Chỉ đạt rate cao khi có receipt verification thật (fix_verified).
    success_rate: float = 0.0 # fix success rate (verified / total); unverified = 0.0


@dataclass
class EvolvedPattern:
    """A pattern evolved from lessons — scanner uses this."""
    pattern_id: str
    timestamp: float
    bug_type: str             # "RaceCondition", "NullDereference", etc.
    pattern_regex: str        # Regex to detect this bug
    pattern_description: str  # Human-readable
    source_lesson_id: str     # Which lesson generated this?
    occurrence_count: int = 0 # How many times detected
    false_positive_count: int = 0
    confidence: float = 0.5   # Initial low, increases with verified fixes


class KBAccumulationStore:
    """Store lessons + evolved patterns for scanner evolution.

    SQLite-based — persists across restarts.
    Thread-safe (Lock).
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "kb_evolve.sqlite"
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize SQLite tables."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    lesson_id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    bug_type TEXT NOT NULL,
                    bug_file TEXT,
                    bug_line INTEGER,
                    root_cause TEXT,
                    lesson TEXT NOT NULL,
                    fix_pattern TEXT,
                    fix_verified INTEGER DEFAULT 0,
                    occurrence_count INTEGER DEFAULT 1,
                    success_rate REAL DEFAULT 0.0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evolved_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    bug_type TEXT NOT NULL,
                    pattern_regex TEXT NOT NULL,
                    pattern_description TEXT,
                    source_lesson_id TEXT,
                    occurrence_count INTEGER DEFAULT 0,
                    false_positive_count INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0.5,
                    FOREIGN KEY (source_lesson_id) REFERENCES lessons(lesson_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lessons_bug_type ON lessons(bug_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_bug_type ON evolved_patterns(bug_type)")
            conn.commit()
            conn.close()

    def save_lesson(self, lesson: Lesson) -> bool:
        """Save a lesson. If same root_cause exists, increment occurrence_count."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self.db_path))
                # Check if lesson with same root_cause exists
                existing = conn.execute(
                    "SELECT lesson_id, occurrence_count, success_rate FROM lessons WHERE root_cause = ?",
                    (lesson.root_cause[:200],)
                ).fetchone()

                if existing:
                    # Update existing — increment count
                    new_count = existing[1] + 1
                    new_rate = (existing[2] * existing[1] + (1.0 if lesson.fix_verified else 0.0)) / new_count
                    conn.execute(
                        "UPDATE lessons SET occurrence_count = ?, success_rate = ?, timestamp = ? WHERE lesson_id = ?",
                        (new_count, new_rate, lesson.timestamp, existing[0])
                    )
                    conn.commit()
                    conn.close()
                    logger.info(f"[KB-EVOLVE] Lesson updated: {existing[0]} (count={new_count}, rate={new_rate:.2f})")
                    return True
                else:
                    # [GAP-03 fail-closed] Lesson chưa verify luôn ghi rate 0.0
                    # vào KB bất kể caller truyền success_rate nào — một lesson
                    # không có receipt verification thật không được phép vượt
                    # ngưỡng verified_lesson_candidates (>= 0.8).
                    stored_rate = float(lesson.success_rate) if lesson.fix_verified else 0.0
                    # Insert new
                    conn.execute("""
                        INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        lesson.lesson_id, lesson.timestamp, lesson.bug_type,
                        lesson.bug_file, lesson.bug_line, lesson.root_cause,
                        lesson.lesson, lesson.fix_pattern, int(lesson.fix_verified),
                        lesson.occurrence_count, stored_rate
                    ))
                    conn.commit()
                    conn.close()
                    logger.info(f"[KB-EVOLVE] New lesson saved: {lesson.lesson_id} (type={lesson.bug_type})")
                    return True
            except Exception as e:
                logger.warning(f"[KB-EVOLVE] Save lesson failed: {e}", exc_info=True)
                return False

    def lookup_lesson(self, bug_type: str, root_cause_hint: str = "") -> Lesson | None:
        """Lookup lesson by bug_type + root_cause hint. Returns most relevant."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self.db_path))
                if root_cause_hint:
                    # Fuzzy match on root_cause
                    rows = conn.execute(
                        "SELECT * FROM lessons WHERE bug_type = ? AND root_cause LIKE ? ORDER BY occurrence_count DESC LIMIT 1",
                        (bug_type, f"%{root_cause_hint[:100]}%")
                    ).fetchone()
                else:
                    rows = conn.execute(
                        "SELECT * FROM lessons WHERE bug_type = ? ORDER BY occurrence_count DESC LIMIT 1",
                        (bug_type,)
                    ).fetchone()
                conn.close()
                if rows:
                    return Lesson(
                        lesson_id=rows[0], timestamp=rows[1], bug_type=rows[2],
                        bug_file=rows[3], bug_line=rows[4], root_cause=rows[5],
                        lesson=rows[6], fix_pattern=rows[7], fix_verified=bool(rows[8]),
                        occurrence_count=rows[9], success_rate=rows[10]
                    )
            except Exception as e:
                logger.debug(f"[KB-EVOLVE] Lookup lesson failed: {e}", exc_info=True)
            return None

    def save_pattern(self, pattern: EvolvedPattern) -> bool:
        """Save an evolved pattern for scanner."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self.db_path))
                conn.execute("""
                    INSERT OR REPLACE INTO evolved_patterns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.pattern_id, pattern.timestamp, pattern.bug_type,
                    pattern.pattern_regex, pattern.pattern_description,
                    pattern.source_lesson_id, pattern.occurrence_count,
                    pattern.false_positive_count, pattern.confidence
                ))
                conn.commit()
                conn.close()
                logger.info(f"[KB-EVOLVE] Pattern saved: {pattern.pattern_id} (type={pattern.bug_type})")
                return True
            except Exception as e:
                logger.warning(f"[KB-EVOLVE] Save pattern failed: {e}", exc_info=True)
                return False

    def get_patterns(self, bug_type: str | None = None) -> list[EvolvedPattern]:
        """Get evolved patterns for a bug_type (or all if None)."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self.db_path))
                if bug_type:
                    rows = conn.execute(
                        "SELECT * FROM evolved_patterns WHERE bug_type = ? AND confidence > 0.3",
                        (bug_type,)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM evolved_patterns WHERE confidence > 0.3"
                    ).fetchall()
                conn.close()
                return [EvolvedPattern(
                    pattern_id=r[0], timestamp=r[1], bug_type=r[2],
                    pattern_regex=r[3], pattern_description=r[4],
                    source_lesson_id=r[5], occurrence_count=r[6],
                    false_positive_count=r[7], confidence=r[8]
                ) for r in rows]
            except Exception as e:
                logger.debug(f"[KB-EVOLVE] Get patterns failed: {e}", exc_info=True)
                return []

    def record_pattern_detection(self, pattern_id: str, is_false_positive: bool = False):
        """Record that a pattern was detected (increment count or FP count)."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self.db_path))
                if is_false_positive:
                    conn.execute(
                        "UPDATE evolved_patterns SET false_positive_count = false_positive_count + 1, "
                        "confidence = MAX(0.1, confidence - 0.1) WHERE pattern_id = ?",
                        (pattern_id,)
                    )
                else:
                    conn.execute(
                        "UPDATE evolved_patterns SET occurrence_count = occurrence_count + 1, "
                        "confidence = MIN(1.0, confidence + 0.05) WHERE pattern_id = ?",
                        (pattern_id,)
                    )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug(f"[KB-EVOLVE] Record detection failed: {e}", exc_info=True)

    def stats(self) -> dict:
        """Get KB accumulation stats."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self.db_path))
                lesson_count = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
                pattern_count = conn.execute("SELECT COUNT(*) FROM evolved_patterns").fetchone()[0]
                total_occurrences = conn.execute("SELECT SUM(occurrence_count) FROM lessons").fetchone()[0] or 0
                avg_success = conn.execute("SELECT AVG(success_rate) FROM lessons").fetchone()[0] or 0
                conn.close()
                return {
                    "total_lessons": lesson_count,
                    "total_patterns": pattern_count,
                    "total_occurrences": total_occurrences,
                    "avg_success_rate": round(avg_success, 3),
                    "db_path": str(self.db_path),
                }
            except Exception as e:
                logger.warning("Learning KB stats query failed: %s", e, exc_info=True)
                return {"error": str(e)}


# ============================================================
# Scanner Evolver — inject dynamic patterns into scanners
# ============================================================

class ScannerEvolver:
    """Evolve scanners with patterns from KB.

    Scanner đọc patterns từ KB (dynamic) thay vì chỉ hardcode.
    """

    # Map bug_type → scanner class
    SCANNER_MAP = {
        "RaceCondition": "race_condition_scanner",
        "NullDereference": "null_safety_scanner",
        "SQLInjectionRisk": "sql_injection_scanner",
        "TypeMismatch": "type_contract_scanner",
        "ResourceLeak": "resource_leak_scanner",
        "BareExceptPass": "ASTScanner",
        "PerformanceIssue": "performance_scanner",
    }

    def __init__(self, kb_store: KBAccumulationStore):
        self.kb = kb_store
        self._injected_patterns: dict[str, list[EvolvedPattern]] = {}

    def inject_patterns(self, bug_type: str) -> int:
        """Inject evolved patterns for a bug_type into scanner.
        Returns number of patterns injected.
        """
        patterns = self.kb.get_patterns(bug_type)
        if patterns:
            self._injected_patterns[bug_type] = patterns
            logger.info(f"[SCANNER-EVOLVE] Injected {len(patterns)} patterns for {bug_type}")
        return len(patterns)

    def get_dynamic_patterns(self, bug_type: str) -> list[EvolvedPattern]:
        """Get injected patterns for a bug_type."""
        if bug_type not in self._injected_patterns:
            self.inject_patterns(bug_type)
        return self._injected_patterns.get(bug_type, [])

    def check_code_against_patterns(self, code: str, bug_type: str) -> list[dict]:
        """Check code against evolved patterns.
        Returns list of matches.
        """
        matches = []
        patterns = self.get_dynamic_patterns(bug_type)
        for pat in patterns:
            try:
                if re.search(pat.pattern_regex, code, re.IGNORECASE | re.MULTILINE):
                    matches.append({
                        "pattern_id": pat.pattern_id,
                        "bug_type": pat.bug_type,
                        "description": pat.pattern_description,
                        "confidence": pat.confidence,
                        "source": "evolved",
                    })
                    # Record detection
                    self.kb.record_pattern_detection(pat.pattern_id)
            except re.error as exc:
                # silent-by-design: invalid regex patterns are skipped so one bad KB entry cannot abort matching.
                logger.debug("kb_evolve: invalid regex skipped: %s", exc, exc_info=True)
                continue  # Skip invalid regex
        return matches

    def stats(self) -> dict:
        """Get scanner evolver stats."""
        return {
            "injected_bug_types": len(self._injected_patterns),
            "total_injected_patterns": sum(len(p) for p in self._injected_patterns.values()),
            "kb_stats": self.kb.stats(),
        }


# ============================================================
# Lesson Extractor — extract lesson from reflect result
# ============================================================

def extract_lesson_from_reflect(reflect_result, fix_verified: bool = False) -> Lesson | None:
    """Extract a Lesson from a ReflectResult.

    Args:
        reflect_result: ReflectResult from evolution.py reflect()
        fix_verified: Whether _verify_fix passed

    Returns:
        Lesson object, or None if reflect was self_falsified
    """
    if reflect_result.self_falsified:
        return None  # WHY rejected — don't learn

    # [V10.1-FIX] TẠI SAO: was `if not lesson_learned: return None`
    # → 4/6 reflects had empty lesson (LLM rate limit) → 0 saved to KB.
    # Fix: if lesson_learned empty or contains search-replace block (<<<<<<<),
    # generate fallback lesson from bug_type + file + line.
    lesson_text = reflect_result.lesson_learned or ""

    # Filter out search-replace blocks (LLM returned <<<<<<< OLD instead of lesson)
    if lesson_text.startswith("<<<<<<<") or lesson_text.startswith("======="):
        lesson_text = ""  # Not a real lesson — search-replace block

    if not lesson_text:
        # [V10.1-FIX] Fallback lesson — save even when LLM didn't provide
        lesson_text = f"Bug {reflect_result.bug_type} fixed at {reflect_result.bug_file}:{reflect_result.bug_line}"

    # Root cause: use why_necessity if available (not search-replace), else lesson_text
    root_cause = reflect_result.why_necessity or ""
    if root_cause.startswith("<<<<<<<") or root_cause.startswith("======="):
        root_cause = lesson_text  # Fallback
    if not root_cause:
        root_cause = lesson_text

    # Generate lesson ID
    lesson_id = hashlib.sha256(
        f"{reflect_result.bug_type}:{lesson_text[:200]}".encode()
    ).hexdigest()[:16]

    return Lesson(
        lesson_id=lesson_id,
        timestamp=time.time(),
        bug_type=reflect_result.bug_type,
        bug_file=reflect_result.bug_file,
        bug_line=reflect_result.bug_line,
        root_cause=root_cause[:200],
        lesson=lesson_text[:500],
        fix_pattern=reflect_result.suggested_pattern[:200] if reflect_result.suggested_pattern else "",
        fix_verified=fix_verified,
    )


def extract_pattern_from_lesson(lesson: Lesson) -> EvolvedPattern | None:
    """Extract an EvolvedPattern from a Lesson.
    Returns None if no pattern can be extracted.
    """
    if not lesson.fix_pattern:
        return None

    # Generate pattern ID
    pattern_id = hashlib.sha256(
        f"{lesson.bug_type}:{lesson.fix_pattern[:100]}".encode()
    ).hexdigest()[:16]

    return EvolvedPattern(
        pattern_id=pattern_id,
        timestamp=time.time(),
        bug_type=lesson.bug_type,
        pattern_regex=lesson.fix_pattern,  # Use fix_pattern as regex
        pattern_description=f"Evolved from lesson: {lesson.lesson[:100]}",
        source_lesson_id=lesson.lesson_id,
        confidence=0.5,  # Initial low confidence
    )


# ============================================================
# Singleton
# ============================================================
_kb_store: KBAccumulationStore | None = None
_scanner_evolver: ScannerEvolver | None = None
_kb_lock = threading.Lock()

def get_kb_store(data_dir: str = "data") -> KBAccumulationStore:
    """Get singleton KBAccumulationStore."""
    global _kb_store
    if _kb_store is None:
        with _kb_lock:
            if _kb_store is None:
                _kb_store = KBAccumulationStore(data_dir=data_dir)
                logger.info("[KB-EVOLVE] KBAccumulationStore initialized")
    return _kb_store

def get_scanner_evolver() -> ScannerEvolver:
    """Get singleton ScannerEvolver."""
    global _scanner_evolver
    if _scanner_evolver is None:
        with _kb_lock:
            if _scanner_evolver is None:
                _scanner_evolver = ScannerEvolver(get_kb_store())
                logger.info("[SCANNER-EVOLVE] ScannerEvolver initialized")
    return _scanner_evolver
