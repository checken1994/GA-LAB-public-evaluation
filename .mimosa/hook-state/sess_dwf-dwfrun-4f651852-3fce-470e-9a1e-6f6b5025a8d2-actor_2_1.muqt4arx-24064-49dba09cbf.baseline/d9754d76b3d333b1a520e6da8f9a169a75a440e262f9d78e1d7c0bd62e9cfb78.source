import asyncio
import sqlite3
import hashlib
import time
import re
from pathlib import Path

from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import hooks, policy


# ==============================================================================
# 1. SCP DNA & SYSTEM INSTRUCTIONS
# ==============================================================================

SCP_DNA_INSTRUCTIONS = """
You are the SCP Orchestrator Agent — an autonomous Agent OS.

CORE INVARIANTS (SCP DNA):
- Reality > Model: Never conclude from reasoning alone; run evidence-gathering tools.
- PASS ≠ TRUE: A test passing only means no failure within that scope.
- Fail-Closed: When uncertain, return UNKNOWN or HUMAN_REVIEW. Never guess ALLOW.
- PASS only when: same-SHA evidence + all mandatory gates + blockers=0.

FORBIDDEN ACTIONS (FA-01 to FA-13 enforced by policies):
- FA-01: Never loosen test assertions.
- FA-02: Never delete/skip/xfail tests.
- FA-03: Never claim PASS without terminal evidence.
- FA-08: Never write fake log/evidence files.
- FA-09: Never claim a bug without a reproducing exploit script.

OPERATING LOOP (DNA evidence-first):
1. Identify task and load relevant SCP Skill.
2. Gather evidence from independent lineages.
3. Name missing pieces explicitly.
4. Make smallest reversible change with rollback plan.
5. Run reality test before declaring success.
6. Record open questions — never claim system is complete.

Language: Vietnamese for reasoning; keep English technical identifiers.
"""

# ==============================================================================
# 2. SAFETY POLICIES (FA ENFORCEMENT)
# ==============================================================================

def fa01_no_loosen(args):
    cmd = args.get("CommandLine", "")
    bad = ["--ignore", "xfail", "skip", "assert False"]
    return any(b in cmd for b in bad)

def fa08_no_forged(args):
    path = args.get("TargetFile", "")
    content = args.get("CodeContent", "")
    fake_markers = ["PASS", "pytest passed", "tests/"]
    return path.endswith((".log", ".out")) and any(m in content for m in fake_markers)

# Fake baseline state for demonstration
_baseline_reconciled = False
def fa06_no_premature_edit(args):
    return not _baseline_reconciled

def is_r2_r3(args):
    cmd = args.get("CommandLine", "")
    r3_keywords = ["git push", "gh pr", "npm publish", "rm -rf", "delete"]
    return any(k in cmd for k in r3_keywords)

ALLOWLIST = ["github.com", "pypi.org", "api.gemini.google.com"]
def egress_blocked(args):
    cmd = args.get("CommandLine", "")
    domains = re.findall(r'https?://([^/\s]+)', cmd)
    return any(d not in ALLOWLIST for d in domains)

async def human_approval(tool_call):
    # In a real environment, this might block and wait for user CLI input or UI approval
    print(f"\n[APPROVAL REQUIRED] Action requested: {tool_call.name} with args {tool_call.args}")
    # Auto-deny for safety in this scaffold, can be changed to input()
    print("-> Auto-denying R2/R3 action in autonomous mode.")
    return False

SCP_POLICIES = [
    policy.deny_all(),                             # Base: deny everything
    policy.allow("view_file"),                     # Read files OK
    policy.allow("grep_search"),                   # Search OK
    policy.allow("find_by_name"),                  # Find OK
    policy.allow("list_dir"),
    policy.deny("write_to_file", when=fa08_no_forged, name="FA-08"),
    policy.deny("replace_file_content", when=fa06_no_premature_edit, name="FA-06"),
    policy.deny("run_command", when=fa01_no_loosen, name="FA-01"),
    policy.deny("run_command", when=egress_blocked, name="egress-deny"),
    policy.ask_user("run_command", when=is_r2_r3, handler=human_approval, name="R2-R3-approval"),
    policy.allow("run_command"),                   # R0/R1 read-only OK
]

# ==============================================================================
# 3. HOOKS (JOURNAL, KILL SWITCH, CIRCUIT BREAKER, VERIFIER)
# ==============================================================================

class JournalHook(hooks.PostToolCallHook):
    """Append-only event journal — FA-08: mọi evidence phải là raw output."""
    def __init__(self, db_path: str):
        self._db = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS journal(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL, tool TEXT, result_hash TEXT,
                outcome TEXT, prev_hash TEXT)""")

    async def run(self, context, data):
        result_str = str(data)
        result_hash = hashlib.sha256(result_str.encode()).hexdigest()[:16]
        prev_hash = self._get_last_hash()
        with sqlite3.connect(self._db) as c:
            c.execute("INSERT INTO journal(ts,tool,result_hash,outcome,prev_hash)"
                      " VALUES(?,?,?,?,?)",
                      (time.time(), context.tool_name,
                       result_hash, result_str[:500], prev_hash))

    def _get_last_hash(self):
        with sqlite3.connect(self._db) as c:
            r = c.execute("SELECT result_hash FROM journal ORDER BY seq DESC LIMIT 1").fetchone()
            return r[0] if r else "GENESIS"


class VerifierHook(hooks.PostToolCallHook):
    """Rule-based verification check after state-mutating tools."""
    VERIFY_TOOLS = {"run_command", "replace_file_content", "write_to_file"}

    async def run(self, context, data):
        if context.tool_name not in self.VERIFY_TOOLS:
            return
        outcome = str(data).lower()
        if "error" in outcome or "traceback" in outcome or "exception" in outcome:
            raise RuntimeError(f"[VERIFIER] Tool {context.tool_name} returned error — HUMAN_REVIEW required")


class KillSwitchHook(hooks.PreToolCallHook):
    """Global kill switch check before any tool call."""
    KILL_FILE = Path(".scp_kill")

    async def run(self, context, data):
        if self.KILL_FILE.exists():
            reason = self.KILL_FILE.read_text().strip()
            raise PermissionError(f"[KILL_SWITCH ACTIVE] {reason} — All actions blocked.")


from collections import defaultdict
class CircuitBreakerHook(hooks.OnToolErrorHook):
    """Open circuit for 5 minutes after 3 consecutive failures."""
    _failures: dict = defaultdict(list)
    THRESHOLD = 3
    COOLDOWN = 300  # 5 mins

    async def run(self, context, data):
        tool = context.tool_name
        now = time.time()
        self._failures[tool] = [t for t in self._failures[tool] if now - t < self.COOLDOWN]
        self._failures[tool].append(now)
        if len(self._failures[tool]) >= self.THRESHOLD:
            return (f"[CIRCUIT_OPEN] {tool} failed {self.THRESHOLD}x "
                    f"in {self.COOLDOWN}s. Retry after cooldown.")
        return None

# ==============================================================================
# 4. SUBAGENTS HIERARCHY
# ==============================================================================

def make_audit_supervisor():
    return types.SubagentConfig(
        name="audit_supervisor",
        description=(
            "Orchestrates SCP audit tasks: runtime-audit, reality-verifier, "
            "release-evidence-gate, skill-review. "
            "Use when checking service health, evidence level, or release readiness."
        ),
        capabilities=types.SubagentCapabilities(
            agent_behavior=types.AgentBehavior.AUTONOMOUS,
            enabled_tools=[
                types.BuiltinTools.VIEW_FILE,
                types.BuiltinTools.RUN_COMMAND,
                types.BuiltinTools.START_SUBAGENT,
            ],
            allowed_subagents=["scp_runtime_auditor", "scp_reality_verifier",
                               "scp_release_gate", "scp_skill_reviewer"],
        ),
    )

def make_skill_executor(name: str, description: str, tools: list, can_spawn: bool = False):
    enabled = list(tools)
    if can_spawn:
        enabled.append(types.BuiltinTools.START_SUBAGENT)
    return types.SubagentConfig(
        name=name, description=description,
        capabilities=types.SubagentCapabilities(
            agent_behavior=types.AgentBehavior.AUTONOMOUS,
            enabled_tools=enabled,
        ),
    )

SKILL_AGENTS = [
    # -- Audit tier
    make_audit_supervisor(),
    make_skill_executor(
        "scp_runtime_auditor",
        "Audit SCP service: process, port, health endpoint, test runner.",
        [types.BuiltinTools.VIEW_FILE, types.BuiltinTools.RUN_COMMAND],
    ),
    make_skill_executor(
        "scp_reality_verifier",
        "Verify claims using 4-level evidence (A-Static->D-Recovery).",
        [types.BuiltinTools.VIEW_FILE],
    ),
    make_skill_executor(
        "scp_release_gate",
        "Check mandatory release gates.",
        [types.BuiltinTools.VIEW_FILE, types.BuiltinTools.RUN_COMMAND],
    ),
    make_skill_executor(
        "scp_skill_reviewer",
        "Audit the skill pack itself.",
        [types.BuiltinTools.VIEW_FILE],
    ),
    
    # -- Security tier
    make_skill_executor(
        "scp_security_reviewer",
        "Review capability security: R0-R3 risk tiers, PEP, egress, secrets.",
        [types.BuiltinTools.VIEW_FILE],
    ),
    make_skill_executor(
        "scp_task_kernel_reviewer",
        "Review Task Kernel state machine, lease, journal.",
        [types.BuiltinTools.VIEW_FILE, types.BuiltinTools.RUN_COMMAND],
    ),
    
    # -- Ops tier
    make_skill_executor(
        "scp_startup_troubleshooter",
        "Diagnose SCP startup failures: port mismatch, launcher corruption.",
        [types.BuiltinTools.VIEW_FILE, types.BuiltinTools.RUN_COMMAND],
    ),
    make_skill_executor(
        "scp_latency_optimizer",
        "Analyze and optimize SCP latency safely.",
        [types.BuiltinTools.VIEW_FILE],
    ),
]

# ==============================================================================
# 5. MAIN AGENT ENTRYPOINT
# ==============================================================================

async def main():
    print("[AGY] Initializing SCP Orchestrator Multi-Agent System...")
    config = LocalAgentConfig(
        system_instructions=SCP_DNA_INSTRUCTIONS,
        subagents=SKILL_AGENTS,
        capabilities=types.CapabilitiesConfig(
            agent_behavior=types.AgentBehavior.AUTONOMOUS,
            enable_subagents=True,
            max_subagent_depth=3,
            allowed_subagents=["audit_supervisor", "scp_security_reviewer",
                               "scp_startup_troubleshooter", "scp_latency_optimizer"],
        ),
        policies=SCP_POLICIES,
        hooks=[
            KillSwitchHook(),
            JournalHook(".scp_journal.db"),
            VerifierHook(),
            CircuitBreakerHook(),
        ],
        budget_config=types.BudgetConfig(
            max_model_calls=50,
            max_tool_calls=200,
            max_total_tokens=500_000,
        ),
    )

    async with Agent(config=config) as agent:
        print("[AGY] Orchestrator Ready. Sending test prompt...")
        # Note: Depending on standard Antigravity auth, you might need GEMINI_API_KEY exported
        # in your environment.
        try:
            resp = await agent.chat(
                "Trạng thái hiện tại: Bạn đang là SCP Orchestrator. "
                "Hãy đọc GA.md và cho tôi biết bạn cần phân công việc cho subagent nào."
            )
            print("\n=== AGENT RESPONSE ===")
            print(await resp.text())
            print("======================")
        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("Note: If you get an auth error, ensure GEMINI_API_KEY is set in your environment.")

if __name__ == "__main__":
    asyncio.run(main())
