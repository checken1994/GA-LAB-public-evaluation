import logging
import os
import platform
import shutil
import subprocess
import sys
import threading
from typing import Any

from scp.security.capability_epoch import CapabilityAuthority, CapabilityToken

logger = logging.getLogger(__name__)



def build_bwrap_argv(cmd: list[str]) -> list[str]:
    """[C2 — Gemini indictment: rlimit là hàng rào đồ chơi] Xây argv Bubblewrap
    cách ly THẬT: --unshare-all cắt Network + PID + Mount namespace, rootFS
    chỉ-đọc, /tmp tmpfs. Pure function — test được trên mọi OS. Chỉ dùng khi
    bwrap có mặt (Linux); Windows dùng Job Objects."""
    return [
        "bwrap",
        "--unshare-all",
        "--die-with-parent",
        "--ro-bind", "/", "/",
        "--tmpfs", "/tmp",  # nosec B108 — bwrap CLI flag, not a temp-file write: mounts a fresh empty tmpfs at /tmp INSIDE the sandbox namespace (this IS the isolation mechanism).
        "--dev", "/dev",
        "--proc", "/proc",
        "--",
    ] + [str(c) for c in cmd]


def isolation_capability() -> dict[str, Any]:
    """[Cổng E — trung thực về reality] Báo cáo khả năng isolation THẬT của
    môi trường hiện tại. Không phóng đại: thiếu cơ chế thì ghi rõ."""
    caps: dict[str, Any] = {"platform": platform.system(), "job_object": False, "bwrap": False, "rlimit": False}
    if caps["platform"] == "Windows":
        try:
            import win32job  # noqa: F401

            caps["job_object"] = True
        except ImportError:
            logger.debug('isolation_capability: ImportError ignored', exc_info=True)
            caps["job_object"] = False
    else:
        try:
            import resource  # noqa: F401

            caps["rlimit"] = True
        except ImportError:
            logger.debug('isolation_capability: ImportError ignored', exc_info=True)
            caps["rlimit"] = False
        caps["bwrap"] = shutil.which("bwrap") is not None
    if caps["job_object"]:
        caps["level"] = "job_object"
    elif caps["bwrap"]:
        caps["level"] = "bwrap"
    elif caps["rlimit"]:
        caps["level"] = "rlimit_only_not_a_sandbox"
    else:
        caps["level"] = "subprocess_only_not_a_sandbox"
    return caps


class ProcessIsolationEnvironment:
    """
    OS-Level isolation wrapper.
    Replaces the dangerously misnamed 'OSSandbox'.
    Uses Windows Job Objects (if on Windows) to enforce memory and process limits.
    For cross-platform compatibility, falls back to subprocess boundaries.

    [CHAOS-FIX 2026-08-29 — Gemini runtime finding verified by reproduction]
    Bản cũ dùng subprocess.Popen(CREATE_SUSPENDED) rồi
    win32process.ResumeThread(int(proc._handle)) — _handle là PROCESS handle
    trong khi ResumeThread đòi THREAD handle → (6, 'The handle is invalid')
    và sandbox tự sát, KHÔNG BAO GIỜ chạy được. Fix: dùng
    win32process.CreateProcess trực tiếp — trả về (hProcess, hThread, pid,
    tid) → AssignProcessToJobObject → ResumeThread(hThread) đúng handle,
    cộng thêm JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE.
    """

    def __init__(self, authority: CapabilityAuthority):
        self.authority = authority
        self.is_windows = platform.system() == "Windows"

    def _execute_windows_job(self, cmd: list[str], cwd: str | None, safe_env: dict[str, str]) -> subprocess.CompletedProcess:
        """Suspended CreateProcess → Job Object → ResumeThread(hThread)."""
        import pywintypes
        import win32api
        import win32con
        import win32event
        import win32file
        import win32job
        import win32pipe
        import win32process

        job = win32job.CreateJobObject(None, "")
        limits = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
        limits['BasicLimitInformation']['LimitFlags'] = (
            win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY
            | win32job.JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            | win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        limits['ProcessMemoryLimit'] = 512 * 1024 * 1024  # 512 MB
        limits['BasicLimitInformation']['ActiveProcessLimit'] = 10
        win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, limits)

        # Pipes inheritable cho stdout/stderr; stdin cắm NUL (không đọc console)
        sa = pywintypes.SECURITY_ATTRIBUTES()
        sa.bInheritHandle = True
        out_r, out_w = win32pipe.CreatePipe(sa, 0)
        err_r, err_w = win32pipe.CreatePipe(sa, 0)
        nul = win32file.CreateFile(
            "NUL", win32file.GENERIC_READ,
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            sa, win32file.OPEN_EXISTING, 0, None,
        )
        startup = win32process.STARTUPINFO()
        startup.dwFlags = win32process.STARTF_USESTDHANDLES
        startup.hStdInput = nul
        startup.hStdOutput = out_w
        startup.hStdError = err_w

        cmdline = " ".join(f'"{c}"' if (" " in str(c) or "\t" in str(c)) else str(c) for c in cmd)
        info = win32process.CreateProcess(
            None, cmdline, None, None, True,
            win32process.CREATE_SUSPENDED,
            {str(k): str(v) for k, v in safe_env.items()},
            cwd, startup,
        )
        h_process, h_thread, _pid, _tid = info
        win32job.AssignProcessToJobObject(job, int(h_process))
        # FIX: ResumeThread với THREAD handle thật từ CreateProcess
        win32process.ResumeThread(h_thread)
        win32api.CloseHandle(out_w)
        win32api.CloseHandle(err_w)
        win32api.CloseHandle(nul)

        buffers: dict[str, list[str]] = {"out": [], "err": []}

        def _drain(handle: Any, sink: list[str]) -> None:
            while True:
                try:
                    _, data = win32file.ReadFile(handle, 65536)
                except pywintypes.error:
                    logger.debug('ProcessIsolationEnvironment._execute_windows_job._drain: pywintypes.error ignored', exc_info=True)
                    break
                if not data:
                    break
                sink.append(data.decode("utf-8", errors="replace"))

        readers = [
            threading.Thread(target=_drain, args=(out_r, buffers["out"]), daemon=True),
            threading.Thread(target=_drain, args=(err_r, buffers["err"]), daemon=True),
        ]
        for reader in readers:
            reader.start()
        try:
            wait = win32event.WaitForSingleObject(h_process, 15 * 1000)
            if wait == win32con.WAIT_TIMEOUT:
                win32job.TerminateJobObject(job, 124)
                raise TimeoutError(f"sandboxed command exceeded 15s: {cmd[:1]}")
            exit_code = win32process.GetExitCodeProcess(h_process)
        finally:
            for reader in readers:
                reader.join(timeout=5)
            for handle in (out_r, err_r, h_process, h_thread):
                try:
                    win32api.CloseHandle(handle)
                except pywintypes.error:
                    logger.debug('ProcessIsolationEnvironment._execute_windows_job: pywintypes.error ignored', exc_info=True)
        return subprocess.CompletedProcess(cmd, exit_code, "".join(buffers["out"]), "".join(buffers["err"]))

    def execute_bounded(self, capability_token: CapabilityToken, cmd: list[str], cwd: str = None) -> subprocess.CompletedProcess:
        if not self.authority.validate(capability_token):
            raise PermissionError(f"Epoch violation or unauthorized capability: {capability_token.token_id}")

        # [CHAOS-FIX #51 — Network egress + file isolation]
        # Gemini indictment CONFIRMED by runtime proof: subprocess inside Job
        # Object can (1) read .env with API keys, (2) freely make HTTP requests.
        # Fix: dead proxy blocks HTTP exfiltration via requests/urllib;
        # minimal PATH restricts tool discovery; SYSTEMROOT kept for cmd.exe.
        # KNOWN LIMITATION (documented honestly): raw sockets + direct file
        # reads still possible — full isolation requires container (WSL2/Docker).
        safe_env = {
            "PATH": os.path.dirname(sys.executable),  # chỉ python dir, không full system PATH
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "TEMP": os.environ.get("TEMP", ""),
            "TMP": os.environ.get("TMP", ""),
            # Dead proxy: urllib/requests theo env vars → kết nối fail ngay
            "HTTP_PROXY": "http://127.0.0.1:1",
            "HTTPS_PROXY": "http://127.0.0.1:1",
            "http_proxy": "http://127.0.0.1:1",
            "https_proxy": "http://127.0.0.1:1",
            "no_proxy": "",
        }

        if self.is_windows:
            try:
                return self._execute_windows_job(cmd, cwd, safe_env)
            except ImportError as e:
                raise RuntimeError("CRITICAL [DNA #27]: win32job/win32 modules missing on Windows. Fail-closed to prevent unisolated execution.") from e
            except TimeoutError:
                raise  # timeout là kết quả thực thi, không phải lỗi isolation
            except Exception as exc:
                # [Fail-Closed] Job Object setup failed — do NOT silently fall through.
                # Running a subprocess without isolation is worse than not running it.
                raise RuntimeError(
                    f"[SANDBOX] Windows Job Object isolation failed — refusing to execute without isolation. "
                    f"Reason: {exc}. Set SCP_SANDBOX_STRICT=0 to allow fallback (not recommended)."
                ) from exc

        # Non-Windows or fallback (win32 not installed)
        # [C2] Ưu tiên bwrap (cách ly namespace THẬT) trước khi hạ xuống rlimit.
        preexec = None
        if not self.is_windows:
            import platform as _plat
            if _plat.system() == "Linux":
                if not shutil.which("bwrap"):
                    raise RuntimeError("CRITICAL [DNA #27]: bwrap is missing on Linux. Fail-closed to prevent unisolated execution.")
                return subprocess.run(
                    build_bwrap_argv(cmd), cwd=cwd, capture_output=True, text=True,
                    timeout=15, env=safe_env,
                )
            # [SEC-FIX dead-branch 2026-09-26] The second `if _plat.system() ==
            # "Linux":` rlimit block below was DELETED: it sat after a branch
            # that either returns (bwrap present) or raises (bwrap missing), so
            # its body was unreachable on every path — sys.settrace over both
            # forced systems ("Linux"/"Darwin") executed none of its lines and
            # `preexec` was always None. Wiring it back would WEAKEN the Linux
            # contract (rlimit fallback is not a namespace sandbox, see
            # isolation_capability(): "rlimit_only_not_a_sandbox") — the
            # fail-closed DNA #27 behavior above is the intent.

        return subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=15,
            env=safe_env, preexec_fn=preexec
        )

    def write_bounded(self, capability_token: CapabilityToken, path: str, content: bytes) -> bool:
        if not self.authority.validate(capability_token):
            raise PermissionError("Write blocked by CapabilityAuthority")

        # Prevent path traversal
        from pathlib import Path
        abs_path = Path(path).resolve()
        cwd_path = Path(os.getcwd()).resolve()
        try:
            abs_path.relative_to(cwd_path)
        except ValueError:
            raise PermissionError(f"Path traversal escape attempt detected: {path}")

        with abs_path.open("wb") as f:
            f.write(content)
        return True
