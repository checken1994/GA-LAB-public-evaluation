# SCP CIRCUIT: M02 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M02-closure.json)
# Auto-extracted from api_server.py
from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import os
import time
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from scp.api_server_parts.helpers import AskRequest, AskResponse, _extract_v98_context, _safe_fetch_url, get_judge
from scp.core.request_run_ledger import stage_request
from scp.meta.simple_explainer import SimpleExplainer
from scp.security.image_voice_detector import ImageJailbreakDetector, VoiceJailbreakDetector
from scp.security.multi_turn_tracker import MultiTurnTracker
from scp.web_control.internet_search import InternetSearch

logger = logging.getLogger(__name__)

_multi_turn_tracker = MultiTurnTracker()
_simple_explainer = SimpleExplainer()
# [W1-c1 2026-10-02] Fact-check là nhánh phụ trợ của /ask: phải được AWAIT
# (không còn fire-and-forget create_task sống sót sau finalize) nhưng có bound
# để không kéo handler quá lâu. 10.0 khớp timeout per-request nội bộ của
# StreamingFactChecker (scp/core/streaming_factcheck.py safe_urlopen timeout=10).
_FACTCHECK_AWAIT_TIMEOUT_S = 10.0
_image_detector = ImageJailbreakDetector()
_voice_detector = VoiceJailbreakDetector()
from scp.api_server_parts._async_fact_check import _async_fact_check


def _history_evidence_record(verdict: str, session_id: str, question: str) -> Any:
    """[HIST-LEDGER-CONTRACT 2026-09-26] Map a /ask judge verdict onto the
    history evidence ledger contract (scp/history/evidence_ledger.py).

    TẠI SAO: the old hook wrote ``kind='verdict_rendered'`` with
    ``status=v.verdict`` ('PASS'/'FAIL'/...), but ``validate_record`` only
    accepts ``status='verified'`` records of kind in {official_document,
    independent_runtime, independent_adjudication} — so append_record raised
    EvidenceContractError on EVERY ask ("history hook failed" WARNING) and the
    ledger file was never created.

    Contract mapping (fail-closed honesty — no claim that would fail
    validation):
      * judge PASS = the judge independently adjudicated the question → one
        ``verified`` record of kind ``independent_adjudication``;
      * FAIL / UNKNOWN / PARTIAL / FLAGGED / withheld runs are NOT verified →
        no record at all (the ledger has no rejected/abstain status; writing
        an invalid record is what produced the per-ask WARNING).
    Returns the EvidenceRecord, or None when nothing may enter the ledger.
    """
    if str(verdict or "") != "PASS":
        return None
    if not str(question or "").strip():
        return None
    from scp.history.evidence_ledger import EvidenceRecord
    return EvidenceRecord(
        subject_id=str(session_id or "") or "session_unknown",
        lineage="ask_endpoint",
        kind="independent_adjudication",
        locator="ask_impl",
        observed_claim=str(question)[:200],
        independent_of="",
        status="verified",
    )



def _extend_ask_response_degradation_fields() -> None:
    """[AUDIT-20260909 MACH2-BUG2] Declare degradation-observability fields on
    the shared AskResponse model.

    TẠI SAO: khi image/voice fetch hoặc OCR/Whisper scan lỗi, pipeline cũ nuốt
    lỗi ở mức logger.debug rồi vẫn trả answer bình thường — multimodal jailbreak
    KHÔNG được scan nhưng client không có cách nào biết. helpers.py không thuộc
    phạm vi file được sửa của task này, nên các field bổ sung được khai báo động
    trên cùng một model class (mặc định None → JSON additive, không phá contract).
    """
    from pydantic.fields import FieldInfo

    _new_fields = {
        "detector_degraded": (bool | None, None),
        "detector_note": (str | None, None),
        "fact_check_degraded": (bool | None, None),
        # [AUDIT-20260909 MACH2-R2-2] fact_check_note từng là biến chết (gán
        # ở branch lỗi nhưng không bao giờ vào response). Note chứa loại
        # exception (`fact_check_error:<Type>`) — chẩn đoán hữu ích đi kèm
        # fact_check_degraded, cùng pattern với detector_note → expose thay vì xoá.
        "fact_check_note": (str | None, None),
        # Milestone 2: Autonomous Evidence Retrieval & Fact Separation (R2)
        "verified_facts": (list[dict[str, Any]], FieldInfo(default_factory=list, annotation=list[dict[str, Any]])),
        "llm_reasoning": (str, ""),
        "confidence_badge": (dict[str, Any] | None, None),
        "web_fallback_used": (bool, False),
        "web_fallback": (dict[str, Any] | None, None),
    }
    _changed = False
    for _name, (_ann, _default) in _new_fields.items():
        if _name not in AskResponse.model_fields:
            if isinstance(_default, FieldInfo):
                AskResponse.model_fields[_name] = _default
            else:
                AskResponse.model_fields[_name] = FieldInfo(default=_default, annotation=_ann)
            _changed = True
    if _changed:
        AskResponse.model_rebuild(force=True)


_extend_ask_response_degradation_fields()


async def _ask_impl(req: AskRequest, request: Request):
    """Main endpoint — question → V98 pipeline → verdict.

    Pipeline:
      1.  MemoryPoisoningGuard + AttackPatternMemory + ThreatDetector
      2.  Route → SLM predict → RealityJudge
      3.  FalsificationEngine + ErrorStore + Governance
      4.  AttackPolicy + CounterResponse + Canary + AttackPatternMemory.record_bypass
    """
    t0 = time.time()
    judge = get_judge()
    stage_request(request, 'judge_ready')
    v98_context = _extract_v98_context(request)
    _web_fallback_used = False
    _web_fallback: dict = {}
    v98_context['body'] = req.question
    if req.session_id:
        v98_context['session_id'] = req.session_id
    _history = []
    for _turn in (req.conversation_history or [])[-8:]:
        if not isinstance(_turn, dict):
            continue
        _role = str(_turn.get('role', 'user'))[:16]
        _content = str(_turn.get('content', ''))[:500].strip()
        if _content and _role in {'user', 'assistant', 'scp'}:
            _norm_role = 'assistant' if _role in {'assistant', 'scp'} else 'user'
            _history.append({'role': _norm_role, 'content': _content})
    if req.session_id and not _history:
        try:
            from scp.core.chat_memory import get_chat_memory_store
            # [ASK-BLOCK-FIX 2026-09-28] ChatMemoryStore.load re-reads and
            # JSON-parses the entire chat_memory.jsonl under an OS file-lock —
            # sync I/O blocking the event loop; offload to a worker thread.
            _mem_store_preload = get_chat_memory_store()
            _loaded = await asyncio.to_thread(_mem_store_preload.load, req.session_id, limit=8)
            for _rec in _loaded:
                _r = str(_rec.get('role', 'user'))
                _c = str(_rec.get('content', ''))[:500].strip()
                if _c and _r in {'user', 'assistant', 'scp'}:
                    _norm_r = 'assistant' if _r in {'assistant', 'scp'} else 'user'
                    _history.append({'role': _norm_r, 'content': _c})
        except Exception as _mem_ld_exc:
            logger.warning("[_ask_impl] Failed to load chat memory: %s", _mem_ld_exc, exc_info=True)
    if _history:
        v98_context['conversation_history'] = _history
    try:
        from scp.api.cognitive_router import run_pre_judge_hooks
        v98_context = await run_pre_judge_hooks(req.question, v98_context)
    except Exception as e:
        logger.warning(f'Cognitive router failed: {e}', exc_info=True)
    # [AUDIT-FIX 2026-09-24] Resource-quota slot bookkeeping. check_request
    # returns None ONLY when the request was admitted, which is exactly
    # when one global slot was taken. The slot must be returned on EVERY
    # exit path (finally below) or leaked slots 429 the whole process.
    _dos_slot_taken = False
    if hasattr(judge, 'dos_protection') and judge.dos_protection:
        try:
            client_ip = request.client.host if request.client else 'unknown'
            dos_alert = judge.dos_protection.check_request(client_ip)
            _dos_slot_taken = dos_alert is None
            action = getattr(dos_alert, 'action_taken', '') if dos_alert else ''
            should_block = action in ('block', 'throttle') or (isinstance(dos_alert, dict) and dos_alert.get('should_block'))
            if should_block:
                status_code = int(getattr(dos_alert, 'status_code', 0) or 429)
                headers = dict(getattr(dos_alert, 'recommended_headers', {}) or {})
                return JSONResponse({'error': {'message': 'Rate limit exceeded', 'type': 'rate_limit_error'}}, status_code=status_code, headers=headers)
        except Exception as e:
            logger.debug(f'[V104.17] DoS check error: {e}', exc_info=True)
    try:
        _multimodal_block = False
        _img_bytes = None
        # [AUDIT-20260909 MACH2-BUG2a] Degradation observability: khi fetch/scan lỗi
        # hoặc OCR/Whisper unavailable, request vẫn chạy nhưng response phải mang
        # dấu hiệu quan sát được (detector_degraded + detector_note).
        _detector_degraded = False
        _detector_notes: list[str] = []
        _DETECT_TIMEOUT_SECONDS = 10.0

        # [SCP-A07 FIX 2026-09-25] TẠI SAO bỏ nhánh "local URL → degraded":
        # _safe_fetch_url CHẲNG BAO GIỜ connect tới một URL local — loopback/private
        # IP bị chặn ở bước validate IP (trước mọi network I/O) và lỗi đó giờ là
        # FetchBlockedError (policy rejection). Nhánh cũ biến mọi SSRF probe
        # loopback (image_url/voice_url = http://127.0.0.1/...) thành "degraded +
        # tiếp tục pipeline" (fail-open cho đúng class SSRF nguy hiểm nhất).
        # Hợp đồng mới: policy rejection (FetchBlockedError và EgressDeniedError)
        # → 400 fail-closed (acceptance SCP-A07); fetch lỗi THẬT sau khi policy
        # cho phép (DNS, refused, HTTP 4xx/5xx — plain ValueError) → degraded
        # quan sát được (giữ nguyên intent MACH2-BUG2a).
        from scp.core.url_fetcher import FetchBlockedError as _FetchBlockedError
        from scp.policy.egress import EgressDeniedError as _EgressDeniedError

        if req.image_data:
            try:
                _raw_image = req.image_data
                if ',' in _raw_image and _raw_image.lower().startswith('data:'):
                    _raw_image = _raw_image.split(',', 1)[1]
                _img_bytes = base64.b64decode(_raw_image, validate=True)
                if not _img_bytes or len(_img_bytes) > 6000000:
                    raise ValueError('image_too_large_or_empty')
            except (binascii.Error, ValueError):
                raise HTTPException(status_code=400, detail='Invalid or oversized image_data') from None
        if req.image_url and _img_bytes is None:
            try:
                _img_bytes = await asyncio.to_thread(_safe_fetch_url, req.image_url)
            except (_FetchBlockedError, _EgressDeniedError):
                # [SCP-A07 FIX] Policy/SSRF/egress rejection — must terminate the
                # request (400) instead of degrading. Loopback probes are ALWAYS
                # caught here: _safe_fetch_url rejects private/loopback IPs before
                # any network I/O, so a "local unreachable" fetch cannot exist.
                logger.warning('[V104.45 #CP][A07] /ask image_url blocked by fetch policy (SSRF fail-closed)')
                raise HTTPException(status_code=400, detail='Invalid or disallowed image_url') from None
            except ValueError as e:
                # Genuine fetch failure AFTER policy allowed the target
                # (DNS/res refusal/HTTP error) — degrade with observability
                # (MACH2-BUG2a contract), do not terminate the request.
                logger.warning(f'[V104.45 #CP] Image fetch failed: {e}')
                _img_bytes = None
                _detector_degraded = True
                _detector_notes.append(f'image_fetch_failed:{type(e).__name__}')
            except Exception as e:
                logger.warning(f'[V104.45 #CP] Image fetch error: {e}', exc_info=True)
                _img_bytes = None
                _detector_degraded = True
                _detector_notes.append(f'image_fetch_failed:{type(e).__name__}')
            if _img_bytes:
                try:
                    _img_result = await asyncio.wait_for(asyncio.to_thread(_image_detector.detect, image_bytes=_img_bytes), timeout=_DETECT_TIMEOUT_SECONDS)
                    if _img_result and _img_result.jailbreak_detected:
                        logger.warning('[V104.45 #CP] Image jailbreak detected on /ask')
                        _multimodal_block = True
                    elif _img_result and _img_result.method == 'ocr_unavailable':
                        logger.warning('[V104.45 #CP] Image OCR unavailable — jailbreak scan degraded, request continues')
                        _detector_degraded = True
                        _detector_notes.append('image_ocr_unavailable')
                except asyncio.TimeoutError:
                    logger.warning(f'[V104.45 #CP] Image detect exceeded {_DETECT_TIMEOUT_SECONDS:.0f}s bound — scan not completed')
                    _detector_degraded = True
                    _detector_notes.append('image_detect_timeout')
                except Exception as e:
                    logger.warning(f'[V104.45 #CP] Image detect error: {e}', exc_info=True)
                    _detector_degraded = True
                    _detector_notes.append(f'image_detect_error:{type(e).__name__}')
        _voice_transcription = ""
        if req.voice_url:
            try:
                _voice_bytes = await asyncio.to_thread(_safe_fetch_url, req.voice_url)
            except (_FetchBlockedError, _EgressDeniedError):
                # [SCP-A07 FIX] Policy/SSRF/egress rejection — same fail-closed
                # coupling as the image path (see comment above).
                logger.warning('[V104.45 #CP][A07] /ask voice_url blocked by fetch policy (SSRF fail-closed)')
                raise HTTPException(status_code=400, detail='Invalid or disallowed voice_url') from None
            except ValueError as e:
                logger.warning(f'[V104.45 #CP] Voice fetch failed: {e}')
                _voice_bytes = None
                _detector_degraded = True
                _detector_notes.append(f'voice_fetch_failed:{type(e).__name__}')
            except Exception as e:
                logger.warning(f'[V104.45 #CP] Voice fetch error: {e}', exc_info=True)
                _voice_bytes = None
                _detector_degraded = True
                _detector_notes.append(f'voice_fetch_failed:{type(e).__name__}')
            if _voice_bytes:
                try:
                    _voice_result = await asyncio.wait_for(asyncio.to_thread(_voice_detector.detect, audio_bytes=_voice_bytes), timeout=_DETECT_TIMEOUT_SECONDS)
                    if _voice_result and _voice_result.jailbreak_detected:
                        logger.warning('[V104.45 #CP] Voice jailbreak detected on /ask')
                        _multimodal_block = True
                    elif _voice_result and _voice_result.method == 'whisper_unavailable':
                        logger.warning('[V104.45 #CP] Voice whisper unavailable — jailbreak scan degraded, request continues')
                        _detector_degraded = True
                        _detector_notes.append('voice_whisper_unavailable')
                    else:
                        from scp.capabilities.voice import VoiceHandler
                        _vh = VoiceHandler()
                        # [AUDIT-20260909 MACH2-R2-1] Whisper transcribe chạy local
                        # qua to_thread nhưng KHÔNG có bound → có thể treo request
                        # vô hạn. Bọc wait_for: default 30s, env override
                        # SCP_TRANSCRIBE_TIMEOUT_SEC (parse an toàn — env rác/≤0/inf
                        # → fallback 30s). Inline parse vì hàm này bị rebind vào
                        # globals của api_server.py (helper module-level sẽ không
                        # nhìn thấy qua rebind).
                        _transcribe_timeout = 30.0
                        try:
                            _env_timeout = float(os.environ.get('SCP_TRANSCRIBE_TIMEOUT_SEC', ''))
                            if _env_timeout > 0 and _env_timeout != float('inf'):
                                _transcribe_timeout = _env_timeout
                        except (TypeError, ValueError):
                            logger.debug('_ask_impl: TypeError, ValueError ignored', exc_info=True)
                        try:
                            _voice_transcription = await asyncio.wait_for(asyncio.to_thread(_vh.transcribe, _voice_bytes), timeout=_transcribe_timeout)
                        except asyncio.TimeoutError:
                            logger.warning(f'[V104.45 #CP] Voice transcribe exceeded {_transcribe_timeout:.0f}s bound — transcription not completed')
                            _detector_degraded = True
                            _detector_notes.append('transcribe_timeout')
                        if _voice_transcription:
                            req.question += f"\n[Voice Transcription]: {_voice_transcription}"
                except asyncio.TimeoutError:
                    logger.warning(f'[V104.45 #CP] Voice detect exceeded {_DETECT_TIMEOUT_SECONDS:.0f}s bound — scan not completed')
                    _detector_degraded = True
                    _detector_notes.append('voice_detect_timeout')
                except Exception as e:
                    logger.warning(f'[V104.45 #CP] Voice detect error: {e}', exc_info=True)
                    _detector_degraded = True
                    _detector_notes.append(f'voice_detect_error:{type(e).__name__}')
        if _multimodal_block:
            return AskResponse(verdict='FAIL', final_answer='[SCP: Answer withheld — multimodal jailbreak detected]', confidence=0.0, domain='security', elapsed_ms=0, session_id=v98_context['session_id'])
        _history = []
        if req.conversation_history:
            _history = list(req.conversation_history)
        if not _history and req.session_id:
            try:
                from scp.core.chat_memory import get_chat_memory_store
                _mem_store = get_chat_memory_store()
                # [ASK-BLOCK-FIX 2026-09-28] full-file read under file-lock —
                # offload to worker thread (see note at first load site).
                _loaded = await asyncio.to_thread(_mem_store.load, req.session_id, limit=8)
                if _loaded:
                    _history = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in _loaded]
            except Exception as _mem_load_err:
                logger.warning(f"[CHATBOT] Failed to load chat memory for session {req.session_id}: {_mem_load_err}", exc_info=True)

        from scp.runtime.question_router import LANE_CHATBOT, LANE_FACTUAL, LANE_SECURITY, route_question
        _route_decision = route_question(req.question)
        _is_chatbot_lane = (_route_decision.lane == LANE_CHATBOT)

        _ai_answer = req.ai_answer
        if not _ai_answer or not _ai_answer.strip():
            try:
                from scp.llm_gateway import get_gateway
                from scp.runtime.question_router import detect_language

                _lang = detect_language(req.question)
                if _lang == "vi":
                    _sys_prompt = (
                        "Bạn là SCP — một trợ lý AI thông minh. Giao tiếp tự nhiên, thân thiện và chính xác bằng tiếng Việt. "
                        "Trả lời ngắn gọn, rõ ràng, trung thực và hỗ trợ thảo luận mở. Chỉ trả lời câu hỏi HIỆN TẠI ở cuối yêu cầu. "
                        "Không tiếp tục chủ đề cũ nếu câu hỏi mới đổi chủ đề. Nếu thiếu dữ liệu, nói rõ chưa đủ dữ liệu thay vì đoán."
                    )
                    _ctx_header = "Lịch sử gần đây (chỉ để tham khảo):\n"
                else:
                    _sys_prompt = (
                        "You are SCP — an intelligent AI assistant. Respond naturally, fluently, and accurately in English. "
                        "Provide clear, honest, and helpful explanations. Answer the CURRENT question at the end of the prompt. "
                        "Do not continue previous topics if the topic has changed. State clearly if data is insufficient rather than guessing."
                    )
                    _ctx_header = "Recent conversation history (for reference only):\n"

                _llm_context = (_ctx_header + '\n'.join(f"{t['role']}: {t['content']}" for t in _history)) if _history else ''
                _gateway = get_gateway()
                _generated_answer, _provider = await _gateway.chat(req.question,
                    context=_llm_context,
                    system_prompt=_sys_prompt,
                    task='chat',
                )
                if _generated_answer:
                    _ai_answer = _generated_answer
                    logger.info(f'[CHATBOT] LLM ({_provider}) generated answer: {_generated_answer[:80]}...')
            except Exception as _generation_error:
                logger.warning(f'[CHATBOT] LLM call failed: {_generation_error}', exc_info=True)
                if not _is_chatbot_lane and os.environ.get('SCP_WEB_FALLBACK', '1') == '1':
                    try:
                        _web_timeout = min(float(os.environ.get('SCP_WEB_FALLBACK_TIMEOUT', '8')), 12.0)
                        _web_search = InternetSearch(timeout=min(_web_timeout / 2.0, 4.0))
                        _web_fallback = await asyncio.wait_for(_web_search.search(req.question, max_results=6), timeout=_web_timeout)
                        _web_fallback_used = bool(_web_fallback.get('success'))
                        _web_fallback['trigger'] = 'llm_timeout_or_error'
                        _web_fallback['llm_error'] = str(_generation_error)[:240]
                        if _web_fallback_used:
                            _snippets = []
                            for _item in _web_fallback.get('results', [])[:6]:
                                _title = str(_item.get('title', '')).strip()
                                _snippet = str(_item.get('snippet', '')).strip()
                                _url = str(_item.get('url', '')).strip()
                                _snippets.append(f'- {_title}: {_snippet} ({_url})')
                            _ai_answer = '[SCP public-web evidence; untrusted, requires verification]\n' + '\n'.join(_snippets)
                            v98_context['web_fallback'] = _web_fallback
                        else:
                            logger.warning('[CHATBOT] Public web fallback returned no result: %s', _web_fallback.get('errors'))
                    except Exception as _web_err:
                        _web_fallback = {'success': False, 'method': 'public-search', 'error': str(_web_err)[:240]}
                        logger.warning('[CHATBOT] Public web fallback failed: %s', _web_err, exc_info=True)
        if not _ai_answer:
            if req.contexts:
                for _c in req.contexts:
                    if _c and str(_c).strip():
                        _ai_answer = str(_c).strip()
                        break
            elif getattr(req, 'retrieved_context', None) and str(req.retrieved_context).strip():
                _ai_answer = str(req.retrieved_context).strip()

        # Milestone 2: Autonomous Evidence Retrieval (KB -> Safe Web Search with Quarantine)
        _retrieval_res: dict[str, Any] = {}
        _has_provided_evidence = bool(req.contexts or (getattr(req, 'retrieved_context', None) and str(req.retrieved_context).strip()))
        try:
            if _route_decision.lane == LANE_FACTUAL and (not _has_provided_evidence or req.confidence < 0.7):
                from scp.knowledge.domain_knowledge import AutonomousEvidenceRetriever
                _retriever = AutonomousEvidenceRetriever()
                _retrieval_res = await _retriever.retrieve(
                    question=req.question,
                    current_confidence=req.confidence,
                    domain=getattr(req, "domain", "general"),
                    allow_web=bool(os.environ.get('SCP_WEB_FALLBACK', '1') == '1'),
                )
                if _retrieval_res.get("retrieval_triggered"):
                    if _retrieval_res.get("web_search_hits") and not _web_fallback_used:
                        _web_fallback_used = True
                        _web_fallback = {
                            "success": True,
                            "results": _retrieval_res.get("web_search_hits", []),
                            "method": "public-search",
                        }
                        v98_context["web_fallback"] = _web_fallback
                    if not _ai_answer and _retrieval_res.get("clean_evidence_snippets"):
                        _ai_answer = "\n".join(_retrieval_res["clean_evidence_snippets"][:3])
        except Exception as _ar_err:
            logger.warning("[_ask_impl] Autonomous retrieval error: %s", _ar_err, exc_info=True)
        _q_lower = req.question.lower() if req.question else ''
        _FACT_CHECK_KEYWORDS = ('true or false', 'fact check', 'is it true', 'fact-check', 'có thật', 'đúng không', 'có thật không', 'kiểm chứng', 'real or fake', 'verify this claim')
        # [AUDIT-20260909 MACH2-BUG2b] chỉ bật khi claim tồn tại (keyword match) và
        # việc verify LỖI — không phải khi câu hỏi không có claim cần kiểm chứng.
        _fact_check_degraded = False
        _fact_check_note = ''
        if any(kw in _q_lower for kw in _FACT_CHECK_KEYWORDS):
            try:
                from scp.core.multi_source_verifier import AsyncMultiSourceVerifier
                from scp.data_sources import get_registry
                _fc_sources = []
                try:
                    _registry = get_registry()
                    _candidates = []
                    try:
                        _candidates = _registry.get_sources_for_intent('fact_check') or []
                    except Exception:
                        logger.warning('_ask_impl: Exception not handled', exc_info=True)
                        _candidates = list(getattr(_registry, '_sources', {}).values())
                    for _src in _candidates:
                        try:
                            if _src.can_handle('fact_check'):
                                _fc_sources.append(_src)
                        except Exception:
                            logger.warning('_ask_impl: Exception not handled', exc_info=True)
                            continue
                except Exception as _reg_err:
                    logger.debug(f'[OPT-22] registry lookup failed: {_reg_err}', exc_info=True)
                async_verifier = AsyncMultiSourceVerifier()
                fact_result = await async_verifier.verify_async(req.question, sources=_fc_sources or None)
                _extra_verified = 0
                _extra_contradicted = 0
                for _raw in fact_result.get('results', []) or []:
                    try:
                        _meta = _raw.get('metadata', {}) if isinstance(_raw, dict) else {}
                        _verdict = str(_meta.get('consensus', '')).upper() if _meta else ''
                        if _verdict == 'FALSE':
                            _extra_contradicted += 1
                        elif _verdict == 'TRUE':
                            _extra_verified += 1
                    except Exception:
                        logger.warning('_ask_impl: Exception not handled', exc_info=True)
                        continue
                if _extra_verified or _extra_contradicted:
                    fact_result['verified'] = fact_result.get('verified', 0) + _extra_verified
                    fact_result['contradicted'] = fact_result.get('contradicted', 0) + _extra_contradicted
                    if fact_result['contradicted'] > fact_result['verified']:
                        fact_result['consensus'] = 'contradicted'
                    elif fact_result['verified'] > fact_result['contradicted']:
                        fact_result['consensus'] = 'verified'
                if fact_result.get('consensus') == 'contradicted':
                    logger.info(f"[OPT-22] Pre-judge fact check: claim contradicted by {fact_result.get('contradicted', 0)} sources (sources_checked={fact_result.get('sources_checked', 0)})")
                    v98_context['fact_check_hint'] = fact_result
                elif fact_result.get('consensus') == 'verified':
                    logger.info(f"[OPT-22] Pre-judge fact check: claim verified by {fact_result.get('verified', 0)} sources (sources_checked={fact_result.get('sources_checked', 0)})")
                    v98_context['fact_check_hint'] = fact_result
            except Exception as e:
                # [AUDIT-20260909 MACH2-BUG2b] Pre-judge fact-check FAILED (claim đã
                # có — keyword match) nên hint bị mất: phải quan sát được, không nuốt.
                _fact_check_degraded = True
                _fact_check_note = f'fact_check_error:{type(e).__name__}'
                logger.warning(f'[OPT-22] async fact check failed: {e}', exc_info=True)
        stage_request(request, 'verifier_started')
        from scp.core.top_systems_learning import inspect_untrusted as _sf_inspect
        _raw_evidence = [str(c) for c in req.contexts or [] if str(c).strip()] + ([str(req.retrieved_context).strip()] if str(getattr(req, 'retrieved_context', '') or '').strip() else [])
        if _retrieval_res and _retrieval_res.get("clean_evidence_snippets"):
            _raw_evidence.extend(_retrieval_res["clean_evidence_snippets"])
        _clean_evidence = []
        _injection_blocked = 0
        for _ev in _raw_evidence:
            _quarantined, _reason = _sf_inspect(_ev)
            if _quarantined:
                _injection_blocked += 1
                logger.warning('[SEMANTIC-FIREWALL] Blocked injection in evidence: %s', _reason)
                continue
            _clean_evidence.append(_ev)
        if _injection_blocked:
            v98_context['semantic_firewall'] = {'blocked': _injection_blocked, 'total': len(_raw_evidence)}
        _evidence_context = ' '.join(_clean_evidence) + ((' ' + _ai_answer) if _ai_answer else '')
        if hasattr(judge, 'judge_with_react_fallback'):
            v = await judge.judge_with_react_fallback(question=req.question, ai_answer=_ai_answer, cycle_count=0, source=req.source, context=_evidence_context, v98_context=v98_context)
        else:
            v = await asyncio.to_thread(judge.judge, question=req.question, ai_answer=_ai_answer, cycle_count=0, source=req.source, context=_evidence_context, v98_context=v98_context)

        class DotDict(dict):

            def __getattr__(self, name):
                return self.get(name, None)

            def __setattr__(self, name, value):
                self[name] = value
        if isinstance(v, dict):
            if v.get('evidence') is None:
                v['evidence'] = {}
            if v.get('slm_responses') is None:
                v['slm_responses'] = []
            if v.get('confidence') is None:
                v['confidence'] = 0.0
            if v.get('final_answer') is None:
                v['final_answer'] = v.get('evidence', {}).get('final_answer', '')
            v = DotDict(v)
        stage_request(request, 'verifier_completed', verdict=getattr(v, 'verdict', 'FAIL'), governance_decision=getattr(v, 'evidence', {}).get('governance_decision', ''))
        if hasattr(judge, 'dos_protection') and judge.dos_protection:
            try:
                judge.dos_protection.record_verdict(getattr(v, 'verdict', 'FAIL'))
                _dos_slot_taken = False  # verdict recorded — record_verdict released the slot
            except Exception as e:
                logger.debug(f'[V104.41 #AC] DoS record_verdict error: {e}', exc_info=True)
    finally:
        if _dos_slot_taken and hasattr(judge, 'dos_protection') and judge.dos_protection:
            # Early exit (HTTP 400/403 return or exception) before a verdict
            # was produced: return the quota slot, leave the circuit alone.
            try:
                judge.dos_protection.release_slot()
            except Exception as _dos_release_err:
                logger.debug(f'[V104.17] DoS slot release error: {_dos_release_err}', exc_info=True)
    elapsed_ms = (time.time() - t0) * 1000
    if hasattr(judge, 'response_monitor') and judge.response_monitor:
        try:
            judge.response_monitor.observe(prompt=req.question, response=v.final_answer or '', latency_ms=elapsed_ms)
        except Exception as e:
            logger.debug(f'[V104.41 #AD] ResponseMonitor observe error: {e}', exc_info=True)
    slm_trace = []
    for r in v.slm_responses:
        slm_trace.append({'domain': r.get('domain', '?'), 'slm_name': r.get('slm_name', r.get('domain', '?')), 'answer': str(r.get('answer', ''))[:200], 'confidence': r.get('confidence', 0), 'source': r.get('evidence', {}).get('source', '?') if isinstance(r.get('evidence'), dict) else '?', 'evidence': r.get('evidence', {}) if isinstance(r.get('evidence'), dict) else {}, 'processing_time_ms': r.get('processing_time', 0)})
    phase_timings = v.evidence.get('v100_phase_timings', {})
    mt_result = None
    _mt_session = req.session_id or v98_context.get('session_id', '')
    if _mt_session:
        mt_result = _multi_turn_tracker.track(_mt_session, req.question, v.verdict)
        if mt_result.suspicious:
            if v.verdict in ('PASS', 'FAIL', 'UNKNOWN', 'PARTIAL'):
                v.verdict = 'FLAGGED'
                v.confidence = (v.confidence or 0.0) * 0.5  # [S-L7 fix] None-guard
                if v.reasoning:
                    v.reasoning += f' [V104 Multi-turn: {mt_result.pattern_type}]'
            logger.warning(f'V104 Multi-turn attack: session={_mt_session}, pattern={mt_result.pattern_type}, reason={mt_result.reason}')
            v98_context['v104_multi_turn'] = mt_result.__dict__
    has_attack = bool(v98_context.get('v99_vietnamese_attack'))
    has_bypass = bool(v.evidence.get('v100_bypass_detected'))
    has_human_review = bool(v.evidence.get('v102_human_review_pending'))
    source_count = len([r for r in v.slm_responses if r.get('answer')])
    _simple_explainer.explain(verdict=v.verdict, confidence=v.confidence, domain=v.domain or '' or '' or '', sources=source_count, has_attack=has_attack, has_bypass=has_bypass, has_human_review=has_human_review, lineage_overlap=0.0, reliability_factor=v.evidence.get('v102_reliability_factor', 1.0))
    _api_final_answer = v.final_answer
    _gov_decision = v.evidence.get('governance_decision', '')
    _api_slm_responses = [{k: str(v2)[:200] for k, v2 in r.items()} for r in v.slm_responses]
    _api_slm_trace = slm_trace
    _api_reasoning = v.reasoning[:500] if v.reasoning else None
    _api_v100_claims = v.evidence.get('v100_claims')
    _api_v103_antibodies = v.evidence.get('v103_antibodies')
    _api_speculative_mode = v.evidence.get('speculative_mode')
    _api_v98_canary_token = v.evidence.get('v98_canary_token')
    _api_v98_guard = v.evidence.get('v98_guard_verdict') or v.evidence.get('v98_guard')
    _api_v98_classification = v.evidence.get('v98_classification')
    _api_v98_attack_policy = v.evidence.get('v98_attack_policy')
    _api_v98_counter_executed = v.evidence.get('v98_counter_executed')
    _api_v98_bypass_recorded = v.evidence.get('v98_bypass_recorded')
    _api_falsification_status = v.evidence.get('falsification_status')
    _is_true_security_threat = (
        _gov_decision == 'KILL'
        or v.verdict == 'FLAGGED'
        or _multimodal_block
        or _route_decision.lane == LANE_SECURITY
        or bool(v.evidence.get('threat_detected'))
        or bool(v.evidence.get('injection_detected'))
    )
    if isinstance(v.evidence, dict):
        v.evidence['judge_evaluated'] = True
        v.evidence['routing'] = _route_decision.to_dict()
    if isinstance(_api_v98_classification, dict):
        _api_v98_classification['judge_evaluated'] = True
    elif _api_v98_classification is None:
        _api_v98_classification = {'judge_evaluated': True}

    if _is_true_security_threat:
        # [F-02 FIX 2026-09-25] Drop the judge verdict from the message: the
        # boundary/kernel verification may override it afterwards
        # (FAIL/ESCALATE), so a stale "verdict: PASS" inside a withheld answer
        # misled API consumers (RUNTIME-AUDIT-20260925-0411, finding F-02).
        _api_final_answer = '[SCP: Answer withheld]'
        if _gov_decision == 'KILL':
            _api_final_answer = '[SCP: Answer withheld — Governance KILL]'
        _api_slm_responses = []
        _api_slm_trace = []
        _api_reasoning = '[SCP: Answer withheld]'
        _api_v100_claims = None
        _api_v103_antibodies = None
        _api_speculative_mode = None
        _api_v98_canary_token = None
        _api_v98_guard = None
        _api_v98_classification = None
        _api_v98_attack_policy = None
        _api_v98_counter_executed = None
        _api_v98_bypass_recorded = None
        _api_falsification_status = None
        logger.info(f'[V104.41 #X] API boundary enforcing abstain (all fields cleared): verdict={v.verdict}, gov={_gov_decision}')
    elif v.verdict == 'PASS' and (not _gov_decision or _gov_decision == 'UNKNOWN'):
        # [SEC-R2-02 second-pass 2026-09-30] Hoisted fail-closed check. TẠI SAO:
        # the missing/UNKNOWN-governance guard used to live ONLY inside the
        # chatbot branch below, so a non-chatbot ask with verdict PASS and
        # governance_decision == '' slipped through EVERY branch here and was
        # DELIVERED without any governance clearance (missing governance
        # silently behaving as ALLOW — directly against SEC-R2-02). A
        # verified-PASS without a governance decision must never clear the
        # boundary, on ANY lane. Escalation semantics match the chatbot branch
        # this was hoisted from: 403 raise (no withhold text is assigned — the
        # raise discards the response being built, which is exactly why the
        # old in-branch assignment before its raise was dead code).
        logger.warning("[SEC-R2-02] Governance decision missing or UNKNOWN in _ask_impl — enforcing fail-closed withhold")
        raise HTTPException(status_code=403, detail="Governance clearance missing — fail-closed")
    elif not _is_chatbot_lane and _gov_decision in ('ESCALATE', 'DEGRADED'):
        # [S-H1 fix] A positive verdict with degraded/escalated governance is
        # NOT cleared: governance disagreement (ESCALATE) or crosscheck
        # failure (DEGRADED) means the 2-LLM consensus did not uphold it.
        _api_final_answer = '[SCP: Answer withheld — governance degraded]'
        _api_slm_responses = []
        _api_slm_trace = []
        _api_reasoning = '[SCP: Answer withheld — governance degraded]'
        _api_v100_claims = None
        _api_v103_antibodies = None
        _api_speculative_mode = None
        _api_v98_canary_token = None
        _api_v98_guard = None
        _api_v98_classification = None
        _api_v98_attack_policy = None
        _api_v98_counter_executed = None
        _api_v98_bypass_recorded = None
        _api_falsification_status = None
        logger.info('[S-H1] API boundary withholding answer: verdict=PASS but governance=%s', _gov_decision)
    elif not _is_chatbot_lane and v.verdict in ('FAIL', 'FLAGGED', 'DEGRADED', 'UNCERTAIN', 'ESCALATE'):
        # [F-02 FIX 2026-09-25] Same rationale as the security-lane branch:
        # the kernel verification may still override this verdict afterwards,
        # so the withhold text must not embed a verdict that can go stale.
        _api_final_answer = '[SCP: Answer withheld]'
        _api_slm_responses = []
        _api_slm_trace = []
        _api_reasoning = '[SCP: Answer withheld]'
        _api_v100_claims = None
        _api_v103_antibodies = None
        _api_speculative_mode = None
        _api_v98_canary_token = None
        _api_v98_guard = None
        _api_v98_classification = None
        _api_v98_attack_policy = None
        _api_v98_counter_executed = None
        _api_v98_bypass_recorded = None
        _api_falsification_status = None
        logger.info(f'[V104.41 #X] API boundary enforcing factual abstain: verdict={v.verdict}')
    elif not _is_chatbot_lane and v.verdict == 'UNKNOWN' and v.evidence.get('why_gate', {}).get('decision') == 'REJECT':
        _api_final_answer = '[SCP: Answer withheld — WHY Gate blocked]'
        _api_slm_responses = []
        _api_slm_trace = []
        _api_reasoning = '[SCP: WHY Gate blocked]'
        _api_v100_claims = None
        _api_v103_antibodies = None
        _api_speculative_mode = None
        _api_v98_canary_token = None
        _api_v98_guard = None
        _api_v98_classification = None
        _api_v98_attack_policy = None
        _api_v98_counter_executed = None
        _api_v98_bypass_recorded = None
        _api_falsification_status = None
        logger.info(f'[FIX-1] API boundary enforcing WHY Gate block (all fields cleared): verdict={v.verdict}')
    elif _is_chatbot_lane:
        # Filter out internal SLM safety artifacts
        if str(_api_final_answer).startswith("User Safety:") or str(_api_final_answer).strip() == "safe":
            _api_final_answer = None

        if not _api_final_answer or str(_api_final_answer).startswith('[SCP: Answer withheld'):
            if _ai_answer and not str(_ai_answer).startswith("User Safety:"):
                _api_final_answer = _ai_answer
            else:
                # Conversational context memory resolver
                _ans_from_mem = None
                _q_lower = req.question.lower()
                if any(k in _q_lower for k in ("tên tôi là gì", "tôi tên là gì", "tôi tên gì", "tên của tôi", "nhớ tôi không", "nhớ tên tôi")):
                    for _h in reversed(_history or []):
                        if _h.get("role") == "user":
                            import re as _re_mem
                            _m_name = _re_mem.search(r"(?:tên\s+là|tôi\s+là|mình\s+là)\s+([A-Za-zÀ-ỹ]+)", _h.get("content", ""), _re_mem.IGNORECASE)
                            if _m_name:
                                _ans_from_mem = f"Bạn đã giới thiệu bạn tên là {_m_name.group(1)}! Tôi luôn ghi nhớ thông tin bạn chia sẻ trong phiên trò chuyện này."
                                break
                    if not _ans_from_mem:
                        _ans_from_mem = "Trong phiên trò chuyện này, bạn chưa nói cho tôi biết tên của bạn. Bạn có muốn chia sẻ tên với tôi không?"
                elif any(k in _q_lower for k in ("chào", "hello", "hi")):
                    _ans_from_mem = "Chào bạn! Tôi là SCP — rất vui được trò chuyện và hỗ trợ bạn."
                elif any(k in _q_lower for k in ("bạn là ai", "who are you")):
                    _ans_from_mem = "Mình là SCP — một trợ lý AI thông minh, hỗ trợ trao đổi tự nhiên, tra cứu thông tin và xử lý tác vụ an toàn."

                _api_final_answer = _ans_from_mem or getattr(v, "final_answer", "") or "Tôi là SCP, trợ lý AI của bạn."
                if str(_api_final_answer).startswith("User Safety:"):
                    _api_final_answer = "Tôi là SCP, trợ lý AI của bạn. Rất vui được hỗ trợ bạn!"

        if _gov_decision in ('KILL', 'REJECT', 'DENY', 'ESCALATE', 'DEGRADED'):
            raise HTTPException(status_code=403, detail="Governance KILL enforced")
        if not _gov_decision or _gov_decision == 'UNKNOWN':
            # [SEC-R2-02] Fail-closed backstop for non-PASS chatbot verdicts
            # (PASS is already escalated by the hoisted check above). The old
            # withhold-text assignment here was dead code — the raise right
            # below discards the response being built — so it is removed.
            logger.warning("[SEC-R2-02] Governance decision missing or UNKNOWN in _ask_impl — enforcing fail-closed withhold")
            _gov_decision = 'DENY'
            raise HTTPException(status_code=403, detail="Governance clearance missing — fail-closed")
        if not _api_reasoning:
            _api_reasoning = v.reasoning[:500] if v.reasoning else "Conversational response"

    elif v.verdict == 'UNKNOWN':
        if _api_final_answer and '[SCP: unverified]' not in _api_final_answer:
            _sources = []
            for r in v.slm_responses:
                if r.get('answer'):
                    _sources.append(f"  • {r.get('slm_name', '?')}: {str(r.get('answer', ''))[:60]}")
            _source_text = '\n'.join(_sources) if _sources else '  (không có SLM nào trả lời)'
            _api_final_answer = str(_api_final_answer) + str(f'\n\nSCP đã kiểm tra:\n{_source_text}\nĐộ tin cậy: {v.confidence:.0%} — chưa đạt ngưỡng (cần ≥70%)')

    # Milestone 2: Fact Separation & Confidence Badge Payload (R2)
    from scp.knowledge.domain_knowledge import FactSeparator
    _fact_separator = FactSeparator()
    _fact_res = _fact_separator.separate(
        question=req.question,
        answer=str(_api_final_answer or ""),
        lane=_route_decision.lane,
        confidence=float(v.confidence if v.confidence is not None else 0.8),
        retrieval_result=_retrieval_res if "_retrieval_res" in locals() and _retrieval_res else {},
        contexts=req.contexts,
    )
    _verified_facts = _fact_res["verified_facts"]
    _llm_reasoning = _fact_res["llm_reasoning"]
    _confidence_badge = _fact_res["confidence_badge"]

    if _is_true_security_threat:
        _verified_facts = []
        _llm_reasoning = "[SCP: Answer withheld]"
        _confidence_badge = {
            "badge": "UNVERIFIED_CONJECTURE",
            "score": 0.0,
            "sources_consulted": [],
            "transparency_notes": "Security boundary triggered fail-closed withhold.",
        }

    if v.verdict == 'PASS' and _api_final_answer and (len(_api_final_answer) > 20):
        # [W1-c1 2026-10-02] Fire-and-forget create_task bị thay bằng AWAIT có
        # bound: không task nào sống sót sau finalize (wait_for hủy coroutine
        # quá hạn). Fact-check là nhánh phụ trợ — khi quá bound, fail-open
        # (proceed) như hành vi nuốt exception trước đây; verdict không đổi.
        try:
            await asyncio.wait_for(
                _async_fact_check(_api_final_answer, req.question, v98_context.get('session_id', '')),
                timeout=_FACTCHECK_AWAIT_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            logger.warning('fact-check bound exceeded — proceeding (auxiliary branch, verdict unchanged)')
        except Exception as e:
            logger.debug(f'[V104.37] api_server.py: e={e}', exc_info=True)

    # --- RESTORED SUBSYSTEMS HOOKS (Wave 1 & 2) ---
    # [AUDIT-20260909 MACH2-BUG2c] TẠI SAO tách: trước đây cả 5 hook dùng chung
    # MỘT try/except với logger.debug — 1 ledger fail làm MẤT toàn bộ các hook
    # còn lại một cách im lặng. Mỗi hook giờ fail độc lập và log WARNING.
    import uuid as _hook_uuid
    from pathlib import Path as _HookPath
    _data_dir = _HookPath(os.environ.get("SCP_DATA_DIR", "data"))

    # 1. Risk Intelligence
    try:
        from scp.risk_intelligence import RiskClassifier, RiskSignal
        _classifier = RiskClassifier()
        _signals = [RiskSignal(source_id="judge", kind="independent", observed_directly=True)]
        _risk = _classifier.classify(_signals, desired_level="PR2", hazard_severity="low")
        if _risk and _risk.level:
            v.evidence['risk_level'] = _risk.level.value
    except Exception as _hook_exc:
        logger.warning(f'[RESTORED-SYSTEMS] risk hook failed: {_hook_exc}', exc_info=True)

    # 2. History Evidence Ledger
    # [HIST-LEDGER-CONTRACT 2026-09-26] Chỉ ghi record khi verdict map được
    # sang contract thật của validate_record (PASS → verified/
    # independent_adjudication); verdict khác → không ghi gì (xem helper).
    try:
        from scp.history.evidence_ledger import append_record
        _record = _history_evidence_record(
            verdict=str(v.verdict or ""),
            session_id=str(req.session_id or ""),
            question=str(req.question or ""),
        )
        if _record is not None:
            # [ASK-BLOCK-FIX 2026-09-28] append_record re-reads the entire
            # hash-chained JSONL on every call (O(file size)) before appending —
            # sync file I/O on the event loop. Offload to worker thread;
            # append + hash-chain semantics unchanged, failures still warn.
            await asyncio.to_thread(append_record, _data_dir / "history_evidence.jsonl", _record)
    except Exception as _hook_exc:
        logger.warning(f'[RESTORED-SYSTEMS] history hook failed: {_hook_exc}', exc_info=True)

    # 3. World State (if PASS, record an event)
    # [C-S2 AUDIT-20260913] Root cause (evidence: scp/world_state/
    # temporal_authority.py:91-92): hook passed evidence_refs=[] while
    # record_observation() defaults epistemic_status="OBSERVED", and an
    # OBSERVED assertion REQUIRES evidence_refs ("unaudited world writes are
    # forbidden"). Result: WorldStateError raised on EVERY judge PASS, caught
    # below as a warning only — world_state never received a /ask record.
    # Fix at the failure point: the auditable provenance of this /ask run is
    # its request-ledger run_id (attached to request.state.scp_run by the
    # traced_request wrapper, same object stage_request already reads), so the
    # event is recorded with evidence_refs=[run_id]. Store-level failures stay
    # fail-open for /ask (hook is auxiliary) but MUST be logged — never silent.
    try:
        if v.verdict == 'PASS':
            _ws_run = getattr(getattr(request, "state", None), "scp_run", None)
            _ask_run_id = str(getattr(_ws_run, "run_id", "") or "")
            if _ask_run_id:
                from scp.contracts.time import now_utc_iso
                from scp.world_state import EntityEventAuthority, TemporalAuthority
                # [ASK-BLOCK-FIX 2026-09-28] FoundationDB.__init__ runs
                # sqlite3.connect + PRAGMA quick_check (full DB scan) and
                # record_event is a sync INSERT — event-loop blocking on EVERY
                # PASS verdict. Move open->record->close to a worker thread;
                # payload captured eagerly, fail-open warning semantics kept.
                _ws_confidence = v.confidence
                _ws_question_head = req.question[:100]

                def _record_world_state_event() -> None:
                    _temporal = TemporalAuthority(db_path=str(_data_dir / "world_state.sqlite"))
                    try:
                        _eea = EntityEventAuthority(_temporal)
                        _eea.record_event(
                            entity_id="ask_session",
                            event_kind="pass_verdict",
                            payload={"confidence": _ws_confidence, "question": _ws_question_head},
                            valid_time=now_utc_iso(),
                            evidence_refs=[_ask_run_id],
                            actor_id="scp-judge"
                        )
                    finally:
                        _temporal.close()

                await asyncio.to_thread(_record_world_state_event)
            else:
                logger.warning('[RESTORED-SYSTEMS] world_state hook: judge PASS without request run_id - world write skipped (unaudited world writes are forbidden)')
    except Exception as _hook_exc:
        logger.warning(f'[RESTORED-SYSTEMS] world_state hook failed: {_hook_exc}', exc_info=True)

    # 4. Calibration (record prediction for UNKNOWN/PARTIAL)
    try:
        if v.verdict in ("UNKNOWN", "PARTIAL", "FLAGGED"):
            from scp.calibration.ledger import CalibrationLedger
            # [ASK-BLOCK-FIX 2026-09-28] CalibrationLedger init = sqlite
            # connect + PRAGMA quick_check; record_prediction = sync INSERT —
            # event-loop blocking. Move open->record->close to a worker
            # thread; payload captured eagerly, semantics unchanged.
            _cal_domain = v.domain or "general"
            _cal_verdict = v.verdict
            _cal_confidence = v.confidence

            def _record_calibration_prediction() -> None:
                _cal = CalibrationLedger(db_path=str(_data_dir / "calibration.sqlite"))
                try:
                    _cal.record_prediction(
                        domain=_cal_domain,
                        task_class="ask",
                        predictor_type="judge",
                        predictor_id="judge_v3",
                        prediction={"verdict": _cal_verdict, "confidence": _cal_confidence}
                    )
                finally:
                    _cal.close()

            await asyncio.to_thread(_record_calibration_prediction)
    except Exception as _hook_exc:
        logger.warning(f'[RESTORED-SYSTEMS] calibration hook failed: {_hook_exc}', exc_info=True)

    # 5. Forecast (if future intent detected)
    try:
        if any(w in req.question.lower() for w in ["sẽ", "dự đoán", "tương lai", "will", "predict"]):
            from scp.contracts.time import now_utc_iso as _now_utc_iso
            from scp.forecast.ledger import ForecastLedger
            _fc = ForecastLedger(db_path=str(_data_dir / "forecast.sqlite"))
            try:
                _fc.record_case({
                    "id": str(_hook_uuid.uuid4())[:8],
                    "domain": v.domain or "general",
                    "claimant": "user",
                    "claim": req.question[:200],
                    "date": _now_utc_iso(),
                    "verdict": v.verdict,
                    "confidence": v.confidence,
                    "outcome_code": 9
                })
            finally:
                _fc.close()
    except Exception as _hook_exc:
        logger.warning(f'[RESTORED-SYSTEMS] forecast hook failed: {_hook_exc}', exc_info=True)
    # ----------------------------------------------
    # 6. Multi-turn Chat Memory Persistence
    if req.session_id:
        try:
            from scp.core.chat_memory import get_chat_memory_store
            _mem_store = get_chat_memory_store()
            # [ASK-BLOCK-FIX 2026-09-28] ChatMemoryStore.append opens the
            # file, writes, os.fsync() and may prune the WHOLE file (>2MB)
            # under an OS file-lock — sync I/O blocking the event loop.
            # Offload both appends to worker threads; user->assistant order
            # and error semantics preserved.
            _mem_session = req.session_id
            _mem_user_content = req.question
            _mem_assistant_content = str(_api_final_answer or "")
            _mem_metadata = {
                "verdict": v.verdict,
                "confidence": v.confidence,
                "domain": v.domain or "general",
                "governance": _gov_decision,
            }
            await asyncio.to_thread(
                _mem_store.append, session_id=_mem_session, role="user", content=_mem_user_content
            )
            await asyncio.to_thread(
                _mem_store.append,
                session_id=_mem_session,
                role="assistant",
                content=_mem_assistant_content,
                metadata=_mem_metadata,
            )
        except Exception as _mem_save_exc:
            logger.warning("[_ask_impl] Failed to persist chat memory turn: %s", _mem_save_exc, exc_info=True)

    # 7. Backward Traceability Recording
    import secrets as _secrets
    _ws_run = getattr(getattr(request, "state", None), "scp_run", None)
    _trace_id = getattr(_ws_run, "trace_id", None) or getattr(getattr(request, "state", None), "trace_id", None)
    if not _trace_id:
        _trace_id = f"trace_{_secrets.token_hex(8)}"
    _ask_run_id = str(getattr(_ws_run, "run_id", "") or "")

    stage_request(request, 'response_boundary', verdict=v.verdict, governance_decision=_gov_decision)
    if _web_fallback_used:
        _api_slm_trace.append({'domain': v.domain or '' or '', 'slm_name': 'public_web_search', 'answer': 'retrieved public snippets', 'time_ms': None, 'source': 'public-search', 'evidence': _web_fallback})
    return AskResponse(
        trace_id=_trace_id,
        run_id=_ask_run_id or None,
        verdict=v.verdict,
        final_answer=_api_final_answer,
        confidence=v.confidence,
        domain=v.domain or '' or '',
        falsification_status=_api_falsification_status,
        governance_decision=_gov_decision or v.evidence.get('governance_decision'),
        lane=_route_decision.lane if "_route_decision" in locals() else "LANE_CHATBOT",
        routing=_route_decision.to_dict() if "_route_decision" in locals() else {},
        v98_guard=_api_v98_guard,
        v98_classification=_api_v98_classification,
        v98_attack_policy=_api_v98_attack_policy,
        v98_counter_executed=_api_v98_counter_executed,
        v98_canary_token=_api_v98_canary_token,
        v98_bypass_recorded=_api_v98_bypass_recorded,
        elapsed_ms=round(elapsed_ms, 1),
        session_id=v98_context['session_id'],
        slm_trace=_api_slm_trace,
        phase_timings=phase_timings,
        reasoning=_api_reasoning,
        slm_responses=_api_slm_responses,
        v100_claims=_api_v100_claims,
        v103_antibodies=_api_v103_antibodies,
        speculative_mode=_api_speculative_mode,
        web_fallback_used=_web_fallback_used,
        web_fallback=_web_fallback or None,
        detector_degraded=_detector_degraded,
        detector_note=('; '.join(_detector_notes) if _detector_notes else None),
        fact_check_degraded=_fact_check_degraded or None,
        fact_check_note=(_fact_check_note or None),
        verified_facts=_verified_facts,
        llm_reasoning=_llm_reasoning,
        confidence_badge=_confidence_badge,
    )
