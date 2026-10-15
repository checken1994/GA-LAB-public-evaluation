# BRIEFING — 2026-09-22T19:57:00Z

## Mission
Investigate Feature F08 & F14: Wiring EgressPolicy into production runtime via url_safety.py and runtime network callers, resolving dev-default open & TOCTOU DNS rebinding, and verifying test impacts.

## 🔒 My Identity
- Archetype: explorer
- Roles: explorer, investigator, synthesizer
- Working directory: D:\scp\.agents\explorer_m2_2
- Original parent: 81004ee7-0162-4442-9168-937ecae6dd34
- Milestone: M2

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Fail-Closed & Evidence-First principles
- Do not modify source code (except within .agents/explorer_m2_2/)

## Current Parent
- Conversation ID: 81004ee7-0162-4442-9168-937ecae6dd34
- Updated: 2026-09-22T19:57:00Z

## Investigation State
- **Explored paths**:
  - `scp/policy/egress.py` (Unified EgressPolicy engine, EgressMode, EgressDeniedError, EgressDestination)
  - `scp/security/url_safety.py` (Choke point with standalone duplicate enforce_egress_policy and safe_urlopen)
  - `scp/llm_gateway/egress_policy.py` & `scp/llm_gateway/client.py` (Duplicate LLM egress checks)
  - `scp/web_control/browser_session.py` & `scp/web_control/playwright_backend.py` (Browser egress paths)
  - `scp/core/url_fetcher.py` (Canonical safe fetcher with DNS IP-pinned connection pattern)
  - `scp/security/egress_static_scan.py` & `tests/T03_capability/test_egress_enforcement.py` (Static gate and test suite)
  - `tests/T03_capability/test_egress_policy_unified.py` & `tests/T05_gateway/test_llm_egress_policy.py`
  - `tools/adversarial_goal3_probe.py` (Probe 3: 203 probes passed)
- **Key findings**:
  1. `scp/policy/egress.py` is fully functional with wildcard domain support and cloud metadata blocking, but currently only imported by a probe, a test, and an unused import in `tools.py`.
  2. `scp/security/url_safety.py:enforce_egress_policy` implements its own duplicate logic and does NOT import or delegate to `EgressPolicy`. Delegating it immediately wires all 20+ runtime network callers into `EgressPolicy`.
  3. `scp/llm_gateway/egress_policy.py` and `scp/llm_gateway/client.py` have two additional redundant copies of LLM egress policy which should be unified under `EgressPolicy`.
  4. `PlaywrightBackend` in `playwright_backend.py:validate_url` calls `validate_safe_url` but omits `enforce_egress_policy`.
  5. `safe_urlopen` in `url_safety.py` suffers from TOCTOU DNS rebinding because it validates via `_is_private_ip()` and then calls `urllib.request.urlopen` which re-resolves DNS. In contrast, `scp/core/url_fetcher.py` already implements `_PinnedHTTPHandler`/`_PinnedHTTPSHandler` which pins the validated IP. Migrating this pattern to `safe_urlopen` eliminates the TOCTOU window.
  6. Dev-default OPEN exists in `url_safety.py:121-122` (returns if mode unset and not in production) and `llm_gateway/egress_policy.py:70`. For F14, unset mode must default to `allowlist` (with empty list = fail-closed external, loopback only).
  7. In `test_egress_enforcement.py`, `assert gated >= 12` fails (finds 9) because 2 files were deleted (`scheduled_crawler.py` and `threat_intel.py`) and `egress_static_scan.py:_is_client_expr` does not inspect `ast.Await(value)` for `client = await self._get_client()` in `client.py:423`. Adding `ast.Await` detection raises tracked sites to 10 (all 10 verified gated).
  8. `EgressDeniedError` in `scp/policy/egress.py` must define `self.url = target` and match message format for full test compatibility.
- **Unexplored areas**: None within the scope of F08 and F14.

## Key Decisions Made
- Mapped out the exact drop-in wiring for `url_safety.py -> EgressPolicy`.
- Identified the exact TOCTOU mitigation reusing `_PinnedHTTPHandler` pattern.
- Formulated the exact test fixes and verification commands for M2 and M3.

## Artifact Index
- D:\scp\.agents\explorer_m2_2\DISPATCH.md — Incoming task instructions
- D:\scp\.agents\explorer_m2_2\BRIEFING.md — Persistent working memory
- D:\scp\.agents\explorer_m2_2\progress.md — Liveness heartbeat
- D:\scp\.agents\explorer_m2_2\handoff.md — Final handoff report
