"""Chaos recovery (Cổng F/C): kill -9 THẬT giữa luồng, boot lại, máy phải
tự replay journal và đưa task về trạng thái an toàn. Không phải mô phỏng —
process con bị TerminateProcess thật."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scp.task_kernel import TaskKernel

CHILD_SCRIPT = r"""
import sys, time
sys.path.insert(0, r"{root}")
from scp.task_kernel import TaskKernel

kernel = TaskKernel(r"{db}")
kernel.create_task("chaos-1", "chaos-worker", "write report to disk", "R2", deadline_ms=600000)
kernel.transition("chaos-1", "PLANNING", actor="chaos", reason="plan")
kernel.transition("chaos-1", "READY", actor="chaos", reason="ready")
kernel.transition("chaos-1", "QUEUED", actor="chaos", reason="queue")
lease = kernel.claim("chaos-1", "chaos-worker", ttl_seconds=300)
kernel.start("chaos-1", lease.lease_id)
kernel.idempotency_claim("chaos-1", "step-1", "fs.write", "report.doc")
print("CHILD_READY", flush=True)
time.sleep(120)  # parent sẽ kill -9 tại đây
"""


def test_hard_kill_then_boot_recovery_replays_journal(tmp_path):
    root = str(Path(__file__).resolve().parents[2])
    db = str(tmp_path / "chaos.sqlite3")
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", "-c", CHILD_SCRIPT.format(root=root, db=db)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
    )
    try:
        line = proc.stdout.readline()
        assert "CHILD_READY" in line, f"child failed to reach RUNNING: {line}"
        proc.kill()  # kill -9 thật (Windows: TerminateProcess)
        proc.wait(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()

    # Process đã CHẾT GIỮA LUỒNG với task đang RUNNING. Boot lại:
    kernel = TaskKernel(db)
    before = kernel.get_task("chaos-1")
    assert before["state"] == "RUNNING", "journal phải giữ đúng trạng thái lúc chết"

    report = kernel.recover_on_boot()
    assert not report["corrupted"], f"journal bị hỏng: {report['corrupted']}"
    assert any(r["task_id"] == "chaos-1" and r["to"] == "HUMAN_REVIEW" for r in report["recovered"])
    assert kernel.get_task("chaos-1")["state"] == "HUMAN_REVIEW"

    # Hash-chain journal phải còn nguyên sau recovery (bằng chứng không phản bác)
    verification = kernel.verify_journal("chaos-1")
    assert verification["hash_chain_valid"] is True


def test_recover_on_boot_never_tamperes_corrupted_journal(tmp_path):
    db = str(tmp_path / "corrupt.sqlite3")
    kernel = TaskKernel(db)
    kernel.create_task("victim-1", "op", "goal", "R0")
    kernel.transition("victim-1", "PLANNING", actor="op", reason="plan")
    # Giả mock tấn công: sửa payload sau khi ghi → hash-chain lệch.
    kernel.conn.execute("UPDATE events SET reason='tampered' WHERE task_id='victim-1' AND seq=1")
    report = kernel.recover_on_boot()
    assert any(c["task_id"] == "victim-1" for c in report["corrupted"])
    # Task KHÔNG bị tự ý sửa khi bằng chứng hỏng (fail-closed với bằng chứng)
    assert kernel.get_task("victim-1")["state"] == "PLANNING"
