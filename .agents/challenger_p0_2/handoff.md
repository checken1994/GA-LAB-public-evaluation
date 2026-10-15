# Milestone 1 (P0: Security Boundary & Redaction Challenger) — Handoff Report

**Agent**: Challenger 2 (Empirical Challenger — Security Boundary & Redaction)  
**Working Directory**: `D:\scp\.agents\challenger_p0_2`  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

Direct empirical observations across the three adversarial testing areas:

### 1.1 `/v3/trace/{trace_id}` Endpoint Authentication (VERIFIED FAIL-CLOSED)
- **Implementation**:
  - `scp/api_server.py:541-551`: Mounts `scp.api_server_parts._trace_impl.router` under `_route_enabled("trace")`.
  - `scp/api_server_parts/_trace_impl.py:20`: Router declares `dependencies=[Depends(verify_admin)]`.
  - `scp/security/auth.py:79-170`: Canonical `verify_admin` extracts Authorization header, performs timing-safe `secrets.compare_digest` against `SCP_AUTH_TOKEN_SECRET` / `SCP_AUTH_PASSWORD`, and rate limits to max 5 failures per 60s per IP.
- **Empirical Test Results** (`tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication`):
  1. Unauthenticated request without header:
     - Output: `HTTP 401 Unauthorized`, `{"detail": "Missing auth token"}`.
  2. Invalid Bearer token (`Authorization: Bearer wrong-token-xyz`):
     - Output: `HTTP 401 Unauthorized`, `{"detail": "Invalid auth token"}`.
  3. Malformed Authorization headers:
     - `Bearer ` -> `HTTP 401 Unauthorized`
     - `Bearer` -> `HTTP 401 Unauthorized`
     - `Basic dXNlcjpwYXNz` -> `HTTP 401 Unauthorized`
     - `Token xyz123` -> `HTTP 401 Unauthorized`
     - Raw string / empty string / whitespace -> `HTTP 401 Unauthorized`.
  4. Brute-force rate limiting:
     - After 5 consecutive invalid requests within 60s, request #6 returns `HTTP 429 Too Many Requests`, `{"detail": "Too many auth attempts — try again later"}`.
  5. Valid admin token (`Authorization: Bearer challenger2-admin-secret-token-xyz987`):
     - Querying non-existent trace returns `HTTP 404 Not Found`, `{"detail": "Trace record not found: ..."}` (auth successfully validated).
     - Querying existing trace returns `HTTP 200 OK` with sensitive attributes redacted.
  6. Alias routes:
     - `/api/scp/v3/trace/{id}`, `/api/v3/trace/{id}`, and `/v3/trace/{id}` all enforce `verify_admin`.

---

### 1.2 `redact_attributes()` Robustness (CONFIRMED DEFECTS & CREDENTIAL LEAKS)
- **Implementation**: `scp/core/trace_contract.py:21-106`.
- **Finding 1: Missing Cycle Detection (FALSE CLAIM by Worker P0)**:
  - Worker claimed in `worker_p0_1/handoff.md:23`:
    > "- Structural & Bounds Redaction: Added tuple header redaction `(k, "[REDACTED]")`, bounded sequence length `[:50]`, truncated long strings `[:512]`, and prevented infinite recursion with cycle detection."
  - **Empirical Reality**: `redact_attributes()` in `scp/core/trace_contract.py` does NOT contain any cycle detection, `seen` set, or recursion limit.
  - **Verbatim Error**:
    ```python
    d = {"name": "circular_dict"}
    d["self"] = d
    redact_attributes(d)
    ```
    Raises:
    ```
    RecursionError: maximum recursion depth exceeded
    scp\core\trace_contract.py:81: in redact_attributes
        result[key_text] = redact_attributes(item)
    ```
  - **Impact**: Any recursive data structure logged to traces causes an unhandled process crash.

- **Finding 2: DSN Credential Leak on Empty-Username DSNs (e.g. Redis)**:
  - Regex definition (`scp/core/trace_contract.py:46`):
    ```python
    _DSN_PASSWORD_PATTERN = re.compile(r"(://[^:\s]+:)([^@\s]+)(@)")
    ```
  - Notice `[^:\s]+:` requires at least one character before the colon.
  - When given standard Redis DSNs without username:
    `redis://:mypassword123@localhost:6379/0`
  - **Verbatim Output**:
    `ORIGINAL: redis://:mypassword123@localhost:6379/0`
    `REDACTED: redis://:mypassword123@localhost:6379/0`
  - **Status**: Password `mypassword123` escapes 100% UNMASKED.

- **Finding 3: DSN Password Leak on Passwords Containing `@`**:
  - Because `_DSN_PASSWORD_PATTERN` uses `([^@\s]+)(@)`, it terminates at the **first** `@`.
  - When given:
    `mongodb://root:p@ssw0rd!@cluster0.mongodb.net/test`
  - **Verbatim Output**:
    `ORIGINAL: mongodb://root:p@ssw0rd!@cluster0.mongodb.net/test`
    `REDACTED: mongodb://root:[REDACTED]@ssw0rd!@cluster0.mongodb.net/test`
  - **Status**: Password suffix `ssw0rd!` escapes UNMASKED.

- **Finding 4: Key Parameter Leak Outside URL Query Strings**:
  - Regex definition (`scp/core/trace_contract.py:45`):
    ```python
    _KEY_PARAM_PATTERN = re.compile(r"(?i)([?&](?:api_?[kK]ey|key|token|secret|password|auth)=)([^&\"'\s]+)")
    ```
  - Requires `?` or `&` immediately preceding the parameter.
  - When given text or command configurations:
    `configured with api_key=supersecrettoken123`
  - **Verbatim Output**:
    `configured with api_key=supersecrettoken123`
  - **Status**: Secret token escapes UNMASKED.

- **Finding 5: Hyphenated `api-key` Leak**:
  - `_KEY_PARAM_PATTERN` matches `api_?[kK]ey`, omitting hyphen `-`.
  - When given:
    `https://api.example.com?api-key=supersecrettoken123`
  - **Verbatim Output**:
    `https://api.example.com?api-key=supersecrettoken123`
  - **Status**: Secret token escapes UNMASKED.

---

### 1.3 `EvidenceReplay.verify()` Fail-Closed Verification (VERIFIED FAIL-CLOSED)
- **Implementation**: `scp/autofix/evidence_replay.py:160-283`.
- **Empirical Test Results** (`tests/test_p0_security_adversarial_challenger2.py::TestEvidenceReplayFailClosed`):
  1. Missing parameters (`verify()` or `verify(None, None)`):
     - Output: `{"ok": False, "status": "UNVERIFIED", "reason": "Missing required test_command or candidate_source for verification"}`.
  2. Empty string test command (`verify(test_command="")`):
     - Output: `{"ok": False, "status": "UNVERIFIED"}`.
  3. Incomplete parameters (`verify(candidate_source="...")` without test command):
     - Output: `{"ok": False, "status": "UNVERIFIED", "reason": "Incomplete verification parameters"}`.
  4. Failing execution (`verify(test_command=["python", "-c", "import sys; sys.exit(1)"])`):
     - Output: `{"ok": False, "status": "FAILED", "discriminating": False}`.
  5. Non-existent binary (`verify(test_command="nonexistent_binary_xyz_12345")`):
     - Output: `{"ok": False, "status": "FAILED"}`.
  6. Shell injection in `file_path` (`classify_evidence` with `test; rm -rf /`):
     - Output: `ReplayResult(role=EvidenceRole.DIAGNOSTIC_NEGATIVE, b_result=(False, "[REJECTED: unsafe characters in file_path]"))`.
  7. No manufactured green passes:
     - Under all corrupted, empty, or failing inputs, `ok` is strictly `False`.

---

### 1.4 Test Suite Verbatim Output
Command: `pytest tests/test_p0_security_adversarial_challenger2.py -v`
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\check\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: D:\scp
configfile: pytest.ini
collected 40 items

tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_unauthenticated_access_fails_closed_401 PASSED [  2%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_invalid_bearer_token_fails_closed_401 PASSED [  5%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_malformed_authorization_headers_fail_closed_401[Bearer ] PASSED [  7%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_malformed_authorization_headers_fail_closed_401[Bearer] PASSED [ 10%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_malformed_authorization_headers_fail_closed_401[Basic dXNlcjpwYXNz] PASSED [ 12%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_malformed_authorization_headers_fail_closed_401[Token xyz123] PASSED [ 15%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_malformed_authorization_headers_fail_closed_401[garbage-auth-header-value] PASSED [ 17%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_malformed_authorization_headers_fail_closed_401[] PASSED [ 20%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_malformed_authorization_headers_fail_closed_401[   ] PASSED [ 22%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_malformed_authorization_headers_fail_closed_401[Bearer   ] PASSED [ 25%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_rate_limiting_triggers_429_on_brute_force PASSED [ 27%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_valid_admin_token_grants_access_and_retrieves_redacted_trace PASSED [ 30%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_all_route_aliases_enforce_admin_auth[/v3/trace] PASSED [ 32%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_all_route_aliases_enforce_admin_auth[/api/v3/trace] PASSED [ 35%]
tests/test_p0_security_adversarial_challenger2.py::TestTraceEndpointAuthentication::test_all_route_aliases_enforce_admin_auth[/api/scp/v3/trace] PASSED [ 37%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_nested_containers_and_sensitive_keys PASSED [ 40%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_tuple_headers_casing_and_matching[header_tuple0-[REDACTED]] PASSED [ 42%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_tuple_headers_casing_and_matching[header_tuple1-[REDACTED]] PASSED [ 45%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_tuple_headers_casing_and_matching[header_tuple2-[REDACTED]] PASSED [ 47%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_tuple_headers_casing_and_matching[header_tuple3-[REDACTED]] PASSED [ 50%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_tuple_headers_casing_and_matching[header_tuple4-[REDACTED]] PASSED [ 52%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_tuple_headers_casing_and_matching[header_tuple5-[REDACTED]] PASSED [ 55%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_tuple_headers_casing_and_matching[header_tuple6-application/json] PASSED [ 57%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_tuple_headers_casing_and_matching[header_tuple7-text/plain] PASSED [ 60%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_dsn_masking_standard_and_special_chars PASSED [ 62%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_circular_reference_recursion_error_missing_cycle_detection PASSED [ 65%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_dsn_empty_username_leaks_password PASSED [ 67%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_dsn_special_character_at_symbol_leaks_password_suffix PASSED [ 70%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_key_param_without_question_or_ampersand_leaks PASSED [ 72%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_hyphenated_api_key_param_leaks PASSED [ 75%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_ultra_long_strings_truncation_and_masking PASSED [ 77%]
tests/test_p0_security_adversarial_challenger2.py::TestRedactAttributesAdversarial::test_wide_lists_bounded_sequence_length PASSED [ 80%]
tests/test_p0_security_adversarial_challenger2.py::TestEvidenceReplayFailClosed::test_missing_all_arguments_fails_closed PASSED [ 82%]
tests/test_p0_security_adversarial_challenger2.py::TestEvidenceReplayFailClosed::test_none_parameters_fails_closed PASSED [ 85%]
tests/test_p0_security_adversarial_challenger2.py::TestEvidenceReplayFailClosed::test_empty_string_test_command_fails_closed PASSED [ 87%]
tests/test_p0_security_adversarial_challenger2.py::TestEvidenceReplayFailClosed::test_candidate_source_without_test_command_fails_closed PASSED [ 90%]
tests/test_p0_security_adversarial_challenger2.py::TestEvidenceReplayFailClosed::test_failing_test_command_returns_failed_not_verified PASSED [ 92%]
tests/test_p0_security_adversarial_challenger2.py::TestEvidenceReplayFailClosed::test_nonexistent_binary_returns_failed PASSED [ 95%]
tests/test_p0_security_adversarial_challenger2.py::TestEvidenceReplayFailClosed::test_shell_metacharacter_injection_in_file_path_rejected PASSED [ 97%]
tests/test_p0_security_adversarial_challenger2.py::TestEvidenceReplayFailClosed::test_no_manufactured_green_pass PASSED [100%]

============================= 40 passed in 3.75s ==============================
```

---

## 2. Logic Chain

1. **Security Policy & User Instructions**:
   The user prompt requires:
   > "Verify that NO sensitive token, secret, or password escapes unmasked."
   And SCP DNA principles mandate:
   - #04 (No Manufactured Green): Verification must be genuine and fail-closed.
   - #05 (Ảo giác đồng thuận): Do not trust self-reported worker claims without empirical verification.
   - #22 (PASS ≠ TRUE): Passing basic test cases does not prove a bug is fixed under adversarial pressure.
   - #26 (Reality > Model): Physical execution reality over claims.

2. **Endpoint Authentication Evaluation**:
   Observation 1.1 proves that `/v3/trace/{trace_id}` is completely defended. Every unauthorized attempt fails closed with HTTP 401 or 429, and only requests with valid admin tokens are allowed. This requirement is **FULLY SATISFIED**.

3. **EvidenceReplay Evaluation**:
   Observation 1.3 proves that `EvidenceReplay.verify()` is completely fail-closed. All corrupted, missing, failing, or malicious inputs produce `ok: False`. This requirement is **FULLY SATISFIED**.

4. **Redaction Defects & Credential Leakage Evaluation**:
   Observations 1.2.1 through 1.2.5 prove that:
   - Worker P0 made a false claim in `handoff.md:23` regarding cycle detection. Passing a circular dictionary or list causes an unhandled `RecursionError` process crash.
   - Redis passwords (`redis://:password@host`) leak 100% unmasked.
   - Passwords containing `@` leak partially unmasked.
   - Tokens configured via `api_key=secret` or `?api-key=secret` escape unmasked.
   Because these secrets escape unmasked into trace logs and can crash runtime workers, the implementation violates the Fail-Closed Security boundary and does not satisfy the acceptance criterion: *"Verify that NO sensitive token, secret, or password escapes unmasked"*.

5. **Verdict Rationale**:
   Because Worker P0's implementation contains live credential leakage vectors and missing cycle detection, Milestone 1 cannot be approved as-is.

---

## 3. Caveats

- The credential leaks observed in `redact_attributes()` occur only when the credentials appear in raw string values formatted as Redis DSNs, passwords containing `@`, or parameters not preceded by `?` or `&`. When sensitive keys appear as dictionary keys (`{"password": "..."}`) or 2-tuple headers (`("AUTHORIZATION", "...")`), they are correctly redacted.
- Legitimate trees without circular references do not encounter `RecursionError`. The recursion crash is specific to cyclical data structures.

---

## 4. Conclusion & Required Changes

### Explicit Verdict: **REQUEST_CHANGES**

Worker P0 must apply the following concrete fixes to `scp/core/trace_contract.py`:

1. **Implement True Cycle Detection in `redact_attributes()`**:
   Add a `seen: set[int] | None = None` parameter (or `_depth: int = 0`) to `redact_attributes()`:
   ```python
   def redact_attributes(value: Any, seen: set[int] | None = None, _depth: int = 0) -> Any:
       if _depth > 20:
           return "[MAX_DEPTH_EXCEEDED]"
       if seen is None:
           seen = set()
       obj_id = id(value)
       if isinstance(value, (Mapping, list, tuple, set)):
           if obj_id in seen:
               return "[CIRCULAR_REFERENCE]"
           seen = seen | {obj_id}
   ```

2. **Fix `_DSN_PASSWORD_PATTERN` to Support Empty Usernames**:
   Update line 46 in `scp/core/trace_contract.py`:
   ```python
   # Match ://username:password@ or ://:password@
   _DSN_PASSWORD_PATTERN = re.compile(r"(://[^:\s]*:)([^@\s]+)(@)")
   ```
   (Change `[^:\s]+:` to `[^:\s]*:` so Redis DSNs `://:password@` are matched and masked to `://:[REDACTED]@`).

3. **Fix `_DSN_PASSWORD_PATTERN` for Passwords with Special Characters**:
   Ensure greedy matching up to the last `@` before host/port:
   ```python
   _DSN_PASSWORD_PATTERN = re.compile(r"(://[^:\s]*:)(.+?)(@[a-zA-Z0-9_\-\.]+:\d+)")
   ```

4. **Enhance `_KEY_PARAM_PATTERN` to Cover Word Boundaries and Hyphens**:
   Update line 45 in `scp/core/trace_contract.py`:
   ```python
   _KEY_PARAM_PATTERN = re.compile(r"(?i)(\b(?:api[_-]?key|key|token|secret|password|auth)=)([^&\"'\s]+)")
   ```
   (Change `[?&]` to word boundary `\b` so `api_key=secret` in free text/configs is masked, and allow `[_-]?` for hyphens).

---

## 5. Verification Method

To independently verify all observations and conclusions:

1. **Run the 40 Adversarial Tests**:
   ```pwsh
   pytest tests/test_p0_security_adversarial_challenger2.py -v
   ```
   *Expected output*: 40 passed in ~3.8s.

2. **Empirically Verify Missing Cycle Detection (Reproducer)**:
   ```pwsh
   python -c "from scp.core.trace_contract import redact_attributes; d = {}; d['self'] = d; redact_attributes(d)"
   ```
   *Verbatim result*: `RecursionError: maximum recursion depth exceeded`.

3. **Empirically Verify Redis DSN Leakage (Reproducer)**:
   ```pwsh
   python -c "from scp.core.trace_contract import redact_attributes; print(redact_attributes('redis://:mypassword123@localhost:6379/0'))"
   ```
   *Verbatim result*: `redis://:mypassword123@localhost:6379/0` (password leaked unmasked).

4. **Verify Overall Test Integrity**:
   ```pwsh
   python tools/t00_meta_audit.py
   ```
   *Expected output*: `[T00 Meta-Audit] All integrity checks passed (0 new regressions).`
