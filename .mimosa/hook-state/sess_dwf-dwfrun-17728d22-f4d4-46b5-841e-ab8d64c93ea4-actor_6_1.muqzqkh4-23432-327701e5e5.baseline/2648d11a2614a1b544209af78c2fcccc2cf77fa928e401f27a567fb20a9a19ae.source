"""P1: Golden Task Runtime Evidence — wrapper THẬT (A13b H-02 remediation).

Lịch sử: file này trước đây là placebo — print "Startup OK. Planning OK..."
+ exit 0 mà KHÔNG chạy bất kỳ golden flow nào (mạo danh golden evidence,
vi phạm FA-04). Đã được thay bằng wrapper GỌI golden flow thật của T09.

Golden flow thật: ``tests/T09_golden_task/test_golden_a_agent_os.py`` —
C-level real production path: TaskKernelHandsBridge -> HandsExecutor ->
PCController -> filesystem thật, với kernel lifecycle đầy đủ (create ->
lease -> start -> idempotency claim -> checkpoint -> dispatch -> verify ->
commit) và post-state được thẩm định bởi IndependentVerifier. KHÔNG có stub
thay thế bất kỳ boundary component nào.

Contract: exit code của pytest là bằng chứng DUY NHẤT. Golden flow thất bại
-> wrapper exit non-zero kèm hướng dẫn truy vết (fail-loud). Không còn
print-pass nào ở đây.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_A_NODE = (
    "tests/T09_golden_task/test_golden_a_agent_os.py"
    "::test_golden_a_agent_os_real_execution_flow"
)


def run_golden() -> int:
    """Dispatch golden flow thật qua subprocess pytest và trả về exit code.

    Subprocess cách ly: golden A tự quản tmp_path của riêng nó; basetemp riêng
    tránh junction ``pytest-current`` hỏng trên máy host. Wrapper KHÔNG tự
    diễn giải kết quả — pytest exit code 0 = PASS, bất kỳ giá trị khác = FAIL.
    """
    cmd = [
        sys.executable, "-m", "pytest", GOLDEN_A_NODE,
        "-q", "--no-header", "-p", "no:cacheprovider",
    ]
    print(f"[golden_task] dispatching real golden flow: {GOLDEN_A_NODE}")
    basetemp = tempfile.mkdtemp(prefix="golden_task_basetemp_")
    try:
        completed = subprocess.run(
            [*cmd, f"--basetemp={basetemp}/bt"], cwd=str(REPO_ROOT)
        )
    finally:
        shutil.rmtree(basetemp, ignore_errors=True)
    if completed.returncode != 0:
        print(
            f"[golden_task] GOLDEN FLOW FAILED (pytest exit {completed.returncode}). "
            f"Reproduce with full trace: python -m pytest {GOLDEN_A_NODE} -v",
            file=sys.stderr,
        )
    return completed.returncode


if __name__ == "__main__":
    sys.exit(run_golden())
