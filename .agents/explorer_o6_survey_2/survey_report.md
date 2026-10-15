# Technical Survey & Mapping Report: R3 & R5

**Author**: `explorer_o6_survey_2`  
**Date**: 2026-09-22T18:16:00Z  
**Project Root**: `D:\scp`  
**Target Milestone**: O6 Implementation Phase (R3: Unfixed Audit Findings & R5: Cleanup Debris and Hygiene)  

---

## 1. Executive Summary

This report delivers the technical mapping, exact file paths, line numbers, root cause mechanisms, and implementation specifications for:
- **R3: Remaining Unfixed Findings from Previous Audit** (7 distinct sub-items: Judge crash fallback & tautology, `expire_leases` OCC rowcount checks, Semantic firewall gaps, Dashboard SSRF on raw-fetch routes, Egress DNS-rebinding & dev defaults, Quorum claims in documentation, Memory multi-turn redaction gaps).
- **R5: Cleanup Debris and Hygiene** (4 distinct sub-items: `prev_ask_impl.py` and `sleeps.txt` debris removal, hardcoded fallback admin token in E2E verifier, `domain_knowledge.py` FactSeparator 2-token overlap tautology, Observability compose plaintext password and `compose.test.yml` `0.0.0.0` exposure).

Every finding was inspected against the live repository at HEAD `7344c1e`. All references, test contracts, and dependencies were mapped to enable immediate, safe implementation without regressions.

---

## 2. R3: Detailed Technical Mapping

### 2.1 Judge Crash Fallback, Answer-Contains-Answer Tautology, & Hardcoded 0.85 Threshold

#### Exact Locations
- `scp/runtime/judge.py:254–262` (sync `judge()` structural verification)
- `scp/runtime/judge.py:306–314` (sync `judge()` multi-LLM crosscheck error catch)
- `scp/runtime/judge.py:346–348` (sync `judge()` hardcoded confidence return)
- `scp/runtime/judge.py:366–374` (async `judge_async()` structural verification)
- `scp/runtime/judge.py:413–415` (async `judge_async()` crosscheck crash failover)
- `scp/runtime/judge.py:444–446` (async `judge_async()` hardcoded confidence return)

#### Mechanism & Code Observations
1. **Crash Fallback to Single Vendor**:
   - In `judge()` lines 306–314:
     ```python
     except Exception as _cc_err:
         logger.warning(
             "[M2/A2] multi-LLM crosscheck failed (%s: %s) — fallback to single judge cascade",
             type(_cc_err).__name__,
             _cc_err,
         )
         semantic = _llm_judge(question, ai_answer, context)
     ```
   - In `judge_async()` lines 413–415:
     ```python
     except Exception as _cc_err:
         semantic = await _llm_judge_async(question, ai_answer, context)
     ```
   - If `cross_verify()` raises an exception (network failure, timeout, provider crash), execution falls back to `_llm_judge` (single vendor). If `_llm_judge` returns `True`, line 320 / line 422 sets `is_pass = True`.
   - The returned verdict at lines 345–349 and 443–447 reports:
     `"verdict": "PASS"`, `"confidence": 0.85`, `"cross_model_agreement": not escalated` (which is `True`!), and `"failures": []`.
   - **Flaw**: The result is NOT flagged as degraded, and `cross_model_agreement` falsely reports `True` even though crosscheck crashed and only a single vendor was consulted.
2. **Answer-Contains-Answer Tautology**:
   - In `judge()` lines 254–262 and `judge_async()` lines 366–374:
     ```python
     if ai_answer:
         postcondition = PostconditionSchema.for_text_answer(ai_answer, evidence_required=False).to_dict()
     else:
         postcondition = PostconditionSchema.no_conditions().to_dict()

     obs = {"evidence_ref": ai_answer, "text": ai_answer}
     result = self.verifier.verify(postcondition, obs)
     is_structurally_pass = (result.verdict == "VERIFIED")
     ```
   - `PostconditionSchema.for_text_answer(expected_answer)` (`scp/core/postcondition_schema.py:100–113`) builds `conditions=[PostconditionCondition(kind="text_contains", value=expected_answer[:500])]`.
   - The verifier compares `obs["text"]` (`ai_answer`) against `condition.value` (`ai_answer[:500]`).
   - Testing whether `ai_answer` contains `ai_answer[:500]` is an **answer-contains-answer tautology**. Any non-empty string trivially passes structural verification, providing zero validation of question alignment or actual answer validity.
3. **Hardcoded 0.85 Threshold**:
   - Lines 346–348 and 444–446 hardcode:
     `"confidence": 0.85 if is_pass else 0.0`
     `"semantic_confidence": 0.85 if is_pass else 0.0`
   - Regardless of whether two distinct providers agreed with 1.0 confidence, or fallback occurred on a degraded single vendor, or whether consensus was weak, the confidence is an arbitrary constant `0.85`.

#### Implementation Recommendations
- When catching `_cc_err`:
  - Set a `degraded = True` flag and record `failures.append("crosscheck_degraded_single_vendor")`.
  - In return dict: include `"degraded": True` (or `"cross_model_agreement": False` when fallback occurred), and clamp confidence (e.g. `confidence: 0.60` instead of `0.85` when degraded).
- Fix structural check:
  - Base structural validation should verify that `ai_answer` is a non-empty string, passes basic length/format criteria, or validates against task postconditions when provided in `kwargs`, rather than synthesizing a `for_text_answer(ai_answer)` tautology.
- Derive confidence dynamically or reflect agreement level (0.85 for full multi-model consensus, degraded score for single-model fallback).

---

### 2.2 `expire_leases` OCC Rowcount Checks on 4 Branches

#### Exact Location
- `scp/task_kernel_parts/taskkernel.py:805–850` (method `TaskKernel.expire_leases`)
- Re-exported via `scp/task_kernel.py:143`

#### Mechanism & Code Observations
In `expire_leases`:
```python
810:  for lease in self.conn.execute('SELECT * FROM leases WHERE released=0 AND expires_at<=?', (now,)).fetchall():
811:      expired.append(lease['lease_id'])
812:      task = self._task(lease['task_id'])
813:      cur_state = task['state']
814:      if cur_state in {'LEASED', 'RUNNING', 'WAITING_TOOL'}:
815:          old = cur_state
816:          cur = self.conn.execute("UPDATE tasks SET state='RECOVERING',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task['task_id'], task['version']))
817:          self._append_event(...)
818:      elif cur_state == 'VERIFYING':
819:          if self.autonomous_mode:
820:              cur = self.conn.execute(
821:                  "UPDATE tasks SET state='FAILED',error=?,version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
822:                  ("verification_lease_expired", now_iso(), task['task_id'], task['version']),
823:              )
824:              self._append_event(...)
825:          else:
826:              cur = self.conn.execute("UPDATE tasks SET state='HUMAN_REVIEW',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task['task_id'], task['version']))
827:              self._append_event(...)
828:      elif cur_state == 'CHECKPOINTED':
829:          cur = self.conn.execute("UPDATE tasks SET state='QUEUED',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task['task_id'], task['version']))
830:          self._append_event(...)
831:      elif task['active_lease_id'] == lease['lease_id']:
832:          self.conn.execute("UPDATE tasks SET active_lease_id=NULL,active_fencing_token=0,version=version+1,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task['task_id'], task['version']))
833:      self.conn.execute('UPDATE leases SET released=1,version=version+1 WHERE lease_id=? AND released=0', (lease['lease_id'],))
```

#### Flaw Analysis
1. **Branch 1** (`cur_state in {'LEASED', 'RUNNING', 'WAITING_TOOL'}`): line 816 updates `tasks` where `task_id=? AND version=?`. If a concurrent worker transitioned or heartbeat the task, `cur.rowcount` is 0. The rowcount is NEVER checked, yet `_append_event` is executed with phantom state `RECOVERING`.
2. **Branch 2** (`cur_state == 'VERIFYING'`):
   - Autonomous: line 820 updates `tasks` without checking `cur.rowcount == 1`.
   - Human review: line 834 updates `tasks` without checking `cur.rowcount == 1`.
3. **Branch 3** (`cur_state == 'CHECKPOINTED'`): line 837 updates `tasks` without checking `cur.rowcount == 1`.
4. **Branch 4** (`elif task['active_lease_id'] == lease['lease_id']`): line 840 does not even capture the cursor `cur`, and does not check rowcount.
5. **Lease release UPDATE**: line 841 executes `UPDATE leases ... WHERE lease_id=? AND released=0` without checking rowcount. If the lease was released concurrently, rowcount is 0.

#### Implementation Recommendations
Follow the established pattern in `TaskKernel` (e.g. lines 694–700, 1381–1385):
```python
if cur.rowcount != 1:
    raise OptimisticLockError(
        f"concurrency conflict expiring lease {lease['lease_id']} on task {task['task_id']}: expected version {task['version']}",
        table="tasks",
        entity_id=task['task_id'],
        expected_version=int(task['version']),
    )
```
Apply this check to all 4 task update branches and the lease release update.

---

### 2.3 Semantic Firewall Gaps (GitHub-desc & Wikipedia Snippet Bypass)

#### Exact Locations
- `scp/core/top_systems_learning.py:253–266` (method `_fetch_github`)
- `scp/core/top_systems_learning.py:311–324` (method `_fetch_wikipedia`)
- `scp/core/top_systems_learning.py:434–436` (method `advise`)

#### Mechanism & Code Observations
1. In `_fetch_github_readme` (lines 284–291), untrusted content is strictly vetted:
   ```python
   quarantined, reason = inspect_untrusted(content)
   return {
       "source": "github_readme",
       "trust": "QUARANTINED" if quarantined else "untrusted",
       "quarantine_reason": reason,
       ...
   }
   ```
2. However, in `_fetch_github` (lines 253–266):
   ```python
   for item in data.get("items", [])[: per_source]:
       out.append(
           {
               "source": "github",
               "kind": "repository",
               "name": str(item.get("full_name", ""))[:200],
               "url": str(item.get("html_url", ""))[:300],
               "stars": int(item.get("stargazers_count", 0)),
               "forks": int(item.get("forks_count", 0)),
               "description": str(item.get("description") or "")[:400],
               "reputation": reputation_from_stars(int(item.get("stargazers_count", 0))),
           }
       )
   ```
   Notice: `item.get("description")` and `name` are NOT inspected via `inspect_untrusted()`. There is NO `"trust"` field assigned.
3. In `_fetch_wikipedia` (lines 311–324):
   ```python
   title = str(item.get("title", ""))
   snippet = _TAG_RE.sub("", str(item.get("snippet", "")))
   out.append(
       {
           "source": "wikipedia",
           "kind": "article",
           "name": title[:200],
           "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
           "description": snippet[:400],
           "reputation": "medium",
       }
   )
   ```
   Notice: `snippet` and `title` are NOT inspected via `inspect_untrusted()`. There is NO `"trust"` field assigned.
4. In `advise()` (lines 434–436):
   ```python
   # [C1] Record bị cách ly KHÔNG BAO GIỜ được serve vào prompt.
   if record.get("trust") == "QUARANTINED":
       continue
   ```
   Because `record.get("trust")` is `None` (not `"QUARANTINED"`), any prompt injection embedded in a GitHub repo description or Wikipedia snippet completely bypasses the Semantic Firewall and is returned by `advise()` to prompt builders!

#### Implementation Recommendations
In `_fetch_github` and `_fetch_wikipedia`:
- Call `quarantined, reason = inspect_untrusted(description + " " + name)` (or snippet + title).
- Populate:
  ```python
  "trust": "QUARANTINED" if quarantined else "untrusted",
  "quarantine_reason": reason,
  "content_sha256": "sha256:" + hashlib.sha256((name + description).encode("utf-8")).hexdigest()[:32],
  ```

---

### 2.4 Dashboard SSRF on Remaining Raw-Fetch Routes

#### Exact Locations
1. `dashboard/src/app/api/scp/status/route.ts:44–45, 220`
   - `const SCP_BASE_URL = process.env.SCP_INTERNAL_URL ?? "http://127.0.0.1:8000"`
   - `const res = await fetch(`${SCP_BASE_URL}/health`, ...)`
2. `dashboard/src/app/api/scanners/route.ts:20–21, 40`
   - `const SCP_BACKEND_URL = process.env.SCP_INTERNAL_URL ?? "http://127.0.0.1:8000"`
   - `const resp = await fetch(`${SCP_BACKEND_URL}/v105/scanners`, ...)`
3. `dashboard/src/app/api/scp/loop/route.ts:22–23, 30`
   - `const SCHEDULER_URL = process.env.LOOP_SCHEDULER_URL ?? "http://127.0.0.1:3030"`
   - `const res = await fetch(`${SCHEDULER_URL}/`, ...)`
4. `dashboard/src/app/api/scp/loop/trigger/route.ts:40–41, 110`
   - `const SCHEDULER_URL = process.env.LOOP_SCHEDULER_URL ?? "http://127.0.0.1:3030"`
   - `const res = await fetch(`${SCHEDULER_URL}/trigger`, ...)`
5. `dashboard/src/app/api/autofix/route.ts:30–31, 62`
   - `const SCP_BACKEND_URL = process.env.SCP_INTERNAL_URL ?? "http://127.0.0.1:8000"`
   - `const resp = await fetch(`${SCP_BACKEND_URL}/v105/autofix/stats`, ...)`

#### Existing PEP & Allowlist Infrastructure
In `dashboard/src/lib/scp-backend-url.ts` and `dashboard/src/lib/probe-allowlist.ts`:
- `isAllowedProbeTarget(url, extraHosts)` validates scheme (http/https only) and host (must be loopback, RFC1918 private, `.docker.internal`, or explicitly in `extraHosts`).
- `resolveScpApiBase()` and `resolveScpProxyBase()` validate environment URLs before returning them to callers.
- In `dashboard/src/app/api/scp/health/route.ts:74–81`, probe targets are validated via `isAllowedProbeTarget(url, extraHosts)` before calling `fetch()`.

#### Implementation Recommendations
- Export `resolveInternalBackendBase()` and `resolveLoopSchedulerBase()` from `dashboard/src/lib/scp-backend-url.ts` using `resolveBackendBase()`.
- In `status/route.ts`, `scanners/route.ts`, `autofix/route.ts`: replace raw `process.env.SCP_INTERNAL_URL` with `resolveInternalBackendBase()`.
- In `loop/route.ts` and `loop/trigger/route.ts`: replace raw `process.env.LOOP_SCHEDULER_URL` with `resolveLoopSchedulerBase()`.

---

### 2.5 Egress DNS-Rebinding & Dev Defaults

#### Exact Locations
- `scp/policy/egress.py:59–76, 86–90, 113–156`
- `scp/security/url_safety.py:120–122, 152–180, 213–220`
- `scp/llm_gateway/egress_policy.py:65–72`

#### Mechanism & Code Observations
1. **Dev Defaults Bypassing Egress**:
   - In `scp/security/url_safety.py:120–122`:
     ```python
     mode = os.environ.get("SCP_EGRESS_MODE", "").strip().lower()
     if not mode and not _production_mode_declared():
         return  # dev default: no restriction beyond the SSRF checks
     ```
   - In `scp/llm_gateway/egress_policy.py:70–71`:
     ```python
     if mode == "":
         return True
     ```
   - In `scp/policy/egress.py:154`:
     ```python
     if self.production_mode and self.mode not in {EgressMode.DENY, EgressMode.ALLOWLIST}:
         raise EgressDeniedError(dest.host, "Production mode requires explicit deny or allowlist egress policy")
     ```
     When `production_mode == False` and `mode == EgressMode.OPEN`, requests are unconditionally permitted without any allowlist check.
2. **DNS-Rebinding (TOCTOU) Gaps**:
   - In `scp/security/url_safety.py`:
     `validate_url(url_str)` calls `_is_private_ip(parsed.hostname)`, which runs `socket.getaddrinfo(host, None)`.
     Then `safe_urlopen()` calls `urllib.request.urlopen(url)`.
     `urlopen()` triggers a *second*, independent DNS lookup. If the attacker configures a DNS server with TTL=0 returning a public IP on the first query and `127.0.0.1` or `169.254.169.254` on the second query, the connection succeeds against private infrastructure.
   - In `scp/policy/egress.py`:
     `EgressPolicy.enforce()` does NOT resolve hostnames at all. It only checks `ipaddress.ip_address(norm_host)`. If `norm_host` is `evil.com` pointing to `127.0.0.1`, `ipaddress.ip_address` raises `ValueError`, so `is_loopback` and `is_cloud_metadata` return `False`.

#### Implementation Recommendations
- Dev default: Require `allowlist` or `deny` as safe defaults or enforce fail-closed on unknown external hosts unless explicitly configured.
- DNS-rebinding: In `url_safety.py`, ensure the socket connects to the pre-resolved IP, or verify resolved IP against egress policy and private ranges; or pin IP address during HTTP request handling.

---

### 2.6 Quorum Claims in Documentation vs Removed Feature

#### Exact Locations
- `docs/SCP_ARCHITECTURE.md:60` ("| 10 | Quorum WHY cho action nguy hiểm | `scp/security/quorum_why.py` (125 LOC) |")
- `docs/SCP_ARCHITECTURE.md:121` ("| `scp/security/quorum_why.py` | 125 | Hội đồng WHY cho action nguy hiểm |")
- `tools/stress_p1_concurrency.py:70` (`"scp.security.quorum_why"`)
- `docs/SCP_HARDENING_20260829.md:91`
- `BAO_CAO_KIEM_TOAN_TOAN_HE_THONG.md:130`

#### Verification
- Checked file existence: `Test-Path D:\scp\scp\security\quorum_why.py` returns `False`. The file was completely removed.
- `SCP_ARCHITECTURE.md` still lists Step 10 in the core pipeline table and in the component inventory table as an active security ring.
- `tools/stress_p1_concurrency.py:70` lists `scp.security.quorum_why` in the imported modules list, risking `ImportError`.

#### Implementation Recommendations
- Update `docs/SCP_ARCHITECTURE.md`:
  - Replace Step 10 with the actual active gate: `why_gate.py` (`scp/meta/why_gate.py`) or remove step 10 and renumber pipeline.
  - Remove `scp/security/quorum_why.py` row from table at line 121.
- Remove `"scp.security.quorum_why"` from `tools/stress_p1_concurrency.py:70`.

---

### 2.7 Memory Multi-Turn Redaction Gaps

#### Exact Location
- `scp/core/chat_memory_store.py:96–101` (`_SECRET_PATTERNS`)

#### Mechanism & Code Observations
`ChatMemoryStore` defines `_SECRET_PATTERNS` as:
```python
_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:openrouter_api_key|scp_auth_password|scp_auth_token_secret|api[_ -]?key|password|token|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----.*?-----END [A-Z ]+ PRIVATE KEY-----"),
)
```
Missing token patterns:
1. **JWT Tokens**: `r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"`. If a raw JWT token is pasted without `"Bearer "` or `"token:="`, it is written in plaintext to `data/chat_memory.jsonl`.
2. **GitHub Personal Access Tokens**: `r"\bghp_[A-Za-z0-9]{30,}\b"` and fine-grained `github_pat_...`.
3. **AWS Access Keys**: `r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"`.
4. **Google API Keys**: `r"\bAIza[0-9A-Za-z_\-]{30,}\b"`.

#### Implementation Recommendations
Add the missing compiled regexes to `ChatMemoryStore._SECRET_PATTERNS`:
```python
re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),
re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"),
```

---

## 3. R5: Detailed Technical Mapping

### 3.1 `prev_ask_impl.py` and `sleeps.txt`

#### Exact Locations
- `D:\scp\prev_ask_impl.py` (877 lines, 49,732 bytes)
- `D:\scp\sleeps.txt` (40 lines, 3,158 bytes)

#### Reference & Safety Check
- Executed whole-repo grep search for `prev_ask_impl`: **0 references**.
- Executed whole-repo grep search for `sleeps.txt`: **0 references**.
- `prev_ask_impl.py` is an old backup of `api_server_parts/_ask_impl.py` accidentally committed at repository root.
- `sleeps.txt` is an ad-hoc grep dump of `time.sleep` calls.
- **Action**: Safely remove both files via `git rm`.

---

### 3.2 Hardcoded Fallback Admin Token in `e2e_live_cluster_verifier.py:100`

#### Exact Location
- `tools/e2e_live_cluster_verifier.py:96–101`

#### Mechanism & Code Observations
```python
def load_env_token() -> str:
    ...
    return (
        os.environ.get("SCP_AUTH_TOKEN_SECRET")
        or os.environ.get("SCP_ADMIN_KEY")
        or os.environ.get("SCP_AUTH_PASSWORD")
        or "scp-v3-68fcc2ae7dac74cc436decf214cae8cc"
    )
```
Line 100 contains a hardcoded fallback token `"scp-v3-68fcc2ae7dac74cc436decf214cae8cc"`.
Lines 112–113 assign this token to `SCP_AUTH_TOKEN_SECRET` and `SCP_ADMIN_KEY` for spawning cluster services.
If the verifier is run in an environment without `.env`, the cluster runs with publicly known admin credentials.

#### Implementation Recommendations
Import `secrets` and generate a dynamic token:
```python
import secrets
...
return (
    os.environ.get("SCP_AUTH_TOKEN_SECRET")
    or os.environ.get("SCP_ADMIN_KEY")
    or os.environ.get("SCP_AUTH_PASSWORD")
    or f"scp-e2e-{secrets.token_hex(16)}"
)
```

---

### 3.3 `domain_knowledge.py` FactSeparator 2-Token Overlap Tautology

#### Exact Locations
- `scp/knowledge/domain_knowledge.py:444–446`
- `scp/knowledge/domain_knowledge.py:526–532` (method `_is_match`)

#### Mechanism & Code Observations
1. In `_is_match(claim, text)` (lines 526–532):
   ```python
   c_tokens = {w.lower() for w in claim.text.split() if len(w) > 2}
   t_tokens = {w.lower() for w in text.split() if len(w) > 2}
   if c_tokens and t_tokens:
       overlap = c_tokens & t_tokens
       if len(overlap) >= 2 or (len(overlap) / len(c_tokens)) >= 0.5:
           return True
   ```
2. In `separate()` (lines 444–446):
   ```python
   s_tokens = {w.lower() for w in sentence.split() if len(w) > 2}
   snip_tokens = {w.lower() for w in snippet.split() if len(w) > 2}
   if s_tokens and snip_tokens and (len(s_tokens & snip_tokens) >= 2 or len(s_tokens & snip_tokens) / len(s_tokens) >= 0.4):
       verified_facts.append(VerifiedFact(claim=sentence, ..., confidence=0.92 if src == "knowledge_base" else 0.85))
   ```
3. Any sentence sharing just TWO arbitrary words longer than 2 characters (which includes common filler words like "the", "and", "for", "cho", "với", "các") is stamped as a `VerifiedFact` with 85%–92% confidence and awarded the `FACT_VERIFIED` badge with transparency note: *"All claims backed by authoritative sources."*

#### Implementation Recommendations
- Introduce stop-word filtering (English and Vietnamese common stop words).
- Require substantial overlap: minimum of 4 non-stop content lemmas/tokens or Jaccard similarity >= 0.6.
- Require entity and target matching when structured claims are present.

---

### 3.4 Observability Compose Password & `compose.test.yml` 0.0.0.0 Binding

#### Exact Locations
- `docker-compose.observability.yml:9–10, 18, 24, 31, 38`
- `compose.test.yml:11`
- Reference comparison: `compose.yml:60, 101` (correctly binds `127.0.0.1:8000:8000` and `127.0.0.1:3030:3030`)

#### Mechanism & Code Observations
1. `docker-compose.observability.yml`:
   - Line 24: `- GF_SECURITY_ADMIN_PASSWORD=scp_admin` — hardcoded default credentials committed to repository.
   - Lines 9, 10, 18, 31, 38: ports `"4317:4317"`, `"4318:4318"`, `"9090:9090"`, `"3000:3000"`, `"3100:3100"` have no IP prefix, binding to `0.0.0.0` (all host network interfaces).
2. `compose.test.yml`:
   - Line 11: `ports: - "8080:8000"` binds port 8080 to `0.0.0.0`. Anyone on the local network can access the test backend during test runs.

#### Implementation Recommendations
1. In `docker-compose.observability.yml`:
   - Use environment interpolation: `- GF_SECURITY_ADMIN_PASSWORD=${GF_SECURITY_ADMIN_PASSWORD:-}` (or document requirement in `.env.example`).
   - Prefix all exposed ports with loopback:
     `"127.0.0.1:4317:4317"`, `"127.0.0.1:4318:4318"`, `"127.0.0.1:9090:9090"`, `"127.0.0.1:3000:3000"`, `"127.0.0.1:3100:3100"`.
2. In `compose.test.yml`:
   - Update line 11 to: `- "127.0.0.1:8080:8000"`.

---

## 4. Dependencies, Risks, and Implementation Sequence

| Priority | Task ID | File Targets | Downstream Risk | Implementation Notes |
|:---|:---|:---|:---|:---|
| P0 | R5.1 | `prev_ask_impl.py`, `sleeps.txt` | None (0 refs) | `git rm` both files. |
| P0 | R5.2 | `tools/e2e_live_cluster_verifier.py` | None | Replace static token with dynamic `secrets.token_hex(16)`. |
| P1 | R3.6 | `docs/SCP_ARCHITECTURE.md`, `tools/stress_p1_concurrency.py` | None | Remove quorum references; update architecture doc with active why_gate. |
| P1 | R5.4 | `docker-compose.observability.yml`, `compose.test.yml` | None | Change port bindings to `127.0.0.1:*` and interpolate password. |
| P1 | R3.7 | `scp/core/chat_memory_store.py` | Low | Add JWT, ghp_, AKIA, AIza regexes. Verified existing test suite passes. |
| P1 | R3.3 | `scp/core/top_systems_learning.py` | Low | Add `inspect_untrusted` to `_fetch_github` and `_fetch_wikipedia`. |
| P1 | R3.4 | `dashboard/src/app/api/...`, `dashboard/src/lib/scp-backend-url.ts` | Low | Wire `resolveBackendBase` across status, scanners, loop, trigger, autofix routes. |
| P2 | R3.2 | `scp/task_kernel_parts/taskkernel.py` | Medium | Add `cur.rowcount != 1` OCC checks to 4 branches in `expire_leases`. Ensure tests using watchdog handle `OptimisticLockError`. |
| P2 | R5.3 | `scp/knowledge/domain_knowledge.py` | Low | Upgrade token overlap from 2-word tautology to content lemma overlap + stopword filtering. |
| P2 | R3.1 | `scp/runtime/judge.py` | Medium | Set degraded flag on crosscheck crash; remove answer-contains-answer tautology; derive confidence. |
| P2 | R3.5 | `scp/policy/egress.py`, `url_safety.py` | Medium | Tighten dev defaults and prevent TOCTOU DNS-rebinding. |

### 4.1 Meta-Audit & Test Integrity Considerations
During test execution verification, running `python tools/t00_meta_audit.py` revealed:
- `t00_meta_audit.py` checks candidate branches against baseline debt.
- In `tests/internal/external_audit/test_security.py:116, 151, 156`, `pytest.skip()` calls for missing bandit or missing `SCP_AUTH_TOKEN_SECRET` are detected as new skips (FA-01) if bandit or the environment variable is not present during test execution. Workers modifying tests or cleaning up debris must ensure no new `pytest.skip` or `pytest.xfail` marks are introduced, and running tests in environments where bandit is present avoids triggering FA-01.

---
*End of Technical Survey Report.*
