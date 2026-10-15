# Local copy of scp-runtime-audit skill
Source: C:\Users\check\.gemini\config\plugins\scp-skills\skills\scp-runtime-audit\SKILL.md

---
name: scp-runtime-audit
description: Audit trạng thái vận hành của SCP bằng cách đối chiếu service, port, health, log, test runner, end-to-end proof, security guard và khả năng tái hiện release.
---

## Core Guidelines
- Phân biệt static assertion, integration proof và end-to-end runtime proof.
- Record commit, git status, runtime versions.
- Service inventory: service_name, host, configured_port, actual_port, health_url, pid, started_at, config_source, evidence_ref.
- Verify real processes and real listening ports.
- Health / Readiness distinction.
- Check security guards: fail-closed, secret redaction, token protection, anti-spoofing.
- Golden task proof: trace_id, fact separator, verifier evidence, audit ledger hash-chain integrity.
- Statuses: NOT_RUNNING, PARTIALLY_RUNNING, CANDIDATE_NOT_PROVEN, RUNTIME_PROVEN.
