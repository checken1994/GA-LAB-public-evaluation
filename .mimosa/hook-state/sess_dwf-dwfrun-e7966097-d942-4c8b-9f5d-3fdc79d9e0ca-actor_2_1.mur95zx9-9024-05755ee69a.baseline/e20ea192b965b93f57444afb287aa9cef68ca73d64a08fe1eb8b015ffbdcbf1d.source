"""Sandbox Evaluator — chạy pytest THẬT trên bản sao workspace (Track C3).

ADOPT-AND-FIX Track C3 + V2 P4: "Autofix không tự chấm bài". Bộ autofix trước
đây chỉ tự chấm bằng ``ast.parse``/grep (static). Module này tách việc chấm ra:
evaluate() copy file đích + test files vào một workspace tạm **ngoài repo**
(system temp), chạy ``pytest`` thật qua subprocess (shell=False, timeout bắt
buộc), và trả về raw stdout/stderr + returncode + verdict.

Invariant fail-closed (DNA #22 — "không chạy được" ≠ "đậu"):

- PASS **chỉ khi** ``returncode == 0`` sau khi pytest thật sự chạy.
- Timeout -> FAIL(reason="timeout"); setup lỗi -> FAIL(reason="setup:...").
- pytest exit 5 (no tests collected) -> FAIL (reality-verifier: "no tests ran"
  is not PASS).
- Không bao giờ trả PASS khi test không chạy được.

Security invariants:

- ``shell=False`` luôn luôn (command là list, không qua shell).
- Workspace nằm trong system temp (``tempfile.mkdtemp``), KHÔNG chạy trên repo sống.
- Env của subprocess là **allowlist tối thiểu** — không kế thừa env nhạy cảm.
- Timeout clamp trong khoảng [5, 900] giây ở mọi đường nhập.
"""

from scp.sandbox_evaluator.evaluator import (
    CHANNEL_EVAL,
    EVENT_EVAL_REQUEST,
    EVENT_EVAL_RESULT,
    EvalResult,
    evaluate,
    sandbox_enabled,
)

__all__ = [
    "CHANNEL_EVAL",
    "EVENT_EVAL_REQUEST",
    "EVENT_EVAL_RESULT",
    "EvalResult",
    "evaluate",
    "sandbox_enabled",
]
