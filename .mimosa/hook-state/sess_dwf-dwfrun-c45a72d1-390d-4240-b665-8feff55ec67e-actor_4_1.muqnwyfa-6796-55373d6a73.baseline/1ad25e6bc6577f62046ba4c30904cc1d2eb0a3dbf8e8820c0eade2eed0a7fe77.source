from pathlib import Path

"""Reality test 4-e-002 — Cổng A: HERMETIC BOOT với bằng chứng.

"Tính tất định môi trường": clone repo về một máy TRẮNG (không .env, không
Ollama, không cấu hình tay) → chỉ cần 3 secret ngẫu nhiên là server phải
boot và trả contract xác định. Test tự sinh env file cô lập (không đọc .env
của repo), boot thật trên port riêng, đối chiếu contract, rồi kill.

S17 (2026-09-13): hermetic contract đổi 2→3 secrets — commit `0c44c13`
(GAP-05/06/08/09 security hardening) làm `SCP_CAPABILITY_SECRET` thành
fail-closed bắt buộc (`scp/core/capability_token.py` raise MissingSecretError
ngay tại import; `.env.example` ghi "Required"). Yêu cầu bảo mật mới NGHIÊM
ngặt hơn → test phản ánh reality mới, vẫn giữ nguyên tính hermetic (secret
sinh ngẫu nhiên mỗi boot, không đọc repo .env, không network).

Bài học ghi tại đây (DNA #26): khi probe boot, stdout PHẢI ghi ra FILE —
dùng PIPE thì buffer 64KB đầy, logging block event loop, mọi request treo
(đã gặp thật khi viết test này — chính là một reality finding).

DNA #1 (Reality > Model) #12 (thử nhỏ tái lập được) #23 (khai báo giới hạn —
hermetic miniature 1 process, không phải orchestration 10.000 node).
"""

import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.request import urlopen as _url_open

ROOT = Path(__file__).resolve().parents[2]
PORT = 8047
BASE = f"http://127.0.0.1:{PORT}"


def _get(url: str, timeout: float = 5.0) -> tuple[int, dict]:
    try:
        with _url_open(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except Exception:
        return 0, {}


def main() -> int:
    # ignore_cleanup_errors: Windows giữ lock boot.log vài giây sau khi
    # TerminateProcess process con — dọn temp không được phép làm đỏ test
    # khi mọi assertion đã PASS (DNA #26: reality của assertion > hygiene).
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        env_file = Path(tmp) / "hermetic.env"
        env_file.write_text(
            f"SCP_JWT_SECRET={secrets.token_hex(32)}\n"
            f"SCP_ADMIN_KEY={secrets.token_urlsafe(24)}\n"
            # S17: GAP-09 (commit 0c44c13) made this secret fail-closed at
            # import (capability_token.get_capability_secret). Random per
            # boot keeps the boot hermetic AND the security posture intact.
            f"SCP_CAPABILITY_SECRET={secrets.token_hex(32)}\n",
            encoding="utf-8",
        )
        boot_log = Path(tmp) / "boot.log"
        env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "PATH": os.environ.get("PATH", ""),
            "TEMP": str(tmp),
            "TMP": str(tmp),
            "SCP_ENV_FILE": str(env_file),
            "PYTHONUTF8": "1",
        }
        with boot_log.open("w", encoding="utf-8") as log_handle:
            proc = subprocess.Popen(
                [sys.executable, "-X", "utf8", "-m", "scp", str(PORT)],
                cwd=str(ROOT), env=env, stdout=log_handle, stderr=subprocess.STDOUT,
            )
            try:
                # 1. Liveness — /health phải 200 trong 40s với contract xác định.
                code, health = 0, {}
                deadline = time.time() + 40
                while time.time() < deadline:
                    code, health = _get(f"{BASE}/health")
                    if code == 200:
                        break
                    time.sleep(1)
                assert code == 200, "FAIL: /health không 200 trong 40s (hermetic boot gãy)"
                identity = health.get("service_identity", {})
                assert identity.get("host") == "127.0.0.1", f"FAIL: bind sai host: {identity}"
                assert identity.get("configured_port") == PORT, f"FAIL: port contract: {identity}"
                assert isinstance(identity.get("pid"), int), "FAIL: pid contract"
                assert str(health.get("version", "")).count(".") >= 1, "FAIL: version contract"
                print(f"PASS [1/3]: hermetic /health 200 - identity port={identity.get('configured_port')} pid={identity.get('pid')}")

                # 2. Readiness — judge sẵn sàng mà KHÔNG cần Ollama/network.
                deadline = time.time() + 30
                ready_code, ready = 0, {}
                while time.time() < deadline:
                    ready_code, ready = _get(f"{BASE}/ready")
                    if ready_code == 200:
                        break
                    time.sleep(1)
                assert ready_code == 200, "FAIL: /ready không 200 trong 30s — judge init phụ thuộc thứ gì đó ngoài env file"
                assert ready.get("checks", {}).get("judge") == "ok", f"FAIL: judge not ok: {ready}"
                print("PASS [2/3]: /ready 200 - judge ready in hermetic env")

                # 3. API-only: boot log không được có vết gọi LLM cục bộ 11434.
                boot_text = boot_log.read_text(encoding="utf-8", errors="replace")
                assert "11434" not in boot_text, "FAIL: boot vẫn chạm 11434 (Ollama ghost)"
                print("PASS [3/3]: boot log sach - khong cham Ollama (API-onlyReality)")
                print("\nOK Reality test 4-e-002 PASSED - hermetic boot tren moi truong trang")
                return 0
            finally:
                try:
                    proc.kill()
                except Exception:
                    pass


if __name__ == "__main__":
    raise SystemExit(main())
