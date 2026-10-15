#!/usr/bin/env bash
# ============================================================
# SCP STOP ALL — Dừng toàn bộ hệ thống
# Usage:  ./stop-scp.sh
# ============================================================
# Fix 4-d-003: previously used `pkill -f "llm-bridge"` / `"loop-scheduler"`,
# but `bun run dev` cmdline contains NEITHER substring, so pkill matched
# nothing. PID files written by start-scp.sh were never read. Services
# became orphans. Now we kill by PID file first (graceful), then by port
# (cleanup), then verify ports are free (DNA #26 reality test).
#
# Windows equivalent: stop-scp.bat uses `netstat | findstr ":<port> "` +
# `taskkill /f /pid` — the same port-based strategy.
# ============================================================
set -e
LOG_DIR="/tmp/scp-logs"

# Helper: kill by port (Linux). Tries fuser, then lsof, then ss.
kill_port() {
  local port="$1"
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "$port/tcp" 2>/dev/null || true
  elif command -v lsof >/dev/null 2>&1; then
    lsof -ti :"$port" 2>/dev/null | xargs -r kill -TERM 2>/dev/null || true
  elif command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | xargs -r kill -TERM 2>/dev/null || true
  fi
}

# Helper: kill by PID file (graceful SIGTERM, then remove stale pidfile).
kill_pidfile() {
  local name="$1"
  local pidfile="$LOG_DIR/$name.pid"
  if [ -f "$pidfile" ]; then
    local pid
    pid=$(cat "$pidfile" 2>/dev/null || echo "")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "  Stopping $name (PID $pid)..."
      kill -TERM "$pid" 2>/dev/null || true
    fi
    rm -f "$pidfile"
  fi
}

echo "🛑 Stopping SCP services..."

# Kill by PID file first (graceful)
kill_pidfile "llm-bridge"
kill_pidfile "loop-scheduler"
kill_pidfile "scp-server"
kill_pidfile "dashboard"

sleep 1

# Then kill by port (cleanup any orphans that escaped the PID file)
kill_port 8081   # llm-bridge
kill_port 3030   # loop-scheduler
kill_port 8000   # scp python
kill_port 3000   # dashboard

sleep 1

# Verify ports are free (DNA #19, #26 — reality test)
echo "🔍 Verifying ports are free..."
for port in 8081 3030 8000 3000; do
  if command -v ss >/dev/null 2>&1; then
    if ss -tlnp 2>/dev/null | grep -q ":$port " 2>/dev/null; then
      echo "  ⚠️  Port $port still in use — forcing kill"
      kill_port "$port"
      sleep 1
    fi
  fi
done

echo "✅ Stop complete (verified ports checked)"
