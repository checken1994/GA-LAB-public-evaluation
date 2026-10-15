"""[F-M1 / GAP-03 + GAP-04] Lesson verification truthfulness pins.

Poisoning chain đã audit:
  producer: ``reflectmixin.py`` truyền ``fix_verified=True`` CỨNG vào
  ``extract_lesson_from_reflect``; ``Lesson.success_rate`` default 1.0
  -> lesson CHƯA verify vào KB với success_rate=1.0 + fix_verified=1
  -> consumer ``history/migration.py`` nhét vào ``verified_lesson_candidates``
     (filter: fix_verified==1 AND success_rate>=0.8) -> Knowledge Poisoning.

Contract sau fix (producer side — consumer là scope của agent khác):
  - ``Lesson.success_rate`` default 0.0;
  - KB store coerce unverified lesson về rate 0.0 (insert), đóng góp 0.0
    (update);
  - ``fix_verified=True`` CHỈ khi có receipt verification thật:
    ``reality_test_result == "pass"`` VÀ ``post_fix_verification.ok is True``;
  - lesson chưa verify KHÔNG bao giờ đạt ngưỡng verified_lesson_candidates.
"""
from __future__ import annotations

import sqlite3

import pytest

# Import qua ``scp.autofix.evolution`` trước: reflectmixin <-> evolution có
# circular import ở mức module — đúng thứ tự nạp của production là evolution
# (nơi gắn mixin vào EvolutionEngine).
import scp.autofix.evolution  # noqa: F401  # khởi tạo mixin wiring
from scp.autofix.evolution_parts.reflectmixin import _fix_verification_receipt
from scp.meta.kb_evolve import KBAccumulationStore, Lesson, extract_lesson_from_reflect

# Threshold của consumer history/migration.py (pin hai phía — nếu consumer đổi
# ngưỡng, test này phải được cập nhật có chủ đích, không âm thầm).
_CANDIDATE_MIN_RATE = 0.8


def _make_lesson(tmp_name: str, *, fix_verified: bool,
                 success_rate: float | None = None) -> Lesson:
    return Lesson(
        lesson_id=f"les-{tmp_name}",
        timestamp=1_700_000_000.0,
        bug_type="BareExceptPass",
        bug_file="scp/demo.py",
        bug_line=10,
        root_cause=f"root cause {tmp_name}",
        lesson=f"lesson {tmp_name}",
        fix_pattern="replace pass with logging",
        fix_verified=fix_verified,
        occurrence_count=1,
        **({} if success_rate is None else {"success_rate": success_rate}),
    )


# ---------------------------------------------------------------
# GAP-03: success_rate default fail-closed
# ---------------------------------------------------------------

def test_lesson_default_success_rate_is_zero():
    lesson = Lesson(
        lesson_id="l", timestamp=0.0, bug_type="t", bug_file="f",
        bug_line=1, root_cause="r", lesson="l", fix_pattern="p",
        fix_verified=False,
    )
    assert lesson.success_rate == 0.0, (
        "default 1.0 = poisoning: lesson chưa verify tự đạt ngưỡng candidate"
    )


def test_unverified_lesson_stored_with_zero_rate_despite_forced_high(tmp_path):
    """Producer lỡ truyền success_rate=1.0 cho lesson chưa verify -> KB vẫn 0.0."""
    store = KBAccumulationStore(data_dir=str(tmp_path))
    lesson = _make_lesson("u1", fix_verified=False, success_rate=1.0)
    assert store.save_lesson(lesson) is True

    with sqlite3.connect(store.db_path) as conn:
        row = conn.execute(
            "SELECT fix_verified, success_rate FROM lessons WHERE lesson_id=?",
            ("les-u1",),
        ).fetchone()
    assert row == (0, 0.0)


def test_verified_lesson_keeps_its_rate(tmp_path):
    store = KBAccumulationStore(data_dir=str(tmp_path))
    lesson = _make_lesson("v1", fix_verified=True, success_rate=0.9)
    assert store.save_lesson(lesson) is True

    with sqlite3.connect(store.db_path) as conn:
        row = conn.execute(
            "SELECT fix_verified, success_rate FROM lessons WHERE lesson_id=?",
            ("les-v1",),
        ).fetchone()
    assert row == (1, 0.9)


def test_update_path_unverified_occurrence_drags_rate_down(tmp_path):
    """Nhánh UPDATE: unverified occurrence đóng góp 0.0 — không nâng rate."""
    store = KBAccumulationStore(data_dir=str(tmp_path))
    store.save_lesson(_make_lesson("dup", fix_verified=True, success_rate=0.9))
    # same root_cause -> UPDATE branch; occurrence mới CHƯA verify
    store.save_lesson(_make_lesson("dup", fix_verified=False))

    with sqlite3.connect(store.db_path) as conn:
        rate, count = conn.execute(
            "SELECT success_rate, occurrence_count FROM lessons WHERE lesson_id=?",
            ("les-dup",),
        ).fetchone()
    assert count == 2
    assert rate == pytest.approx(0.45)  # (0.9*1 + 0.0) / 2 -> dưới ngưỡng 0.8


def test_unverified_lesson_never_enters_verified_candidates(tmp_path):
    """Pin GAP-03 end-to-end ở producer boundary: lọc đúng như consumer."""
    store = KBAccumulationStore(data_dir=str(tmp_path))
    store.save_lesson(_make_lesson("poison", fix_verified=False, success_rate=1.0))
    store.save_lesson(_make_lesson("honest", fix_verified=True, success_rate=0.9))

    with sqlite3.connect(store.db_path) as conn:
        rows = conn.execute("SELECT lesson_id, fix_verified, success_rate FROM lessons").fetchall()
    candidates = [
        r[0] for r in rows
        if int(r[1] or 0) == 1 and float(r[2] or 0) >= _CANDIDATE_MIN_RATE
    ]
    assert candidates == ["les-honest"]


# ---------------------------------------------------------------
# GAP-04: fix_verified chỉ True khi có receipt verification thật
# ---------------------------------------------------------------

def _receipt(*, action="fixed", reality="pass", pfv_ok=True) -> dict:
    return {
        "action": action,
        "reality_test_result": reality,
        "post_fix_verification": {"ok": pfv_ok, "phases": {"import": {"ok": True}}},
    }


def test_receipt_true_only_with_both_verification_layers():
    assert _fix_verification_receipt(_receipt()) is True


@pytest.mark.parametrize("receipt", [
    {},                                   # không receipt nào
    None,                                 # không phải dict
    {"action": "fixed"},                  # thiếu cả 2 tầng
    _receipt(action="skipped"),           # chưa fix -> không verify
    _receipt(reality="skipped"),          # reality test bị skip
    _receipt(reality="fail:assert"),      # reality test fail
    _receipt(reality=None),               # receipt Tier 3 cũ: không reality
    _receipt(pfv_ok=False),               # post-fix verify từ chối
    _receipt(pfv_ok=None),                # post-fix verify UNKNOWN
    {"action": "fixed", "reality_test_result": "pass"},  # thiếu pfv
])
def test_receipt_false_without_genuine_verification(receipt):
    """Mọi trạng thái thiếu/chỉnh chứng minh verification -> fix_verified=False."""
    assert _fix_verification_receipt(receipt) is False


def test_extract_lesson_respects_explicit_false():
    """extract_lesson_from_reflect nhận fix_verified=False (không hardcode)."""
    result = SimpleReflect(self_falsified=False, lesson_learned="log instead of pass")
    lesson = extract_lesson_from_reflect(result, fix_verified=False)
    assert lesson is not None
    assert lesson.fix_verified is False
    assert lesson.success_rate == 0.0


class SimpleReflect:
    """ReflectResult-lite — đủ contract mà extract_lesson_from_reflect đọc."""

    def __init__(self, *, self_falsified: bool, lesson_learned: str):
        from scp.autofix.evolution import ReflectResult
        self._rr = ReflectResult(
            bug_file="scp/demo.py", bug_line=10, bug_type="BareExceptPass",
            fix_diff="", why_necessity="silent except hides failure",
            why_falsification="logging preserves behavior", self_falsified=self_falsified,
            lesson_learned=lesson_learned,
        )

    def __getattr__(self, name):
        return getattr(self._rr, name)
