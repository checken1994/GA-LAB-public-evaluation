import importlib.util
import unittest
from pathlib import Path

BRIDGE_PATH = Path(__file__).with_name("scp_dashboard_bridge.py")
SPEC = importlib.util.spec_from_file_location("scp_dashboard_bridge", BRIDGE_PATH)
bridge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        bridge.REQUESTS.clear()
        bridge.BRIDGE_ENV = {"SCP_DASHBOARD_ORIGINS": "https://dashboard.example,http://localhost:3000"}

    def test_origin_allowlist(self):
        self.assertIn("https://dashboard.example", bridge.allowed_origins())
        self.assertNotIn("https://evil.example", bridge.allowed_origins())

    def test_rate_limit(self):
        self.assertTrue(all(not bridge.limited("127.0.0.1") for _ in range(bridge.RATE_LIMIT)))
        self.assertTrue(bridge.limited("127.0.0.1"))

    def test_live_payload_sanitizes_failed_v98(self):
        old_read_api = bridge.read_api
        bridge.read_api = lambda path, authenticated: (200, {"version": "14.0.0"}) if path == "/health" else (401, {"detail": "Invalid auth token"})
        try:
            result = bridge.build_live_payload()
        finally:
            bridge.read_api = old_read_api
        self.assertEqual(result["state"], "degraded")
        self.assertEqual(result["healthStatus"], 200)
        self.assertEqual(result["status"], {"available": False, "httpStatus": 401})
        self.assertNotIn("detail", result["status"])


if __name__ == "__main__":
    unittest.main()
