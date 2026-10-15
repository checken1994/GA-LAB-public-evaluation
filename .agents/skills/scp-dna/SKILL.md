---
name: scp-dna
description: Apply SCP DNA (29 core principles) for rigorous analysis, debugging, self-correction, claim verification, system design, and audit. Use when the user mentions SCP DNA, missing piece, Reality over Model, PASS not equal TRUE, ao giac dong thuan, or asks for deep root-cause analysis, self-auditing, or truth-seeking reasoning on code, claims, or designs.
---

# SCP DNA Reasoning Skill

Apply the 29 SCP DNA principles as operational rules when analyzing problems, debugging code, verifying claims, designing systems, or performing audits.

Full principle list lives in `references/dna-principles.md`. Load it when you need the exact wording of any principle.

## Core Operating Loop

Always follow this sequence (DNA #1 + #18):

1. **Hỏi Tại sao** — Start from the problem, not the solution. Ask "Tại sao?" at least 3–5 times to surface assumptions and missing pieces.
2. **Tìm bằng chứng** — Gather evidence from independent lineages (DNA #5, #14, #20). Prefer cross-lineage agreement over majority vote of the same lineage.
3. **Phát hiện missing piece** — Explicitly name what is missing or unobservable (DNA #19, #25).
4. **Thử nhỏ + quan sát thực tế** — Prefer small, reversible actions with clear observation (DNA #12, #17).
5. **Reality test** — After any change, run a concrete check (import, execute, cross-check). Reality has final authority (DNA #26).
6. **Audit & calibrate** — Log decisions, acknowledge limits, leave open questions (DNA #8, #22, #23).

## Key Decision Rules

### Evidence & Consensus
- Never treat multiple sources that share the same origin as independent (DNA #5).
- Majority agreement is not proof. Demand at least one independent lineage or adversarial check (DNA #14).
- PASS only means "no error found within current scope and current evidence" (DNA #22). Never conclude "done" or "no remaining issues".

### Authority & Scope
- Do not grant the system the final decision on high-stakes logic changes. Surface recommendations and require human understanding (DNA #4, #11).
- Stay inside allowed data and scope. If evidence is insufficient, say so explicitly (DNA #16).
- Prefer external tools or methods when they are better suited (DNA #13).

### Safety of Change
- Every proposed fix must include a rollback path and a non-fatal guard (DNA #7, #9).
- Prefer small batches with checkpoints over big-bang changes (DNA #17, #18).
- After applying a change, always perform a Reality test before declaring success (DNA #2, #26).

### Self-Correction
- Treat the analysis process itself as auditable. Ask whether the current method can detect its own failures (DNA #3, #21).
- When scanners or tools agree, check for shared blind spots (DNA #19).
- End every substantial analysis with remaining open questions rather than a final "PASS" (DNA #23, #24, #25).

## Response Structure for Analysis Tasks

When performing deep analysis, debugging, or verification:

1. **Problem statement** — Restate the issue without jumping to solutions.
2. **Why chain** — List the successive "Tại sao?" and the assumptions uncovered.
3. **Evidence map** — Sources used, their lineages, and any shared origin risks.
4. **Missing pieces** — Explicit gaps or unobservables.
5. **Proposed action** — Small, reversible, with Reality-test plan and rollback.
6. **Open questions** — What still cannot be known with current capability.

## When Not to Over-Apply

- Simple factual lookups or straightforward coding tasks that do not involve uncertainty, self-modification, or high-stakes claims do not need the full 29-principle ritual.
- Still keep the spirit: prefer evidence, name uncertainty, and avoid overconfidence.

## Loading Full DNA

Read `references/dna-principles.md` whenever you need the precise text of any of the 29 principles or their anti-patterns.
