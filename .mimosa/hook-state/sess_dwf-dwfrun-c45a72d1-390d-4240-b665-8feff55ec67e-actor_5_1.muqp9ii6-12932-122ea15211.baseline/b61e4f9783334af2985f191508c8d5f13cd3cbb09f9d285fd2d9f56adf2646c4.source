"""Sandbox Evaluator service loop (Track C3 — compose profile ``sandbox``).

Chạy như một service riêng: consume ``EVAL_REQUEST`` từ Pg event bus (bảng
durable ``scp_events`` + NOTIFY chỉ là chuông — Track C2), chạy ``evaluate()``
(pytest thật trên workspace tạm), publish ``EVAL_RESULT`` về cùng channel
``scp_eval``.

Delivery semantics (kế thừa PgEventBus):
- at-least-once -> handler PHẢI idempotent: evaluate() thuần túy (workspace
  tạm trong system temp, không đụng repo sống) nên chạy lại là vô hại.
- handler lỗi -> retry tối đa ``max_attempts`` rồi dead-letter (poison guard) —
  payload malformed KHÔNG bao giờ block channel vĩnh viễn.
- service chết giữa chừng -> event vẫn durable trong bảng; khi sống lại
  ``start_at="beginning"`` replay mọi event chưa delivered (mất NOTIFY không
  mất event).

Fail-closed khởi động:
- ``SCP_EVENT_BUS_ENABLED`` không truthy -> exit 2 với lý do rõ (service
  opt-in, KHÔNG chạy nửa vời không có bus).
- ``SCP_EVENT_BUS_ENABLED`` truthy nhưng thiếu ``SCP_EVENT_BUS_DSN`` ->
  make_event_bus raise RuntimeError (fail-closed theo Track C2) -> exit 2.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import threading

from scp.event_bus_pg import PgEventBus, make_event_bus
from scp.sandbox_evaluator.evaluator import (
    CHANNEL_EVAL,
    EVENT_EVAL_REQUEST,
    evaluate,
)
from scp.sandbox_evaluator.events import build_eval_result_payload

logger = logging.getLogger("scp.sandbox_evaluator.loop")

_POLL_ENV = "SCP_SANDBOX_EVALUATOR_POLL_SECONDS"
_POLL_DEFAULT = 5
_POLL_MIN = 1
_POLL_MAX = 600


def make_handler(bus: PgEventBus):
    """Build handler idempotent cho channel ``scp_eval``."""

    def handler(event) -> None:
        payload = event.payload
        if not isinstance(payload, dict):
            # Poison payload: raise -> retry -> dead-letter sau max_attempts
            # (poison guard của PgEventBus), không block channel vĩnh viễn.
            raise ValueError(
                f"EVAL_REQUEST payload phải là dict, nhận {type(payload).__name__}"
            )
        if payload.get("type") != EVENT_EVAL_REQUEST:
            # Channel dùng chung: EVAL_RESULT (hoặc traffic lạ) -> bỏ qua.
            logger.debug("sandbox evaluator loop: bỏ qua event type=%r", payload.get("type"))
            return
        patch_target = {
            "files": payload.get("files") or {},
            "extra_files": payload.get("extra_files") or {},
            "test_files": payload.get("test_files") or {},
            "timeout_seconds": payload.get("timeout_seconds"),
        }
        result = evaluate(patch_target)
        out = build_eval_result_payload(
            result,
            request_id=payload.get("request_id"),
            job_id=payload.get("job_id"),
            evaluator="sandbox-evaluator-service",
        )
        bus.publish(CHANNEL_EVAL, out, correlation_id=event.correlation_id)

    return handler


def _poll_seconds() -> float:
    raw = os.environ.get(_POLL_ENV, "").strip()
    try:
        value = float(raw) if raw else _POLL_DEFAULT
    except ValueError:
        logger.warning("%s=%r không phải số — dùng default %ss", _POLL_ENV, raw, _POLL_DEFAULT)
        value = _POLL_DEFAULT
    return max(_POLL_MIN, min(_POLL_MAX, value))


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        bus = make_event_bus()
    except RuntimeError as exc:
        # Fail-closed theo Track C2 (enabled nhưng thiếu DSN): exit rõ ràng,
        # không idle không bus, không fallback im lặng.
        print(json.dumps({"service": "sandbox-evaluator", "status": "exited", "reason": str(exc)}))
        return 2
    if bus is None:
        # Fail-closed: service này KHÔNG có chế độ idle không bus.
        print(json.dumps({
            "service": "sandbox-evaluator",
            "status": "exited",
            "reason": "SCP_EVENT_BUS_ENABLED không truthy — service là opt-in; "
                      "khởi động nó phải kèm event bus (fail-closed, không chạy nửa vời)",
        }))
        return 2

    logger.info("sandbox evaluator: event bus %s", bus.redacted_dsn())
    bus.ensure_schema()

    stop = threading.Event()

    def _request_stop(signum, _frame):
        logger.info("sandbox evaluator: nhận signal %s — dừng sau poll cycle hiện tại", signum)
        stop.set()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    poll = _poll_seconds()
    logger.info("sandbox evaluator: subscribe channel=%s poll=%ss start_at=beginning", CHANNEL_EVAL, poll)
    stats = bus.subscribe_poll(
        CHANNEL_EVAL,
        make_handler(bus),
        poll_interval=poll,
        stop_event=stop,
        start_at="beginning",  # replay mọi EVAL_REQUEST chưa delivered sau downtime
    )
    print(json.dumps({"service": "sandbox-evaluator", "status": "stopped", "stats": stats}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
