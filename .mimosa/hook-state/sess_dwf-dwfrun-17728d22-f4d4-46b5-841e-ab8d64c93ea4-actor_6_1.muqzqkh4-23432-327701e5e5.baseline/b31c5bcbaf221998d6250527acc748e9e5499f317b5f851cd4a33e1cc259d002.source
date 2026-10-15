#!/usr/bin/env bash
PYTHON_BIN="${SCP_PYTHON_BIN:-$(command -v python3 >/dev/null 2>&1 && echo python3 || echo python)}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
run_python() {
  local target="$1"
  shift
  if command -v cygpath >/dev/null 2>&1; then
    target="$(cygpath -w "$target")"
  fi
  "$PYTHON_BIN" "$target" "$@"
}
# Run all reality-test scripts in tests/reality-tests/.
#
# Phase 2 rule (Root Cause 2 — "fix" without reality test → new bug).
# This is the CI gate that enforces DNA #2 (vòng lặp khép kín) + #22
# (PASS≠TRUE) + #26 (reality test): every fix must have a reality-test
# script, and every reality-test script must pass.
#
# Use as a pre-commit hook (symlink target is this script inside the repo's
# tests/ directory — two directory levels above .git/hooks/):
#   ln -s <repo-root>/tests/run-reality-tests.sh .git/hooks/pre-commit
# Or as a CI step:
#   bash tests/run-reality-tests.sh
#
# Exits 1 if any reality-test fails. Exits 0 if all pass (or if no
# reality-tests directory exists yet — graceful no-op for new repos).
set -e

DIR="$(cd "$(dirname "$0")" && pwd)/reality-tests"
if [ ! -d "$DIR" ]; then
  echo "ℹ️  No reality-tests directory yet — nothing to run."
  exit 0
fi

# Retired reality tests — skipped VISIBLY, never silently (S17, 2026-09-13).
# Each entry must be documented in the script's own docstring with the
# retirement reason + the commit(s) that made it obsolete. A retired script
# is still a fail-closed guard: it must exist in the repo (checked below)
# and must itself FAIL if its retirement premise is broken.
RETIRED_REALITY_TESTS=(
  "reality_4-c-022.py"  # S17: SA-4 target scp/api/_lifespan.py deleted as dead code (B2: 4e935a7 + c1dcde4); R7-2 pattern exists nowhere under scp/ — see script docstring.
)
is_retired() {
  local candidate="$1"
  local entry
  for entry in "${RETIRED_REALITY_TESTS[@]}"; do
    [ "$candidate" = "$entry" ] && return 0
  done
  return 1
}

PASS=0
FAIL=0
RETIRED=0
FAILED_NAMES=()

for script in "$DIR"/reality_*.py "$DIR"/reality_*.sh; do
  # shellcheck disable=SC2153
  [ -e "$script" ] || continue
  name=$(basename "$script")
  if is_retired "$name"; then
    echo "  ⊘ $name (RETIRED — see script docstring for reason + commit refs)"
    RETIRED=$((RETIRED + 1))
    continue
  fi
  if [[ "$script" == *.py ]]; then
    if run_python "$script" >/dev/null 2>&1; then
      echo "  ✓ $name"
      PASS=$((PASS + 1))
    else
      echo "  ✗ $name"
      FAILED_NAMES+=("$name")
      FAIL=$((FAIL + 1))
    fi
  elif [[ "$script" == *.sh ]]; then
    if bash "$script" >/dev/null 2>&1; then
      echo "  ✓ $name"
      PASS=$((PASS + 1))
    else
      echo "  ✗ $name"
      FAILED_NAMES+=("$name")
      FAIL=$((FAIL + 1))
    fi
  fi
done

echo ""
echo "Reality-tests: $PASS passed, $FAIL failed, $RETIRED retired (skipped visibly)"

# Fail-closed: a retired entry must still exist as a repo file. If the file
# is deleted while still listed, the retirement record is dangling — fail
# loudly instead of letting the gate go quietly green.
for entry in "${RETIRED_REALITY_TESTS[@]}"; do
  if [ ! -f "$DIR/$entry" ]; then
    echo "  ✗ retired test listed but file missing: $entry (fix the skip-list or restore the script)"
    FAILED_NAMES+=("$entry(retired-file-missing)")
    FAIL=$((FAIL + 1))
  fi
done

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "Failed tests (re-run individually for details):"
  for n in "${FAILED_NAMES[@]}"; do
    echo "  - $n"
  done
  exit 1
fi
exit 0
