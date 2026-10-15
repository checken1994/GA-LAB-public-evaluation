# SCP Reality Verifier (Local Copy)

Source: `d:\scp\.agents\skills\scp-reality-verifier\SKILL.md`

## Evidence Hierarchy
- A: Static (File, route, schema exists - does not prove runtime)
- B: Integration (Modules/processes connect)
- C: End-to-end (Real task flows through planner, policy, tool, verifier)
- D: Recovery proof (Level C + crash/timeout/restart handled properly)

## Rules
- PASS != TRUE
- Do not trust claims or logs without re-executing probes.
- Empirical verification: run commands with live python interpreter.
- Falsification condition and postcondition checking.
