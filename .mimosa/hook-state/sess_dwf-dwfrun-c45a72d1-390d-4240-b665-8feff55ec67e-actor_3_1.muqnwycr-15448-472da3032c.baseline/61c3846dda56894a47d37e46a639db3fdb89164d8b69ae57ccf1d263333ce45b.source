"""Long-running, evidence-producing soak test for the SCP TaskKernel."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scp.task_kernel import TaskKernel

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")
        stream.flush()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class WorkResult:
    task_id: str
    duration_seconds: float
    event_count: int


def _run_kernel_workload(kernel: TaskKernel, run_id: str, sequence: int) -> WorkResult:
    """Execute one valid, independently verified TaskKernel lifecycle."""
    task_id = f"soak-{run_id}-{sequence:09d}"
    worker_id = f"soak-worker-{threading.get_ident()}"
    started = time.perf_counter()

    kernel.create_task(
        task_id,
        owner=f"soak-owner-{sequence % 16}",
        goal="bounded TaskKernel durability workload",
        risk_tier="R0",
        deadline_ms=120_000,
    )
    kernel.transition(task_id, "PLANNING", actor=worker_id, reason="soak_plan")
    kernel.transition(task_id, "READY", actor=worker_id, reason="soak_ready")
    kernel.transition(task_id, "QUEUED", actor=worker_id, reason="soak_enqueue")
    lease = kernel.claim(task_id, worker_id, ttl_seconds=60.0)
    kernel.start(task_id, lease.lease_id)
    kernel.transition(task_id, "VERIFYING", actor=worker_id, reason="soak_postcondition")
    kernel.commit_completed(
        task_id,
        lease.lease_id,
        verifier_verdict="VERIFIED",
        evidence_ref=f"soak://{run_id}/{sequence}",
    )
    journal = kernel.verify_journal(task_id)
    if not journal.get("hash_chain_valid"):
        raise RuntimeError(f"journal integrity failed for {task_id}: {journal.get('errors', [])[:3]}")
    task = kernel.get_task(task_id)
    if task.get("state") != "COMPLETED":
        raise RuntimeError(f"postcondition failed for {task_id}: state={task.get('state')}")
    return WorkResult(
        task_id=task_id,
        duration_seconds=time.perf_counter() - started,
        event_count=int(journal["event_count"]),
    )


def _run_subprocess_workload(tid: int, results: dict[int, dict]) -> None:
    """Compatibility seam for the older fail-closed soak harness.

    The newer evidence runner executes TaskKernel work in-process for bounded,
    high-volume campaigns. Older callers still use ``run_workload(tid, results)``
    and depend on a separate child process so crashes and timeouts are observable.
    Preserve that stronger isolation contract rather than silently dropping it.
    """
    db_path = (ROOT / "soak.sqlite3").as_posix()
    task_id = f"soak-{tid}"
    script = (
        "from scp.task_kernel import TaskKernel; import time; "
        f"k = TaskKernel('{db_path}'); task_id = '{task_id}'; "
        "k.create_task(task_id, 'soak-worker', 'bounded soak workload', 'R0'); "
        "k.transition(task_id, 'PLANNING', actor='soak-worker', reason='soak_lifecycle'); "
        "k.transition(task_id, 'READY', actor='soak-worker', reason='soak_lifecycle'); "
        "k.transition(task_id, 'QUEUED', actor='soak-worker', reason='soak_lifecycle'); "
        "lease = k.claim(task_id, 'soak-worker', ttl_seconds=30); "
        "k.start(task_id, lease.lease_id); time.sleep(0.1); "
        "k.transition(task_id, 'VERIFYING', actor='soak-worker', reason='soak_verify'); "
        "k.commit_verification_result(task_id, lease.lease_id, "
        "{'verdict':'VERIFIED','verifier_id':'scp-soak-harness-v2','evidence_ref':'soak://'+task_id}); "
        "k.close()"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            timeout=5,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        stdout = proc.stdout.decode("utf-8", errors="replace") if isinstance(proc.stdout, bytes) else (proc.stdout or "")
        stderr = proc.stderr.decode("utf-8", errors="replace") if isinstance(proc.stderr, bytes) else (proc.stderr or "")
        results[tid] = {
            "returncode": proc.returncode,
            "stdout": stdout[-1000:],
            "stderr": stderr[-1000:],
        }
    except subprocess.TimeoutExpired as exc:
        results[tid] = {"timeout": True, "error": repr(exc)}
    except Exception as exc:
        results[tid] = {"error": repr(exc)}


def run_workload(
    kernel_or_tid: TaskKernel | int,
    run_id_or_results: str | dict[int, dict],
    sequence: int | None = None,
) -> WorkResult | None:
    """Run either the current kernel workload or the legacy isolated workload."""
    if sequence is None:
        if isinstance(kernel_or_tid, int) and isinstance(run_id_or_results, dict):
            _run_subprocess_workload(kernel_or_tid, run_id_or_results)
            return None
        raise TypeError("legacy run_workload requires (tid: int, results: dict)")
    if not isinstance(kernel_or_tid, TaskKernel) or not isinstance(run_id_or_results, str):
        raise TypeError("kernel run_workload requires (TaskKernel, run_id: str, sequence: int)")
    return _run_kernel_workload(kernel_or_tid, run_id_or_results, sequence)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return ordered[index]


def _latency_summary(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
    return {
        "min": round(min(values), 6),
        "mean": round(sum(values) / len(values), 6),
        "p50": round(_percentile(values, 0.50), 6),
        "p95": round(_percentile(values, 0.95), 6),
        "p99": round(_percentile(values, 0.99), 6),
        "max": round(max(values), 6),
    }


class SoakLock:
    def __init__(self, db_path: Path, run_id: str) -> None:
        self.path = db_path.with_suffix(db_path.suffix + ".soak.lock")
        self.run_id = run_id
        self._descriptor: int | None = None

    def __enter__(self) -> "SoakLock":
        try:
            self._descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            owner = self.path.read_text(encoding="utf-8", errors="replace").strip()
            raise RuntimeError(f"soak database is already locked: {self.path} ({owner})") from exc
        os.write(
            self._descriptor,
            f"pid={os.getpid()} run_id={self.run_id} started_at={utc_now()}".encode("utf-8"),
        )
        os.close(self._descriptor)
        self._descriptor = None
        return self

    def __exit__(self, *_: object) -> None:
        if self._descriptor is not None:
            os.close(self._descriptor)
        self.path.unlink(missing_ok=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    duration = parser.add_mutually_exclusive_group()
    duration.add_argument("--duration-hours", type=float)
    duration.add_argument("--duration-seconds", type=float)
    parser.add_argument("--run-id")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument("--integrity-interval-seconds", type=float, default=900.0)
    parser.add_argument("--report-interval-seconds", type=float, default=60.0)
    parser.add_argument("--max-errors", type=int, default=1)
    parser.add_argument("--min-free-mb", type=int, default=1024)
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> tuple[str, Path, Path, Path, float]:
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run-id must contain only letters, digits, dot, underscore or hyphen")
    output_dir = (args.output_dir or ROOT / "reports" / "soak" / run_id).resolve()
    db_path = (args.db or output_dir / "kernel.sqlite3").resolve()
    report_path = (args.report or output_dir / "progress.json").resolve()
    duration_seconds = (
        args.duration_seconds
        if args.duration_seconds is not None
        else (args.duration_hours if args.duration_hours is not None else 24.0) * 3600.0
    )
    numeric_positive = {
        "duration": duration_seconds,
        "workers": args.workers,
        "batch-size": args.batch_size,
        "interval": args.interval_seconds,
        "integrity interval": args.integrity_interval_seconds,
        "report interval": args.report_interval_seconds,
        "max errors": args.max_errors,
    }
    for name, value in numeric_positive.items():
        if not math.isfinite(float(value)) or value <= 0:
            raise ValueError(f"{name} must be positive")
    if args.batch_size > args.workers * 4:
        raise ValueError("batch-size must be <= workers * 4")
    if args.min_free_mb < 0:
        raise ValueError("min-free-mb cannot be negative")
    if db_path.exists():
        raise ValueError(f"refusing to overwrite existing soak database: {db_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    events_path = output_dir / "events.jsonl"
    if report_path.exists() or events_path.exists():
        raise ValueError("refusing to mix a new soak run with existing evidence files")
    return run_id, output_dir, db_path, report_path, float(duration_seconds)


def run(args: argparse.Namespace) -> int:
    run_id, output_dir, db_path, report_path, duration_seconds = _validate_args(args)
    events_path = output_dir / "events.jsonl"
    started_at = utc_now()
    started_monotonic = time.monotonic()
    stop_requested = threading.Event()
    interrupted = False
    failure_reason = ""
    errors: list[dict[str, str]] = []
    latencies: list[float] = []
    counters = {"submitted": 0, "completed": 0, "failed": 0, "events_verified": 0}
    integrity_checks = 0
    last_integrity: dict[str, Any] | None = None
    pending: set[Future[WorkResult]] = set()
    # Provenance is gathered BEFORE the measured soak window (see the
    # re-anchored deadline below the loop preamble): on Windows CI a cold
    # ``git status --porcelain`` over the worktree can take seconds, which
    # once consumed the whole window before the first deadline check and
    # produced a zero-workload soak (submitted=0, completed=0, FAILED).
    commit = _git("rev-parse", "HEAD")
    dirty = bool(_git("status", "--porcelain"))

    config = {
        "duration_seconds": duration_seconds,
        "workers": args.workers,
        "batch_size": args.batch_size,
        "interval_seconds": args.interval_seconds,
        "integrity_interval_seconds": args.integrity_interval_seconds,
        "report_interval_seconds": args.report_interval_seconds,
        "max_errors": args.max_errors,
        "min_free_mb": args.min_free_mb,
    }

    def snapshot(status: str) -> dict[str, Any]:
        elapsed = max(0.0, time.monotonic() - started_monotonic)
        free_mb = shutil.disk_usage(output_dir).free // (1024 * 1024)
        return {
            "schema_version": 1,
            "run_id": run_id,
            "status": status,
            "started_at": started_at,
            "updated_at": utc_now(),
            "elapsed_seconds": round(elapsed, 3),
            "target_duration_seconds": duration_seconds,
            "progress_fraction": round(min(1.0, elapsed / duration_seconds), 6),
            "pid": os.getpid(),
            "database": str(db_path),
            "events_log": str(events_path),
            "provenance": {
                "git_commit": commit,
                "working_tree_dirty_at_start": dirty,
                "python": sys.version.split()[0],
                "platform": platform.platform(),
            },
            "config": config,
            "counters": dict(counters),
            "pending": len(pending),
            "latency_seconds": _latency_summary(latencies),
            "integrity_checks": integrity_checks,
            "last_integrity": last_integrity,
            "free_disk_mb": free_mb,
            "failure_reason": failure_reason or None,
            "recent_errors": errors[-20:],
        }

    def request_stop(signum: int, _frame: object) -> None:
        nonlocal interrupted, failure_reason
        interrupted = True
        failure_reason = f"signal:{signum}"
        stop_requested.set()

    previous_handlers: dict[int, Any] = {}
    for sig in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[sig] = signal.signal(sig, request_stop)

    def process_future(future: Future[WorkResult]) -> None:
        nonlocal failure_reason
        try:
            result = future.result()
            counters["completed"] += 1
            counters["events_verified"] += result.event_count
            latencies.append(result.duration_seconds)
        except Exception as exc:
            counters["failed"] += 1
            errors.append({"at": utc_now(), "type": type(exc).__name__, "message": str(exc)[:500]})
            if counters["failed"] >= args.max_errors:
                failure_reason = "workload_error_limit"
                stop_requested.set()

    kernel: TaskKernel | None = None
    executor: ThreadPoolExecutor | None = None
    final_status = "FAILED"
    try:
        with SoakLock(db_path, run_id):
            kernel = TaskKernel(db_path)
            executor = ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="scp-soak")
            _atomic_json(report_path, snapshot("RUNNING"))
            _append_jsonl(events_path, {"type": "STARTED", **snapshot("RUNNING")})
            print(f"SOAK_STARTED run_id={run_id} pid={os.getpid()} report={report_path}", flush=True)

            # The measured soak window starts here — after git provenance,
            # database creation, executor startup, and the STARTED artifacts —
            # so slow setup can never consume the workload deadline.
            started_monotonic = time.monotonic()
            deadline = started_monotonic + duration_seconds
            next_submit = started_monotonic
            next_integrity = started_monotonic + args.integrity_interval_seconds
            next_report = started_monotonic + args.report_interval_seconds
            max_pending = args.workers * 4

            while time.monotonic() < deadline and not stop_requested.is_set():
                now = time.monotonic()
                if now >= next_submit:
                    available = max_pending - len(pending)
                    for _ in range(min(args.batch_size, max(0, available))):
                        counters["submitted"] += 1
                        pending.add(
                            executor.submit(run_workload, kernel, run_id, counters["submitted"])
                        )
                    next_submit = now + args.interval_seconds

                done = {future for future in pending if future.done()}
                for future in done:
                    pending.remove(future)
                    process_future(future)

                now = time.monotonic()
                if now >= next_integrity and not stop_requested.is_set():
                    last_integrity = kernel.verify_integrity()
                    integrity_checks += 1
                    _append_jsonl(
                        events_path,
                        {"type": "INTEGRITY", "at": utc_now(), "result": last_integrity},
                    )
                    if last_integrity.get("quick_check") != "ok" or last_integrity.get("invalid_chains"):
                        failure_reason = "integrity_check_failed"
                        stop_requested.set()
                    next_integrity = now + args.integrity_interval_seconds

                if now >= next_report:
                    current = snapshot("RUNNING")
                    _atomic_json(report_path, current)
                    _append_jsonl(events_path, {"type": "PROGRESS", **current})
                    print(
                        f"SOAK_PROGRESS elapsed={current['elapsed_seconds']}s "
                        f"completed={counters['completed']} failed={counters['failed']} "
                        f"p95={current['latency_seconds']['p95']}s",
                        flush=True,
                    )
                    if current["free_disk_mb"] < args.min_free_mb:
                        failure_reason = "minimum_free_disk_reached"
                        stop_requested.set()
                    next_report = now + args.report_interval_seconds

                if not done:
                    time.sleep(min(0.2, max(0.01, deadline - time.monotonic())))

            for future in list(pending):
                process_future(future)
                pending.remove(future)

            last_integrity = kernel.verify_integrity()
            integrity_checks += 1
            if last_integrity.get("quick_check") != "ok" or last_integrity.get("invalid_chains"):
                failure_reason = failure_reason or "final_integrity_check_failed"
            if counters["submitted"] == 0:
                # Distinct, loud marker for "the window expired before any
                # workload was submitted" — a harness/setup anomaly, not a
                # genuine workload failure.
                failure_reason = failure_reason or "no_workload_submitted"
            if counters["completed"] == 0:
                failure_reason = failure_reason or "no_workload_completed"

            if interrupted:
                final_status = "INTERRUPTED"
            elif failure_reason or counters["failed"]:
                final_status = "FAILED"
            else:
                final_status = "COMPLETED"

            executor.shutdown(wait=True, cancel_futures=False)
            executor = None
            kernel.close()
            kernel = None

            final = snapshot(final_status)
            final["finished_at"] = utc_now()
            final["database_sha256"] = _sha256_file(db_path)
            _atomic_json(report_path, final)
            _append_jsonl(events_path, {"type": "FINISHED", **final})
            print(
                f"SOAK_FINISHED status={final_status} completed={counters['completed']} "
                f"failed={counters['failed']} submitted={counters['submitted']}"
                + (f" failure_reason={failure_reason}" if failure_reason else "")
                + f" report={report_path}",
                flush=True,
            )
    except Exception as exc:
        failure_reason = failure_reason or f"harness_exception:{type(exc).__name__}"
        errors.append({"at": utc_now(), "type": type(exc).__name__, "message": str(exc)[:500]})
        final_status = "FAILED"
        try:
            _atomic_json(report_path, snapshot(final_status))
            _append_jsonl(events_path, {"type": "HARNESS_ERROR", **snapshot(final_status)})
        except OSError:
            pass
        print(f"SOAK_FAILED {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    finally:
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
        if kernel is not None:
            kernel.close()
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)

    if final_status == "COMPLETED":
        return 0
    if final_status == "INTERRUPTED":
        return 130
    return 1


def soak_loop(duration_hours: float = 24) -> bool:
    """Backward-compatible boolean soak loop with subprocess isolation.

    This remains intentionally fail closed: zero/negative/non-finite duration,
    child-process failures, journal failures, incomplete terminal state, or an
    interrupt all return ``False``.
    """
    if not math.isfinite(float(duration_hours)) or duration_hours <= 0:
        return False

    print(f"Starting {duration_hours}h SCP Soak Test...")
    end_time = time.time() + (duration_hours * 3600)
    db_path = ROOT / "soak.sqlite3"
    if db_path.exists():
        db_path.unlink()

    kernel = TaskKernel(db_path)
    total_spawned = 0
    total_failed = 0
    start_time = time.time()

    try:
        while time.time() < end_time:
            batch = random.randint(10, 50)
            batch_results: dict[int, dict] = {}
            threads = []
            batch_ids = []

            for _ in range(batch):
                total_spawned += 1
                tid = total_spawned
                batch_ids.append(tid)
                thread = threading.Thread(target=run_workload, args=(tid, batch_results))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            process_failures = []
            journal_failures = []
            state_failures = []
            for tid in batch_ids:
                task_id = f"soak-{tid}"
                process_result = batch_results.get(tid)
                if not process_result or process_result.get("returncode") != 0:
                    process_failures.append((tid, process_result))
                    continue
                try:
                    journal = kernel.verify_journal(task_id)
                    task = kernel.get_task(task_id)
                except Exception as exc:
                    journal_failures.append((tid, f"verify/read error: {exc!r}"))
                    continue
                if not journal.get("hash_chain_valid", False):
                    journal_failures.append((tid, "hash_chain_valid=False"))
                if task.get("state") != "COMPLETED":
                    state_failures.append((tid, task.get("state")))

            batch_failed = len(process_failures) + len(journal_failures) + len(state_failures)
            total_failed += batch_failed
            elapsed = time.time() - start_time
            status = "PASS" if batch_failed == 0 else f"FAIL ({batch_failed})"
            print(
                f"Elapsed {elapsed/3600:.4f}h | Spawned: {total_spawned} | "
                f"Batch: {batch} | Ledger/workload check: {status}"
            )
            if process_failures:
                print(f"  process failures: {process_failures[:3]}")
            if journal_failures:
                print(f"  journal failures: {journal_failures[:3]}")
            if state_failures:
                print(f"  state failures: {state_failures[:3]}")
            if batch_failed:
                return False
            time.sleep(1)
    except KeyboardInterrupt:
        print("Soak test interrupted — not a PASS.")
        return False
    finally:
        kernel.close()

    print(f"Soak complete: spawned={total_spawned}, failures={total_failed}")
    return total_spawned > 0 and total_failed == 0


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        return run(args)
    except (ValueError, RuntimeError) as exc:
        print(f"SOAK_CONFIG_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
