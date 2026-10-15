"""
Mảnh ghép #38 — Parallel Speculative Execution: brute-force thông minh.

TẠI SAO: SCP sửa lỗi tuyến tính như con người (sinh 1 giải pháp → test →
sai → sinh lại). Máy móc không bị giới hạn bởi một bộ não: với bug khó, nhân
bản workspace thành N vũ trụ song song (Git Worktrees), ép N solver viết N
hướng giải KHÁC nhau cùng lúc, đua với verifier. Nhánh nào PASS TRƯỚC — lấy
code đó, dọn sạch N-1 vũ trụ còn lại.

Thiết kế DNA:
  - Solver/Verifier là INJECTABLE — harness này không ràng buộc cách sinh
    patch (llm_fix, deterministic fixer, thậm chí 5 model khác nhau cho 5
    nhánh — đúng tinh thần không ưu tiên model nào).
  - Mỗi attempt chạy trong GIT WORKTREE riêng → cách ly hệ số khác nhau,
    failed attempts bị dọn sạch, main workspace không bao giờ bị chạm.
  - First-PASS-wins: attempt chậm bị hủy (không đợi).
  - Mọi lifecycle ghi evidence log.
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.core.speculative")

CleanupFn = Callable[[Path], None]
SolverFn = Callable[[Path, dict[str, Any]], Any]      # (worktree_path, bug) -> attempt result
VerifierFn = Callable[[Path, Any], bool]              # (worktree_path, attempt_result) -> PASS?


def _git(args: list[str], cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd) if cwd else None, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )


class SpeculativeRace:
    """Race N solver attempts trong N git worktrees cách ly. First-PASS-wins."""

    def __init__(
        self,
        repo_root: str | Path,
        solver: SolverFn,
        verifier: VerifierFn,
        attempts: int | None = None,
        cleanup: CleanupFn | None = None,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.solver = solver
        self.verifier = verifier
        self.attempts = int(
            attempts if attempts is not None
            else os.environ.get("SCP_SPECULATIVE_ATTEMPTS", "3")
        )
        if self.attempts < 1:
            raise ValueError("attempts must be >= 1")
        self.cleanup_extra = cleanup
        self.evidence: list[dict[str, Any]] = []

    def _worktree_add(self, base: Path, name: str) -> Path:
        path = base / name
        result = _git(["worktree", "add", "-b", name, str(path)], cwd=self.repo_root)
        if result.returncode != 0:
            # branch đã tồn tại từ race trước (crash) — dùng force + branch mới unique
            unique = f"{name}-{uuid.uuid4().hex[:6]}"
            result = _git(["worktree", "add", "-b", unique, str(path)], cwd=self.repo_root)
            if result.returncode != 0:
                raise RuntimeError(f"worktree add failed: {result.stderr[:200]}")
        return path

    @staticmethod
    def _worktree_remove(path: Path, repo_root: Path) -> None:
        _git(["worktree", "remove", "--force", str(path)], cwd=repo_root, timeout=30)

    def run(self, bug: dict[str, Any]) -> dict[str, Any]:
        """Race N attempts. Returns {verdict, winner, attempts_meta, evidence}."""
        started = time.time()
        base = Path(tempfile.mkdtemp(prefix="scp-speculative-"))
        lock = threading.Lock()
        winner: dict[str, Any] | None = None
        attempts_meta: list[dict[str, Any]] = []

        def _attempt(index: int) -> None:
            nonlocal winner
            if winner is not None:
                return  # đã có người PASS trước — nhánh này không cần chạy nữa
            name = f"speculative-attempt-{index}"
            worktree: Path | None = None
            meta: dict[str, Any] = {"attempt": index, "worktree": None, "verdict": "UNKNOWN"}
            try:
                worktree = self._worktree_add(base, name)
                meta["worktree"] = str(worktree)
                attempt_result = self.solver(worktree, bug)
                passed = self.verifier(worktree, attempt_result)
                meta["verdict"] = "PASS" if passed else "FAIL"
                if passed and winner is None:
                    with lock:
                        if winner is None:  # double-check: first-PASS-wins
                            winner = {
                                "attempt": index,
                                "worktree": str(worktree),
                                "result": attempt_result,
                            }
                            meta["verdict"] = "PASS (WINNER)"
            except Exception as exc:
                # silent-by-design: the error is recorded in meta[verdict] and returned to the caller.
                logger.debug("speculative: attempt failed, verdict=ERROR recorded: %s", exc, exc_info=True)
                meta["verdict"] = f"ERROR: {type(exc).__name__}: {str(exc)[:100]}"
            finally:
                with lock:
                    attempts_meta.append(meta)
                # Nhánh thắng KHÔNG dọn (worktree giữ lại cho caller lấy patch);
                # nhánh thua dọn ngay để giải phóng disk.
                if worktree is not None and (winner is None or winner.get("worktree") != str(worktree)):
                    try:
                        self._worktree_remove(worktree, self.repo_root)
                    except Exception as exc:
                        logger.debug("worktree cleanup failed: %s", exc, exc_info=True)

        threads = [threading.Thread(target=_attempt, args=(i,)) for i in range(1, self.attempts + 1)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if self.cleanup_extra:
            try:
                self.cleanup_extra(base)
            except Exception as exc:
                # silent-by-design: user-provided cleanup is best-effort; it must not mask the main result.
                logger.debug("speculative: cleanup_extra failed (non-fatal): %s", exc, exc_info=True)

        report = {
            "verdict": "SOLVED" if winner else "UNSOLVED",
            "winner": winner,
            "attempts": self.attempts,
            "attempts_meta": attempts_meta,
            "elapsed_sec": round(time.time() - started, 2),
        }
        self.evidence.append(report)
        return report
