#!/usr/bin/env bash
# ============================================================
# SCP START ALL — 1 lệnh chạy toàn bộ hệ thống
# Usage:  ./start-scp.sh          (foreground, Ctrl+C để dừng tất cả)
#         ./start-scp.sh daemon   (background, ghi log vào /tmp)
# ============================================================
set -e

# Fix 4-d-001: auto-resolve PROJECT_DIR to the directory containing this script.
# The root is derived from this script, so `cd $PROJECT_DIR/mini-services/...`
# remains portable across checkouts and does not depend on a sandbox path.
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="/tmp/scp-logs"
mkdir -p "$LOG_DIR"

# Reality test (DNA #26): fail loud if PROJECT_DIR doesn't actually contain
# the SCP mini-services tree. Better to exit 1 here than to silently cd-fail later.
if [ ! -d "$PROJECT_DIR/mini-services/llm-bridge" ]; then
  echo "ERROR: PROJECT_DIR wrong: $PROJECT_DIR (mini-services/llm-bridge not found)" >&2
  echo "       Script must be run from inside the scp-system/ directory." >&2
  exit 1
fi

# --- cleanup any old instances ---
# Note: pkill -f "llm-bridge" / "loop-scheduler" match NOTHING in `bun run dev`
# cmdline (see Finding 4-d-003). Kept here for the python3 -m scp match, but the
# real cleanup is done by stop-scp.sh using port+PID-file based kill.
echo "🛑 Stopping existing services..."
pkill -f "python3 -m scp" 2>/dev/null || true
pkill -f "llm-bridge" 2>/dev/null || true
pkill -f "loop-scheduler" 2>/dev/null || true
sleep 2

# Fix 4-d-017: poll-until-ready helper (replaces fixed `sleep 3` / `sleep 1`).
# Previously: hardcoded `sleep 3` (after LLM Bridge launch) and `sleep 1`
# (after Loop Scheduler launch). On slow boots (cold cache, NFS, encrypted disk)
# bun cold-start can take 5-10s, so the downstream service started before
# the upstream was reachable → first LLM call 502s, scheduler race condition.
#
# This helper polls every 1s up to `max` seconds and returns 0 as soon as the
# URL responds 2xx. Returns 1 (non-zero) on timeout — combined with `set -e`
# this aborts startup so the operator sees the failure instead of a cascade.
wait_for_url() {
  local url="$1"
  local name="$2"
  local max="${3:-30}"
  local i=0
  echo "  ⏳ Waiting for $name at $url (max ${max}s)..."
  while [ "$i" -lt "$max" ]; do
    if curl -sf --max-time 1 "$url" >/dev/null 2>&1; then
      echo "  ✅ $name ready after ${i}s"
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  echo "  ❌ $name NOT ready after ${max}s" >&2
  return 1
}

MODE="${1:-foreground}"

start_services() {
  echo "🚀 Starting SCP system (4 services)..."

  # 1. LLM Bridge (port 8081) — must start FIRST (SCP depends on it)
  echo "  [1/4] LLM Bridge → port 8081"
  cd "$PROJECT_DIR/mini-services/llm-bridge"
  if [ "$MODE" = "daemon" ]; then
    setsid nohup bun run dev > "$LOG_DIR/llm-bridge.log" 2>&1 &
  else
    setsid nohup bun run dev > "$LOG_DIR/llm-bridge.log" 2>&1 &
  fi
  echo $! > "$LOG_DIR/llm-bridge.pid"

  # Fix 4-d-017: poll /api/tags instead of `sleep 3`. On slow boots the bridge
  # can take 5-10s to bind; a fixed 3s sleep causes SCP's first LLM call to 502.
  # 30s cap (was 3s). Returns 1 on timeout → aborts startup (set -e).
  wait_for_url "http://127.0.0.1:8081/api/tags" "LLM Bridge" 30 \
    || { echo "ERROR: LLM Bridge not ready — aborting startup. Check $LOG_DIR/llm-bridge.log" >&2; exit 1; }

  # 2. Loop Scheduler (port 3030) — optional but useful
  echo "  [2/4] Loop Scheduler → port 3030"
  cd "$PROJECT_DIR/mini-services/loop-scheduler"
  SCP_BASE_URL="${SCP_BASE_URL:-http://127.0.0.1:8000}" \
    LLM_BRIDGE_URL="${LLM_BRIDGE_URL:-http://127.0.0.1:8081}" \
    LOOP_LOG_PATH="$PROJECT_DIR/data/loop_runs.jsonl" \
    setsid nohup bun run dev > "$LOG_DIR/loop-scheduler.log" 2>&1 &
  echo $! > "$LOG_DIR/loop-scheduler.pid"

  # Fix 4-d-017: poll /healthz instead of `sleep 1`. Same race-condition fix.
  wait_for_url "http://127.0.0.1:3030/healthz" "Loop Scheduler" 30 \
    || { echo "ERROR: Loop Scheduler not ready — aborting startup. Check $LOG_DIR/loop-scheduler.log" >&2; exit 1; }

  # 3. SCP Python (port 8000) — boots in ~60s
  echo "  [3/4] SCP Python → port 8000 (booting ~60s, please wait...)"
  cd "$PROJECT_DIR"
  setsid nohup python3 -m scp 8000 > "$LOG_DIR/scp-server.log" 2>&1 &
  echo $! > "$LOG_DIR/scp-server.pid"

  # 4. Dashboard Next.js (port 3000)
  # Fix 4-d-002: previously `cd "$PROJECT_DIR"` ran `bun run dev` against
  # whichever package.json lived at $PROJECT_DIR — which on this layout is
  # nothing (no package.json at the repository root). The real SCP dashboard is
  # at $PROJECT_DIR/dashboard/.
  #
  # PORT CONFLICT NOTE: the SCP dashboard
  # ($PROJECT_DIR/dashboard/package.json: "dev": "next dev -p 3000") uses port
  # 3000. If you need both running simultaneously, set DASHBOARD_PORT=3001 (or
  # any free port) in the environment. We pass `-- -p $DASHBOARD_PORT` after
  # `bun run dev`; next dev accepts the LAST -p flag, so this overrides the
  # hardcoded 3000 in package.json without editing that file.
  DASHBOARD_PORT="${DASHBOARD_PORT:-3000}"
  echo "  [4/4] Dashboard Next.js → port $DASHBOARD_PORT"
  cd "$PROJECT_DIR/dashboard"
  setsid nohup bun run dev -- -p "$DASHBOARD_PORT" > "$LOG_DIR/dashboard.log" 2>&1 &
  echo $! > "$LOG_DIR/dashboard.pid"

  # --- wait for SCP to finish booting ---
  # Fix 4-d-017: use wait_for_url with 120s cap (was 60s = 30 iterations × 2s).
  # SCP's RealLearningEngine + KB init can exceed 60s on first boot with a cold
  # cache and large KB. Non-zero exit on timeout so the operator sees the
  # failure instead of a misleading "🎉 SCP SYSTEM RUNNING" banner.
  echo ""
  echo "⏳ Waiting for SCP to finish booting (polling /health, max 120s)..."
  wait_for_url "http://127.0.0.1:8000/health" "SCP Python" 120 \
    || { echo "ERROR: SCP not ready after 120s — check $LOG_DIR/scp-server.log" >&2; exit 1; }

  # --- final status ---
  echo ""
  echo "============================================================"
  echo "🎉 SCP SYSTEM RUNNING"
  echo "============================================================"
  echo ""
  echo "  Dashboard:       http://localhost:3000"
  echo "  SCP /health:     http://localhost:8000/health"
  echo "  SCP /ask:        curl -X POST http://localhost:8000/ask \\"
  echo "                     -H 'Content-Type: application/json' \\"
  echo "                     -d '{\"question\":\"What is the capital of France?\"}'"
  echo "  LLM Bridge:      http://localhost:8081/api/tags"
  echo "  Loop Scheduler:  http://localhost:3030/"
  echo ""
  echo "  Logs: $LOG_DIR/{llm-bridge,loop-scheduler,scp-server,dashboard}.log"
  echo "  PIDs: $LOG_DIR/*.pid"
  echo ""
  echo "  Stop all:  ./stop-scp.sh   (or pkill -f 'python3 -m scp|llm-bridge|loop-scheduler|next')"
  echo "============================================================"
}

start_services

if [ "$MODE" != "daemon" ]; then
  echo ""
  echo "📋 Services running in background. Logs at $LOG_DIR/"
  echo "   Press Ctrl+C to exit this script (services keep running)."
  echo "   Run ./stop-scp.sh to stop all services."
  # Keep script alive so user can Ctrl+C
  trap 'echo ""; echo "🛑 Stopping all services..."; pkill -f "python3 -m scp|llm-bridge|loop-scheduler|next" 2>/dev/null; echo "✅ Stopped."; exit 0' INT TERM
  wait
fi
