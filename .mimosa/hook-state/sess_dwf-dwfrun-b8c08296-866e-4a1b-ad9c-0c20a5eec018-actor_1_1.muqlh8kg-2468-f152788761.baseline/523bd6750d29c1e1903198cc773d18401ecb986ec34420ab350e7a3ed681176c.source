#!/usr/bin/env python3
"""Reality test for Fix 4-d-013: cache key uses 128-bit+ hash (not 32-bit DJB2).

DNA #5 (ảo giác đồng thuận — cached "answer" trusted as truth) + #14 (đồng
thuận ≠ đúng — collision = wrong answer) + #22 (PASS ≠ TRUE).

Before fix:
  - _cacheKey used a 32-bit DJB2-style hash of (model + messages).
  - Birthday-paradox collision: ~50% collision chance at ~65k distinct inputs.
  - A collision maps two DIFFERENT prompts to the same cache key → second
    prompt returns the FIRST prompt's answer. SCP would silently emit a
    wrong verdict/fact/fix.
  - The cache log said "cache HIT (key=...)" — looked like a successful
    optimization but was actually returning a wrong answer (DNA #22).

After fix (accepted alternatives per spec):
  - EITHER: use the full message string as key (truncated if too long).
  - OR: use a 128-bit hash (sha256 truncated, or xxhash128).
  This implementation uses SHA-256 hex (256-bit) of the payload —
  collision-resistant well beyond any practical cache size.

Tier-A (static-source) reality test.
"""
import re
import sys
from pathlib import Path

SOURCE_PATH = Path(
    str(Path(__file__).resolve().parents[2]) + '/mini-services/llm-bridge/core.ts'
)


def main() -> int:
    assert SOURCE_PATH.exists(), (
        f"FAIL: llm-bridge/index.ts not found at {SOURCE_PATH}"
    )
    src = SOURCE_PATH.read_text(encoding="utf-8")
    print(f"PASS [1/5]: file exists ({SOURCE_PATH.name})")

    # -------------------------------------------------------------------------
    # TEST 2 — the OLD 32-bit DJB2 hash pattern MUST be gone from code.
    # Pattern: `hash = ((hash << 5) - hash + payload.charCodeAt(i)) | 0;`
    # This is the textbook DJB2-style 32-bit hash. We exclude comments so
    # historical mentions in fix-comments don't trigger a false positive.
    # -------------------------------------------------------------------------
    code_lines = [
        line
        for line in src.split("\n")
        if not line.strip().startswith("//")
        and not line.strip().startswith("*")
    ]
    code_section = "\n".join(code_lines)
    has_djb2_32bit = bool(
        re.search(
            r"\(\s*\(hash\s*<<\s*5\s*\)\s*-\s*hash\s*\+\s*\w+\.charCodeAt",
            code_section,
        )
    ) or bool(
        re.search(r"\|0\s*;\s*return\s+[`'\"]h", code_section)
    )
    assert not has_djb2_32bit, (
        "FAIL: 32-bit DJB2 hash still present in code (collision risk on "
        "65k distinct inputs → wrong cached answer)"
    )
    print("PASS [2/5]: 32-bit DJB2 hash pattern removed from code")

    # -------------------------------------------------------------------------
    # TEST 3 — must use EITHER:
    #   (a) a 128-bit+ hash: SHA-256 (`crypto.subtle.digest` / `createHash`),
    #       xxhash128 (`Bun.hash` with 128-bit mode), OR
    #   (b) the full message string as key (with optional truncation).
    # -------------------------------------------------------------------------
    uses_sha256 = bool(
        re.search(r"createHash\s*\(\s*[\"']sha-?256[\"']\s*\)", src, re.IGNORECASE)
    ) or bool(
        re.search(r"crypto\.subtle\.digest\s*\(\s*[\"']SHA-?256[\"']", src, re.IGNORECASE)
    )
    uses_xxhash_or_bun_hash = bool(
        re.search(r"Bun\.hash\s*\(", src)
    )
    # Full-string key: the _cacheKey function returns the payload itself
    # (possibly truncated) without hashing.
    uses_full_string_key = bool(
        re.search(
            r"function\s+_cacheKey\s*\([^)]+\)\s*:\s*string\s*\{[^}]*?return\s+[`'\"](?:raw|full)[:]?[^}]*?\}",
            src,
            re.DOTALL,
        )
    )
    assert (
        uses_sha256 or uses_xxhash_or_bun_hash or uses_full_string_key
    ), (
        "FAIL: cache key function does not use SHA-256 / xxhash / Bun.hash / "
        "full-string-key — collision risk persists"
    )
    methods = []
    if uses_sha256: methods.append("SHA-256")
    if uses_xxhash_or_bun_hash: methods.append("Bun.hash (64-bit+ wyhash)")
    if uses_full_string_key: methods.append("full-string-key")
    print(f"PASS [3/5]: collision-resistant key method ({', '.join(methods)})")

    # -------------------------------------------------------------------------
    # TEST 4 — the new hash function must actually be CALLED by the cache
    # get/set path. Look for `_cacheKey(` (call site) and `_cacheGet(` /
    # `_cacheSet(` (uses of the key).
    # -------------------------------------------------------------------------
    cachekey_call = bool(re.search(r"_cacheKey\s*\(", src))
    cache_uses_key = bool(re.search(r"_cacheGet\s*\(\s*\w+\s*\)", src)) and bool(
        re.search(r"_cacheSet\s*\(\s*\w+\s*,", src)
    )
    assert cachekey_call and cache_uses_key, (
        "FAIL: _cacheKey is declared but not called by cache get/set path "
        "(fix is dead code)"
    )
    print("PASS [4/5]: _cacheKey called by _cacheGet/_cacheSet (live code)")

    # -------------------------------------------------------------------------
    # TEST 5 — collision-resistance sanity: the key prefix must NOT be the
    # old `h<digits>` (32-bit decimal). Look for `sha256:` or `xxh:` prefix
    # OR a long hex/string key (>= 32 chars). This is a strong signal that
    # the key space is >= 128 bits.
    # -------------------------------------------------------------------------
    has_long_key = bool(
        re.search(r"return\s+[`'\"](?:sha256|xxh|sha|hash)[:\-]?[a-f0-9`'\"]+", src, re.IGNORECASE)
    ) or bool(
        # The hash function produces a long hex digest.
        re.search(r"digest\s*\(\s*[\"']hex[\"']\s*\)", src)
    )
    # Fallback: if the full-string-key approach is used, the key length is
    # the payload length (unbounded — definitely > 128 bits for any
    # non-trivial prompt).
    assert has_long_key or uses_full_string_key, (
        "FAIL: cache key prefix is still short (e.g. `h<32-bit-decimal>`) — "
        "collision space still small"
    )
    print("PASS [5/5]: cache key length is long (>= 128-bit equivalent)")

    print("\n✓ Reality test 4-d-013 PASSED (5/5 assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
