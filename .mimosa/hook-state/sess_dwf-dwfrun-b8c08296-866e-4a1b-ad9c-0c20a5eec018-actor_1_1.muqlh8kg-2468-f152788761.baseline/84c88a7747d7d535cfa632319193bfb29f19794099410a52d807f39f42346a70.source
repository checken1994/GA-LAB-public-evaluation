"""OpenTelemetry integration for SCP V3 Enterprise.

[F-07 2026-09-25] Runtime audit RUNTIME-AUDIT-20260925-0411 F-07: OTel span
JSON (service.name=unknown_service) was printed to stdout on every request
while the boot log simultaneously said '[OTel] tracing disabled:
SCP_OTEL_ENABLED=0' — because setup_telemetry() unconditionally installed a
TracerProvider + BatchSpanProcessor(ConsoleSpanExporter()) with NO Resource
(implicit service.name=unknown_service), regardless of the flag.

Contract now (single source of truth for the flag lives in
scp.observability.otel.otel_flag_enabled):
  * SCP_OTEL_ENABLED != "1"  →  install NOTHING (no tracer provider, no
    console span processor, no FastAPI instrumentation) and return None —
    no span output at all, consistent with the 'tracing disabled' log line;
  * SCP_OTEL_ENABLED == "1"  →  provider carries a real Resource with
    service.name = SCP_OTEL_SERVICE_NAME (default 'scp-backend', matching the
    /health service_identity) — never the implicit 'unknown_service'.
"""
import logging
import os

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from scp.observability.otel import otel_flag_enabled

logger = logging.getLogger(__name__)

DEFAULT_SERVICE_NAME = "scp-backend"


def setup_telemetry(app):
    """Install console tracing ONLY when SCP_OTEL_ENABLED=1 (F-07 contract).

    Returns the TracerProvider when tracing is enabled, or None when disabled
    (callers must tolerate None — api_server.py wraps this call in try/except
    and only logs).
    """
    if not otel_flag_enabled():
        logger.info(
            "[OTel] tracing disabled: SCP_OTEL_ENABLED=%r — no tracer provider, "
            "no console exporter installed",
            os.environ.get("SCP_OTEL_ENABLED", "0"),
        )
        return None
    # Real service identity — a bare TracerProvider() would surface as
    # service.name=unknown_service in every exported span (the F-07 symptom).
    service_name = os.environ.get("SCP_OTEL_SERVICE_NAME", DEFAULT_SERVICE_NAME)
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": service_name,
                "service.version": os.environ.get("SCP_MODEL_VERSION", "unknown"),
            }
        )
    )
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    return provider
