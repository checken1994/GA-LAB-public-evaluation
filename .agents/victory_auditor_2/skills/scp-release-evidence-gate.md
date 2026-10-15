# SCP Release Evidence Gate

## Core Methodology
Kiểm tra release candidate của SCP bằng commit snapshot, service manifest, test runner, smoke test, golden task, chaos test, security gate, reproducibility và rollback evidence.
- Release candidate requires runtime proof, security gates, recovery and reproducibility.
- 7 mandatory gates: Config, Static, Runtime, Golden task, Chaos, Security, Reproducibility.
- Pass conditions:
  - PASS: gate executed within workload and specific evidence.
  - BLOCKED: insufficient evidence.
  - FAIL: gate executed and required condition failed.
  - Agent OS label requires task kernel, durable state, lease fencing, capability, supervisor, verifier, recovery, observability, kill switch, and golden task runtime evidence.
