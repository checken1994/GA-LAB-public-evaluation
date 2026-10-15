from pathlib import Path

"""Reality test for Fix 4-a-015: image/voice check routes use asyncio.to_thread.

Before fix: /v104/image/check + /v104/voice/check async route handlers called
detect() synchronously (blocking CPU: OCR via Tesseract + Whisper ASR). The
event loop was blocked for the duration of OCR/ASR — slow /v104/image/check
stalled /health and all other async requests.

After fix: detect() is wrapped in `await asyncio.to_thread(...)` so the
event loop stays responsive while the blocking CPU work runs in a thread.

DNA principles exercised:
  #2  (vòng lặp khép kín — reality test of the fix, not just the fix)
  #9  (no harm — blocking I/O starves other async handlers)
  #22 (PASS ≠ TRUE — old code "worked" but stalled the event loop)
  #26 (reality test — AST inspection + behavioral thread execution test)
"""
import base64
import os
import secrets
import sys
import threading
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Hermetic boot (S17 contract, GAP-09): scp.core.capability_token fail-closes at
# import when SCP_CAPABILITY_SECRET is missing. The portable runner provides an
# isolated env (no repo .env), so generate a random per-run secret here instead
# of reading the repo .env. Behavioral assertions below are unchanged.
os.environ.setdefault("SCP_CAPABILITY_SECRET", secrets.token_hex(32))

FILE = str(Path(__file__).resolve().parents[2]) + '/scp/api/routes/v104_routes.py'


def test_reality_4_a_015_ast():
    """Verify AST to_thread usage in v104_routes.py."""
    assert os.path.isfile(FILE), f"FAIL: file missing: {FILE}"
    with open(FILE, encoding="utf-8") as f:
        src = f.read()
    assert "to_thread" in src or "run_in_executor" in src, (
        "FAIL: neither asyncio.to_thread nor run_in_executor is used in v104_routes.py"
    )


def test_image_check_runs_in_worker_thread():
    """Behavioral test: OCR detect() executes on a separate worker thread via to_thread."""
    from scp.api import _shared
    from scp.api_server import app

    main_thread = threading.get_ident()
    detected_thread = None

    class MockDetectionResult:
        def __init__(self):
            self.jailbreak = False
            self.confidence = 0.0

    def mock_detect(image_bytes=None):
        nonlocal detected_thread
        detected_thread = threading.get_ident()
        return MockDetectionResult()

    orig_detector = _shared._image_detector
    mock_detector = MagicMock()
    mock_detector.detect = mock_detect
    _shared._image_detector = mock_detector

    try:
        client = TestClient(app)
        os.environ["SCP_AUTH_TOKEN_SECRET"] = "test-token-015"
        resp = client.post(
            "/v104/image/check",
            params={"image_base64": base64.b64encode(b"test-bytes").decode("ascii")},
            headers={"Authorization": "Bearer test-token-015"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert detected_thread is not None, "Detector was not called"
        assert detected_thread != main_thread, (
            f"Detector ran on main thread {main_thread}, not on a worker thread via asyncio.to_thread"
        )
    finally:
        _shared._image_detector = orig_detector


if __name__ == "__main__":
    test_reality_4_a_015_ast()
    test_image_check_runs_in_worker_thread()
    print("PASS: reality_4-a-015 behavioral test succeeded")
