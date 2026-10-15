from pathlib import Path


def test_ask_request_has_bounded_multimodal_and_history_fields():
    root = Path(__file__).resolve().parents[2]
    source = (root / "scp" / "api_server_parts" / "helpers.py").read_text(encoding="utf-8")
    assert "image_data" in source
    assert "max_length=8_000_000" in source
    assert "conversation_history" in source
    assert "max_length=8" in source


def test_dashboard_preserves_session_and_has_explicit_media_controls():
    root = Path(__file__).resolve().parents[2]
    source = (root / "scp" / "api" / "dashboard_html.py").read_text(encoding="utf-8")
    assert "sessionStorage" in source
    assert "conversation_history" in source
    assert "getUserMedia" in source
    assert "MediaRecorder" not in source
    assert "captureImage" in source
    assert "video: true, audio: false" in source


def test_real_ask_path_prioritizes_current_question_and_accepts_image_data():
    root = Path(__file__).resolve().parents[2]
    source = (root / "scp" / "api_server_parts" / "_ask_impl.py").read_text(encoding="utf-8")
    assert "_history = []" in source
    assert "await _gateway.chat(req.question" in source
    assert "HIỆN TẠI" in source
    assert "base64.b64decode" in source
    assert "Invalid or oversized image_data" in source


def test_websocket_chat_passes_conversation_context_to_judge():
    root = Path(__file__).resolve().parents[2]
    source = (root / "scp" / "api" / "chat.py").read_text(encoding="utf-8")
    # [event-loop fix] the call moved to asyncio.to_thread — the contract
    # is the same call with the same argument, now off the event loop.
    assert (
        "_conversation_mgr.get_context_string, session_id" in source
        or "get_context_string(session_id)" in source
    )
    assert '"conversation_history": _conversation_context' in source
    assert '"current_question": user_message' in source


def test_chat_runtime_user_visible_strings_are_clean_and_vietnamese_keywords_work():
    root = Path(__file__).resolve().parents[2]
    source = (root / "scp" / "api" / "chat.py").read_text(encoding="utf-8")
    assert 'f"{RELEASE_LABEL} — kết nối. Session: {session_id}\\n"' in source
    assert 'f"Tôi có thể kiểm tra câu trả lời, phát hiện tấn công, và tự học.\\n"' in source
    assert 'f"Hỏi tôi bất cứ điều gì — tôi sẽ nói \'Tại sao?\' và kiểm tra."' in source
    assert '"(Không có câu trả lời)"' in source
    assert '"Tôi chưa đủ thông tin để kết luận. "' in source
    assert '"Tôi không thể xác nhận câu trả lời này. Lý do: "' in source
    assert '"Đã kiểm tra: câu trả lời đạt độ tin cậy ' in source
    assert '"tiến hóa" in user_message.lower()' in source
    assert '"học" in user_message.lower()' in source


def test_ask_runtime_user_visible_strings_and_fact_check_keywords_are_clean():
    root = Path(__file__).resolve().parents[2]
    source = (root / "scp" / "api_server_parts" / "_ask_impl.py").read_text(encoding="utf-8")
    assert "Bạn là SCP — một trợ lý AI thông minh." in source
    for keyword in ("có thật", "đúng không", "có thật không", "kiểm chứng"):
        assert keyword in source
    assert "[SCP: Answer withheld — Governance KILL]" in source
    assert "[SCP: Answer withheld — WHY Gate blocked]" in source
    # [EM-DASH-FIX] governance degraded/ESCALATE withhold text dùng em-dash
    # như mọi nhánh sibling — literal '?' cũ là artifact typo, user-visible.
    assert "[SCP: Answer withheld — governance degraded]" in source
    assert "[SCP: Answer withheld ? governance degraded]" not in source
    assert "SCP đã kiểm tra:" in source
    assert "Độ tin cậy: {v.confidence:.0%} — chưa đạt ngưỡng (cần ≥70%)" in source
