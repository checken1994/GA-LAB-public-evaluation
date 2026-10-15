"""
[Capability 4] Voice I/O — STT (Speech-to-Text) + TTS (Text-to-Speech).

TÁI SAO: SCP chỉ nhận text. User muốn hỏi bằng giọng nói → cần Whisper STT.
SCP trả lời text → cần TTS để user nghe được.

STT: openai-whisper (local, free)
TTS: edge-tts (Microsoft Edge TTS, free)
"""
from __future__ import annotations

import logging
import os
import tempfile

logger = logging.getLogger("scp.capabilities.voice")

class VoiceHandler:
    """STT + TTS handler."""

    def __init__(self):
        self._whisper_model = None

    def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        """STT: audio bytes → text (Whisper local)."""
        try:
            import whisper
            if self._whisper_model is None:
                self._whisper_model = whisper.load_model("base")
            # [Fix 4-a-013] try/finally ensures the temp file is unlinked even
            # if transcribe() raises — previously the file leaked in /tmp on
            # any exception (DNA #9: no harm — leaks accumulate under load).
            tmp_path: str | None = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(audio_bytes)
                    f.flush()
                    tmp_path = f.name
                result = self._whisper_model.transcribe(tmp_path, language=language)
                return result.get("text", "")
            finally:
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        logger.debug('VoiceHandler.transcribe: OSError ignored', exc_info=True)
        except ImportError:
            logger.warning("whisper not installed — pip install openai-whisper")
            return ""
        except Exception as e:
            logger.debug(f"STT error: {e}", exc_info=True)
            return ""

    async def speak(self, text: str, voice: str = "vi-VN-HoaiMyNeural") -> bytes:
        """TTS: text → audio bytes (edge-tts, free)."""
        try:
            import edge_tts
            # [Fix 4-a-013] try/finally ensures the temp file is unlinked even
            # if edge-tts save()/read() raises — previously leaked in /tmp on
            # any exception (DNA #9: no harm).
            tmp_path: str | None = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    tmp_path = f.name
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(tmp_path)
                with open(tmp_path, "rb") as audio:
                    data = audio.read()
                return data
            finally:
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        logger.debug('VoiceHandler.speak: OSError ignored', exc_info=True)
        except ImportError:
            logger.warning("edge-tts not installed — pip install edge-tts")
            return b""
        except Exception as e:
            logger.debug(f"TTS error: {e}", exc_info=True)
            return b""
