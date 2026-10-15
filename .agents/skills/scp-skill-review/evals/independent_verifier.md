# SCP Skill Review — Independent C5 Verifier Contract

This verifier is a separate evaluation role. It MUST NOT be the generator/author of the skill or the agent trajectory being graded.

## Inputs
- exact repository SHA
- target skill path
- C4 eval case and observed trajectory/output
- authoritative repository evidence used by the target skill

## Independence gate
1. Record `generator_actor_or_lineage` and `verifier_actor_or_lineage` when observable.
2. If they are the same, or independence cannot be established, return `BLOCKED_INDEPENDENCE`.
3. `BLOCKED_INDEPENDENCE` is never PASS and never VERIFIED.

## Verification checks
For every C4 case, independently check:
1. The exact SHA exists and all cited repository evidence belongs to that SHA.
2. Assertions are evaluated from observed output/trajectory, not from the target skill's self-report.
3. Declared counts are recomputed from authoritative source data.
4. Contradictions, missing evidence, or unavailable runtime observations fail closed.
5. The target skill does not weaken SCP DNA, tests, protected semantics, or evidence requirements to obtain a pass.
6. Evidence level is assigned only from actually observed evidence: A=static, B=integration, C=end-to-end, D=recovery.

## Verdict
Return exactly one of:
- `VERIFIED`: every assertion passes, evidence >= B, independence established, no contradiction.
- `CONTRADICTED`: authoritative evidence contradicts the target output.
- `INSUFFICIENT`: required integration/runtime evidence is missing.
- `BLOCKED_INDEPENDENCE`: verifier independence is absent or unprovable.
- `HUMAN_REVIEW`: authority/scope/security conflict requires the human owner.

## Required record
```json
{
  "sha": "<exact sha>",
  "case_id": "<C4 case>",
  "target_skill": "<path>",
  "generator_actor_or_lineage": "<id or UNKNOWN>",
  "verifier_actor_or_lineage": "<id>",
  "independence_confirmed": false,
  "assertions": [{"name": "...", "result": "PASS|FAIL", "evidence": "..."}],
  "evidence_level": "A|B|C|D",
  "verdict": "VERIFIED|CONTRADICTED|INSUFFICIENT|BLOCKED_INDEPENDENCE|HUMAN_REVIEW"
}
```

A verifier MUST NOT edit the target skill while issuing the verdict. Remediation is a separate subsequent action and requires re-evaluation on the new SHA.
