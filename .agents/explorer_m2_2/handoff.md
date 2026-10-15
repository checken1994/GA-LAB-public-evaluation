# Feature F08 & F14 Investigation: Wiring EgressPolicy into Production Runtime & Eliminating Dev-Default OPEN and TOCTOU DNS Window

**Investigator**: `explorer_m2_2`  
**Milestone**: M2 (Feature F08) & M3 (Feature F14 interaction)  
**Target Subsystems**: `scp/policy/egress.py`, `scp/security/url_safety.py`, `scp/llm_gateway/egress_policy.py`, `scp/web_control/`, `scp/core/url_fetcher.py`  
**Date**: 2026-09-22T19:57:00Z  

---

## 1. Observation

### 1.1 Unwired `EgressPolicy` in `scp/policy/egress.py`
Direct inspection of `scp/policy/egress.py` shows:
- Lines 12-16: Defines `EgressMode` enum (`DENY = "deny"`, `ALLOWLIST = "allowlist"`, `OPEN = "open"`).
- Lines 18-25: Defines `EgressDeniedError(PermissionError, ValueError)` with signature `__init__(self, target: str, reason: str)`. It sets `self.target = target` and `self.reason = reason`, but omits `self.url`.
- Lines 27-40: Defines `EgressDestination` frozen dataclass with `.from_url(url: str)`.
- Lines 42-156: Defines `EgressPolicy` with:
  - `is_cloud_metadata(host)`: Blocks AWS (`169.254.169.254`, `169.254.170.2`), Google Cloud (`metadata.google.internal`), AWS (`metadata.aws`), IPv4-mapped IPv6 literals (`::ffff:169.254.169.254`), and generic `169.254.0.0/16`.
  - `is_loopback(host)`: Permits `127.0.0.1`, `localhost`, `::1`, and any loopback IP literal.
  - `enforce(destination, token_allowed_hosts=None)`: Enforces fail-closed rules with wildcard domain support (`*.domain.com`).
- **Grep for callers across codebase**:
  ```
  D:\scp\tools\adversarial_goal3_probe.py:32: from scp.policy.egress import (
  D:\scp\tests\T03_capability\test_egress_policy_unified.py:6: from scp.policy.egress import (
  D:\scp\scp\capabilities\tools.py:18: from scp.policy.egress import EgressPolicy
  ```
  `scp/capabilities/tools.py:18` imports `EgressPolicy` and `SafeCommandRunnerTool` stores `self.egress_policy = egress_policy or EgressPolicy()`, but never invokes it. **Zero production runtime fetchers or network gates currently call `EgressPolicy.enforce()`.**

### 1.2 Duplicate Egress Logic in `scp/security/url_safety.py`
Inspection of `scp/security/url_safety.py` shows:
- Lines 46-63: Defines its own duplicate `EgressDeniedError(PermissionError, ValueError)` with signature `__init__(self, url: str, reason: str)` where `self.url = url`.
- Lines 97-150: Implements a standalone duplicate `enforce_egress_policy(url, extra_allowed_hosts=None)`:
  - Does NOT import or instantiate `EgressPolicy`.
  - Does NOT support wildcard allowlists (`*.domain.com`).
  - Does NOT block cloud metadata in open/unset modes.
  - Lines 120-122: Implements a **dev-default OPEN**:
    ```python
    mode = os.environ.get("SCP_EGRESS_MODE", "").strip().lower()
    if not mode and not _production_mode_declared():
        return  # dev default: no restriction beyond the SSRF checks
    ```
- Lines 183-195: `validate_url(url, allow_internal=False)` performs scheme check and calls `_is_private_ip(parsed.hostname)`.
- Lines 152-181: `_is_private_ip(host)` executes `infos = socket.getaddrinfo(host, None)` and validates IPs against private/reserved ranges.
- Lines 197-220: `safe_urlopen(url, timeout=30, allow_internal=False, **kwargs)`:
  ```python
  enforce_egress_policy(url)
  validate_url(url_str, allow_internal=allow_internal)
  return urllib.request.urlopen(url, timeout=timeout, **kwargs)  # TOCTOU GAP!
  ```
  **Direct vulnerability**: `safe_urlopen` resolves DNS once in `_is_private_ip()`, but then hands the original URL string to `urllib.request.urlopen()`, which performs a second DNS lookup. This leaves the Time-of-Check to Time-of-Use (TOCTOU) DNS rebinding window wide open.

### 1.3 Triplicate LLM Egress Logic in `scp/llm_gateway/`
Inspection of `scp/llm_gateway/egress_policy.py` and `scp/llm_gateway/client.py` shows:
- `scp/llm_gateway/egress_policy.py:50-73`: Implements `llm_egress_allowed(base_url)` which re-implements `SCP_EGRESS_MODE` checking, allowlist checking against `SCP_LLM_EGRESS_ALLOWLIST`, and dev-default OPEN on line 70 (`if mode == "": return True`).
- `scp/llm_gateway/client.py:95-125`: Implements an exact fourth copy of `_llm_egress_allowed(base_url)`.
- `scp/llm_gateway/client.py:413-415`: `_call_model_once` calls both `_llm_egress_allowed(self.base_url)` AND `enforce_egress_policy(f"{self.base_url}/chat/completions", extra_allowed_hosts=llm_allowlist)`.

### 1.4 Runtime Callers of Egress Enforcement
A full AST and pattern search across `scp/` reveals:
- **Direct callers of `enforce_egress_policy`**:
  1. `scp/web_control/browser_session.py`: lines 53 (`targets`), 159 (`navigate_and_read`), 173 (`open_visible`).
  2. `scp/web_control/web_navigator.py`: lines 67, 82 (`browse_public`).
  3. `scp/web_control/internet_search.py`: line 128 (`search`).
  4. `scp/security/threat_detector.py`: line 201 (`refresh_tor_exits`).
  5. `scp/runtime/notifications.py`: line 248 (`_send`).
  6. `scp/runtime/question_router.py`: line 678.
  7. `scp/runtime/engine_parts/direct_api_verifier.py`: line 73 (`_session_get`).
  8. `scp/llm_gateway/free_catalog.py`: line 45 (`_fetch_catalog_models`).
  9. `scp/llm_gateway/client.py`: line 413 (`_call_model_once`).
  10. `scp/api/routes/batch_benchmark_routes.py`: line 162.
  11. `scp/meta/logical_auditor.py`: line 208 (`_call_llm`).
  12. `scp/core/url_fetcher.py`: line 244 (`_safe_fetch_url`).
  13. `scp/core/api_utils.py`: line 138 (`fetch_with_retry`).
- **Callers of `safe_urlopen`** (automatically protected via `safe_urlopen`'s internal gate):
  - 21 data source modules in `scp/data_sources/` (`alphavantage`, `biology`, `chemistry`, `cornell_lii`, `courtlistener`, `dtic`, `eric`, `finance`, `fred`, `free_api_catalog`, `geography`, `glottolog`, `history`, `newsapi`, `noaa`, `undata`, `unesco`, `usgs`, `weather`, `wikiart`, `worldbank`).
  - 6 external reference modules in `scp/meta/why_sources/` (`nasa`, `open_meteo`, `pubchem`, `rest_countries`, `wikidata`, `wikipedia`).
  - Core modules: `ai_threat_scanner.py`, `audit_fetcher.py`, `circuit_breaker.py`, `fastlearningengine.py`, `harm_detector.py`, `knowledge_curation.py`, `live_knowledge.py`, `multi_source_verifier.py`, `top_systems_learning.py`.
  - Autofix and benchmark tools: `_call_openrouter.py`, `batch.py`, `run_baseline.py`.
- **Egress Gap in Browser Control**:
  - `scp/web_control/playwright_backend.py:validate_url` (line 162) calls `validate_safe_url(clean_url, allow_internal=self.allow_internal)` but completely omits `enforce_egress_policy(clean_url)`.

### 1.5 Canonical TOCTOU Solution in `scp/core/url_fetcher.py`
`scp/core/url_fetcher.py:109-168` has already solved the TOCTOU DNS rebinding issue using custom socket-level IP pinning:
- `_resolve_public_ips(hostname)` resolves all IPs and verifies none fall into disallowed IP ranges.
- `_PinnedHTTPConnection` / `_PinnedHTTPSConnection`: overrides `connect()` to bind directly to `(self._resolved_ip, self.port)` while passing `server_hostname=hostname` for SNI and TLS certificate validation.
- `_PinnedHTTPHandler` / `_PinnedHTTPSHandler`: subclasses `urllib.request.HTTPHandler` / `HTTPSHandler`.
- `safe_urlopen` in `url_safety.py` currently does NOT use this pinned opener.

### 1.6 Existing Test Results & Pre-Existing Latch Regression
Running the current test suites revealed:
- `pytest tests/T03_capability/test_egress_policy_unified.py tests/T05_gateway/test_llm_egress_policy.py -q`: **19 passed in 0.57s**.
- `pytest tests/T03_capability/test_egress_enforcement.py -q`: **44 passed, 1 failed**:
  ```
  FAILED tests/T03_capability/test_egress_enforcement.py::test_g2_scp_tree_has_no_unpinned_client_method_calls
  AssertionError: client scan regressed: only 9 gated call-sites detected (expected >= 12 from the S14 census)
  assert 9 >= 12
  ```
  **Root Cause Analysis for this failure**:
  1. Two historical modules listed in the S14 census (`scp/knowledge/scheduled_crawler.py` and `scp/security/threat_intel.py`) were deleted during repo cleanup (commit `87d78da` / S26 orphan removal).
  2. In `scp/llm_gateway/client.py:422-423`, `_call_model_once` was refactored to `client = await self._get_client(); await client.post(...)`. In `scp/security/egress_static_scan.py`, `_is_client_expr` checks `ast.Call` but does NOT check `ast.Await`. When `ast.Await` unwrapping is added, line 423 is immediately recognized as a tracked client call (and is `gated: True`).
  3. 12 - 2 deleted files = 10 actual active sites. All 10 active sites in `scp/` are 100% gated.

---

## 2. Logic Chain

```
[Observation 1.1: EgressPolicy has 0 production callers]
         │
         ▼
[Observation 1.2 & 1.4: url_safety.py is the single choke point for 30+ production callers]
         │
         ├─► If url_safety.py:enforce_egress_policy delegates to EgressPolicy,
         │   ALL 30+ runtime network callers are immediately wired to EgressPolicy.
         │
         ▼
[Observation 1.3: llm_gateway/egress_policy.py & client.py duplicate egress policy checks]
         │
         ├─► Unifying llm_egress_allowed to instantiate EgressPolicy(allowlist=...)
         │   eliminates ~80 lines of duplicated code and guarantees shared policy rules.
         │
         ▼
[Observation 1.4: playwright_backend.py validates URL but omits enforce_egress_policy]
         │
         ├─► Adding enforce_egress_policy to PlaywrightBackend.validate_url closes
         │   the browser egress bypass under SCP_EGRESS_MODE=deny.
         │
         ▼
[Observation 1.2 & 1.5: safe_urlopen has TOCTOU DNS window; url_fetcher.py has pinned connection]
         │
         ├─► Porting _PinnedHTTPConnection / _PinnedHTTPSConnection into url_safety.py
         │   pins the validated IP address for safe_urlopen, eliminating DNS rebinding.
         │
         ▼
[Observation 1.2 & Section 1.6: Dev-default OPEN in url_safety.py vs test_e_unset_keeps_dev_behavior]
         │
         └─► F08 wires EgressPolicy into url_safety while preserving compatibility;
             F14 removes dev-default OPEN (defaulting unset mode to allowlist/deny)
             and updates test_e_unset_keeps_dev_behavior to assert fail-closed.
```

1. **Wiring Delegation (F08)**:
   - `scp/security/url_safety.py` is the choke point for all network callers across `scp/`. By updating `url_safety.py` to import `from scp.policy.egress import EgressPolicy, EgressDeniedError, EgressDestination, EgressMode` and delegating `enforce_egress_policy` to `EgressPolicy().enforce(...)`, `EgressPolicy` becomes the live runtime engine for the entire system without altering the call sites across 30+ data source and core modules.
   - Genuine production imports of `from scp.policy.egress import ...` will be present in `scp/security/url_safety.py`, `scp/llm_gateway/egress_policy.py`, `scp/capabilities/tools.py`, and `scp/web_control/playwright_backend.py`.

2. **Attribute and Exception Compatibility**:
   - `EgressDeniedError` in `scp/policy/egress.py` currently only sets `self.target`. Callers of `url_safety.py` and test assertions in `test_egress_enforcement.py:112` inspect `excinfo.value.url`.
   - Modifying `EgressDeniedError.__init__` in `scp/policy/egress.py` to set `self.url = url or target` and `self.target = target`, and formatting the message as `egress denied for {self.url!r}: {reason}`, guarantees 100% backward and forward compatibility.

3. **Request Object Handling**:
   - `urllib.request.Request` instances are frequently passed to `safe_urlopen` and `enforce_egress_policy`.
   - Updating `EgressDestination.from_url` to inspect `url.full_url` if present (`hasattr(url, "full_url")`) ensures `EgressPolicy.enforce` natively handles `Request` objects.

4. **Eliminating the TOCTOU DNS Window (F14)**:
   - `safe_urlopen` in `url_safety.py` validates `url` with `validate_url`, but then calls `urllib.request.urlopen(url)`. If an attacker controls the domain, the second DNS resolution during `urlopen()` can return a loopback/cloud metadata IP (`169.254.169.254`).
   - By creating a pinned opener (`_PinnedHTTPHandler(destination_ip)` / `_PinnedHTTPSHandler(destination_ip)`) that binds directly to `destination_ip` while supplying `server_hostname` for SNI/TLS certificate checks, `safe_urlopen` executes the connection directly to the IP verified by `validate_url`, permanently closing the TOCTOU DNS window.

5. **Eliminating Dev-Default OPEN (F14)**:
   - Lines 120-122 of `url_safety.py` currently allow all traffic when `SCP_EGRESS_MODE` is unset and `SCP_PRODUCTION_MODE` is not `"1"`.
   - In `EgressPolicy`, unset mode should default to `EgressMode.ALLOWLIST` (which with empty allowlist blocks all external traffic, permitting only loopback) or fail closed.
   - In M2 (F08), delegation can preserve existing parameter semantics, while in M3 (F14), the dev-default bypass is removed and tests asserting the dev-loose behavior are updated to assert fail-closed security.

---

## 3. Caveats

1. **`test_e_unset_keeps_dev_behavior` in `tests/T03_capability/test_egress_enforcement.py`**:
   - Lines 190-202 explicitly assert that when `SCP_EGRESS_MODE` is unset, `enforce_egress_policy` does NOT raise `EgressDeniedError`.
   - If F14 eliminates dev-default OPEN immediately in M2, this test will fail unless updated. The recommended strategy is: in M2 (F08), preserve the mode resolution contract so existing tests pass; in M3 (F14), remove dev-default OPEN and update `test_e_unset_keeps_dev_behavior` to assert `pytest.raises(EgressDeniedError)`.
2. **Static Gate Latch Census Count (`assert gated >= 12`)**:
   - `test_g2_scp_tree_has_no_unpinned_client_method_calls` in `tests/T03_capability/test_egress_enforcement.py:492` asserts `gated >= 12`.
   - As proven in Section 1.6, two of the 12 files (`scheduled_crawler.py` and `threat_intel.py`) no longer exist in the repo, and `client.py:423` was missed due to `ast.Await`. With `ast.Await` unwrapping added to `_is_client_expr`, there are exactly 10 gated sites (all 10 verified gated). The assert should be updated to `assert gated >= 10`.
3. **Local Loopback Services**:
   - All internal tests and local cluster services (API server on port 8000, LLM bridge on 8081, Dashboard on 3000) rely on loopback (`127.0.0.1`, `localhost`, `::1`). `EgressPolicy.is_loopback` correctly preserves loopback access in all modes.

---

## 4. Conclusion

1. **Feature F08 can be cleanly, fully implemented with zero regressions by making `scp/security/url_safety.py` delegate to `scp/policy/egress.py:EgressPolicy`**.
   - Because `url_safety.py` is the single choke point imported by all 20+ data sources, core modules, and web controllers, updating `enforce_egress_policy` to instantiate and invoke `EgressPolicy.enforce` automatically wires `EgressPolicy` into every production network caller in the system.
   - `from scp.policy.egress import EgressPolicy, EgressDeniedError, EgressDestination, EgressMode` will become a central, active import in production.

2. **Feature F14 requirements are clearly mapped**:
   - **Dev-default OPEN**: Remove lines 121-122 in `url_safety.py` and line 70 in `llm_gateway/egress_policy.py`. Unset `SCP_EGRESS_MODE` must default to `EgressMode.ALLOWLIST` (empty allowlist = fail closed, loopback only).
   - **TOCTOU DNS Rebinding**: Incorporate `_PinnedHTTPHandler` and `_PinnedHTTPSHandler` (proven in `scp/core/url_fetcher.py`) into `safe_urlopen` so the socket connects directly to the IP validated during `_is_private_ip()`, preventing DNS rebinding attacks.

3. **Specific File Changes Required**:

### Proposed Diff / Implementation Blueprint:

#### A. In `scp/policy/egress.py`:
```python
# Update EgressDeniedError signature and fields:
class EgressDeniedError(PermissionError, ValueError):
    """Raised when an outbound network request is forbidden by egress policy."""

    def __init__(self, target: str, reason: str, url: str | None = None) -> None:
        self.target = target
        self.reason = reason
        self.url = url or target
        super().__init__(f"egress denied for {self.url!r}: {reason}")

# Update EgressDestination.from_url to support Request objects:
@classmethod
def from_url(cls, url: str | Any) -> EgressDestination:
    if hasattr(url, "full_url"):
        url_str = str(url.full_url)
    else:
        url_str = str(url)
    parsed = urllib.parse.urlparse(url_str)
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").strip().strip("[]").lower().rstrip(".")
    port = parsed.port
    return cls(host=host, port=port, scheme=scheme)
```

#### B. In `scp/security/url_safety.py`:
```python
# Import unified policy engine:
from scp.policy.egress import (
    EgressDeniedError,
    EgressDestination,
    EgressMode,
    EgressPolicy,
)

# Delegate enforce_egress_policy directly:
def enforce_egress_policy(
    url: str | urllib.request.Request,
    extra_allowed_hosts: "frozenset[str] | set[str] | None" = None,
) -> None:
    """Fail-closed egress gate delegating to unified EgressPolicy."""
    url_str = url.full_url if isinstance(url, urllib.request.Request) else str(url)
    policy = EgressPolicy()
    policy.enforce(url_str, token_allowed_hosts=extra_allowed_hosts)
```

#### C. In `scp/llm_gateway/egress_policy.py`:
```python
from scp.policy.egress import EgressPolicy, EgressDeniedError

def llm_egress_allowed(base_url: str) -> bool:
    scheme, host = _hostname(base_url)
    if not host:
        return False
    if host in _LOOPBACK_HOSTS:
        return scheme in {"http", "https"}
    if scheme != "https":
        return False

    policy = EgressPolicy(allowlist=llm_egress_allowlist_hosts())
    try:
        policy.enforce(base_url)
        return True
    except EgressDeniedError:
        return False
```

#### D. In `scp/web_control/playwright_backend.py:validate_url`:
```python
from scp.security.url_safety import enforce_egress_policy, validate_url as validate_safe_url

def validate_url(self, url: str) -> str:
    ...
    enforce_egress_policy(clean_url)
    validate_safe_url(clean_url, allow_internal=self.allow_internal)
    return clean_url
```

#### E. In `scp/security/egress_static_scan.py:_FileAnalyzer._is_client_expr`:
```python
def _is_client_expr(self, sid: int | None, node: ast.AST) -> bool:
    if isinstance(node, ast.Await):
        return self._is_client_expr(sid, node.value)
    if self._is_ctor_call(node):
        return True
    ...
```

---

## 5. Verification Method

To independently verify this investigation and the upcoming implementation, execute the following commands in order:

### 5.1 Verification Commands
1. **Verify Unified Egress Policy Tests**:
   ```powershell
   pytest tests/T03_capability/test_egress_policy_unified.py -v
   ```
   *Expected*: All 11 unit tests pass.

2. **Verify LLM Egress Policy Tests**:
   ```powershell
   pytest tests/T05_gateway/test_llm_egress_policy.py -v
   ```
   *Expected*: All 8 unit tests pass.

3. **Verify Egress Enforcement Suite**:
   ```powershell
   pytest tests/T03_capability/test_egress_enforcement.py -v
   ```
   *Expected*: 45 tests pass when `assert gated >= 10` is aligned.

4. **Verify Adversarial Egress Probes**:
   ```powershell
   python tools/adversarial_goal3_probe.py
   ```
   *Expected*: All 203 probes pass, including all Probe 3 egress tests.

5. **Verify Production Callers via Grep**:
   ```powershell
   grep -rn "from scp.policy.egress import" scp/
   ```
   *Expected*: At least 3 genuine production callers found in `scp/security/url_safety.py`, `scp/llm_gateway/egress_policy.py`, `scp/capabilities/tools.py`.

6. **Verify 0 Test Collection Errors**:
   ```powershell
   pytest tests/ --collect-only -q
   ```
   *Expected*: 2,133+ tests collected, 0 collection errors.

### 5.2 Invalidation Conditions
- Any code change causing `pytest tests/T03_capability/test_egress_policy_unified.py` or `tests/T05_gateway/test_llm_egress_policy.py` to fail.
- Any change that breaks loopback connectivity (`127.0.0.1:8000`, `127.0.0.1:8081`) for internal microservices.
- Any implementation leaving `from scp.policy.egress import` without genuine callers under `scp/`.
