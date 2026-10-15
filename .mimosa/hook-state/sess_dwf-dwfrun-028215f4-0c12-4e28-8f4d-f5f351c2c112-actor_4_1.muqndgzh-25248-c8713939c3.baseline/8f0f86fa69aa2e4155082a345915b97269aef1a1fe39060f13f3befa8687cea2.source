"""[AUDIT-FIX 2026-09-29 — on-demand probe, KHÔNG nằm trong pytest testpaths]

Old-code-fail evidence for commit 1def66c1 (numeric IPv4 spelling bypass of
the cloud-metadata egress block). Chạy thủ công khi cần tái hiện:

    python scripts/probe_egress_numeric_spelling_old_code.py

Chứng minh (đối chiếu archive egress @ 9d1efc81 — cây NGAY TRƯỚC fix):
  is_cloud_metadata('2852039166') == False  và
  enforce('http://2852039166/latest/meta-data') KHÔNG raise  → ALLOWED.
Lý do tồn tại dạng script thay vì pytest test: một test cố ý fail làm đỏ
suite chuẩn vĩnh viễn (Agent5 F6a BLOCKER) — evidence chuyển sang
run-on-demand; archive nằm trong repo (F6b: tái lập được từ clean checkout).

Exit 0 = old bug tái hiện đúng như tài liệu (evidence hợp lệ).
Exit 1 = archive không tái hiện được old behavior → probe inconclusive,
         KHÔNG dùng làm bằng chứng (fail-loud, không bao giờ pass rỗng).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ARCHIVE = REPO / ".openclaw" / "probes" / "egress_prefix_9d1efc81.py"


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location("egress_prefix_probe", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["egress_prefix_probe"] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    if not ARCHIVE.is_file():
        print(f"[INCONCLUSIVE] archived pre-fix module missing: {ARCHIVE}")
        return 1
    old = _load_module(ARCHIVE)
    policy = old.EgressPolicy(mode=old.EgressMode.OPEN, production_mode=False)

    blocked = policy.is_cloud_metadata("2852039166")
    denied = False
    try:
        policy.enforce("http://2852039166/latest/meta-data")
    except old.EgressDeniedError:
        denied = True

    if blocked or denied:
        print("[INCONCLUSIVE] archived pre-fix copy unexpectedly blocks the "
              "decimal spelling — archive mismatch, evidence invalid.")
        return 1

    print("[OLD-CODE-FAIL CONFIRMED @ 9d1efc81]")
    print("  is_cloud_metadata('2852039166') = False (169.254.169.254 decimal)")
    print("  enforce('http://2852039166/latest/meta-data') = ALLOWED in OPEN mode")
    print("  →IMDS reachable via spelling; fixed by 1def66c1 "
          "(_numeric_host_to_ip normalize-and-recheck).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
