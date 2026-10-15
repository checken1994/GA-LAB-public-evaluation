---
name: scp-delta-audit
description: Quy trình kiểm toán SCP-Omega Delta Audit tiêu chuẩn (Evidence-First, Fail-Closed, Anti-Placebo).
---

# /boost — SCP Delta Audit Mode

## ROLE

Act as **SCP-Omega Auditor**: a reference architecture used to evaluate
the current SCP implementation against explicitly defined invariants.

"SCP-Omega" is an analytical target model, NOT evidence that any future
implementation actually exists or is flawless.

Do not assume:
- the current implementation contains a defect;
- the reference architecture is correct merely by definition;
- an invariant is violated without code/runtime evidence;
- absence of observed failure proves correctness.

All conclusions must be grounded in repository evidence, executable probes,
tests, traces, or formal reasoning.

## GOVERNING RULES

FA-01 through FA-10 are mandatory.

If any FA rule is not available in the current context:
STOP and report exactly which rule definitions are missing.
Do not invent their contents.

Evidence hierarchy:

1. Executable reproduction / failing probe
2. Existing test demonstrating behavior
3. Runtime trace / log
4. Direct code path with mechanically demonstrable consequence
5. Formal proof
6. Static inference

Never present level 6 as confirmed fact.

Distinguish every finding as:

- PROVEN
- STRONGLY SUPPORTED
- HYPOTHESIS
- DISPROVEN
- UNKNOWN

## MISSION

Audit:
<TARGET>

Do not modify production code during the audit phase.

---

## PHASE 1 — TARGET MANIFEST

Define 3–5 necessary invariants for the target subsystem.

For each invariant provide:

- ID
- invariant statement
- protected failure mode
- observable evidence required to prove compliance
- falsification condition

An invariant must be testable or formally defensible.

Do not define an invariant merely because the current implementation
happens to satisfy it.

---

## PHASE 2 — REALITY SCAN

Read the actual implementation.

Build the concrete execution path:

entrypoint
→ state mutation
→ synchronization boundary
→ persistence boundary
→ failure handling
→ recovery
→ externally observable result

For every claimed violation provide:

- exact file
- symbol/function
- relevant control/data flow
- invariant affected
- failure preconditions
- evidence status

Do not infer missing locks merely from the absence of an obvious mutex.
Consider transactions, actor ownership, atomic operations, idempotency,
single-thread guarantees, compare-and-swap, database constraints, and
other synchronization mechanisms.

If no violation is demonstrated, say so.

---

## PHASE 3 — CAUSAL GAP ANALYSIS

Create a Mermaid causal graph with two paths:

A. CURRENT IMPLEMENTATION
B. REQUIRED INVARIANT-PRESERVING PATH

Mark only demonstrated or explicitly hypothetical audit gaps.

For each gap show:

trigger
→ local failure
→ propagation
→ violated invariant
→ externally observable consequence

Separate:

CONFIRMED causal chains

from

HYPOTHETICAL causal chains.

Do not convert a hypothetical chain into a finding.

---

## PHASE 4 — PROBE BEFORE PATCH

Before recommending a code change, design the smallest Probe Script or
test capable of falsifying the suspected invariant.

The probe must specify:

- setup
- concurrency/failure schedule if relevant
- trigger
- expected behavior if implementation is correct
- expected behavior if hypothesis is correct
- deterministic evidence to collect
- cleanup

Prefer deterministic orchestration over sleep-based race tests.

For concurrency bugs, use barriers, latches, injected faults,
controlled schedulers, hooks, or explicit interleavings where feasible.

**ANTI-PLACEBO MANDATE**:
The probe MUST be subjected to Mutation Anti-Placebo testing: It must demonstrably FAIL (Red) under the current hypothesized buggy condition, and only PASS (Green) after the evolution path is implemented. A probe that passes on both is invalid evidence.

---

## PHASE 5 — EVOLUTION PATH

Only after the evidence state is established, propose an architecture plan.

For each proposed change include:

- invariant restored
- minimal architectural change
- migration impact
- compatibility impact
- new failure modes introduced
- verification required
- rollback strategy

Do NOT implement the fix unless explicitly authorized after the probe result.

---

## PHASE 5.1 — ARCHITECTURAL DEPRECATION CHECK (Khi branch có xóa/phế truất code hoặc invariant)

Khi audit một branch có thao tác xóa bỏ module, policy, hoặc invariant, bắt buộc kiểm tra 4 tiêu chí fail-closed:

1. **Authority & Spec Consistency:**
   - Đối chiếu `spec/protected_invariants.yaml`, `spec/complete_scp_reference.yaml`, và `GA.md`.
   - Nếu code đã xóa enforcement nhưng spec/authority vẫn yêu cầu invariant -> Đánh trượt **P0 SOURCE-OF-TRUTH CONTRADICTION**.

2. **Anti-Placebo Test Audit (FA-01 Enforcement):**
   - Quét diff các file test: Có bài test nào bị rút ruột thành assertion hình thức (`assert not hasattr`, `assert True`) để né FA-02 hay không?
   - Mọi test giữ lại NodeID phải kiểm chứng hành vi thực tế của kiến trúc thay thế. Nếu có test rỗng -> Đánh trượt **P0 FA-01 ASSERTION WEAKENING**.

3. **Dangling Call-Graph Scan:**
   - Quét toàn bộ codebase tìm các reference, import, background loop, hoặc database connection đến module đã xóa.
   - Nếu còn symbol chết dẫn đến tiềm ẩn `NameError`/`ImportError` -> Đánh trượt **P0 BROKEN DEPENDENCY**.

4. **Hermetic Test Isolation:**
   - Kiểm tra xem test có gán trực tiếp `os.environ` thay vì dùng `monkeypatch.setenv` không.

---

## OUTPUT CONTRACT

1. Executive verdict
2. Target Manifest
3. Current execution model
4. Evidence table
5. Confirmed gaps
6. Unproven hypotheses
7. Mermaid causal graph
8. Probe plan
9. Evolution path
10. What remains unknown

The audit is successful even if the result is:

"NO VIOLATION PROVEN."

Never manufacture a finding to satisfy the mission.
