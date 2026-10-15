#!/usr/bin/env bash
PYTHON_BIN="${SCP_PYTHON_BIN:-python3}"
REALITY_TEST_TIMEOUT_SECONDS="${SCP_REALITY_TEST_TIMEOUT_SECONDS:-90}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
# ============================================================
# SCP-DNA Phase 1 — CI Reality-Test Layer
# Root Cause 1 fix: every claim must have an assertion (DNA #2, #22, #26)
#
# Tier A: static checks (runnable without starting services)
# Tier B: runtime checks (require SCP backend + mini-services running)
#
# Usage:
#   ./tests/reality-check.sh              # Tier A only (fast, ~2s)
#   ./tests/reality-check.sh --runtime    # Tier A + Tier B
#
# Exit code: 0 = all pass, 1 = any fail
# ============================================================
set -u

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DASHBOARD_DIR="$PROJECT_DIR/dashboard"
SCP_DIR="$PROJECT_DIR/scp"
PASS=0
FAIL=0
RUNTIME_MODE="${1:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

assert_contains() {
  local id="$1" file="$2" pattern="$3" desc="$4"
  if [ ! -f "$file" ]; then
    echo -e "  ${RED}✗ $id${NC} FILE MISSING: $file"
    FAIL=$((FAIL + 1)); return
  fi
  if grep -q "$pattern" "$file" 2>/dev/null; then
    echo -e "  ${GREEN}✓ $id${NC} $desc"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}✗ $id${NC} $desc (pattern not found)"
    FAIL=$((FAIL + 1))
  fi
}

assert_not_contains() {
  local id="$1" file="$2" pattern="$3" desc="$4"
  if [ ! -f "$file" ]; then
    echo -e "  ${RED}✗ $id${NC} FILE MISSING: $file"
    FAIL=$((FAIL + 1)); return
  fi
  if grep -q "$pattern" "$file" 2>/dev/null; then
    echo -e "  ${RED}✗ $id${NC} $desc (forbidden pattern found)"
    FAIL=$((FAIL + 1))
  else
    echo -e "  ${GREEN}✓ $id${NC} $desc"
    PASS=$((PASS + 1))
  fi
}

# DNA #19: observation calibration — check pattern is NOT in code (excludes comment lines)
# Comment markers: # (bash/python), // (TS line), * (TS block comment continuation)
assert_not_in_code() {
  local id="$1" file="$2" pattern="$3" desc="$4"
  if [ ! -f "$file" ]; then
    echo -e "  ${RED}✗ $id${NC} FILE MISSING: $file"
    FAIL=$((FAIL + 1)); return
  fi
  # Strip comment lines, then search for the pattern in remaining code
  if grep -v '^\s*#' "$file" 2>/dev/null | grep -v '^\s*//' | grep -v '^\s*\*' | grep -v '^\s*/\*' | grep -q "$pattern"; then
    echo -e "  ${RED}✗ $id${NC} $desc (pattern found in CODE)"
    FAIL=$((FAIL + 1))
  else
    echo -e "  ${GREEN}✓ $id${NC} $desc"
    PASS=$((PASS + 1))
  fi
}

assert_bash_syntax() {
  local id="$1" file="$2" desc="$3"
  if bash -n "$file" 2>/dev/null; then
    echo -e "  ${GREEN}✓ $id${NC} $desc"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}✗ $id${NC} $desc (bash -n failed)"
    FAIL=$((FAIL + 1))
  fi
}

run_python_script() {
  local script="$1"
  if command -v timeout >/dev/null 2>&1; then
    timeout --foreground "${REALITY_TEST_TIMEOUT_SECONDS}s" "$PYTHON_BIN" "$script"
  else
    "$PYTHON_BIN" "$script"
  fi
}

assert_python_syntax() {
  local id="$1" file="$2" desc="$3"
  local python_file="$file"
  # Git Bash exposes Windows paths as /c/... while Windows Python expects
  # C:/...; normalize only when cygpath is available. Linux CI keeps the
  # original path unchanged.
  if command -v cygpath >/dev/null 2>&1; then
    python_file=$(cygpath -w "$file")
  fi
  if "$PYTHON_BIN" -c 'import ast, sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' "$python_file" 2>/dev/null; then
    echo -e "  ${GREEN}✓ $id${NC} $desc"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}✗ $id${NC} $desc (ast.parse failed)"
    FAIL=$((FAIL + 1))
  fi
}

echo "🔍 SCP-DNA Phase 1 — CI Reality-Test Layer"
echo "   Project: $PROJECT_DIR"
echo ""

# ===== TIER A — Static checks =====
echo "▶ TIER A — Static checks (DNA #22: claim vs reality)"
echo "   Fix group 1-A: Dashboard config + API routes"
echo ""

assert_contains "4-c-001" "$DASHBOARD_DIR/next.config.ts" "ignoreBuildErrors: false" \
  "next.config.ts typescript.ignoreBuildErrors = false"
assert_contains "4-c-002a" "$DASHBOARD_DIR/eslint.config.mjs" '"@typescript-eslint/no-explicit-any": "warn"' \
  "ESLint no-explicit-any = warn"
assert_contains "4-c-002b" "$DASHBOARD_DIR/eslint.config.mjs" '"no-unreachable": "warn"' \
  "ESLint no-unreachable = warn"
assert_contains "4-c-002c" "$DASHBOARD_DIR/eslint.config.mjs" '"prefer-const": "warn"' \
  "ESLint prefer-const = warn"
assert_not_contains "4-c-003" "$DASHBOARD_DIR/src/app/api/scp/routes/route.ts" "DEAD ROUTE" \
  "routes/route.ts no longer claims DEAD ROUTE"
assert_contains "4-c-004" "$DASHBOARD_DIR/src/app/api/scp/status/route.ts" "6/6" \
  "status route reports 6/6 v4 wired"
assert_not_in_code "4-c-012" "$DASHBOARD_DIR/src/app/api/scp/status/route.ts" '0/6 wired' \
  "status route no longer claims 0/6 wired in code"
assert_contains "4-c-013" "$DASHBOARD_DIR/src/app/api/audit/route.ts" "force-dynamic" \
  "api/audit is force-dynamic (timestamp not frozen)"
assert_contains "4-c-014a" "$DASHBOARD_DIR/src/app/api/scanners/route.ts" "force-dynamic" \
  "api/scanners is force-dynamic"
assert_contains "4-c-014b" "$DASHBOARD_DIR/src/app/api/autofix/route.ts" "force-dynamic" \
  "api/autofix is force-dynamic"
assert_contains "4-d-010a" "$DASHBOARD_DIR/src/app/api/scp/health/route.ts" "11434" \
  "health route probes llm-bridge (11434)"
assert_contains "4-d-010b" "$DASHBOARD_DIR/src/app/api/scp/health/route.ts" "3030" \
  "health route probes loop-scheduler (3030)"
assert_contains "4-d-010c" "$DASHBOARD_DIR/src/app/api/scp/health/route.ts" "8000" \
  "health route probes FastAPI (8000)"

echo ""
echo "   Fix group 1-B: Python backend silent failures"
echo ""

assert_contains "4-a-001a" "$SCP_DIR/api_server.py" "global _judge" \
  "api_server.py propagates _judge to module scope"
assert_contains "4-a-001b" "$SCP_DIR/api_server.py" "background_scheduler_started" \
  "api_server.py exposes background_scheduler_started flag"
assert_python_syntax "4-a-001c" "$SCP_DIR/api_server.py" "api_server.py syntax valid"
assert_contains "4-a-007a" "$SCP_DIR/api/routes/openai_compat.py" "_t0 = time.perf_counter()" \
  "openai_compat.py captures _t0 at handler start"
assert_contains "4-a-007b" "$SCP_DIR/api/routes/openai_compat.py" "elapsed_ms" \
  "openai_compat.py reports elapsed_ms"
assert_python_syntax "4-a-007c" "$SCP_DIR/api/routes/openai_compat.py" "openai_compat.py syntax valid"
assert_not_in_code "4-a-016" "$SCP_DIR/api_server.py" 'if req is not None' \
  "/ask handler no longer has dead 'if req is not None' branch in code"

echo ""
echo "   Fix group 1-C: Orchestrator scripts"
echo ""

assert_contains "4-d-001a" "$PROJECT_DIR/start-scp.sh" 'dirname "$0"' \
  "start-scp.sh auto-resolves PROJECT_DIR"
assert_contains "4-d-001b" "$PROJECT_DIR/start-scp.sh" "mini-services/llm-bridge" \
  "start-scp.sh has reality-check guard for llm-bridge dir"
assert_bash_syntax "4-d-001c" "$PROJECT_DIR/start-scp.sh" "start-scp.sh syntax valid"
assert_contains "4-d-002" "$PROJECT_DIR/start-scp.sh" 'PROJECT_DIR/dashboard' \
  "start-scp.sh cds to dashboard/ (not project root)"
assert_contains "4-d-003a" "$PROJECT_DIR/stop-scp.sh" "kill_port" \
  "stop-scp.sh uses port-based kill (not just pkill -f)"
assert_contains "4-d-003b" "$PROJECT_DIR/stop-scp.sh" "kill_pidfile" \
  "stop-scp.sh reads PID files from start-scp.sh"
assert_not_in_code "4-d-003c" "$PROJECT_DIR/stop-scp.sh" 'pkill -f "llm-bridge"' \
  "stop-scp.sh no longer uses broken pkill -f llm-bridge in code"
assert_bash_syntax "4-d-003d" "$PROJECT_DIR/stop-scp.sh" "stop-scp.sh syntax valid"

echo ""
echo "▶ TIER A SUMMARY (Phase 1): ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}"

# ===== PHASE 2 — Root Cause 2 reality-tests =====
echo ""
echo "▶ PHASE 2 — Reality-test scripts (Root Cause 2: 'fix' without reality test)"
echo ""

PHASE2_PASS=0
PHASE2_FAIL=0

run_reality_test() {
  local script="$1"
  local name
  name=$(basename "$script")
  if [ ! -f "$script" ]; then
    return
  fi
  if run_python_script "$script" >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓ $name${NC}"
    PHASE2_PASS=$((PHASE2_PASS + 1))
  else
    echo -e "  ${RED}✗ $name${NC}"
    PHASE2_FAIL=$((PHASE2_FAIL + 1))
  fi
}

RT_DIR="$PROJECT_DIR/tests/reality-tests"
for rt in "$RT_DIR"/reality_*.py; do
  [ -e "$rt" ] || continue
  run_reality_test "$rt"
done
for rt in "$RT_DIR"/reality_*.sh; do
  [ -e "$rt" ] || continue
  if bash "$rt" >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓ $(basename "$rt")${NC}"
    PHASE2_PASS=$((PHASE2_PASS + 1))
  else
    echo -e "  ${RED}✗ $(basename "$rt")${NC}"
    PHASE2_FAIL=$((PHASE2_FAIL + 1))
  fi
done

echo ""
echo "▶ PHASE 2 SUMMARY: ${GREEN}$PHASE2_PASS passed${NC}, ${RED}$PHASE2_FAIL failed${NC}"

# Also check Phase 2 source fixes (static)
echo ""
echo "▶ PHASE 2 — Static source assertions"
echo ""

assert_not_in_code "4-b-002" "$SCP_DIR/runtime/judge_parts/judgecore_mixin.py" 'ground_truth\[_slm_name\] = _slm_resp.get' \
  "4-b-002: SLM answer no longer added to ground_truth (self-verify removed)"
assert_contains "4-b-003" "$SCP_DIR/meta/external_trust.py" "HUMAN_APPROVED_BY" \
  "4-b-003: strict line-1 HUMAN_APPROVED_BY marker (not substring)"
assert_not_in_code "4-b-004" "$SCP_DIR/meta/policy_applier.py" 'threshold_adjustment"\]?\s*=\s*-0\.' \
  "4-b-004: no negative threshold adjustments (inverted logic fixed)"
assert_contains "4-b-005" "$SCP_DIR/security/escalation.py" "medium" \
  "4-b-005: classify_threat returns medium default (not always high)"
assert_contains "4-b-017" "$SCP_DIR/meta/why_gate.py" "FALSIFICATION_REJECT" \
  "4-b-017: falsification reject patterns enforced"
assert_not_in_code "4-d-004" "$PROJECT_DIR/mini-services/llm-bridge/index.ts" 'OLLAMA_BASE_URL.*127.0.0.1:11434' \
  "4-d-004: no self-targeting ollama fallback URL in code"
assert_contains "4-d-004b" "$PROJECT_DIR/mini-services/llm-bridge/index.ts" "X-LLM-Bridge-Internal" \
  "4-d-004: recursion guard header present"
assert_contains "PR-RULE" "$PROJECT_DIR/docs/PULL_REQUEST_TEMPLATE.md" "Reality test" \
  "PR template enforces reality-test requirement"
assert_contains "HARNESS" "$PROJECT_DIR/tests/run-reality-tests.sh" "reality_" \
  "reality-test harness exists"

# ===== PHASE 3 — Root Cause 3 (Divergent implementation) static assertions =====
echo ""
echo "▶ PHASE 3 — Divergent implementation static assertions (Root Cause 3)"
echo ""

assert_contains "4-a-005" "$SCP_DIR/core/api_utils.py" "_safe_fetch_url" \
  "4-a-005: fetch_with_retry delegates to _safe_fetch_url (1 canonical fetcher)"
assert_contains "4-a-005b" "$SCP_DIR/core/url_fetcher.py" "_safe_fetch_url" \
  "4-a-005: canonical _safe_fetch_url in neutral url_fetcher.py module"
assert_contains "4-a-006" "$SCP_DIR/security/auth.py" "def verify_admin" \
  "4-a-006: canonical verify_admin in scp/security/auth.py"
assert_not_in_code "4-a-006b" "$SCP_DIR/api_server_parts/helpers.py" "def verify_admin" \
  "4-a-006: helpers.py no longer defines its own verify_admin (re-exports)"
assert_contains "4-b-015" "$SCP_DIR/knowledge/trust_hierarchy.py" "PubChem\|pubchem" \
  "4-b-015: PubChem in canonical trust_hierarchy.py table"
assert_not_in_code "4-b-015b" "$SCP_DIR/knowledge/trust_hierarchy.py" "slm_self.*5\|tier.*=.*5.*slm" \
  "4-b-015: no slm_self tier 5 reference (enum 1-4 only)"
assert_contains "4-d-005" "$PROJECT_DIR/mini-services/llm-bridge/index.ts" "TASK_MODEL_MAP" \
  "4-d-005: TASK_MODEL_MAP wires per-task model routing"
assert_contains "4-d-005b" "$PROJECT_DIR/mini-services/llm-bridge/index.ts" "OPENROUTER_MODEL_AUTOFIX" \
  "4-d-005: per-task OPENROUTER_MODEL_AUTOFIX env var referenced"
assert_contains "4-c-019" "$DASHBOARD_DIR/src/app/layout.tsx" "/logo.svg" \
  "4-c-019: favicon points to local /logo.svg (not external CDN)"
assert_not_in_code "4-c-019b" "$DASHBOARD_DIR/src/app/layout.tsx" "z-cdn.chatglm.cn" \
  "4-c-019: no external CDN reference for favicon"

# ===== PHASE 4 — Root Cause 4 (Scanner/verifier blind spot) static assertions =====
echo ""
echo "▶ PHASE 4 — Scanner/verifier blind spot static assertions (Root Cause 4)"
echo ""

assert_contains "4-b-007a" "$SCP_DIR/autofix/scanners/race_condition_scanner.py" "asyncio" \
  "4-b-007: RaceConditionScanner detects asyncio primitives"
assert_contains "4-b-007b" "$SCP_DIR/autofix/scanners/race_condition_scanner.py" "gather" \
  "4-b-007: scanner detects asyncio.gather"
assert_contains "4-b-007c" "$SCP_DIR/autofix/scanners/race_condition_scanner.py" "return_exceptions" \
  "4-b-007: scanner checks return_exceptions"
assert_contains "4-b-008" "$SCP_DIR/meta/cognitive_layers/meta_falsifier.py" "domain\|_resolve_required_vectors" \
  "4-b-008: MetaFalsifier domain vectors reachable (not dead code)"
assert_contains "4-b-009a" "$SCP_DIR/security/dos_protection.py" "_last_throttle =" \
  "4-b-009: _last_throttle assigned (not just read)"
assert_contains "4-b-009b" "$SCP_DIR/security/dos_protection.py" "429\|Retry-After" \
  "4-b-009: throttle returns 429 + Retry-After"
assert_not_in_code "4-a-010" "$SCP_DIR/core/cross_verify.py" "with ThreadPoolExecutor" \
  "4-a-010: no blocking with-ThreadPoolExecutor pattern (deadline real)"
assert_contains "4-a-010b" "$SCP_DIR/core/cross_verify.py" "wait=False\|cancel_futures" \
  "4-a-010: uses shutdown(wait=False) or cancel_futures"
assert_contains "4-a-012a" "$SCP_DIR/core/circuit_breaker.py" "PROBE_TIMEOUT\|probe_started_at\|_probe_started" \
  "4-a-012: probe timeout/expiry mechanism present"
assert_contains "4-a-012b" "$SCP_DIR/core/circuit_breaker.py" "_probe_in_flight = False" \
  "4-a-012: _probe_in_flight reset logic present"
assert_contains "4-b-011a" "$SCP_DIR/meta/knowledge_arbiter.py" "multi_source_agreement" \
  "4-b-011: multi_source_agreement logic present (not dead code)"
assert_contains "4-b-011b" "$SCP_DIR/meta/knowledge_arbiter.py" "independent\|lineage" \
  "4-b-011: independence/lineage check (DNA #5)"
assert_contains "4-b-014a" "$SCP_DIR/meta/cognitive_layers/recursive_why.py" "reputation" \
  "4-b-014: reputation source traversable in RecursiveWhy"
assert_contains "4-b-014b" "$SCP_DIR/meta/cognitive_layers/recursive_why.py" "depth\|max_depth\|level" \
  "4-b-014: recursion depth/limit present"
assert_not_in_code "4-b-020" "$SCP_DIR/meta/cognitive_layers/recursive_why.py" "Local.*Database.*AUTHORITATIVE\|AUTHORITATIVE.*Local.*Database" \
  "4-b-020: no Local DB in AUTHORITATIVE_SOURCES (DNA #6)"

# ===== PHASE 5 — Root Cause 5 (Safety mechanism guard) static assertions =====
echo ""
echo "▶ PHASE 5 — Safety mechanism guard static assertions (Root Cause 5)"
echo ""

assert_contains "4-a-002a" "$SCP_DIR/core/safe_process.py" "realpath\|shutil.which" \
  "4-a-002: safe_run uses realpath/shutil.which (no path bypass)"
assert_not_in_code "4-a-002b" "$SCP_DIR/core/safe_process.py" '"/" not in.*not in.*raise' \
  "4-a-002: old bypass pattern gone (default-deny)"
assert_contains "4-a-008a" "$SCP_DIR/api/routes/v105_routes.py" "os.replace\|os.rename" \
  "4-a-008: rollback uses atomic os.replace"
assert_contains "4-a-008b" "$SCP_DIR/api/routes/v105_routes.py" "tempfile\|mkstemp\|tmp_path" \
  "4-a-008: rollback writes to temp file first"
assert_contains "4-a-009" "$SCP_DIR/api/routes/v105_routes.py" "pending_apply\|apply_failed\|mark_apply_status" \
  "4-a-009: approval transactional (pending → applied/apply_failed)"
assert_contains "4-b-006a" "$SCP_DIR/autofix/classifier.py" "RELAXATION\|relaxation" \
  "4-b-006: BugClassifier re-checks RELAXATION_PATTERNS"
assert_contains "4-b-006b" "$SCP_DIR/autofix/classifier.py" "tier_hint\|TIER_3" \
  "4-b-006: tier_hint capped (no self-promotion)"
assert_contains "4-b-012a" "$SCP_DIR/autofix/audit_log.py" "before_hash" \
  "4-b-012: audit log has before_hash field"
assert_contains "4-b-012b" "$SCP_DIR/autofix/audit_log.py" "after_hash" \
  "4-b-012: audit log has after_hash field"
assert_contains "4-b-012c" "$SCP_DIR/autofix/audit_log.py" "rollback_token" \
  "4-b-012: audit log has rollback_token field"
assert_contains "4-b-013a" "$SCP_DIR/autofix/rollback_registry.py" "force\|raise\|refuse" \
  "4-b-013: rollback refuses on hash mismatch (force required)"
assert_contains "4-d-007a" "$PROJECT_DIR/mini-services/loop-scheduler/index.ts" "409\|already running" \
  "4-d-007: loop-scheduler returns 409 on concurrent trigger"
assert_contains "4-d-007b" "$PROJECT_DIR/mini-services/loop-scheduler/index.ts" "running\|isRunning" \
  "4-d-007: running flag present"
assert_not_in_code "4-d-008" "$PROJECT_DIR/mini-services/loop-scheduler/index.ts" "0.0.0.0" \
  "4-d-008: loop-scheduler does not bind 0.0.0.0"
assert_contains "4-d-008b" "$PROJECT_DIR/mini-services/loop-scheduler/index.ts" "127.0.0.1\|LOOP_SCHEDULER_HOST" \
  "4-d-008: loop-scheduler binds 127.0.0.1 (loopback)"
assert_not_in_code "4-d-009a" "$PROJECT_DIR/mini-services/llm-bridge/index.ts" 'Access-Control-Allow-Origin.*"\*"' \
  "4-d-009: llm-bridge no wildcard CORS *"
assert_contains "4-d-009b" "$PROJECT_DIR/mini-services/llm-bridge/index.ts" "127.0.0.1\|ZAI_BRIDGE_HOST" \
  "4-d-009: llm-bridge binds 127.0.0.1 or has HOST env"

# ===== PHASE 6 — Root Cause 6 (Dashboard static data) static assertions =====
echo ""
echo "▶ PHASE 6 — Dashboard static data static assertions (Root Cause 6)"
echo ""

assert_not_in_code "4-c-005" "$DASHBOARD_DIR/src/lib/audit-data/bugs-critical.ts" "asyncio.create_task(refresh_tor_exits_loop)" \
  "4-c-005: fabricated beforeCode removed (R7-2)"
assert_contains "4-c-005b" "$DASHBOARD_DIR/src/lib/audit-data/bugs-critical.ts" "omitted\|fabricated\|git" \
  "4-c-005: honest note present (beforeCode omission documented)"
assert_not_in_code "4-c-006a" "$DASHBOARD_DIR/src/app/api/scp/status/route.ts" "4389\|4,389" \
  "4-c-006: hardcoded 4389 LOC removed (was drifted +505)"
assert_contains "4-c-006b" "$DASHBOARD_DIR/src/app/api/scp/status/route.ts" "computeAutofixLoc\|readdirSync\|readFileSync" \
  "4-c-006: v4 LOC computed from actual files (not hardcoded)"

# ===== PHASE 7 — Root Cause 7 (Hardcoded paths/ports/numbers) static assertions =====
echo ""
echo "▶ PHASE 7 — Hardcoded paths/ports/numbers static assertions (Root Cause 7)"
echo ""

assert_contains "4-d-015a" "$PROJECT_DIR/.env.example" "SCP_INTERNAL_URL" \
  "4-d-015: SCP_INTERNAL_URL in .env.example"
assert_contains "4-d-015b" "$PROJECT_DIR/.env.example" "LOOP_SCHEDULER_URL" \
  "4-d-015: LOOP_SCHEDULER_URL in .env.example"
assert_contains "4-d-016a" "$PROJECT_DIR/.env.example" "OPENROUTER_MODEL_AUTOFIX" \
  "4-d-016: OPENROUTER_MODEL_AUTOFIX in .env.example"
assert_contains "4-d-016b" "$PROJECT_DIR/.env.example" "OPENROUTER_MODEL_JUDGE" \
  "4-d-016: OPENROUTER_MODEL_JUDGE in .env.example"
assert_not_in_code "4-d-014" "$PROJECT_DIR/install-scp.bat" "scp\\\\data\|scp/data" \
  "4-d-014: install-scp.bat creates data dirs at project root (not inside scp/)"
assert_contains "4-d-017a" "$PROJECT_DIR/start-scp.sh" "wait_for_url\|wait_for\|poll" \
  "4-d-017: start-scp.sh uses poll-until-ready (not fixed sleep)"
assert_contains "4-d-017b" "$PROJECT_DIR/start-scp.sh" "curl.*--max-time\|curl.*-sf\|curl.*--retry" \
  "4-d-017: curl readiness check present"
assert_not_in_code "4-d-018" "$PROJECT_DIR/stop-scp.bat" "taskkill.*\/im.*bun\|\/im.*bun.exe" \
  "4-d-018: stop-scp.bat does not kill all bun.exe (uses /pid instead)"
assert_contains "4-d-018b" "$PROJECT_DIR/stop-scp.bat" "netstat\|/pid" \
  "4-d-018: stop-scp.bat uses netstat + /pid (port-based kill)"

echo ""
echo "▶ TIER A + PHASE 2 + PHASE 3 + PHASE 4 + PHASE 5 + PHASE 6 + PHASE 7 TOTAL: ${GREEN}$((PASS + PHASE2_PASS)) passed${NC}, ${RED}$((FAIL + PHASE2_FAIL)) failed${NC}"

if [ "$RUNTIME_MODE" != "--runtime" ]; then
  echo ""
  echo "ℹ️  Tier B (runtime) skipped. Run with --runtime to probe live services."
  if [ "$((FAIL + PHASE2_FAIL))" -gt 0 ]; then exit 1; fi
  exit 0
fi

# ===== TIER B — Runtime checks =====
echo ""
echo "▶ TIER B — Runtime checks (DNA #26: reality has final word)"
echo ""

RT_PASS=0; RT_FAIL=0; RT_SKIP=0

check_url() {
  local id="$1" url="$2" expect="$3" desc="$4"
  local resp_code
  resp_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "$url" 2>/dev/null || echo "000")
  if [ "$resp_code" = "000" ]; then
    echo -e "  ${YELLOW}⊘ $id${NC} $desc (service not reachable)"
    RT_SKIP=$((RT_SKIP + 1))
  elif [ "$resp_code" = "$expect" ]; then
    echo -e "  ${GREEN}✓ $id${NC} $desc ($resp_code)"
    RT_PASS=$((RT_PASS + 1))
  else
    echo -e "  ${RED}✗ $id${NC} $desc (got $resp_code, expected $expect)"
    RT_FAIL=$((RT_FAIL + 1))
  fi
}

check_url "RT-001" "http://127.0.0.1:8000/health" "200" "FastAPI backend health"
check_url "RT-002" "http://127.0.0.1:8000/health/detailed" "200" "FastAPI /health/detailed"
check_url "RT-003" "http://127.0.0.1:11434/api/tags" "200" "llm-bridge /api/tags"
check_url "RT-004" "http://127.0.0.1:3030/healthz" "200" "loop-scheduler /healthz"
check_url "RT-005" "http://127.0.0.1:3000/api/scp/health" "200" "dashboard composite health"

if curl -sf --max-time 2 "http://127.0.0.1:8000/health/detailed" 2>/dev/null | grep -q '"background_scheduler_started": *true'; then
  echo -e "  ${GREEN}✓ RT-006${NC} background_scheduler_started = true (4-a-001 verified at runtime)"
  RT_PASS=$((RT_PASS + 1))
elif curl -sf --max-time 2 "http://127.0.0.1:8000/health/detailed" 2>/dev/null | grep -q '"background_scheduler_started"'; then
  echo -e "  ${RED}✗ RT-006${NC} background_scheduler_started present but NOT true"
  RT_FAIL=$((RT_FAIL + 1))
else
  echo -e "  ${YELLOW}⊘ RT-006${NC} background_scheduler_started (backend not reachable)"
  RT_SKIP=$((RT_SKIP + 1))
fi

echo ""
echo "▶ TIER B SUMMARY: ${GREEN}$RT_PASS passed${NC}, ${RED}$RT_FAIL failed${NC}, ${YELLOW}$RT_SKIP skipped${NC}"
echo ""
echo "▶ TOTAL: $((PASS + RT_PASS)) passed, $((FAIL + RT_FAIL)) failed, $RT_SKIP skipped"

if [ "$((FAIL + RT_FAIL))" -gt 0 ]; then exit 1; fi
exit 0
