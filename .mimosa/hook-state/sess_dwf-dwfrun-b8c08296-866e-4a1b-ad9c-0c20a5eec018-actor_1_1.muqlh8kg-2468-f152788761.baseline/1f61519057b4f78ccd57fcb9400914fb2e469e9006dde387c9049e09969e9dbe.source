"""Optional OpenTelemetry wiring for SCP HTTP traces.

The default is disabled. When enabled, SCP exports only route/method/status
spans and deliberately does not capture request headers, query strings, body,
or media payloads. Missing OTel packages or endpoint configuration degrades to
an explicit disabled state instead of blocking the API.
"""
from __future__ import annotations

import logging
import os
from typing import Any


def otel_flag_enabled() -> bool:
    """[F-07 2026-09-25] Single source of truth for the SCP_OTEL_ENABLED flag.

    Both the OTLP wiring (configure_fastapi_otel) and the console telemetry
    (scp.observability.telemetry.setup_telemetry) must agree on this flag —
    previously the log could say 'tracing disabled: SCP_OTEL_ENABLED=0' while
    an unrelated console exporter was still running (runtime audit
    RUNTIME-AUDIT-20260925-0411 F-07)."""
    return os.environ.get("SCP_OTEL_ENABLED", "0").strip() == "1"


def configure_fastapi_otel(app: Any) -> dict[str, Any]:
    if not otel_flag_enabled():
        return {"enabled": False, "reason": "SCP_OTEL_ENABLED=0"}
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        return {"enabled": False, "reason": "OTEL_EXPORTER_OTLP_ENDPOINT is missing"}
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        return {"enabled": False, "reason": f"OTel packages unavailable: {type(exc).__name__}"}

    try:
        provider = TracerProvider(resource=Resource.create({
            "service.name": os.environ.get("SCP_OTEL_SERVICE_NAME", "scp-backend"),
            "service.version": os.environ.get("SCP_MODEL_VERSION", "unknown"),
        }))
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls=os.environ.get("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS", "health,metrics"),
            http_capture_headers_server_request=[],
            http_capture_headers_server_response=[],
            http_capture_headers_sanitize_fields=["authorization", "cookie", "set-cookie"],
        )
        return {"enabled": True, "service_name": os.environ.get("SCP_OTEL_SERVICE_NAME", "scp-backend"), "endpoint_configured": True}
    except Exception as exc:
        logger.warning("OTel FastAPI instrumentation setup failed: %s", exc, exc_info=True)
        return {"enabled": False, "reason": f"OTel setup failed: {type(exc).__name__}"}


logger = logging.getLogger(__name__)

__all__ = ["configure_fastapi_otel"]
