"""[SEC-FIX voice-temp 2026-09-26] Temp wav cleanup contract cho VoiceJailbreakDetector.

FA-09 provenance: probe (temp dir) xác nhận TRƯỚC fix — khi whisper
load_model/transcribe raise, file .wav tạm (delete=False, chứa audio người
dùng) còn tồn tại trong %TEMP% (residue tmpvcefx3ki.wav).

Contract sau fix: try/finally dọn temp trên MỌI đường — exception lẫn success.
Lỗi gốc không bị nuốt; lỗi unlink chỉ log debug.
"""
from __future__ import annotations

import sys
import tempfile
import types

from scp.security.image_voice_detector import VoiceJailbreakDetector


class _BoomModel:
    def transcribe(self, path):
        raise RuntimeError("simulated ASR crash")


class _BenignModel:
    def transcribe(self, path):
        return {"text": "xin chao banthan binh thuong"}


def _install_fake_whisper(monkeypatch, model) -> None:
    fake = types.ModuleType("whisper")
    fake.load_model = lambda name="base": model
    monkeypatch.setitem(sys.modules, "whisper", fake)


def test_temp_audio_file_removed_on_transcription_failure(tmp_path, monkeypatch):
    _install_fake_whisper(monkeypatch, _BoomModel())
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    detector = VoiceJailbreakDetector()
    result = detector.detect(audio_bytes=b"RIFF-fake" + b"\x00" * 32)
    assert result.error and "simulated ASR crash" in result.error
    assert list(tmp_path.glob("*.wav")) == [], (
        "temp wav phải được dọn cả khi transcribe raise (probe: residue tồn tại trước fix)"
    )


def test_temp_audio_file_removed_on_success(tmp_path, monkeypatch):
    _install_fake_whisper(monkeypatch, _BenignModel())
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    detector = VoiceJailbreakDetector()
    result = detector.detect(audio_bytes=b"RIFF-fake" + b"\x00" * 32)
    # Success-path behavior giữ nguyên: text được trích + không flag jailbreak.
    assert result.text_extracted.startswith("xin chao")
    assert result.jailbreak_detected is False
    assert list(tmp_path.glob("*.wav")) == []


def test_no_temp_file_when_no_audio_bytes(tmp_path, monkeypatch):
    """Không audio bytes → không tạo temp nào (path rỗng không chạm filesystem)."""
    _install_fake_whisper(monkeypatch, _BenignModel())
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    detector = VoiceJailbreakDetector()
    detector.detect(audio_bytes=b"")
    assert list(tmp_path.glob("*.wav")) == []
