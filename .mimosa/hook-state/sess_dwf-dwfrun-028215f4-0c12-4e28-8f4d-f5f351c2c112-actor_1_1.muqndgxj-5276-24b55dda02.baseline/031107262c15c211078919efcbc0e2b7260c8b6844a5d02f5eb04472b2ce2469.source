# SCP CIRCUIT: M1 Boot & Background — STATUS: CLOSED (closure: docs/evidence-summary/M01-closure.json)
"""SCP API server composition root.

High-coupling request execution and lifespan orchestration live in
``scp.api_server_parts``.  The extracted functions are rebound to this module's
namespace so existing process-global state, monkeypatch points, and route
contracts remain authoritative here.
"""
from __future__ import annotations

from scp.security.env_loader import load_selected_env

load_selected_env()

import asyncio
import base64  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
import binascii  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
import logging
import os
import threading
import time  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
import types
from collections import deque
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from scp import __version__ as _SCP_VERSION
from scp.api_server_parts import _ask_impl as _ask_impl_part
from scp.api_server_parts import _async_fact_check as _async_fact_check_part
from scp.api_server_parts import lifespan as _lifespan_part
from scp.api_server_parts.helpers import (
    AskRequest,
    AskResponse,
    _extract_v98_context,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    _safe_fetch_url,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    get_judge,
)
from scp.core.real_learning_engine import RealLearningEngine
from scp.core.release_identity import (
    DOMAIN_EXPERT_ENSEMBLE_TERM,
    RELEASE_LABEL,
    public_release_metadata,
)
from scp.core.request_run_ledger import (  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    RequestRunLedger,
    stage_request,
    traced_request,
)
from scp.core.runtime_paths import runtime_data_dir, runtime_path
from scp.core.streaming_factcheck import StreamingFactChecker
from scp.meta.simple_explainer import SimpleExplainer
from scp.observability.telemetry import setup_telemetry
from scp.pc_control.pc_controller import default_kill_switch_path
from scp.runtime.judge import RealityJudge
from scp.security.attack_crawler import AttackCrawler
from scp.security.auth import verify_admin
from scp.security.cross_language_learner import CrossLanguageLearner
from scp.security.image_voice_detector import ImageJailbreakDetector, VoiceJailbreakDetector
from scp.security.jwt_guard import (  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    get_current_user,
    verify_jwt_token,
)
from scp.security.multi_turn_tracker import MultiTurnTracker
from scp.web_control.internet_search import (
    InternetSearch,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
)

logger = logging.getLogger("scp.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

from prometheus_client import REGISTRY

if "scp_request_count" in REGISTRY._names_to_collectors:
    REQUEST_COUNT = REGISTRY._names_to_collectors["scp_request_count"]
else:
    REQUEST_COUNT = Counter("scp_request_count", "Total SCP Requests", ["method", "endpoint"])

if "scp_request_latency_seconds" in REGISTRY._names_to_collectors:
    REQUEST_LATENCY = REGISTRY._names_to_collectors["scp_request_latency_seconds"]
else:
    REQUEST_LATENCY = Histogram("scp_request_latency_seconds", "Request latency", ["endpoint"])

_CACHED_COMMIT: str | None = None


def _scp_service_identity() -> dict:
    """Expose bounded runtime identity for local service/port verification.

    [F-02 audit-r2 2026-10-01] config_hash was REMOVED from this identity on
    purpose: /health is unauthenticated and used to return
    ``sha256(<.env contents>)`` — an offline cracking oracle for every secret
    living in the env file (SCP_ADMIN_KEY included). No auth-gated consumer
    needs it (grep-verified 2026-10-01: zero readers outside the stale test
    pin), so the hash is no longer computed at all instead of being moved.
    """
    global _CACHED_COMMIT
    import subprocess as _subprocess
    import sys as _sys
    from pathlib import Path as _Path

    # [IDENTITY-PORT-PRECEDENCE 2026-09-26] The bound socket follows
    # __main__.main() precedence: argv PORT > SCP_PORT env > 8000. The
    # identity MUST use the same precedence or it contradicts the socket:
    # with SCP_ENV_FILE set, load_selected_env() at module import re-applies
    # the env file's SCP_PORT AFTER main() resolved the argv port and wrote
    # it into os.environ — an env-first reader then advertised the env-file
    # port (e.g. 8000) while uvicorn bound the argv port (e.g. 8091).
    # argv-first keeps configured_port equal to the actually bound port for
    # every entry flow (`python -m scp [PORT]`, env-only boots, direct uvicorn).
    _port = None
    for _arg in _sys.argv[1:]:
        if _arg.isdigit() and 1 <= int(_arg) <= 65535:
            _port = int(_arg)
            break
    if _port is None and "SCP_PORT" in os.environ:
        _raw_port = os.environ["SCP_PORT"]
        try:
            _port = int(_raw_port)
        except (TypeError, ValueError) as _port_err:
            # [MACH1-FIX-8 / D6 fail-loudly] A malformed SCP_PORT silently
            # changed the advertised identity/port match — surface it.
            # [MACH1-FIX-9 / F7 log hygiene] Never log the raw env value, and
            # never log the exception message (ValueError embeds the raw value
            # in its text). Keep a length-bounded, control-character-free
            # preview so untrusted text cannot inject log lines.
            _port_text = _raw_port if isinstance(_raw_port, str) else f"<{type(_raw_port).__name__}>"
            _port_preview = "".join(
                _ch if _ch.isprintable() else "?" for _ch in _port_text[:24]
            )
            logger.warning(
                "[MACH1-FIX-8] SCP_PORT is not an integer (%s, len=%d, preview=%r) — falling back to argv/default",
                type(_port_err).__name__, len(_port_text), _port_preview,
            )
    if _port is None:
        _port = 8000
    _mode = os.environ.get("SCP_MODE")
    if not _mode:
        _mode = "production" if _port == 8000 else "test" if _port == 8001 else "unknown"
    if _CACHED_COMMIT is None:
        # [MACH1-FIX-6] Docker images have no .git — prefer the build-time
        # SCP_GIT_SHA ARG (baked into the image ENV) so the running container
        # can bind its runtime evidence to the exact source SHA.
        _env_sha = os.environ.get("SCP_GIT_SHA", "").strip()
        if _env_sha and _env_sha != "unknown":
            _commit = _env_sha
        else:
            try:
                _creationflags = getattr(_subprocess, "CREATE_NO_WINDOW", 0) if _sys.platform == "win32" else 0
                _commit = _subprocess.check_output(
                    ["git", "-C", str(_Path(__file__).resolve().parent.parent), "rev-parse", "HEAD"],
                    text=True,
                    stderr=_subprocess.DEVNULL,
                    timeout=2,
                    creationflags=_creationflags,
                ).strip()
            except Exception:
                logger.warning('_scp_service_identity: Exception not handled', exc_info=True)
                _commit = "unknown"
        _CACHED_COMMIT = _commit or "unknown"
    # [F-02 audit-r2 2026-10-01] The sha256(<.env>) computation that used to
    # live here was deleted together with the `config_hash` field: an
    # unauthenticated hash of the secret file lets a local probe brute-force
    # the admin key offline (probe → hash match → confirmed credential).
    return {
        "service_name": os.environ.get("SCP_SERVICE_NAME", "scp-backend"),
        "mode": _mode,
        "host": os.environ.get("SCP_HOST", "127.0.0.1"),
        "configured_port": _port,
        "pid": os.getpid(),
        "commit": _CACHED_COMMIT or "unknown",
        # [SEC-FIX /health-identity 2026-09-26] argv was dropped from the
        # identity on purpose: /health is unauthenticated and used to echo the
        # FULL command line — any secret ever passed via CLI (token, password,
        # connection string) would be exposed to every local caller. Port
        # precedence (argv PORT > SCP_PORT > 8000) is preserved in
        # `configured_port`; the raw argv is never disclosed.
        # [F-02 audit-r2 2026-10-01] config_hash dropped for the same reason
        # (sha256 of the .env file = offline cracking oracle).
    }


_REQUEST_RUN_LEDGER = RequestRunLedger()
_ASK_KERNEL_ADAPTERS: dict[tuple[str, str], Any] = {}
_ASK_KERNEL_ADAPTER_LOCK = threading.Lock()
_ASK_KERNEL_INIT_ERROR: Exception | None = None


def _ask_is_context_rag(req: AskRequest) -> bool:
    return bool(
        getattr(req, "rag_enabled", False)
        or getattr(req, "contexts", None)
        or str(getattr(req, "retrieved_context", "") or "").strip()
    )


def _ask_kernel_enabled(req: AskRequest) -> bool:
    return os.environ.get("SCP_ASK_KERNEL_ENABLED", "1") == "1"


def _question_routing_stats() -> dict:
    """[S24] Snapshot KPI question-router (LOOKUP→data-API fork). Fail-open:
    health endpoint không được chết vì counters."""
    try:
        from scp.runtime.question_router import route_stats_snapshot

        return route_stats_snapshot()
    except Exception as exc:
        logger.warning("[S24] routing stats unavailable: %s", exc, exc_info=True)
        return {"error": type(exc).__name__}


def _get_ask_kernel_adapter() -> Any:
    global _ASK_KERNEL_INIT_ERROR
    db_path = str(runtime_path("SCP_KERNEL_DB_PATH", "ask_task_kernel.sqlite3"))
    trace_path = str(runtime_path("SCP_KERNEL_TRACE_PATH", "ask_task_kernel_trace.jsonl"))
    key = (db_path, trace_path)
    with _ASK_KERNEL_ADAPTER_LOCK:
        if key in _ASK_KERNEL_ADAPTERS:
            return _ASK_KERNEL_ADAPTERS[key]
        try:
            from scp.ask_kernel_adapter import AskKernelAdapter
            adapter = AskKernelAdapter(db_path, trace_path)
            _ASK_KERNEL_ADAPTERS[key] = adapter
            return adapter
        except Exception as exc:
            _ASK_KERNEL_INIT_ERROR = exc
            logger.error("[ASK-KERNEL] durable adapter initialization failed: %s", type(exc).__name__, exc_info=True)
            return None


def _kernel_gate_unavailable_response(req: AskRequest, exc: Exception) -> AskResponse:
    return AskResponse(
        verdict="FAIL",
        final_answer="[SCP: Answer withheld — Kernel gate unavailable]",
        confidence=0.0,
        domain=req.domain_override or req.domain or "general",
        falsification_status="KERNEL_GATE_UNAVAILABLE",
        governance_decision="KILL",
        v98_guard={"mode": "rag-verified", "readOnly": True, "security_blocked": True, "kernel_error": type(exc).__name__},
        v98_classification={"provenance": "kernel_gate", "evidence_count": 0},
        elapsed_ms=0.0,
        session_id=req.session_id or "ask-kernel-unavailable",
        run_status="REJECTED",
        ledger_status="BLOCKED",
    )


def _pc_kill_switch_engaged() -> bool:
    """[F-RUN-01 audit-r2 2026-10-01] Read the PC-controller kill-switch flag.

    The flag file is written by ``POST /v3/pc/kill`` (PCController) and is the
    durable, cross-process authority. Before this gate the ask path never
    consulted it, so an engaged kill switch still let /ask run to COMPLETED
    (audit A9, OBSERVED). Fail-closed: if the flag's existence cannot be
    observed (OSError), the kill-switch state is UNKNOWN and the ask must be
    refused — a safety control whose state cannot be proven OFF is treated as
    ON (DNA fail-closed, INV fail-closed-when-unproven).
    """
    try:
        return default_kill_switch_path().exists()
    except OSError as exc:
        logger.error(
            "[F-RUN-01] kill-switch flag unreadable (%s: %s) — failing CLOSED",
            type(exc).__name__, exc,
        )
        return True


def _kill_switch_blocked_response(req: AskRequest) -> AskResponse:
    """Fail-closed /ask admission answer while the kill switch is engaged."""
    return AskResponse(
        verdict="FAIL",
        final_answer="[SCP: Answer withheld — Kill switch engaged (POST /v3/pc/kill)]",
        confidence=0.0,
        domain=req.domain_override or req.domain or "general",
        falsification_status="KILL_SWITCH_ENGAGED",
        governance_decision="KILL",
        v98_guard={"mode": "rag-verified", "readOnly": True, "security_blocked": True, "kill_switch": "engaged"},
        v98_classification={"provenance": "kill_switch_gate", "evidence_count": 0},
        elapsed_ms=0.0,
        session_id=req.session_id or "ask-kill-switch-blocked",
        run_status="REJECTED",
        ledger_status="BLOCKED",
    )


if TYPE_CHECKING:
    from scp.prediction.predictive import PredictiveOrchestrator as PredictiveEngine

try:
    from scp.api.chat import router as chat_router
    _CHAT_AVAILABLE = True
except ImportError as e:
    logger.warning("V104.48 Chat router unavailable: %s", e)
    _CHAT_AVAILABLE = False

_V98_V100_ROUTERS_AVAILABLE = False
v98_admin_router = None
v100_admin_router = None

try:
    from scp.core.fast_learning_engine import (  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        FastLearningEngine,
        start_fast_learning_thread,
    )
    _V1042_AVAILABLE = True
except ImportError as e:
    logger.warning("V104.2 FastLearningEngine unavailable: %s", e)
    _V1042_AVAILABLE = False

try:
    from scp.core.startup_optimizer import (
        STARTUP_DEFER_SECONDS,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        cleanup_data_directory,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        deferred_background_start,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        get_data_directory_stats,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        run_startup_optimization,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    )
    _V1043_AVAILABLE = True
except ImportError as e:
    logger.warning("V104.3 StartupOptimizer unavailable: %s", e)
    _V1043_AVAILABLE = False

try:
    from scp.core.data_partitioner import (
        DOMAIN_KEYWORDS,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        DOMAIN_TABLES,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        TTL_QUESTION_LOG,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        TTL_VERDICT_CACHE,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        TTL_VERDICT_CACHE_DB,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        BypassLessonsStore,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        DataPartitioner,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        ThreeTierCache,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        TTLExpirer,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        detect_domain,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
        migrate_old_to_new,  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    )
    _V1044_AVAILABLE = True
except ImportError as e:
    logger.warning("V104.4 DataPartitioner unavailable: %s", e)
    _V1044_AVAILABLE = False

_judge: RealityJudge | None = None
_judge_lock = threading.Lock()
_background_task: asyncio.Task | None = None
_attack_crawler: AttackCrawler | None = None
_multi_turn_tracker = MultiTurnTracker()
_image_detector = ImageJailbreakDetector()
_voice_detector = VoiceJailbreakDetector()
_cross_language_learner = CrossLanguageLearner()
_fact_checker = StreamingFactChecker()
_simple_explainer = SimpleExplainer()
_real_learning = RealLearningEngine(
    scp_db_path=str(runtime_path("SCP_DB_PATH", "v13.db")), data_dir=str(runtime_data_dir())
)
_fast_learning: FastLearningEngine | None = None
if _V1042_AVAILABLE:
    _fast_learning = FastLearningEngine(
        scp_db_path=str(runtime_path("SCP_DB_PATH", "v13.db")), data_dir=str(runtime_data_dir())
    )
_predictive_engine: PredictiveEngine | None = None
_async_factcheck_tasks: set = set()
_fact_check_retract_queue: deque[dict] = deque(maxlen=1000)


def _rebind_part_function(fn):
    """Execute extracted API code against this module's authoritative composition root state."""
    rebound = types.FunctionType(fn.__code__, globals(), fn.__name__, fn.__defaults__, fn.__closure__)
    rebound.__kwdefaults__ = fn.__kwdefaults__
    rebound.__annotations__ = dict(getattr(fn, "__annotations__", {}))
    rebound.__doc__ = fn.__doc__
    rebound.__module__ = __name__
    return rebound


_async_fact_check = _rebind_part_function(_async_fact_check_part._async_fact_check)
_ask_impl = _rebind_part_function(_ask_impl_part._ask_impl)
# [HIST-LEDGER-CONTRACT 2026-09-26] Rebind-namespace export: the rebound
# `_ask_impl` executes against THIS module's globals (see _rebind_part_function),
# so every global it references must live here — including the history-evidence
# helper its restored-subsystems hook calls. Importing it as a plain name would
# be flagged F401 (this is a namespace export, not an unused import).
_history_evidence_record = _ask_impl_part._history_evidence_record
# [F-RUN-02 audit-r2 2026-10-01] Namespace export (same rebind-namespace
# contract as `_history_evidence_record` above): the rebound `lifespan`
# executes against THIS module's globals, and its nested deep-audit scheduler
# body (`_deep_audit_loop`, defined inside lifespan.py) calls
# `deep_audit_boot_run_enabled()` at its first cycle. That name used to exist
# only in scp/api_server_parts/lifespan.py — the call raised NameError on
# EVERY boot (observed in docker logs), killing the deep-audit scheduler
# body before its 24h cadence loop could start. Export the flag reader here
# so the LOAD_GLOBAL resolves; the generic guard is pinned by
# tests/T02_contract/test_api_server_rebind_globals.py (walks every code
# object of all three rebound functions and asserts each LOAD_GLOBAL
# resolves — the whole missing-export class, not just this one name).
deep_audit_boot_run_enabled = _lifespan_part.deep_audit_boot_run_enabled
lifespan_raw = _rebind_part_function(getattr(_lifespan_part.lifespan, "__wrapped__", _lifespan_part.lifespan))
lifespan = asynccontextmanager(lifespan_raw)


class SimulationRequest(BaseModel):
    count: int = Field(50, ge=1, le=500)


try:
    from scp.api.routes.admin_v98 import router as v98_admin_router
    from scp.api.routes.admin_v100 import router as v100_admin_router
    _V98_V100_ROUTERS_AVAILABLE = True
except ImportError as e:
    logger.warning("[Task 7-A] V98/V100 admin routers unavailable: %s", e)
    _V98_V100_ROUTERS_AVAILABLE = False

try:
    from scp.api.dashboard_html import DASHBOARD_HTML
except ImportError as e:
    logger.warning("[Task 8-A] dashboard_html unavailable: %s", e)
    DASHBOARD_HTML = "<html><body>Dashboard unavailable</body></html>"

from scp.api.route_profile import resolve_api_profile, route_group_enabled

_API_PROFILE = resolve_api_profile()


def _route_enabled(group: str) -> bool:
    return route_group_enabled(group, _API_PROFILE)


_prod_mode = os.environ.get("SCP_PRODUCTION_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}
_enable_docs = os.environ.get("SCP_ENABLE_DOCS", "0" if _prod_mode else "1").strip().lower() in {"1", "true", "yes", "on"}

app = FastAPI(
    title=f"{RELEASE_LABEL} - Self-Correcting Pipeline API",
    description=f"{DOMAIN_EXPERT_ENSEMBLE_TERM} + FalsificationEngine + Governance + Chat + Evolution",
    version=_SCP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
    openapi_url="/openapi.json" if _enable_docs else None,
)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
try:
    setup_telemetry(app)
except Exception as e:
    logger.warning("Telemetry setup skipped: %s", e, exc_info=True)


@app.get("/metrics", dependencies=[Depends(verify_admin)])
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


_cors_origins_raw = os.environ.get("SCP_CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["http://localhost:3000"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
)
try:
    from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
    if os.environ.get("SCP_FORCE_HTTPS", "0") == "1":
        app.add_middleware(HTTPSRedirectMiddleware)
        logger.info("[Security] HTTPS redirect enabled (SCP_FORCE_HTTPS=1)")
    else:
        _bind_host = os.environ.get("SCP_HOST", "127.0.0.1")
        if _bind_host not in ("127.0.0.1", "localhost", "::1"):
            logger.warning("[Security] production deployment without HTTPS; configure TLS termination")
        else:
            logger.info("[Security] HTTPS redirect disabled (set SCP_FORCE_HTTPS=1 in prod)")
except ImportError:
    logger.debug("[Security] HTTPSRedirectMiddleware unavailable")
logger.info("[Security] CSRF protection: Bearer token auth")

if _CHAT_AVAILABLE and _route_enabled("chat"):
    app.include_router(chat_router, tags=["chat"])
if _V98_V100_ROUTERS_AVAILABLE and _route_enabled("versioned_admin"):
    app.include_router(v98_admin_router)
    app.include_router(v100_admin_router)

_EXTRA_ROUTERS_AVAILABLE = False
try:
    from scp.api.routes.evaluation_routes import router as evaluation_router
    from scp.api.routes.import_routes import router as import_router
    from scp.api.routes.openai_compat import router as openai_compat_router
    from scp.api.routes.swe_bench_routes import router as swe_bench_router
    from scp.api.routes.v102_v103_routes import router as v102_v103_router
    from scp.api.routes.v104_routes import router as v104_router
    from scp.api.routes.v105_routes import router as v105_router
    _EXTRA_ROUTERS_AVAILABLE = True
except ImportError as e:
    logger.warning("[Task 9-B] V102-V105/import routers unavailable: %s", e)

if _EXTRA_ROUTERS_AVAILABLE:
    if _route_enabled("openai_compat"):
        app.include_router(openai_compat_router)
    if _route_enabled("evaluation"):
        app.include_router(evaluation_router)
    if _route_enabled("versioned_admin"):
        app.include_router(v102_v103_router)
        app.include_router(v104_router)
        app.include_router(v105_router)
        app.include_router(swe_bench_router)
        try:
            from scp.api.routes.v106_routes import audit_router, capability_router
            app.include_router(audit_router)
            app.include_router(capability_router)
        except ImportError as _v106_err:
            # [MACH1-FIX-8 / D6 fail-loudly] A missing v106 module silently
            # drops the audit/capability route group — operators must see it.
            logger.warning("[Task 9-B] v106 audit/capability routers unavailable: %s", _v106_err)
    if _route_enabled("import"):
        app.include_router(import_router)

try:
    from scp.api.routes.control_routes import router as control_router
    if _route_enabled("control"):
        app.include_router(control_router, tags=["control"])
        _CONTROL_ROUTES_AVAILABLE = True
    else:
        _CONTROL_ROUTES_AVAILABLE = False
except ImportError as e:
    logger.warning("[SCP Control] Control router unavailable: %s", e)
    _CONTROL_ROUTES_AVAILABLE = False

for _group, _module_name, _router_name, _tags in (
    ("stream", "scp.api.routes.stream_routes", "router", ["stream"]),
    ("threat", "scp.api.routes.threat_routes", "router", ["threats"]),
    ("audit", "scp.api.routes.audit_routes", "router", ["audit"]),
    ("prediction", "scp.api.routes.prediction_routes", "router", ["predictions"]),
    # Wave-1: Restored subsystems
    ("risk_intelligence", "scp.api.routes.risk_routes", "router", ["risk-intelligence"]),
    ("world_state", "scp.api.routes.world_state_routes", "router", ["world-state"]),
    # Wave-2: Restored subsystems
    ("calibration", "scp.api.routes.calibration_routes", "router", ["calibration"]),
    ("forecast", "scp.api.routes.forecast_routes", "router", ["forecast"]),
    ("history", "scp.api.routes.history_routes", "router", ["history"]),
):
    try:
        if _route_enabled(_group):
            import importlib as _importlib
            _router = getattr(_importlib.import_module(_module_name), _router_name)
            app.include_router(_router, tags=_tags)
    except ImportError as _e:
        logger.warning("%s router unavailable: %s", _group, _e)

try:
    from scp.api.webhook import router as webhook_router
    if _route_enabled("webhook"):
        app.include_router(webhook_router)
        _WEBHOOK_ROUTER_AVAILABLE = True
    else:
        _WEBHOOK_ROUTER_AVAILABLE = False
except ImportError as e:
    logger.warning("[Task 42-B] Webhook router unavailable: %s", e)
    _WEBHOOK_ROUTER_AVAILABLE = False

try:
    from scp.api.routes.pc_controller_routes import router as pc_controller_router
    if _route_enabled("pc_controller"):
        app.include_router(pc_controller_router)
        _PC_CONTROLLER_AVAILABLE = True
    else:
        _PC_CONTROLLER_AVAILABLE = False
except ImportError as e:
    logger.warning("[V3.1] PC Controller router unavailable: %s", e)
    _PC_CONTROLLER_AVAILABLE = False

try:
    from scp.api.routes.web_control_routes import router as web_control_router
    if _route_enabled("web_control"):
        app.include_router(web_control_router)
        _WEB_CONTROL_AVAILABLE = True
    else:
        _WEB_CONTROL_AVAILABLE = False
except ImportError as e:
    logger.warning("[V3.1] Web control router unavailable: %s", e)
    _WEB_CONTROL_AVAILABLE = False


class TokenRequest(BaseModel):
    admin_key: str


@app.post("/auth/token")
@limiter.limit("5/minute")
def login_for_access_token(req: TokenRequest, request: Request):
    # [STEP0-FIX 2026-09-02] Fail-closed: the previous default "admin" let
    # anyone mint an admin JWT on deployments without SCP_ADMIN_KEY (P0,
    # verified live 2026-08-29). Unconfigured auth is a 401 authorization
    # failure, matching the canonical verify_admin contract in
    # scp/security/auth.py (no dev-mode bypass).
    expected_key = os.environ.get("SCP_ADMIN_KEY", "")
    import secrets as _secrets
    if not expected_key or not _secrets.compare_digest(req.admin_key.encode(), expected_key.encode()):
        raise HTTPException(status_code=401, detail="Incorrect admin key")
    from scp.security.jwt_guard import create_access_token
    access_token = create_access_token(data={"sub": "admin"})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/ask", response_model=AskResponse)
@limiter.limit("60/minute")
@traced_request(_REQUEST_RUN_LEDGER)
async def ask(req: AskRequest, request: Request, current_user: Any = Depends(verify_jwt_token)):
    REQUEST_COUNT.labels(method="POST", endpoint="/ask").inc()
    # [F-RUN-01 audit-r2 2026-10-01] Kill-switch admission gate — placed BEFORE
    # every other check (judge readiness, kernel adapter) because an engaged
    # kill switch is an absolute stop: no kernel task may be created, leased
    # or completed while it is engaged (audit A9 observed /ask reaching
    # COMPLETED after POST /v3/pc/kill). Kernel-level enforcement additionally
    # engages taskkernel.set_global_kill(True) on the live adapters (see
    # pc_controller_routes._engage_kernel_global_kill); this file-flag gate is
    # the process-independent authority that also covers adapters created
    # after the kill was engaged.
    if _pc_kill_switch_engaged():
        logger.warning(
            "[F-RUN-01] /ask refused: kill switch engaged (falsification_status=KILL_SWITCH_ENGAGED)"
        )
        return _kill_switch_blocked_response(req)
    # [MACH1-FIX-4] Fail-closed judge gate (matches the /readiness contract and
    # the lifespan comment "/ask returns 503 until ready"). Without this, a
    # request arriving before the judge is ready triggered a blocking 30-60s
    # lazy init inside the request path.
    if not getattr(app.state, "judge_ready", False):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "judge_initializing",
                "reason": getattr(app.state, "readiness_reason", None) or "judge_initialization_pending",
                "retry_after_seconds": 5,
            },
        )
    if not _ask_kernel_enabled(req):
        return _kernel_gate_unavailable_response(req, RuntimeError("rag_kernel_disabled"))
    adapter = _get_ask_kernel_adapter()
    if adapter is None:
        return _kernel_gate_unavailable_response(
            req,
            _ASK_KERNEL_INIT_ERROR or RuntimeError("kernel_adapter_unavailable"),
        )
    return await adapter.run_rag(req, request, _ask_impl)


try:
    from scp.api_server_parts._trace_impl import router as trace_router
    if _route_enabled("trace"):
        app.include_router(trace_router, tags=["trace"])
        _TRACE_AVAILABLE = True
    else:
        _TRACE_AVAILABLE = False
except ImportError as e:
    logger.warning("[SCP Trace] Trace router unavailable: %s", e)
    _TRACE_AVAILABLE = False


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(DASHBOARD_HTML)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service_identity": _scp_service_identity(),
        "version": _SCP_VERSION,
        "release": public_release_metadata(),
        "routes": len(app.routes),
        "modules": "136+ Python files",
        "note": "minimal health — use /health/detailed for full status",
    }


# [SEC-FIX /health-authz 2026-09-26] /health/detailed discloses internals
# (data dir size, tracker stats, sandbox capability, routing stats). It now
# requires admin auth like /metrics does; plain /health stays unauthenticated
# and minimal for liveness probes.
@app.get("/health/detailed", dependencies=[Depends(verify_admin)])
async def health_detailed():
    try:
        judge = get_judge()
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        db_size = 0
        if os.path.exists(data_dir):
            for filename in os.listdir(data_dir):
                filepath = os.path.join(data_dir, filename)
                if os.path.isfile(filepath):
                    db_size += os.path.getsize(filepath)
        _sched_started = getattr(app.state, "background_scheduler_started", False)
        from scp.security.os_sandbox import isolation_capability
        return {
            "status": "ok",
            "version": _SCP_VERSION,
            "release": public_release_metadata(),
            "domain_experts": len(judge.domain_experts),
            "slms": len(judge.domain_experts),
            "v98_modules": sum(1 for value in judge.get_v98_status().values() if value != "inactive"),
            "routes": len(app.routes),
            "modules": "136+ Python files",
            "data_size_mb": round(db_size / (1024 * 1024), 2),
            "multi_turn_tracker": _multi_turn_tracker.stats(),
            "cross_language": _cross_language_learner.stats(),
            "fact_checker": _fact_checker.stats(),
            "sandbox_capability": isolation_capability(),
            "runtime_routing": {
                "math_probe_route": list(judge._route_question("2+2")) if hasattr(judge, "_route_question") else ["math"],
                "domain_expert_loaded": "math" in getattr(judge, "domain_experts", {}),
                "math_slm_loaded": "math" in getattr(judge, "domain_experts", {}),
            },
            # [S24] Question-router fork KPIs (LOOKUP→data-API trước LLM).
            # [S24 seam chọn /health/detailed thay vì admin_v100: container chạy
            # SCP_API_PROFILE=core → nhóm versioned_admin KHÔNG được mount, còn
            # /health/detailed luôn có mặt. Key additive, chỉ aggregate counters.
            "question_routing": _question_routing_stats(),
            "background_scheduler_started": _sched_started,
        }
    except Exception as e:
        logger.debug(f"health_detailed ignored: {e}", exc_info=True)
        _sched_started = getattr(app.state, "background_scheduler_started", False)
        return {
            "status": "initializing",
            "version": _SCP_VERSION,
            "routes": len(app.routes),
            # [SEC-FIX /health-authz 2026-09-26] Never echo exception text to
            # the client: str(e) may embed internal paths, env-file names or
            # credential material. Full detail stays in the server log above.
            "error": type(e).__name__,
            "background_scheduler_started": _sched_started,
            "note": "judge init in progress — /health returns ok, /ask may be slow",
        }


@app.get("/ready")
@app.get("/readiness")
async def readiness():
    judge_ready = bool(getattr(app.state, "judge_ready", False))
    scheduler_started = bool(getattr(app.state, "background_scheduler_started", False))
    payload = {
        "status": "ready" if judge_ready else "initializing",
        "service": "scp-api",
        "version": _SCP_VERSION,
        "checks": {
            "judge": "ok" if judge_ready else "pending",
            "background_scheduler": "ok" if scheduler_started else "pending",
        },
        "reason": getattr(app.state, "readiness_reason", None),
    }
    return JSONResponse(payload, status_code=200 if judge_ready else 503)


@app.get("/")
async def root():
    return {
        "name": "SCP",
        "version": _SCP_VERSION,
        "description": "Self-Correcting Pipeline with V98 security",
        "endpoints": [
            "POST /ask",
            "POST /v1/chat/completions",
            "GET  /v1/models",
            "POST /v98/analyze-session",
            "POST /v98/run-simulation",
            "POST /v98/run-intel-crawl",
            "GET  /v98/status",
            "GET  /v98/counter/stats",
            "GET  /v98/canary/triggers",
            "GET  /v98/error-store/stats",
            "GET  /v98/attack-memory/stats",
            "GET  /dashboard",
            "GET  /health",
        ],
    }


try:
    from scp.api.routes.hands_routes import router as hands_router
    if _route_enabled("hands"):
        app.include_router(hands_router)
    from scp.api.routes.batch_benchmark_routes import router as batch_benchmark_router
    if _route_enabled("batch_benchmark"):
        app.include_router(batch_benchmark_router)
    _HANDS_AVAILABLE = _route_enabled("hands")
except ImportError as e:
    logger.warning("[SCP Hands v3.2] Hands router unavailable: %s", e)
    _HANDS_AVAILABLE = False

try:
    from scp.api.routes.agent_routes import router as agent_router
    if _route_enabled("agent"):
        app.include_router(agent_router)
        _AGENT_ORCHESTRATOR_AVAILABLE = True
    else:
        _AGENT_ORCHESTRATOR_AVAILABLE = False
except ImportError as e:
    logger.warning("[SCP Agent] Agent orchestrator router unavailable: %s", e)
    _AGENT_ORCHESTRATOR_AVAILABLE = False

try:
    from scp.api.routes.call_routes import router as call_router
    if _route_enabled("call"):
        app.include_router(call_router)
        _CALL_SIGNALING_AVAILABLE = True
    else:
        _CALL_SIGNALING_AVAILABLE = False
except ImportError as e:
    logger.warning("[SCP Call] Call signaling router unavailable: %s", e)
    _CALL_SIGNALING_AVAILABLE = False

try:
    from scp.observability.otel import configure_fastapi_otel
    _OTEL_STATUS = configure_fastapi_otel(app)
    if _OTEL_STATUS.get("enabled"):
        logger.info("[OTel] FastAPI tracing enabled without request-body/header capture")
    else:
        logger.info("[OTel] tracing disabled: %s", _OTEL_STATUS.get("reason", "not configured"))
except Exception as e:
    _OTEL_STATUS = {"enabled": False, "reason": type(e).__name__}
    logger.warning("[OTel] optional instrumentation unavailable: %s", type(e).__name__, exc_info=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("scp.api_server:app", host="127.0.0.1", port=8000, reload=False, log_level="info")

