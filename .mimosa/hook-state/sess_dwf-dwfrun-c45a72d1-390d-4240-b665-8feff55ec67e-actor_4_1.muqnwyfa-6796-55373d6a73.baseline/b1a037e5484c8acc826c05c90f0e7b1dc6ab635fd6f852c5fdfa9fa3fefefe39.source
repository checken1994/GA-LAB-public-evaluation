"""[SANDBOX-SKIP] Regression tests — realtime sandbox-incompatible semantics.

Bối cảnh: realtime_verifier fail-closes trên RestrictedSourceError (source
không thể COMPILE trong sandbox bị giới hạn — ví dụ mọi source gọi builtin
``open``). Đúng theo fail-closed, NHƯNG khi các layer còn lại (shadow canary
+ post_fix_verify) thực sự chạy được và verify thật, một patch hành xử đúng
bị chặn oan → golden B chết ở 2 node.

Hợp đồng mới (orchestrator-approved, FAIL-CLOSED vẫn là mặc định):
  1. realtime_verifier đánh dấu ``sandbox_incompatible=True`` CHỈ trên nhánh
     RestrictedSourceError (ok vẫn False — không tự ân xá).
  2. Mixin chỉ tiếp tục pipeline khi canary GENUINELY PASSED trong cùng run
     (ctx.v4_shadow_result.passed — bằng chứng verify hành vi đã thực thi);
     khi đó result dict phải mang ``realtime_skipped=True`` (skip nhìn thấy
     được, không phải pass im lặng).
  3. Canary không pass / không chạy → vẫn chặn (realtime_blocked).
  4. Verdict thường (ok / violation) không đổi.

Causal matrix (FA-13) cho 2 file sửa:
  scp/autofix/realtime_verifier.py
    B1 RestrictedSourceError leg        -> ok=False + sandbox_incompatible=True
                                           (test_b + test_a end-to-end)
    B2 executable ok leg                -> ok=True, sandbox_incompatible=False
                                           (test_c)
    B3 executable violation leg         -> ok=False, sandbox_incompatible=False
                                           (test_d)
    B4 các nhánh fail khác              -> sandbox_incompatible=False (đã phủ
                                           bởi test_autofix_realtime_verifier_
                                           failclosed.py — chạy cùng T07)
  scp/autofix/engine_parts/autofix_mixin.py
    M1 sandbox_incompatible + canary passed     -> proceed + realtime_skipped
                                                   (test_a, engine-level)
    M2 sandbox_incompatible + canary None/False -> block realtime_blocked
                                                   (test_b, gate-level)
    M3 verdict ok thường                        -> không đổi (test_c)
    M4 verdict violation thường                 -> block không đổi (test_d)

Không skip/xfail, không mock verdict — engine-level chạy stack gate thật.
"""
from __future__ import annotations

import ast
from types import SimpleNamespace

from scp.autofix.bug_report_validator import validate_findings
from scp.autofix.engine import AutoFixEngine
from scp.autofix.engine_parts.context import FixContext
from scp.autofix.realtime_verifier import verify_patch_realtime
from scp.autofix.runner_phases.ast_scan import _build_bug_report, _scan_file

# Source GỐC của golden B: gọi builtin `open` → sandbox không compile được
# (open nằm trong _FORBIDDEN_CALLS) → orig leg RestrictedSourceError.
BUGGY_SOURCE = (
    "def load_text(path):\n"
    "    try:\n"
    "        with open(path, encoding=\"utf-8\") as handle:\n"
    "            return handle.read()\n"
    "    except:\n"
    "        pass\n"
)

# Fix bảo toàn hợp đồng canary VÀ phân biệt được ở seeded replay:
#   - shadow canary (smoke_call) chỉ so sánh EXCEPTION SIGNATURE —
#     `except Exception` bắt đúng những input mà bare clause bắt (mọi
#     KeyboardInterrupt/SystemExit-class đều ngoài tầm các suite deterministic)
#     → signature list giống hệt → canary GENUINELY PASSED.
#   - seeded evidence_replay YÊU CẦU khác biệt observable: `return None` tái
#     tạo đúng implicit-None của state buggy → "cannot discriminate" →
#     fail-closed UNVERIFIED (đã chứng minh thực nghiệm 2026-09-26). Explicit
#     `return ""` cho replay một discriminator thật mà vẫn sạch với canary.
GOOD_FIX = (
    "<<<<<<< SEARCH\n"
    "    except:\n"
    "        pass\n"
    "=======\n"
    "    except Exception:\n"
    "        return \"\"\n"
    ">>>>>>> REPLACE\n"
)

# Source COMPATIBLE (không open/import/class): cả hai leg compile + chạy được
# trong sandbox → realtime verifier ra VERDICT THẬT (không phải skip).
COMPATIBLE_SOURCE = (
    "def coerce(value):\n"
    "    try:\n"
    "        return int(value)\n"
    "    except:\n"
    "        pass\n"
)

COMPATIBLE_GOOD_FIX = GOOD_FIX  # cùng shape, bảo toàn hành vi trên int-coerce

# Patch hijack kiểu trả về trên source COMPATIBLE → violation thường.
COMPATIBLE_TYPE_HIJACK_FIX = (
    "<<<<<<< SEARCH\n"
    "        return int(value)\n"
    "=======\n"
    "        return str(int(value))\n"
    ">>>>>>> REPLACE\n"
)


def _seed(tmp_path, source: str):
    """Seed workspace + scan + validate (same contract as golden B seeding)."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "util.py"
    # LF cố ý: SEARCH/REPLACE blocks là LF-based (fixture artifact, not product).
    target.write_text(source, encoding="utf-8", newline="\n")

    findings = _scan_file(target)
    assert any(f["bug_type"] == "BareExceptPass" for f in findings), (
        f"Scanner missed the seeded BareExceptPass anomaly: {findings}"
    )
    reports = [_build_bug_report(str(target), f) for f in findings]
    validated = validate_findings(reports)
    bug = next(b for b in validated if b.bug_type == "BareExceptPass")
    return target, bug


def test_a_sandbox_incompatible_with_canary_passed_proceeds(tmp_path, monkeypatch):
    """(a) sandbox-incompatible + canary GENUINELY PASSED → pipeline proceeds,
    result mang realtime_skipped=True (skip nhìn thấy được, không phải pass)."""
    target, bug = _seed(tmp_path, BUGGY_SOURCE)
    bug.suggested_fix = GOOD_FIX

    # Pin WHY gate về deterministic + seed gold evidence để commit leg chạy
    # hết pipeline (same contract as golden B commit leg).
    monkeypatch.setenv("SCP_WHY_LLM_ENABLED", "0")
    monkeypatch.setenv("SCP_SEED_GOLD_EVIDENCE", "1")

    engine = AutoFixEngine(str(tmp_path / "autofix-data"))
    result = engine.process_bug(bug)

    assert result.get("action") == "fixed", (
        f"Sandbox-incompatible patch with a genuinely-passed canary was not "
        f"allowed to proceed: {result}"
    )
    assert result.get("realtime_skipped") is True, (
        f"The visible realtime skip marker is missing on the eventual result: "
        f"{result}"
    )
    assert result.get("realtime_blocked") is not True, result
    assert "except Exception:" in target.read_text(encoding="utf-8"), (
        "Pipeline proceeded but the fix never landed in the file"
    )


def test_b_sandbox_incompatible_without_canary_pass_still_blocks(tmp_path):
    """(b) sandbox-incompatible + canary KHÔNG pass (unavailable hoặc failed)
    → vẫn block (realtime_blocked). Không bao giờ promote khi không có ít
    nhất MỘT layer verification thực sự chạy."""
    # B1: verifier phải đánh dấu explicitly (không tồn tại trên code cũ →
    # test này FAIL trên code cũ, PASS trên code mới).
    result = verify_patch_realtime(
        BUGGY_SOURCE,
        BUGGY_SOURCE.replace("    except:\n        pass",
                             "    except Exception:\n        return None"),
        func_name="load_text",
    )
    assert result.ok is False, "sandbox-incompatible check must stay fail-closed"
    assert result.sandbox_incompatible is True, (
        f"RestrictedSourceError leg must set the explicit marker: {result}"
    )
    assert any(v.startswith("sandbox_incompatible_source_") for v in result.violations)

    target, bug = _seed(tmp_path, BUGGY_SOURCE)
    bug.suggested_fix = GOOD_FIX
    engine = AutoFixEngine(str(tmp_path / "autofix-data"))

    # M2 case 1 — canary UNAVAILABLE (chưa từng chạy: ctx.v4_shadow_result=None).
    ctx = FixContext(bug=bug, filepath=target, report=False, attack_mode=False)
    ctx.pre_fix_content = BUGGY_SOURCE
    ctx.v4_shadow_result = None
    blocked = engine._auto_fix_part3(ctx)
    assert blocked is not None and blocked.get("action") == "skipped", blocked
    assert blocked.get("realtime_blocked") is True, blocked
    assert "realtime_verifier" in blocked.get("reason", ""), blocked
    assert blocked.get("realtime_skipped") is not True, blocked

    # M2 case 2 — canary CHẠY THẬT nhưng FAILED (passed=False) → vẫn block.
    ctx_failed = FixContext(bug=bug, filepath=target, report=False, attack_mode=False)
    ctx_failed.pre_fix_content = BUGGY_SOURCE
    ctx_failed.v4_shadow_result = SimpleNamespace(
        passed=False, reason="smoke_call regression", tests_run=6, diffs=["x"]
    )
    blocked_failed = engine._auto_fix_part3(ctx_failed)
    assert blocked_failed is not None and blocked_failed.get("action") == "skipped", (
        blocked_failed
    )
    assert blocked_failed.get("realtime_blocked") is True, blocked_failed

    # Gate block phải không đụng vào file (block TRƯỚC write).
    assert target.read_text(encoding="utf-8") == BUGGY_SOURCE


def test_c_normal_verifier_ok_path_unchanged(tmp_path, monkeypatch):
    """(c) Verdict ok THƯỜNG (source executable) giữ nguyên hành vi: verify
    bằng input thật, KHÔNG mang marker skip, KHÔNG bị block."""
    result = verify_patch_realtime(
        "def f(x):\n    return x + 1\n",
        "def f(x):\n    return x + 2\n",
        func_name="f",
    )
    assert result.ok is True, result.reason
    assert result.inputs_tested > 0
    assert result.sandbox_incompatible is False, (
        "A real executed verdict must NOT carry the sandbox marker"
    )

    # Engine-level: source compatible → realtime OK → proceed như cũ, không
    # có realtime_skipped lẫn realtime_blocked trên result.
    target, bug = _seed(tmp_path, COMPATIBLE_SOURCE)
    bug.suggested_fix = COMPATIBLE_GOOD_FIX
    monkeypatch.setenv("SCP_WHY_LLM_ENABLED", "0")
    monkeypatch.setenv("SCP_SEED_GOLD_EVIDENCE", "1")

    engine = AutoFixEngine(str(tmp_path / "autofix-data"))
    engine_result = engine.process_bug(bug)
    assert engine_result.get("action") == "fixed", (
        f"Normal realtime-OK path regressed: {engine_result}"
    )
    assert engine_result.get("realtime_skipped") is not True, engine_result
    assert engine_result.get("realtime_blocked") is not True, engine_result
    assert "except Exception:" in target.read_text(encoding="utf-8")


def test_d_normal_verifier_violation_still_blocks(tmp_path):
    """(d) Verdict violation THƯỜNG (type hijack trên source executable) vẫn
    block — nhánh skip mới không được phép thấm sang violation thường."""
    result = verify_patch_realtime(
        "def f(x):\n    return x + 1\n",
        "def f(x):\n    return str(x)\n",
        func_name="f",
    )
    assert result.ok is False, "return-type hijack must stay blocked"
    assert result.sandbox_incompatible is False, (
        f"A real executed violation is NOT a sandbox-incompatibility: {result}"
    )

    # Gate-level: kể cả khi canary state cho phép, violation thường phải block.
    target, bug = _seed(tmp_path, COMPATIBLE_SOURCE)
    bug.suggested_fix = COMPATIBLE_TYPE_HIJACK_FIX
    engine = AutoFixEngine(str(tmp_path / "autofix-data"))
    ctx = FixContext(bug=bug, filepath=target, report=False, attack_mode=False)
    ctx.pre_fix_content = COMPATIBLE_SOURCE
    ctx.v4_shadow_result = SimpleNamespace(passed=True, reason="canary ok", tests_run=6, diffs=[])
    blocked = engine._auto_fix_part3(ctx)
    assert blocked is not None and blocked.get("action") == "skipped", blocked
    assert blocked.get("realtime_blocked") is True, blocked
    assert blocked.get("realtime_skipped") is not True, blocked
    assert target.read_text(encoding="utf-8") == COMPATIBLE_SOURCE, (
        "Blocked patch must not touch the file"
    )


# [FA-13 sanity] fix text của GOOD_FIX phải tự parse được (fixture hygiene).
def test_good_fix_fixture_is_valid_python():
    patched = BUGGY_SOURCE.replace(
        "    except:\n        pass", "    except Exception:\n        return None"
    )
    ast.parse(patched, filename="good_fix_fixture_preview.py")
    assert "except Exception:" in patched
