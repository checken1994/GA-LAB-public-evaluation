import os
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

with open('.env.example', 'r', encoding='utf-8') as f:
    env_example_text = f.read()

example_keys = set()
for line in env_example_text.splitlines():
    line = line.strip()
    m = re.match(r'^(?:#\s*)?([A-Za-z_][A-Za-z0-9_]*)=', line)
    if m:
        example_keys.add(m.group(1))

# Extract all env vars from scp/
all_found = defaultdict(list)
pattern = re.compile(r"""(?:os\.environ\[|os\.environ\.get\(|os\.getenv\(|os\.environ\.setdefault\()\s*["']([A-Z0-9_]+)["']""")

for root, dirs, files in os.walk('scp'):
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                for lineno, line in enumerate(fp, 1):
                    for m in pattern.finditer(line):
                        k = m.group(1)
                        all_found[k].append((path, lineno, line.strip()))
        except Exception:
            continue

os_vars = {'SYSTEMROOT', 'TEMP', 'TMP', 'LOCALAPPDATA', 'PROGRAMFILES'}
app_missing = sorted([k for k in all_found if k not in example_keys and k not in os_vars])

print(f"Total application missing variables: {len(app_missing)}")

# Analyze each variable
var_details = {}
for k in app_missing:
    entries = all_found[k]
    files = sorted(set(e[0] for e in entries))
    lines = [e[2] for e in entries]

    # infer default value
    defaults = set()
    for l in lines:
        m = re.search(r"""(?:getenv|get|setdefault)\s*\(\s*["']""" + k + r"""["']\s*,\s*([^)]+)""", l)
        if m:
            val = m.group(1).strip().strip("'\"")
            defaults.add(val)

    def_val = list(defaults)[0] if defaults else ""

    # determine subsystem
    rel_path = files[0].replace('\\', '/')
    subsys = rel_path.split('/')[1]
    if subsys.endswith('.py'):
        subsys = 'core_root'

    var_details[k] = {
        'subsystem': subsys,
        'default': def_val,
        'files': files,
        'sample_line': lines[0] if lines else ""
    }

# Group by logical domain for .env.example
logical_groups = {
    "Security & Authentication": [
        "SCP_ADMIN_EMAIL", "SCP_ADMIN_WEBHOOK_URL", "SCP_ENCRYPTION_KEY",
        "SCP_ENCRYPT_BYPASSES", "SCP_ENABLE_POISON_COUNTER", "SCP_ENABLE_REVERSE_PROBE_PORTS",
        "SCP_EGRESS_ALLOWLIST", "SCP_VERIFIER_SECRET", "SCP_TOP_SYSTEMS_EGRESS"
    ],
    "Persistence & Databases (PostgreSQL / SQLite)": [
        "SCP_STORAGE_BACKEND", "SCP_KERNEL_BACKEND", "SCP_KERNEL_PG_DSN",
        "SCP_EVENT_BUS_DSN", "SCP_EVENT_BUS_ENABLED", "SCP_KERNEL_DB_PATH",
        "SCP_KERNEL_TRACE_PATH", "SCP_TRACE_STORE_PATH", "SCP_CHAT_MEMORY_PATH",
        "SCP_LEARNING_RUN_LEDGER_PATH", "SCP_REQUEST_RUN_LEDGER_PATH",
        "SCP_AGENT_RUN_STATE_PATH", "SCP_WAL_THRESHOLD", "SCP_JSONL_MAX",
        "SCP_STARTUP_DEFER"
    ],
    "API Server & Routing": [
        "SCP_SERVICE_NAME", "SCP_CONFIG_HASH", "SCP_ENV_FILE", "SCP_FORCE_HTTPS",
        "SCP_ASK_KERNEL_ENABLED", "SCP_ASK_LEASE_TTL_SECONDS", "SCP_ASK_LEASE_HEARTBEAT",
        "SCP_ASK_MAX_INFLIGHT", "SCP_AUTONOMOUS_MODE", "SCP_KERNEL_BACKUP_RETENTION",
        "SCP_T2_ROUTER", "SCP_T2_MIN_CONFIDENCE", "SCP_LOCAL_ONLY",
        "SCP_MAX_AUTO_RETRIES", "SCP_RETRY_TIMEOUT_SEC", "SCP_POLICY_VERSION",
        "SCP_SAFE_PROCESS_EXTRA", "SCP_SPECULATIVE_ATTEMPTS"
    ],
    "Observability & Telemetry": [
        "SCP_OTEL_SERVICE_NAME", "SCP_OTEL_ENDPOINT", "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_PYTHON_FASTAPI_EXCLUDED_URLS", "SCP_MCP_LOG_LEVEL"
    ],
    "LLM Gateway & Microservices": [
        "GROQ_API_KEY", "GROQ_BASE_URL", "GROQ_MODEL",
        "OPENROUTER_MODEL_JUDGE_PRIMARY", "OPENROUTER_MODEL_LOGICAL_AUDITOR",
        "OPENROUTER_MODEL_LOGICAL_AUDITOR_FALLBACK", "SCP_BUDGET_ROUTING",
        "SCP_LLM_ATTEMPT_TIMEOUT_SECONDS", "SCP_LLM_BREAKER_COOLDOWN_SEC",
        "SCP_LLM_BREAKER_THRESHOLD", "SCP_LLM_HEDGE", "SCP_LLM_HEDGE_MAX_SECONDS",
        "SCP_LLM_REQUEST_TIMEOUT_SECONDS", "SCP_MULTI_LLM_CROSSCHECK"
    ],
    "Knowledge & Data Sources": [
        "ALPHAVANTAGE_API_KEY", "COURTLISTENER_TOKEN", "ERIC_API_KEY",
        "FRED_API_KEY", "NCBI_API_KEY", "NOAA_API_KEY", "PUBMED_API_KEY",
        "WIKIART_API_KEY", "NEWSAPI_API_KEY", "SCP_FREE_API_CATALOG_TTL_SEC",
        "SCP_KW_ENABLE", "WIKIPEDIA_USER_AGENT", "SCP_WHY_WIKIPEDIA_BASE",
        "SCP_WHY_NASA_BASE", "SCP_WHY_OPENMETEO_BASE"
    ],
    "Meta & Cognitive System": [
        "SCP_CAPABILITY_LEVEL", "SCP_COGNITIVE_LAYERS", "SCP_METAWHY_ANALYSIS_INTERVAL",
        "SCP_WHY_DATA_FLOW", "SCP_WHY_SECURITY_THREAT", "SCP_WHY_TYPE_INFERENCE",
        "SCP_SELF_CONSISTENCY_N", "SCP_DOUBT_INTERVAL_SEC", "SCP_DOUBT_BACKLOG_LIMIT"
    ],
    "Automation & Controls (PC & Web)": [
        "SCP_PC_WORKING_DIR", "SCP_BROWSER_PATH", "SCP_BROWSER_DEBUG_PORT",
        "SCP_MODEL_VERSION"
    ],
    "AutoFix & Self-Healing Engine": [
        "SCP_AUTOFIX_ENABLED", "SCP_AUTOFIX_MODE", "SCP_AUTOFIX_MAX_RETRIES",
        "SCP_AUTOFIX_TIMEOUT"
    ]
}

# Find all remaining unassigned
assigned = set()
for grp, vlist in logical_groups.items():
    assigned.update(vlist)

unassigned = [k for k in app_missing if k not in assigned]
print(f"Assigned to pre-defined groups: {len(assigned & set(app_missing))}")
print(f"Unassigned: {len(unassigned)}")

# Group unassigned by subsystem
unassigned_by_sub = defaultdict(list)
for k in unassigned:
    sub = var_details[k]['subsystem']
    unassigned_by_sub[sub].append(k)

for sub, vlist in sorted(unassigned_by_sub.items()):
    print(f"  {sub} ({len(vlist)}): {', '.join(vlist)}")
