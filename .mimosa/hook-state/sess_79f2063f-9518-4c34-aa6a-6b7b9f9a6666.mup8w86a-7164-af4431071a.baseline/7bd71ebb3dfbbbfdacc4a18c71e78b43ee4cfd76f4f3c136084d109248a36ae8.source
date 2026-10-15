#!/usr/bin/env python
"""TypeSafe AI evaluation CLI — công cụ độc lập của quy trình làm việc.

KHÔNG thuộc code sản phẩm SCP: script này không import package `scp`,
chỉ gọi thẳng POST https://api.typesafe.ai/v1/systemone (typed evaluation:
noul/choice/score — xem docs.typesafe.ai/api).

Cách dùng nhanh:
    export TYPESAFE_API_KEY=...        # tạo key tại https://console.typesafe.ai/keys
    python tools/typesafe_eval.py --demo
    python tools/typesafe_eval.py --state "Ticket: charged twice, angry customer" \
        --noul billing="Is this about billing?" \
        --choice tone=calm|frustrated|angry \
        --score urgency="can wait|this week|today"

Key được đọc từ biến môi trường TYPESAFE_API_KEY; nếu không có, script thử
đọc từ file .env ở repo root (giải quyết động theo vị trí file, không hardcode
đường dẫn người dùng). Key không bao giờ được in ra stdout/stderr.

Exit codes (fail-closed, không retry tự động trong v1):
    0 OK · 1 lỗi khác · 2 auth (401) · 3 validation (422) · 4 rate-limit (429/529)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

DEFAULT_BASE_URL = "https://api.typesafe.ai"
DEFAULT_MODEL = "jev-latest"
DEFAULT_TIMEOUT = 30.0
REPO_ROOT = Path(__file__).resolve().parents[2]


def load_api_key() -> str:
    """Đọc key từ env; fallback parse .env ở repo root (chỉ biến TYPESAFE_API_KEY)."""
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if key:
        return key
    env_file = REPO_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("TYPESAFE_API_KEY="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value
    return ""


def build_questions(args: argparse.Namespace) -> dict:
    questions: dict = {}
    for spec in args.noul or []:
        name, _, instructions = spec.partition("=")
        if not name or not instructions:
            raise SystemExit(f"--noul cần dạng name='câu hỏi': {spec!r}")
        questions[name] = {"type": "noul", "instructions": instructions}
    for spec in args.choice or []:
        name, _, options = spec.partition("=")
        opts = [o for o in options.split("|") if o]
        if not name or len(opts) < 2:
            raise SystemExit(f"--choice cần dạng name=opt1|opt2|...: {spec!r}")
        # Wire format thật (422 2026-09-21): choice dùng field `criteria` là
        # map option -> mô tả (null nếu không có mô tả), không phải `options`.
        questions[name] = {
            "type": "choice",
            "instructions": "Choose one.",
            "criteria": {opt: None for opt in opts},
        }
    for spec in args.score or []:
        name, _, levels = spec.partition("=")
        lvls = [l for l in levels.split("|") if l]
        if not name or len(lvls) < 2:
            raise SystemExit(f"--score cần dạng name=level1|level2|...: {spec!r}")
        # SDK docs: Score dùng `criteria` là danh sách mức có thứ tự.
        questions[name] = {"type": "score", "instructions": "Rate the level.", "criteria": lvls}
    if not questions:
        raise SystemExit("Cần ít nhất một câu hỏi: --noul / --choice / --score (hoặc --demo).")
    return questions


def demo_payload() -> dict:
    return {
        "state": (
            "Hi, I've been trying to connect my Stripe account for 3 days and the "
            "integration keeps failing. I'm losing sales. Please help ASAP."
        ),
        "model": DEFAULT_MODEL,
        "questions": {
            "is_urgent": {"type": "noul", "instructions": "Does this message express urgency?"},
            "department": {
                "type": "choice",
                "instructions": "Which department should handle this?",
                "criteria": {"technical": None, "sales": None, "billing": None},
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="TypeSafe AI evaluation CLI (docs.typesafe.ai/api)")
    parser.add_argument("--state", help="Nội dung cần đánh giá (string); bỏ trống khi dùng --demo hoặc --file")
    parser.add_argument("--file", help="Đường dẫn file chứa nội dung cần đánh giá (ví dụ diff, plan, file log)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--noul", action="append", metavar="NAME='QUESTION'")
    parser.add_argument("--choice", action="append", metavar="NAME=opt1|opt2|...")
    parser.add_argument("--score", action="append", metavar="NAME=level1|level2|...")
    parser.add_argument("--base-url", default=os.environ.get("TYPESAFE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--demo", action="store_true", help="Chạy ví dụ quickstart không cần --state")
    args = parser.parse_args()

    state_text = args.state or ""
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_file():
            raise SystemExit(f"File không tồn tại: {args.file}")
        state_text = file_path.read_text(encoding="utf-8", errors="replace")

    payload = demo_payload() if args.demo else {
        "state": state_text,
        "model": args.model,
        "questions": build_questions(args),
    }
    if not args.demo and not payload["state"]:
        raise SystemExit("Thiếu --state hoặc --file (hoặc dùng --demo).")
    if args.demo:
        payload["model"] = args.model

    api_key = load_api_key()
    if not api_key:
        print(
            "TYPESAFE_API_KEY chưa cấu hình. Tạo key tại https://console.typesafe.ai/keys "
            "rồi `export TYPESAFE_API_KEY=...` hoặc thêm vào .env ở repo root.",
            file=sys.stderr,
        )
        return 2

    url = f"{args.base_url.rstrip('/')}/v1/systemone"
    try:
        resp = httpx.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=args.timeout,
        )
    except httpx.HTTPError as exc:
        print(f"Lỗi transport khi gọi {url}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    # Reality probe 2026-09-21: thiếu key api.typesafe.ai trả 403
    # authentication_error (docs mô tả 401 — cả hai đều là nhánh auth).
    if resp.status_code in (401, 403):
        print(f"HTTP {resp.status_code} — key thiếu hoặc sai (kiểm tra TYPESAFE_API_KEY). "
              f"Body: {resp.text[:300]}", file=sys.stderr)
        return 2
    if resp.status_code == 422:
        print(f"422 Unprocessable Entity — body: {resp.text[:500]}", file=sys.stderr)
        return 3
    if resp.status_code in (429, 529):
        print(f"HTTP {resp.status_code} — rate-limit/overloaded, thử lại sau (backoff).", file=sys.stderr)
        return 4
    if resp.status_code >= 400:
        print(f"HTTP {resp.status_code} — body: {resp.text[:500]}", file=sys.stderr)
        return 1

    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
