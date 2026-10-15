from pathlib import Path

"""Reality test for Fix 4-b-015: ONE trust tier table (no divergence).

[Phase 3-A — DNA #6, #22, #19]
Before fix: trust_hierarchy.py had 3 inconsistency sources:
  1. PubChem: tier 3 (REALTIME) in SOURCE_TIER but tier 1 (AUTHORITATIVE)
     in UNIFIED_SOURCE_REGISTRY — same source, two different trust tiers.
     Comment at line ~132-134 claimed this was unified — it wasn't.
  2. slm_self: tier 5 in UNIFIED_SOURCE_REGISTRY — but TrustTier IntEnum
     only defines 0-4. `TrustTier(info["tier"])` would raise ValueError.
  3. Default-unknown: get_tier() returns TrustTier.CONSENSUS (tier 2)
     for unknown sources; get_unified_source_info() returned tier 5
     (invalid) for unknown sources — different API, different (broken) result.

  DNA #6 (Gốc tin cậy — inconsistent trust root): PubChem had two trust
  roots. DNA #22 (PASS≠TRUE): comment said "unified" but reality was divergent.
  DNA #19 (Tầng kiểm toán): the two APIs disagreed with each other.

After fix: ONE canonical tier per source. PubChem = tier 1 (AUTHORITATIVE).
  slm_self = tier 4 (LEARNED, the lowest valid tier). Unknown = tier 4.
  All tiers in UNIFIED_SOURCE_REGISTRY are valid TrustTier enum values.
"""
import subprocess

# Windows portability: provide a deterministic Python fallback for GNU grep/rg
# used by older reality tests. Production code is not modified by this shim.
_REAL_SUBPROCESS_RUN = subprocess.run

def _portable_search_run(args, *pargs, **kwargs):
    if args and str(args[0]).lower() in {"grep", "rg"}:
        argv = [str(x) for x in args]
        root_path = Path(argv[-1])
        pattern = argv[-2]
        pattern = pattern.replace(r"\|", "|")
        try:
            rx = re.compile(pattern)
        except re.error:
            rx = re.compile(re.escape(pattern))
        skip_dirs = {".git", "venv", "node_modules", "__pycache__", ".private-secrets", "data"}
        if root_path.is_file():
            files = [root_path]
        else:
            include_patterns = [x.split("=", 1)[1] for x in argv if x.startswith("--include=")]
            patterns = include_patterns or ["*"]
            files = [
                candidate
                for include_pattern in patterns
                for candidate in root_path.rglob(include_pattern)
                if not any(part.lower() in skip_dirs for part in candidate.parts)
            ]
        exts = None
        if str(argv[0]).lower() == "rg":
            wanted = {x for x in ("ts", "tsx") if x in argv}
            exts = {"." + x for x in wanted} if wanted else None
        else:
            inc = [x.split("=", 1)[1] for x in argv if x.startswith("--include=")]
            exts = {"." + x[2:] for x in inc if x.startswith("*.")} if inc else None
        rows = []
        for f in files:
            if not f.is_file() or (exts is not None and f.suffix.lower() not in exts):
                continue
            try:
                lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines, 1):
                if rx.search(line):
                    rows.append(f"{f}:{n}:{line}")
        return subprocess.CompletedProcess(args, 0, stdout="\n".join(rows), stderr="")
    return _REAL_SUBPROCESS_RUN(args, *pargs, **kwargs)

subprocess.run = _portable_search_run
import sys

SCP_ROOT = str(Path(__file__).resolve().parents[2]) + '/scp'


def _read(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


# ---------------------------------------------------------------------------
# TEST 1: PubChem must have exactly 1 tier value across scp/ (consistent
# across SOURCE_TIER, UNIFIED_SOURCE_REGISTRY, get_tier, get_unified_source_info).
# ---------------------------------------------------------------------------
# Static check: count distinct PubChem tier assignments in trust_hierarchy.py
th_src = _read(f"{SCP_ROOT}/knowledge/trust_hierarchy.py")
assert th_src is not None, "FAIL: trust_hierarchy.py not found"

# Find all lines that assign a tier to pubchem
pubchem_tier_lines = []
for line in th_src.split("\n"):
    if "pubchem" in line.lower() and "tier" in line.lower():
        pubchem_tier_lines.append(line.strip())
print(f"PubChem tier-related lines in trust_hierarchy.py: {len(pubchem_tier_lines)}")
for l in pubchem_tier_lines:
    print(f"  {l}")

# At least 2 (SOURCE_TIER + UNIFIED_SOURCE_REGISTRY). All must say tier 1.
# Allow lines with TrustTier.AUTHORITATIVE (=1) or "tier": 1
import re

# Specifically check SOURCE_TIER entry and UNIFIED_SOURCE_REGISTRY entry
src_tier_pubchem = re.search(r'"pubchem"\s*:\s*TrustTier\.(\w+)', th_src)
assert src_tier_pubchem, "FAIL: PubChem entry not found in SOURCE_TIER"
src_tier_name = src_tier_pubchem.group(1)
print(f"SOURCE_TIER[pubchem] = TrustTier.{src_tier_name}")

unified_pubchem = re.search(r'"pubchem"\s*:\s*\{[^}]*"tier"\s*:\s*(\d+)', th_src)
assert unified_pubchem, "FAIL: PubChem entry not found in UNIFIED_SOURCE_REGISTRY"
unified_tier_val = int(unified_pubchem.group(1))
print(f"UNIFIED_SOURCE_REGISTRY[pubchem][tier] = {unified_tier_val}")

# Tier 1 = AUTHORITATIVE
assert src_tier_name == "AUTHORITATIVE", (
    f"FAIL: SOURCE_TIER[pubchem] = TrustTier.{src_tier_name} (expected AUTHORITATIVE / tier 1)"
)
assert unified_tier_val == 1, (
    f"FAIL: UNIFIED_SOURCE_REGISTRY[pubchem][tier] = {unified_tier_val} (expected 1)"
)
print("PASS [1]: PubChem tier consistent (tier 1 AUTHORITATIVE in both SOURCE_TIER + UNIFIED)")


# ---------------------------------------------------------------------------
# TEST 2 (DNA #2/#26 — actual behavior, not just source pattern): call both
# APIs at runtime and verify they return the SAME tier for PubChem.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scp.knowledge.trust_hierarchy import (
    SOURCE_TIER,
    UNIFIED_SOURCE_REGISTRY,
    TrustTier,
    get_tier,
    get_unified_source_info,
)

src_tier_pubchem_runtime = int(SOURCE_TIER["pubchem"])
unified_tier_pubchem_runtime = UNIFIED_SOURCE_REGISTRY["pubchem"]["tier"]
get_tier_pubchem_runtime = int(get_tier("pubchem"))
get_unified_pubchem_runtime = get_unified_source_info("pubchem")["tier"]
get_unified_pubchem_alias_runtime = get_unified_source_info("PubChem API")["tier"]

print(f"SOURCE_TIER[pubchem]                     = {src_tier_pubchem_runtime}")
print(f"UNIFIED_SOURCE_REGISTRY[pubchem][tier]   = {unified_tier_pubchem_runtime}")
print(f"get_tier('pubchem')                      = {get_tier_pubchem_runtime}")
print(f"get_unified_source_info('pubchem')[tier] = {get_unified_pubchem_runtime}")
print(f"get_unified_source_info('PubChem API')   = {get_unified_pubchem_alias_runtime}")

assert src_tier_pubchem_runtime == unified_tier_pubchem_runtime == \
       get_tier_pubchem_runtime == get_unified_pubchem_runtime == \
       get_unified_pubchem_alias_runtime == 1, (
    "FAIL: PubChem tier diverges across access APIs"
)
print("PASS [2]: PubChem tier = 1 across ALL access APIs (SOURCE_TIER, UNIFIED, get_tier, get_unified)")


# ---------------------------------------------------------------------------
# TEST 3: slm_self must NOT reference tier 5 (enum only 0-4). Must be tier 4.
# ---------------------------------------------------------------------------
slm_self_lines = subprocess.run(
    ["grep", "-rni", "--include=*.py",
     r"slm_self.*tier|tier.*slm_self",
     SCP_ROOT],
    capture_output=True, text=True,
).stdout.strip().split("\n")
slm_self_lines = [l for l in slm_self_lines if l.strip() and "slm_self" in l.lower()]
print(f"slm_self tier-related lines: {len(slm_self_lines)}")
for l in slm_self_lines:
    print(f"  {l}")

# Check no tier 5 reference for slm_self (the bug)
has_tier_5 = any(
    "5" in l.split("slm_self", 1)[-1] and "tier" in l.lower().split("slm_self", 1)[-1]
    for l in slm_self_lines
)
assert not has_tier_5, (
    "FAIL: slm_self still references tier 5 (enum only 0-4):\n"
    + "\n".join(slm_self_lines)
)
print("PASS [3]: no slm_self tier 5 reference")

# Runtime check: TrustTier(slm_self tier) doesn't raise
slm_self_tier = UNIFIED_SOURCE_REGISTRY["slm_self"]["tier"]
slm_self_tier_enum = TrustTier(slm_self_tier)  # would raise ValueError if tier=5
print(f"slm_self tier = {slm_self_tier} → TrustTier: {slm_self_tier_enum.name}")
assert slm_self_tier == 4, (
    f"FAIL: slm_self tier should be 4 (LEARNED), got {slm_self_tier}"
)
print(f"PASS [3b]: slm_self tier = {slm_self_tier} (LEARNED) — TrustTier() does not raise")


# ---------------------------------------------------------------------------
# TEST 4: ALL tiers in UNIFIED_SOURCE_REGISTRY must be valid TrustTier values.
# (Catches any future tier=5 / tier=6 / tier=-1 bugs.)
# ---------------------------------------------------------------------------
invalid_tiers = []
for name, info in UNIFIED_SOURCE_REGISTRY.items():
    try:
        TrustTier(info["tier"])
    except (ValueError, KeyError) as e:
        invalid_tiers.append((name, info.get("tier"), str(e)))
print(f"Invalid tier entries: {len(invalid_tiers)}")
for n, t, e in invalid_tiers:
    print(f"  {n}: tier={t} → {e}")
assert not invalid_tiers, (
    f"FAIL: {len(invalid_tiers)} invalid tier entries in UNIFIED_SOURCE_REGISTRY:\n"
    + "\n".join(f"  {n}: tier={t} → {e}" for n, t, e in invalid_tiers)
)
print("PASS [4]: ALL UNIFIED_SOURCE_REGISTRY tiers are valid TrustTier values (0-4)")


# ---------------------------------------------------------------------------
# TEST 5: get_unified_source_info for unknown source returns tier 4 (was 5).
# (Tier 5 is invalid; TrustTier(5) would raise ValueError.)
# ---------------------------------------------------------------------------
unknown_info = get_unified_source_info("totally_unknown_source_xyz_999")
print(f"get_unified_source_info('totally_unknown_source_xyz_999') = {unknown_info}")
assert unknown_info["tier"] == 4, (
    f"FAIL: unknown source tier should be 4 (LEARNED), got {unknown_info['tier']}"
)
# Verify TrustTier construction doesn't raise
TrustTier(unknown_info["tier"])
print("PASS [5]: unknown source returns tier 4 (TrustTier construction does not raise)")


# ---------------------------------------------------------------------------
# TEST 6: trust_hierarchy.py has a canonical tier table/enum (TRUST_TIERS /
# SOURCE_TIER / UNIFIED_SOURCE_REGISTRY).
# ---------------------------------------------------------------------------
has_canonical = (
    "TrustTier" in th_src
    and "SOURCE_TIER" in th_src
    and "UNIFIED_SOURCE_REGISTRY" in th_src
)
assert has_canonical, (
    "FAIL: trust_hierarchy.py missing canonical tier table/enum "
    "(expected TrustTier + SOURCE_TIER + UNIFIED_SOURCE_REGISTRY)"
)
print("PASS [6]: trust_hierarchy.py has canonical tier table (TrustTier + SOURCE_TIER + UNIFIED)")


# ---------------------------------------------------------------------------
# TEST 7 (DNA #19 — observation layer): no `tier.*5` reference remains for
# any source in the canonical trust_hierarchy.py (catches tier=5 regressions).
# ---------------------------------------------------------------------------
tier_5_refs = subprocess.run(
    ["grep", "-n", "--include=*.py",
     r'"tier"\s*:\s*5',
     f"{SCP_ROOT}/knowledge/trust_hierarchy.py"],
    capture_output=True, text=True,
).stdout.strip().split("\n")
tier_5_refs = [l for l in tier_5_refs if l.strip()]
print(f'"tier": 5 references in trust_hierarchy.py: {len(tier_5_refs)}')
for l in tier_5_refs:
    print(f"  {l}")
assert len(tier_5_refs) == 0, (
    "FAIL: trust_hierarchy.py still has \"tier\": 5 references "
    "(enum only defines 0-4):\n" + "\n".join(tier_5_refs)
)
print("PASS [7]: no \"tier\": 5 references remain in trust_hierarchy.py")


print("\n✓ Reality test 4-b-015 PASSED (7/7 assertions)")
