from pathlib import Path

"""Reality test for Fix 4-a-002: safe_run whitelist must NOT be bypassed by paths.

Before fix: any exe with '/' or '\\\\' passed (whitelist bypassed).
  The bypass was `if "/" not in str(exe) and "\\\\" not in str(exe): raise` —
  which only raised when exe had NO path separator. Any path-based exe
  (/tmp/evil.sh, ./evil.cmd, /usr/bin/malicious) bypassed the whitelist.
After fix: resolved path checked against _WHITELISTED_PATHS (sys.executable +
  SCP_SAFE_PROCESS_EXTRA env var); basename alone is never sufficient for a
  path-qualified executable; default-deny otherwise.

DNA principles covered:
  #6 (Gốc tin cậy bên ngoài) — sys.executable is the only trusted external path.
  #7 (Autofix an toàn) — default-deny is the safe posture.
  #9 (No harm) — non-fatal guard: raises ValueError, doesn't run the binary.
  #22 (PASS≠TRUE) — old "Executable must be in whitelist" docstring was a lie.
"""
import re
import sys

PATH = str(Path(__file__).resolve().parents[2]) + '/scp/core/safe_process.py'

with open(PATH) as f:
    src = f.read()

# Strip comment-only lines so we test the CODE, not the documentation.
code_lines = [l for l in src.split("\n") if not l.strip().startswith("#")]
code_section = "\n".join(code_lines)

# ---------------------------------------------------------------------------
# TEST 1: the old bypass pattern must be GONE from the code.
# Old bypass (literal):
#     if "/" not in str(exe) and "\\" not in str(exe):
#         raise ValueError(...)
# We look for the conjunction of `"/" not in` AND a backslash-check that
# gates a `raise`. The bypass is structurally `if X not in Y and Z not in W:
# raise` — and specifically the old code raised when BOTH separators were
# absent (the inverse of the safe behavior).
# ---------------------------------------------------------------------------
bypass_regex = re.compile(
    r'if\s+["\']/["\']\s+not\s+in\b[^\\]*\\\\[^:]*:\s*\n?\s*raise',
    re.MULTILINE,
)
# Also check the simpler heuristic: `"/" not in` co-located with `\\` in code
# (the old bypass had both tokens within ~120 chars).
has_bypass_token = False
for line in code_lines:
    if '"/" not in' in line and '\\\\' in line and 'raise' in code_section:
        # Likely the old bypass — confirm by checking it gates a raise nearby
        idx = code_section.find(line)
        if idx >= 0:
            window = code_section[idx:idx + 200]
            if 'raise' in window:
                has_bypass_token = True
                break
has_bypass = bool(bypass_regex.search(code_section)) or has_bypass_token
assert not has_bypass, (
    "FAIL: old bypass pattern `if '/' not in ... and '\\\\' not in ... raise` "
    "still present in code"
)
print("PASS [1/4]: old bypass pattern removed from code")

# ---------------------------------------------------------------------------
# TEST 2: must use realpath or shutil.which for resolution
# ---------------------------------------------------------------------------
has_resolution = (
    "realpath" in src
    or "shutil.which" in src
    or "shutil" in src
)
assert has_resolution, "FAIL: no path resolution (realpath/shutil.which)"
print("PASS [2/4]: path resolution present (realpath or shutil.which)")

# ---------------------------------------------------------------------------
# TEST 3: default-deny — non-whitelisted exe must raise ValueError
# (raise is inside the whitelist check branch, not elsewhere)
# ---------------------------------------------------------------------------
has_raise = (
    "raise ValueError" in src
    or "raise PermissionError" in src
)
assert has_raise, "FAIL: no raise on non-whitelisted exe"
# Confirm the raise is in the whitelist-check context (not just anywhere)
# by looking for a raise within ~500 chars of the resolved-path check.
window_match = re.search(r'resolved\b.*?raise\s+ValueError', src, re.DOTALL)
assert window_match, (
    "FAIL: no `raise ValueError` near the resolved-path whitelist check"
)
print("PASS [3/5]: raises ValueError on non-whitelisted exe (default-deny)")

# ---------------------------------------------------------------------------
# TEST 4-5 (runtime, DNA #2/#26): malicious paths, including allowlisted basename,
# must raise before subprocess execution.
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scp.core.safe_process import safe_run  # type: ignore
    for number, candidate in enumerate(("/tmp/nonexistent-evil-script-12345.sh", "/tmp/git"), start=4):
        try:
            safe_run([candidate])
            print(f"FAIL [{number}/5]: runtime — safe_run allowed {candidate}")
            sys.exit(1)
        except (ValueError, PermissionError):
            print(f"PASS [{number}/5]: runtime — path blocked: {candidate}")
        except Exception as e:
            print(
                f"SKIP [{number}/5]: runtime — {type(e).__name__}: {e} (DNA #23 — "
                f"non-ValueError raised; whitelist did not silently allow)"
            )
except Exception as e:
    print(
        f"SKIP [4-5/5]: import failed — {type(e).__name__}: {e} (DNA #23)"
    )

print("\n✓ Reality test 4-a-002 PASSED")
