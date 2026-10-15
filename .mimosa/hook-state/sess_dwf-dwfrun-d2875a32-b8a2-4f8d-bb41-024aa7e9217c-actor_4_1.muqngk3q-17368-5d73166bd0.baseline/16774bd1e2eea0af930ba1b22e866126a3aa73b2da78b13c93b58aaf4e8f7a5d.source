"""
SCP LLM Gateway — Unified LLM client (API-only).

Single source of truth for ALL LLM calls in SCP (inference + learning).

Provider Strategy (2026-08-31):
  Gateway chỉ gọi OpenRouter API trực tiếp (primary).
  Fallback: OpenAI-compatible provider qua env (OPENAI_API_KEY/OPENAI_BASE_URL)
  hoặc bất kỳ provider nào khai báo qua SCP_LLM_FALLBACK_PROVIDERS.
  Không còn hardcode bất kỳ provider cụ thể nào (Ollama, Groq đã bị gỡ).

Design:
  - Async-first (httpx.AsyncClient) for inference path (/ask)
  - chat_sync() wrapper for background threads (learning engines)
  - Task routing: mỗi task có một OpenRouterProvider riêng
    (primary = OPENROUTER_MODEL, free fallback per task, key round-robin)
  - Singleton get_gateway() — shared connection pool, thread-safe init
"""
from __future__ import annotations

import asyncio
import ipaddress
import itertools
import logging
import math
import os
import random
import threading
import time
from typing import Any

import httpx

logger = logging.getLogger("scp.llm_gateway")

# [B311-fix 2026-09-30] RNG cho retry-backoff jitter (uniform(0, 0.15)s thêm
# vào exponential backoff khi retry transient error). Jitter chỉ nhằm tránh
# thundering-herd giữa các request retry — KHÔNG có mục đích bảo mật. Dùng
# instance SystemRandom RIÊNG ở module level (pattern:
# scp/security/gcg_attack.py `_GCG_RNG`) thay cho global RNG để tách biệt với
# mọi lời random.seed() của module khác; phân phối uniform(0, 0.15) và cap
# min(..., 2.0) giữ nguyên (behavior-preserving).
_BACKOFF_JITTER_RNG = random.SystemRandom()

# Sync wrapper hard timeout: OpenRouter client timeout is 60s inside
# _call_model; the sync wrapper adds headroom for thread-pool scheduling.
SYNC_CALL_TIMEOUT_SECONDS = 90

# ============================================================
# [S21 HEDGE] Hedged LLM race — owner directive: "khi LLM trả kết quả chậm
# khoảng 10s -> chuyển sang LLM khác hoặc API khác".
#   - SCP_LLM_ATTEMPT_TIMEOUT_SECONDS (default 10): deadline cho MỖI attempt;
#     quá hạn → bắn provider kế tiếp trong chain vào race SONG SONG (provider
#     cũ không bị hủy — ai về trước thắng).
#   - SCP_LLM_HEDGE_MAX_SECONDS (default 90): cap tổng cho toàn bộ race;
#     quá cap → fail-closed (None + error rõ), không chờ vô hạn.
#   - SCP_LLM_HEDGE=off: kill-switch → quay về failover tuần tự cũ.
# Env parse FAIL-CLOSED: giá trị lỗi/0/âm/non-finite → default.
# ============================================================
HEDGE_DEFAULT_ATTEMPT_TIMEOUT_SECONDS = 10.0
HEDGE_DEFAULT_MAX_SECONDS = 90.0
_HEDGE_OFF_VALUES = {"off", "0", "false", "no"}


def _parse_positive_seconds(raw: str | None, default: float) -> float:
    """Parse giây từ env; giá trị lỗi/0/âm/non-finite → default (fail-closed)."""
    if raw is None:
        return default
    try:
        value = float(raw.strip())
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value) or value <= 0:
        return default
    return value


def _hedge_settings() -> tuple[bool, float, float]:
    """(enabled, attempt_deadline_seconds, hedge_max_seconds) từ env."""
    enabled = os.environ.get("SCP_LLM_HEDGE", "on").strip().lower() not in _HEDGE_OFF_VALUES
    attempt_deadline = _parse_positive_seconds(
        os.environ.get("SCP_LLM_ATTEMPT_TIMEOUT_SECONDS"),
        HEDGE_DEFAULT_ATTEMPT_TIMEOUT_SECONDS,
    )
    hedge_cap = _parse_positive_seconds(
        os.environ.get("SCP_LLM_HEDGE_MAX_SECONDS"),
        HEDGE_DEFAULT_MAX_SECONDS,
    )
    return enabled, attempt_deadline, hedge_cap


def _is_loopback_host(host: str) -> bool:
    """Return True only for explicit loopback hosts/addresses."""
    normalized = host.strip().rstrip(".").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        logger.debug('_is_loopback_host: ValueError ignored', exc_info=True)
        return False


from scp.llm_gateway.egress_policy import llm_egress_allowed


def _llm_egress_allowed(base_url: str) -> bool:
    """Enforce the SCP LLM egress contract delegating to unified egress policy."""
    return llm_egress_allowed(base_url)


# ============================================================
# [OPENROUTER-FREE-FIX] REGISTRY OF ALL 17 FREE MODELS ON OPENROUTER
# ============================================================
# Verified via https://openrouter.ai/api/v1/models on 2026-08-06.
# All have pricing.prompt=0 AND pricing.completion=0 (cost $0).
# Use this list when you need to iterate over ALL free models (e.g. for
# fallback chains, model rotation, or auto-discovery).
# ============================================================
OPENROUTER_FREE_MODELS: list[str] = [
    # ---- 2026+ SCP Added Models ----
    "deepseek/deepseek-r1:free",                         # DeepSeek R1 reasoning
    "deepseek/deepseek-chat:free",                       # DeepSeek V3 chat
    "google/gemini-2.5-pro:free",                        # Gemini 2.5 Pro (if free)
    "google/gemini-2.5-flash:free",                      # Gemini 2.5 Flash
    "meta-llama/llama-3.3-70b-instruct:free",            # Llama 3.3 70B
    "meta-llama/llama-3.1-8b-instruct:free",             # Llama 3.1 8B
    "meta-llama/llama-3.2-3b-instruct:free",             # Llama 3.2 3B
    "qwen/qwen-2.5-72b-instruct:free",                   # Qwen 2.5 72B
    "qwen/qwen-2.5-coder-32b-instruct:free",             # Qwen 2.5 Coder
    "mistralai/mistral-nemo:free",                       # Mistral Nemo
    "microsoft/phi-3-mini-128k-instruct:free",           # Phi 3 Mini
    "google/gemma-2-27b-it:free",                        # Gemma 2 27B
    "anthropic/claude-3.5-sonnet:free",                  # Claude 3.5 Sonnet (if rotated to free)

    # ---- Existing SCP Models ----
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "cohere/north-mini-code:free",
    "inclusionai/ling-3.0-tiny:free",
    "poolside/laguna-s-2.1:free",
    "poolside/laguna-xs-2.1:free",
    "openrouter/free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3.5-content-safety:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/lyria-3-pro-preview",
    "google/lyria-3-clip-preview",
]


from scp.security.provider_keys import ProviderCredentialError, load_openrouter_keys
from scp.security.url_safety import EgressDeniedError, enforce_egress_policy  # [EE-G1]


class CircuitBreaker:
    """[C5 — Gemini indictment: round-robin ngây thơ] Cầu dao tự ngắt.

    Một endpoint/model fail liên tục N lần → OPEN: mọi request tới nó bị
    chặn NGAY tại client (fast-fail, không chờ time-out), tránh nghẽn chết
    hàng đợi Task Kernel. Sau cooldown → HALF-OPEN: cho đúng 1 request thăm
    dò; thành công → CLOSE (reset), thất bại → OPEN lại. Đây cùng nguyên lý
    với scp/core/circuit_breaker.py nhưng cho đường LLM outbound."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 300.0):
        if failure_threshold < 1 or cooldown_seconds <= 0:
            raise ValueError("failure_threshold >= 1 and cooldown_seconds > 0 required")
        self.failure_threshold = int(failure_threshold)
        self.cooldown_seconds = float(cooldown_seconds)
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        # [AUDIT-FIX low-7a] Docstring hứa "cho đúng 1 request thăm dò" nhưng
        # transition HALF-OPEN từng nằm trong is_open() → N request classify
        # đồng thời sau cooldown đều thấy breaker "đóng" và đều được probe.
        # Việc cấp probe duy nhất tách ra acquire_half_open_probe() (gọi ở
        # ĐIỂM THỰC SỰ thực hiện HTTP attempt — _call_model), is_open() giờ
        # là pure classifier.
        self._half_open_probe_in_flight = False
        self._lock = threading.Lock()

    def is_open(self) -> bool:
        """Pure classifier: True = OPEN (fast-fail), False = CLOSED hoặc
        cooldown đã hết (HALF-OPEN pending). KHÔNG mutate state."""
        with self._lock:
            if self._opened_at is None:
                return False
            return time.monotonic() - self._opened_at < self.cooldown_seconds

    def acquire_half_open_probe(self) -> bool:
        """[AUDIT-FIX low-7a] Cấp quyền thực hiện một attempt trên breaker.

        - CLOSED → True cho mọi caller (không tiêu probe).
        - OPEN (còn trong cooldown) → False (fast-fail như cũ).
        - Cooldown vừa hết (HALF-OPEN) → True cho ĐÚNG 1 caller (probe),
          False cho mọi caller khác cho đến khi probe được record/released.
        """
        with self._lock:
            if self._half_open_probe_in_flight:
                return False
            if self._opened_at is None:
                return True
            if time.monotonic() - self._opened_at < self.cooldown_seconds:
                return False
            # Cooldown hết → chuyển HALF-OPEN: giảm 1 ngưỡng để probe thất bại
            # mở lại ngay, thành công thì record_success reset về 0.
            self._consecutive_failures = self.failure_threshold - 1
            self._opened_at = None
            self._half_open_probe_in_flight = True
            return True

    def release_half_open_probe(self) -> None:
        """Nhả probe reservation (idempotent — record_* đã tự nhả)."""
        with self._lock:
            self._half_open_probe_in_flight = False

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._opened_at = None
            self._half_open_probe_in_flight = False

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.failure_threshold:
                self._opened_at = time.monotonic()
            self._half_open_probe_in_flight = False


# ============================================================
# [F-05 DEAD-MODEL BREAKER 2026-09-25] Per-process dead-model cache.
# Runtime audit RUNTIME-AUDIT-20260925-0411 F-05: every LLM-lane ask burned
# 3x HTTP 404 on stale OpenRouter model names in the fallback chain before a
# live model answered (known debt GA.md B11 — the owner's .env lists dead
# model names; .env belongs to the owner, so the PRODUCT caches the
# provider's own verdict instead of re-asking every request).
# Contract:
#   * only a 404 whose body ACTUALLY says model-not-found (strict body
#     classification) marks (provider, base_url, model) dead — any other 404
#     is a normal failure and is NEVER cached;
#   * cached-dead candidates are skipped on later attempts; ONLY that
#     candidate is skipped — the chain/failover semantics are unchanged and
#     nothing that was previously allowed becomes disallowed;
#   * the cache starts EMPTY on every process start, so new owner config is
#     honored after a restart (no persisted state);
#   * kill-switch SCP_LLM_DEAD_MODEL_BREAKER=off disables the cache
#     (same env convention as SCP_LLM_HEDGE; default ON).
#
# [F-05-EXT QUOTA-DEAD 2026-09-26] Live sweep extension: dead providers burned
# latency on EVERY ask cycle with hard-quota errors (Cerebras/SambaNova 402
# Payment Required, Gemini 429) because only the 404 model-not-found verdict
# was cached. Contract for quota classes:
#   * 402 Payment Required = hard quota: payment state does not change
#     mid-process → the candidate is cached dead IMMEDIATELY (strict status
#     classification — the sentinel is raised from the real HTTP status, never
#     from body text or substrings);
#   * 429 = rate limit that may be transient → the candidate is cached dead
#     only after N CONSECUTIVE 429s within the process for the same
#     (provider, base_url, model) — threshold from
#     SCP_LLM_RATE_LIMIT_BREAKER_THRESHOLD (default 3, matches the
#     scp-gateway-resilience breaker rule); any non-429 outcome for that
#     candidate resets the streak;
#   * strict classification: 404-shaped, 5xx, egress_denied and generic
#     errors NEVER enter the cache through this path (the 404 model-not-found
#     cache above is the ONLY 404 path, unchanged);
#   * kill-switch semantics identical to the 404 cache
#     (SCP_LLM_DEAD_MODEL_BREAKER=off disables both).
# ============================================================
_DEAD_MODEL_REGISTRY: set[tuple[str, str, str]] = set()
_DEAD_MODEL_REGISTRY_LOCK = threading.Lock()
# Why a candidate is dead — keeps the skip message honest without embedding
# status digits that downstream quota-signal substring matching would
# misread ("payment-dead"/"rate-dead" deliberately avoid 402/429/quota/
# rate-limit substrings).
_DEAD_MODEL_REASONS: dict[tuple[str, str, str], str] = {}
_REASON_MODEL_NOT_FOUND = "404 model-not-found"
_REASON_PAYMENT_DEAD = "payment-dead"
_REASON_RATE_DEAD = "rate-dead"

# [BREAKER-ONCE 2026-09-30] Marker máy đọc được mà inner layer gắn lên MỌI
# error whose breaker failure nó ĐÃ record (404 model-not-found, 402 hard
# quota, 429 threshold-trip, final transient). Hợp đồng exactly-once: một
# real HTTP failure phải được record_failure() ĐÚNG MỘT LẦN — chat()'s
# key-rotation tail PHẢI skip các error đã đánh dấu; các quota error CHƯA
# đánh dấu (429 dưới streak threshold, legacy provider 429/402 error strings)
# vẫn được tail count đúng một lần mỗi ask như cũ.
_RECORDED_FAILURE_PREFIX = "recorded_failure:"

# [F-05-EXT] Consecutive-429 streaks per candidate (per process).
_RATE_LIMIT_STREAKS: dict[tuple[str, str, str], int] = {}
_RATE_LIMIT_STREAKS_LOCK = threading.Lock()

_RATE_LIMIT_THRESHOLD_DEFAULT = 3

_MODEL_NOT_FOUND_MARKERS = (
    "no endpoints",
    "model_not_found",
    "model not found",
    "not a valid model",
    "unknown model",
    "no allowed providers",
    "no provider available",
)


def _dead_model_breaker_enabled() -> bool:
    """Kill-switch read; values off/0/false/no disable the dead-model cache."""
    return os.environ.get("SCP_LLM_DEAD_MODEL_BREAKER", "on").strip().lower() not in _HEDGE_OFF_VALUES


def _is_model_not_found_response(resp: Any) -> bool:
    """Strict classifier: HTTP 404 AND the response body says the model does
    not exist. Any other status — or a 404 whose body matches none of the
    markers (wrong path, permissions, HTML error pages) — is NOT classified
    as a dead model and stays a normal failure."""
    if getattr(resp, "status_code", None) != 404:
        return False
    try:
        body = resp.text
    except Exception:
        logger.debug('_is_model_not_found_response: body read failed', exc_info=True)
        return False
    if not body:
        return False
    lowered = str(body).lower()
    return any(marker in lowered for marker in _MODEL_NOT_FOUND_MARKERS)


def _mark_dead_model(provider_name: str, base_url: str, model: str, reason: str = _REASON_MODEL_NOT_FOUND) -> bool:
    """Cache (provider, base_url, model) as dead for the process lifetime.
    No-op (returns False) when the kill-switch is off or model is empty."""
    if not model or not _dead_model_breaker_enabled():
        return False
    key = (str(provider_name), str(base_url), str(model))
    with _DEAD_MODEL_REGISTRY_LOCK:
        _DEAD_MODEL_REGISTRY.add(key)
        _DEAD_MODEL_REASONS[key] = reason
    return True


def _is_dead_model(provider_name: str, base_url: str, model: str) -> bool:
    if not model:
        return False
    with _DEAD_MODEL_REGISTRY_LOCK:
        return (str(provider_name), str(base_url), str(model)) in _DEAD_MODEL_REGISTRY


def reset_dead_model_cache() -> None:
    """Empty the dead-model cache (test isolation hook; also usable by ops
    after a config reload without a process restart)."""
    with _DEAD_MODEL_REGISTRY_LOCK:
        _DEAD_MODEL_REGISTRY.clear()
        _DEAD_MODEL_REASONS.clear()
    with _RATE_LIMIT_STREAKS_LOCK:
        _RATE_LIMIT_STREAKS.clear()


def _rate_limit_threshold() -> int:
    """Consecutive-429 threshold; invalid/non-positive env → default 3."""
    try:
        value = int(os.environ.get("SCP_LLM_RATE_LIMIT_BREAKER_THRESHOLD", ""))
    except (TypeError, ValueError):
        return _RATE_LIMIT_THRESHOLD_DEFAULT
    return value if value >= 1 else _RATE_LIMIT_THRESHOLD_DEFAULT


def _record_rate_limit_hit(provider_name: str, base_url: str, model: str) -> bool:
    """Count one consecutive 429 for the candidate. Returns True when the
    streak reached the kill threshold (candidate must be cached dead)."""
    key = (str(provider_name), str(base_url), str(model))
    with _RATE_LIMIT_STREAKS_LOCK:
        _RATE_LIMIT_STREAKS[key] = _RATE_LIMIT_STREAKS.get(key, 0) + 1
        return _RATE_LIMIT_STREAKS[key] >= _rate_limit_threshold()


def _clear_rate_limit_streak(provider_name: str, base_url: str, model: str) -> None:
    """Any non-429 outcome for the candidate resets its consecutive streak."""
    key = (str(provider_name), str(base_url), str(model))
    with _RATE_LIMIT_STREAKS_LOCK:
        _RATE_LIMIT_STREAKS.pop(key, None)


class OpenRouterProvider:
    """OpenAI-compatible base với breaker; ProviderName dùng làm nhãn fallback."""
    PROVIDER_NAME = "openrouter"
    """OpenRouter cloud LLM provider — PAID primary + FREE fallback.

    Architecture:
      1. PRIMARY: PAID model (OPENROUTER_MODEL env) — used for ALL tasks by default.
      2. FALLBACK: FREE models (cost $0) — used when PAID model fails
         (rate limit, quota exhausted, network error).
         Task-specific FREE model selected from TASK_FREE_FALLBACK_MAP.
      3. 3 API KEYS round-robin: OPENROUTER_API_KEY, _2, _3 — rotates per call
         to avoid 20 req/min rate limit per key. Effective: 60 req/min total.

    Fallback chain per call:
      1. Try PAID model with key rotation
      2. If 429/402/quota → try task-specific FREE model
      3. If still fails → try openrouter/free (auto-router, picks any free)
      4. If still fails → return None (caller sees provider "none" and must
         fail closed — no answer is fabricated)
    """

    # Task → FREE fallback model. Used ONLY when PAID model fails.
    # All defaults are FREE (cost $0), verified on 2026-08-06.
    TASK_FREE_FALLBACK_MAP: dict[str, str] = {
        "autofix":       "deepseek/deepseek-r1:free",
        "why":           "deepseek/deepseek-chat:free",
        "learning":      "qwen/qwen-2.5-72b-instruct:free",
        "fast_learning": "meta-llama/llama-3.3-70b-instruct:free",
        "judge":         "nvidia/nemotron-3-super-120b-a12b:free",
        "chat":          "google/gemini-2.5-flash:free",
        "vision":        "google/gemini-2.5-flash:free",
        "coding":        "qwen/qwen-2.5-coder-32b-instruct:free",
        "fact_check":    "deepseek/deepseek-r1:free",
        "default":       "openrouter/free",
    }

    # Class-level: 3 API keys + round-robin iterator (shared across all instances)
    _API_KEYS: list[str] = []
    _key_cycle: itertools.cycle | None = None
    _key_lock = threading.Lock()

    @classmethod
    def _init_keys(cls) -> None:
        """Load API keys from env vars (3 keys supported for round-robin)."""
        if cls._API_KEYS:
            return  # already loaded
        try:
            keys = load_openrouter_keys()
        except ProviderCredentialError as exc:
            logger.error("[LLM Gateway] provider credential configuration rejected: %s", str(exc))
            keys = []
        cls._API_KEYS = keys
        if keys:
            cls._key_cycle = itertools.cycle(keys)

    _dynamic_models_loaded = False

    @classmethod
    def _init_dynamic_models(cls) -> None:
        if cls._dynamic_models_loaded:
            return
        try:
            from scp.llm_gateway.free_catalog import refresh_free_catalog
            refresh_free_catalog()
        except Exception as e:
            logger.warning('[LLM Gateway] free-catalog refresh failed: %s', e, exc_info=True)
        cls._dynamic_models_loaded = True


    @classmethod
    def _next_key(cls) -> str:
        """Get next API key (round-robin). Returns '' if no keys configured."""
        cls._init_keys()
        cls._init_dynamic_models()
        with cls._key_lock:
            if cls._key_cycle is None:
                return ""
            return next(cls._key_cycle)

    def __init__(self, task: str = "default"):
        self.task = task
        # PRIMARY: PAID model (user's OPENROUTER_MODEL) — used FIRST for ALL tasks.
        if task == "judge":
            self.model = os.environ.get("OPENROUTER_MODEL_JUDGE_PRIMARY", "anthropic/claude-3-5-sonnet")
        else:
            self.model = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash-0731")
        # FREE fallback for this task (used if PAID fails with 429/402/quota)
        self.free_fallback = os.environ.get(
            f"OPENROUTER_MODEL_{task.upper()}",
            self.TASK_FREE_FALLBACK_MAP.get(task, self.TASK_FREE_FALLBACK_MAP["default"]),
        )
        self.base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        # [C5] Cầu dao theo (provider, model): fail liên tục → fast-fail có
        # thời hạn, không ném request vào endpoint đang sập.
        self._breaker = CircuitBreaker(
            failure_threshold=int(os.environ.get("SCP_LLM_BREAKER_THRESHOLD", "3")),
            cooldown_seconds=float(os.environ.get("SCP_LLM_BREAKER_COOLDOWN_SEC", "300")),
        )
        self._client: httpx.AsyncClient | None = None
        # [Fix 4-a-014] Race condition on lazy _client init — two concurrent
        # _call_model() calls could both see _client is None, both create an
        # httpx.AsyncClient, and one would leak. asyncio.Lock + double-checked
        # init closes the race. DNA #9 (no harm — leaked httpx clients).
        self._client_lock = asyncio.Lock()

    @property
    def api_key(self) -> str:
        """Current API key (round-robin across 3 keys)."""
        return self._next_key()

    @property
    def enabled(self) -> bool:
        """True if at least one non-placeholder API key is configured and model is configured."""
        self._init_keys()
        self._init_dynamic_models()
        return len(self._API_KEYS) > 0 and bool(self.model)

    def _key_count(self) -> int:
        """Số key khả dụng — subclass có key-instance override chỗ này."""
        self._init_keys()
        self._init_dynamic_models()
        return len(self._API_KEYS)

    async def _call_model(self, model: str, messages: list[dict], api_key: str) -> tuple[str | None, str | None]:
        """Call a specific model with a specific key. Returns (answer, error).

        [#33 Resilient Transport] Lỗi TRANSIENT (network/5xx/timeout) được
        retry tối đa 2 lần với exponential backoff + jitter trước khi tính
        là failure thật — chống sập vì một gián đoạn mạng vài trăm ms.
        429/402 KHÔNG retry (rate-limit là trạng thái provider — failover
        sang tầng kế tiếp là đúng, chờ thêm chỉ lãng phí)."""
        # [AUDIT-FIX low-7a] Fast-fail khi OPEN; khi cooldown vừa hết, caller
        # này là probe HALF-OPEN DUY NHẤT được đi tiếp (các caller khác nhận
        # False → circuit_open). finally-release bảo đảm probe reservation
        # không kẹt trên các nhánh return không record (dead-model skip,
        # egress_denied, 429/402, last_error rỗng) — record_success/record_
        # failure cũng tự nhả, nên release ở finally là idempotent.
        if not self._breaker.acquire_half_open_probe():
            # [C5] Fast-fail: endpoint đang bị ngắt — không đốt time-out.
            return None, "circuit_open (fast-fail)"
        try:
            return await self._call_model_inner(model, messages, api_key)
        finally:
            self._breaker.release_half_open_probe()

    async def _call_model_inner(
        self, model: str, messages: list[dict], api_key: str
    ) -> tuple[str | None, str | None]:
        if _is_dead_model(self.PROVIDER_NAME, self.base_url, model):
            # [F-05] Dead-candidate breaker: skip ONLY the cached-dead
            # candidate — no HTTP attempt, no key rotation; the chain
            # continues to the next candidate with its normal semantics.
            with _DEAD_MODEL_REGISTRY_LOCK:
                _dead_reason = _DEAD_MODEL_REASONS.get(
                    (self.PROVIDER_NAME, self.base_url, model), _REASON_MODEL_NOT_FOUND
                )
            return None, (
                f"dead_model_skipped: {model} "
                f"({_dead_reason} cached for {self.PROVIDER_NAME})"
            )
        last_error: str | None = None
        for attempt in range(3):
            answer, err = await self._call_model_once(model, messages, api_key)
            if answer is not None:
                self._breaker.record_success()  # thành công thật: reset chuỗi lỗi
                _clear_rate_limit_streak(self.PROVIDER_NAME, self.base_url, model)
                return answer, err
            if err == "egress_denied":
                return None, err
            if err and err.startswith("model_not_found"):
                # [F-05] Permanent per-model failure (strict 404
                # model-not-found classification) — cache it kill-switch-aware
                # and fail over WITHOUT the transient retries; the provider
                # breaker still records the endpoint failure exactly once
                # ([BREAKER-ONCE]) and the error carries the
                # recorded_failure: marker so chat()'s tail never
                # double-counts it.
                _mark_dead_model(self.PROVIDER_NAME, self.base_url, model)
                self._breaker.record_failure()
                return None, f"{_RECORDED_FAILURE_PREFIX}{err}"
            if err and err.startswith("payment_required:"):
                # [F-05-EXT] 402 Payment Required = hard quota: payment state
                # does not change mid-process → cache the candidate dead
                # immediately (same registry + kill-switch as the 404 cache)
                # and fail over without transient retries. Breaker failure is
                # recorded exactly once here ([BREAKER-ONCE]) and the error is
                # returned with the recorded_failure: marker so chat()'s tail
                # does not double-count it.
                _mark_dead_model(self.PROVIDER_NAME, self.base_url, model, reason=_REASON_PAYMENT_DEAD)
                _clear_rate_limit_streak(self.PROVIDER_NAME, self.base_url, model)
                self._breaker.record_failure()
                return None, f"{_RECORDED_FAILURE_PREFIX}{err}"
            if err and err.startswith("rate_limited:"):
                # [F-05-EXT] 429 may be transient: cache the candidate dead
                # only after N consecutive 429s in-process for this candidate
                # (any non-429 outcome resets the streak). At threshold the
                # breaker failure is recorded here ([BREAKER-ONCE]) and the
                # error carries the recorded_failure: marker; below threshold
                # the historical semantics are unchanged: failover now, no
                # cache, no inner record — the error stays UNMARKED so
                # chat()'s tail counts it exactly once.
                if _record_rate_limit_hit(self.PROVIDER_NAME, self.base_url, model):
                    _mark_dead_model(self.PROVIDER_NAME, self.base_url, model, reason=_REASON_RATE_DEAD)
                    self._breaker.record_failure()
                    return None, f"{_RECORDED_FAILURE_PREFIX}{err}"
                return None, err
            if err and ("429" in err or "402" in err):
                return None, err  # quota/rate-limit: failover, không retry tại chỗ
            _clear_rate_limit_streak(self.PROVIDER_NAME, self.base_url, model)
            last_error = err
            transient = (
                err is not None
                and not any(sig in err for sig in ("429", "402", "circuit_open", "egress_denied"))
            )
            if attempt < 2 and transient:
                await asyncio.sleep(min(0.25 * (2 ** attempt) + _BACKOFF_JITTER_RNG.uniform(0, 0.15), 2.0))
                continue
            break
        # Breaker chỉ ghi MỘT lần theo kết quả cuối — 3 retry nhanh trong 1s
        # không được phép mở breaker oan (transient blip != endpoint chết).
        # [BREAKER-ONCE] Error được trả kèm recorded_failure: marker vì
        # failure này ĐÃ được record ngay tại đây.
        if last_error:
            self._breaker.record_failure()
            return None, f"{_RECORDED_FAILURE_PREFIX}{last_error}"
        return None, last_error

    async def _get_client(self) -> httpx.AsyncClient:
        """Double-checked locking accessor for HTTP client singleton."""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def _call_model_once(self, model: str, messages: list[dict], api_key: str) -> tuple[str | None, str | None]:
        if not _llm_egress_allowed(self.base_url):
            logger.warning(
                "[LLM Gateway] outbound blocked by SCP egress policy: provider=%s base_url=%s",
                self.PROVIDER_NAME,
                self.base_url,
            )
            return None, "egress_denied"
        # [EE-G1] Generic egress gate (idempotent, SCP_EGRESS_MODE-aware) on
        # the real request URL. Denial maps to the SAME "egress_denied"
        # sentinel as the LLM check above — _call_model returns it without
        # retry and without recording a breaker failure (fail-closed, no I/O).
        # The LLM operator allowlist (SCP_LLM_EGRESS_ALLOWLIST) is passed as
        # extra_allowed_hosts so the generic allowlist branch and the LLM
        # policy above agree on this transport instead of contradicting each
        # other; deny modes still fail closed for every non-loopback host.
        try:
            llm_allowlist = frozenset(
                item.strip().lower().rstrip(".")
                for item in os.environ.get("SCP_LLM_EGRESS_ALLOWLIST", "").split(",")
                if item.strip()
            )
            enforce_egress_policy(
                f"{self.base_url}/chat/completions", extra_allowed_hosts=llm_allowlist
            )
        except EgressDeniedError:
            return None, "egress_denied"
        try:
            # [Fix 4-a-014] Double-checked locking — only the first concurrent
            # caller creates _client; subsequent callers see it set + skip
            # the lock entirely (no contention on the hot path).
            client = await self._get_client()
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json={"model": model, "messages": messages, "stream": False},
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://scp-vietnam.local",
                    "X-Title": "SCP Gateway",
                },
            )
            # [F-05-EXT] Strict per-status classification from the REAL HTTP
            # status (never body text): 429 = rate limit (may be transient →
            # consecutive-streak breaker), 402 = payment required (hard quota →
            # immediate dead-candidate cache). Both keep the quota/rate-limit
            # phrasing so chat()'s key-rotation/failover matching still sees
            # them; _call_model_inner handles the sentinels.
            if resp.status_code == 402:
                return None, "payment_required: HTTP 402 (quota/rate-limit)"
            if resp.status_code == 429:
                return None, "rate_limited: HTTP 429 (quota/rate-limit)"
            # [F-05] Strict model-not-found classification: a 404 whose body
            # actually says the model does not exist. Other 404s fall through
            # to raise_for_status → normal failure, NEVER breaker-cached.
            if resp.status_code == 404 and _is_model_not_found_response(resp):
                return None, (
                    f"model_not_found: HTTP 404 for model '{model}' "
                    f"on {self.PROVIDER_NAME}"
                )
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if answer:
                return (answer, None)
            return (None, "empty_completion")
        except Exception as e:
            logger.debug(f"OpenRouterProvider._call_model_once: exception ignored: {e}", exc_info=True)
            return None, str(e)

    async def chat(self, question: str, context: str = "", system_prompt: str = "", prioritize_free: bool = False) -> tuple[str | None, str]:
        if not self.enabled:
            return None, "none"

        primary_model = self.model
        fallback_model = self.free_fallback
        if prioritize_free:
            primary_model, fallback_model = fallback_model, primary_model

        if not self._breaker.is_open():
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": f"{context}\n\n{question}".strip()})

            err: str | None = None
            for _attempt in range(min(3, self._key_count())):
                key = self._next_key()
                answer, err = await self._call_model(primary_model, messages, key)
                if answer:
                    self._breaker.record_success()
                    return answer, f"{self.PROVIDER_NAME}:{primary_model}"
                if err == "egress_denied":
                    return None, "none"
                if err and "quota" not in err.lower() and "rate-limit" not in err.lower() and "429" not in err and "402" not in err:
                    logger.debug(f"OpenRouter PAID ({primary_model}) failed: {err}")
                    break
                logger.debug(f"OpenRouter PAID ({primary_model}) key failed: {err}, trying next key")

            # [BREAKER-ONCE 2026-09-30] Exactly-once contract: _call_model/
            # _call_model_inner ĐÃ record breaker failure cho mọi error mang
            # marker "recorded_failure:" (404 model-not-found, 402 hard quota,
            # 429 threshold-trip, final transient) — tail PHẢI skip chúng.
            # Chỉ các quota/rate error CHƯA đánh dấu (429 dưới streak
            # threshold, legacy provider 429/402 error strings) được count
            # ĐÚNG MỘT lần tại đây. (Comment cũ "Quota/rate failures return
            # before that point" đã stale sau F-05-EXT: 402/429-threshold bị
            # record ngay trong inner, không còn "return before that point".)
            if (
                err
                and not err.startswith(_RECORDED_FAILURE_PREFIX)
                and any(sig in err.lower() for sig in ("quota", "rate-limit", "429", "402"))
            ):
                self._breaker.record_failure()

            if fallback_model != primary_model:
                key = self._next_key()
                answer, err = await self._call_model(fallback_model, messages, key)
                if answer:
                    return answer, f"{self.PROVIDER_NAME}:{fallback_model}"
                if err == "egress_denied":
                    return None, "none"
                logger.debug(f"{self.PROVIDER_NAME} FREE fallback ({fallback_model}) failed: {err}")

            if self.PROVIDER_NAME == "openrouter" and fallback_model != "openrouter/free" and primary_model != "openrouter/free":
                key = self._next_key()
                answer, err = await self._call_model("openrouter/free", messages, key)
                if answer:
                    logger.info("OpenRouter auto-router (openrouter/free) succeeded")
                    return answer, f"{self.PROVIDER_NAME}:openrouter/free"
                logger.debug(f"OpenRouter auto-router failed: {err}")
        else:
            logger.warning(f"[{self.PROVIDER_NAME}] Circuit Breaker is OPEN. Bypassing provider to prevent rate-limit ban.")

        return None, "none"

    def stats(self) -> dict:
        self._init_keys()
        self._init_dynamic_models()
        return {
            "configured": self.enabled,
            "num_keys": len(self._API_KEYS),
            "primary_model": self.model,
            "free_fallback": self.free_fallback,
            "task": self.task,
            "total_free_models_available": len(OPENROUTER_FREE_MODELS),
        }


# ============================================================
# [FAILOVER] Provider dự phòng ngoài OpenRouter.
# Khi 1 API bị rate-limit/quota/sập, gateway tự chuyển sang provider kế
# tiếp trong chuỗi. Các provider OpenAI-compatible khác khai báo qua
# SCP_LLM_FALLBACK_PROVIDERS mà không cần sửa code:
# "name:KEY_ENV:BASEURL_ENV:MODEL_ENV,name2:..."
# ============================================================
_PLACEHOLDER_KEYS = {"", "changeme", "your-key", "your_api_key", "placeholder", "xxx", "sk-xxx", "none"}


class EnvCompatProvider(OpenRouterProvider):
    """Provider OpenAI-compatible khai báo qua env (instance-keyed)."""

    def __init__(self, name: str, task: str, key_env: str, base_url_env: str, model_env: str, default_model: str = "", default_base_url: str = ""):
        self.PROVIDER_NAME = name
        self.task = task
        key = os.environ.get(key_env, "").strip()
        self._instance_keys = [key] if key and key.lower() not in _PLACEHOLDER_KEYS else []
        self._instance_key_cycle = itertools.cycle(self._instance_keys) if self._instance_keys else None
        self.model = os.environ.get(model_env, default_model)
        self.free_fallback = self.model
        self.base_url = os.environ.get(base_url_env, default_base_url).rstrip("/")
        self._breaker = CircuitBreaker(
            failure_threshold=int(os.environ.get("SCP_LLM_BREAKER_THRESHOLD", "3")),
            cooldown_seconds=float(os.environ.get("SCP_LLM_BREAKER_COOLDOWN_SEC", "300")),
        )
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()

    @classmethod
    def _init_keys(cls) -> None:
        return None  # instance-level keys

    _dynamic_models_loaded = False

    @classmethod
    def _init_dynamic_models(cls) -> None:
        if cls._dynamic_models_loaded:
            return
        try:
            from scp.llm_gateway.free_catalog import refresh_free_catalog
            refresh_free_catalog()
        except Exception as e:
            logger.warning('[LLM Gateway] free-catalog refresh failed: %s', e, exc_info=True)
        cls._dynamic_models_loaded = True


    @property
    def enabled(self) -> bool:
        return bool(self._instance_keys) and bool(self.model) and bool(self.base_url)

    def _key_count(self) -> int:
        return len(self._instance_keys)

    def _next_key(self) -> str:
        return next(self._instance_key_cycle) if self._instance_key_cycle else ""

    def stats(self) -> dict:
        return {
            "configured": self.enabled,
            "num_keys": len(self._instance_keys),
            "primary_model": self.model,
            "base_url": self.base_url,
            "task": self.task,
        }


# ============================================================
# GATEWAY — single entry point with task routing
# ============================================================

class LLMGateway:
    """Unified LLM gateway — OpenRouter API only, routed per task.

    Task routing (primary model is OPENROUTER_MODEL for every task; the
    per-task provider differs only in its FREE fallback model):
        task="autofix"       → free fallback nemotron-3-ultra-550b:free
        task="why"           → free fallback gemma-4-31b-it:free
        task="learning"      → free fallback gemma-4-31b-it:free
        task="fast_learning" → free fallback nemotron-3-nano-30b:free
        task="judge"         → free fallback nemotron-3-super-120b:free
        task="chat"          → free fallback gpt-oss-20b:free
        task="default"       → free fallback gpt-oss-20b:free

    Usage (async):
        gw = get_gateway()
        answer, provider = await gw.chat("What is 2+2?", task="default")

    Usage (sync — for background threads):
        answer, provider = chat_sync("What is 2+2?", task="learning")
    """

    def __init__(self):
        tasks = ("autofix", "why", "learning", "fast_learning", "judge", "chat")
        # Tier 1 — OpenRouter (primary, per-task FREE fallback map).
        for task in tasks:
            provider = OpenRouterProvider(task=task)
            setattr(self, f"openrouter_{task}", provider)
        self.openrouter_default = OpenRouterProvider(task="default")
        # Backward-compat alias — old code used `gateway.openrouter`.
        self.openrouter = self.openrouter_default
        # [AUDIT-FIX low-7c] Đã xóa `or self.openrouter_fast` — nhánh chết:
        # openrouter_fast_learning luôn được set bởi vòng lặp task phía trên
        # ("fast_learning" ∈ tasks), nên RHS không bao giờ được đánh giá.
        # Tier 3 — provider OpenAI-compatible khai báo qua env (không sửa code).
        self._extra_providers: dict[str, list[EnvCompatProvider]] = {t: [] for t in tasks + ("default",)}
        self._parse_extra_providers()
        self._stats_lock = threading.Lock()  # [AUDIT-FIX low-7d] telemetry-only
        self._rr_counter = 0  # brand-neutral rotation: không ưu tiên model nào
        self._stats = {
            "total_calls": 0,
            "openrouter_calls": 0,
            "extra_calls": 0,
            "failover_count": 0,
            "failures": 0,
            # [S21 HEDGE] telemetry — cùng store _stats hiện có, không store mới.
            "hedge_fires": 0,
            "hedge_wins": 0,
            "hedge_caps": 0,
        }

    def _parse_extra_providers(self) -> None:
        spec = os.environ.get("SCP_LLM_FALLBACK_PROVIDERS", "")
        tasks = ("autofix", "why", "learning", "fast_learning", "judge", "chat", "default")

        # [NEW] 1. Generic OpenAI API (highest priority if configured)
        for task in tasks:
            self._extra_providers.setdefault(task, []).append(
                EnvCompatProvider(
                    "openai_compat", task,
                    "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL",
                    default_base_url="https://api.openai.com/v1"
                )
            )

        for entry in (e.strip() for e in spec.split(",") if e.strip()):
            parts = [p.strip() for p in entry.split(":")]
            if len(parts) != 4:
                logger.warning("[FAILOVER] malformed SCP_LLM_FALLBACK_PROVIDERS entry (want name:KEY_ENV:BASEURL_ENV:MODEL_ENV): %s", entry)
                continue
            name, key_env, base_env, model_env = parts
            for task in tasks:
                self._extra_providers.setdefault(task, []).append(
                    EnvCompatProvider(name, task, key_env, base_env, model_env)
                )



    def _provider_chain(self, task: str) -> list:
        """Chuỗi failover theo task."""
        openrouter = {
            "autofix":       self.openrouter_autofix,
            "why":           self.openrouter_why,
            "learning":      self.openrouter_learning,
            "fast_learning": self.openrouter_fast_learning,
            "judge":         self.openrouter_judge,
            "chat":          self.openrouter_chat,
        }.get(task, self.openrouter_default)

        extra = self._extra_providers.get(task, [])
        openai_compat = extra[0] if extra and extra[0].PROVIDER_NAME == "openai_compat" else None

        chain = []
        # Priority 1: Custom OpenAI API (if enabled by env vars)
        if openai_compat and openai_compat.enabled:
            chain.append(openai_compat)

        # Priority 2: OpenRouter (if enabled)
        if openrouter.enabled:
            chain.append(openrouter)

        # Priority 3: Other fallback providers
        if extra:
            start_idx = 1 if openai_compat else 0
            chain.extend(extra[start_idx:])

        return chain

    def _bump_stat(self, key: str, amount: int = 1) -> None:
        """[AUDIT-FIX low-7d] Increment telemetry counter dưới lock. Telemetry
        only — không dùng làm tín hiệu điều khiển."""
        with self._stats_lock:
            self._stats[key] = self._stats.get(key, 0) + amount

    async def chat(
        self,
        question: str,
        context: str = "",
        system_prompt: str = "",
        task: str = "default",
    ) -> tuple[str | None, str]:
        """Chat with LLM — đa provider failover.

        Thứ tự: OpenRouter (primary) → provider env-declared (OPENAI_API_KEY) → SCP_LLM_FALLBACK_PROVIDERS.
        Provider bị rate-limit (429/402) hoặc breaker OPEN → chuyển NGAY sang
        provider kế tiếp, caller không thấy lỗi, không đốt time-out.
        """
        self._bump_stat("total_calls")  # [AUDIT-FIX low-7d]
        prioritize_free = False
        if os.environ.get("SCP_BUDGET_ROUTING", "0") == "1":
            from scp.core.budget_engine import order_tiers
            tiers = order_tiers(question + context, task)
            if tiers[0] == "free":
                prioritize_free = True

        chain = self._provider_chain(task)
        # [KHÔNG ƯU TIÊN MODEL] Pool brand-neutral: provider khỏe xoay vòng theo
        # lượt gọi (chia tải đều, không đặt clip nào lên trên vĩnh viễn);
        # provider breaker OPEN bị đẩy xuống cuối (chỉ dùng khi hết người khỏe).
        enabled = [p for p in chain if p.enabled]
        healthy = [p for p in enabled if not p._breaker.is_open()]
        degraded = [p for p in enabled if p._breaker.is_open()]
        pool = healthy + degraded
        if not pool:
            self._bump_stat("failures")  # [AUDIT-FIX low-7d]
            return None, "none"
        with self._stats_lock:  # [AUDIT-FIX low-7d] atomic rotate
            start = self._rr_counter % len(pool)
            self._rr_counter += 1
        rotation = pool[start:] + pool[:start]

        # [S21 HEDGE] Owner directive: LLM chậm ~10s → bắn LLM/API khác song
        # song, ai trả trước thắng. Kill-switch SCP_LLM_HEDGE=off hoặc chain
        # chỉ có 1 provider → failover tuần tự cũ (giữ nguyên hành vi).
        hedge_on, attempt_deadline, hedge_cap = _hedge_settings()
        if hedge_on and len(rotation) > 1:
            return await self._chat_hedged(
                rotation, question, context, system_prompt, prioritize_free,
                attempt_deadline, hedge_cap,
            )
        return await self._chat_sequential(
            rotation, question, context, system_prompt, prioritize_free,
        )

    async def _chat_sequential(
        self,
        rotation: list,
        question: str,
        context: str,
        system_prompt: str,
        prioritize_free: bool,
    ) -> tuple[str | None, str]:
        """Failover TUẦN TỰ gốc (SCP_LLM_HEDGE=off hoặc chain 1 provider)."""
        attempted = 0
        for provider in rotation:
            attempted += 1
            self._bump_stat(f"{provider.PROVIDER_NAME}_calls")  # [AUDIT-FIX low-7d]
            answer, _provider_label = await provider.chat(
                question,
                context,
                system_prompt,
                prioritize_free=prioritize_free,
            )
            if answer:
                if attempted > 1:
                    self._bump_stat("failover_count")  # [AUDIT-FIX low-7d]
                return answer, _provider_label
            # provider trả None (quota/rate-limit/breaker) → sang provider kế

        self._bump_stat("failures")  # [AUDIT-FIX low-7d]
        return None, "none"

    async def _chat_hedged(
        self,
        rotation: list,
        question: str,
        context: str,
        system_prompt: str,
        prioritize_free: bool,
        attempt_deadline: float,
        hedge_cap: float,
    ) -> tuple[str | None, str]:
        """[S21] Hedged race — first-result-wins đa provider.

        Provider đầu tiên chạy NGAY; quá ``attempt_deadline`` mà chưa có kết
        quả thì provider KẾ TIẾP theo chain sẵn có được bắn vào race SONG
        SONG (task đang chạy KHÔNG bị hủy — "ai về trước thắng"). Answer
        thành công đầu tiên của bất kỳ provider nào được trả về ngay; các
        task còn lại chỉ bị hủy ở bước DỌN DẸP sau khi winner đã chắc chắn
        (hủy sau khi đã có winner là an toàn, không double-spend vô nghĩa).
        Provider LỖI (không chậm) vẫn failover NGAY sang kế tiếp như tuần tự.
        Mỗi provider chỉ 1 hedge attempt — retry logic cũ giữ nguyên trong
        provider.chat(). Quá ``hedge_cap``: fail-closed (None + error rõ),
        không chờ vô hạn. Mọi attempt vẫn đi qua breaker + egress guard của
        provider (không đổi).
        """
        loop = asyncio.get_running_loop()
        start = time.monotonic()
        cap_at = start + hedge_cap
        pending: set[asyncio.Task] = set()
        idx_by_task: dict[asyncio.Task, int] = {}
        expiry: dict[asyncio.Task, float] = {}  # hedge-fire deadline per attempt
        next_idx = 0
        errors: list[str] = []

        def _launch_next(reason: str, slow_provider: str = "") -> None:
            nonlocal next_idx
            if next_idx >= len(rotation):
                return
            provider = rotation[next_idx]
            task_idx = next_idx
            next_idx += 1
            self._bump_stat(f"{provider.PROVIDER_NAME}_calls")  # [AUDIT-FIX low-7d]
            task = loop.create_task(
                provider.chat(question, context, system_prompt, prioritize_free=prioritize_free)
            )
            pending.add(task)
            idx_by_task[task] = task_idx
            expiry[task] = time.monotonic() + attempt_deadline
            if reason == "hedge":
                self._bump_stat("hedge_fires")  # [AUDIT-FIX low-7d]
                logger.info(
                    "[S21 HEDGE] fire: %s chưa trả sau deadline %.1fs → bắn thêm %s (chain idx %d) vào race song song",
                    slow_provider, attempt_deadline, provider.PROVIDER_NAME, task_idx,
                )

        _launch_next("first")
        winner: tuple[str, str, int] | None = None
        cap_hit = False
        try:
            while pending or next_idx < len(rotation):
                now = time.monotonic()
                if now >= cap_at:
                    cap_hit = True
                    break
                if not pending:
                    # Defensive: hết task đang chạy mà còn provider → bắn tiếp.
                    _launch_next("after-failure")
                    continue
                # Thức dậy sớm nhất tại: hedge-fire deadline gần nhất (nếu còn
                # provider để bắn) hoặc hedge cap — không bao giờ chờ vô hạn.
                wake = cap_at
                if next_idx < len(rotation) and expiry:
                    wake = min(wake, min(expiry[t] for t in pending if t in expiry))
                timeout = max(0.0, wake - now)
                done, _still_pending = await asyncio.wait(
                    set(pending), timeout=timeout, return_when=asyncio.FIRST_COMPLETED
                )
                # Winner: success đầu tiên theo THỨ TỰ chain (deterministic
                # tie-break khi nhiều task về đích cùng một lượt wait).
                for task in sorted(done, key=lambda t: idx_by_task[t]):
                    pending.discard(task)
                    expiry.pop(task, None)
                    idx = idx_by_task.pop(task)
                    try:
                        answer, label = task.result()
                    except Exception as exc:  # provider.chat tự nuốt lỗi; phòng hộ fail-closed
                        logger.debug(f"LLMGateway._chat_hedged: exception ignored: {exc}", exc_info=True)
                        errors.append(f"{rotation[idx].PROVIDER_NAME}: {type(exc).__name__}")
                        continue
                    if answer:
                        winner = (answer, label, idx)
                        break
                    errors.append(f"{rotation[idx].PROVIDER_NAME}: {label}")
                if winner is not None:
                    break
                if done and next_idx < len(rotation):
                    # Provider vừa LỖI → chuyển NGAY sang kế tiếp (failover
                    # tuần tự giữa các lỗi; hedge song song chỉ cho provider CHẬM).
                    _launch_next("after-failure")
                # Hedge-fire: task còn chạy quá attempt deadline → bắn kế tiếp
                # SONG SONG vào race (không hủy task đang chạy).
                now = time.monotonic()
                for task in [t for t in list(expiry) if expiry[t] <= now]:
                    expiry.pop(task, None)  # mỗi provider chỉ được fire đúng 1 lần
                    if next_idx < len(rotation):
                        _launch_next("hedge", slow_provider=rotation[idx_by_task[task]].PROVIDER_NAME)
        finally:
            # Dọn dẹp: winner đã chắc chắn (hoặc cap/toàn fail) → hủy phần còn
            # lại. Hủy DIỄN RA SAU khi winner đã được lấy kết quả — an toàn.
            leftover = [t for t in pending if not t.done()]
            for task in leftover:
                task.cancel()
            if leftover:
                await asyncio.gather(*leftover, return_exceptions=True)

        if winner is not None:
            answer, label, idx = winner
            if idx > 0:
                self._bump_stat("failover_count")  # [AUDIT-FIX low-7d]
            self._bump_stat("hedge_wins")  # [AUDIT-FIX low-7d]
            logger.info(
                "[S21 HEDGE] race won by %s sau %.2fs (first_provider_won=%s, hedge_fires=%d)",
                label, time.monotonic() - start, idx == 0, self._stats["hedge_fires"],
            )
            return answer, label

        self._bump_stat("failures")  # [AUDIT-FIX low-7d]
        if cap_hit:
            self._bump_stat("hedge_caps")  # [AUDIT-FIX low-7d]
            logger.error(
                "[S21 HEDGE] cap %.0fs vượt quá sau %.2fs — fail-closed (không answer); lỗi các attempt: %s",
                hedge_cap, time.monotonic() - start, "; ".join(errors) or "no-attempt-error",
            )
            return None, "hedge_cap_exceeded"
        logger.error(
            "[S21 HEDGE] tất cả provider trong race đều lỗi: %s",
            "; ".join(errors) or "unknown",
        )
        return None, "none"

    def chat_sync(
        self,
        question: str,
        context: str = "",
        system_prompt: str = "",
        task: str = "default",
    ) -> tuple[str | None, str]:
        """Sync wrapper for background threads. Runs async chat safely.

        [RUNTIME-FIX-2] Root cause (runtime log line 732, 941):
          RuntimeWarning: coroutine 'LLMGateway.chat' was never awaited
        Bug: `loop.run_until_complete(self.chat(...))` evaluates self.chat(...)
        FIRST, creating a coroutine object. If run_until_complete raises (e.g.
        'event loop already running' inside async thread, or RuntimeError on
        loop creation), the coroutine object is never awaited and never closed
        -> leaks memory + GC pressure. In production 24/7 this means thousands
        of leaked coroutines per day.

        Fix: hold the coroutine reference explicitly. On ANY exception path,
        call coro.close() to release it cleanly. Use asyncio.run() (which
        handles loop creation+close properly) instead of manual loop management.
        Detect 'event loop already running' and fall back to ThreadPoolExecutor
        so we don't nest event loops.
        """
        coro = self.chat(question, context, system_prompt, task=task)
        # [AUDIT-FIX low-7b] Flag quyền sở hữu coroutine: trên path timeout,
        # worker bị abandon (shutdown(wait=False)) vẫn chạy nốt coroutine →
        # caller KHÔNG được close() coroutine của worker từ luồng khác (race).
        _abandoned_worker_owns_coro = False
        try:
            # Detect if we're already inside an async context (event loop running).
            # In that case, asyncio.run() would raise RuntimeError. Fall back to
            # running in a fresh thread with its own event loop.
            try:
                asyncio.get_running_loop()
                _in_async = True
            except RuntimeError:
                logger.debug('LLMGateway.chat_sync: RuntimeError ignored', exc_info=True)
                _in_async = False

            if _in_async:
                # We're inside async code (e.g. called from async def without await).
                # Run the coroutine in a separate thread to avoid 'loop already running'.
                import concurrent.futures
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                try:
                    future = pool.submit(asyncio.run, coro)
                    return future.result(timeout=SYNC_CALL_TIMEOUT_SECONDS)
                except concurrent.futures.TimeoutError:
                    _abandoned_worker_owns_coro = True
                    logger.warning(
                        "chat_sync: vượt SYNC_CALL_TIMEOUT %.0fs — abandon worker "
                        "thread (bounded leak: đúng 1 worker/lần timeout, worker tự "
                        "kết thúc khi coroutine hoàn tất; caller không join nữa)",
                        SYNC_CALL_TIMEOUT_SECONDS,
                    )
                    raise
                finally:
                    # [AUDIT-FIX low-7b] shutdown(wait=False): timeout path KHÔNG
                    # join worker (từng bị context manager `with` join vô hạn sau
                    # khi caller đã hết 90s). Success/error path worker đã xong
                    # nên shutdown không block.
                    pool.shutdown(wait=False)
            else:
                # Normal sync context — asyncio.run handles loop lifecycle properly.
                return asyncio.run(coro)
        except Exception as e:
            # CRITICAL: ensure coroutine is closed to prevent leak.
            # RuntimeWarning 'coroutine was never awaited' happens when coro
            # is created but never awaited AND never closed.
            # [SCP-DNA-FIX R5-5] TẠI SAO: Python 3 semantic — `except Exception
            # as e:` DELETES `e` on exit of the except block (PEP 3110). The
            # inner `try/except` below calls `coro.close()`, and if coro.close()
            # raises, the inner except's exit deletes its OWN `e` — but the
            # outer `e` is ALSO already gone by the time we reach the
            # `logger.warning(f"chat_sync failed: {e}")` line below, raising
            # NameError. Breaks the chat_sync fail-open contract (returns
            # (None, "none") on error). mypy [misc] "Trying to read deleted
            # variable e" caught it. Fix: snapshot `e` into a local `_err`
            # BEFORE the inner try so it survives the inner-except deletion.
            _err = e  # save before inner try deletes e
            try:
                if not _abandoned_worker_owns_coro:
                    coro.close()
            except Exception as e:
                logger.exception("[client.py:608] silenced exception")
            logger.warning(f"chat_sync failed: {_err}", exc_info=True)  # upgrade debug->warning for observability
            self._bump_stat("failures")  # [AUDIT-FIX low-7d]
            return None, "none"

    def stats(self) -> dict:
        extras: dict[str, dict] = {}
        for providers in self._extra_providers.values():
            for provider in providers:
                if provider.PROVIDER_NAME not in extras:
                    extras[provider.PROVIDER_NAME] = provider.stats()
        with self._stats_lock:  # [AUDIT-FIX low-7d] consistent snapshot
            stats_snapshot = dict(self._stats)
        return {
            **stats_snapshot,
            "openrouter_default":  self.openrouter_default.stats(),
            "openrouter_autofix":  self.openrouter_autofix.stats(),
            "openrouter_why":      self.openrouter_why.stats(),
            "openrouter_learning": self.openrouter_learning.stats(),
            "openrouter_fast_learning": self.openrouter_fast_learning.stats(),
            "openrouter_judge":    self.openrouter_judge.stats(),
            "extra_providers": extras,
        }


# ============================================================
# SINGLETON (thread-safe — EXEC-2 R3)
# ============================================================
# FRESH-2 finding: bare `if _gateway is None: _gateway = LLMGateway()` had no
# lock. Two concurrent first-callers (e.g. /ask hit while a learning thread
# boots) would both pass the None check and create duplicate LLMGateway
# instances — leaking httpx.AsyncClient connection pools and breaking the
# shared-stats invariant. Fix: double-checked locking with threading.Lock.
# ============================================================

_gateway: LLMGateway | None = None
_gateway_lock = threading.Lock()


def get_gateway() -> LLMGateway:
    """Get or create the singleton LLM gateway (thread-safe)."""
    global _gateway
    if _gateway is None:
        with _gateway_lock:
            # Re-check inside lock — another thread may have created it while
            # we were waiting.
            if _gateway is None:
                _gateway = LLMGateway()
                try:
                    from scp.llm_gateway.free_catalog import start_background_refresh
                    start_background_refresh()
                except Exception:
                    logger.warning('get_gateway: Exception not handled', exc_info=True)
    return _gateway


def chat_sync(
    question: str,
    context: str = "",
    system_prompt: str = "",
    task: str = "default",
) -> tuple[str | None, str]:
    """Module-level sync shortcut. Uses singleton gateway."""
    return get_gateway().chat_sync(question, context, system_prompt, task=task)
