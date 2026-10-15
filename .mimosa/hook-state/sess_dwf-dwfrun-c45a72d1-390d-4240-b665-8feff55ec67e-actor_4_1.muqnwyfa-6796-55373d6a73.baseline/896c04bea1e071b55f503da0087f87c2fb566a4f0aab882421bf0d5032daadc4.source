# SCP CIRCUIT: M02 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M02-closure.json)
"""api_server parts — extracted from api_server.py (Task 19-A).
 kept verbatim; only the location changed.

[Task 19-C] ruff: noqa: F821 — this is a MIXIN module. Names like
RealityJudge, _judge_lock, AttackCrawler, start_crawl_thread,
_cross_language_learner, _V1042_AVAILABLE, DataPartitioner, ThreeTierCache,
etc. are defined in the parent api_server.py and injected at runtime via the
mixin pattern. They cannot be imported here without creating a circular
dependency. The noqa suppresses F821 for the entire file.

[SCP-DNA-FIX R5-1] Note: _SCP_SAFE_FETCH_UA was REMOVED from the noqa
scope above because it is now defined LOCALLY below (was the cause of the
Round 5 / Source 1+2+4 cross-validated CRITICAL bug: constant defined only
in api_server.py:73 but USED at helpers.py:258 → NameError → caught by
except Exception at api_server.py:588 → image/voice jailbreak detector
silently skipped for ALL multimodal requests).
"""
# [hygiene] blanket "noqa: F821" removed — narrowed to per-line noqa below
from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from fastapi import Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

from scp.core.runtime_paths import runtime_data_dir, runtime_path

# [Fix 4-a-005 / Phase 3-A — DNA #5, #14, #19]
# TẠI SAO _SCP_SAFE_FETCH_UA / _is_disallowed_ip / _SafeRedirectHandler /
# _safe_fetch_url are now IMPORTED (not defined here):
#   Before: helpers.py had its OWN inline definitions of all 4 symbols, and
#   api_utils.py had a SEPARATE fetch_with_retry that bypassed all of them
#   (urllib.request.urlopen with no IP check, follows redirects). Two
#   divergent implementations of "safe URL fetch" — scanners only checked one
#   (DNA #5 ảo giác đồng thuận). DNA #14: same name "safe fetch" ≠ same
#   safety posture.
#   After: ALL 4 symbols live in scp.core.url_fetcher (neutral module, no
#   circular-dep risk). helpers.py re-exports them so existing imports
#   (api_server.py line 42, _shared.py PEP 562 delegation, v104_routes.py)
#   keep working unchanged. If you need a fetcher, extend url_fetcher.py —
#   do NOT add a third impl here.
from scp.core.url_fetcher import (  # noqa: E402,F401 (compatibility re-exports)
    _SCP_SAFE_FETCH_UA,
    _is_disallowed_ip,
    _safe_fetch_url,
    _SafeRedirectHandler,
)

logger = logging.getLogger("scp.api")

# V103 FIX: Auth cho admin endpoints — shared singleton
_security = HTTPBearer(auto_error=False)

# [FIX-A P0-3] Log-once flag: warn when admin token is empty (deny-by-default).
_admin_no_token_warned: bool = False

# [Task 19-B / Mục 20] Module-level singletons used by get_judge() below.
# TẠI SAO: helpers.py is a MIXIN extracted from api_server.py by Task 19-A.
# `global _judge` inside get_judge() refers to THIS module's namespace, not
# api_server.py's. Without these declarations here, `get_judge()` raises
# NameError at first call (was the root cause of /ask 500 errors during
# the 23 golden tests). Declaring them here as None-initial lets the
# double-checked locking pattern work correctly. api_server.py still
# has its own copies (line ~167) for any direct reads, but they are
# effectively dead — get_judge() is the only entry point and it uses
# these.
import threading as _threading

_judge = None
_judge_lock = _threading.Lock()
_attack_crawler = None
_predictive_engine = None

# [Task 19-B / Mục 20] Lazy imports of all the helpers that get_judge()
# references. Originally these were imported at api_server.py module-level
# (lines 100-165) and assumed available in helpers.py via the "mixin
# pattern" — but Python doesn't auto-inject module globals. We re-import
# them here (try/except — non-fatal if any module is unavailable) so
# get_judge() can find them.
AttackCrawler = None
start_crawl_thread = None
try:
    from scp.security.attack_crawler import AttackCrawler as _AC
    from scp.security.attack_crawler import start_crawl_thread as _SCT
    AttackCrawler = _AC
    start_crawl_thread = _SCT
except Exception as _e_ac:
    logger.warning(f"[helpers] AttackCrawler import failed (non-fatal): {_e_ac}", exc_info=True)

start_learning_thread = None
try:
    from scp.core.real_learning_engine import start_learning_thread as _SLT
    start_learning_thread = _SLT
except Exception as _e_rle:
    logger.warning(f"[helpers] start_learning_thread import failed (non-fatal): {_e_rle}", exc_info=True)

start_fast_learning_thread = None
_V1042_AVAILABLE = False
try:
    from scp.core.fast_learning_engine import start_fast_learning_thread as _SFLT
    start_fast_learning_thread = _SFLT
    _V1042_AVAILABLE = True
except Exception as _e_fle:
    logger.warning(f"[helpers] start_fast_learning_thread import failed (non-fatal): {_e_fle}", exc_info=True)

deferred_background_start = None
_V1043_AVAILABLE = False
try:
    from scp.core.startup_optimizer import deferred_background_start as _DBS
    deferred_background_start = _DBS
    _V1043_AVAILABLE = True
except Exception as _e_so:
    logger.warning(f"[helpers] deferred_background_start import failed (non-fatal): {_e_so}", exc_info=True)

DataPartitioner = None
ThreeTierCache = None
_V1044_AVAILABLE = False
try:
    from scp.core.data_partitioner import DataPartitioner as _DP
    from scp.core.data_partitioner import ThreeTierCache as _TTC
    DataPartitioner = _DP
    ThreeTierCache = _TTC
    _V1044_AVAILABLE = True
except Exception as _e_dp:
    logger.warning(f"[helpers] DataPartitioner import failed (non-fatal): {_e_dp}", exc_info=True)

_cross_language_learner = None
try:
    from scp.security.cross_language_learner import CrossLanguageLearner as _CLL
    _cross_language_learner = _CLL()
except Exception as _e_cll:
    logger.warning(f"[helpers] CrossLanguageLearner init failed (non-fatal): {_e_cll}", exc_info=True)
# RealityJudge type is imported lazily inside get_judge() to avoid circular import


class AskResponse(BaseModel):
    verdict: str
    final_answer: str
    confidence: float
    domain: str
    falsification_status: str | None = None
    governance_decision: str | None = None
    v98_guard: dict[str, Any] | None = None
    v98_classification: dict[str, Any] | None = None
    v98_attack_policy: dict[str, Any] | None = None
    v98_counter_executed: dict[str, Any] | None = None
    v98_canary_token: str | None = None
    v98_bypass_recorded: bool | None = None
    elapsed_ms: float
    session_id: str
    # P1: Durable request-level identity and terminal status.
    run_id: str | None = None
    trace_id: str | None = None
    run_status: str | None = None
    ledger_status: str | None = None
    # Canonical public vocabulary: Domain Expert / Domain Expert Ensemble.
    # Legacy slm_* fields remain as read-only compatibility aliases.
    expert_trace: list[dict[str, Any]] | None = None
    expert_responses: list[dict[str, Any]] | None = None
    expert_ensemble: str | None = None
    # V105: Full pipeline trace — SLM nào chạy, time từng phase, reasoning
    slm_trace: list[dict[str, Any]] | None = None  # [{domain, slm_name, answer, confidence, time_ms, source}]
    phase_timings: dict[str, float] | None = None  # {intake_ms, routing_ms, ...}
    reasoning: str | None = None
    slm_responses: list[dict[str, Any]] | None = None
    v100_claims: dict[str, Any] | None = None
    v103_antibodies: dict[str, Any] | None = None
    speculative_mode: dict[str, Any] | None = None
    lane: str | None = None
    routing: dict[str, Any] | None = None
    web_fallback: dict[str, Any] | None = None

    def __init__(self, **data: Any):
        # Populate canonical fields from legacy callers without changing
        # the old JSON contract. New callers should use expert_* fields.
        if data.get("expert_trace") is None and data.get("slm_trace") is not None:
            data["expert_trace"] = data["slm_trace"]
        if data.get("expert_responses") is None and data.get("slm_responses") is not None:
            data["expert_responses"] = data["slm_responses"]
        if data.get("expert_ensemble") is None:
            data["expert_ensemble"] = "Domain Expert Ensemble"
        super().__init__(**data)



class AskRequest(BaseModel):
    question: str = Field(..., min_length=0, max_length=8000)  # [FIX-P0-8C] min_length=0 cho UNKNOWN handling
    ai_answer: str = Field("", max_length=10000)
    domain: str = Field("general")
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    session_id: str | None = None
    source: str = Field("api")
    contexts: list[str] = Field(default_factory=list, max_length=8)
    retrieved_context: str = Field("", max_length=96000)
    ground_truth: str = Field("", max_length=4000)
    rag_enabled: bool = False
    domain_override: str = Field("", max_length=64)
    # [V104.45 #CP] Multimodal input remains optional and bounded.
    image_url: str | None = Field(None, description="URL of image to scan for jailbreak")
    voice_url: str | None = Field(None, description="URL of audio to scan for jailbreak")
    # Browser webcam sends a data URL only after the user presses Capture.
    # Keep the cap below the normal reverse-proxy request limits.
    image_data: str | None = Field(None, max_length=8_000_000, description="Base64/data URL image captured by an explicitly enabled webcam")
    # The client sends only the recent visible turns. The server treats this as
    # context, never as instructions, and keeps the current question authoritative.
    conversation_history: list[dict[str, str]] = Field(default_factory=list, max_length=8)



class SessionAnalyzeRequest(BaseModel):
    session_logs: list[dict[str, Any]]
    model_responses: list[dict[str, Any]]



# NOTE: _SafeRedirectHandler, _safe_fetch_url, _is_disallowed_ip are now
# imported from scp.core.url_fetcher (see top of file). Their inline
# definitions were REMOVED in Fix 4-a-005 to enforce ONE canonical fetcher.



def _extract_v98_context(request: Request) -> dict[str, Any]:
    """Extract bounded request metadata for V98 security modules.

    Credential and cookie header values must never enter model-adjacent
    security context.  The detector keeps only a bounded user-agent
    fingerprint plus header names and a sensitive-header presence flag.
    """
    from scp.security.request_context import safe_header_metadata

    ip = request.client.host if request.client else "unknown"
    header_metadata = safe_header_metadata(request.headers)
    return {
        "ip": ip,
        "headers": header_metadata["headers"],
        "header_names": header_metadata["header_names"],
        "sensitive_headers_present": header_metadata["sensitive_headers_present"],
        "user_agent_present": header_metadata["user_agent_present"],
        "session_id": str(uuid.uuid4()),
        "endpoint": str(request.url.path),
        "body": "",
    }



# [Fix 4-a-006 / Phase 3-A — DNA #5, #14, #19]
# TẠI SAO verify_admin is now IMPORTED (not defined here):
#   Before: TWO divergent `verify_admin` functions existed:
#     - helpers.py (HERE): HTTPBearer-based, NO rate limiting, 401 on no-config.
#       Dead code — confirmed by grep: 0 callers imported it from helpers.
#     - _shared.py: Header-based, HAS rate limiting, 503 on no-config (wrong).
#       All route modules imported from _shared.
#   DNA #5 (ảo giác đồng thuận): same name `verify_admin` ≠ same auth posture.
#   DNA #14: both passed basic tests; only the rate-limit + 503-vs-401
#   differences mattered under attack.
#   After: ONE canonical `verify_admin` lives in scp.security.auth (with
#   rate limiting + 401 on no-config — the BEST of both old versions).
#   Both helpers.py and _shared.py re-export it. Existing imports keep
#   working; there is now ONE implementation.
from scp.security.auth import verify_admin  # noqa: E402,F401  (re-exported for backward-compat)


def get_judge() -> RealityJudge:  # noqa: F821  # [hygiene-keep] RealityJudge: lazily imported inside get_judge() body (circular-import guard) + provided by api_server.py namespace (mixin rebind)
    """Build / return the singleton RealityJudge.

    [Task 19-B / Mục 20] RealityJudge imported lazily inside this function
    to avoid a circular import (helpers → api_server → runtime → ...).
    The TYPE hint is a string (forward reference) for the same reason.
    """
    global _judge, _attack_crawler, _predictive_engine
    # [FIX-10] Double-checked locking — acquire lock only on cold path.
    if _judge is None:
        with _judge_lock:
            if _judge is not None:
                # Another thread won the race while we waited for the lock
                return _judge
            logger.info("Initializing RealityJudge (V98)...")
            # [Task 19-B] Lazy import — avoids circular dependency
            from scp.runtime.judge import RealityJudge as _RealityJudge
            _judge = _RealityJudge()
            from scp.interfaces.judge import set_judge_provider
            set_judge_provider(_judge)
            logger.info(f"RealityJudge ready: {len(getattr(_judge, 'domain_experts', []))} SLMs, V98 modules={_judge.get_v98_status() is not None}")
        # [V104.36 #56-wire] Create PredictiveOrchestrator WITH production judge
        # TẠI SAO: must happen AFTER _judge is set, so SelfLearner gets real judge.v13
        try:
            from scp.prediction.predictive import PredictiveOrchestrator
            _predictive_engine = PredictiveOrchestrator(judge=_judge)
            logger.info("V104.36 PredictiveOrchestrator wired to production judge "
                        "(SelfLearner will retrain judge.v13.classifier)")
        except Exception as e:
            logger.warning(f"V104.36 PredictiveOrchestrator init failed: {e}", exc_info=True)
            _predictive_engine = None

        # [M12-FIX PF-4a] Wire WHY Engine onto the judge singleton.
        # TẠI SAO: RealityJudge has no `why_engine` attribute at all, so the
        # background WHY verify loop (`_why_verify_loop`, guard:
        # getattr(judge, "why_engine", None)) could NEVER find an engine —
        # deferred why_verification_plans piled up pending forever (R6-3
        # wiring claim was PASS-without-reality). Guarded non-fatal: WHY
        # engine init failure must not take down the judge.
        try:
            from scp.meta.why_engine_parts.whyengine import WhyEngine as _WhyEngine
            _judge.why_engine = _WhyEngine()
            logger.info("WHY Engine wired to production judge (deferred verification active)")
        except Exception as e:
            logger.warning(f"WHY Engine init failed (non-fatal, deferred verification disabled): {e}", exc_info=True)

        # [V5.6-FIX] TẠI SAO: toàn bộ init dưới đây nằm NGOÀI `if _judge is None:`
        # → mỗi request /ask gọi get_judge() → spawn thêm thread + start learning
        # engine + reload patterns → thread explosion → CPU 100% → crash.
        # Log Gà: 262 lần "RealLearningEngine started" + 130 threads "Deferred
        # background start" trong 27 giây = thread leak.
        # Fix: move toàn bộ init vào trong guard — chỉ chạy 1 lần duy nhất.

        # V103: Start AttackCrawler thread
        if _attack_crawler is None:
            _attack_crawler = AttackCrawler(data_dir="data")
            start_crawl_thread(data_dir="data")
            logger.info("V103 AttackCrawler started (10 min interval)")

        # V104: Auto-load cross-language patterns into VietnameseDetector
        try:
            patterns = _cross_language_learner.transfer_existing_vietnamese_patterns()
            if patterns:
                en_patterns = [p for p in patterns if p["target_lang"] == "en"]
                logger.info(f"V104 CrossLanguage: {len(patterns)} patterns across 8 langs "
                           f"({len(en_patterns)} EN patterns ready)")
                # [V104.44 #CQ] TẠI SAO: was only logging "patterns ready" but never
                # loading them into AttackPatternMemory → detector never got cross-lang rules.
                # Fix: write each pattern as a dynamic rule in AttackPatternMemory.
                try:
                    _judge_for_am = _judge
                    if _judge_for_am and _judge_for_am.attack_memory:
                        _installed = 0
                        for _p in patterns:
                            try:
                                _judge_for_am.attack_memory.record_bypass(
                                    question=_p.get("source_pattern", "")[:500],
                                    answer="",
                                    attack_type=f"cross_lang_{_p.get('target_lang', 'unknown')}",
                                    signatures=[_p.get("translated_pattern", "")[:200]],
                                )
                                _installed += 1
                            except Exception:
                                logger.exception("[api_server.py:387] silenced exception")
                        if _installed > 0:
                            logger.info(f"[V104.44 #CQ] CrossLanguage: {_installed} patterns loaded into AttackPatternMemory")
                except Exception as _am_err:
                    logger.debug(f"[V104.44 #CQ] CrossLanguage rule load error: {_am_err}", exc_info=True)
        except Exception as e:
            logger.debug(f"CrossLanguage auto-load: {e}", exc_info=True)
        # [G3-MERGE A5] Start Learning Engine — SINGLE thread (was: 2 threads racing).
        # pre-merge: start_learning_thread (V104.1, 1h) + start_fast_learning_thread
        # (V104.2, 5min adaptive) BOTH ran, writing to the same `data/v13.db` KB
        # → race condition (Task 2-B finding P1-04). Post-merge: real_learning_engine
        # is a stub that aliases start_learning_thread → start_fast_learning_thread
        # (idempotent). Only ONE thread runs; the second call no-ops via the
        # module-level _FAST_LEARNING_THREAD guard. Skipping the explicit V104.1
        # call here makes intent explicit + avoids a noisy "already running" log.
        try:
            # [F-10-2] The fast-learning thread runs LLM-backed cycles on an
            # adaptive 1-30 min schedule — real provider quota burned in the
            # background of every boot, and its non-daemon executor workers
            # can hang interpreter exit when a network call stalls. It is now
            # opt-in: set SCP_FAST_LEARNING_THREAD=1 to start it (the
            # /v104/learn/* endpoints remain available on demand either way).
            if os.environ.get('SCP_FAST_LEARNING_THREAD', '0') != '1':
                logger.info("V104.2 FastLearningEngine NOT started (SCP_FAST_LEARNING_THREAD unset) — "
                            "opt in with SCP_FAST_LEARNING_THREAD=1; /v104/learn/* endpoints still available")
            elif _V1042_AVAILABLE:
                start_fast_learning_thread(
                    scp_db_path=str(runtime_path("SCP_DB_PATH", "v13.db")),
                    data_dir=str(runtime_data_dir()),
                )
                logger.info("V104.2 FastLearningEngine started (CANONICAL — post G3-MERGE) "
                            "(10 concurrent Ollama + 5 concurrent Wiki + adaptive 1-30 min). "
                            "RealLearningEngine merged in; V104.1 sequential API still "
                            "available via /v104/learn/{ollama,local,news,all} endpoints.")
            else:
                # Fallback: if V104.2 unavailable, fall back to V104.1 (now alias).
                start_learning_thread(
                    scp_db_path=str(runtime_path("SCP_DB_PATH", "v13.db")),
                    data_dir=str(runtime_data_dir()),
                )
                logger.info("V104 RealLearningEngine started (fallback — V104.2 unavailable)")
        except Exception as e:
            logger.warning(f"Learning engine start failed: {e}", exc_info=True)

        # [V104.47 RESTORE] V104.3 StartupOptimizer + V104.4 DataPartitioner
        if _V1043_AVAILABLE:
            try:
                import asyncio
                import threading
                loop = asyncio.new_event_loop()
                threading.Thread(target=lambda: loop.run_until_complete(deferred_background_start(judge=_judge))).start()
                logger.info("V104.3 StartupOptimizer started (deferred background init)")
            except Exception as e:
                logger.warning(f"V104.3 StartupOptimizer start failed: {e}", exc_info=True)

        if _V1044_AVAILABLE:
            try:
                # [RUNTIME-FIX-1] Root cause: ThreeTierCache(_partitioner) truyền
                # DataPartitioner instance vào tham số db_path (Path) -> TypeError
                # "argument should be a str or an os.PathLike... not 'DataPartitioner'"
                # (runtime log line 147). Fix: tách biệt 2 object, không phụ thuộc nhau.
                _partitioner = DataPartitioner("data")
                # ThreeTierCache nhận db_path (Path), KHÔNG nhận partitioner.
                from scp.core.partition.shard import DATA_DIR as _V1044_DATA_DIR
                _cache = ThreeTierCache(db_path=str(_V1044_DATA_DIR / "v13.db"))  # noqa: F841 — side-effect: keep cache object alive (ThreeTierCache registers internally)
                # [ROOT-FIX-A] ThreeTierCache (scp/core/partition/rotate.py) has NO
                # `attach_partitioner()` method — the previous `if hasattr(...)` block
                # was dead code that silently no-op'd. Removed to keep the init path
                # honest about which objects are actually wired.
                # [ROOT-FIX-B] DataPartitioner has NO `list_partitions()` method
                # (runtime error: "'DataPartitioner' object has no attribute
                # 'list_partitions'"). Use `get_structure()` which returns a dict
                # of partition sub-dicts; sum their lengths for a real count.
                _struct = _partitioner.get_structure()
                _n_partitions = sum(
                    len(_struct.get(k, {}))
                    for k in ("by_domain_knowledge", "by_day_errors", "by_day_bypasses")
                )
                logger.info(
                    f"V104.4 DataPartitioner started "
                    f"({_n_partitions} partitions) + ThreeTierCache wired"
                )
            except Exception as e:
                logger.warning(f"V104.4 DataPartitioner start failed: {e}", exc_info=True)

    from scp.interfaces.judge import set_judge_provider
    set_judge_provider(_judge)
    return _judge



