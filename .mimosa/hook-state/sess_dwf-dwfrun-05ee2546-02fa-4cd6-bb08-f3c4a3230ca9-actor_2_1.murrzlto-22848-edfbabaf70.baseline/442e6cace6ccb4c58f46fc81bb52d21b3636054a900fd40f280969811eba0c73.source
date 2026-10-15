"""Adversarial stress tests for P0 security boundaries and redaction fixes.

Conducted by Challenger 2 (Milestone 1: P0 Security Boundary & Redaction Challenger).

Tests:
1. /v3/trace/{trace_id} endpoint authentication fail-closed behavior:
   - Unauthenticated access (missing header) -> 401
   - Invalid bearer token -> 401
   - Malformed authorization headers -> 401
   - Brute-force rate limiting (5 failures in 60s) -> 429
   - Valid admin token grants access (404 if not found, 200 with redacted record if found)
   - Route path aliases (/api/scp/v3/trace, /api/v3/trace, /v3/trace) all enforce auth
2. redact_attributes() adversarial robustness:
   - Nested dicts, lists, sets, tuples
   - Uppercase and mixed-case 2-tuple headers
   - DSN credential masking & special characters
   - Circular reference behavior (cycle detection audit)
   - Ultra-long strings (>1000 chars) truncation & secret masking
   - Wide lists (>100 items) bounded sequence truncation
3. EvidenceReplay.verify() fail-closed verification:
   - Empty/missing inputs -> ok=False, status='UNVERIFIED'
   - Incomplete parameters -> ok=False, status='UNVERIFIED'
   - Failing/corrupted test command -> ok=False, status='FAILED'
   - Non-existent test binary -> ok=False, status='FAILED'
   - Metacharacter injection in file_path -> DIAGNOSTIC_NEGATIVE rejection
   - Absence of manufactured green passes
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure environment is configured for test
os.environ["SCP_OTEL_ENABLED"] = "0"
_ADMIN_TOKEN = "challenger2-admin-secret-token-xyz987"
os.environ["SCP_AUTH_TOKEN_SECRET"] = _ADMIN_TOKEN

from scp.api_server import app
from scp.autofix.evidence_replay import EvidenceReplay, EvidenceRole
from scp.core.trace_contract import (
    _MAX_SEQUENCE_ITEMS,
    _MAX_STRING_LENGTH,
    redact_attributes,
)
from scp.core.trace_store import get_trace_store
from scp.security.auth import _auth_failures

# =====================================================================
# 1. /v3/trace/{trace_id} Endpoint Authentication Tests
# =====================================================================

class TestTraceEndpointAuthentication:
    """Adversarially challenge the /v3/trace/{trace_id} security boundary."""

    @pytest.fixture(autouse=True)
    def reset_rate_limit(self, monkeypatch):
        """Clear rate limiter state and pin auth config before each test.

        [ISOLATION FIX] Several other test modules write
        os.environ["SCP_AUTH_TOKEN_SECRET"] at MODULE-IMPORT level (e.g.
        tests/T03_capability/test_flow_34_swe_bench_scp_standard.py sets
        'test-swe-token'). load_auth_config() reads the env per request, so
        whichever module imported last silently decided whether the valid
        admin token matched — observed in full-suite runs as
        `assert 401 == 404` on the valid-token flow. Pin the auth config for
        every test in this class (monkeypatch restores it afterwards) so the
        challenge is deterministic regardless of import order. The limiter
        itself (scp/security/auth.py) is NOT touched.
        """
        _auth_failures.clear()
        monkeypatch.delenv("SCP_AUTH_PASSWORD", raising=False)
        monkeypatch.delenv("SCP_AUTH_PASSWORD_FILE", raising=False)
        monkeypatch.delenv("SCP_AUTH_TOKEN_SECRET_FILE", raising=False)
        monkeypatch.setenv("SCP_AUTH_TOKEN_SECRET", _ADMIN_TOKEN)
        yield
        _auth_failures.clear()

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_unauthenticated_access_fails_closed_401(self, client):
        """Missing Authorization header must return fail-closed HTTP 401."""
        response = client.get("/v3/trace/nonexistent-trace-id")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "auth" in data["detail"].lower() or "unauthorized" in data["detail"].lower()

    def test_invalid_bearer_token_fails_closed_401(self, client):
        """Invalid Bearer token must return fail-closed HTTP 401."""
        headers = {"Authorization": "Bearer completely-wrong-token-abc123"}
        response = client.get("/v3/trace/nonexistent-trace-id", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid auth token"

    @pytest.mark.parametrize("bad_header", [
        "Bearer ",                          # Empty token after Bearer
        "Bearer",                           # Just 'Bearer' without space
        "Basic dXNlcjpwYXNz",               # Basic auth instead of Bearer
        "Token xyz123",                     # Token prefix
        "garbage-auth-header-value",        # Raw string
        "",                                 # Empty header
        "   ",                              # Whitespace only
        "Bearer   ",                        # Whitespace token
    ])
    def test_malformed_authorization_headers_fail_closed_401(self, client, bad_header):
        """Malformed or non-Bearer headers must fail-closed with HTTP 401."""
        headers = {"Authorization": bad_header}
        response = client.get("/v3/trace/nonexistent-trace-id", headers=headers)
        assert response.status_code == 401

    def test_rate_limiting_triggers_429_on_brute_force(self, client):
        """5 failed auth attempts within 60s must trigger HTTP 429 Too Many Requests."""
        headers = {"Authorization": "Bearer bad-token"}
        # First 5 attempts fail with 401
        for i in range(5):
            resp = client.get(f"/v3/trace/t-{i}", headers=headers)
            assert resp.status_code == 401, f"Attempt {i+1} should fail with 401"

        # 6th attempt must be blocked by rate-limiting (429)
        resp_blocked = client.get("/v3/trace/t-blocked", headers=headers)
        assert resp_blocked.status_code == 429
        assert "too many" in resp_blocked.json()["detail"].lower()

    def test_valid_admin_token_grants_access_and_retrieves_redacted_trace(self, client):
        """Valid admin token grants access; non-existent trace returns 404, existing returns 200 with redacted attributes."""
        admin_headers = {"Authorization": f"Bearer {_ADMIN_TOKEN}"}

        # 1. Valid token on nonexistent trace -> 404 Not Found (auth passed!)
        resp_404 = client.get("/v3/trace/trace-nonexistent-12345", headers=admin_headers)
        assert resp_404.status_code == 404
        assert "not found" in resp_404.json()["detail"].lower()

        # 2. Record a trace with sensitive credentials and query it
        store = get_trace_store()
        t_id = f"trace-adversarial-{os.urandom(4).hex()}"
        store.record_trace({
            "trace_id": t_id,
            "query": "select * from users where token='secret-token'",
            "routing": {"auth_token": f"Bearer sk-{os.urandom(12).hex()}", "safe_field": "model-v1"},
            "retrieval": {"database_dsn": f"postgres://dbuser:{os.urandom(8).hex()}@127.0.0.1:5432/scp"},
            "multi_llm_crosscheck": {"api_key": f"sk-proj-{os.urandom(12).hex()}"},
            "governance": {"secret_salt": f"salt-{os.urandom(8).hex()}"},
            "final_decision": {"status": "OK", "cookie": f"session={os.urandom(8).hex()}"}
        })

        resp_200 = client.get(f"/v3/trace/{t_id}", headers=admin_headers)
        assert resp_200.status_code == 200
        record = resp_200.json()

        # Verify sensitive fields are redacted
        assert record["trace_id"] == t_id
        assert record["routing"]["auth_token"] == "[REDACTED]"
        assert record["routing"]["safe_field"] == "model-v1"
        assert record["retrieval"]["database_dsn"] == "[REDACTED]"
        assert record["multi_llm_crosscheck"]["api_key"] == "[REDACTED]"
        assert record["governance"]["secret_salt"] == "[REDACTED]"
        assert record["final_decision"]["cookie"] == "[REDACTED]"

    @pytest.mark.parametrize("route_prefix", [
        "/v3/trace",
        "/api/v3/trace",
        "/api/scp/v3/trace",
    ])
    def test_all_route_aliases_enforce_admin_auth(self, client, route_prefix):
        """All mounted alias paths must reject unauthenticated requests."""
        resp = client.get(f"{route_prefix}/trace-check")
        assert resp.status_code == 401


# =====================================================================
# 2. redact_attributes() Adversarial Input Tests
# =====================================================================

class TestRedactAttributesAdversarial:
    """Stress-test redact_attributes against adversarial inputs."""

    def test_nested_containers_and_sensitive_keys(self):
        """Deeply nested structures must have all sensitive keys masked."""
        payload = {
            "root": {
                "level1": {
                    "level2": {
                        "api_key": f"sk-{os.urandom(8).hex()}",
                        "password": f"pw-{os.urandom(8).hex()}",
                        "safe_nested": ["normal_text", {"token": f"tok-{os.urandom(8).hex()}"}],
                        "header_tuples": [
                            ("AUTHORIZATION", f"Bearer sk-{os.urandom(8).hex()}"),
                            ("X-Custom-Token", f"custom-{os.urandom(8).hex()}"),
                            ("User-Agent", "Mozilla/5.0"),
                        ]
                    }
                }
            }
        }
        res = redact_attributes(payload)
        level2 = res["root"]["level1"]["level2"]
        assert level2["api_key"] == "[REDACTED]"
        assert level2["password"] == "[REDACTED]"
        assert level2["safe_nested"][0] == "normal_text"
        assert level2["safe_nested"][1]["token"] == "[REDACTED]"
        assert level2["header_tuples"][0] == ("AUTHORIZATION", "[REDACTED]")
        assert level2["header_tuples"][1] == ("X-Custom-Token", "[REDACTED]")
        assert level2["header_tuples"][2] == ("User-Agent", "Mozilla/5.0")

    @pytest.mark.parametrize("header_tuple,expected_val", [
        (("AUTHORIZATION", "Bearer sk-1234567890"), "[REDACTED]"),
        (("Authorization", "Bearer sk-1234567890"), "[REDACTED]"),
        (("AuThOrIzAtIoN", "Bearer secret"), "[REDACTED]"),
        (("X-API-KEY", "secret-value"), "[REDACTED]"),
        (("Proxy-Authorization", "Basic dXNlcjpwYXNz"), "[REDACTED]"),
        (("SET-COOKIE", "session=abcdef"), "[REDACTED]"),
        (("Accept", "application/json"), "application/json"),
        (("Content-Type", "text/plain"), "text/plain"),
    ])
    def test_tuple_headers_casing_and_matching(self, header_tuple, expected_val):
        """Tuples representing headers in any case must mask sensitive header values."""
        res = redact_attributes(header_tuple)
        assert res[0] == header_tuple[0]
        assert res[1] == expected_val

    def test_dsn_masking_standard_and_special_chars(self):
        """Standard DSNs must have passwords redacted."""
        dsns = [
            ("postgres://admin:secretpass@db.example.com:5432/main",
             "postgres://admin:[REDACTED]@db.example.com:5432/main"),
            ("mysql://app_user:Complex%20P%40ss@mysql.local/db",
             "mysql://app_user:[REDACTED]@mysql.local/db"),
            ("http://user:pass123@api.internal.net",
             "http://user:[REDACTED]@api.internal.net"),
        ]
        for original, expected in dsns:
            redacted = redact_attributes(original)
            assert redacted == expected, f"Failed on DSN: {original}"
            assert "secretpass" not in redacted
            assert "Complex%20P%40ss" not in redacted
            assert "pass123" not in redacted

    def test_circular_reference_recursion_error_missing_cycle_detection(self):
        """REMEDIATED: True cycle detection and recursion depth limiting."""
        d = {"name": "circular_dict"}
        d["self"] = d
        redacted = redact_attributes(d)
        assert redacted["name"] == "circular_dict"
        assert redacted["self"] == "[CIRCULAR_REFERENCE]"

        # Also test list cycles
        l = ["item"]
        l.append(l)
        redacted_list = redact_attributes(l)
        assert redacted_list[0] == "item"
        assert redacted_list[1] == "[CIRCULAR_REFERENCE]"

        # Also test depth limit > 20
        deep = cur = {}
        for i in range(25):
            cur["child"] = {}
            cur = cur["child"]
        redacted_deep = redact_attributes(deep)
        check = redacted_deep
        for _ in range(21):
            check = check["child"]
        assert check == "[MAX_DEPTH_EXCEEDED]"

    def test_dsn_empty_username_leaks_password(self):
        """REMEDIATED: Redis DSN with empty user `://:password@host` masks password."""
        redis_dsn = "redis://:mypassword123@localhost:6379/0"
        redacted = redact_attributes(redis_dsn)
        assert "mypassword123" not in redacted
        assert redacted == "redis://:[REDACTED]@localhost:6379/0"

    def test_dsn_special_character_at_symbol_leaks_password_suffix(self):
        """REMEDIATED: Password containing '@' is fully masked up to last '@'."""
        mongo_dsn = "mongodb://root:p@ssw0rd!@cluster0.mongodb.net/test"
        redacted = redact_attributes(mongo_dsn)
        assert "ssw0rd!" not in redacted
        assert "p@ssw0rd!" not in redacted
        assert redacted == "mongodb://root:[REDACTED]@cluster0.mongodb.net/test"

    def test_key_param_without_question_or_ampersand_leaks(self):
        """REMEDIATED: api_key=value not preceded by ? or & is masked with word boundary."""
        text = "configured with api_key=supersecrettoken123"
        redacted = redact_attributes(text)
        assert "supersecrettoken123" not in redacted
        assert redacted == "configured with api_key=[REDACTED]"

    def test_hyphenated_api_key_param_leaks(self):
        """REMEDIATED: ?api-key=value (with hyphen) is matched and masked."""
        text = "https://api.example.com?api-key=supersecrettoken123"
        redacted = redact_attributes(text)
        assert "supersecrettoken123" not in redacted
        assert redacted == "https://api.example.com?api-key=[REDACTED]"

    def test_ultra_long_strings_truncation_and_masking(self):
        """Strings > 512 chars must be truncated and embedded secrets masked."""
        secret_sk = "sk-adversarialtoken1234567890"
        long_str = "prefix_" + "x" * 400 + " Bearer secret_bearer_token " + "y" * 400 + f" {secret_sk} " + "z" * 400
        assert len(long_str) > 1000

        redacted = redact_attributes(long_str)
        # Secret values must NOT appear in output
        assert "secret_bearer_token" not in redacted
        assert secret_sk not in redacted
        # Must be truncated
        assert len(redacted) <= _MAX_STRING_LENGTH + len("...[truncated]")
        assert redacted.endswith("...[truncated]")

    def test_wide_lists_bounded_sequence_length(self):
        """Lists with > 100 items must be bounded to _MAX_SEQUENCE_ITEMS (50)."""
        wide_list = [f"item_{i}" for i in range(120)]
        wide_list[5] = "Bearer secret_in_first_50"
        wide_list[80] = "Bearer secret_in_last_70"

        redacted = redact_attributes(wide_list)
        assert len(redacted) == _MAX_SEQUENCE_ITEMS
        assert redacted[5] == "Bearer [REDACTED]"
        # Item 80 was truncated off
        assert "secret_in_last_70" not in str(redacted)


# =====================================================================
# 3. EvidenceReplay.verify() Fail-Closed Tests
# =====================================================================

class TestEvidenceReplayFailClosed:
    """Stress-test EvidenceReplay.verify() to ensure fail-closed semantics (FA-04)."""

    @pytest.fixture
    def replay(self, tmp_path):
        return EvidenceReplay(working_dir=tmp_path)

    def test_missing_all_arguments_fails_closed(self, replay):
        """Calling verify() with no parameters must return ok=False, status='UNVERIFIED'."""
        res = replay.verify()
        assert res["ok"] is False
        assert res["status"] == "UNVERIFIED"
        assert "reason" in res

    def test_none_parameters_fails_closed(self, replay):
        """Calling verify(None, None) must return ok=False, status='UNVERIFIED'."""
        res = replay.verify(test_command=None, candidate_source=None)
        assert res["ok"] is False
        assert res["status"] == "UNVERIFIED"

    def test_empty_string_test_command_fails_closed(self, replay):
        """Empty test_command string must return ok=False, status='UNVERIFIED'."""
        res = replay.verify(test_command="")
        assert res["ok"] is False
        assert res["status"] == "UNVERIFIED"

    def test_candidate_source_without_test_command_fails_closed(self, replay):
        """Candidate source without test command must fail closed."""
        res = replay.verify(candidate_source="def broken(): return 1 / 0")
        assert res["ok"] is False
        assert res["status"] == "UNVERIFIED"
        assert res["reason"] == "Incomplete verification parameters"

    def test_failing_test_command_returns_failed_not_verified(self, replay):
        """Failing test command (exit code != 0) must return ok=False, status='FAILED'."""
        res = replay.verify(test_command=["python", "-c", "import sys; sys.exit(1)"])
        assert res["ok"] is False
        assert res["status"] == "FAILED"
        assert res["discriminating"] is False

    def test_nonexistent_binary_returns_failed(self, replay):
        """Non-existent executable must fail closed with ok=False, status='FAILED'."""
        res = replay.verify(test_command="nonexistent_binary_xyz_12345 --run")
        assert res["ok"] is False
        assert res["status"] == "FAILED"
        assert "EXECUTION ERROR" in res["output"] or "not found" in res["output"].lower()

    def test_shell_metacharacter_injection_in_file_path_rejected(self, replay):
        """classify_evidence must reject file_paths containing shell metacharacters."""
        malicious_path = "test_script.py; rm -rf /"
        result = replay.classify_evidence(
            test_command="pytest",
            buggy_source="x = 1",
            candidate_source="x = 2",
            gold_source="x = 3",
            file_path=malicious_path,
        )
        assert result.role == EvidenceRole.DIAGNOSTIC_NEGATIVE
        assert result.b_result[0] is False
        assert "unsafe characters" in result.b_result[1]

    def test_windows_83_short_name_temp_path_is_not_rejected(self, replay):
        """Regression guard (pre-RC run 36102606213): GitHub Windows runners
        expose the temp directory through 8.3 short names (e.g.
        C:\\Users\\RUNNER~1\\AppData\\Local\\Temp). post_fix_verify builds the
        replay file_path from tempfile.TemporaryDirectory(), so a legitimate
        '~' in the path must NOT be treated as a shell metacharacter — the
        B-leg must execute instead of returning
        '[REJECTED: unsafe characters in file_path]'. Genuinely unsafe inputs
        stay rejected (see test_shell_metacharacter_injection_in_file_path_rejected)."""
        runner_shaped_path = str(
            Path(replay.working_dir) / "RUNNER~1" / "bsgva_replay_ab12cd34" / "util.py"
        )
        result = replay.classify_evidence(
            test_command=["python", "-c", "import sys; sys.exit(0)"],
            buggy_source="x = 1",
            candidate_source="x = 2",
            gold_source="x = 3",
            file_path=runner_shaped_path,
        )
        # The replay actually EXECUTED (B-leg ran the command) instead of
        # rejecting the path outright.
        assert result.b_result[0] is True
        assert "unsafe characters" not in result.b_result[1]

    def test_no_manufactured_green_pass(self, replay):
        """Ensure that verify() never returns ok=True unless an actual test command exits 0."""
        # Genuine passing test command
        res_pass = replay.verify(test_command=["python", "-c", "import sys; sys.exit(0)"])
        assert res_pass["ok"] is True
        assert res_pass["status"] == "VERIFIED"

        # Invalid or corrupted inputs must NEVER produce ok=True
        corrupted_cases = [
            {"test_command": ["python", "-c", "raise RuntimeError()"]},
            {"test_command": "   "},
            {"test_command": []},
            {"test_command": None},
        ]
        for case in corrupted_cases:
            res = replay.verify(**case)
            assert res["ok"] is False, f"Corrupted case produced manufactured pass: {case}"
            assert res["status"] in ("UNVERIFIED", "FAILED")
