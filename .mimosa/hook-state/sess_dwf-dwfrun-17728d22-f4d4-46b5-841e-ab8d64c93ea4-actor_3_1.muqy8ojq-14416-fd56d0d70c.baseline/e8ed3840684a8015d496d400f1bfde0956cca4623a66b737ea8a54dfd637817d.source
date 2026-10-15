# SCP CIRCUIT: M13 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M13-closure.json)
"""
[Task 8-A] V104 endpoints │Ă¢â€Â¬Ă¢â‚¬Â extracted from api_server.py

TÄ‚Â¡Ă‚ÂºĂ‚Â I SAO: api_server.py 2,144 LOC god file. TĂ„â€Ă‚Â¡ch 16 routes /v104/* vĂ„â€Ă‚Â o module
nĂ„â€Ă‚Â y. Backward-compatible │Ă¢â€Â¬Ă¢â‚¬Â public API paths/methods unchanged.

Routes:
  GET  /v104/status                          │Ă¢â€Â¬Ă¢â‚¬Â V104 modules status
  POST /v104/multi-turn/check                │Ă¢â€Â¬Ă¢â‚¬Â Multi-turn attack pattern check
  POST /v104/image/check                     │Ă¢â€Â¬Ă¢â‚¬Â Image jailbreak via OCR
  POST /v104/voice/check                     │Ă¢â€Â¬Ă¢â‚¬Â Voice jailbreak via Whisper ASR
  GET  /v104/cross-language/transfer         │Ă¢â€Â¬Ă¢â‚¬Â Transfer VN patterns to target langs
  GET  /v104/explain                         │Ă¢â€Â¬Ă¢â‚¬Â Verdict explanation in Vietnamese
  POST /v104/fact-check                      │Ă¢â€Â¬Ă¢â‚¬Â Real-time fact check
  POST /v104/learn/ollama                    │Ă¢â€Â¬Ă¢â‚¬Â Ollama learning loop
  POST /v104/learn/local                     │Ă¢â€Â¬Ă¢â‚¬Â Local file learning
  POST /v104/learn/news                      │Ă¢â€Â¬Ă¢â‚¬Â News learning loop
  POST /v104/learn/all                       │Ă¢â€Â¬Ă¢â‚¬Â All 3 learning loops
  GET  /v104/learn/status                    │Ă¢â€Â¬Ă¢â‚¬Â Real Learning Engine status
  GET  /v104/learn/matrix                    │Ă¢â€Â¬Ă¢â‚¬Â 14 countries Ă„â€Ă¢â‚¬â€ 5 domains matrix
  POST /v104/learn/ollama-matrix             │Ă¢â€Â¬Ă¢â‚¬Â Full matrix coverage (70 questions)
  POST /v104/learn/fast                      │Ă¢â€Â¬Ă¢â‚¬Â Fast learning cycle (parallel)
  GET  /v104/learn/fast/status               │Ă¢â€Â¬Ă¢â‚¬Â Fast Learning Engine stats
  GET  /v104/learn/fast/benchmark            │Ă¢â€Â¬Ă¢â‚¬Â V104.1 sequential vs V104.2 parallel benchmark
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import logging

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import shared deps from api_server (same pattern as api/chat.py + admin_v98.py)
# [BLE001-fix] logger được định nghĩa local (cùng singleton "scp.api" như
# scp.api._shared) để ruff resolve được logging call trong except handler.
from scp.api import _shared
from scp.api._shared import verify_admin

logger = logging.getLogger("scp.api")
from scp.core.request_run_ledger import RequestRunLedger, traced_request

_V104_ROUTES_LEDGER = RequestRunLedger()

router = APIRouter(tags=["v104"])

_MAX_IMAGE_BASE64_BYTES = 10 * 1024 * 1024
_MAX_AUDIO_BASE64_BYTES = 25 * 1024 * 1024


class _PayloadTooLarge(ValueError):
    """Raised before decoding an over-budget Base64 media payload."""


class VoiceCheckRequest(BaseModel):
    audio_url: str = ""
    audio_base64: str = ""


def _decode_bounded_base64(payload: str, *, max_bytes: int, label: str) -> bytes:
    """Decode strict Base64 only after enforcing encoded and decoded limits."""
    max_chars = ((max_bytes + 2) // 3) * 4
    if len(payload) > max_chars:
        raise _PayloadTooLarge(f"{label} base64 exceeds encoded size budget")
    try:
        decoded = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"invalid {label} base64") from exc
    if len(decoded) > max_bytes:
        raise _PayloadTooLarge(f"{label} exceeds decoded size budget")
    return decoded


@router.get("/v104/status", dependencies=[Depends(verify_admin)])  # RC-2 FIX: BFLA auth
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="v104_status")
async def v104_status():
    """V104: Status of all new modules."""
    return {
        "multi_turn_tracker": _shared._multi_turn_tracker.stats(),
        "image_detector": _shared._image_detector.stats(),
        "voice_detector": _shared._voice_detector.stats(),
        "cross_language": _shared._cross_language_learner.stats(),
        "fact_checker": _shared._fact_checker.stats(),
    }


@router.post("/v104/multi-turn/check")
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="v104_multi_turn_check")
async def v104_multi_turn_check(
    session_id: str,
    question: str,
    verdict: str = "PASS",
    _admin: bool = Depends(verify_admin),
):
    """V104: Check multi-turn attack pattern."""
    result = _shared._multi_turn_tracker.track(session_id, question, verdict)
    return result.__dict__


@router.post("/v104/image/check")
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="v104_image_check")
async def v104_image_check(
    image_url: str = "",
    image_base64: str = "",
    _admin: bool = Depends(verify_admin),
):
    """V104: Check image for jailbreak via OCR."""
    if image_base64:
        try:
            image_bytes = _decode_bounded_base64(
                image_base64, max_bytes=_MAX_IMAGE_BASE64_BYTES, label="image"
            )
        except _PayloadTooLarge:
            return JSONResponse(status_code=413, content={"error": "Image payload too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid image_base64"})
        # [Fix 4-a-015] detect() runs OCR (Tesseract) │Ă¢â€Â¬Ă¢â‚¬Â blocking CPU work.
        # Wrap in asyncio.to_thread so the event loop is not blocked while
        # OCR runs (DNA #9 no harm │Ă¢â€Â¬Ă¢â‚¬Â slow /v104/image/check would stall all
        # other async requests, including /health).
        result = await asyncio.to_thread(_shared._image_detector.detect, image_bytes=image_bytes)
    elif image_url:
        # [FIX-A P0-2] Was a raw urlopen-style fetch on the client-supplied
        # URL — accepted file:// (LFI), cloud-metadata (169.254.169.254) and
        # internal-IP SSRF, followed redirects, no size cap, blocked the event
        # loop. Now: _shared._safe_fetch_url + asyncio.to_thread + generic 400
        # on policy violation (no URL echo).
        try:
            image_bytes = await asyncio.to_thread(_shared._safe_fetch_url, image_url)
            # [Fix 4-a-015] same fix │Ă¢â€Â¬Ă¢â‚¬Â detect() is blocking CPU work.
            result = await asyncio.to_thread(_shared._image_detector.detect, image_bytes=image_bytes)
        except ValueError:
            logger.warning("/v104/image/check image_url rejected by _shared._safe_fetch_url policy")
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid or disallowed image_url"},
            )
        except Exception as e:
            logger.debug(f"/v104/image/check error: {e}", exc_info=True)
            return JSONResponse(
                status_code=400,
                content={"error": "Failed to process image"},
            )
    else:
        return {"error": "Provide image_url or image_base64"}
    return result.__dict__


@router.post("/v104/voice/check")
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="v104_voice_check")
async def v104_voice_check(
    audio_url: str = "",
    audio_base64: str = "",
    payload: VoiceCheckRequest | None = Body(default=None),  # noqa: B008 — FastAPI body dependency idiom
    _admin: bool = Depends(verify_admin),
):
    """V104: Check audio for jailbreak via Whisper ASR."""
    if payload is not None:
        audio_url = audio_url or payload.audio_url
        audio_base64 = audio_base64 or payload.audio_base64
    if audio_base64:
        try:
            audio_bytes = _decode_bounded_base64(
                audio_base64, max_bytes=_MAX_AUDIO_BASE64_BYTES, label="audio"
            )
        except _PayloadTooLarge:
            return JSONResponse(status_code=413, content={"error": "Audio payload too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid audio_base64"})
        # [Fix 4-a-015] detect() runs Whisper ASR │Ă¢â€Â¬Ă¢â‚¬Â blocking CPU work.
        # Wrap in asyncio.to_thread so the event loop is not blocked while
        # Whisper transcribes (DNA #9 no harm │Ă¢â€Â¬Ă¢â‚¬Â slow /v104/voice/check would
        # stall all other async requests, including /health).
        result = await asyncio.to_thread(_shared._voice_detector.detect, audio_bytes=audio_bytes)
    elif audio_url:
        # [FIX-A P0-2] Was passing audio_url as a local file path to the
        # detector │Ă¢â€Â¬Ă¢â‚¬Â failed silently AND allowed SSRF (detector may have
        # fetched internally). Now: fetch via _shared._safe_fetch_url (scheme/IP/
        # redirect/size defenses, non-blocking) then pass audio_bytes=...
        try:
            audio_bytes = await asyncio.to_thread(_shared._safe_fetch_url, audio_url)
            # [Fix 4-a-015] same fix │Ă¢â€Â¬Ă¢â‚¬Â detect() is blocking CPU work.
            result = await asyncio.to_thread(_shared._voice_detector.detect, audio_bytes=audio_bytes)
        except ValueError:
            logger.warning("/v104/voice/check audio_url rejected by _shared._safe_fetch_url policy")
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid or disallowed audio_url"},
            )
        except Exception as e:
            logger.debug(f"/v104/voice/check error: {e}", exc_info=True)
            return JSONResponse(
                status_code=400,
                content={"error": "Failed to process audio"},
            )
    else:
        return {"error": "Provide audio_url or audio_base64"}
    return result.__dict__


@router.get("/v104/cross-language/transfer", dependencies=[Depends(verify_admin)])  # RC-2 FIX: BFLA auth
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="v104_cross_language_transfer")
async def v104_cross_language_transfer(target_lang: str = "all"):
    """V104: Transfer Vietnamese patterns to target language(s)."""
    if target_lang == "all":
        patterns = _shared._cross_language_learner.transfer_existing_vietnamese_patterns()
        return {"count": len(patterns), "patterns": patterns}
    else:
        patterns = _shared._cross_language_learner.transfer_existing_vietnamese_patterns()
        filtered = [p for p in patterns if p["target_lang"] == target_lang]
        return {"count": len(filtered), "patterns": filtered}


@router.get("/v104/explain", dependencies=[Depends(verify_admin)])  # RC-2 FIX: BFLA auth
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="v104_explain")
async def v104_explain(
    verdict: str = "PASS",
    confidence: float = 0.8,
    domain: str = "",
    sources: int = 0,
    has_attack: bool = False,
    has_bypass: bool = False,
    has_human_review: bool = False,
    lineage_overlap: float = 0.0,
    reliability_factor: float = 1.0,
):
    """V104: Explain verdict in simple Vietnamese for non-experts."""
    result = _shared._simple_explainer.explain(
        verdict=verdict, confidence=confidence, domain=domain, sources=sources,
        has_attack=has_attack, has_bypass=has_bypass, has_human_review=has_human_review,
        lineage_overlap=lineage_overlap, reliability_factor=reliability_factor,
    )
    return result.__dict__


@router.post("/v104/fact-check")
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="v104_fact_check")
async def v104_fact_check(text: str, question: str = "", _admin: bool = Depends(verify_admin)):
    """V104: Real-time fact check │Ă¢â€Â¬Ă¢â‚¬Â extract claims + verify."""
    results = await _shared._fact_checker.check_text(text, question)
    return {
        "claims_found": len(results),
        "results": [r.__dict__ for r in results],
        "stats": _shared._fact_checker.stats(),
    }


@router.post("/v104/learn/ollama")
@traced_request(_V104_ROUTES_LEDGER, require_write=True, action="v104_learn_ollama")
async def v104_learn_ollama(count: int = 10, _admin: bool = Depends(verify_admin)):
    """V104.1 FIX: Trigger Ollama learning loop │Ă¢â€Â¬Ă¢â‚¬Â ma trÄ‚Â¡Ă‚ÂºĂ‚Â­n 14 quÄ‚Â¡Ă‚Â»Ă¢â‚¬Ëœc gia Ă„â€Ă¢â‚¬â€ 5 l-Ă‚Â©nh vÄ‚Â¡Ă‚Â»Ă‚Â±c."""
    results = await _shared._real_learning.ollama_learning_cycle(count=count)
    return results


@router.post("/v104/learn/local")
@traced_request(_V104_ROUTES_LEDGER, require_write=True, action="v104_learn_local")
async def v104_learn_local(_admin: bool = Depends(verify_admin)):
    """V104 FIX: Trigger local file learning │Ă¢â€Â¬Ă¢â‚¬Â scan data/ → verify → KB."""
    results = await _shared._real_learning.local_learning_cycle()
    return results


@router.post("/v104/learn/news")
@traced_request(_V104_ROUTES_LEDGER, require_write=True, action="v104_learn_news")
async def v104_learn_news(_admin: bool = Depends(verify_admin)):
    """V104 FIX: Trigger news learning │Ă¢â€Â¬Ă¢â‚¬Â fetch RSS → verify → KB."""
    results = await _shared._real_learning.news_learning_cycle()
    return results


@router.post("/v104/learn/all")
@traced_request(_V104_ROUTES_LEDGER, require_write=True, action="v104_learn_all")
async def v104_learn_all(_admin: bool = Depends(verify_admin)):
    """V104 FIX: Trigger all 3 learning loops."""
    results = await _shared._real_learning.run_all_cycles()
    return results


@router.get("/v104/learn/status", dependencies=[Depends(verify_admin)])  # RC-2 FIX: BFLA auth
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="v104_learn_status")
async def v104_learn_status():
    """V104 FIX: Status of Real Learning Engine."""
    return _shared._real_learning.stats()


@router.get("/v104/learn/matrix", dependencies=[Depends(verify_admin)])  # RC-2 FIX: BFLA auth
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="v104_learn_matrix")
async def v104_learn_matrix():
    """V104.1 NEW: TrÄ‚Â¡Ă‚ÂºĂ‚Â£ vÄ‚Â¡Ă‚Â»Ă‚Â ma trÄ‚Â¡Ă‚ÂºĂ‚Â­n 14 quÄ‚Â¡Ă‚Â»Ă¢â‚¬Ëœc gia Ă„â€Ă¢â‚¬â€ 5 l-Ă‚Â©nh vÄ‚Â¡Ă‚Â»Ă‚Â±c = 70 combinations.

    MÄ‚Â¡Ă‚Â»Ă¢â‚¬â€i cell = sÄ‚Â¡Ă‚Â»Ă¢â‚¬Ëœ cĂ„â€Ă‚Â¢u hÄ‚Â¡Ă‚Â»Ă‚Âi cĂ„â€Ă‚Â³ thÄ‚Â¡Ă‚Â»Ă†â€™ sinh ra cho (country, domain).
    TÄ‚Â¡Ă‚Â»Ă¢â‚¬Â¢ng = 14 Ă„â€Ă¢â‚¬â€ 5 = 70 cells (-Ă¢â‚¬Ëœa l-Ă‚Â©nh vÄ‚Â¡Ă‚Â»Ă‚Â±c + toĂ„â€Ă‚Â n quÄ‚Â¡Ă‚Â»Ă¢â‚¬Ëœc gia).
    """
    from scp.core.real_learning_engine import (
        COUNTRIES,
        COUNTRY_DOMAIN_HINTS,
        DOMAINS,
        get_country_domain_matrix,
        get_total_combinations,
    )
    matrix = get_country_domain_matrix()
    total = get_total_combinations()
    return {
        "matrix_size": "14 quốc gia x 5 lĩnh vực = 70 ô",
        "total_country_specific_combinations": total,
        "countries_count": len(COUNTRIES),
        "domains_count": len(DOMAINS),
        "countries": COUNTRIES,
        "domains": DOMAINS,
        "matrix": matrix,
        "hints_count": sum(
            len(hints) for hints in COUNTRY_DOMAIN_HINTS.values()
        ),
        "summary": {
            "geography": "14 x 5 = 70 (theo quốc gia)",
            "history": "14 x 3 = 42 (theo quốc gia)",
            "chemistry": "14 x 3 = 42 (theo quốc gia) + 6 x 3 = 18 (theo hợp chất) = 60",
            "physics": "14 x 3 = 42 (theo quốc gia) + 3 (tổng quát) = 45",
            "biology": "14 x 3 = 42 (theo quốc gia) + 3 (tổng quát) = 45",
        },
    }


@router.post("/v104/learn/ollama-matrix")
@traced_request(_V104_ROUTES_LEDGER, require_write=True, action="v104_learn_ollama_matrix")
async def v104_learn_ollama_matrix(_admin: bool = Depends(verify_admin)):
    """V104.1 NEW: Run full matrix coverage (70 questions = 1 vĂ„â€Ă‚Â²ng ma trÄ‚Â¡Ă‚ÂºĂ‚Â­n -Ă¢â‚¬ËœÄ‚Â¡Ă‚ÂºĂ‚Â§y -Ă¢â‚¬ËœÄ‚Â¡Ă‚Â»Ă‚Â§).

    MÄ‚Â¡Ă‚Â»Ă¢â‚¬â€i (country, domain) -Ă¢â‚¬Ëœ- Ă‚Â°Ä‚Â¡Ă‚Â»Ă‚Â£c hÄ‚Â¡Ă‚Â»Ă‚Âi 1 lÄ‚Â¡Ă‚ÂºĂ‚Â§n → -Ă¢â‚¬ËœÄ‚Â¡Ă‚ÂºĂ‚Â£m bÄ‚Â¡Ă‚ÂºĂ‚Â£o coverage 14 Ă„â€Ă¢â‚¬â€ 5 = 70.
    """
    results = await _shared._real_learning.ollama_learning_cycle(count=70)
    return results


# ============================================================
# V104.2 NEW: Fast Learning (Parallel + Skip-Known + Compounding)
# ============================================================

@router.post("/v104/learn/fast")
@traced_request(_V104_ROUTES_LEDGER, require_write=True, action="v1042_learn_fast")
async def v1042_learn_fast(count: int = 50, _admin: bool = Depends(verify_admin)):
    """V104.2 NEW: Fast learning cycle │Ă¢â€Â¬Ă¢â‚¬Â parallel 10 concurrent Ollama + 5 Wiki.

    Default count=50. Skip cĂ„â€Ă‚Â¢u -Ă¢â‚¬ËœĂ„â€Ă‚Â£ cĂ„â€Ă‚Â³ trong KB. Sinh cĂ„â€Ă‚Â¢u hÄ‚Â¡Ă‚Â»Ă‚Âi Level-2 compounding.
    Adaptive interval 1-30 min tĂ„â€Ă‚Â¹y throughput.
    Returns: asked, skipped_known, verified, stored, compounding_L2, time_ms, adaptive_mode.
    """
    if not _shared._V1042_AVAILABLE or _shared._fast_learning is None:
        return {"error": "V104.2 FastLearningEngine not available"}
    results = await _shared._fast_learning.fast_learning_cycle(count=count)
    return results


@router.get("/v104/learn/fast/status", dependencies=[Depends(verify_admin)])  # RC-2 FIX: BFLA auth
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="v1042_learn_fast_status")
async def v1042_learn_fast_status():
    """V104.2 NEW: Fast Learning Engine stats.

    TrÄ‚Â¡Ă‚ÂºĂ‚Â£ vÄ‚Â¡Ă‚Â»Ă‚Â: cycles_completed, asked, skipped, verified, stored,
    compounding_L2/L3, avg_cycle_time_ms, fastest/slowest, adaptive_interval.
    """
    if not _shared._V1042_AVAILABLE or _shared._fast_learning is None:
        return {"error": "V104.2 FastLearningEngine not available"}
    return _shared._fast_learning.stats()


@router.get("/v104/learn/fast/benchmark", dependencies=[Depends(verify_admin)])  # RC-2 FIX: BFLA auth
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="v1042_learn_fast_benchmark")
async def v1042_learn_fast_benchmark():
    """V104.2 NEW: Benchmark V104.1 tuÄ‚Â¡Ă‚ÂºĂ‚Â§n tÄ‚Â¡Ă‚Â»Ă‚Â± vs V104.2 parallel.

    Returns: speedup factor, sequential_ms vs parallel_ms, concurrency.
    """
    if not _shared._V1042_AVAILABLE or _shared._fast_learning is None:
        return {"error": "V104.2 FastLearningEngine not available"}
    stats = _shared._fast_learning.stats()
    avg_ms = stats.get("avg_cycle_time_ms", 0)
    asked_avg = 50  # default count
    sequential_estimated_ms = asked_avg * 700  # 700ms per question sequential
    speedup = (sequential_estimated_ms / avg_ms) if avg_ms > 0 else 0
    return {
        # [STEP0-FIX 2026-09-02] Truth-in-metrics: the sequential side is a
        # constant-model estimate (50 q x 700 ms), NOT a measured benchmark.
        # Labeled so it can never be read as a measured speedup or used as a
        # performance gate (Bước 0.12: ESTIMATE != BENCHMARK).
        "measurement_kind": "ESTIMATE",
        "estimate_note": "sequential side = 50 questions x 700ms constant estimate; not measured - do not use as a performance gate",
        # [STEP0-FIX 2026-09-02] MEASURED side from real recorded cycle times
        # (bounded window of 100) - the honest half of this endpoint.
        "measured_parallel": {
            "kind": "MEASURED",
            "cycles_n": stats.get("cycle_times_n", 0),
            "p50_cycle_ms": stats.get("p50_cycle_ms"),
            "p95_cycle_ms": stats.get("p95_cycle_ms"),
        },
        "v104_1_sequential_ms_per_q": 700,
        "v104_2_parallel_avg_cycle_ms": avg_ms,
        "v104_2_questions_per_cycle": asked_avg,
        "v104_2_estimated_sequential_ms": sequential_estimated_ms,
        "speedup_factor": round(speedup, 1),
        "concurrency_llm": 10,
        "concurrency_wikipedia": 5,
        "adaptive_interval_current_s": stats.get("adaptive_interval_current", 300),
        "cycles_completed": stats.get("cycles_completed", 0),
        "facts_stored_total": stats.get("ollama_kb_facts_stored", 0),
    }


# ============================================================
# [2026-08-29] Free-API warehouse + TOP-1% systems learning loop.
# Kho dữ liệu free (public-apis catalog ~1.7k APIs) + vòng học từ GitHub /
# Wikipedia về thực hành của các hệ thống TOP 1%. Fail-closed, host
# allowlist cố định, chi tiết tại scp/core/top_systems_learning.py.
# ============================================================
from pydantic import Field as _TopSystemsField


class TopSystemsRunRequest(BaseModel):
    topics: list[str] | None = None
    per_source: int = _TopSystemsField(default=5, ge=1, le=10)


@router.get("/v104/learn/top-systems/status", dependencies=[Depends(verify_admin)])
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="top_systems_status")
async def v104_top_systems_status():
    import os as _os

    from scp.core.top_systems_learning import get_learner
    from scp.data_sources.free_api_catalog import get_catalog

    learner = get_learner(data_dir=_os.environ.get("SCP_DATA_DIR", "data"))
    return {
        "learner": learner.stats(),
        "catalog": get_catalog(data_dir=_os.environ.get("SCP_DATA_DIR", "data")).status(),
    }


@router.post("/v104/learn/top-systems", dependencies=[Depends(verify_admin)])
@traced_request(_V104_ROUTES_LEDGER, require_write=True, action="top_systems_learn")
async def v104_learn_top_systems(payload: TopSystemsRunRequest | None = None, _admin: bool = Depends(verify_admin)):
    """Run one bounded learning cycle: collect top-tier systems knowledge from
    free sources (GitHub + Wikipedia) into the durable knowledge ledger."""
    import os as _os

    from scp.core.top_systems_learning import get_learner

    learner = get_learner(data_dir=_os.environ.get("SCP_DATA_DIR", "data"))
    topics = payload.topics if payload else None
    per_source = payload.per_source if payload else 5
    result = await asyncio.to_thread(learner.learn_all, topics, per_source)
    return JSONResponse(result, status_code=200 if result.get("ok") else 503)


@router.get("/v104/learn/top-systems/advise", dependencies=[Depends(verify_admin)])
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="top_systems_advise")
async def v104_top_systems_advise(query: str, limit: int = 10, _admin: bool = Depends(verify_admin)):
    """Consult the collected TOP-1% knowledge (used by WHY/autofix + humans)."""
    import os as _os

    from scp.core.top_systems_learning import get_learner

    learner = get_learner(data_dir=_os.environ.get("SCP_DATA_DIR", "data"))
    return {"query": query[:200], "records": learner.advise(query, limit=limit)}


@router.get("/v104/free-apis/search", dependencies=[Depends(verify_admin)])
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="free_apis_search")
async def v104_free_apis_search(
    query: str = "",
    category: str | None = None,
    auth: str | None = None,
    limit: int = 25,
    _admin: bool = Depends(verify_admin),
):
    """Search the free-API catalog (auth="No" → APIs usable without a key)."""
    import os as _os

    from scp.data_sources.free_api_catalog import get_catalog

    catalog = get_catalog(data_dir=_os.environ.get("SCP_DATA_DIR", "data"))
    if not catalog.entries():
        await asyncio.to_thread(catalog.refresh)
    results = await asyncio.to_thread(catalog.search, query, category, auth, limit)
    return {"count": len(results), "results": results}


@router.get("/v104/doubt/status", dependencies=[Depends(verify_admin)])
@traced_request(_V104_ROUTES_LEDGER, require_write=False, action="doubt_status")
async def v104_doubt_status():
    """[MẢNH #11] Cronjob of Doubt — trạng thái vòng nghi ngờ tự kích hoạt."""
    import os as _os

    from scp.core.doubt_cron import get_doubt_cron

    cron = get_doubt_cron(data_dir=_os.environ.get("SCP_DATA_DIR", "data"))
    return {
        "interval_seconds": cron.interval,
        "running": bool(cron._thread and cron._thread.is_alive()),
        "last_report": cron.last_report,
    }


@router.post("/v104/doubt/run", dependencies=[Depends(verify_admin)])
@traced_request(_V104_ROUTES_LEDGER, require_write=True, action="doubt_run")
async def v104_doubt_run(_admin: bool = Depends(verify_admin)):
    """Chạy ngay 1 vòng nghi ngờ (fitness drift + kernel integrity + backlog + WHY anomaly)."""
    import os as _os

    from scp.core.doubt_cron import run_doubt_cycle

    report = await asyncio.to_thread(run_doubt_cycle, _os.environ.get("SCP_DATA_DIR", "data"))
    return JSONResponse(report, status_code=200 if report["verdict"] == "CLEAN" else 503)

@router.post("/v104/learn/consolidate", dependencies=[Depends(verify_admin)])
@traced_request(_V104_ROUTES_LEDGER, require_write=True, action="consolidate_knowledge")
async def consolidate_knowledge():
    """Trigger knowledge consolidator (Wave 2).

    [M13-FIX] This handler used to call the nonexistent
    ``KnowledgeConsolidator.consolidate_unverified()`` -> AttributeError ->
    HTTP 500 on EVERY call (probe-proven at runtime during the M13 closure).
    The consolidator is a documented minimal stub
    (scp/consolidator/consolidator.py: ``consolidate()`` is a passthrough and
    no persistent unverified-fact store is wired) and the arbiter below is
    per-request in-memory, so this endpoint consolidates nothing durable. The
    response now says so explicitly instead of implying a real consolidation.
    """
    from scp.consolidator.consolidator import KnowledgeConsolidator
    from scp.meta.knowledge_arbiter import KnowledgeArbiter
    arbiter = KnowledgeArbiter()
    consolidator = KnowledgeConsolidator(arbiter)
    result = consolidator.consolidate([])  # [M13-FIX] real API; was: nonexistent consolidate_unverified()
    return {
        "status": "ok_stub_noop",
        "result": result,
        "consolidator_mode": "minimal_stub_passthrough",
        "arbiter_stats": arbiter.stats(),
        "note": (
            "KnowledgeConsolidator is a documented minimal stub: consolidate() "
            "is a passthrough and no persistent unverified-fact store is wired. "
            "This endpoint does not persist or transform knowledge."
        ),
    }
