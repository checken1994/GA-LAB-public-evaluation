import os

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from scp.observability import telemetry as telemetry_mod
from scp.observability.otel import configure_fastapi_otel, otel_flag_enabled


def test_otel_disabled_by_default():
    os.environ["SCP_OTEL_ENABLED"] = "0"
    app = FastAPI()
    result = configure_fastapi_otel(app)
    assert result["enabled"] is False
    assert result["reason"] == "SCP_OTEL_ENABLED=0"

def test_otel_enabled_without_endpoint_fails_safe():
    os.environ["SCP_OTEL_ENABLED"] = "1"
    os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    app = FastAPI()
    result = configure_fastapi_otel(app)
    assert result["enabled"] is False
    assert "missing" in result["reason"].lower()


# ------------------------------------------------------------------
# [F-07 2026-09-25] setup_telemetry must honor the SAME flag as
# configure_fastapi_otel: flag off → nothing installed at all (no console
# span processor, no instrumentation), flag on → real service.name.
# ------------------------------------------------------------------

class _FakeExporter:
    """Minimal exporter stand-in (BatchSpanProcessor calls these on shutdown)."""

    def export(self, spans):
        return 0  # EXPORT_SUCCESS

    def shutdown(self):
        return None

    def force_flush(self, timeout_millis=None):
        return True


def test_otel_flag_predicate_matches_disable_reason(monkeypatch):
    monkeypatch.setenv("SCP_OTEL_ENABLED", "0")
    assert otel_flag_enabled() is False
    monkeypatch.setenv("SCP_OTEL_ENABLED", "1")
    assert otel_flag_enabled() is True


def test_setup_telemetry_installs_nothing_when_flag_off(monkeypatch):
    """[F-07] SCP_OTEL_ENABLED=0 → no tracer provider, no console span
    processor, no FastAPI instrumentation, None returned — no span output at
    all, consistent with the '[OTel] tracing disabled' log line."""
    monkeypatch.setenv("SCP_OTEL_ENABLED", "0")

    def _must_not_construct(*args, **kwargs):
        raise AssertionError("telemetry constructor invoked while tracing is disabled")

    instrumented: list = []
    monkeypatch.setattr(telemetry_mod, "TracerProvider", _must_not_construct)
    monkeypatch.setattr(telemetry_mod, "BatchSpanProcessor", _must_not_construct)
    monkeypatch.setattr(telemetry_mod, "ConsoleSpanExporter", _must_not_construct)
    monkeypatch.setattr(
        FastAPIInstrumentor, "instrument_app", lambda app, **kwargs: instrumented.append(app)
    )

    app = FastAPI()
    assert telemetry_mod.setup_telemetry(app) is None
    assert instrumented == [], "FastAPI must not be instrumented while tracing is disabled"


def test_setup_telemetry_enabled_uses_real_service_name(monkeypatch):
    """[F-07] Flag on → the provider carries a real Resource service.name
    (default 'scp-backend', never the implicit 'unknown_service') and the
    console exporter IS registered; the global tracer provider is captured,
    not asserted, to avoid cross-test global state."""
    monkeypatch.setenv("SCP_OTEL_ENABLED", "1")
    monkeypatch.delenv("SCP_OTEL_SERVICE_NAME", raising=False)
    monkeypatch.delenv("SCP_MODEL_VERSION", raising=False)

    object()
    monkeypatch.setattr(telemetry_mod, "ConsoleSpanExporter", _FakeExporter)

    real_processor_cls = telemetry_mod.BatchSpanProcessor
    wired = {}

    def fake_processor(exporter):
        wired["exporter"] = exporter
        return real_processor_cls(exporter)

    monkeypatch.setattr(telemetry_mod, "BatchSpanProcessor", fake_processor)

    set_calls: list = []
    monkeypatch.setattr(telemetry_mod.trace, "set_tracer_provider", lambda p: set_calls.append(p))

    instrumented: list = []
    monkeypatch.setattr(
        FastAPIInstrumentor, "instrument_app", lambda app, **kwargs: instrumented.append(app)
    )

    app = FastAPI()
    provider = telemetry_mod.setup_telemetry(app)
    assert provider is not None
    assert dict(provider.resource.attributes)["service.name"] == "scp-backend"
    assert isinstance(wired["exporter"], _FakeExporter), "console exporter must be registered when tracing is enabled"
    assert set_calls and set_calls[0] is provider
    assert instrumented == [app]


def test_setup_telemetry_enabled_service_name_from_config(monkeypatch):
    """[F-07] SCP_OTEL_SERVICE_NAME overrides the default service.name."""
    monkeypatch.setenv("SCP_OTEL_ENABLED", "1")
    monkeypatch.setenv("SCP_OTEL_SERVICE_NAME", "scp-backend-staging")

    monkeypatch.setattr(telemetry_mod, "ConsoleSpanExporter", _FakeExporter)
    real_processor_cls = telemetry_mod.BatchSpanProcessor
    monkeypatch.setattr(
        telemetry_mod, "BatchSpanProcessor", lambda exporter: real_processor_cls(exporter)
    )
    monkeypatch.setattr(telemetry_mod.trace, "set_tracer_provider", lambda p: None)
    monkeypatch.setattr(
        FastAPIInstrumentor, "instrument_app", lambda app, **kwargs: None
    )

    app = FastAPI()
    provider = telemetry_mod.setup_telemetry(app)
    assert provider is not None
    assert dict(provider.resource.attributes)["service.name"] == "scp-backend-staging"
