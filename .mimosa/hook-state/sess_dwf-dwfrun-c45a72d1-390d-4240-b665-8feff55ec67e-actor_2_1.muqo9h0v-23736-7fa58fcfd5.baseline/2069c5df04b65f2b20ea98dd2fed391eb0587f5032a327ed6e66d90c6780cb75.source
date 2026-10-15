import os

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

from unittest.mock import MagicMock, patch

from scp.capabilities.voice import VoiceHandler


def test_voice_handler_transcribe():
    '''FA-13: Cover capabilities/voice.py transcription logic'''
    vh = VoiceHandler()
    mock_whisper = MagicMock()
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "hello stt"}
    mock_whisper.load_model.return_value = mock_model
    
    with patch.dict('sys.modules', {'whisper': mock_whisper}):
        res = vh.transcribe(b"fake_audio", language="vi")
        assert res == "hello stt"
