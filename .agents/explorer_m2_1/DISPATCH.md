# Dispatch for explorer_m2_1

**Milestone**: M2 (Wire Security Modules into Production Runtime)
**Focus**: Feature F07 — Wiring `SafeCommandRunnerTool` (`scp/capabilities/tools.py`) into production runtime.

## Investigation Scope
1. Inspect `scp/capabilities/tools.py` to understand `SafeCommandRunnerTool` interface and constraints.
2. Inspect `scp/runtime/engine_parts/hands_planner.py` (around lines 486-495), `ActionRegistry`, `AutonomousCapabilityGovernor`, and `HandsExecutor` (`scp/hands/`).
3. Identify where old governor regexes or unwired tool invocation paths are being used instead of `SafeCommandRunnerTool`.
4. Determine the exact changes needed so that `from scp.capabilities.tools import SafeCommandRunnerTool` (or related classes) is called in production code paths during tool execution and capability governance.
5. Identify affected test suites and recommend a concrete implementation strategy and test verification commands.

## Required Output
Write your findings to `D:\scp\.agents\explorer_m2_1\handoff.md`.

## 2026-09-22T19:48:14Z
Investigate Feature F07 of Milestone M2:
- Wiring SafeCommandRunnerTool (scp/capabilities/tools.py) into production runtime paths: ActionRegistry, AutonomousCapabilityGovernor, and HandsExecutor.
- Locate old governor regexes (e.g. in scp/runtime/engine_parts/hands_planner.py:486-495, scp/hands/) and plan their delegation or replacement with genuine tool boundary execution.
- Ensure grep -rn "from scp.capabilities.tools import" will find genuine production callers (not in tests/).
- Determine impact on existing test suites, edge cases, and define the exact fix strategy and verification commands.
