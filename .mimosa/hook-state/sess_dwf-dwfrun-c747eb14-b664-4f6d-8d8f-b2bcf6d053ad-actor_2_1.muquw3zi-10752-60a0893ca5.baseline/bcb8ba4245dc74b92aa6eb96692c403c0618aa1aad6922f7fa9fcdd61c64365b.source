"""Event-driven seam cho SandboxEvaluator (Track C3, theo V2 + Track C2 bus).

Một channel duy nhất ``scp_eval`` chứa cả hai loại event (payload phân biệt
qua trường ``type``):

- ``EVAL_REQUEST``  — yêu cầu đánh giá TỰ-ĐỦ (self-contained): ``files`` +
  ``extra_files`` + ``test_files`` nhúng nội dung đầy đủ -> evaluator service
  có thể evaluate mà KHÔNG cần đọc repo, và replay sau downtime là an toàn
  (nội dung cố định trong payload, không phụ thuộc trạng thái đĩa).
- ``EVAL_RESULT``   — kết quả raw: verdict/reason/returncode + stdout/stderr
  (truncated có đánh dấu ở mức 32k chars/field — bounded resource; raw đầy đủ
  vẫn nằm ở EvalResult.to_dict() của producer).

Quy ước fail-closed:
- Publisher (worker) publish **best-effort có log loudly**: event bus là
  side-channel quan sát + trigger cho evaluator service; VERDICT GATE vẫn là
  lần evaluate() in-process — publish lỗi không bao giờ đổi verdict.
- EVAL_REQUEST quá giới hạn kích thước (5MB) KHÔNG được publish (tránh đẩy
  payload khổng lồ vào PG); in-process gate vẫn chạy bình thường.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path

from scp.sandbox_evaluator.evaluator import (
    EVENT_EVAL_REQUEST,
    EVENT_EVAL_RESULT,
    EvalResult,
    default_timeout_seconds,
)

logger = logging.getLogger("scp.sandbox_evaluator.events")

MAX_PAYLOAD_BYTES = 5 * 1024 * 1024  # publish guard: refuse oversized requests
MAX_EVENT_OUTPUT_CHARS = 32_000  # EVAL_RESULT stdout/stderr truncation bound


def build_eval_request_payload(
    patch_target: dict,
    *,
    job_id: str | None = None,
    producer: str = "deterministic_worker",
) -> dict | None:
    """Build payload EVAL_REQUEST tự-đủ; trả None nếu KHÔNG publish được
    (test path không đọc được hoặc payload vượt giới hạn) — caller log loudly.

    ``test_paths`` trên đĩa được nhúng vào ``test_files`` (nội dung đọc tại
    thời điểm publish) nên replay sau downtime vẫn đánh giá đúng bản vá đó.
    """
    test_files: dict[str, str] = dict(patch_target.get("test_files") or {})
    unembedded: list[str] = []
    for tp in patch_target.get("test_paths") or []:
        try:
            test_files[f"tests/{Path(str(tp)).name}"] = Path(str(tp)).read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError as exc:
            unembedded.append(str(tp))
            logger.warning(
                "sandbox evaluator: không nhúng được test path %s vào EVAL_REQUEST (%s)",
                tp, exc,
            )
    if unembedded:
        # Request phải tự-đủ; thiếu nguồn test -> không publish (gate in-process
        # không bị ảnh hưởng).
        return None

    payload = {
        "type": EVENT_EVAL_REQUEST,
        "request_id": uuid.uuid4().hex,
        "job_id": str(job_id) if job_id else None,
        "created_at": time.time(),
        "producer": producer,
        "files": dict(patch_target.get("files") or {}),
        "extra_files": dict(patch_target.get("extra_files") or {}),
        "test_files": test_files,
        "timeout_seconds": int(
            patch_target.get("timeout_seconds") or default_timeout_seconds()
        ),
    }
    size = len(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"))
    if size > MAX_PAYLOAD_BYTES:
        logger.warning(
            "sandbox evaluator: EVAL_REQUEST payload %d bytes > %d — không publish "
            "(side-channel guard); in-process gate vẫn chạy bình thường",
            size, MAX_PAYLOAD_BYTES,
        )
        return None
    return payload


def build_eval_result_payload(
    result: EvalResult,
    *,
    request_id: str | None = None,
    job_id: str | None = None,
    evaluator: str,
) -> dict:
    """Build payload EVAL_RESULT — raw stdout/stderr truncated có đánh dấu."""
    return {
        "type": EVENT_EVAL_RESULT,
        "request_id": request_id,
        "job_id": str(job_id) if job_id else None,
        "verdict": result.verdict,
        "reason": result.reason,
        "returncode": result.returncode,
        "timed_out": result.timed_out,
        "stdout": _truncate(result.stdout),
        "stderr": _truncate(result.stderr),
        "duration_seconds": round(result.duration_seconds, 3),
        "evaluator": evaluator,
        "finished_at": time.time(),
    }


def _truncate(text: str, limit: int = MAX_EVENT_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    head = text[: limit // 2]
    tail = text[-(limit // 2):]
    return f"{head}\n...[EVAL_RESULT truncated {len(text) - limit} chars]...\n{tail}"
