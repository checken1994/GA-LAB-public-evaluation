# Handoff Report: Milestone M3 Investigation (Features F10, F11, F12, F13, F15, F16)

**Agent**: `explorer_m3_1`  
**Working Directory**: `D:\scp\.agents\explorer_m3_1`  
**Recipient**: `orchestrator_7` (ID: `81004ee7-0162-4442-9168-937ecae6dd34`)  
**Type**: Hard Handoff (Investigation Complete)  
**Date**: 2026-09-22T20:15:00Z  

---

## 1. Observation

All observations were verified directly against the live repository at `D:\scp` using `view_file`, `grep_search`, and test runners:

### 1.1 F10: Judge Crosscheck Crash Fallback & Answer-Contains-Answer Tautology (`scp/runtime/judge.py`)
- **File**: `scp/runtime/judge.py`
- **Sync `judge()` fallback**:
  - Lines 306–314:
    ```python
    except Exception as _cc_err:
        logger.warning(
            "[M2/A2] multi-LLM crosscheck failed (%s: %s) — fallback to single judge cascade",
            type(_cc_err).__name__,
            _cc_err,
        )
        semantic = _llm_judge(question, ai_answer, context)
    ```
- **Async `judge_async()` fallback**:
  - Lines 413–415:
    ```python
    except Exception as _cc_err:
        semantic = await _llm_judge_async(question, ai_answer, context)
    ```
- **Verdict return metadata** (Lines 344–360 and 442–455):
  - Both methods return:
    ```python
    "verdict": "PASS" if is_pass else "FAIL",
    "confidence": 0.85 if is_pass else 0.0,
    "deterministic_confidence": 1.0 if is_structurally_pass else 0.0,
    "semantic_confidence": 0.85 if is_pass else 0.0,
    "cross_model_agreement": not escalated,
    "reasoning": "Delegated to IndependentVerifier and LLM Semantic Judge",
    ```
  - When crosscheck crashes, `semantic` is determined by single-vendor `_llm_judge`. If that passes, `is_pass = True`, `escalated = False`. The returned dict reports `"cross_model_agreement": True`, confidence `0.85`, and contains no `degraded` flag indicating single-vendor fallback occurred.
- **Answer-contains-answer tautology**:
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
  - In `scp/core/postcondition_schema.py:100–113`, `PostconditionSchema.for_text_answer(expected_answer)` constructs condition `PostconditionCondition(kind="text_contains", value=expected_answer[:500])`.
  - In `scp/verifier.py:47–50`, `IndependentVerifier` checks:
    ```python
    elif kind == "text_contains":
        expected = condition.get("value")
        actual = observation.get("text") or ""
        ok = bool(expected and expected in actual)
    ```
  - Passing `expected = ai_answer[:500]` and `actual = ai_answer` evaluates `ai_answer[:500] in ai_answer`, which is vacuously `True` for any non-empty answer. It tests if the answer contains itself.

---

### 1.2 F11: `expire_leases` OCC Rowcount Checks across 4 Branches (`scp/task_kernel_parts/taskkernel.py`)
- **File**: `scp/task_kernel_parts/taskkernel.py`, lines 805–850:
  ```python
  810: for lease in self.conn.execute('SELECT * FROM leases WHERE released=0 AND expires_at<=?', (now,)).fetchall():
  811:     expired.append(lease['lease_id'])
  812:     task = self._task(lease['task_id'])
  813:     cur_state = task['state']
  814:     if cur_state in {'LEASED', 'RUNNING', 'WAITING_TOOL'}:
  815:         old = cur_state
  816:         cur = self.conn.execute("UPDATE tasks SET state='RECOVERING',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task['task_id'], task['version']))
  817:         self._append_event(task['task_id'], 'LEASE_EXPIRED', old, 'RECOVERING', 'kernel', 'heartbeat_expired', {'lease_id': lease['lease_id']})
  818:     elif cur_state == 'VERIFYING':
  819:         if self.autonomous_mode:
  820:             cur = self.conn.execute(
  821:                 "UPDATE tasks SET state='FAILED',error=?,version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
  822:                 ("verification_lease_expired", now_iso(), task['task_id'], task['version']),
  823:             )
  824:             self._append_event(...)
  825:         else:
  826:             cur = self.conn.execute("UPDATE tasks SET state='HUMAN_REVIEW',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task['task_id'], task['version']))
  827:             self._append_event(...)
  828:     elif cur_state == 'CHECKPOINTED':
  829:         cur = self.conn.execute("UPDATE tasks SET state='QUEUED',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task['task_id'], task['version']))
  830:         self._append_event(...)
  831:     elif task['active_lease_id'] == lease['lease_id']:
  832:         self.conn.execute("UPDATE tasks SET active_lease_id=NULL,active_fencing_token=0,version=version+1,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task['task_id'], task['version']))
  833:     self.conn.execute('UPDATE leases SET released=1,version=version+1 WHERE lease_id=? AND released=0', (lease['lease_id'],))
  ```
- **OCC checks missing**:
  - Branch 1 (line 816): `cur.rowcount` is not checked.
  - Branch 2 (lines 820, 826): `cur.rowcount` is not checked in either autonomous or human review mode.
  - Branch 3 (line 829): `cur.rowcount` is not checked.
  - Branch 4 (line 832): cursor is not even assigned, `cur.rowcount` is not checked.
  - Lease release (line 833): cursor is not assigned, `cur.rowcount` is not checked.
  - In contrast, lines 876–883 in `release()` rigorously check `cur.rowcount != 1` and raise `OptimisticLockError`.

---

### 1.3 F12: Semantic Firewall Ingestion Gaps (`scp/core/top_systems_learning.py`)
- **File**: `scp/core/top_systems_learning.py`
- In `_fetch_github` (lines 253–266):
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
  Neither `name` nor `description` is vetted via `inspect_untrusted()`. No `"trust"`, `"quarantine_reason"`, or `"content_sha256"` field is populated.
- In `_fetch_wikipedia` (lines 311–324):
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
  Neither `title` nor `snippet` is vetted via `inspect_untrusted()`. No `"trust"`, `"quarantine_reason"`, or `"content_sha256"` field is populated.
- In `advise()` (lines 434–436):
  ```python
  if record.get("trust") == "QUARANTINED":
      continue
  ```
  Because `record.get("trust")` is `None` for GitHub and Wikipedia entries, any prompt injection in external repository descriptions or Wikipedia snippets bypasses the filter and is returned directly to prompt builders.

---

### 1.4 F13: Dashboard SSRF on Remaining Raw-Fetch Routes
- Five dashboard routes perform raw `fetch()` on environment variables without passing through `resolveBackendBase()` or `isAllowedProbeTarget()`:
  1. `dashboard/src/app/api/scp/status/route.ts:44–45, 220`:
     `const SCP_BASE_URL = process.env.SCP_INTERNAL_URL ?? "http://127.0.0.1:8000"`
     `fetch(`${SCP_BASE_URL}/health`, ...)`
  2. `dashboard/src/app/api/scanners/route.ts:20–21, 40`:
     `const SCP_BACKEND_URL = process.env.SCP_INTERNAL_URL ?? "http://127.0.0.1:8000"`
     `fetch(`${SCP_BACKEND_URL}/v105/scanners`, ...)`
  3. `dashboard/src/app/api/scp/loop/route.ts:22–23, 30`:
     `const SCHEDULER_URL = process.env.LOOP_SCHEDULER_URL ?? "http://127.0.0.1:3030"`
     `fetch(`${SCHEDULER_URL}/`, ...)`
  4. `dashboard/src/app/api/scp/loop/trigger/route.ts:40–41, 110`:
     `const SCHEDULER_URL = process.env.LOOP_SCHEDULER_URL ?? "http://127.0.0.1:3030"`
     `fetch(`${SCHEDULER_URL}/trigger`, ...)`
  5. `dashboard/src/app/api/autofix/route.ts:30–31, 62`:
     `const SCP_BACKEND_URL = process.env.SCP_INTERNAL_URL ?? "http://127.0.0.1:8000"`
     `fetch(`${SCP_BACKEND_URL}/v105/autofix/stats`, ...)`
- In contrast, `dashboard/src/lib/scp-backend-url.ts` defines `resolveBackendBase` and `isAllowedProbeTarget(url, extraHosts)` (from `./probe-allowlist`), which blocks any non-loopback, non-private, or cloud-metadata URLs.

---

### 1.5 F15: Quorum Removal in Documentation & Stale Test Imports
- **Documentation**:
  - `docs/SCP_ARCHITECTURE.md:60`: Lists Step 10: `| 10 | Quorum WHY cho action nguy hiểm | scp/security/quorum_why.py (125 LOC) |`.
  - `docs/SCP_ARCHITECTURE.md:121`: Lists `| scp/security/quorum_why.py | 125 | Hội đồng WHY cho action nguy hiểm |`.
- **Filesystem**:
  - `Test-Path D:\scp\scp\security\quorum_why.py` returns `False`. The file was completely removed. Only an orphaned `.pyc` file exists in `scp/security/__pycache__/quorum_why.cpython-312.pyc`.
- **Stale Import in Tools**:
  - `tools/stress_p1_concurrency.py:70`:
    ```python
    "scp.security.quorum_why",
    ```
    Attempting to dynamically import this module in `stress_p1_concurrency.py` will fail with `ModuleNotFoundError`.

---

### 1.6 F16: `ChatMemoryStore._SECRET_PATTERNS` Additions (`scp/core/chat_memory_store.py`)
- **File**: `scp/core/chat_memory_store.py:96–101` (re-exported by `scp/core/chat_memory.py`):
  ```python
  _SECRET_PATTERNS = (
      re.compile(r"(?i)\b(?:openrouter_api_key|scp_auth_password|scp_auth_token_secret|api[_ -]?key|password|token|secret)\s*[:=]\s*[^\s,;]+"),
      re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b"),
      re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
      re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----.*?-----END [A-Z ]+ PRIVATE KEY-----"),
  )
  ```
- Missing token formats:
  1. Standalone JWT tokens without `Bearer`: `eyJhbGci...`
  2. GitHub Personal Access Tokens: `ghp_...`
  3. AWS Access Key IDs: `AKIA...` or `ASIA...`
  4. Google API keys: `AIza...`
- When any of these credentials appear in multi-turn conversation without a recognized prefix (e.g. `api_key=`), they are written unredacted to `data/chat_memory.jsonl`.

---

## 2. Logic Chain

1. **F10 (Judge Fallback & Tautology)**:
   - [Observation 1.1] shows that on crosscheck exception, `_llm_judge` is called as single vendor, but verdict reports `cross_model_agreement: True` and confidence `0.85`.
   - Therefore, single-vendor decisions masquerade as multi-model consensus, violating DNA #5 ("Reality over Model / Consensus != True").
   - Furthermore, `PostconditionSchema.for_text_answer(ai_answer)` checks if `ai_answer` contains `ai_answer[:500]`. Testing whether an answer contains itself provides zero validation against task requirements.
   - [Remediation]: Introduce a `degraded: bool` flag. When crosscheck fails, set `degraded = True`, record `"crosscheck_degraded_single_vendor"` in failures, set `"cross_model_agreement": (not escalated) and (not degraded)`, and adjust confidence (e.g. 0.60). For structural checks: if `postcondition` or `expected_answer` is supplied in `kwargs`, verify against it; otherwise check that `ai_answer` is non-empty and non-whitespace, recording `"empty_ai_answer"` if missing, removing the tautological self-check.

2. **F11 (`expire_leases` OCC Rowcounts)**:
   - [Observation 1.2] shows 4 branches updating `tasks` and 1 statement updating `leases` using `WHERE ... version=?`, but `cur.rowcount` is never checked.
   - If another process concurrently modified the task or renewed the lease, the UPDATE affects 0 rows.
   - Without checking `cur.rowcount == 1`, `_append_event()` records a phantom state transition (e.g. `LEASE_EXPIRED -> RECOVERING`), and transaction commits a corrupt state history.
   - [Remediation]: Check `if cur.rowcount != 1: raise OptimisticLockError(...)` across all 4 branches and the lease release query. Since `expire_leases()` runs inside a database transaction with `try/except: self._rollback()`, an `OptimisticLockError` rolls back cleanly without writing phantom events.

3. **F12 (Semantic Firewall Ingestion)**:
   - [Observation 1.3] shows `_fetch_github` and `_fetch_wikipedia` do not invoke `inspect_untrusted()` on repository descriptions or Wikipedia snippets, and `advise()` only drops records if `record.get("trust") == "QUARANTINED"`.
   - Consequently, prompt injection strings in GitHub descriptions or Wikipedia search results flow unfiltered into prompt builders.
   - [Remediation]: Call `inspect_untrusted(f"{name} {desc}")` and `inspect_untrusted(f"{title} {snippet}")` at ingestion, setting `"trust": "QUARANTINED" if quarantined else "untrusted"`, recording `"quarantine_reason"`, and computing `"content_sha256"`. This ensures malicious payloads are quarantined immediately and filtered by `advise()`.

4. **F13 (Dashboard SSRF on Raw-Fetch Routes)**:
   - [Observation 1.4] shows 5 routes construct URLs from environment variables and call `fetch()` directly without allowlist gating.
   - An attacker or misconfigured deployment providing an SSRF target (e.g. cloud metadata `http://169.254.169.254/latest/meta-data`) could trigger internal network exfiltration.
   - [Remediation]: Export `resolveInternalBackendBase()` and `resolveLoopSchedulerBase()` from `dashboard/src/lib/scp-backend-url.ts` (which validates hosts against loopback, private RFC1918, and `.docker.internal` via `isAllowedProbeTarget`), and use these helpers in the 5 route handlers within their existing `try/catch` blocks.

5. **F15 (Quorum Removal in Docs & Stale Import)**:
   - [Observation 1.5] shows `docs/SCP_ARCHITECTURE.md` claims `scp/security/quorum_why.py` exists as Step 10 and in the component inventory table, while the file was deleted. `tools/stress_p1_concurrency.py:70` still imports it.
   - Discrepancy between documentation and reality misleads audits, and importing deleted modules breaks test tools.
   - [Remediation]: Remove Step 10 and table row 121 from `docs/SCP_ARCHITECTURE.md`, and delete `"scp.security.quorum_why"` from `tools/stress_p1_concurrency.py`.

6. **F16 (ChatMemoryStore Secret Redaction)**:
   - [Observation 1.6] shows `_SECRET_PATTERNS` in `scp/core/chat_memory_store.py` lacks patterns for JWT (`eyJ...`), GitHub PATs (`ghp_...`), AWS credentials (`AKIA...`/`ASIA...`), and Google API keys (`AIza...`).
   - Plaintext credentials in multi-turn chat leak to `data/chat_memory.jsonl`.
   - [Remediation]: Add the 4 compiled regexes to `ChatMemoryStore._SECRET_PATTERNS`.

---

## 3. Caveats

- **Scope Boundary**: Feature F14 (Egress DNS-rebinding & dev default OPEN) was surveyed in `explorer_o6_survey_2`, but was explicitly reassigned to Milestone M2 (`worker_m2_1` and `explorer_m2_2`). It is therefore not part of M3 execution.
- **Single Vendor Fallback Semantics**: When multi-LLM crosscheck is explicitly disabled by setting `SCP_MULTI_LLM_CROSSCHECK=0`, this is intentional configuration rather than a crash; `degraded` should only be `True` when multi-LLM crosscheck was enabled/expected but failed during execution.
- **OCC Concurrency Under Load**: Adding `OptimisticLockError` in `expire_leases()` causes concurrent lease expiry races to raise and rollback. Callers of `expire_leases` (such as background watchdog threads) already wrap the call in `try...except Exception: pass`, which gracefully handles OCC conflicts.

---

## 4. Conclusion & Concrete Implementation Blueprints

All 6 features have been fully investigated and mapped down to exact lines and drop-in code modifications.

### Blueprint F10: `scp/runtime/judge.py`
Replace structural validation and crosscheck fallback in both `judge()` and `judge_async()`:
1. **Structural check** (lines 253–262 & 366–374):
   ```python
   # 1. Base structural validation
   expected_answer = kwargs.get("expected_answer")
   custom_postcondition = kwargs.get("postcondition")
   if custom_postcondition and isinstance(custom_postcondition, dict):
       obs = {"evidence_ref": kwargs.get("evidence_ref", ai_answer), "text": ai_answer}
       res = self.verifier.verify(custom_postcondition, obs)
       is_structurally_pass = (res.verdict == "VERIFIED")
       failures = list(res.failures)
   elif expected_answer:
       postcondition = PostconditionSchema.for_text_answer(
           expected_answer,
           evidence_required=bool(kwargs.get("evidence_required", False)),
       ).to_dict()
       obs = {"evidence_ref": kwargs.get("evidence_ref", ai_answer), "text": ai_answer}
       res = self.verifier.verify(postcondition, obs)
       is_structurally_pass = (res.verdict == "VERIFIED")
       failures = list(res.failures)
   else:
       is_structurally_pass = bool(ai_answer and ai_answer.strip())
       failures = [] if is_structurally_pass else ["empty_ai_answer"]
   ```
2. **Crosscheck fallback & return dict** (lines 300–355 & 406–454):
   ```python
   degraded = False
   if _os.environ.get("SCP_MULTI_LLM_CROSSCHECK", "1") == "1":
       try:
           cross = _run_crosscheck_sync(question, ai_answer, context)
           semantic = cross["final"]
           if cross["consensus"] == "disagree":
               failures.append("multi_llm_disagreement")
       except Exception as _cc_err:
           logger.warning(
               "[M2/A2] multi-LLM crosscheck failed (%s: %s) — fallback to single judge cascade",
               type(_cc_err).__name__,
               _cc_err,
           )
           degraded = True
           failures.append("crosscheck_degraded_single_vendor")
           semantic = _llm_judge(question, ai_answer, context)
   else:
       semantic = _llm_judge(question, ai_answer, context)
   ```
   And in the verdict return:
   ```python
   return {
       "verdict": "PASS" if is_pass else "FAIL",
       "confidence": (0.60 if degraded else 0.85) if is_pass else 0.0,
       "deterministic_confidence": 1.0 if is_structurally_pass else 0.0,
       "semantic_confidence": (0.60 if degraded else 0.85) if is_pass else 0.0,
       "cross_model_agreement": (not escalated) and (not degraded),
       "degraded": degraded,
       "reasoning": (
           "Degraded fallback to single vendor: crosscheck failed"
           if degraded
           else "Delegated to IndependentVerifier and LLM Semantic Judge"
       ),
       "cycle_count": cycle_count,
       "failures": failures,
       "final_answer": ai_answer,
       "slm_responses": slm_responses_list,
       "evidence": {
           "governance_decision": "UPHOLD" if is_pass else "KILL",
           "knowledge": kb_refs
       }
   }
   ```
   (Identical changes applied to `judge_async()`).

---

### Blueprint F11: `scp/task_kernel_parts/taskkernel.py`
In `TaskKernel.expire_leases()` (lines 810–845):
```python
if cur_state in {'LEASED', 'RUNNING', 'WAITING_TOOL'}:
    old = cur_state
    cur = self.conn.execute("UPDATE tasks SET state='RECOVERING',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task['task_id'], task['version']))
    if cur.rowcount != 1:
        raise OptimisticLockError(
            f"concurrency conflict expiring lease {lease['lease_id']} on task {task['task_id']}",
            table="tasks",
            entity_id=task['task_id'],
            expected_version=int(task['version']),
        )
    self._append_event(task['task_id'], 'LEASE_EXPIRED', old, 'RECOVERING', 'kernel', 'heartbeat_expired', {'lease_id': lease['lease_id']})
elif cur_state == 'VERIFYING':
    if self.autonomous_mode:
        cur = self.conn.execute(
            "UPDATE tasks SET state='FAILED',error=?,version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
            ("verification_lease_expired", now_iso(), task['task_id'], task['version']),
        )
        if cur.rowcount != 1:
            raise OptimisticLockError(
                f"concurrency conflict expiring verification lease {lease['lease_id']} on task {task['task_id']}",
                table="tasks",
                entity_id=task['task_id'],
                expected_version=int(task['version']),
            )
        self._append_event(
            task['task_id'],
            'LEASE_EXPIRED',
            cur_state,
            'FAILED',
            'kernel:autonomous',
            'heartbeat_expired_autonomous',
            {'lease_id': lease['lease_id'], 'autonomous': True},
        )
    else:
        cur = self.conn.execute("UPDATE tasks SET state='HUMAN_REVIEW',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task['task_id'], task['version']))
        if cur.rowcount != 1:
            raise OptimisticLockError(
                f"concurrency conflict expiring verification lease {lease['lease_id']} on task {task['task_id']}",
                table="tasks",
                entity_id=task['task_id'],
                expected_version=int(task['version']),
            )
        self._append_event(task['task_id'], 'LEASE_EXPIRED', cur_state, 'HUMAN_REVIEW', 'kernel', 'heartbeat_expired', {'lease_id': lease['lease_id']})
elif cur_state == 'CHECKPOINTED':
    cur = self.conn.execute("UPDATE tasks SET state='QUEUED',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task['task_id'], task['version']))
    if cur.rowcount != 1:
        raise OptimisticLockError(
            f"concurrency conflict expiring checkpoint lease {lease['lease_id']} on task {task['task_id']}",
            table="tasks",
            entity_id=task['task_id'],
            expected_version=int(task['version']),
        )
    self._append_event(task['task_id'], 'LEASE_EXPIRED', cur_state, 'QUEUED', 'kernel', 'heartbeat_expired', {'lease_id': lease['lease_id']})
elif task['active_lease_id'] == lease['lease_id']:
    cur = self.conn.execute("UPDATE tasks SET active_lease_id=NULL,active_fencing_token=0,version=version+1,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task['task_id'], task['version']))
    if cur.rowcount != 1:
        raise OptimisticLockError(
            f"concurrency conflict expiring active lease {lease['lease_id']} on task {task['task_id']}",
            table="tasks",
            entity_id=task['task_id'],
            expected_version=int(task['version']),
        )
cur_lease = self.conn.execute('UPDATE leases SET released=1,version=version+1 WHERE lease_id=? AND released=0', (lease['lease_id'],))
if cur_lease.rowcount != 1:
    raise OptimisticLockError(
        f"concurrency conflict releasing expired lease {lease['lease_id']}",
        table="leases",
        entity_id=lease['lease_id'],
        expected_version=int(lease.get('version', 1)),
    )
```

---

### Blueprint F12: `scp/core/top_systems_learning.py`
In `_fetch_github` (lines 253–266):
```python
for item in data.get("items", [])[: per_source]:
    name = str(item.get("full_name", ""))[:200]
    desc = str(item.get("description") or "")[:400]
    quarantined, reason = inspect_untrusted(f"{name} {desc}")
    content_sha = "sha256:" + hashlib.sha256(f"{name}:{desc}".encode("utf-8")).hexdigest()[:32]
    out.append(
        {
            "source": "github",
            "kind": "repository",
            "name": name,
            "url": str(item.get("html_url", ""))[:300],
            "stars": int(item.get("stargazers_count", 0)),
            "forks": int(item.get("forks_count", 0)),
            "description": desc,
            "trust": "QUARANTINED" if quarantined else "untrusted",
            "quarantine_reason": reason,
            "content_sha256": content_sha,
            "reputation": reputation_from_stars(int(item.get("stargazers_count", 0))),
        }
    )
```
In `_fetch_wikipedia` (lines 311–324):
```python
for item in data.get("query", {}).get("search", [])[:per_source]:
    title = str(item.get("title", ""))
    snippet = _TAG_RE.sub("", str(item.get("snippet", "")))
    quarantined, reason = inspect_untrusted(f"{title} {snippet}")
    content_sha = "sha256:" + hashlib.sha256(f"{title}:{snippet}".encode("utf-8")).hexdigest()[:32]
    out.append(
        {
            "source": "wikipedia",
            "kind": "article",
            "name": title[:200],
            "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
            "description": snippet[:400],
            "trust": "QUARANTINED" if quarantined else "untrusted",
            "quarantine_reason": reason,
            "content_sha256": content_sha,
            "reputation": "medium",
        }
    )
```

---

### Blueprint F13: Dashboard SSRF Elimination
1. In `dashboard/src/lib/scp-backend-url.ts`, export the two new helpers:
   ```typescript
   export function resolveInternalBackendBase(): string {
     return resolveBackendBase(
       process.env.SCP_INTERNAL_URL,
       parseHostList(process.env.SCP_API_ALLOWED_HOSTS),
     )
   }

   export function resolveLoopSchedulerBase(): string {
     return resolveBackendBase(
       process.env.LOOP_SCHEDULER_URL ?? "http://127.0.0.1:3030",
       parseHostList(process.env.SCP_HEALTH_ALLOWED_HOSTS),
     )
   }
   ```
2. In `dashboard/src/app/api/scp/status/route.ts`:
   Remove top-level `const SCP_BASE_URL = ...`.
   Inside `GET()` `try`:
   ```typescript
   const scpBase = resolveInternalBackendBase()
   const res = await fetch(`${scpBase}/health`, { ... })
   ```
3. In `dashboard/src/app/api/scanners/route.ts`:
   Remove top-level `const SCP_BACKEND_URL = ...`.
   Inside `GET()` `try`:
   ```typescript
   const scpBackend = resolveInternalBackendBase()
   const resp = await fetch(`${scpBackend}/v105/scanners`, { ... })
   ```
4. In `dashboard/src/app/api/autofix/route.ts`:
   Remove top-level `const SCP_BACKEND_URL = ...`.
   Inside `GET()` `try`:
   ```typescript
   const scpBackend = resolveInternalBackendBase()
   const resp = await fetch(`${scpBackend}/v105/autofix/stats`, { ... })
   ```
5. In `dashboard/src/app/api/scp/loop/route.ts`:
   Remove top-level `const SCHEDULER_URL = ...`.
   Inside `GET()` `try`:
   ```typescript
   const schedulerUrl = resolveLoopSchedulerBase()
   const res = await fetch(`${schedulerUrl}/`, { ... })
   ```
6. In `dashboard/src/app/api/scp/loop/trigger/route.ts`:
   Remove top-level `const SCHEDULER_URL = ...`.
   Inside `POST()` `try`:
   ```typescript
   const schedulerUrl = resolveLoopSchedulerBase()
   const res = await fetch(`${schedulerUrl}/trigger`, { ... })
   ```

---

### Blueprint F15: Quorum Removal in Docs & Tools
1. In `docs/SCP_ARCHITECTURE.md`:
   - Delete line 60: `| 10 | Quorum WHY cho action nguy hiểm | `scp/security/quorum_why.py` (125 LOC) |` (renumber pipeline steps 1–12).
   - Delete line 121: `| `scp/security/quorum_why.py` | 125 | Hội đồng WHY cho action nguy hiểm |`.
2. In `tools/stress_p1_concurrency.py`:
   - Delete line 70: `"scp.security.quorum_why",`.
3. Clean dead artifact: remove `scp/security/__pycache__/quorum_why.cpython-312.pyc`.

---

### Blueprint F16: `ChatMemoryStore._SECRET_PATTERNS` Additions (`scp/core/chat_memory_store.py`)
In `scp/core/chat_memory_store.py:96–101`:
```python
    _SECRET_PATTERNS = (
        re.compile(r"(?i)\b(?:openrouter_api_key|scp_auth_password|scp_auth_token_secret|api[_ -]?key|password|token|secret)\s*[:=]\s*[^\s,;]+"),
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b"),
        re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
        re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----.*?-----END [A-Z ]+ PRIVATE KEY-----"),
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),
        re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
        re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"),
    )
```

---

## 5. Verification Method

To independently verify these findings and test future worker implementations:

1. **F10 Verification**:
   - Run: `pytest tests/T05_gateway/test_judge_sync_crosscheck_alive.py -q` (5 passed).
   - Run: `pytest tests/contract/test_judge_verifier_contract.py -q` (1 passed).
   - Invalidation condition: If `test_sync_judge_crosscheck_failure_logs_then_falls_back` fails or returns `degraded: False` when crosscheck raises.

2. **F11 Verification**:
   - Run: `pytest tests/T04_kernel/test_autonomous_state_machine_lifecycle.py tests/T04_kernel/test_adversarial_kernel_flaws.py -q` (54 passed).
   - Invalidation condition: If concurrent race between `expire_leases()` and `commit_completed()` corrupts task state without raising `OptimisticLockError`.

3. **F12 Verification**:
   - Run: `pytest tests/T03_capability/test_flow_13_free_api_learning_scp_standard.py tests/T03_capability/test_internet_safety_firewall.py -q` (32 passed).
   - Invalidation condition: If a GitHub description containing `"ignore all previous instructions"` appears in `advise()` output.

4. **F13 Verification**:
   - Grep: `grep_search` across `dashboard/src/app/api/` for `process.env.SCP_INTERNAL_URL` and `process.env.LOOP_SCHEDULER_URL`. Expected result: 0 occurrences outside of `dashboard/src/lib/scp-backend-url.ts`.
   - Invalidation condition: If any route handler imports or references raw env URLs directly into a `fetch` statement.

5. **F15 Verification**:
   - Grep: `grep_search` for `quorum_why` across the repository.
   - Expected result: 0 matches in `docs/SCP_ARCHITECTURE.md` and `tools/stress_p1_concurrency.py`.
   - Command: `python tools/stress_p1_concurrency.py --check-imports` must not fail with `ModuleNotFoundError: No module named 'scp.security.quorum_why'`.

6. **F16 Verification**:
   - Run: `pytest tests/T12_unified_chatbot/test_tier3_cross_feature.py -k test_comb17_multiturn_memory_secret_redaction_trace -q`.
   - Python unit test:
     ```python
     from scp.core.chat_memory_store import ChatMemoryStore
     assert ChatMemoryStore.redact("ghp_[REDACTED-ROTATE-ME]") == "[REDACTED]"
     # NOTE 2026-10-01: dòng trên chứa literal GitHub PAT shape `ghp_` + 36 ký tự đã bị
     # exposure trong scratch note này → đã redact. Token ĐÃ lộ cần ROTATE ngay trên
     # GitHub (Settings → Developer settings → PATs) — đây là hành động của owner,
     # redaction trong doc không vô hiệu hoá token. (FA-08/secret hygiene)
     assert ChatMemoryStore.redact("AKIAIOSFODNN7EXAMPLE") == "[REDACTED]"
     assert ChatMemoryStore.redact("AIzaSyA_1234567890abcdefghijklmnopqrstuv") == "[REDACTED]"
     assert ChatMemoryStore.redact("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c") == "[REDACTED]"
     ```
   - Invalidation condition: If any of the 4 raw credential formats appears unmasked in `ChatMemoryStore.redact()` output.
