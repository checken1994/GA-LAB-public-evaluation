# SCP CIRCUIT: M12 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M12-closure.json)
"""
Mảnh ghép #11 — Cronjob of Doubt: vòng nghi ngờ TỰ KÍCH HOẠT.

TẠI SAO tồn tại (Chain Audit #11): SCP không hề tự kích hoạt vòng kiểm
toán — nó cần "Gà" gõ phím "Tôi không tin". Sự tự chủ đó là giả tạo: nếu
người vận hành biến mất, hệ thống dừng lại và tự huyễn hoặc rằng nó đã
hoàn hảo. Cronjob of Doubt là ngọn lửa "Nghi ngờ mặc định" chạy nền: ĐỊNH
KỲ tự bóc trần chính nó theo 4 phép kiểm không xin phép:

  1. FITNESS DRIFT  — Golden Suite chạy lại: accuracy có tụt so với baseline
     không? (tiến hóa mù = random mutation, DNA #22)
  2. KERNEL INTEGRITY — quick_check + hash-chain toàn bộ journal còn nguyên?
  3. ESCALATION BACKLOG — bao nhiêu task đang kẹt HUMAN_REVIEW/UNKNOWN?
     (ngập lụt review là dấu hiệu tầng verification đang ốm)
  4. WHY GATE ANOMALY — tỉ lệ REJECT gần đây có bất thường không?

Fail-safe: mỗi check bọc try/except riêng — một check lỗi không chết vòng;
mọi kết quả (kể cả lỗi) ghi vào data/doubt_ledger.jsonl làm bằng chứng.
Khác mảnh #53: KHÔNG tự inject lỗi — chỉ đo lường và BÁO CÁO cho người.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.core.doubt_cron")

DOUBT_LEDGER_DEFAULT = Path("data") / "doubt_ledger.jsonl"


def _check_fitness(data_dir: str) -> dict[str, Any]:
    from scp.core.fitness_engine import gate, load_baseline, run_suite

    report = run_suite()
    prev = load_baseline()
    verdict = gate(prev, report)
    return {
        "check": "fitness_drift",
        "ok": verdict["verdict"] != "ROLLBACK",
        "detail": {
            "accuracy": report["decision_accuracy"],
            "false_accept_rate": report["false_accept_rate"],
            "avg_decision_ms": report["avg_decision_ms"],
            "verdict": verdict["verdict"],
            "reasons": verdict["reasons"],
        },
    }


def _check_kernel_integrity(data_dir: str) -> dict[str, Any]:
    db_path = Path(data_dir) / "ask_task_kernel.sqlite3"
    if not db_path.exists():
        return {"check": "kernel_integrity", "ok": True, "detail": "no kernel db yet"}
    from scp.task_kernel import TaskKernel

    kernel = TaskKernel(db_path)
    try:
        integrity = kernel.verify_integrity()
        ok = integrity["quick_check"] == "ok" and not integrity["invalid_chains"]
        return {"check": "kernel_integrity", "ok": ok, "detail": integrity}
    finally:
        kernel.close()


def _check_escalation_backlog(data_dir: str) -> dict[str, Any]:
    db_path = Path(data_dir) / "ask_task_kernel.sqlite3"
    if not db_path.exists():
        return {"check": "escalation_backlog", "ok": True, "detail": "no kernel db yet"}
    from scp.task_kernel import TaskKernel

    kernel = TaskKernel(db_path)
    try:
        stuck = kernel.conn.execute(
            "SELECT state, COUNT(*) AS n FROM tasks WHERE state IN ('HUMAN_REVIEW','UNKNOWN','RECONCILING') GROUP BY state"
        ).fetchall()
        backlog = {row["state"]: row["n"] for row in stuck}
        total = sum(backlog.values())
        # Ngưỡng cảnh báo: >500 task kẹt = tầng verification đang ốm
        return {
            "check": "escalation_backlog",
            "ok": total <= int(os.environ.get("SCP_DOUBT_BACKLOG_LIMIT", "500")),
            "detail": {"backlog": backlog, "total": total},
        }
    finally:
        kernel.close()


def _check_why_gate_anomaly(data_dir: str) -> dict[str, Any]:
    audit_path = Path(data_dir) / "why_gate_audit.jsonl"
    if not audit_path.exists():
        return {"check": "why_gate_anomaly", "ok": True, "detail": "no audit yet"}
    lines = audit_path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]
    reject = sum(1 for line in lines if '"decision": "REJECT"' in line)
    total = len(lines)
    reject_rate = reject / total if total else 0.0
    return {
        "check": "why_gate_anomaly",
        "ok": reject_rate <= 0.5,
        "detail": {"recent": total, "reject": reject, "reject_rate": round(reject_rate, 3)},
    }


CHECKS: tuple[Callable[[str], dict[str, Any]], ...] = (
    _check_fitness,
    _check_kernel_integrity,
    _check_escalation_backlog,
    _check_why_gate_anomaly,
)


def run_doubt_cycle(data_dir: str = "data") -> dict[str, Any]:
    """Chạy 1 vòng nghi ngờ đầy đủ. Không bao giờ raise (fail-safe per check)."""
    started = time.time()
    checks: list[dict[str, Any]] = []
    # resolve động theo tên — cho phép test/module monkeypatch từng check
    display_names = {
        "_check_fitness": "fitness_drift",
        "_check_kernel_integrity": "kernel_integrity",
        "_check_escalation_backlog": "escalation_backlog",
        "_check_why_gate_anomaly": "why_gate_anomaly",
    }
    for check_ref in CHECKS:
        check = globals().get(check_ref.__name__, check_ref)
        display = display_names.get(check_ref.__name__, check_ref.__name__)
        try:
            checks.append(check(data_dir))
        except Exception as exc:
            # silent-by-design: the failure is carried in the report entry below (ok=False + detail).
            logger.debug("doubt_cron: check %s failed: %s", display, exc, exc_info=True)
            checks.append({"check": display, "ok": False, "detail": f"{type(exc).__name__}: {str(exc)[:150]}"})
    report = {
        "ran_at": started,
        "verdict": "CLEAN" if all(c.get("ok") for c in checks) else "DOUBT_DETECTED",
        "checks": checks,
    }
    ledger = Path(data_dir) / "doubt_ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False) + "\n")
    return report


class DoubtCron:
    """Vòng nghi ngờ chạy nền theo interval. Đứng lên bằng thread daemon."""

    def __init__(self, data_dir: str = "data", interval_seconds: float | None = None):
        self.data_dir = data_dir
        self.interval = float(
            interval_seconds
            if interval_seconds is not None
            else os.environ.get("SCP_DOUBT_INTERVAL_SEC", "21600")  # mặc định 6h
        )
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_report: dict[str, Any] | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def _loop() -> None:
            # Chạy ngay 1 vòng đầu (nghi ngờ không cần chờ 6 tiếng đầu tiên)
            while not self._stop.is_set():
                try:
                    self.last_report = run_doubt_cycle(self.data_dir)
                    if self.last_report["verdict"] != "CLEAN":
                        logger.warning("[DOUBT] %s: %s", self.last_report["verdict"],
                                       json.dumps(self.last_report["checks"], ensure_ascii=False)[:400])
                except Exception as exc:
                    logger.warning("[DOUBT] cycle failed (non-fatal): %s", exc, exc_info=True)
                self._stop.wait(self.interval)

        self._thread = threading.Thread(target=_loop, daemon=True, name="scp-doubt-cron")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()


_CRON: DoubtCron | None = None
_CRON_LOCK = threading.Lock()


def get_doubt_cron(data_dir: str = "data") -> DoubtCron:
    global _CRON
    if _CRON is None:
        with _CRON_LOCK:
            if _CRON is None:
                _CRON = DoubtCron(data_dir=data_dir)
    return _CRON
