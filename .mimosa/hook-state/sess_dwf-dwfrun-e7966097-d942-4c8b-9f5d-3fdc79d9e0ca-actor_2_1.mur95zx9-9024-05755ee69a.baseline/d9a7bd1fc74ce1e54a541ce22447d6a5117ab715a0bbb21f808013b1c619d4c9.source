"""Reality test for Fix 4-a-013: voice.py temp file leak on exception.

Behavioral execution test: verifies that VoiceHandler unlinks temporary files
even when transcription raises an exception (no temp file leaks in finally block).
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

def test_transcribe_cleans_up_temp_file_on_exception():
    from scp.capabilities.voice import VoiceHandler

    handler = VoiceHandler()
    captured_paths = []

    def mock_transcribe_failure(path, **kwargs):
        captured_paths.append(path)
        assert os.path.exists(path), f"Temp file should exist during transcribe execution: {path}"
        raise RuntimeError("Simulated ASR transcription failure")

    mock_whisper = MagicMock()
    mock_model = MagicMock()
    mock_model.transcribe = mock_transcribe_failure
    mock_whisper.load_model = MagicMock(return_value=mock_model)
    handler._whisper_model = mock_model

    with patch.dict(sys.modules, {"whisper": mock_whisper}):
        # Run transcribe with dummy bytes
        res = handler.transcribe(b"RIFF....WAVEfmt ....data....")
        assert res == ""

    # Verify that the temp file was unlinked in the finally block
    assert len(captured_paths) == 1
    tmp_path = captured_paths[0]
    assert not os.path.exists(tmp_path), f"Temp file leaked after exception: {tmp_path}"

if __name__ == "__main__":
    test_transcribe_cleans_up_temp_file_on_exception()
    print("PASS: reality_4-a-013 behavioral tests passed")
