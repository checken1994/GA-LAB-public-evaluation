"""Sandbox Evaluator core — evaluate(patch_target) -> EvalResult (Track C3).

Chạy pytest thật trên BẢN SAO workspace trong system temp. KHÔNG bao giờ chạy
trên repo sống; KHÔNG bao giờ trả PASS khi test không chạy được (DNA #22).

patch_target schema (dict, mọi trường optional trừ test sources):

    {
      "job_id":          str   — định danh phục vụ audit/event (optional)
      "files":           {relpath: content}  — file đích (nội dung đã vá) ghi
                         vào workspace. relpath giữ nguyên cấu trúc để import
                         package-style hoạt động (PEP 420 namespace packages).
      "extra_files":     {relpath: content}  — module phụ trợ (optional)
      "test_files":      {relpath: content}  — test file nội dung inline
      "test_paths":      [path, ...] — test file trên đĩa sẽ được copy vào
                         workspace tại ``tests/<basename>`` (tên trùng -> setup
                         FAIL). Ít nhất MỘT nguồn test phải có, nếu không
                         -> FAIL(setup:no_tests) — không test = không chấm.
      "timeout_seconds": int — clamp [5, 900]; default từ env
                         ``SCP_SANDBOX_EVALUATOR_TIMEOUT_S`` (120).
      "keep_workspace":  bool — giữ workspace để debug (default False).
    }

Verdict contract:
    PASS   — pytest chạy thật và ``returncode == 0``.
    FAIL   — mọi trường hợp khác; ``reason`` phân loại:
             "setup:<chi tiết>" (workspace/copy/validation lỗi),
             "timeout" (TimeoutExpired),
             "test_failed" (pytest exit 1),
             "no_tests_collected" (pytest exit 5),
             "pytest_usage_error" (4), "pytest_internal_error" (3),
             "pytest_interrupted" (2), "pytest_exit_<rc>" (khác).
    ``returncode is None`` khi pytest không hề được spawn (lỗi setup).
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath

logger = logging.getLogger("scp.sandbox_evaluator")

# Event bus contract (ADOPT-AND-FIX Track C2/C3 — one channel, typed payloads).
CHANNEL_EVAL = "scp_eval"
EVENT_EVAL_REQUEST = "EVAL_REQUEST"
EVENT_EVAL_RESULT = "EVAL_RESULT"

DEFAULT_TIMEOUT_SECONDS = 120
MIN_TIMEOUT_SECONDS = 5
MAX_TIMEOUT_SECONDS = 900
_TIMEOUT_ENV = "SCP_SANDBOX_EVALUATOR_TIMEOUT_S"

# Opt-in env cho wire vào autofix pipeline (deterministic_worker + engine).
_SANDBOX_ENV = "SCP_SANDBOX_EVALUATOR"
_TRUTHY = ("1", "true", "yes", "on")

# Allowlist env tối thiểu cho subprocess pytest. KHÔNG kế thừa env còn lại —
# secrets (.env, tokens, credentials) không bao giờ lọt vào workspace subprocess.
_ENV_ALLOWLIST = (
    "PATH",
    "PATHEXT",  # Windows: resolve .exe
    "SYSTEMROOT",  # Windows: socket/ssl init bắt buộc
    "SYSTEMDRIVE",
    "COMSPEC",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "HOME",
    "USERPROFILE",
    "PYTHONIOENCODING",
)

# conftest.py tối tiểu chèn workspace root vào sys.path để test import được
# module đích (root-level và package-style qua namespace packages).
_CONFTEST_SRC = (
    "import sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, str(Path(__file__).resolve().parent))\n"
)

_PYTEST_EXIT_REASON = {
    1: "test_failed",
    2: "pytest_interrupted",
    3: "pytest_internal_error",
    4: "pytest_usage_error",
    5: "no_tests_collected",
}


@dataclass(frozen=True)
class EvalResult:
    """Kết quả một lần đánh giá sandbox. ``verdict == "PASS"`` chỉ khi pytest
    thật sự chạy và returncode == 0 (fail-closed ở mọi đường lỗi khác)."""

    verdict: str  # "PASS" | "FAIL"
    reason: str  # "" khi PASS; phân loại lỗi khi FAIL (xem module docstring)
    returncode: int | None  # None khi pytest không được spawn (setup fail)
    stdout: str  # raw pytest stdout (decoded, errors="replace")
    stderr: str  # raw pytest stderr
    duration_seconds: float
    workspace: str  # đường dẫn workspace tạm (đã dọn nếu keep_workspace=False)
    command: list[str] = field(default_factory=list)  # chứng minh shell=False
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "reason": self.reason,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": round(self.duration_seconds, 3),
            "workspace": self.workspace,
            "command": list(self.command),
            "timed_out": self.timed_out,
        }

    def to_dict_bounded(self, max_output_chars: int = 4096) -> dict:
        """Bản bounded cho audit log/result — raw output đầy đủ vẫn nằm ở
        to_dict()/EVAL_RESULT event; audit chỉ giữ excerpt hai đầu."""
        out = self.to_dict()
        for key in ("stdout", "stderr"):
            val = out[key]
            if len(val) > max_output_chars:
                head = val[: max_output_chars // 2]
                tail = val[-(max_output_chars // 2):]
                out[key] = f"{head}\n...[truncated {len(val) - max_output_chars} chars]...\n{tail}"
        return out


def sandbox_enabled() -> bool:
    """Opt-in flag: ``SCP_SANDBOX_EVALUATOR`` truthy -> autofix pipeline dùng
    SandboxEvaluator thay vì reality-test nội bộ. Default (env off) giữ nguyên
    behavior hiện tại."""
    return os.environ.get(_SANDBOX_ENV, "0").strip().lower() in _TRUTHY


def default_timeout_seconds() -> int:
    """Timeout mặc định từ env, clamp [5, 900] (giới hạn subprocess ở mọi chỗ)."""
    raw = os.environ.get(_TIMEOUT_ENV, "").strip()
    try:
        value = int(raw) if raw else DEFAULT_TIMEOUT_SECONDS
    except ValueError:
        logger.warning("%s=%r không phải int — dùng default %ss (fail-safe)",
                       _TIMEOUT_ENV, raw, DEFAULT_TIMEOUT_SECONDS)
        value = DEFAULT_TIMEOUT_SECONDS
    return max(MIN_TIMEOUT_SECONDS, min(MAX_TIMEOUT_SECONDS, value))


def _fail(reason: str, *, started: float, workspace: str = "",
          stderr: str = "", keep: bool = False) -> EvalResult:
    _cleanup(workspace, keep)
    return EvalResult(
        verdict="FAIL",
        reason=reason,
        returncode=None,
        stdout="",
        stderr=stderr,
        duration_seconds=time.monotonic() - started,
        workspace=workspace,
        command=[],
    )


def _cleanup(workspace: str, keep: bool) -> None:
    if not workspace or keep:
        return
    shutil.rmtree(workspace, ignore_errors=True)


def _contained_path(workspace: str, *parts: str):
    """Join ``parts`` dưới ``workspace`` và KIỂM TRA CHỨA tường minh (fail-closed).

    Trả Path tuyệt đối đã resolve (symlink + ".." được xử lý thật) nếu nằm
    BÊN TRONG workspace; trả None nếu thoát ra ngoài. Invariant "mọi file ghi
    phải nằm trong workspace" được kiểm chứng TẠI BOUNDARY bằng
    ``Path.resolve()`` + ``Path.is_relative_to()`` — không dựa vào
    ``_safe_relpath`` ở lớp trên.
    """
    root = Path(workspace).resolve()
    dest = root.joinpath(*parts).resolve()
    if dest == root or not dest.is_relative_to(root):
        return None
    return dest


def _safe_relpath(relpath: str) -> str | None:
    """Chuẩn hoá relpath cho file ghi vào workspace; None nếu unsafe.

    Chặn: absolute path, drive letters, ``os.pardir`` (".."), backslash
    traversal — file ghi phải nằm BÊN TRONG workspace (sandbox escape guard).
    """
    if not isinstance(relpath, str) or not relpath.strip():
        return None
    if "\x00" in relpath:
        return None
    win = PureWindowsPath(relpath)
    if win.is_absolute() or win.drive or win.root:
        return None
    posix = PurePosixPath(relpath.replace("\\", "/"))
    if posix.is_absolute():
        return None
    parts = [p for p in posix.parts if p not in (".", "")]
    if not parts or any(p == os.pardir for p in parts):
        return None
    return "/".join(parts)


def _read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("sandbox evaluator: đọc test path %s thất bại: %s", path, exc)
        return None


def _setup_workspace(patch_target: dict, started: float, keep: bool):
    """Tạo workspace tạm (system temp) + ghi toàn bộ file. Trả về
    (workspace, test_args) hoặc EvalResult FAIL(setup:...) — fail-closed."""
    try:
        workspace = tempfile.mkdtemp(prefix="scp_sandbox_eval_")
    except OSError as exc:
        return _fail(f"setup:mkdtemp:{exc}", started=started)

    files: dict[str, str] = {}
    for key in ("files", "extra_files", "test_files"):
        section = patch_target.get(key)
        if section is None:
            continue
        if not isinstance(section, dict):
            return _fail(f"setup:{key}_not_dict", started=started, workspace=workspace, keep=keep)
        files.update(section)

    test_args: list[str] = []

    # Inline files (nội dung đã vá + test inline + phụ trợ).
    for relpath, content in files.items():
        safe = _safe_relpath(relpath)
        if safe is None:
            return _fail(f"setup:unsafe_relpath:{relpath!r}", started=started, workspace=workspace, keep=keep)
        if not isinstance(content, str):
            return _fail(f"setup:content_not_str:{relpath!r}", started=started, workspace=workspace, keep=keep)
        dest = _contained_path(workspace, *safe.split("/"))
        if dest is None:
            return _fail(f"setup:path_escapes_workspace:{relpath!r}", started=started, workspace=workspace, keep=keep)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8", newline="")
        except OSError as exc:
            return _fail(f"setup:write:{safe}:{exc}", started=started, workspace=workspace, keep=keep)
        if relpath in (patch_target.get("test_files") or {}):
            test_args.append(safe)

    # Test file trên đĩa -> copy vào tests/<basename> (tên trùng -> setup FAIL).
    test_paths = patch_target.get("test_paths") or []
    if not isinstance(test_paths, list):
        return _fail("setup:test_paths_not_list", started=started, workspace=workspace, keep=keep)
    seen_names: set[str] = set()
    for tp in test_paths:
        if not isinstance(tp, str) or not tp.strip():
            return _fail(f"setup:bad_test_path:{tp!r}", started=started, workspace=workspace, keep=keep)
        src = Path(tp)
        if not src.is_file():
            return _fail(f"setup:test_path_missing:{tp}", started=started, workspace=workspace, keep=keep)
        base = src.name
        if base in seen_names:
            return _fail(f"setup:colliding_test_filenames:{base}", started=started, workspace=workspace, keep=keep)
        seen_names.add(base)
        content = _read_text(str(src))
        if content is None:
            return _fail(f"setup:test_path_unreadable:{tp}", started=started, workspace=workspace, keep=keep)
        dest = _contained_path(workspace, "tests", base)
        if dest is None:
            return _fail(f"setup:path_escapes_workspace:{base!r}", started=started, workspace=workspace, keep=keep)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8", newline="")
        except OSError as exc:
            return _fail(f"setup:write_test:{base}:{exc}", started=started, workspace=workspace, keep=keep)
        test_args.append(f"tests/{base}")

    if not test_args:
        # DNA #22: không có test nào -> không có gì để chạy -> KHÔNG BAO GIỜ PASS.
        return _fail("setup:no_tests", started=started, workspace=workspace, keep=keep)

    try:
        conftest_dest = _contained_path(workspace, "conftest.py")
        if conftest_dest is None:  # bất khả thi về logic; giữ fail-closed tường minh
            return _fail("setup:path_escapes_workspace:conftest", started=started, workspace=workspace, keep=keep)
        conftest_dest.write_text(_CONFTEST_SRC, encoding="utf-8")
    except OSError as exc:
        return _fail(f"setup:conftest:{exc}", started=started, workspace=workspace, keep=keep)

    return workspace, test_args


def _sanitized_env() -> dict[str, str]:
    """Allowlist env tối thiểu — không kế thừa env nhạy cảm của process cha."""
    env = {k: os.environ[k] for k in _ENV_ALLOWLIST if k in os.environ}
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def evaluate(patch_target: dict) -> EvalResult:
    """Chạy pytest thật trên bản sao workspace; PASS chỉ khi returncode == 0.

    Fail-closed: mọi lỗi setup/timeout/spawn -> FAIL; không bao giờ PASS khi
    test không chạy được (DNA #22).
    """
    started = time.monotonic()
    if not isinstance(patch_target, dict):
        return _fail("setup:patch_target_not_dict", started=started)

    keep = bool(patch_target.get("keep_workspace", False))

    raw_timeout = patch_target.get("timeout_seconds")
    if raw_timeout is None:
        timeout = default_timeout_seconds()
    else:
        try:
            timeout = int(raw_timeout)
        except (TypeError, ValueError):
            return _fail(f"setup:bad_timeout:{raw_timeout!r}", started=started)
        timeout = max(MIN_TIMEOUT_SECONDS, min(MAX_TIMEOUT_SECONDS, timeout))

    setup = _setup_workspace(patch_target, started, keep)
    if isinstance(setup, EvalResult):  # fail-closed setup
        return setup
    workspace, test_args = setup

    # Task C3 contract: [sys.executable, "-m", "pytest", <target-tests>, "-x", "-q"]
    # (+ -p no:cacheprovider: workspace tạm không cần .pytest_cache).
    command = [sys.executable, "-m", "pytest", *test_args, "-x", "-q", "-p", "no:cacheprovider"]

    try:
        proc = subprocess.run(  # noqa: S603 — argv list, shell=False, timeout bắt buộc
            command,
            cwd=workspace,
            env=_sanitized_env(),
            timeout=timeout,
            capture_output=True,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _decode(getattr(exc, "stdout", None))
        stderr = _decode(getattr(exc, "stderr", None))
        result = EvalResult(
            verdict="FAIL",
            reason="timeout",
            returncode=None,
            stdout=stdout,
            stderr=stderr or f"timeout after {timeout}s (subprocess killed)",
            duration_seconds=time.monotonic() - started,
            workspace=workspace,
            command=command,
            timed_out=True,
        )
        _cleanup(workspace, keep)
        return result
    except OSError as exc:
        result = _fail(f"setup:subprocess_spawn:{exc}", started=started, workspace=workspace)
        return EvalResult(
            verdict=result.verdict,
            reason=result.reason,
            returncode=None,
            stdout="",
            stderr=str(exc),
            duration_seconds=time.monotonic() - started,
            workspace=result.workspace,
            command=command,
        )

    rc = int(proc.returncode)
    verdict = "PASS" if rc == 0 else "FAIL"
    reason = "" if rc == 0 else _PYTEST_EXIT_REASON.get(rc, f"pytest_exit_{rc}")
    result = EvalResult(
        verdict=verdict,
        reason=reason,
        returncode=rc,
        stdout=_decode(proc.stdout),
        stderr=_decode(proc.stderr),
        duration_seconds=time.monotonic() - started,
        workspace=workspace,
        command=command,
    )
    _cleanup(workspace, keep)
    return result


def _decode(data) -> str:
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return str(data)


def build_patch_target(
    file_path: str,
    patched_content: str,
    *,
    test_paths: list[str],
    allowed_root: str | None = None,
    timeout_seconds: int | None = None,
    job_id: str | None = None,
) -> dict:
    """Build một patch_target schema-correct cho evaluate().

    File đích được đặt tại relpath TƯƠNG ĐỐI với allowed_root (giữ cấu trúc
    package để import package-style hoạt động qua namespace packages); nếu file
    nằm ngoài allowed_root thì dùng basename (import root-level).
    """
    target = Path(file_path)
    relname: str | None = None
    if allowed_root is not None:
        try:
            relname = str(
                target.resolve().relative_to(Path(allowed_root).resolve())
            ).replace("\\", "/")
        except ValueError:
            relname = None
    if not relname:
        relname = target.name
    target_spec: dict = {
        "files": {relname: patched_content},
        "test_paths": [str(tp) for tp in test_paths],
    }
    if job_id is not None:
        target_spec["job_id"] = str(job_id)
    if timeout_seconds is not None:
        target_spec["timeout_seconds"] = max(
            MIN_TIMEOUT_SECONDS, min(MAX_TIMEOUT_SECONDS, int(timeout_seconds))
        )
    return target_spec
